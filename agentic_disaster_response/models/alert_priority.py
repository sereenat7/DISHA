"""
Alert priority models and enums.
"""

from dataclasses import dataclass
from datetime import timedelta
from enum import Enum
from typing import List, Optional


class PriorityLevel(Enum):
    """Priority levels for disaster alerts."""
    CRITICAL = "critical"  # Immediate life-threatening situations
    HIGH = "high"         # Serious situations requiring rapid response
    MEDIUM = "medium"     # Important situations requiring response within hours
    LOW = "low"          # Non-urgent situations for routine processing


class ResourceType(Enum):
    """Types of resources required for disaster response."""
    MEDICAL = "medical"
    FIRE_RESCUE = "fire_rescue"
    POLICE = "police"
    EVACUATION_TRANSPORT = "evacuation_transport"
    EMERGENCY_SHELTER = "emergency_shelter"
    COMMUNICATION = "communication"
    UTILITIES = "utilities"
    SEARCH_RESCUE = "search_rescue"


@dataclass
class AlertPriority:
    """Represents the priority level and details for a disaster alert."""
    level: PriorityLevel
    score: float  # Numerical score used for ranking (0.0 - 1.0)
    reasoning: str  # Human-readable explanation of priority assignment
    estimated_response_time: timedelta
    required_resources: List[ResourceType]
    # Confidence in priority assignment (0.0 - 1.0)
    confidence: Optional[float] = None

    def __post_init__(self):
        """Validate priority score and confidence."""
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(
                f"Priority score must be between 0.0 and 1.0, got {self.score}")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"Confidence must be between 0.0 and 1.0, got {self.confidence}")

    @classmethod
    def create_default_high_priority(cls, reasoning: str = "Priority determination failed") -> 'AlertPriority':
        """Create a default HIGH priority alert for fallback scenarios."""
        return cls(
            level=PriorityLevel.HIGH,
            score=0.75,
            reasoning=reasoning,
            estimated_response_time=timedelta(minutes=15),
            required_resources=[
                ResourceType.EMERGENCY_SHELTER, ResourceType.COMMUNICATION],
            confidence=0.5
        )
