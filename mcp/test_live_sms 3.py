#!/usr/bin/env python3
"""
Test LIVE SMS sending with real Twilio credentials.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    from twilio.rest import Client

    # Get real credentials
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    twilio_phone = os.getenv('TWILIO_PHONE_NUMBER')

    print("🚀 Testing LIVE SMS with Real Twilio Credentials")
    print("=" * 50)
    print(f"Account SID: {account_sid[:10]}...{account_sid[-4:]}")
    print(f"From Phone: {twilio_phone}")
    print()

    # Initialize Twilio client
    client = Client(account_sid, auth_token)

    # Test phone numbers
    test_numbers = [
        "+918850755760",  # Joel Pawar
        "+919529685725",  # Sereena Thomas
        "+919322945843",  # Seane Dcosta
    ]

    # Test message
    message_body = "🚨 DISHA EMERGENCY TEST 🚨\nThis is a test of the real notification system. Your phone number is registered for emergency alerts from the Government of India DISHA system. Stay safe!"

    print("📱 Sending LIVE SMS to registered numbers...")
    print("-" * 40)

    successful_sends = 0
    failed_sends = 0

    for phone_number in test_numbers:
        try:
            print(f"Sending to {phone_number}...", end=" ")

            message = client.messages.create(
                body=message_body,
                from_=twilio_phone,
                to=phone_number
            )

            print(f"✅ SUCCESS (SID: {message.sid})")
            successful_sends += 1

        except Exception as e:
            print(f"❌ FAILED: {e}")
            failed_sends += 1

    print()
    print("📊 RESULTS:")
    print(f"✅ Successful: {successful_sends}")
    print(f"❌ Failed: {failed_sends}")
    print(f"📱 Total: {len(test_numbers)}")

    if successful_sends > 0:
        print()
        print("🎉 REAL SMS NOTIFICATIONS ARE WORKING!")
        print("People will receive actual emergency alerts when disasters are reported!")

except ImportError:
    print("❌ Twilio library not installed. Run: pip install twilio")
except Exception as e:
    print(f"❌ Error: {e}")
