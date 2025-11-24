"""State tracking for dog presence, location, and behavior over time."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DogState:
    """Track state for a single dog."""

    def __init__(self, dog_id: str):
        self.dog_id = dog_id
        self.last_seen = None
        self.last_location = None
        self.location_history = []
        self.behavior_history = []

    def update_location(self, location: str, timestamp: datetime):
        """Update dog's location."""
        self.last_seen = timestamp
        self.last_location = location
        self.location_history.append({
            "location": location,
            "timestamp": timestamp
        })
        logger.debug(f"{self.dog_id} location updated: {location}")

    def update_behavior(self, behavior: str, timestamp: datetime, confidence: int):
        """Record a behavior observation."""
        self.behavior_history.append({
            "behavior": behavior,
            "timestamp": timestamp,
            "confidence": confidence
        })

    def get_last_seen_in_location(self, location: str) -> Optional[datetime]:
        """Get when dog was last seen in a specific location."""
        for entry in reversed(self.location_history):
            if entry["location"] == location:
                return entry["timestamp"]
        return None

    def time_since_seen_in_location(self, location: str) -> Optional[float]:
        """Get minutes since last seen in location."""
        last_seen = self.get_last_seen_in_location(location)
        if last_seen:
            return (datetime.now() - last_seen).total_seconds() / 60
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "dog_id": self.dog_id,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "last_location": self.last_location,
            "location_history": [
                {
                    "location": entry["location"],
                    "timestamp": entry["timestamp"].isoformat()
                }
                for entry in self.location_history[-10:]  # Keep last 10
            ]
        }


class StateTracker:
    """Track global state across cameras and analyzers."""

    def __init__(self):
        self.dogs: Dict[str, DogState] = {}
        self.motion_history: Dict[str, List[datetime]] = defaultdict(list)
        self.alert_history: List[Dict[str, Any]] = []
        self.camera_locations: Dict[str, str] = {}

    def register_camera_location(self, camera_id: str, location: str):
        """Register what location a camera covers."""
        self.camera_locations[camera_id] = location
        logger.info(f"Camera {camera_id} registered for location: {location}")

    def get_or_create_dog(self, dog_id: str) -> DogState:
        """Get or create dog state."""
        if dog_id not in self.dogs:
            self.dogs[dog_id] = DogState(dog_id)
            logger.info(f"Created state for dog: {dog_id}")
        return self.dogs[dog_id]

    def update_dog_presence(self, camera_id: str, dogs_present: List[str], timestamp: datetime):
        """Update which dogs are present at a camera."""
        location = self.camera_locations.get(camera_id, camera_id)

        for dog_id in dogs_present:
            dog = self.get_or_create_dog(dog_id)
            dog.update_location(location, timestamp)

        logger.info(f"Updated presence for {len(dogs_present)} dog(s) at {camera_id}")

    def record_motion(self, camera_id: str, timestamp: datetime, window_minutes: int = 10):
        """Record motion event."""
        self.motion_history[camera_id].append(timestamp)

        # Clean old entries
        cutoff = timestamp - timedelta(minutes=window_minutes)
        self.motion_history[camera_id] = [
            t for t in self.motion_history[camera_id] if t > cutoff
        ]

    def has_recent_motion(self, camera_id: str, window_minutes: int = 10) -> bool:
        """Check if camera has recent motion."""
        if camera_id not in self.motion_history:
            return False

        cutoff = datetime.now() - timedelta(minutes=window_minutes)
        recent = [t for t in self.motion_history[camera_id] if t > cutoff]
        return len(recent) > 0

    def get_motion_count(self, camera_id: str) -> int:
        """Get motion event count for camera."""
        return len(self.motion_history.get(camera_id, []))

    def record_alert(self, alert_data: Dict[str, Any]):
        """Record an alert."""
        self.alert_history.append({
            **alert_data,
            "recorded_at": datetime.now()
        })
        logger.info(f"Alert recorded: {alert_data.get('message', 'No message')}")

    def get_context_for_camera(self, camera_id: str) -> Dict[str, Any]:
        """Get analysis context for a camera."""
        return {
            "has_motion": self.has_recent_motion(camera_id),
            "motion_count": self.get_motion_count(camera_id),
            "camera_location": self.camera_locations.get(camera_id),
            "dog_state": {
                dog_id: dog.to_dict()
                for dog_id, dog in self.dogs.items()
            },
            "recent_alerts": self.alert_history[-10:]
        }

    def get_dogs_not_seen_in_location(
        self,
        location: str,
        time_threshold_minutes: int,
        expected_count: int = 2
    ) -> List[str]:
        """Get dogs not seen in location for threshold time."""
        not_seen = []

        # Check all known dogs
        for dog_id, dog in self.dogs.items():
            time_since = dog.time_since_seen_in_location(location)
            if time_since is None or time_since > time_threshold_minutes:
                not_seen.append(dog_id)

        # If we haven't seen enough dogs yet, assume they exist
        for i in range(expected_count - len(self.dogs)):
            not_seen.append(f"dog_{i}")

        return not_seen

    def to_dict(self) -> Dict[str, Any]:
        """Export state as dictionary."""
        return {
            "dogs": {dog_id: dog.to_dict() for dog_id, dog in self.dogs.items()},
            "motion_history": {
                camera_id: [t.isoformat() for t in times]
                for camera_id, times in self.motion_history.items()
            },
            "camera_locations": self.camera_locations,
            "alert_count": len(self.alert_history)
        }
