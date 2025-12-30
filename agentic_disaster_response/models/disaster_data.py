"""
Core disaster data models and enums.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional
from .location import Location


class DisasterType(Enum):
    """Types of disasters supported by the system."""
    FIRE = "fire"
    FLOOD = "flood"
    EARTHQUAKE = "earthquake"
    EXPLOSION = "explosion"
    CHEMICAL_SPILL = "chemical_spill"
    TORNADO = "tornado"
    VOLCANIC = "volcanic"
    ELECTRICAL = "electrical"
    BUILDING_COLLAPSE = "building_collapse"
    TERRORIST_ATTACK = "terrorist_attack"


class SeverityLevel(Enum):
    """Severity levels for disasters."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ProcessingStatus(Enum):
    """Status of disaster processing workflow."""
    PENDING = "pending"
    CONTEXT_BUILDING = "context_building"
    PRIORITY_ANALYSIS = "priority_analysis"
    ALERT_DISPATCH = "alert_dispatch"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class GeographicalArea:
    """Represents a geographical area affected by disaster."""
    center: Location
    radius_km: float
    polygon_coordinates: Optional[List[Location]] = None
    area_name: Optional[str] = None


@dataclass
class ImpactAssessment:
    """Assessment of disaster impact."""
    estimated_affected_population: int
    estimated_casualties: Optional[int] = None
    infrastructure_damage_level: SeverityLevel = SeverityLevel.MEDIUM
    economic_impact_estimate: Optional[float] = None
    environmental_impact: Optional[str] = None


@dataclass
class DisasterData:
    """Core disaster data structure."""
    disaster_id: str
    disaster_type: DisasterType
    location: Location
    severity: SeverityLevel
    timestamp: datetime
    affected_areas: List[GeographicalArea]
    estimated_impact: ImpactAssessment
    description: Optional[str] = None
    source: Optional[str] = None  # Manual trigger, sensor, API, etc.
    metadata: Optional[dict] = None
