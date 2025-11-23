# Wyze Camera Setup Guide for Roxy

Quick guide to get your Wyze cameras working with Roxy monitor.

## Option 1: Docker Wyze Bridge (Recommended)

This is the **easiest and best option** - works with ALL Wyze cameras, no firmware flashing needed!

### Install Docker

#### Linux:
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
```

#### Mac:
Download Docker Desktop from: https://www.docker.com/products/docker-desktop

#### Windows:
Download Docker Desktop from: https://www.docker.com/products/docker-desktop

### Run Wyze Bridge

```bash
docker run -d \
  --name wyze-bridge \
  --restart unless-stopped \
  -p 8554:8554 \
  -e WYZE_EMAIL=your-email@example.com \
  -e WYZE_PASSWORD=your-wyze-password \
  mrlt8/wyze-bridge
```

### Find Your Camera URLs

```bash
# Check logs to see camera names
docker logs wyze-bridge

# Look for lines like:
# [Front Door] rtsp://192.168.1.X:8554/front-door
# [Living Room] rtsp://192.168.1.X:8554/living-room
```

### Configure Roxy

In your `.env` file:
```bash
CAMERA_LIVING_ROOM_URL=rtsp://192.168.1.X:8554/living-room
CAMERA_KITCHEN_URL=rtsp://192.168.1.X:8554/kitchen
# etc.
```

### Advanced Options

```bash
docker run -d \
  --name wyze-bridge \
  --restart unless-stopped \
  -p 8554:8554 \
  -e WYZE_EMAIL=your-email@example.com \
  -e WYZE_PASSWORD=your-wyze-password \
  -e QUALITY=HD120 \              # HD quality, 120fps
  -e SNAPSHOT=API \               # Enable snapshots
  -e ON_DEMAND=True \            # Stream only when needed (saves bandwidth)
  mrlt8/wyze-bridge
```

Full documentation: https://github.com/mrlt8/docker-wyze-bridge

## Option 2: Official RTSP Firmware

Only works for older Wyze cameras (V2, V3, Pan, Pan V2).

### Supported Cameras
- Wyze Cam v2
- Wyze Cam v3
- Wyze Cam Pan
- Wyze Cam Pan v2

NOT supported:
- Wyze Cam v4 (use Docker Bridge instead)
- Wyze Cam OG (use Docker Bridge instead)

### Steps

1. **Download RTSP firmware** from:
   https://support.wyze.com/hc/en-us/articles/360026245231-Wyze-Cam-RTSP

2. **Flash firmware** via Wyze app:
   - Open Wyze app
   - Go to camera settings
   - Select "Device Info"
   - Select "Firmware Upgrade"
   - Choose the RTSP firmware file

3. **Enable RTSP** in camera settings:
   - Open camera in Wyze app
   - Go to Settings → Advanced Settings → RTSP
   - Turn on RTSP
   - Set username and password

4. **Get RTSP URL**:
   ```
   rtsp://username:password@camera-ip:554/live
   ```

## Testing Your Setup

### Test Stream with VLC

```bash
# Install VLC if needed
# Mac: brew install vlc
# Ubuntu: sudo apt install vlc
# Windows: Download from videolan.org

# Test stream
vlc rtsp://your-camera-url
```

### Test with FFmpeg

```bash
# Install ffmpeg if needed
# Mac: brew install ffmpeg
# Ubuntu: sudo apt install ffmpeg

# Test stream
ffplay rtsp://your-camera-url

# Check stream info
ffprobe rtsp://your-camera-url
```

## Multiple Cameras

You can run multiple Wyze cameras through the same Docker Bridge:

```bash
docker run -d \
  --name wyze-bridge \
  --restart unless-stopped \
  -p 8554:8554 \
  -e WYZE_EMAIL=your-email@example.com \
  -e WYZE_PASSWORD=your-wyze-password \
  mrlt8/wyze-bridge
```

All cameras on your Wyze account will be available automatically!

Then in `config_advanced.yaml`:
```yaml
cameras:
  living_room:
    url: rtsp://192.168.1.X:8554/living-room
    location: inside
    enabled: true

  kitchen:
    url: rtsp://192.168.1.X:8554/kitchen
    location: inside
    enabled: true

  backyard:
    url: rtsp://192.168.1.X:8554/backyard
    location: outside
    enabled: true
```

## Troubleshooting

### Can't Connect to Docker Bridge

1. Check container is running:
   ```bash
   docker ps
   ```

2. Check logs:
   ```bash
   docker logs wyze-bridge
   ```

3. Restart container:
   ```bash
   docker restart wyze-bridge
   ```

### Stream Buffering/Lagging

1. Reduce quality:
   ```bash
   docker run ... -e QUALITY=SD60 ...
   ```

2. Enable on-demand mode:
   ```bash
   docker run ... -e ON_DEMAND=True ...
   ```

3. Check network speed:
   ```bash
   ping camera-ip
   ```

### Authentication Failed

1. Verify credentials in docker command
2. Check if 2FA is enabled (may need app password)
3. Try re-entering credentials:
   ```bash
   docker stop wyze-bridge
   docker rm wyze-bridge
   # Run docker run command again with correct credentials
   ```

### Camera Not Appearing

1. Ensure camera is online in Wyze app
2. Check camera name in logs:
   ```bash
   docker logs wyze-bridge | grep "Camera"
   ```

3. Verify firmware is up to date in Wyze app

## Performance Tips

### Bandwidth Optimization

If you have many cameras:

```bash
docker run -d \
  --name wyze-bridge \
  -p 8554:8554 \
  -e WYZE_EMAIL=your-email@example.com \
  -e WYZE_PASSWORD=your-wyze-password \
  -e QUALITY=SD30 \              # Lower quality
  -e ON_DEMAND=True \            # Only stream when needed
  mrlt8/wyze-bridge
```

### Local Network Only

For security, bind to localhost only if running on same machine:

```bash
docker run -d \
  --name wyze-bridge \
  -p 127.0.0.1:8554:8554 \
  -e WYZE_EMAIL=your-email@example.com \
  -e WYZE_PASSWORD=your-wyze-password \
  mrlt8/wyze-bridge
```

Then use:
```
rtsp://127.0.0.1:8554/camera-name
```

## Recommended Wyze Settings

For best results with Roxy:

1. **Night Vision**: Auto or On
2. **Motion Detection**: Enabled
3. **Recording**: Continuous or Event
4. **Resolution**: 1080p (HD)
5. **Detection Zone**: Set to focus on areas where dog moves

## Next Steps

After setting up cameras:

1. ✅ Test each camera URL with VLC/ffplay
2. ✅ Add URLs to `.env` file
3. ✅ Configure cameras in `config_advanced.yaml`
4. ✅ Run Roxy monitor
5. ✅ Watch logs to confirm cameras connected
6. ✅ Test with your dog and adjust settings

## Getting Help

- **Docker Wyze Bridge Issues**: https://github.com/mrlt8/docker-wyze-bridge/issues
- **Wyze RTSP Issues**: https://forums.wyze.com/
- **Roxy Issues**: Check main README troubleshooting section
