"""Flexible analyzer framework for multiple scenario types."""

import base64
import json
import logging
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
import cv2
import numpy as np
from anthropic import Anthropic

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AnalysisResult:
    """Standardized analysis result."""

    def __init__(
        self,
        analyzer_name: str,
        camera_id: str,
        timestamp: datetime,
        alert: bool,
        confidence: int,
        data: Dict[str, Any],
        message: str
    ):
        self.analyzer_name = analyzer_name
        self.camera_id = camera_id
        self.timestamp = timestamp
        self.alert = alert
        self.confidence = confidence
        self.data = data
        self.message = message

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "analyzer": self.analyzer_name,
            "camera": self.camera_id,
            "timestamp": self.timestamp.isoformat(),
            "alert": self.alert,
            "confidence": self.confidence,
            "data": self.data,
            "message": self.message
        }


class BaseAnalyzer(ABC):
    """Base class for all analyzers."""

    def __init__(self, name: str, config: Dict[str, Any]):
        """
        Initialize analyzer.

        Args:
            name: Analyzer name
            config: Analyzer-specific configuration
        """
        self.name = name
        self.config = config
        self.enabled = config.get("enabled", True)

    @abstractmethod
    def analyze(self, camera_id: str, frame: np.ndarray, context: Dict[str, Any]) -> Optional[AnalysisResult]:
        """
        Analyze a frame.

        Args:
            camera_id: ID of camera that captured frame
            frame: Video frame to analyze
            context: Additional context (motion history, state, etc.)

        Returns:
            AnalysisResult or None
        """
        pass

    @abstractmethod
    def should_analyze(self, camera_id: str, context: Dict[str, Any]) -> bool:
        """
        Determine if this analyzer should run for this camera/context.

        Args:
            camera_id: Camera ID
            context: Current context

        Returns:
            True if should analyze
        """
        pass


class VisionLLMAnalyzer(BaseAnalyzer):
    """Base class for analyzers using vision LLM."""

    def __init__(self, name: str, config: Dict[str, Any], api_key: str, model: str):
        super().__init__(name, config)
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.prompt = config.get("prompt", "")
        self.confidence_threshold = config.get("confidence_threshold", 60)

    def frame_to_base64(self, frame: np.ndarray) -> str:
        """Convert frame to base64 JPEG."""
        success, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not success:
            raise ValueError("Failed to encode frame")
        return base64.b64encode(buffer).decode('utf-8')

    def query_llm(self, frame: np.ndarray, prompt: str) -> Optional[Dict[str, Any]]:
        """Query vision LLM with frame."""
        try:
            image_data = self.frame_to_base64(frame)

            message = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": image_data,
                                },
                            },
                            {"type": "text", "text": prompt}
                        ],
                    }
                ],
            )

            response_text = message.content[0].text

            # Try to extract JSON
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                return json.loads(json_str)
            else:
                return {"raw_response": response_text}

        except Exception as e:
            logger.error(f"LLM query error: {e}")
            return None


class BathroomDetectionAnalyzer(VisionLLMAnalyzer):
    """Detect bathroom needs."""

    def __init__(self, config: Dict[str, Any], api_key: str, model: str):
        super().__init__("bathroom_detection", config, api_key, model)

    def should_analyze(self, camera_id: str, context: Dict[str, Any]) -> bool:
        """Analyze if motion detected recently."""
        return context.get("has_motion", False)

    def analyze(self, camera_id: str, frame: np.ndarray, context: Dict[str, Any]) -> Optional[AnalysisResult]:
        """Analyze for bathroom behavior."""
        result = self.query_llm(frame, self.prompt)

        if not result:
            return None

        needs_bathroom = result.get("needs_bathroom", False)
        confidence = result.get("confidence", 0)
        behaviors = result.get("behaviors_observed", [])

        alert = needs_bathroom and confidence >= self.confidence_threshold

        message = f"Dog needs bathroom (confidence: {confidence}%)" if alert else "No bathroom behavior detected"

        return AnalysisResult(
            analyzer_name=self.name,
            camera_id=camera_id,
            timestamp=datetime.now(),
            alert=alert,
            confidence=confidence,
            data=result,
            message=message
        )


