"""
MCP News Tool for disaster-related news and information using Groq AI.
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


# Import Groq client
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False


class NewsMCPTool(MCPTool):
    """
    MCP News Tool for fetching disaster-related news and information.

    Uses Groq AI to:
    - Get current natural disaster news
    - Generate disaster-specific information
    - Provide context-aware updates
    - Create emergency bulletins
    """

    def __init__(self, config: MCPToolConfig):
        super().__init__(config)
        self.client = httpx.AsyncClient(timeout=30.0)

        # Initialize Groq client
        self._init_groq_client()

        self.news_operations = {
            "current_disasters": self._get_current_disasters,
            "disaster_context": self._get_disaster_context,
            "emergency_bulletin": self._generate_emergency_bulletin,
            "safety_instructions": self._generate_safety_instructions,
            "evacuation_guidance": self._generate_evacuation_guidance
        }

    def _init_groq_client(self):
        """Initialize Groq client if API key is available."""
        self.logger.info(
            f"Initializing Groq client... GROQ_AVAILABLE={GROQ_AVAILABLE}")

        if GROQ_AVAILABLE:
            api_key = os.getenv('GROQ_API_KEY') or os.getenv('GROQ')

            self.logger.info(
                f"Groq API key check: {'***' + api_key[-4:] if api_key else 'None'}")

            if api_key:
                self.groq_client = Groq(api_key=api_key)
                self.logger.info("✅ Groq client initialized successfully")
            else:
                self.groq_client = None
                self.logger.warning(
                    "❌ Groq API key not found, using simulation")
        else:
            self.groq_client = None
            self.logger.warning(
                "❌ Groq library not installed, using simulation")

    def _clean_groq_json_response(self, content: str) -> str:
        """Clean Groq API response content to extract valid JSON."""
        # Remove markdown code blocks
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        return content.strip()

    async def execute(self, alert_data: AlertData, tool_config: ToolConfiguration) -> ExecutionResult:
        """Execute news operations for disaster context."""
        start_time = datetime.now()

        try:
            self.logger.info(
                f"Executing news tool for disaster {alert_data.alert_id}")

            # Validate configuration
            if not self.validate_configuration(tool_config):
                raise MCPToolError(
                    f"Invalid configuration for news tool {self.config.tool_name}")

            # Get requested operations from configuration
            operations = tool_config.parameters.get(
                "operations", ["current_disasters"])

            # Execute all requested operations
            results = {}
            successful_operations = 0
            failed_operations = 0

            for operation in operations:
                try:
                    if operation in self.news_operations:
                        result = await self.news_operations[operation](alert_data, tool_config)
                        results[operation] = result

                        if result.get("success", False):
                            successful_operations += 1
                        else:
                            failed_operations += 1
                    else:
                        self.logger.warning(
                            f"Unknown news operation: {operation}")
                        failed_operations += 1

                except Exception as e:
                    self.logger.error(
                        f"News operation {operation} failed: {e}")
                    results[operation] = {
                        "success": False,
                        "error": str(e)
                    }
                    failed_operations += 1

            # Calculate execution time
            execution_time = int(
                (datetime.now() - start_time).total_seconds() * 1000)

            # Determine overall success
            overall_success = successful_operations > 0
            status = ExecutionStatus.SUCCESS if overall_success else ExecutionStatus.FAILURE

            # Create response data
            response_data = {
                "alert_id": alert_data.alert_id,
                "operations_attempted": len(operations),
                "successful_operations": successful_operations,
                "failed_operations": failed_operations,
                "results": results,
                "timestamp": datetime.now().isoformat(),
                "groq_service_used": self.groq_client is not None
            }

            self.logger.info(
                f"News tool completed: {successful_operations}/{len(operations)} operations successful"
            )

            return ExecutionResult(
                status=status,
                tool_name=self.config.tool_name,
                execution_time_ms=execution_time,
                response_data=response_data,
                error_message=None if overall_success else f"Failed operations: {failed_operations}"
            )

        except Exception as e:
            execution_time = int(
                (datetime.now() - start_time).total_seconds() * 1000)
            self.logger.error(f"News tool execution failed: {e}")

            return ExecutionResult(
                status=ExecutionStatus.FAILURE,
                tool_name=self.config.tool_name,
                execution_time_ms=execution_time,
                response_data=None,
                error_message=str(e)
            )

    async def _get_current_disasters(self, alert_data: AlertData, tool_config: ToolConfiguration) -> Dict[str, Any]:
        """Get current natural disasters worldwide and location-specific news using Groq AI."""
        try:
            if self.groq_client:
                # Get location information
                location = alert_data.context.disaster_info.location
                disaster_type = alert_data.context.disaster_info.disaster_type.value
                severity = alert_data.context.disaster_info.severity.value

                prompt = f"""
