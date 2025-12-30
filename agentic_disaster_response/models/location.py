"""
Location and coordinate models.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Coordinate:
    """Represents a coordinate point."""
    latitude: float
    longitude: float

    def __post_init__(self):
        """Validate coordinate ranges."""
        if not -90 <= self.latitude <= 90:
            raise ValueError(
                f"Latitude must be between -90 and 90, got {self.latitude}")
        if not -180 <= self.longitude <= 180:
            raise ValueError(
                f"Longitude must be between -180 and 180, got {self.longitude}")


@dataclass
class Location:
    """Represents a location with optional address information."""
    latitude: float
    longitude: float
    address: Optional[str] = None
    administrative_area: Optional[str] = None
    country: Optional[str] = None

    def __post_init__(self):
        """Validate coordinate ranges."""
        if not -90 <= self.latitude <= 90:
            raise ValueError(
                f"Latitude must be between -90 and 90, got {self.latitude}")
        if not -180 <= self.longitude <= 180:
            raise ValueError(
                f"Longitude must be between -180 and 180, got {self.longitude}")

    @property
    def coordinate(self) -> Coordinate:
        """Get coordinate representation of this location."""
        return Coordinate(self.latitude, self.longitude)

    def distance_to(self, other: 'Location') -> float:
        """Calculate haversine distance to another location in kilometers."""
        import math

        R = 6371  # Earth radius in kilometers
        dlat = math.radians(other.latitude - self.latitude)
        dlon = math.radians(other.longitude - self.longitude)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(self.latitude))
            * math.cos(math.radians(other.latitude))
            * math.sin(dlon / 2) ** 2
        )
        return 2 * R * math.asin(math.sqrt(a))
