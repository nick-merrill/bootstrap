#!/bin/bash

# One-Command GCP VM Setup for Roxy
# This creates a VM with everything pre-installed, ready for Claude to configure

# REQUIRED: Set these variables first
PROJECT_ID="your-project-id"
ZONE="us-central1-a"
INSTANCE_NAME="roxy-monitor"
MACHINE_TYPE="e2-small"  # or e2-micro, e2-medium

# Optional: Your GitHub repo (if private, you'll need to provide credentials later)
GITHUB_REPO="https://github.com/nick-merrill/bootstrap.git"

# Create comprehensive startup script
read -r -d '' STARTUP_SCRIPT << 'SCRIPT_EOF'
#!/bin/bash
set -e

echo "=== Roxy VM Setup - Starting ==="

# Update system
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get upgrade -y

# Install Docker
apt-get install -y \
    docker.io \
    docker-compose \
    git \
    python3 \
    python3-pip \
    htop \
    tmux \
    vim \
    curl \
    wget \
    net-tools

# Enable and start Docker
systemctl enable docker
systemctl start docker

# Add default user to docker group
DEFAULT_USER=$(ls /home | head -n 1)
if [ -n "$DEFAULT_USER" ]; then
    usermod -aG docker $DEFAULT_USER
fi

# Install Python packages system-wide
pip3 install --upgrade pip

# Clone repository to /opt for system-wide access
cd /opt
if [ ! -d "bootstrap" ]; then
    git clone GITHUB_REPO_PLACEHOLDER bootstrap || mkdir -p bootstrap/Roxy
fi

cd /opt/bootstrap/Roxy

# Install Python dependencies if requirements.txt exists
if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt
fi

# Create .env from example if it doesn't exist
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    cp .env.example .env
    chmod 600 .env
fi

# Create deployment directory if needed
mkdir -p deployment
cd deployment

# Create docker-compose .env symlink
if [ ! -f ".env" ]; then
    ln -s ../.env .env 2>/dev/null || true
fi

# Set up systemd service if it exists
if [ -f "roxy.service" ]; then
    # Update service file with correct paths and user
    sed "s|YOUR_USERNAME|$DEFAULT_USER|g" roxy.service > /tmp/roxy.service
    sed -i "s|/home/YOUR_USERNAME|/opt|g" /tmp/roxy.service
    cp /tmp/roxy.service /etc/systemd/system/roxy.service
    systemctl daemon-reload
fi

# Create helpful README in home directory
cat > /home/$DEFAULT_USER/SETUP_INSTRUCTIONS.txt << 'EOF'
=== Roxy Monitor Setup Instructions ===

Your VM is ready! Here's what's been installed:
- Docker & Docker Compose
- Python 3 with pip
- Git and dev tools
- Repository cloned to /opt/bootstrap

NEXT STEPS:

1. Configure credentials:
   sudo nano /opt/bootstrap/Roxy/.env

   Required:
   - WYZE_EMAIL
   - WYZE_PASSWORD
   - TOTP_KEY (if 2FA enabled)
   - ANTHROPIC_API_KEY
   - TWILIO credentials

2. Configure cameras:
   sudo nano /opt/bootstrap/Roxy/config_advanced.yaml

3. Start Wyze Bridge:
   cd /opt/bootstrap/Roxy/deployment
   sudo docker-compose up -d wyze-bridge

4. Check cameras connected:
   sudo docker logs wyze-bridge

5. Start Roxy:
   sudo systemctl enable roxy
   sudo systemctl start roxy

6. View logs:
   sudo journalctl -u roxy -f

For detailed help, see:
/opt/bootstrap/Roxy/GCP_DEPLOYMENT.md
EOF

chown $DEFAULT_USER:$DEFAULT_USER /home/$DEFAULT_USER/SETUP_INSTRUCTIONS.txt

# Set permissions
chown -R $DEFAULT_USER:$DEFAULT_USER /opt/bootstrap 2>/dev/null || true

# Create completion marker
echo "Setup completed at $(date)" > /var/log/roxy-setup-complete.log

echo "=== Roxy VM Setup - Complete ==="
SCRIPT_EOF

# Replace GitHub repo placeholder
STARTUP_SCRIPT="${STARTUP_SCRIPT//GITHUB_REPO_PLACEHOLDER/$GITHUB_REPO}"

# Create the VM
echo "Creating GCP VM: $INSTANCE_NAME"
echo "Project: $PROJECT_ID"
echo "Zone: $ZONE"
echo "Machine Type: $MACHINE_TYPE"
echo ""

gcloud compute instances create "$INSTANCE_NAME" \
  --project="$PROJECT_ID" \
  --zone="$ZONE" \
  --machine-type="$MACHINE_TYPE" \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=20GB \
  --boot-disk-type=pd-standard \
  --tags=roxy-monitor \
  --metadata=startup-script="$STARTUP_SCRIPT" \
  --scopes=cloud-platform

echo ""
echo "=== VM Creation Started ==="
echo ""
echo "Waiting for VM to be ready..."
sleep 15

# Get external IP
EXTERNAL_IP=$(gcloud compute instances describe "$INSTANCE_NAME" \
    --zone="$ZONE" \
    --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

echo ""
echo "✅ VM Created Successfully!"
echo ""
echo "Instance Name: $INSTANCE_NAME"
echo "External IP: $EXTERNAL_IP"
echo "Zone: $ZONE"
echo ""
echo "=== Next Steps ==="
echo ""
echo "1. Wait 2-3 minutes for startup script to complete"
echo ""
echo "2. Check startup script status:"
echo "   gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command='cat /var/log/roxy-setup-complete.log'"
echo ""
echo "3. SSH into VM:"
echo "   gcloud compute ssh $INSTANCE_NAME --zone=$ZONE"
echo ""
echo "4. Or provide Claude with SSH access:"
echo "   gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command='sudo cat /opt/bootstrap/Roxy/SETUP_INSTRUCTIONS.txt'"
echo ""
echo "5. Create firewall rule (if needed):"
echo "   gcloud compute firewall-rules create allow-ssh-roxy \\"
echo "     --allow=tcp:22 \\"
echo "     --target-tags=roxy-monitor \\"
echo "     --source-ranges=YOUR_IP/32"
echo ""
