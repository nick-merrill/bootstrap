#!/usr/bin/env python3
"""
Test script for the dog bathroom detection system.

This script allows you to test the system with a static image or webcam
instead of requiring an RTSP camera.
"""

import sys
import logging
import cv2
import numpy as np
from llm_analyzer import DogBehaviorAnalyzer
import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_with_image(image_path: str):
    """
    Test the system with a static image.

    Args:
        image_path: Path to image file
    """
    logger.info(f"Testing with image: {image_path}")

    # Load image
    frame = cv2.imread(image_path)
    if frame is None:
        logger.error(f"Could not load image: {image_path}")
        return

    # Initialize analyzer
    if not config.ANTHROPIC_API_KEY:
        logger.error("ANTHROPIC_API_KEY not set")
        return

    analyzer = DogBehaviorAnalyzer(
        api_key=config.ANTHROPIC_API_KEY,
        model=config.MODEL_NAME,
        prompt=config.BATHROOM_DETECTION_PROMPT
    )

    # Analyze
    logger.info("Analyzing image...")
    analysis = analyzer.analyze_frame(frame)

    if analysis:
        print("\n" + "=" * 60)
        print("ANALYSIS RESULT")
        print("=" * 60)
        print(f"Needs Bathroom: {analysis.get('needs_bathroom', False)}")
        print(f"Confidence: {analysis.get('confidence', 0)}%")
        print(f"Behaviors: {', '.join(analysis.get('behaviors_observed', []))}")
        print(f"Recommendation: {analysis.get('recommendation', '')}")
        print("=" * 60 + "\n")

        if analyzer.should_alert(analysis):
            print("🚨 ALERT: Dog may need to go to the bathroom!")
    else:
        logger.error("Analysis failed")


def test_with_webcam():
    """Test the system with your computer's webcam."""
    logger.info("Testing with webcam (press 'q' to quit, 'space' to analyze frame)")

    # Open webcam
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        logger.error("Could not open webcam")
        return

    # Initialize analyzer
    if not config.ANTHROPIC_API_KEY:
        logger.error("ANTHROPIC_API_KEY not set")
        return

    analyzer = DogBehaviorAnalyzer(
        api_key=config.ANTHROPIC_API_KEY,
        model=config.MODEL_NAME,
        prompt=config.BATHROOM_DETECTION_PROMPT
    )

    print("\nWebcam Controls:")
    print("  SPACE - Analyze current frame")
    print("  Q - Quit\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Display frame
        cv2.imshow('Webcam Test (SPACE=analyze, Q=quit)', frame)

        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            break
        elif key == ord(' '):
            logger.info("Analyzing frame...")
            analysis = analyzer.analyze_frame(frame)

            if analysis:
                print("\n" + "=" * 60)
                print("ANALYSIS RESULT")
                print("=" * 60)
                print(f"Needs Bathroom: {analysis.get('needs_bathroom', False)}")
                print(f"Confidence: {analysis.get('confidence', 0)}%")
                print(f"Behaviors: {', '.join(analysis.get('behaviors_observed', []))}")
                print(f"Recommendation: {analysis.get('recommendation', '')}")
                print("=" * 60 + "\n")

    cap.release()
    cv2.destroyAllWindows()


def main():
    """Main entry point for test script."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Test with image:  python test_system.py <image_path>")
        print("  Test with webcam: python test_system.py --webcam")
        sys.exit(1)

    if sys.argv[1] == "--webcam":
        test_with_webcam()
    else:
        test_with_image(sys.argv[1])


if __name__ == "__main__":
    main()
