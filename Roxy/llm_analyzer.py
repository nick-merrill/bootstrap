"""Visual LLM analyzer for dog bathroom behavior detection."""

import base64
import json
import logging
from typing import Dict, Any, Optional
import cv2
import numpy as np
from anthropic import Anthropic

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DogBehaviorAnalyzer:
    """Analyze dog behavior using visual LLM."""

    def __init__(self, api_key: str, model: str, prompt: str):
        """
        Initialize the behavior analyzer.

        Args:
            api_key: Anthropic API key
            model: Model name to use
            prompt: System prompt for behavior analysis
        """
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.prompt = prompt

    def frame_to_base64(self, frame: np.ndarray) -> str:
        """
        Convert OpenCV frame to base64 encoded JPEG.

        Args:
            frame: OpenCV frame (BGR format)

        Returns:
            Base64 encoded JPEG string
        """
        # Encode frame as JPEG
        success, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not success:
            raise ValueError("Failed to encode frame as JPEG")

        # Convert to base64
        jpg_as_text = base64.b64encode(buffer).decode('utf-8')
        return jpg_as_text

    def analyze_frame(self, frame: np.ndarray) -> Optional[Dict[str, Any]]:
        """
        Analyze a video frame for dog bathroom behavior.

        Args:
            frame: OpenCV frame to analyze

        Returns:
            Analysis result dictionary or None if error
        """
        try:
            # Convert frame to base64
            image_data = self.frame_to_base64(frame)

            # Call Claude API with vision
            logger.info("Analyzing frame with visual LLM...")
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
                            {
                                "type": "text",
                                "text": self.prompt
                            }
                        ],
                    }
                ],
            )

            # Extract response
            response_text = message.content[0].text
            logger.info(f"LLM Response: {response_text}")

            # Try to parse JSON response
            try:
                # Look for JSON in the response
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    result = json.loads(json_str)
                else:
                    # If no JSON found, create a structured response
                    result = {
                        "needs_bathroom": False,
                        "confidence": 0,
                        "behaviors_observed": [],
                        "recommendation": response_text
                    }
            except json.JSONDecodeError:
                logger.warning("Could not parse JSON response, using raw text")
                result = {
                    "needs_bathroom": False,
                    "confidence": 0,
                    "behaviors_observed": [],
                    "recommendation": response_text
                }

            return result

        except Exception as e:
            logger.error(f"Error analyzing frame: {e}")
            return None

    def should_alert(self, analysis: Dict[str, Any], confidence_threshold: int = 60) -> bool:
        """
        Determine if an alert should be sent based on analysis.

        Args:
            analysis: Analysis result from analyze_frame
            confidence_threshold: Minimum confidence to alert

        Returns:
            True if alert should be sent
        """
        if analysis is None:
            return False

        needs_bathroom = analysis.get("needs_bathroom", False)
        confidence = analysis.get("confidence", 0)

        return needs_bathroom and confidence >= confidence_threshold
