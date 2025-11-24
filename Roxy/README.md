# Roxy - Dog Bathroom Detection System

An intelligent monitoring system that uses an RTSP camera feed, motion detection, and visual LLM analysis to detect when your dog needs to go to the bathroom.

## Features

- **RTSP Camera Integration**: Connects to any RTSP-compatible camera
- **Motion Detection**: Monitors for activity in the last 10 minutes
- **Visual LLM Analysis**: Uses Claude's vision capabilities to analyze dog behavior at 1 fps when motion is detected
- **Intelligent Alerts**: Provides confidence scores and behavioral observations
- **Image Capture**: Saves frames when high-confidence bathroom needs are detected

## How It Works

1. **Continuous Monitoring**: Connects to your RTSP camera and monitors the video feed
2. **Motion Detection**: Tracks motion events over a configurable time window (default: 10 minutes)
3. **Conditional Analysis**: When motion is detected, begins analyzing frames at 1 fps using Claude's vision API
4. **Behavior Recognition**: Looks for signs like:
   - Pacing or circling near the door
   - Whining or barking at the door
   - Sniffing around for a spot
   - Restlessness or agitation
   - Squatting behavior
   - Standing by the door expectantly
   - Scratching at the door
5. **Alert System**: Logs alerts and saves images when high confidence is detected

## Installation

### Prerequisites

- Python 3.8 or higher
- RTSP-compatible camera
- Anthropic API key ([get one here](https://console.anthropic.com/))

### Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   ```

3. **Edit `.env` with your settings**:
   - `RTSP_URL`: Your camera's RTSP stream URL
   - `ANTHROPIC_API_KEY`: Your Anthropic API key
   - Adjust other settings as needed

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `RTSP_URL` | RTSP stream URL | `rtsp://your-camera-ip:554/stream` |
| `MOTION_THRESHOLD` | Minimum pixels changed for motion | `1000` |
| `MOTION_WINDOW_MINUTES` | Time window to track motion | `10` |
| `FPS_PROCESSING` | Frames per second to analyze with LLM | `1` |
| `ANTHROPIC_API_KEY` | Your Anthropic API key | (required) |
| `MODEL_NAME` | Claude model to use | `claude-3-5-sonnet-20241022` |

### RTSP URL Format

Common RTSP URL formats:
- Generic: `rtsp://username:password@camera-ip:port/stream`
- Hikvision: `rtsp://admin:password@192.168.1.64:554/Streaming/Channels/101`
- Dahua: `rtsp://admin:password@192.168.1.108:554/cam/realmonitor?channel=1&subtype=0`
- Amcrest: `rtsp://admin:password@192.168.1.100:554/cam/realmonitor?channel=1&subtype=1`
- Reolink: `rtsp://admin:password@192.168.1.100:554/h264Preview_01_main`

## Usage

### Run the monitor:

```bash
python dog_monitor.py
```

### Monitor output:

The system will log:
- Connection status
- Motion detection events
- LLM analysis results
- Alerts when bathroom behavior is detected

### Stop the monitor:

Press `Ctrl+C` to stop monitoring gracefully.

## Project Structure

```
Roxy/
├── dog_monitor.py          # Main orchestration script
├── camera_handler.py       # RTSP camera connection
├── motion_detector.py      # Motion detection logic
├── llm_analyzer.py         # Visual LLM analysis
├── config.py              # Configuration management
├── requirements.txt        # Python dependencies
├── .env.example           # Example environment configuration
└── README.md              # This file
```

## Cost Considerations

The system processes frames at 1 fps only when motion is detected. Each image analysis costs approximately:
- Claude 3.5 Sonnet: ~$0.003 per image

If motion is continuous for 10 minutes, expect ~600 API calls per 10-minute window.

## Troubleshooting

### Camera won't connect
- Verify RTSP URL is correct
- Check network connectivity to camera
- Ensure camera supports RTSP and it's enabled
- Verify username/password if required

### No motion detected
- Adjust `MOTION_THRESHOLD` (lower = more sensitive)
- Check camera view is capturing the area where your dog moves

### API errors
- Verify `ANTHROPIC_API_KEY` is set correctly
- Check your API key has sufficient credits
- Ensure you have access to vision models

### High false positive rate
- The system logs confidence scores - you can adjust alerting threshold in code
- Modify the prompt in `config.py` to be more specific to your dog's behavior

## Customization

### Adjust the detection prompt

Edit `BATHROOM_DETECTION_PROMPT` in `config.py` to customize what behaviors the LLM should look for.

### Change alert threshold

Modify the `confidence_threshold` parameter in `llm_analyzer.py`'s `should_alert()` method (default: 60%).

### Add notifications

Extend the `send_alert()` method in `dog_monitor.py` to send push notifications, emails, or SMS alerts.

## License

MIT License - feel free to modify and use for your own pets!
