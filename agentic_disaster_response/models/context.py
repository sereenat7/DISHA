"""
Context building models and data structures.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from .disaster_data import DisasterData
from .location import Location


@dataclass
class EvacuationRoute:
    """Represents an evacuation route from existing system."""
    route_id: str
    start_location: Location
    end_location: Location
    distance_km: float
    estimated_time_minutes: int
    capacity: int
    current_load: int
    route_geometry: List[Location]
    safe_location_name: str
    safe_location_category: str  # hospitals, bunkers_shelters, underground_parking


@dataclass
class PopulationData:
    """Population data for affected areas."""
    total_population: int
    vulnerable_population: int  # elderly, disabled, children
    current_occupancy: Optional[int] = None  # actual people present
    population_density_per_km2: Optional[float] = None


@dataclass
class ResourceInventory:
    """Available resources for disaster response."""
    available_shelters: int
    shelter_capacity: int
    medical_facilities: int
    emergency_vehicles: int
    communication_systems: int
    backup_power_systems: int


@dataclass
class RiskMetrics:
    """Risk assessment metrics for the disaster."""
    overall_risk_score: float  # 0.0 - 1.0
    evacuation_difficulty: float  # 0.0 - 1.0
    time_criticality: float  # 0.0 - 1.0
    resource_availability: float  # 0.0 - 1.0
    weather_impact: Optional[float] = None
    traffic_congestion: Optional[float] = None


@dataclass
class GeographicalContext:
    """Geographical context information."""
    affected_areas: List[Location]
    safe_locations: List[Location]
    blocked_routes: List[str] = field(default_factory=list)
    accessible_routes: List[str] = field(default_factory=list)
    terrain_difficulty: Optional[float] = None
    weather_conditions: Optional[Dict[str, Any]] = None


@dataclass
class StructuredContext:
    """Structured context data for decision-making."""
    disaster_info: DisasterData
    geographical_context: GeographicalContext
    evacuation_routes: List[EvacuationRoute]
    affected_population: PopulationData
    available_resources: ResourceInventory
    risk_assessment: RiskMetrics
    context_completeness: float  # 0.0 - 1.0, indicates how complete the context is
    missing_data_indicators: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate context completeness score."""
        if not 0.0 <= self.context_completeness <= 1.0:
            raise ValueError(
                f"Context completeness must be between 0.0 and 1.0, got {self.context_completeness}")


@dataclass
class EnrichedContext:
    """Context enriched with additional analysis."""
    base_context: StructuredContext
    priority_factors: Dict[str, float]
    recommended_actions: List[str]
    alternative_scenarios: List[Dict[str, Any]] = field(default_factory=list)
    confidence_metrics: Dict[str, float] = field(default_factory=dict)
