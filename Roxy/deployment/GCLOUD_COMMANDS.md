# One-Command GCP VM Setup

Copy and run these commands to create a fully configured VM that's ready for setup.

## Option 1: Run the Script (Easiest)

```bash
cd Roxy/deployment

# Edit the variables at the top of the script first:
nano create_vm_auto.sh
# Set: PROJECT_ID, ZONE, INSTANCE_NAME, MACHINE_TYPE

# Run it
./create_vm_auto.sh
```

## Option 2: Direct gcloud Commands (Copy-Paste)

### Step 1: Set Variables

```bash
export PROJECT_ID="your-gcp-project-id"
export ZONE="us-central1-a"
export INSTANCE_NAME="roxy-monitor"
export MACHINE_TYPE="e2-small"
export GITHUB_REPO="https://github.com/nick-merrill/bootstrap.git"
```

### Step 2: Create Startup Script

```bash
cat > /tmp/roxy-startup.sh << 'EOF'
#!/bin/bash
set -e
echo "=== Roxy VM Setup Starting ==="

# Update and install everything
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get upgrade -y
apt-get install -y docker.io docker-compose git python3 python3-pip htop tmux vim curl wget

# Start Docker
systemctl enable docker
systemctl start docker

# Add user to docker group
DEFAULT_USER=$(ls /home | head -n 1)
usermod -aG docker $DEFAULT_USER

# Clone repo
cd /opt
git clone https://github.com/nick-merrill/bootstrap.git || true
cd /opt/bootstrap/Roxy

# Install Python deps
pip3 install -r requirements.txt || true

# Setup .env
cp .env.example .env 2>/dev/null || true
chmod 600 .env

# Setup systemd service
if [ -f "deployment/roxy.service" ]; then
    sed "s|YOUR_USERNAME|$DEFAULT_USER|g" deployment/roxy.service | \
    sed "s|/home/YOUR_USERNAME|/opt|g" > /etc/systemd/system/roxy.service
    systemctl daemon-reload
fi

# Set permissions
chown -R $DEFAULT_USER:$DEFAULT_USER /opt/bootstrap

# Create instructions
cat > /home/$DEFAULT_USER/NEXT_STEPS.txt << 'INNER_EOF'
Roxy VM is ready!

Edit configuration:
  sudo nano /opt/bootstrap/Roxy/.env

Start Wyze Bridge:
  cd /opt/bootstrap/Roxy/deployment
  sudo docker-compose up -d wyze-bridge
  sudo docker logs wyze-bridge

Start Roxy:
  sudo systemctl start roxy
  sudo journalctl -u roxy -f
INNER_EOF

chown $DEFAULT_USER:$DEFAULT_USER /home/$DEFAULT_USER/NEXT_STEPS.txt
echo "Setup complete: $(date)" > /var/log/roxy-ready.log
echo "=== Roxy VM Setup Complete ==="
EOF
```

### Step 3: Create the VM

```bash
gcloud compute instances create "$INSTANCE_NAME" \
  --project="$PROJECT_ID" \
  --zone="$ZONE" \
  --machine-type="$MACHINE_TYPE" \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=20GB \
  --boot-disk-type=pd-standard \
  --tags=roxy-monitor \
  --metadata-from-file=startup-script=/tmp/roxy-startup.sh \
  --scopes=cloud-platform
```

### Step 4: Wait and Check Status

```bash
# Wait for startup to complete (2-3 minutes)
echo "Waiting for VM startup..."
sleep 120

# Check if ready
gcloud compute ssh "$INSTANCE_NAME" --zone="$ZONE" \
  --command='cat /var/log/roxy-ready.log'

# If you see the completion message, you're ready!
```

### Step 5: Get SSH Command for Claude

```bash
# Get the SSH command
echo "SSH into the VM with:"
echo "gcloud compute ssh $INSTANCE_NAME --zone=$ZONE"

# Or get external IP for direct SSH
gcloud compute instances describe "$INSTANCE_NAME" \
  --zone="$ZONE" \
  --format='get(networkInterfaces[0].accessConfigs[0].natIP)'
```

## After VM is Created

### For You to Give Claude SSH Access:

1. **Get the SSH command:**
   ```bash
   gcloud compute ssh roxy-monitor --zone=us-central1-a
   ```

2. **Share this with Claude in the chat:**
   - The instance name
   - The zone
   - Tell Claude to use the Bash tool with gcloud commands

3. **Claude can then:**
   - SSH in using: `gcloud compute ssh roxy-monitor --zone=us-central1-a --command='...'`
   - Edit configuration files
   - Start services
   - Check logs

### Configuration Files Claude Needs to Edit:

1. **`/opt/bootstrap/Roxy/.env`** - Add credentials
2. **`/opt/bootstrap/Roxy/config_advanced.yaml`** - Configure cameras/analyzers

### Commands Claude Will Run:

```bash
# Edit .env
gcloud compute ssh roxy-monitor --zone=us-central1-a --command='sudo nano /opt/bootstrap/Roxy/.env'

# Start Wyze Bridge
gcloud compute ssh roxy-monitor --zone=us-central1-a --command='cd /opt/bootstrap/Roxy/deployment && sudo docker-compose up -d'

# Check cameras
gcloud compute ssh roxy-monitor --zone=us-central1-a --command='sudo docker logs wyze-bridge'

# Start Roxy
gcloud compute ssh roxy-monitor --zone=us-central1-a --command='sudo systemctl start roxy'

# View logs
gcloud compute ssh roxy-monitor --zone=us-central1-a --command='sudo journalctl -u roxy -f'
```

## Optional: Create Firewall Rule

```bash
# Restrict SSH to your IP (recommended)
gcloud compute firewall-rules create allow-ssh-roxy \
  --allow=tcp:22 \
  --target-tags=roxy-monitor \
  --source-ranges=$(curl -s ifconfig.me)/32 \
  --description="SSH access for Roxy monitor"
```

## Machine Type Reference

- `e2-micro` (~$7/month) - 1-2 cameras, minimal
- `e2-small` (~$14/month) - 3-5 cameras, recommended
- `e2-medium` (~$28/month) - 6+ cameras, high performance

## Preemptible (80% cheaper, can be stopped by GCP)

Add `--preemptible` to the create command:

```bash
gcloud compute instances create "$INSTANCE_NAME" \
  --preemptible \
  # ... rest of options
```

## Quick Test

After VM is created:

```bash
# Test connection
gcloud compute ssh roxy-monitor --zone=us-central1-a --command='echo "VM is ready!"'

# Check setup status
gcloud compute ssh roxy-monitor --zone=us-central1-a --command='cat /var/log/roxy-ready.log'

# View next steps
gcloud compute ssh roxy-monitor --zone=us-central1-a --command='cat ~/NEXT_STEPS.txt'
```

---

**Ready to go!** Just set your PROJECT_ID and run the commands. Then share the SSH details with me and I'll complete the configuration.