You are a professional disaster news aggregator and local emergency information specialist.

TASK 1: Provide current global natural disasters
TASK 2: Generate location-specific emergency information for this specific incident:

INCIDENT DETAILS:
- Type: {disaster_type}
- Location: {location.address} (Lat: {location.latitude:.4f}, Lon: {location.longitude:.4f})
- Severity: {severity}
- Administrative Area: {location.administrative_area}

Return ONLY valid JSON in this exact format:

{{
  "global_disasters": {{
    "as_of": "YYYY-MM-DD",
    "total_disasters": number,
    "disasters": [
      {{
        "headline": "Clear and concise headline",
        "type": "Flood / Earthquake / Cyclone / Wildfire / etc.",
        "locations": ["Country", "Region"],
        "summary": "Brief impact summary including deaths, affected people, damage",
        "source": "Main sources",
        "date": "Start or key date"
      }}
    ]
  }},
  "location_specific": {{
    "incident_headline": "Specific headline for this {disaster_type} at {location.address}",
    "local_context": "Brief context about this specific location and disaster type",
    "immediate_concerns": ["concern1", "concern2", "concern3"],
    "local_resources": ["resource1", "resource2"],
    "weather_impact": "Current weather conditions affecting the situation",
    "transportation": "Local transportation status and alternatives",
    "community_impact": "Expected impact on local community and infrastructure",
    "historical_reference": "Any relevant historical context for this area"
  }}
}}
"""

                completion = self.groq_client.chat.completions.create(
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a precise JSON generator and emergency information specialist. Always respond with only valid JSON and nothing else. Focus on accurate, helpful information for emergency response."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    model="llama-3.3-70b-versatile",
                    temperature=0.3,
                    max_tokens=1500,
                    top_p=0.9
                )

                content = completion.choices[0].message.content.strip()

                # Log the raw response for debugging
                self.logger.info(
                    f"Groq API raw response length: {len(content)}")
                self.logger.info(
                    f"Groq API raw response preview: {content[:200]}...")

                # Clean the response using helper function
                content = self._clean_groq_json_response(content)

                # Check if content is empty
                if not content:
                    self.logger.error("Groq API returned empty content")
                    return {
                        "success": False,
                        "error": "Empty response from Groq API",
                        "service": "groq_real"
                    }

                news_data = json.loads(content)

                return {
                    "success": True,
                    "operation": "current_disasters",
                    "data": news_data,
                    "service": "groq_real",
                    "location_specific": True
                }

            else:
                # Fallback simulation
                return await self._get_current_disasters_simulation()

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error in current disasters: {e}")
            self.logger.error(
                f"Raw content that failed to parse: '{content if 'content' in locals() else 'No content'}'")
            return {
                "success": False,
                "error": "Invalid JSON from AI model",
                "raw_response": content if 'content' in locals() else "No response",
                "service": "groq_real"
            }
        except Exception as e:
            self.logger.error(f"Current disasters fetch failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "service": "groq_real"
            }

    async def _get_disaster_context(self, alert_data: AlertData, tool_config: ToolConfiguration) -> Dict[str, Any]:
        """Generate disaster-specific context using Groq AI."""
        try:
            if self.groq_client:
                disaster_info = alert_data.context.disaster_info

                prompt = f"""
You are a disaster response expert. Provide detailed context and analysis for this disaster:

Disaster Type: {disaster_info.disaster_type.value}
Location: {disaster_info.location.address}
Severity: {disaster_info.severity.value}
Affected Population: {alert_data.context.affected_population.total_population}

Provide a comprehensive analysis including:
1. Typical impacts of this disaster type
2. Immediate risks and concerns
3. Historical context for this region
4. Expected duration and progression
5. Key response priorities

