#!/usr/bin/env python3
"""
Dog Bathroom Detection Monitor

Monitors RTSP camera feed for dog bathroom behavior using motion detection
and visual LLM analysis.
"""

import time
import logging
import sys
from datetime import datetime
from typing import Optional
import cv2

from camera_handler import RTSPCamera
from motion_detector import MotionDetector
from llm_analyzer import DogBehaviorAnalyzer
import config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DogMonitor:
    """Main monitor orchestrating camera, motion detection, and LLM analysis."""

    def __init__(self):
        """Initialize the dog monitor."""
        # Validate configuration
        if not config.ANTHROPIC_API_KEY:
            logger.error("ANTHROPIC_API_KEY not set in environment")
            sys.exit(1)

        # Initialize components
        self.camera = RTSPCamera(config.RTSP_URL)
        self.motion_detector = MotionDetector(
            threshold=config.MOTION_THRESHOLD,
            window_minutes=config.MOTION_WINDOW_MINUTES
        )
        self.analyzer = DogBehaviorAnalyzer(
            api_key=config.ANTHROPIC_API_KEY,
            model=config.MODEL_NAME,
            prompt=config.BATHROOM_DETECTION_PROMPT
        )

        self.frame_interval = 1.0 / config.FPS_PROCESSING
        self.last_analysis_time = 0
        self.running = False

    def process_frame(self, frame):
        """
        Process a single frame for motion and behavior analysis.

        Args:
            frame: OpenCV frame to process
        """
        # Always check for motion
        motion_detected, pixel_change = self.motion_detector.detect_motion(frame)

        # Check if we should analyze with LLM
        current_time = time.time()
        has_recent_motion = self.motion_detector.has_recent_motion()

        # Only analyze if:
        # 1. Motion detected in last N minutes
        # 2. Enough time has passed since last analysis (1 fps)
        if has_recent_motion and (current_time - self.last_analysis_time >= self.frame_interval):
            logger.info("Motion detected recently, analyzing frame with LLM...")

            analysis = self.analyzer.analyze_frame(frame)

            if analysis:
                self.handle_analysis_result(analysis, frame)

            self.last_analysis_time = current_time
        elif has_recent_motion:
            motion_count = self.motion_detector.get_motion_count()
            logger.debug(
                f"Motion active ({motion_count} events in {config.MOTION_WINDOW_MINUTES}min), "
                f"waiting for next analysis interval..."
            )

    def handle_analysis_result(self, analysis: dict, frame):
        """
        Handle the analysis result from the LLM.

        Args:
            analysis: Analysis result dictionary
            frame: Current frame (for saving if needed)
        """
        needs_bathroom = analysis.get("needs_bathroom", False)
        confidence = analysis.get("confidence", 0)
        behaviors = analysis.get("behaviors_observed", [])
        recommendation = analysis.get("recommendation", "")

        logger.info("=" * 60)
        logger.info("ANALYSIS RESULT")
        logger.info("=" * 60)
        logger.info(f"Needs Bathroom: {needs_bathroom}")
        logger.info(f"Confidence: {confidence}%")
        logger.info(f"Behaviors Observed: {', '.join(behaviors) if behaviors else 'None'}")
        logger.info(f"Recommendation: {recommendation}")
        logger.info("=" * 60)

        # Alert if high confidence
        if self.analyzer.should_alert(analysis):
            self.send_alert(analysis, frame)

    def send_alert(self, analysis: dict, frame):
        """
        Send alert when dog needs bathroom.

        Args:
            analysis: Analysis result
            frame: Current frame
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"alert_{timestamp}.jpg"

        # Save the frame
        cv2.imwrite(filename, frame)

        logger.warning("!" * 60)
        logger.warning("🚨 ALERT: Roxy may need to go to the bathroom!")
        logger.warning(f"Confidence: {analysis.get('confidence', 0)}%")
        logger.warning(f"Behaviors: {', '.join(analysis.get('behaviors_observed', []))}")
        logger.warning(f"Image saved to: {filename}")
        logger.warning("!" * 60)

    def run(self):
        """Main monitoring loop."""
        logger.info("Starting Dog Bathroom Monitor...")
        logger.info(f"RTSP URL: {config.RTSP_URL}")
        logger.info(f"Motion window: {config.MOTION_WINDOW_MINUTES} minutes")
        logger.info(f"Processing rate: {config.FPS_PROCESSING} fps")

        self.running = True

        try:
            with self.camera:
                logger.info("Monitoring started. Press Ctrl+C to stop.")

                while self.running:
                    frame = self.camera.get_frame()

                    if frame is not None:
                        self.process_frame(frame)
                    else:
                        logger.warning("No frame received, retrying...")
                        time.sleep(1)

                    # Small delay to prevent overwhelming the system
                    time.sleep(0.1)

        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}", exc_info=True)
        finally:
            self.running = False
            logger.info("Dog Bathroom Monitor stopped")


def main():
    """Entry point for the dog monitor."""
    monitor = DogMonitor()
    monitor.run()


if __name__ == "__main__":
    main()
