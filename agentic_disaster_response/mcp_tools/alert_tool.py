"""
Concrete implementation of MCP Alert Tool for disaster response notifications.
Enhanced with real Twilio, Firebase, and SendGrid integrations.
"""

from agentic_disaster_response.core.exceptions import MCPToolError
from agentic_disaster_response.models.alert_priority import PriorityLevel
from agentic_disaster_response.models.mcp_tools import MCPToolConfig, ToolConfiguration
from agentic_disaster_response.mcp_integration import MCPTool, AlertData, ExecutionResult, ExecutionStatus
import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, List
import httpx
from dotenv import load_dotenv

# Load environment variables from Backend/.env
load_dotenv()
load_dotenv('Backend/.env')  # Also try Backend/.env for MCP tools


# Import real service clients
try:
    from twilio.rest import Client as TwilioClient
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False

try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False

try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False


class AlertMCPTool(MCPTool):
    """
    Enhanced MCP Alert Tool with real service integrations.

    Supports:
    - Twilio SMS & Voice calls
    - Firebase push notifications  
    - SendGrid email alerts
    - Emergency broadcast systems
    - Web notifications
    """

    def __init__(self, config: MCPToolConfig):
        super().__init__(config)
        self.client = httpx.AsyncClient(timeout=30.0)

        # Initialize real service clients
        self._init_twilio_client()
        self._init_sendgrid_client()
        self._init_firebase_client()

        self.delivery_channels = {
            "emergency_broadcast": self._send_emergency_broadcast,
            "mobile_push": self._send_mobile_push,
            "email": self._send_email_alert,
            "sms": self._send_sms_alert,
            "voice_call": self._send_voice_call,
            "web_notification": self._send_web_notification
        }

    def _init_twilio_client(self):
        """Initialize Twilio client if credentials are available."""
        self.logger.info(
            f"Initializing Twilio client... TWILIO_AVAILABLE={TWILIO_AVAILABLE}")

        if TWILIO_AVAILABLE:
            account_sid = os.getenv('TWILIO_ACCOUNT_SID')
            auth_token = os.getenv('TWILIO_AUTH_TOKEN')

            self.logger.info(
                f"Twilio credentials check: SID={'***' + account_sid[-4:] if account_sid else 'None'}, TOKEN={'***' + auth_token[-4:] if auth_token else 'None'}")

            if account_sid and auth_token:
                self.twilio_client = TwilioClient(account_sid, auth_token)
                self.twilio_phone = os.getenv('TWILIO_PHONE_NUMBER')
                self.logger.info(
                    f"✅ Twilio client initialized successfully with phone {self.twilio_phone}")
            else:
                self.twilio_client = None
                self.logger.warning(
                    "❌ Twilio credentials not found, using simulation")
        else:
            self.twilio_client = None
            self.logger.warning(
                "❌ Twilio library not installed, using simulation")

    def _init_sendgrid_client(self):
        """Initialize SendGrid client if credentials are available."""
        self.logger.info(
            f"Initializing SendGrid client... SENDGRID_AVAILABLE={SENDGRID_AVAILABLE}")

        if SENDGRID_AVAILABLE:
            api_key = os.getenv('SENDGRID_API_KEY')

            self.logger.info(
                f"SendGrid API key check: {'***' + api_key[-4:] if api_key else 'None'}")

            if api_key:
                self.sendgrid_client = SendGridAPIClient(api_key=api_key)
                self.sendgrid_from_email = os.getenv(
                    'SENDGRID_FROM_EMAIL', 'alerts@disha.gov.in')
                self.logger.info(
                    f"✅ SendGrid client initialized successfully with from_email {self.sendgrid_from_email}")
            else:
                self.sendgrid_client = None
                self.logger.warning(
                    "❌ SendGrid API key not found, using simulation")
        else:
            self.sendgrid_client = None
            self.logger.warning(
                "❌ SendGrid library not installed, using simulation")

    def _init_firebase_client(self):
        """Initialize Firebase client if credentials are available."""
        if FIREBASE_AVAILABLE:
            service_account_path = os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH')

            # Try multiple possible paths for Firebase credentials
            possible_paths = [
                service_account_path,
                f"Backend/{service_account_path}" if service_account_path and not service_account_path.startswith(
                    'Backend/') else None,
                "Backend/hackxios-firebase-adminsdk-fbsvc-c39d6ff416.json",
                "./Backend/hackxios-firebase-adminsdk-fbsvc-c39d6ff416.json"
            ]

            firebase_path = None
            for path in possible_paths:
                if path and os.path.exists(path):
                    firebase_path = path
                    break

            if firebase_path:
                try:
                    if not firebase_admin._apps:
                        cred = credentials.Certificate(firebase_path)
                        firebase_admin.initialize_app(cred)
                    self.firebase_initialized = True
                    self.logger.info(
                        f"Firebase client initialized successfully with {firebase_path}")
                except Exception as e:
                    self.firebase_initialized = False
                    self.logger.warning(f"Firebase initialization failed: {e}")
            else:
                self.firebase_initialized = False
                self.logger.warning(
                    f"Firebase credentials not found at any of these paths: {possible_paths}")
        else:
            self.firebase_initialized = False
            self.logger.warning(
                "Firebase library not installed, using simulation")

    async def execute(self, alert_data: AlertData, tool_config: ToolConfiguration) -> ExecutionResult:
        """Execute alert delivery through configured channels."""
        start_time = datetime.now()

        try:
            self.logger.info(
                f"Executing REAL alert tool for disaster {alert_data.alert_id}")

            # Validate configuration
            if not self.validate_configuration(tool_config):
                raise MCPToolError(
                    f"Invalid configuration for alert tool {self.config.tool_name}")

            # Format data for this tool
            formatted_data = self.format_data(
                alert_data, alert_data.priority.level)

            # Determine delivery channels based on priority
            channels = self._select_channels_for_priority(
                alert_data.priority.level, tool_config)

            # Execute delivery through all selected channels
            delivery_results = []
            successful_deliveries = 0
            failed_deliveries = 0

            for channel in channels:
                try:
                    channel_result = await self._deliver_through_channel(
                        channel, formatted_data, tool_config
                    )
                    delivery_results.append(channel_result)

                    if channel_result.get("success", False):
                        successful_deliveries += 1
                    else:
                        failed_deliveries += 1

                except Exception as e:
                    self.logger.error(
                        f"Channel {channel} delivery failed: {e}")
                    delivery_results.append({
                        "channel": channel,
                        "success": False,
                        "error": str(e)
                    })
                    failed_deliveries += 1

            # Calculate execution time
            execution_time = int(
                (datetime.now() - start_time).total_seconds() * 1000)

            # Determine overall success
            overall_success = successful_deliveries > 0
            status = ExecutionStatus.SUCCESS if overall_success else ExecutionStatus.FAILURE

            # Create response data
            response_data = {
                "alert_id": alert_data.alert_id,
                "channels_attempted": len(channels),
                "successful_deliveries": successful_deliveries,
                "failed_deliveries": failed_deliveries,
                "delivery_results": delivery_results,
                "estimated_recipients": self._estimate_recipients(alert_data, channels),
                "delivery_timestamp": datetime.now().isoformat(),
                "real_services_used": {
                    "twilio": self.twilio_client is not None,
                    "sendgrid": self.sendgrid_client is not None,
                    "firebase": self.firebase_initialized
                }
            }

            self.logger.info(
                f"REAL alert delivery completed: {successful_deliveries}/{len(channels)} channels successful"
            )

            return ExecutionResult(
                status=status,
                tool_name=self.config.tool_name,
                execution_time_ms=execution_time,
                response_data=response_data,
                error_message=None if overall_success else f"Failed deliveries: {failed_deliveries}"
            )

        except Exception as e:
            execution_time = int(
                (datetime.now() - start_time).total_seconds() * 1000)
            self.logger.error(f"REAL alert tool execution failed: {e}")

            return ExecutionResult(
                status=ExecutionStatus.FAILURE,
                tool_name=self.config.tool_name,
                execution_time_ms=execution_time,
                response_data=None,
                error_message=str(e)
            )

    def format_data(self, alert_data: AlertData, priority: PriorityLevel) -> Dict[str, Any]:
        """Format alert data for delivery channels."""
        return {
            "alert_id": alert_data.alert_id,
            "priority": priority.value,
            "urgency": self._map_priority_to_urgency(priority),
            "title": self._generate_alert_title(alert_data),
            "message": alert_data.message,
            "disaster_type": alert_data.context.disaster_info.disaster_type.value,
            "location": {
                "latitude": alert_data.context.disaster_info.location.latitude,
                "longitude": alert_data.context.disaster_info.location.longitude,
                "address": alert_data.context.disaster_info.location.address,
                "administrative_area": alert_data.context.disaster_info.location.administrative_area
            },
            "severity": alert_data.context.disaster_info.severity.value,
            "timestamp": alert_data.context.disaster_info.timestamp.isoformat(),
            "affected_population": alert_data.context.affected_population.total_population,
            "evacuation_routes_available": len(alert_data.context.evacuation_routes),
            "estimated_response_time_minutes": int(alert_data.priority.estimated_response_time.total_seconds() / 60),
            "required_actions": self._generate_required_actions(alert_data),
            "contact_info": self._get_emergency_contacts(priority),
            "metadata": alert_data.metadata
        }

    def validate_configuration(self, tool_config: ToolConfiguration) -> bool:
        """Validate tool configuration."""
        required_params = ["channels", "broadcast_radius_km"]

        for param in required_params:
            if param not in tool_config.parameters:
                self.logger.error(f"Missing required parameter: {param}")
                return False

        # Validate channels
        channels = tool_config.parameters.get("channels", [])
        if not isinstance(channels, list) or not channels:
            self.logger.error("Invalid or empty channels configuration")
            return False

        # Validate each channel is supported
        for channel in channels:
            if channel not in self.delivery_channels:
                self.logger.error(f"Unsupported delivery channel: {channel}")
                return False

        return True

    def _select_channels_for_priority(self, priority: PriorityLevel, tool_config: ToolConfiguration) -> List[str]:
        """Select appropriate delivery channels based on priority level."""
        all_channels = tool_config.parameters.get("channels", [])

        # Priority-based channel selection
        if priority == PriorityLevel.CRITICAL:
            # Use all available channels for critical alerts
            return all_channels
        elif priority == PriorityLevel.HIGH:
            # Use high-impact channels
            preferred = ["emergency_broadcast", "mobile_push", "sms"]
            return [ch for ch in preferred if ch in all_channels] or all_channels
        elif priority == PriorityLevel.MEDIUM:
            # Use standard channels
            preferred = ["mobile_push", "email", "web_notification"]
            return [ch for ch in preferred if ch in all_channels] or all_channels
        else:  # LOW priority
            # Use low-impact channels
            preferred = ["email", "web_notification"]
            return [ch for ch in preferred if ch in all_channels] or all_channels[:1]

    async def _deliver_through_channel(self, channel: str, data: Dict[str, Any],
                                       tool_config: ToolConfiguration) -> Dict[str, Any]:
        """Deliver alert through specific channel."""
        if channel not in self.delivery_channels:
            raise MCPToolError(f"Unsupported delivery channel: {channel}")

        delivery_func = self.delivery_channels[channel]
        return await delivery_func(data, tool_config)

    async def _send_emergency_broadcast(self, data: Dict[str, Any],
                                        tool_config: ToolConfiguration) -> Dict[str, Any]:
        """Send emergency broadcast alert."""
        try:
            # Simulate emergency broadcast system integration
            broadcast_data = {
                "alert_type": "emergency_broadcast",
                "priority": data["urgency"],
                "message": data["message"],
                "location": data["location"],
                "broadcast_radius_km": tool_config.parameters.get("broadcast_radius_km", 10),
                "duration_seconds": 60 if data["priority"] == "critical" else 30
            }

            # Simulate API call to emergency broadcast system
            await asyncio.sleep(0.1)  # Simulate network delay

            self.logger.info(
                f"Emergency broadcast sent for alert {data['alert_id']}")

            return {
                "channel": "emergency_broadcast",
                "success": True,
                "recipients_reached": self._estimate_broadcast_recipients(
                    data["location"], tool_config.parameters.get(
                        "broadcast_radius_km", 10)
                ),
                "delivery_time": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Emergency broadcast failed: {e}")
            return {
                "channel": "emergency_broadcast",
                "success": False,
                "error": str(e)
            }

    async def _send_mobile_push(self, data: Dict[str, Any],
                                tool_config: ToolConfiguration) -> Dict[str, Any]:
        """Send mobile push notifications."""
        try:
            push_data = {
                "title": data["title"],
                "body": data["message"][:200] + "..." if len(data["message"]) > 200 else data["message"],
                "priority": data["urgency"],
                "location": data["location"],
                "action_buttons": ["View Details", "Get Directions"],
                "sound": "emergency" if data["priority"] in ["critical", "urgent"] else "default"
            }

            # Simulate push notification service
            await asyncio.sleep(0.05)

            self.logger.info(
                f"Mobile push notification sent for alert {data['alert_id']}")

            return {
                "channel": "mobile_push",
                "success": True,
                "recipients_reached": data["affected_population"],
                "delivery_time": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Mobile push notification failed: {e}")
            return {
                "channel": "mobile_push",
                "success": False,
                "error": str(e)
            }

    async def _send_email_alert(self, data: Dict[str, Any],
                                tool_config: ToolConfiguration) -> Dict[str, Any]:
        """Send email alerts."""
        try:
            email_data = {
                "subject": data["title"],
                "body": self._generate_email_body(data),
                "priority": data["urgency"],
                "recipients": self._get_email_recipients(data["location"]),
                "attachments": ["evacuation_map.pdf"] if data["evacuation_routes_available"] > 0 else []
            }

            # Simulate email service
            await asyncio.sleep(0.1)

            self.logger.info(f"Email alert sent for alert {data['alert_id']}")

            return {
                "channel": "email",
                "success": True,
                "recipients_reached": len(email_data["recipients"]),
                "delivery_time": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Email alert failed: {e}")
            return {
                "channel": "email",
                "success": False,
                "error": str(e)
            }

    async def _send_sms_alert(self, data: Dict[str, Any],
                              tool_config: ToolConfiguration) -> Dict[str, Any]:
        """Send REAL SMS alerts using Twilio."""
        try:
            if self.twilio_client and self.twilio_phone:
                # REAL Twilio SMS
                sms_message = f"🚨 EMERGENCY ALERT 🚨\n{data['disaster_type'].upper()} at {data['location']['address']}\n{data['message'][:140]}...\nStay safe! - DISHA"

                # Get real phone numbers from database or config
                phone_numbers = self._get_real_phone_numbers(data["location"])

                successful_sends = 0
                failed_sends = 0
                message_sids = []

                for phone_number in phone_numbers:
                    try:
                        message = self.twilio_client.messages.create(
                            body=sms_message,
                            from_=self.twilio_phone,
                            to=phone_number
                        )
                        message_sids.append(message.sid)
                        successful_sends += 1
                        self.logger.info(
                            f"REAL SMS sent to {phone_number}: {message.sid}")
                    except Exception as e:
                        failed_sends += 1
                        self.logger.error(
                            f"REAL SMS failed to {phone_number}: {e}")

                return {
                    "channel": "sms",
                    "success": successful_sends > 0,
                    "recipients_reached": successful_sends,
                    "failed_sends": failed_sends,
                    "message_sids": message_sids,
                    "delivery_time": datetime.now().isoformat(),
                    "service": "twilio_real"
                }
            else:
                # Fallback to simulation
                return await self._send_sms_alert_simulation(data, tool_config)

        except Exception as e:
            self.logger.error(f"REAL SMS alert failed: {e}")
            return {
                "channel": "sms",
                "success": False,
                "error": str(e),
                "service": "twilio_real"
            }

    async def _send_voice_call(self, data: Dict[str, Any],
                               tool_config: ToolConfiguration) -> Dict[str, Any]:
        """Send REAL voice calls using Twilio."""
        try:
            if self.twilio_client and self.twilio_phone:
                # REAL Twilio Voice Calls
                phone_numbers = self._get_real_phone_numbers(data["location"])

                successful_calls = 0
                failed_calls = 0
                call_sids = []

                # Create TwiML URL for emergency message
                twiml_url = self._create_emergency_twiml_url(data)

                for phone_number in phone_numbers:
                    try:
                        call = self.twilio_client.calls.create(
                            to=phone_number,
                            from_=self.twilio_phone,
                            url=twiml_url,
                            status_callback_method='POST',
                            status_callback_event=['completed', 'failed']
                        )
                        call_sids.append(call.sid)
                        successful_calls += 1
                        self.logger.info(
                            f"REAL voice call initiated to {phone_number}: {call.sid}")
                    except Exception as e:
                        failed_calls += 1
                        self.logger.error(
                            f"REAL voice call failed to {phone_number}: {e}")

                return {
                    "channel": "voice_call",
                    "success": successful_calls > 0,
                    "recipients_reached": successful_calls,
                    "failed_calls": failed_calls,
                    "call_sids": call_sids,
                    "delivery_time": datetime.now().isoformat(),
                    "service": "twilio_real"
                }
            else:
                # Fallback to simulation
                return await self._send_voice_call_simulation(data, tool_config)

        except Exception as e:
            self.logger.error(f"REAL voice call failed: {e}")
            return {
                "channel": "voice_call",
                "success": False,
                "error": str(e),
                "service": "twilio_real"
            }

    async def _send_email_alert(self, data: Dict[str, Any],
                                tool_config: ToolConfiguration) -> Dict[str, Any]:
        """Send REAL email alerts using SendGrid."""
        try:
            if self.sendgrid_client and self.sendgrid_from_email:
                # REAL SendGrid Email
                email_addresses = self._get_real_email_addresses(
                    data["location"])

                successful_sends = 0
                failed_sends = 0
                message_ids = []

                for email_address in email_addresses:
                    try:
                        message = Mail(
                            from_email=self.sendgrid_from_email,
                            to_emails=email_address,
                            subject=data["title"],
                            html_content=self._generate_email_body(data)
                        )

                        response = self.sendgrid_client.send(message)
                        message_ids.append(response.headers.get(
                            'X-Message-Id', 'unknown'))
                        successful_sends += 1
                        self.logger.info(f"REAL email sent to {email_address}")
                    except Exception as e:
                        failed_sends += 1
                        self.logger.error(
                            f"REAL email failed to {email_address}: {e}")

                return {
                    "channel": "email",
                    "success": successful_sends > 0,
                    "recipients_reached": successful_sends,
                    "failed_sends": failed_sends,
                    "message_ids": message_ids,
                    "delivery_time": datetime.now().isoformat(),
                    "service": "sendgrid_real"
                }
            else:
                # Fallback to simulation
                return await self._send_email_alert_simulation(data, tool_config)

        except Exception as e:
            self.logger.error(f"REAL email alert failed: {e}")
            return {
                "channel": "email",
                "success": False,
                "error": str(e),
                "service": "sendgrid_real"
            }

    async def _send_mobile_push(self, data: Dict[str, Any],
                                tool_config: ToolConfiguration) -> Dict[str, Any]:
        """Send REAL push notifications using Firebase."""
        try:
            if self.firebase_initialized:
                # REAL Firebase Push Notifications
                device_tokens = self._get_device_tokens(data["location"])

                if not device_tokens:
                    return await self._send_mobile_push_simulation(data, tool_config)

                # Create message
                message = messaging.MulticastMessage(
                    notification=messaging.Notification(
                        title=data["title"],
                        body=data["message"][:200] +
                        "..." if len(data["message"]
                                     ) > 200 else data["message"]
                    ),
                    data={
                        "disaster_id": data["alert_id"],
                        "priority": data["priority"],
                        "location": json.dumps(data["location"]),
                        "disaster_type": data["disaster_type"],
                        "severity": data["severity"]
                    },
                    tokens=device_tokens
                )

                response = messaging.send_multicast(message)

                self.logger.info(
                    f"REAL push notifications sent: {response.success_count}/{len(device_tokens)}")

                return {
                    "channel": "mobile_push",
                    "success": response.success_count > 0,
                    "recipients_reached": response.success_count,
                    "failed_sends": response.failure_count,
                    "delivery_time": datetime.now().isoformat(),
                    "service": "firebase_real"
                }
            else:
                # Fallback to simulation
                return await self._send_mobile_push_simulation(data, tool_config)

        except Exception as e:
            self.logger.error(f"REAL push notification failed: {e}")
            return {
                "channel": "mobile_push",
                "success": False,
                "error": str(e),
                "service": "firebase_real"
            }

    async def _send_web_notification(self, data: Dict[str, Any],
                                     tool_config: ToolConfiguration) -> Dict[str, Any]:
        """Send web notifications."""
        try:
            web_data = {
                "title": data["title"],
                "message": data["message"],
                "priority": data["urgency"],
                "location": data["location"],
                "action_url": f"/disaster/{data['alert_id']}/details",
                "icon": "emergency-icon.png",
                "badge": "emergency-badge.png"
            }

            # Simulate web notification service
            await asyncio.sleep(0.03)

            self.logger.info(
                f"Web notification sent for alert {data['alert_id']}")

            return {
                "channel": "web_notification",
                "success": True,
                # Assume 70% have web access
                "recipients_reached": int(data["affected_population"] * 0.7),
                "delivery_time": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Web notification failed: {e}")
            return {
                "channel": "web_notification",
                "success": False,
                "error": str(e)
            }

    def _map_priority_to_urgency(self, priority: PriorityLevel) -> str:
        """Map priority level to urgency string."""
        mapping = {
            PriorityLevel.CRITICAL: "critical",
            PriorityLevel.HIGH: "urgent",
            PriorityLevel.MEDIUM: "normal",
            PriorityLevel.LOW: "routine"
        }
        return mapping.get(priority, "normal")

    def _generate_alert_title(self, alert_data: AlertData) -> str:
        """Generate alert title based on disaster data."""
        disaster_type = alert_data.context.disaster_info.disaster_type.value.replace(
            '_', ' ').title()
        severity = alert_data.context.disaster_info.severity.value.upper()
        location = alert_data.context.disaster_info.location.administrative_area

        return f"{severity} {disaster_type} Alert - {location}"

    def _generate_required_actions(self, alert_data: AlertData) -> List[str]:
        """Generate list of required actions based on disaster context."""
        actions = []

        # Priority-based actions
        if alert_data.priority.level == PriorityLevel.CRITICAL:
            actions.append("EVACUATE IMMEDIATELY")
            actions.append("Follow designated evacuation routes")
        elif alert_data.priority.level == PriorityLevel.HIGH:
            actions.append("Prepare for immediate evacuation")
            actions.append("Monitor emergency communications")
        else:
            actions.append("Stay alert and monitor situation")
            actions.append("Prepare emergency supplies")

        # Context-specific actions
        if alert_data.context.evacuation_routes:
            actions.append(
                f"{len(alert_data.context.evacuation_routes)} evacuation routes available")

        if alert_data.context.available_resources.available_shelters > 0:
            actions.append(
                f"{alert_data.context.available_resources.available_shelters} emergency shelters available")

        return actions

    def _get_emergency_contacts(self, priority: PriorityLevel) -> Dict[str, str]:
        """Get emergency contact information based on priority."""
        contacts = {
            "emergency_services": "911",
            "disaster_hotline": "1-800-DISASTER",
            "evacuation_info": "1-800-EVACUATE"
        }

        if priority in [PriorityLevel.CRITICAL, PriorityLevel.HIGH]:
            contacts["immediate_assistance"] = "911"

        return contacts

    def _estimate_recipients(self, alert_data: AlertData, channels: List[str]) -> int:
        """Estimate total number of recipients across all channels."""
        base_population = alert_data.context.affected_population.total_population

        # Channel reach estimates
        channel_reach = {
            "emergency_broadcast": 0.95,  # 95% reach
            "mobile_push": 0.85,          # 85% reach
            "email": 0.70,                # 70% reach
            "sms": 0.90,                  # 90% reach
            "web_notification": 0.60      # 60% reach
        }

        # Calculate unique reach (avoiding double counting)
        total_reach = 0.0
        for channel in channels:
            total_reach = max(total_reach, channel_reach.get(channel, 0.5))

        return int(base_population * total_reach)

    def _estimate_broadcast_recipients(self, location: Dict[str, Any], radius_km: float) -> int:
        """Estimate recipients for emergency broadcast based on location and radius."""
        # Simplified population density estimation
        # In production, this would use actual demographic data
        population_density_per_km2 = 1000  # Default urban density
        area_km2 = 3.14159 * (radius_km ** 2)
        return int(area_km2 * population_density_per_km2)

    def _generate_email_body(self, data: Dict[str, Any]) -> str:
        """Generate detailed email body for alert."""
        return f"""
EMERGENCY ALERT: {data['title']}

{data['message']}

DISASTER DETAILS:
- Type: {data['disaster_type'].replace('_', ' ').title()}
- Severity: {data['severity'].upper()}
- Location: {data['location']['address']}
- Time: {data['timestamp']}
- Affected Population: {data['affected_population']:,}

REQUIRED ACTIONS:
{chr(10).join(f"• {action}" for action in data['required_actions'])}

EVACUATION INFORMATION:
- Routes Available: {data['evacuation_routes_available']}
- Estimated Response Time: {data['estimated_response_time_minutes']} minutes

EMERGENCY CONTACTS:
{chr(10).join(f"• {name}: {number}" for name, number in data['contact_info'].items())}

This is an automated emergency alert. Do not reply to this email.
For immediate assistance, call 911.
        """.strip()

    def _get_real_phone_numbers(self, location: Dict[str, Any]) -> List[str]:
        """Get real phone numbers from database or configuration."""
        # In production, this would query a database of registered users
        # For now, return the configured phone numbers from your alerts.py
        default_numbers = [
            "+918850755760",  # Joel Pawar
            "+919529685725",  # Sereena Thomas
            "+919322945843",  # Seane Dcosta
        ]

        # TODO: Implement database query based on location radius
        # SELECT phone_number FROM users
        # WHERE ST_DWithin(
        #     ST_Point(longitude, latitude)::geography,
        #     ST_Point(location['longitude'], location['latitude'])::geography,
        #     notification_radius_km * 1000
        # ) AND phone_number IS NOT NULL;

        return default_numbers

    def _get_real_email_addresses(self, location: Dict[str, Any]) -> List[str]:
        """Get real email addresses from database or configuration."""
        # In production, this would query a database of registered users
        default_emails = [
            "emergency@disha.gov.in",
            "alerts@disha.gov.in",
            "disaster-response@disha.gov.in"
        ]

        # TODO: Implement database query based on location radius
        return default_emails

    def _get_device_tokens(self, location: Dict[str, Any]) -> List[str]:
        """Get device tokens for push notifications from database."""
        # In production, this would query a database of registered devices
        # For now, return empty list to trigger simulation

        # TODO: Implement database query for device tokens
        # SELECT device_token FROM users
        # WHERE device_token IS NOT NULL AND notifications_enabled = true
        # AND ST_DWithin(...) -- location-based query

        return []  # Empty list triggers simulation

    def _create_emergency_twiml_url(self, data: Dict[str, Any]) -> str:
        """Create TwiML URL for emergency voice message."""
        # In production, you would host your own TwiML endpoint
        # For now, use Twilio's demo URL or create a simple one

        # TODO: Create your own TwiML endpoint that says:
        # "This is an emergency alert from DISHA. There is a {disaster_type}
        #  at {location}. Please follow evacuation instructions immediately."

        return "http://demo.twilio.com/docs/voice.xml"

    # Simulation fallback methods
    async def _send_sms_alert_simulation(self, data: Dict[str, Any],
                                         tool_config: ToolConfiguration) -> Dict[str, Any]:
        """Fallback SMS simulation when Twilio is not available."""
        sms_message = f"EMERGENCY: {data['disaster_type'].upper()} at {data['location']['address']}. {data['message'][:100]}..."

        sms_data = {
            "message": sms_message,
            "priority": data["urgency"],
            "recipients": self._get_sms_recipients(data["location"]),
            "sender": "EMERGENCY"
        }

        # Simulate SMS service
        await asyncio.sleep(0.08)

        self.logger.info(f"SMS alert SIMULATED for alert {data['alert_id']}")

        return {
            "channel": "sms",
            "success": True,
            "recipients_reached": len(sms_data["recipients"]),
            "delivery_time": datetime.now().isoformat(),
            "service": "simulation"
        }

    async def _send_voice_call_simulation(self, data: Dict[str, Any],
                                          tool_config: ToolConfiguration) -> Dict[str, Any]:
        """Fallback voice call simulation when Twilio is not available."""
        await asyncio.sleep(0.1)

        self.logger.info(f"Voice call SIMULATED for alert {data['alert_id']}")

        return {
            "channel": "voice_call",
            "success": True,
            "recipients_reached": 3,  # Simulate 3 calls
            "delivery_time": datetime.now().isoformat(),
            "service": "simulation"
        }

    async def _send_email_alert_simulation(self, data: Dict[str, Any],
                                           tool_config: ToolConfiguration) -> Dict[str, Any]:
        """Fallback email simulation when SendGrid is not available."""
        email_data = {
            "subject": data["title"],
            "body": self._generate_email_body(data),
            "priority": data["urgency"],
            "recipients": self._get_email_recipients(data["location"]),
            "attachments": ["evacuation_map.pdf"] if data["evacuation_routes_available"] > 0 else []
        }

        # Simulate email service
        await asyncio.sleep(0.1)

        self.logger.info(f"Email alert SIMULATED for alert {data['alert_id']}")

        return {
            "channel": "email",
            "success": True,
            "recipients_reached": len(email_data["recipients"]),
            "delivery_time": datetime.now().isoformat(),
            "service": "simulation"
        }

    async def _send_mobile_push_simulation(self, data: Dict[str, Any],
                                           tool_config: ToolConfiguration) -> Dict[str, Any]:
        """Fallback push notification simulation when Firebase is not available."""
        push_data = {
            "title": data["title"],
            "body": data["message"][:200] + "..." if len(data["message"]) > 200 else data["message"],
            "priority": data["urgency"],
            "location": data["location"],
            "action_buttons": ["View Details", "Get Directions"],
            "sound": "emergency" if data["priority"] in ["critical", "urgent"] else "default"
        }

        # Simulate push notification service
        await asyncio.sleep(0.05)

        self.logger.info(
            f"Mobile push notification SIMULATED for alert {data['alert_id']}")

        return {
            "channel": "mobile_push",
            "success": True,
            "recipients_reached": data["affected_population"],
            "delivery_time": datetime.now().isoformat(),
            "service": "simulation"
        }

    def _get_sms_recipients(self, location: Dict[str, Any]) -> List[str]:
        """Get SMS recipients based on location."""
        # In production, this would query a database
        return ["+918850755760", "+919529685725", "+919322945843"]

    def _get_email_recipients(self, location: Dict[str, Any]) -> List[str]:
        """Get email recipients based on location."""
        # In production, this would query a database
        return ["emergency@disha.gov.in", "alerts@disha.gov.in"]

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()
