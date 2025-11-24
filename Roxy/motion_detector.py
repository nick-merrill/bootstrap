"""Motion detection module for RTSP camera stream."""

import cv2
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MotionDetector:
    """Detects motion in video stream using frame differencing."""

    def __init__(self, threshold: int = 1000, window_minutes: int = 10):
        """
        Initialize motion detector.

        Args:
            threshold: Minimum number of pixels changed to count as motion
            window_minutes: Time window to track motion history
        """
        self.threshold = threshold
        self.window_minutes = window_minutes
        self.motion_history = []
        self.previous_frame = None

    def detect_motion(self, frame: np.ndarray) -> Tuple[bool, int]:
        """
        Detect motion in the current frame.

        Args:
            frame: Current video frame (BGR format)

        Returns:
            Tuple of (motion_detected, pixel_change_count)
        """
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        # Initialize previous frame if needed
        if self.previous_frame is None:
            self.previous_frame = gray
            return False, 0

        # Compute absolute difference between current and previous frame
        frame_delta = cv2.absdiff(self.previous_frame, gray)
        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]

        # Dilate to fill in holes
        thresh = cv2.dilate(thresh, None, iterations=2)

        # Count non-zero pixels
        pixel_change = np.sum(thresh > 0)

        # Update previous frame
        self.previous_frame = gray

        # Determine if motion detected
        motion_detected = pixel_change > self.threshold

        if motion_detected:
            self.motion_history.append(datetime.now())
            logger.info(f"Motion detected: {pixel_change} pixels changed")

        return motion_detected, pixel_change

    def has_recent_motion(self) -> bool:
        """
        Check if motion has been detected in the last N minutes.

        Returns:
            True if motion detected within the time window
        """
        # Clean up old entries
        cutoff_time = datetime.now() - timedelta(minutes=self.window_minutes)
        self.motion_history = [
            timestamp for timestamp in self.motion_history
            if timestamp > cutoff_time
        ]

        has_motion = len(self.motion_history) > 0

        if has_motion:
            logger.info(
                f"Motion detected {len(self.motion_history)} times "
                f"in last {self.window_minutes} minutes"
            )

        return has_motion

    def get_motion_count(self) -> int:
        """Get the number of motion events in the time window."""
        cutoff_time = datetime.now() - timedelta(minutes=self.window_minutes)
        self.motion_history = [
            timestamp for timestamp in self.motion_history
            if timestamp > cutoff_time
        ]
        return len(self.motion_history)
