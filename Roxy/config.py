"""Configuration for dog bathroom detection system."""

import os
from dotenv import load_dotenv

load_dotenv()

# RTSP Camera Configuration
RTSP_URL = os.getenv("RTSP_URL", "rtsp://your-camera-ip:554/stream")

# Motion Detection Configuration
MOTION_THRESHOLD = int(os.getenv("MOTION_THRESHOLD", "1000"))  # Minimum pixels changed
MOTION_WINDOW_MINUTES = int(os.getenv("MOTION_WINDOW_MINUTES", "10"))

# Frame Processing Configuration
FPS_PROCESSING = int(os.getenv("FPS_PROCESSING", "1"))  # Process 1 frame per second

# LLM Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "claude-3-5-sonnet-20241022")

# Bathroom Detection Prompt
BATHROOM_DETECTION_PROMPT = """Analyze this image of a dog and determine if the dog is showing signs that they need to go to the bathroom. Look for these behavioral cues:

1. Pacing or circling near the door
2. Whining or barking at the door
3. Sniffing around looking for a spot
4. Restlessness or agitation
5. Squatting or attempting to relieve themselves
6. Standing by the door looking expectant
7. Scratching at the door

Respond with a JSON object containing:
- "needs_bathroom": true/false
- "confidence": 0-100 (percentage)
- "behaviors_observed": list of observed behaviors
- "recommendation": what action to take

Be specific about what you observe in the image."""
