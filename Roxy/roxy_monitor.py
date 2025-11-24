#!/usr/bin/env python3
"""
Roxy - Advanced Multi-Camera Dog Monitor

Multi-camera monitoring system with flexible analyzers and Twilio notifications.
"""

import time
import logging
import sys
import os
from datetime import datetime
from pathlib import Path
import cv2

from config_loader import ConfigLoader
from multi_camera_handler import MultiCameraManager
from motion_detector import MotionDetector
from analyzer_framework import AnalyzerManager
from state_tracker import StateTracker
from notifier import NotificationManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RoxyMonitor:
    """Advanced multi-camera dog monitoring system."""

    def __init__(self, config_path: str = "config_advanced.yaml"):
        """
        Initialize Roxy monitor.

        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        logger.info("Loading configuration...")
        self.config_loader = ConfigLoader(config_path)
        self.config_loader.load()

        # Setup logging
        log_config = self.config_loader.get_logging_config()
        log_level = getattr(logging, log_config.get('level', 'INFO'))
        logging.getLogger().setLevel(log_level)

        # Setup alert image directory
        self.save_alert_images = log_config.get('save_alert_images', True)
        self.alert_directory = Path(log_config.get('alert_image_directory', './alerts'))
        if self.save_alert_images:
            self.alert_directory.mkdir(exist_ok=True)
            logger.info(f"Alert images will be saved to: {self.alert_directory}")

        # Initialize components
        logger.info("Initializing components...")

        # Camera manager
        camera_configs = self.config_loader.get_camera_configs()
        self.camera_manager = MultiCameraManager(camera_configs)
        logger.info(f"Initialized {len(camera_configs)} cameras")

        # Motion detectors (one per camera)
        motion_config = self.config_loader.get_motion_config()
        self.motion_detectors = {
            camera_id: MotionDetector(
                threshold=motion_config.get('threshold', 1000),
                window_minutes=motion_config.get('window_minutes', 10)
            )
            for camera_id in camera_configs.keys()
        }
        logger.info("Initialized motion detectors")

        # State tracker
        self.state_tracker = StateTracker()
        camera_locations = self.config_loader.get_camera_locations()
        for camera_id, location in camera_locations.items():
            self.state_tracker.register_camera_location(camera_id, location)
        logger.info("Initialized state tracker")

        # Analyzer manager
        llm_config = self.config_loader.get_llm_config()
        self.analyzer_manager = AnalyzerManager(
            api_key=llm_config['api_key'],
            model=llm_config.get('model', 'claude-3-5-sonnet-20241022')
        )
        self.analyzer_manager.load_from_config(self.config_loader.config)
        logger.info(f"Initialized {len(self.analyzer_manager.analyzers)} analyzers")

        # Notification manager
        notif_config = self.config_loader.get_notification_config()
        self.notification_manager = NotificationManager(
            notif_config.get('twilio', {})
        )
        self.alert_routing = notif_config.get('alert_routing', {})
        logger.info("Initialized notification manager")

        # Processing settings
        processing_config = self.config_loader.get_processing_config()
        self.fps = processing_config.get('fps', 1)
        self.frame_interval = 1.0 / self.fps
        self.last_analysis_time = {}

        self.running = False

    def process_camera_frame(self, camera_id: str, frame):
        """
        Process a frame from a specific camera.

        Args:
            camera_id: ID of the camera
            frame: Video frame
        """
        # Always check for motion
        motion_detected, pixel_change = self.motion_detectors[camera_id].detect_motion(frame)

        if motion_detected:
            self.state_tracker.record_motion(camera_id, datetime.now())

        # Check if we should run analyzers
        current_time = time.time()
        last_analysis = self.last_analysis_time.get(camera_id, 0)

        if current_time - last_analysis >= self.frame_interval:
            # Get context for this camera
            context = self.state_tracker.get_context_for_camera(camera_id)

            # Run analyzers
            results = self.analyzer_manager.analyze_frame(camera_id, frame, context)

            # Process results
            for result in results:
                self.handle_analysis_result(result, frame)

            self.last_analysis_time[camera_id] = current_time

    def handle_analysis_result(self, result, frame):
        """
        Handle analysis result from an analyzer.

        Args:
            result: AnalysisResult object
            frame: Frame that was analyzed
        """
        logger.info(f"[{result.camera_id}] {result.analyzer_name}: {result.message}")

        # Update state based on analyzer type
        if result.analyzer_name == "presence_detection":
            dogs_present = result.data.get('dogs_present', [])
            self.state_tracker.update_dog_presence(
                result.camera_id,
                dogs_present,
                result.timestamp
            )

        # Handle alerts
        if result.alert:
            self.handle_alert(result, frame)

    def handle_alert(self, result, frame):
        """
        Handle an alert condition.

        Args:
            result: AnalysisResult that triggered alert
            frame: Current frame
        """
        logger.warning("=" * 60)
        logger.warning(f"🚨 ALERT: {result.message}")
        logger.warning(f"Camera: {result.camera_id}")
        logger.warning(f"Analyzer: {result.analyzer_name}")
        logger.warning(f"Confidence: {result.confidence}%")
        logger.warning("=" * 60)

        # Save frame if configured
        if self.save_alert_images:
            timestamp = result.timestamp.strftime("%Y%m%d_%H%M%S")
            filename = self.alert_directory / f"{result.analyzer_name}_{result.camera_id}_{timestamp}.jpg"
            cv2.imwrite(str(filename), frame)
            logger.info(f"Alert image saved: {filename}")

        # Record alert in state
        self.state_tracker.record_alert(result.to_dict())

        # Send notifications
        self._send_notification(result)

    def _send_notification(self, result):
        """Send notification based on alert routing."""
        routing = self.alert_routing.get(result.analyzer_name, {})

        use_sms = routing.get('use_sms', True)
        use_call = routing.get('use_call', False)
        priority = routing.get('priority', 'normal')

        # Special handling for specific analyzer types
        if result.analyzer_name == "bathroom_detection":
            behaviors = result.data.get('behaviors_observed', [])
            self.notification_manager.send_bathroom_alert(
                camera_id=result.camera_id,
                confidence=result.confidence,
                behaviors=behaviors
            )
        elif result.analyzer_name == "time_based_alert":
            location = result.data.get('location', 'unknown')
            dogs_missing = result.data.get('dogs_not_seen', [])
            # Extract time threshold from config
            time_threshold = 60  # Default
            for analyzer_config in self.config_loader.get_analyzer_configs():
                if analyzer_config.get('type') == 'time_based_alert':
                    time_threshold = analyzer_config.get('time_threshold_minutes', 60)
                    break

            self.notification_manager.send_presence_alert(
                location=location,
                dogs_missing=dogs_missing,
                minutes=time_threshold
            )
        else:
            # Generic alert
            self.notification_manager.send_alert(
                title=f"Alert from {result.analyzer_name}",
                message=result.message,
                priority=priority,
                use_sms=use_sms,
                use_call=use_call
            )

    def run(self):
        """Main monitoring loop."""
        logger.info("=" * 60)
        logger.info("🐕 Starting Roxy Monitor")
        logger.info("=" * 60)
        logger.info(f"Cameras: {len(self.camera_manager.get_camera_ids())}")
        logger.info(f"Analyzers: {len(self.analyzer_manager.analyzers)}")
        logger.info(f"Processing: {self.fps} fps")
        logger.info("=" * 60)

        self.running = True

        try:
            with self.camera_manager:
                logger.info("🎥 All cameras started")
                logger.info("Press Ctrl+C to stop")

                while self.running:
                    # Get frames from all cameras
                    frames = self.camera_manager.get_all_frames()

                    # Process each frame
                    for camera_id, frame in frames.items():
                        self.process_camera_frame(camera_id, frame)

                    # Small delay
                    time.sleep(0.1)

        except KeyboardInterrupt:
            logger.info("\n👋 Monitoring stopped by user")
        except Exception as e:
            logger.error(f"❌ Error in monitoring loop: {e}", exc_info=True)
            self.notification_manager.send_system_alert(f"System error: {e}")
        finally:
            self.running = False
            logger.info("🛑 Roxy Monitor stopped")

            # Print final state
            logger.info("\nFinal State:")
            state = self.state_tracker.to_dict()
            logger.info(f"Dogs tracked: {len(state['dogs'])}")
            logger.info(f"Alerts generated: {state['alert_count']}")


def main():
    """Entry point."""
    config_path = os.getenv("ROXY_CONFIG", "config_advanced.yaml")

    if len(sys.argv) > 1:
        config_path = sys.argv[1]

    if not os.path.exists(config_path):
        logger.error(f"Configuration file not found: {config_path}")
        logger.info("Usage: python roxy_monitor.py [config_file]")
        sys.exit(1)

    monitor = RoxyMonitor(config_path)
    monitor.run()


if __name__ == "__main__":
    main()