Return ONLY valid JSON:
{{
  "disaster_analysis": {{
    "typical_impacts": ["impact1", "impact2"],
    "immediate_risks": ["risk1", "risk2"],
    "historical_context": "Brief historical context",
    "expected_duration": "Duration estimate",
    "response_priorities": ["priority1", "priority2"]
  }}
}}
"""

                completion = self.groq_client.chat.completions.create(
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a disaster response expert. Provide only valid JSON responses."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    model="llama-3.3-70b-versatile",
                    temperature=0.3,
                    max_tokens=800,
                    top_p=0.9
                )

                content = completion.choices[0].message.content.strip()

                # Log the raw response for debugging
                self.logger.info(
                    f"Groq API disaster context response length: {len(content)}")

                # Clean content using helper function
                content = self._clean_groq_json_response(content)

                # Check if content is empty
                if not content:
                    self.logger.error(
                        "Groq API returned empty content for disaster context")
                    return {
                        "success": False,
                        "error": "Empty response from Groq API",
                        "service": "groq_real"
                    }

                context_data = json.loads(content)

                return {
                    "success": True,
                    "operation": "disaster_context",
                    "data": context_data,
                    "service": "groq_real"
                }

            else:
                return await self._get_disaster_context_simulation(alert_data)

        except Exception as e:
            self.logger.error(f"Disaster context generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "service": "groq_real"
            }

    async def _generate_emergency_bulletin(self, alert_data: AlertData, tool_config: ToolConfiguration) -> Dict[str, Any]:
        """Generate emergency bulletin using Groq AI."""
        try:
            if self.groq_client:
                disaster_info = alert_data.context.disaster_info

                prompt = f"""
Create an official emergency bulletin for this disaster:

Disaster: {disaster_info.disaster_type.value}
Location: {disaster_info.location.address}
Severity: {disaster_info.severity.value}
Time: {disaster_info.timestamp}
Affected Population: {alert_data.context.affected_population.total_population}

Create a professional emergency bulletin with:
1. Clear headline
2. Situation summary
3. Immediate actions required
4. Safety instructions
5. Contact information

Format as official government bulletin. Return ONLY valid JSON:
{{
  "bulletin": {{
    "headline": "Official headline",
    "situation_summary": "Current situation",
    "immediate_actions": ["action1", "action2"],
    "safety_instructions": ["instruction1", "instruction2"],
    "contact_info": "Emergency contact information",
    "issued_by": "DISHA - Government of India",
    "issued_at": "{datetime.now().isoformat()}"
  }}
}}
"""

                completion = self.groq_client.chat.completions.create(
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an official emergency communications specialist. Create professional, clear emergency bulletins."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    model="llama-3.3-70b-versatile",
                    temperature=0.2,
                    max_tokens=600,
                    top_p=0.8
                )

                content = completion.choices[0].message.content.strip()

                # Clean content using helper function
                content = self._clean_groq_json_response(content)

                bulletin_data = json.loads(content)

                return {
                    "success": True,
                    "operation": "emergency_bulletin",
                    "data": bulletin_data,
                    "service": "groq_real"
                }

            else:
                return await self._generate_emergency_bulletin_simulation(alert_data)

        except Exception as e:
            self.logger.error(f"Emergency bulletin generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "service": "groq_real"
            }

    async def _generate_safety_instructions(self, alert_data: AlertData, tool_config: ToolConfiguration) -> Dict[str, Any]:
        """Generate safety instructions using Groq AI."""
        try:
            if self.groq_client:
                disaster_info = alert_data.context.disaster_info

                prompt = f"""
Create detailed safety instructions for this disaster:

Disaster: {disaster_info.disaster_type.value}
Location: {disaster_info.location.address}
Severity: {disaster_info.severity.value}

Provide specific, actionable safety instructions for:
1. Immediate actions to take
2. What to avoid
3. Emergency supplies needed
4. Communication protocols
5. Evacuation procedures if needed

