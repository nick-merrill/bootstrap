"""Multi-camera RTSP stream handler."""

import cv2
import numpy as np
from typing import Optional, Dict, List
import logging
import time
import threading
from queue import Queue, Empty

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CameraStream:
    """Individual camera stream handler."""

    def __init__(self, camera_id: str, rtsp_url: str, reconnect_delay: int = 5):
        """
        Initialize camera stream.

        Args:
            camera_id: Unique identifier for this camera
            rtsp_url: RTSP stream URL
            reconnect_delay: Seconds to wait before reconnecting
        """
        self.camera_id = camera_id
        self.rtsp_url = rtsp_url
        self.reconnect_delay = reconnect_delay
        self.capture = None
        self.is_connected = False
        self.latest_frame = None
        self.frame_lock = threading.Lock()
        self.running = False
        self.thread = None

    def connect(self) -> bool:
        """Connect to RTSP stream."""
        try:
            logger.info(f"[{self.camera_id}] Connecting to RTSP stream...")
            self.capture = cv2.VideoCapture(self.rtsp_url)
            self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            if self.capture.isOpened():
                self.is_connected = True
                logger.info(f"[{self.camera_id}] Successfully connected")
                return True
            else:
                logger.error(f"[{self.camera_id}] Failed to open stream")
                self.is_connected = False
                return False
        except Exception as e:
            logger.error(f"[{self.camera_id}] Connection error: {e}")
            self.is_connected = False
            return False

    def disconnect(self):
        """Disconnect from stream."""
        if self.capture is not None:
            self.capture.release()
            self.is_connected = False
            logger.info(f"[{self.camera_id}] Disconnected")

    def _capture_loop(self):
        """Background thread to continuously capture frames."""
        while self.running:
            if not self.is_connected:
                if not self.connect():
                    time.sleep(self.reconnect_delay)
                    continue

            try:
                ret, frame = self.capture.read()
                if ret:
                    with self.frame_lock:
                        self.latest_frame = frame
                else:
                    logger.warning(f"[{self.camera_id}] Failed to read frame, reconnecting...")
                    self.disconnect()
            except Exception as e:
                logger.error(f"[{self.camera_id}] Capture error: {e}")
                self.disconnect()

            time.sleep(0.033)  # ~30 fps max

    def start(self):
        """Start background frame capture."""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        logger.info(f"[{self.camera_id}] Started background capture")

    def stop(self):
        """Stop background frame capture."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        self.disconnect()
        logger.info(f"[{self.camera_id}] Stopped background capture")

    def get_frame(self) -> Optional[np.ndarray]:
        """Get latest frame."""
        with self.frame_lock:
            return self.latest_frame.copy() if self.latest_frame is not None else None


class MultiCameraManager:
    """Manage multiple camera streams."""

    def __init__(self, camera_configs: Dict[str, str]):
        """
        Initialize multi-camera manager.

        Args:
            camera_configs: Dict of {camera_id: rtsp_url}
        """
        self.cameras: Dict[str, CameraStream] = {}

        for camera_id, rtsp_url in camera_configs.items():
            self.cameras[camera_id] = CameraStream(camera_id, rtsp_url)
            logger.info(f"Registered camera: {camera_id}")

    def start_all(self):
        """Start all camera streams."""
        logger.info(f"Starting {len(self.cameras)} camera streams...")
        for camera in self.cameras.values():
            camera.start()

    def stop_all(self):
        """Stop all camera streams."""
        logger.info("Stopping all camera streams...")
        for camera in self.cameras.values():
            camera.stop()

    def get_frame(self, camera_id: str) -> Optional[np.ndarray]:
        """Get latest frame from specific camera."""
        if camera_id in self.cameras:
            return self.cameras[camera_id].get_frame()
        return None

    def get_all_frames(self) -> Dict[str, np.ndarray]:
        """Get latest frames from all cameras."""
        frames = {}
        for camera_id, camera in self.cameras.items():
            frame = camera.get_frame()
            if frame is not None:
                frames[camera_id] = frame
        return frames

    def get_camera_ids(self) -> List[str]:
        """Get list of all camera IDs."""
        return list(self.cameras.keys())

    def __enter__(self):
        """Context manager entry."""
        self.start_all()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop_all()
