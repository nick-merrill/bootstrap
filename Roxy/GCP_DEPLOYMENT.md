# Deploying Roxy to Google Cloud Platform

Complete guide to deploy Roxy monitoring system on GCP with automatic startup and monitoring.

## 🎯 Overview

We'll set up:
- GCP Compute Engine VM
- Docker + Docker Compose
- Wyze Bridge container
- Roxy monitor running as a systemd service
- Automatic restart on failure/reboot
- SSH access for management

## 📋 Prerequisites

1. **GCP Account** - [Sign up](https://cloud.google.com/)
2. **gcloud CLI** - [Install](https://cloud.google.com/sdk/docs/install)
3. **Anthropic API Key** - [Get one](https://console.anthropic.com/)
4. **Twilio Account** (optional) - [Sign up](https://www.twilio.com/try-twilio)

## 🚀 Quick Start (Automated)

### Option 1: One-Command Deployment

```bash
# Clone and run setup script
git clone https://github.com/YOUR_REPO/bootstrap.git
cd bootstrap/Roxy/deployment
./deploy_to_gcp.sh
```

The script will:
1. Create GCP VM
2. Install Docker
3. Set up Wyze Bridge
4. Install Roxy
5. Configure systemd service
6. Start monitoring

### Option 2: Manual Step-by-Step

Follow the sections below for manual deployment.

## 📦 Step 1: Create GCP VM

### Using gcloud CLI

```bash
# Set your project
gcloud config set project YOUR_PROJECT_ID

# Create VM instance
gcloud compute instances create roxy-monitor \
  --zone=us-central1-a \
  --machine-type=e2-medium \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=20GB \
  --boot-disk-type=pd-standard \
  --tags=roxy-monitor \
  --metadata=startup-script='#!/bin/bash
    apt-get update
    apt-get install -y docker.io docker-compose git python3-pip
    systemctl enable docker
    systemctl start docker
    usermod -aG docker $USER'

# Create firewall rule (if you need external access)
gcloud compute firewall-rules create allow-ssh-roxy \
  --allow=tcp:22 \
  --target-tags=roxy-monitor \
  --source-ranges=0.0.0.0/0
```

### Recommended VM Specs

| Use Case | Machine Type | vCPUs | RAM | Monthly Cost* |
|----------|-------------|-------|-----|---------------|
| 1-2 cameras | e2-micro | 2 | 1 GB | ~$7 |
| 3-5 cameras | e2-small | 2 | 2 GB | ~$14 |
| 6+ cameras | e2-medium | 2 | 4 GB | ~$28 |

*Approximate costs, check current GCP pricing

### Using GCP Console

1. Go to [GCP Console](https://console.cloud.google.com/)
2. Navigate to **Compute Engine → VM Instances**
3. Click **Create Instance**
4. Configure:
   - **Name**: roxy-monitor
   - **Region**: us-central1 (or nearest)
   - **Machine type**: e2-medium (or smaller)
   - **Boot disk**: Ubuntu 22.04 LTS, 20 GB
   - **Firewall**: Allow HTTP/HTTPS (optional)
5. Click **Create**

## 🔐 Step 2: SSH into VM

```bash
# Using gcloud
gcloud compute ssh roxy-monitor --zone=us-central1-a

# Or use regular SSH
ssh -i ~/.ssh/google_compute_engine USERNAME@EXTERNAL_IP
```

## 🐳 Step 3: Install Dependencies

Run on the VM:

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker
sudo apt-get install -y docker.io docker-compose

# Install Python and dependencies
sudo apt-get install -y python3 python3-pip git

# Add user to docker group
sudo usermod -aG docker $USER

# Reload groups (or logout/login)
newgrp docker

# Verify installation
docker --version
python3 --version
```

## 📥 Step 4: Clone Repository

```bash
# Clone your repo
git clone https://github.com/YOUR_REPO/bootstrap.git
cd bootstrap/Roxy

# Or if starting fresh, create directory
mkdir -p ~/roxy && cd ~/roxy
```

## 🎬 Step 5: Set Up Docker Compose

We'll use Docker Compose to manage both Wyze Bridge and Roxy:

```bash
# Copy docker-compose.yml (see deployment/ folder)
cp deployment/docker-compose.yml .

# Create .env file
cp .env.example .env
nano .env  # Edit with your credentials
```

Edit `.env`:
```bash
# Camera URLs will be from wyze-bridge: rtsp://wyze-bridge:8554/camera-name
CAMERA_LIVING_ROOM_URL=rtsp://wyze-bridge:8554/living-room
CAMERA_KITCHEN_URL=rtsp://wyze-bridge:8554/kitchen

# API Keys
ANTHROPIC_API_KEY=your_key_here
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_FROM_NUMBER=+1234567890
TWILIO_TO_NUMBER_1=+1234567890

# Wyze Credentials
WYZE_EMAIL=your-email@example.com
WYZE_PASSWORD=your-password
```

Start services:
```bash
docker-compose up -d
```

## 🔧 Step 6: Install Roxy as System Service

This runs Roxy natively (not in Docker) for easier management:

```bash
cd ~/bootstrap/Roxy

# Install Python dependencies
pip3 install -r requirements.txt

# Copy systemd service file
sudo cp deployment/roxy.service /etc/systemd/system/

# Edit service file with correct paths
sudo nano /etc/systemd/system/roxy.service

# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable roxy

# Start service
sudo systemctl start roxy

# Check status
sudo systemctl status roxy
```

## 📊 Step 7: Monitor and Manage

### View Logs

```bash
# Roxy logs
sudo journalctl -u roxy -f

# Wyze Bridge logs
docker logs -f wyze-bridge

# Docker Compose logs
docker-compose logs -f
```

### Service Management

```bash
# Start
sudo systemctl start roxy

# Stop
sudo systemctl stop roxy

# Restart
sudo systemctl restart roxy

# Status
sudo systemctl status roxy

# Disable auto-start
sudo systemctl disable roxy
```

### Update Roxy

```bash
cd ~/bootstrap/Roxy
git pull
sudo systemctl restart roxy
```

## 🔒 Security Best Practices

### 1. Restrict SSH Access

```bash
# Limit to your IP
gcloud compute firewall-rules update allow-ssh-roxy \
  --source-ranges=YOUR_IP/32
```

### 2. Use Service Account

Instead of storing credentials in .env:

```bash
# Store in GCP Secret Manager
gcloud secrets create roxy-anthropic-key --data-file=-
# Enter your key, then Ctrl+D

# Grant VM access to secrets
gcloud secrets add-iam-policy-binding roxy-anthropic-key \
  --member=serviceAccount:YOUR_VM_SERVICE_ACCOUNT \
  --role=roles/secretmanager.secretAccessor
```

### 3. Enable OS Login

```bash
gcloud compute instances add-metadata roxy-monitor \
  --metadata enable-oslogin=TRUE
```

### 4. Set Up Firewall Rules

```bash
# Only allow SSH from your IP
gcloud compute firewall-rules create roxy-ssh-restricted \
  --allow=tcp:22 \
  --source-ranges=YOUR_IP/32 \
  --target-tags=roxy-monitor
```

## 💰 Cost Optimization

### Auto-Shutdown at Night

```bash
# Add to crontab
crontab -e

# Add line (shutdown 11 PM - 6 AM if not needed)
0 23 * * * sudo systemctl stop roxy && sudo docker-compose down
0 6 * * * sudo docker-compose up -d && sudo systemctl start roxy
```

### Use Preemptible VM

Saves ~80% on cost:

```bash
gcloud compute instances create roxy-monitor \
  --preemptible \
  --machine-type=e2-small \
  # ... other options
```

Note: VM can be stopped by GCP with 30s notice. Use for non-critical monitoring.

### Reduce Processing

In `config_advanced.yaml`:
```yaml
processing:
  fps: 0.5  # Analyze every 2 seconds instead of 1

analyzers:
  - type: presence_detection
    check_interval_seconds: 120  # Check every 2 minutes
```

## 🐛 Troubleshooting

### Can't Connect to Cameras

```bash
# Test Wyze Bridge
docker exec -it wyze-bridge /bin/sh
# Check if cameras listed

# Test RTSP stream
docker exec -it wyze-bridge ffmpeg -i rtsp://localhost:8554/camera-name -frames:v 1 test.jpg
```

### Service Won't Start

```bash
# Check service logs
sudo journalctl -u roxy -n 50

# Check permissions
ls -la ~/bootstrap/Roxy/

# Test manually
cd ~/bootstrap/Roxy
python3 roxy_monitor.py
```

### Out of Memory

```bash
# Check memory usage
free -h
docker stats

# Add swap
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### API Rate Limits

Check `config_advanced.yaml`:
```yaml
processing:
  fps: 0.5  # Reduce from 1 to 0.5

analyzers:
  - type: presence_detection
    check_interval_seconds: 120  # Increase interval
```

## 📈 Monitoring the System

### Set Up Uptime Monitoring

```bash
# Install monitoring agent
curl -sSO https://dl.google.com/cloudagents/add-google-cloud-ops-agent-repo.sh
sudo bash add-google-cloud-ops-agent-repo.sh --also-install
```

### Add Health Check Endpoint

Edit `roxy_monitor.py` to add HTTP health endpoint, or use systemd:

```bash
# Systemd will auto-restart on failure (already configured in roxy.service)
# Check restart count
systemctl show roxy | grep NRestarts
```

### Email Alerts on Failure

```bash
# Install mailutils
sudo apt-get install -y mailutils

# Edit service to send email on failure
sudo systemctl edit roxy
```

Add:
```ini
[Unit]
OnFailure=failure-email@%n.service
```

## 🔄 Backup and Recovery

### Backup Configuration

```bash
# Backup script
cat > ~/backup_roxy.sh << 'EOF'
#!/bin/bash
tar -czf ~/roxy-backup-$(date +%Y%m%d).tar.gz \
  ~/bootstrap/Roxy/.env \
  ~/bootstrap/Roxy/config_advanced.yaml \
  ~/bootstrap/Roxy/alerts/
EOF

chmod +x ~/backup_roxy.sh

# Add to crontab (daily backup)
crontab -e
# Add: 0 2 * * * ~/backup_roxy.sh
```

### Sync to GCS

```bash
# Install gsutil
sudo apt-get install google-cloud-sdk

# Sync alerts to bucket
gsutil -m rsync -r ~/bootstrap/Roxy/alerts/ gs://YOUR_BUCKET/roxy-alerts/
```

## 🎓 Next Steps

1. ✅ VM created and running
2. ✅ Wyze Bridge connected
3. ✅ Roxy monitoring started
4. ⏭️ Test notifications
5. ⏭️ Tune motion detection
6. ⏭️ Add monitoring dashboards
7. ⏭️ Set up automated backups

## 📞 Getting Help

- **GCP Issues**: Check [GCP Documentation](https://cloud.google.com/docs)
- **Docker Issues**: `docker logs <container>`
- **Roxy Issues**: `sudo journalctl -u roxy -f`

---

**Ready to deploy?** Run the automated setup script or follow the manual steps above!
