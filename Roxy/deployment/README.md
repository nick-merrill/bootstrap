# Roxy GCP Deployment

Quick deployment scripts for running Roxy on Google Cloud Platform.

## 🚀 Quick Start

### From Your Local Machine

```bash
cd Roxy/deployment

# 1. Create GCP VM
./create_gcp_vm.sh

# 2. SSH into VM (replace with your instance name and zone)
gcloud compute ssh roxy-monitor --zone=us-central1-a

# 3. On the VM, run setup script
wget https://raw.githubusercontent.com/YOUR_REPO/bootstrap/main/Roxy/deployment/setup_vm.sh
chmod +x setup_vm.sh
./setup_vm.sh
```

### If You Already Have a VM

SSH into your VM and run:

```bash
# Clone repository
git clone https://github.com/YOUR_REPO/bootstrap.git
cd bootstrap/Roxy/deployment

# Run setup
./setup_vm.sh
```

## 📋 What Gets Installed

The `setup_vm.sh` script installs:

1. **Docker & Docker Compose** - Container runtime
2. **Python 3 & pip** - Python environment
3. **Wyze Bridge** - RTSP streams from Wyze cameras
4. **Roxy dependencies** - All Python packages
5. **Systemd service** - Auto-start on boot

## 📁 Files in This Directory

| File | Purpose |
|------|---------|
| `create_gcp_vm.sh` | Create GCP VM from your local machine |
| `setup_vm.sh` | Set up Roxy on the VM (run on VM) |
| `docker-compose.yml` | Docker services configuration |
| `roxy.service` | Systemd service file |
| `Dockerfile` | Docker image for Roxy (optional) |

## ⚙️ Configuration

After running `setup_vm.sh`, you need to configure:

### 1. Edit `.env` file

```bash
cd ~/bootstrap/Roxy
nano .env
```

Add your credentials:
```bash
# Camera URLs (auto-configured from wyze-bridge)
CAMERA_LIVING_ROOM_URL=rtsp://wyze-bridge:8554/living-room

# API Keys
ANTHROPIC_API_KEY=your_key_here
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_FROM_NUMBER=+1234567890
TWILIO_TO_NUMBER_1=+1234567890

# Wyze credentials
WYZE_EMAIL=your-email@example.com
WYZE_PASSWORD=your-password
```

### 2. Edit `config_advanced.yaml`

```bash
nano config_advanced.yaml
```

Configure cameras and analyzers to match your setup.

### 3. Find Your Camera Names

```bash
# Check Wyze Bridge logs to see camera names
docker logs wyze-bridge | grep "Camera"

# You'll see output like:
# [Living Room Camera] Connected
# [Kitchen Camera] Connected
```

Use these names in your camera URLs:
```
rtsp://wyze-bridge:8554/living-room-camera
```

## 🎮 Managing the Service

### Start/Stop Roxy

```bash
# Start
sudo systemctl start roxy

# Stop
sudo systemctl stop roxy

# Restart
sudo systemctl restart roxy

# View status
sudo systemctl status roxy

# Enable auto-start on boot
sudo systemctl enable roxy

# Disable auto-start
sudo systemctl disable roxy
```

### View Logs

```bash
# Roxy logs (live)
sudo journalctl -u roxy -f

# Roxy logs (last 100 lines)
sudo journalctl -u roxy -n 100

# Wyze Bridge logs
docker logs -f wyze-bridge

# All Docker services
docker-compose logs -f
```

### Update Roxy

```bash
cd ~/bootstrap/Roxy
git pull
sudo systemctl restart roxy
```

## 🐳 Docker vs Systemd

You can run Roxy either way:

### Option 1: Systemd Service (Recommended)

**Pros:**
- Direct access to logs
- Easier debugging
- Simpler resource management

**Cons:**
- Need to manage Python environment

```bash
sudo systemctl start roxy
sudo journalctl -u roxy -f
```

