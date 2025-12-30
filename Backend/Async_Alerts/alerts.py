import os
from twilio.rest import Client
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import logging
from datetime import datetime
from colorama import Fore, Back, Style, init
from dotenv import load_dotenv
load_dotenv()

init(autoreset=True)

account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
twilio_phone = os.environ.get('TWILIO_PHONE_NUMBER')

client = Client(account_sid, auth_token)


class ColoredFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Back.WHITE
    }

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, Fore.WHITE)
        record.levelname = f"{log_color}{record.levelname}{Style.RESET_ALL}"
        record.msg = f"{log_color}{record.msg}{Style.RESET_ALL}"
        return super().format(record)


logger = logging.getLogger('TwilioAlertSystem')
logger.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

file_handler = logging.FileHandler(
    f'twilio_alerts_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
file_handler.setLevel(logging.DEBUG)

console_format = ColoredFormatter(
    '%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
file_format = logging.Formatter(
    '%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

console_handler.setFormatter(console_format)
file_handler.setFormatter(file_format)

logger.addHandler(console_handler)
logger.addHandler(file_handler)


def make_single_call(to_number, from_number, twiml_url, attempt):
    try:
        logger.info(f"Initiating call #{attempt} to {to_number}")
        call = client.calls.create(
            to=to_number,
            from_=from_number,
            url=twiml_url,
            status_callback_method='POST',
            status_callback_event=['completed', 'failed']
        )
        logger.info(
            f"Call #{attempt} to {to_number} - SID: {call.sid} - Status: {call.status}")
        return {
            'success': True,
            'call_sid': call.sid,
            'to': to_number,
            'attempt': attempt,
            'status': call.status
        }
    except Exception as e:
        logger.error(
            f"Call #{attempt} to {to_number} FAILED - Error: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'to': to_number,
            'attempt': attempt
        }


def make_parallel_calls_for_attempt(contacts, from_number, attempt):
    logger.info(
        f"{Fore.YELLOW}Starting call round #{attempt} for all contacts in parallel")
    results = []

    with ThreadPoolExecutor(max_workers=len(contacts)) as executor:
        futures = {
            executor.submit(
                make_single_call,
                contact['phone'],
                from_number,
                contact['twiml_url'],
                attempt
            ): contact
            for contact in contacts
        }

        for future in as_completed(futures):
            contact = futures[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(
                    f"Exception in call to {contact['phone']}: {str(e)}")
                results.append({
                    'success': False,
                    'error': str(e),
                    'to': contact['phone'],
                    'attempt': attempt
                })

    logger.info(
        f"{Fore.YELLOW}Completed call round #{attempt} for all contacts")
    return results


def call_all_contacts_multiple_times(contacts, from_number, num_attempts=5, wait_time=40):
    all_call_results = {contact['phone']: [] for contact in contacts}

    for attempt in range(1, num_attempts + 1):
        round_results = make_parallel_calls_for_attempt(
            contacts, from_number, attempt)

        for result in round_results:
            all_call_results[result['to']].append(result)

        if attempt < num_attempts:
            logger.info(
                f"{Fore.CYAN}Waiting {wait_time} seconds before next call round...")
            time.sleep(wait_time)

    return all_call_results


def send_sms_parallel(contacts, from_number):
    logger.info(f"{Fore.YELLOW}Sending SMS to all contacts in parallel")
    results = {}

    def send_single_sms(contact):
        to_number = contact['phone']
        message = contact.get('sms_message', 'This is an alert message.')
        try:
            logger.info(f"Sending SMS to {to_number}")
            message_obj = client.messages.create(
                body=message,
                from_=from_number,
                to=to_number
            )
            logger.info(
                f"SMS to {to_number} - SID: {message_obj.sid} - Status: {message_obj.status}")
            return {
                'phone': to_number,
                'success': True,
                'message_sid': message_obj.sid,
                'status': message_obj.status
            }
        except Exception as e:
            logger.error(f"SMS to {to_number} FAILED - Error: {str(e)}")
            return {
                'phone': to_number,
                'success': False,
                'error': str(e)
            }

    with ThreadPoolExecutor(max_workers=len(contacts)) as executor:
        futures = {executor.submit(
            send_single_sms, contact): contact for contact in contacts}

        for future in as_completed(futures):
            try:
                result = future.result()
                results[result['phone']] = result
            except Exception as e:
                contact = futures[future]
                logger.error(
                    f"Exception sending SMS to {contact['phone']}: {str(e)}")
                results[contact['phone']] = {
                    'phone': contact['phone'],
                    'success': False,
                    'error': str(e)
                }

    return results


def send_parallel_alerts(contacts, max_workers=10, num_call_attempts=5, wait_time_between_rounds=40):
    logger.info(f"{Fore.MAGENTA}{'#'*60}")
    logger.info(f"{Fore.MAGENTA}STARTING PARALLEL ALERT SYSTEM")
    logger.info(f"{Fore.MAGENTA}Total contacts: {len(contacts)}")
    logger.info(
        f"{Fore.MAGENTA}Call attempts per contact: {num_call_attempts}")
    logger.info(
        f"{Fore.MAGENTA}Wait time between rounds: {wait_time_between_rounds} seconds")
    logger.info(f"{Fore.MAGENTA}{'#'*60}")

    start_time = time.time()

    call_results = call_all_contacts_multiple_times(
        contacts, twilio_phone, num_call_attempts, wait_time_between_rounds)

    sms_results = send_sms_parallel(contacts, twilio_phone)

    all_results = []
    for contact in contacts:
        phone = contact['phone']
        all_results.append({
            'phone': phone,
            'calls': call_results.get(phone, []),
            'sms': sms_results.get(phone, {'success': False, 'error': 'No SMS result'})
        })

    elapsed_time = time.time() - start_time
    logger.info(f"{Fore.MAGENTA}{'#'*60}")
    logger.info(f"{Fore.MAGENTA}ALERT SYSTEM COMPLETED")
    logger.info(f"{Fore.MAGENTA}Total time: {elapsed_time:.2f} seconds")
    logger.info(f"{Fore.MAGENTA}{'#'*60}")

    return all_results


def print_summary(results):
    logger.info(f"\n{Fore.CYAN}{'='*60}")
    logger.info(f"{Fore.CYAN}FINAL SUMMARY REPORT")
    logger.info(f"{Fore.CYAN}{'='*60}")

    for result in results:
        logger.info(f"\n{Fore.YELLOW}Phone: {result['phone']}")
        if 'error' in result:
            logger.error(f"Error: {result['error']}")
        else:
            total_calls = len(result['calls'])
            successful_calls = sum(1 for c in result['calls'] if c['success'])
            logger.info(f"Calls: {successful_calls}/{total_calls} successful")
            logger.info(
                f"SMS: {'✓ Sent' if result['sms']['success'] else '✗ Failed'}")

            for call in result['calls']:
                if call['success']:
                    logger.debug(
                        f"  Call #{call['attempt']}: {call['status']} (SID: {call['call_sid']})")
                else:
                    logger.debug(f"  Call #{call['attempt']}: FAILED")


if __name__ == "__main__":
    contacts = [
        {
            'phone': '+918850755760',  # Joel Pawar
            'twiml_url': 'http://demo.twilio.com/docs/voice.xml',
            'sms_message': 'URGENT: This is an emergency alert! from Government of India by DISHA , Make sure you are safe'
        },
        {
            'phone': '+919529685725',  # Sereena Thomas
            'twiml_url': 'http://demo.twilio.com/docs/voice.xml',
            'sms_message': 'URGENT: This is an emergency alert! from Government of India by DISHA , Make sure you are safe'
        },
        {
            'phone': '+919322945843',  # Seane Dcosta
            'twiml_url': 'http://demo.twilio.com/docs/voice.xml',
            'sms_message': 'URGENT: This is an emergency alert! from Government of India by DISHA , Make sure you are safe'
        }
    ]

    results = send_parallel_alerts(
        contacts, max_workers=5, num_call_attempts=5, wait_time_between_rounds=40)

    print_summary(results)

    # alerts done
