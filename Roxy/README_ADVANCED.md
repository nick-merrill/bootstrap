# Roxy - Advanced Multi-Camera Dog Monitor 🐕

An intelligent multi-camera monitoring system with flexible scenario analysis and Twilio notifications for monitoring your dogs.

## 🆕 What's New in Advanced Version

The advanced version (`roxy_monitor.py`) adds:

- **Multi-Camera Support**: Monitor multiple cameras simultaneously
- **Multi-Analyzer Framework**: Run different types of analyzers in parallel
- **State Tracking**: Track dog presence/location over time
- **Twilio Integration**: SMS and voice call notifications
- **Time-Based Alerts**: Alert when conditions persist (e.g., "dogs not seen inside for 60+ minutes")
- **YAML Configuration**: Flexible, easy-to-edit configuration
- **Alert Routing**: Configure different notification methods per alert type

## 📋 Two Versions Available

1. **Simple Version** (`dog_monitor.py`) - Single camera, bathroom detection only
2. **Advanced Version** (`roxy_monitor.py`) - Multi-camera, multi-analyzer, full notifications

## 🚀 Quick Start (Advanced Version)

### Prerequisites

1. **Wyze Cameras** or any RTSP-compatible cameras
2. **Anthropic API Key** - [Get one here](https://console.anthropic.com/)
3. **Twilio Account** (optional but recommended) - [Sign up here](https://www.twilio.com/try-twilio)

### For Wyze Cameras

The easiest way to use Wyze cameras is with **docker-wyze-bridge**:

```bash
docker run -p 8554:8554 \
  -e WYZE_EMAIL=your-email@example.com \
  -e WYZE_PASSWORD=your-wyze-password \
  mrlt8/wyze-bridge
```

This creates RTSP streams at: `rtsp://your-ip:8554/camera-name`

See: https://github.com/mrlt8/docker-wyze-bridge

### Installation

```bash
cd Roxy

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your camera URLs and API keys
```

### Configure

Edit `config_advanced.yaml` to:

1. **Set up cameras** - Add/remove cameras, set locations
2. **Configure analyzers** - Enable/disable different detection types
3. **Customize prompts** - Modify what the AI looks for
4. **Set up alerts** - Configure when to send SMS vs calls

Example scenario (included by default):
```yaml
# Alert if both dogs not confirmed inside for 60+ minutes
- type: time_based_alert
  enabled: true
  location: inside
  time_threshold_minutes: 60
  required_dogs: 2
```

### Run

```bash
python roxy_monitor.py
```

Or specify a custom config:
```bash
python roxy_monitor.py my_config.yaml
```

## 🎯 Built-in Analyzers

### 1. Bathroom Detection
- Monitors for signs dog needs bathroom
- Looks for: pacing, door scratching, whining, restlessness
- Triggers: When motion detected + high confidence

### 2. Presence Detection
- Identifies which dogs are visible
- Tracks where each dog was last seen
- Updates state for time-based alerts

### 3. Time-Based Alerts
- Monitors conditions over time
- Example: "Both dogs not seen inside for 60+ minutes"
- Can trigger voice calls for urgent situations

## 📱 Notification System

### SMS Notifications
- Quick alerts for bathroom needs
- Includes camera ID and confidence
- Respects cooldown periods (15min default)

### Voice Calls
- Reserved for urgent alerts
- Example: Dogs not seen inside for extended period
- Can escalate if SMS not acknowledged

### Alert Routing

Configure per-analyzer in `config_advanced.yaml`:

```yaml
alert_routing:
  bathroom_detection:
    use_sms: true
    use_call: false
    priority: high

  time_based_alert:
    use_sms: true
    use_call: true  # More urgent
    priority: high
```

## 📁 Configuration Guide

### Camera Configuration

```yaml
cameras:
  living_room:
    url: ${CAMERA_LIVING_ROOM_URL}
    location: inside
    enabled: true

  backyard:
    url: ${CAMERA_BACKYARD_URL}
    location: outside
    enabled: true
```

- **url**: RTSP stream URL (can use environment variable)
- **location**: Logical location for state tracking
- **enabled**: Enable/disable camera

### Adding Custom Analyzers

You can create custom scenarios by modifying `config_advanced.yaml`:

```yaml
analyzers:
  - type: presence_detection
    enabled: true
    check_interval_seconds: 30
    prompt: |
      Your custom prompt here.
      Ask the AI to look for specific things.
```

## 🔧 Architecture

```
roxy_monitor.py              # Main orchestration
├── multi_camera_handler.py  # Manages multiple RTSP streams
├── motion_detector.py       # Motion detection per camera
├── analyzer_framework.py    # Extensible analyzer system
├── state_tracker.py         # Dog state & history tracking
├── notifier.py             # Twilio SMS/voice integration
└── config_loader.py        # YAML config with env vars
```

## 💡 Usage Examples

### Example 1: Bathroom Monitoring Only

```yaml
cameras:
  living_room:
    url: ${CAMERA_URL}
    location: inside
    enabled: true

analyzers:
  - type: bathroom_detection
    enabled: true
    confidence_threshold: 70

notifications:
  alert_routing:
    bathroom_detection:
      use_sms: true
      use_call: false
```

### Example 2: Multi-Dog Presence Tracking

```yaml
cameras:
  front_door:
    url: ${CAMERA_FRONT_URL}
    location: inside
    enabled: true

  back_door:
    url: ${CAMERA_BACK_URL}
    location: outside
    enabled: true

analyzers:
  - type: presence_detection
    enabled: true
    check_interval_seconds: 60

  - type: time_based_alert
    enabled: true
    location: inside
    time_threshold_minutes: 60
    required_dogs: 2
```

### Example 3: Full House Coverage

Set up cameras in:
- Living room (inside)
- Kitchen (inside)
- Bedrooms (inside)
- Backyard (outside)

Enable all analyzers to track:
- When dogs need bathroom
- Where each dog is located
- If dogs are outside too long
- If dogs are inside when expected

## 🧪 Testing

Test the system without cameras:

```bash
# Test with an image
python test_system.py path/to/dog-image.jpg

# Test with webcam
python test_system.py --webcam
```

## 📊 State Tracking

The system maintains state about:
- **Dog locations**: Last seen location per dog
- **Motion history**: Recent motion per camera
- **Alert history**: All alerts generated
- **Behavior patterns**: Historical observations

Access via logs or extend for database storage.

## 💰 Cost Estimation

### API Costs (Anthropic Claude)

- ~$0.003 per image analysis
- 1 fps when motion detected
- Example: 10 minutes of activity = 600 images = ~$1.80

### Twilio Costs

- SMS: ~$0.01 per message
- Voice: ~$0.02 per minute
- With 15min cooldowns, costs stay minimal

**Optimization Tips**:
- Adjust `check_interval_seconds` for presence detection
- Use motion-triggered analysis only
- Set appropriate confidence thresholds
- Use SMS over calls when possible

## 🛠️ Troubleshooting

### Cameras Won't Connect

1. Test RTSP URL with VLC or ffplay:
   ```bash
   ffplay rtsp://your-camera-url
   ```

2. For Wyze via docker-wyze-bridge:
   - Check container logs: `docker logs <container>`
   - Verify camera names match
   - Ensure network connectivity

### No Notifications

1. Check Twilio credentials in `.env`
2. Verify phone numbers in E.164 format: `+1234567890`
3. Check Twilio console for error messages
4. Ensure cooldown periods haven't blocked alerts

### High API Costs

1. Reduce FPS: `processing.fps: 0.5` (one frame every 2 seconds)
2. Increase presence check interval: `check_interval_seconds: 120`
3. Raise confidence thresholds to reduce false positives
4. Disable analyzers you don't need

### Motion Detection Too Sensitive

Adjust in config:
```yaml
motion_detection:
  threshold: 2000  # Higher = less sensitive
  window_minutes: 10
```

## 🔐 Security Notes

- Store API keys in `.env`, never commit to git
- Use Twilio test credentials during development
- Consider network segmentation for cameras
- Rotate API keys periodically

## 🚧 Extending the System

### Add New Analyzer Type

1. Create analyzer class in `analyzer_framework.py`:
   ```python
   class MyCustomAnalyzer(VisionLLMAnalyzer):
       def should_analyze(self, camera_id, context):
           # Your logic

       def analyze(self, camera_id, frame, context):
           # Your analysis
   ```

2. Register in `AnalyzerManager.load_from_config()`

3. Add to `config_advanced.yaml`:
   ```yaml
   - type: my_custom_analyzer
     enabled: true
     # Your config
   ```

### Add Database Storage

Extend `StateTracker` to persist state:
```python
def save_to_db(self):
    # Store self.to_dict() in database
```

### Add Web Dashboard

Expose state via Flask/FastAPI:
```python
@app.get("/state")
def get_state():
    return state_tracker.to_dict()
```

## 📚 Additional Resources

- **Wyze RTSP Guide**: https://support.wyze.com/hc/en-us/articles/360026245231
- **docker-wyze-bridge**: https://github.com/mrlt8/docker-wyze-bridge
- **Anthropic API Docs**: https://docs.anthropic.com/
- **Twilio Python Guide**: https://www.twilio.com/docs/sms/quickstart/python

## 🐛 Known Issues

- Motion detection may be sensitive to lighting changes
- LLM responses vary in consistency - adjust prompts as needed
- Multiple dogs can be challenging to identify individually
- Camera reconnection may take 5-10 seconds

## 🎓 Tips for Best Results

1. **Camera Placement**: Cover entry/exit points and main living areas
2. **Lighting**: Ensure good lighting for better AI analysis
3. **Test Prompts**: Iterate on analyzer prompts with test images
4. **Start Simple**: Enable one analyzer at a time, validate, then add more
5. **Monitor Logs**: Watch for patterns in false positives/negatives

## 📝 License

MIT License - Use freely for your pets!

## 🙏 Contributing

Issues and PRs welcome! This started as a tool for Roxy but can help many dogs and their humans.