Return ONLY valid JSON:
{{
  "safety_instructions": {{
    "immediate_actions": ["action1", "action2"],
    "avoid_these": ["danger1", "danger2"],
    "emergency_supplies": ["item1", "item2"],
    "communication": "How to stay informed",
    "evacuation": "Evacuation guidance if applicable"
  }}
}}
"""

                completion = self.groq_client.chat.completions.create(
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a disaster safety expert. Provide only valid JSON responses."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    model="llama-3.3-70b-versatile",
                    temperature=0.2,
                    max_tokens=600,
                    top_p=0.8
                )

                content = completion.choices[0].message.content.strip()

                # Clean content using helper function
                content = self._clean_groq_json_response(content)

                safety_data = json.loads(content)

                return {
                    "success": True,
                    "operation": "safety_instructions",
                    "data": safety_data,
                    "service": "groq_real"
                }

            else:
                return await self._generate_safety_instructions_simulation(alert_data)

        except Exception as e:
            self.logger.error(f"Safety instructions generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "service": "groq_real"
            }

    async def _generate_evacuation_guidance(self, alert_data: AlertData, tool_config: ToolConfiguration) -> Dict[str, Any]:
        """Generate evacuation guidance using Groq AI."""
        try:
            if self.groq_client:
                disaster_info = alert_data.context.disaster_info

                prompt = f"""
Create evacuation guidance for this disaster:

Disaster: {disaster_info.disaster_type.value}
Location: {disaster_info.location.address}
Severity: {disaster_info.severity.value}
Available Routes: {len(alert_data.context.evacuation_routes)}

Provide specific evacuation guidance including:
1. When to evacuate
2. What to take
3. Transportation options
4. Safe destinations
5. Special considerations

