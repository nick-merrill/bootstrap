"""RTSP camera connection and frame extraction."""

import cv2
import numpy as np
from typing import Optional
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RTSPCamera:
    """Handle RTSP camera connection and frame capture."""

    def __init__(self, rtsp_url: str, reconnect_delay: int = 5):
        """
        Initialize RTSP camera handler.

        Args:
            rtsp_url: RTSP stream URL
            reconnect_delay: Seconds to wait before reconnecting on failure
        """
        self.rtsp_url = rtsp_url
        self.reconnect_delay = reconnect_delay
        self.capture = None
        self.is_connected = False

    def connect(self) -> bool:
        """
        Connect to RTSP stream.

        Returns:
            True if connection successful
        """
        try:
            logger.info(f"Connecting to RTSP stream: {self.rtsp_url}")
            self.capture = cv2.VideoCapture(self.rtsp_url)

            # Set buffer size to reduce latency
            self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            if self.capture.isOpened():
                self.is_connected = True
                logger.info("Successfully connected to RTSP stream")
                return True
            else:
                logger.error("Failed to open RTSP stream")
                self.is_connected = False
                return False
        except Exception as e:
            logger.error(f"Error connecting to RTSP stream: {e}")
            self.is_connected = False
            return False

    def disconnect(self):
        """Disconnect from RTSP stream."""
        if self.capture is not None:
            self.capture.release()
            self.is_connected = False
            logger.info("Disconnected from RTSP stream")

    def get_frame(self) -> Optional[np.ndarray]:
        """
        Get a single frame from the stream.

        Returns:
            Frame as numpy array, or None if failed
        """
        if not self.is_connected or self.capture is None:
            if not self.connect():
                time.sleep(self.reconnect_delay)
                return None

        try:
            ret, frame = self.capture.read()
            if ret:
                return frame
            else:
                logger.warning("Failed to read frame, reconnecting...")
                self.disconnect()
                return None
        except Exception as e:
            logger.error(f"Error reading frame: {e}")
            self.disconnect()
            return None

    def get_fps(self) -> float:
        """Get the FPS of the camera stream."""
        if self.capture is not None and self.is_connected:
            return self.capture.get(cv2.CAP_PROP_FPS)
        return 0.0

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