### Option 2: Docker Container

**Pros:**
- Isolated environment
- Consistent across systems

**Cons:**
- Slightly more complex networking
- Extra container overhead

```bash
# Edit docker-compose.yml, uncomment roxy service
docker-compose up -d roxy
docker logs -f roxy-monitor
```

## 🔍 Troubleshooting

### Wyze Bridge Not Connecting

```bash
# Check logs
docker logs wyze-bridge

# Restart container
docker-compose restart wyze-bridge

# Check credentials in .env
nano .env
```

### Roxy Service Won't Start

```bash
# Check service status
sudo systemctl status roxy

# View detailed logs
sudo journalctl -u roxy -n 50

# Test manually
cd ~/bootstrap/Roxy
python3 roxy_monitor.py
```

### Can't Connect to Cameras

```bash
# List running containers
docker ps

# Check if wyze-bridge is running
docker logs wyze-bridge

# Test RTSP stream
docker exec -it wyze-bridge ffmpeg -i rtsp://localhost:8554/camera-name -frames:v 1 test.jpg
```

### Out of Memory

```bash
# Check memory usage
free -h
docker stats

# Add swap space
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## 💰 Cost Management

### Monitor Costs

```bash
# Check VM costs in GCP Console
# Compute Engine → VM Instances → click instance → see pricing

# Estimated costs:
# e2-micro:  ~$7/month  (1-2 cameras)
# e2-small:  ~$14/month (3-5 cameras)
# e2-medium: ~$28/month (6+ cameras)
```

### Reduce Costs

1. **Use smaller VM** if performance allows
2. **Use preemptible VM** (80% cheaper, can be stopped)
3. **Stop VM when not needed**:
   ```bash
   gcloud compute instances stop roxy-monitor --zone=us-central1-a
   gcloud compute instances start roxy-monitor --zone=us-central1-a
   ```
4. **Reduce FPS** in config_advanced.yaml:
   ```yaml
   processing:
     fps: 0.5  # Half the API calls
   ```

## 🔒 Security Checklist

- [ ] Restrict SSH to your IP:
  ```bash
  gcloud compute firewall-rules update allow-ssh-roxy \
    --source-ranges=YOUR_IP/32
  ```

- [ ] Use strong passwords for Wyze account
- [ ] Keep API keys in `.env`, never commit to git
- [ ] Enable OS Login:
  ```bash
  gcloud compute instances add-metadata roxy-monitor \
    --metadata enable-oslogin=TRUE
  ```

- [ ] Regular updates:
  ```bash
  sudo apt-get update && sudo apt-get upgrade -y
  ```

## 📊 Monitoring

### Set Up Alerts

1. Go to GCP Console → Monitoring → Alerting
2. Create alert for:
   - High CPU usage
   - High memory usage
   - VM stopped unexpectedly

### Health Checks

```bash
# Check all services
docker ps
sudo systemctl status roxy

# Check disk space
df -h

# Check memory
free -h
```

## 🆘 Getting Help

1. **Check logs first**:
   ```bash
   sudo journalctl -u roxy -f
   docker logs wyze-bridge
   ```

2. **Test components individually**:
   ```bash
   # Test Wyze Bridge
   docker logs wyze-bridge

   # Test Roxy manually
   cd ~/bootstrap/Roxy
   python3 roxy_monitor.py
   ```

3. **Common issues**: See main GCP_DEPLOYMENT.md

## 🎓 Next Steps

After deployment:

1. ✅ VM created and configured
2. ✅ Wyze Bridge running
3. ⏭️ Edit .env with your credentials
4. ⏭️ Configure config_advanced.yaml
5. ⏭️ Start Roxy service
6. ⏭️ Test notifications
7. ⏭️ Monitor and tune settings

---

**Need more help?** See the full [GCP_DEPLOYMENT.md](../GCP_DEPLOYMENT.md) guide.