Return ONLY valid JSON:
{{
  "evacuation_guidance": {{
    "when_to_evacuate": "Timing guidance",
    "what_to_take": ["item1", "item2"],
    "transportation": ["option1", "option2"],
    "safe_destinations": ["location1", "location2"],
    "special_considerations": ["consideration1", "consideration2"]
  }}
}}
"""

                completion = self.groq_client.chat.completions.create(
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an evacuation planning expert. Provide only valid JSON responses."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    model="llama-3.3-70b-versatile",
                    temperature=0.2,
                    max_tokens=600,
                    top_p=0.8
                )

                content = completion.choices[0].message.content.strip()

                # Clean content using helper function
                content = self._clean_groq_json_response(content)

                evacuation_data = json.loads(content)

                return {
                    "success": True,
                    "operation": "evacuation_guidance",
                    "data": evacuation_data,
                    "service": "groq_real"
                }

            else:
                return await self._generate_evacuation_guidance_simulation(alert_data)

        except Exception as e:
            self.logger.error(f"Evacuation guidance generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "service": "groq_real"
            }

    async def _generate_safety_instructions_simulation(self, alert_data: AlertData) -> Dict[str, Any]:
        """Simulation fallback for safety instructions."""
        await asyncio.sleep(0.1)

        disaster_info = alert_data.context.disaster_info

        return {
            "success": True,
            "operation": "safety_instructions",
            "data": {
                "safety_instructions": {
                    "immediate_actions": ["Stay calm", "Follow official instructions", "Check on neighbors"],
                    "avoid_these": ["Panic", "Spreading rumors", "Ignoring evacuation orders"],
                    "emergency_supplies": ["Water", "Food", "First aid kit", "Flashlight", "Radio"],
                    "communication": "Monitor emergency broadcasts and official social media channels",
                    "evacuation": f"Follow designated evacuation routes if ordered for {disaster_info.disaster_type.value}"
                }
            },
            "service": "simulation"
        }

    async def _generate_evacuation_guidance_simulation(self, alert_data: AlertData) -> Dict[str, Any]:
        """Simulation fallback for evacuation guidance."""
        await asyncio.sleep(0.1)

        return {
            "success": True,
            "operation": "evacuation_guidance",
            "data": {
                "evacuation_guidance": {
                    "when_to_evacuate": "When ordered by authorities or if immediate danger is present",
                    "what_to_take": ["Important documents", "Medications", "Emergency supplies", "Phone charger"],
                    "transportation": ["Personal vehicle", "Public transport", "Emergency transport"],
                    "safe_destinations": ["Designated shelters", "Friends/family outside affected area"],
                    "special_considerations": ["Assist elderly neighbors", "Secure pets", "Turn off utilities"]
                }
            },
            "service": "simulation"
        }

    async def _get_current_disasters_simulation(self) -> Dict[str, Any]:
        """Simulation fallback for current disasters."""
        await asyncio.sleep(0.1)

        return {
            "success": True,
            "operation": "current_disasters",
            "data": {
                "global_disasters": {
                    "as_of": datetime.now().strftime("%Y-%m-%d"),
                    "total_disasters": 2,
                    "disasters": [
                        {
                            "headline": "Simulated Earthquake in Pacific Region",
                            "type": "Earthquake",
                            "locations": ["Pacific Ocean", "Ring of Fire"],
                            "summary": "Magnitude 6.5 earthquake, no major damage reported",
                            "source": "USGS, Local Authorities",
                            "date": datetime.now().strftime("%Y-%m-%d")
                        },
                        {
                            "headline": "Simulated Wildfire in California",
                            "type": "Wildfire",
                            "locations": ["California", "USA"],
                            "summary": "Active wildfire, 1000 acres affected, evacuations ongoing",
                            "source": "CAL FIRE, Reuters",
                            "date": datetime.now().strftime("%Y-%m-%d")
                        }
                    ]
                },
                "location_specific": {
                    "incident_headline": "Simulated Emergency Incident",
                    "local_context": "Simulated local emergency context",
                    "immediate_concerns": ["Safety", "Evacuation", "Communication"],
                    "local_resources": ["Emergency services", "Local shelters"],
                    "weather_impact": "Weather conditions being monitored",
                    "transportation": "Transportation alternatives available",
                    "community_impact": "Community response coordinated",
                    "historical_reference": "Similar events handled successfully"
                }
            },
            "service": "simulation"
        }

    async def _get_disaster_context_simulation(self, alert_data: AlertData) -> Dict[str, Any]:
        """Simulation fallback for disaster context."""
        await asyncio.sleep(0.1)

        return {
            "success": True,
            "operation": "disaster_context",
            "data": {
                "disaster_analysis": {
                    "typical_impacts": ["Property damage", "Infrastructure disruption", "Population displacement"],
                    "immediate_risks": ["Secondary hazards", "Communication breakdown", "Resource shortages"],
                    "historical_context": "This region has experienced similar events in the past",
                    "expected_duration": "24-72 hours for immediate response phase",
                    "response_priorities": ["Life safety", "Evacuation", "Emergency services coordination"]
                }
            },
            "service": "simulation"
        }

    async def _generate_emergency_bulletin_simulation(self, alert_data: AlertData) -> Dict[str, Any]:
        """Simulation fallback for emergency bulletin."""
        await asyncio.sleep(0.1)

        disaster_info = alert_data.context.disaster_info

        return {
            "success": True,
            "operation": "emergency_bulletin",
            "data": {
                "bulletin": {
                    "headline": f"EMERGENCY: {disaster_info.disaster_type.value.upper()} Alert - {disaster_info.location.administrative_area}",
                    "situation_summary": f"A {disaster_info.severity.value} {disaster_info.disaster_type.value} has been reported in {disaster_info.location.address}",
                    "immediate_actions": ["Follow evacuation orders", "Stay informed", "Avoid affected areas"],
                    "safety_instructions": ["Stay calm", "Follow official guidance", "Keep emergency supplies ready"],
                    "contact_info": "Emergency Services: 911 | Disaster Hotline: 1-800-DISASTER",
                    "issued_by": "DISHA - Government of India",
                    "issued_at": datetime.now().isoformat()
                }
            },
            "service": "simulation"
        }

    def format_data(self, alert_data: AlertData, priority: PriorityLevel) -> Dict[str, Any]:
        """Format alert data for news operations."""
        return {
            "alert_id": alert_data.alert_id,
            "priority": priority.value,
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
            "message": alert_data.message
        }

    def validate_configuration(self, tool_config: ToolConfiguration) -> bool:
        """Validate tool configuration."""
        required_params = ["operations"]

        for param in required_params:
            if param not in tool_config.parameters:
                self.logger.error(f"Missing required parameter: {param}")
                return False

        # Validate operations
        operations = tool_config.parameters.get("operations", [])
        if not isinstance(operations, list) or not operations:
            self.logger.error("Invalid or empty operations configuration")
            return False

        # Validate each operation is supported
        for operation in operations:
            if operation not in self.news_operations:
                self.logger.error(f"Unsupported news operation: {operation}")
                return False

        return True

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()