class PresenceDetectionAnalyzer(VisionLLMAnalyzer):
    """Detect dog presence/absence."""

    def __init__(self, config: Dict[str, Any], api_key: str, model: str):
        super().__init__("presence_detection", config, api_key, model)
        self.check_interval = config.get("check_interval_seconds", 60)
        self.last_check = {}

    def should_analyze(self, camera_id: str, context: Dict[str, Any]) -> bool:
        """Check at regular intervals."""
        now = datetime.now()
        last = self.last_check.get(camera_id, datetime.min)
        return (now - last).total_seconds() >= self.check_interval

    def analyze(self, camera_id: str, frame: np.ndarray, context: Dict[str, Any]) -> Optional[AnalysisResult]:
        """Analyze for dog presence."""
        self.last_check[camera_id] = datetime.now()

        result = self.query_llm(frame, self.prompt)

        if not result:
            return None

        dogs_present = result.get("dogs_present", [])
        num_dogs = len(dogs_present)
        confidence = result.get("confidence", 0)

        return AnalysisResult(
            analyzer_name=self.name,
            camera_id=camera_id,
            timestamp=datetime.now(),
            alert=False,  # Presence alone doesn't trigger alert
            confidence=confidence,
            data={"dogs_present": dogs_present, "count": num_dogs},
            message=f"{num_dogs} dog(s) detected in {camera_id}"
        )


class TimeBasedAlertAnalyzer(BaseAnalyzer):
    """Alert based on time-based conditions (e.g., not seen inside for X time)."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__("time_based_alert", config)
        self.condition = config.get("condition", "")
        self.time_threshold_minutes = config.get("time_threshold_minutes", 60)
        self.required_dogs = config.get("required_dogs", 2)
        self.location = config.get("location", "inside")

    def should_analyze(self, camera_id: str, context: Dict[str, Any]) -> bool:
        """Check every analysis cycle."""
        return True

    def analyze(self, camera_id: str, frame: np.ndarray, context: Dict[str, Any]) -> Optional[AnalysisResult]:
        """Check time-based conditions."""
        # Get dog state from context
        dog_state = context.get("dog_state", {})

        # Check when dogs were last seen in the required location
        dogs_in_location = dog_state.get(self.location, {})
        current_time = datetime.now()

        dogs_not_seen = []
        for dog_id in range(self.required_dogs):
            last_seen = dogs_in_location.get(f"dog_{dog_id}", None)
            if last_seen is None:
                dogs_not_seen.append(dog_id)
            else:
                time_diff = (current_time - last_seen).total_seconds() / 60
                if time_diff > self.time_threshold_minutes:
                    dogs_not_seen.append(dog_id)

        alert = len(dogs_not_seen) == self.required_dogs

        if alert:
            message = f"All {self.required_dogs} dogs not confirmed {self.location} for {self.time_threshold_minutes}+ minutes"
        else:
            message = f"Dogs confirmed {self.location} recently"

        return AnalysisResult(
            analyzer_name=self.name,
            camera_id=camera_id,
            timestamp=current_time,
            alert=alert,
            confidence=100,
            data={"dogs_not_seen": dogs_not_seen, "location": self.location},
            message=message
        )


class AnalyzerManager:
    """Manage multiple analyzers."""

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.analyzers: List[BaseAnalyzer] = []

    def add_analyzer(self, analyzer: BaseAnalyzer):
        """Add an analyzer."""
        self.analyzers.append(analyzer)
        logger.info(f"Added analyzer: {analyzer.name}")

    def load_from_config(self, config: Dict[str, Any]):
        """Load analyzers from configuration."""
        for analyzer_config in config.get("analyzers", []):
            analyzer_type = analyzer_config.get("type")

            if analyzer_type == "bathroom_detection":
                self.add_analyzer(
                    BathroomDetectionAnalyzer(analyzer_config, self.api_key, self.model)
                )
            elif analyzer_type == "presence_detection":
                self.add_analyzer(
                    PresenceDetectionAnalyzer(analyzer_config, self.api_key, self.model)
                )
            elif analyzer_type == "time_based_alert":
                self.add_analyzer(
                    TimeBasedAlertAnalyzer(analyzer_config)
                )

    def analyze_frame(
        self,
        camera_id: str,
        frame: np.ndarray,
        context: Dict[str, Any]
    ) -> List[AnalysisResult]:
        """Run all applicable analyzers on a frame."""
        results = []

        for analyzer in self.analyzers:
            if not analyzer.enabled:
                continue

            if analyzer.should_analyze(camera_id, context):
                logger.debug(f"Running analyzer: {analyzer.name} on camera: {camera_id}")
                result = analyzer.analyze(camera_id, frame, context)
                if result:
                    results.append(result)

        return results
