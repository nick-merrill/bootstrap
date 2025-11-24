#!/bin/bash
set -e

# Roxy VM Setup Script
# Run this on your GCP VM after SSH-ing in

echo "========================================"
echo "   Roxy Monitor - VM Setup Script"
echo "========================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get current user
CURRENT_USER=$(whoami)
HOME_DIR=$(eval echo ~$CURRENT_USER)

echo -e "${GREEN}Setting up for user: $CURRENT_USER${NC}"
echo -e "${GREEN}Home directory: $HOME_DIR${NC}"
echo ""

# Update system
echo -e "${YELLOW}[1/8] Updating system...${NC}"
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker
echo -e "${YELLOW}[2/8] Installing Docker...${NC}"
if ! command -v docker &> /dev/null; then
    sudo apt-get install -y docker.io docker-compose
    sudo systemctl enable docker
    sudo systemctl start docker
    sudo usermod -aG docker $CURRENT_USER
    echo -e "${GREEN}Docker installed!${NC}"
else
    echo -e "${GREEN}Docker already installed${NC}"
fi

# Install Python and dependencies
echo -e "${YELLOW}[3/8] Installing Python dependencies...${NC}"
sudo apt-get install -y python3 python3-pip git libgl1-mesa-glx

# Install system tools
echo -e "${YELLOW}[4/8] Installing system tools...${NC}"
sudo apt-get install -y htop tmux vim curl wget

# Clone repository (or use existing)
echo -e "${YELLOW}[5/8] Setting up Roxy repository...${NC}"
REPO_DIR="$HOME_DIR/bootstrap"

if [ ! -d "$REPO_DIR" ]; then
    echo "Enter your repository URL (or press Enter to skip):"
    read REPO_URL

    if [ -n "$REPO_URL" ]; then
        git clone "$REPO_URL" "$REPO_DIR"
    else
        echo -e "${YELLOW}Skipping repository clone. You'll need to upload files manually.${NC}"
        mkdir -p "$REPO_DIR/Roxy"
    fi
else
    echo -e "${GREEN}Repository directory already exists${NC}"
    cd "$REPO_DIR"
    git pull || true
fi

cd "$REPO_DIR/Roxy"

# Install Python requirements
echo -e "${YELLOW}[6/8] Installing Python packages...${NC}"
pip3 install -r requirements.txt

# Set up environment file
echo -e "${YELLOW}[7/8] Configuring environment...${NC}"
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${YELLOW}Created .env file. You need to edit it with your credentials:${NC}"
    echo "  nano .env"
    echo ""
fi

# Set up Docker Compose
echo -e "${YELLOW}[8/8] Setting up Docker Compose...${NC}"
cd deployment

# Update docker-compose .env if needed
if [ ! -f .env ]; then
    ln -s ../.env .env
fi

# Start Wyze Bridge
echo -e "${YELLOW}Starting Wyze Bridge...${NC}"
docker-compose up -d wyze-bridge

# Wait for Wyze Bridge to start
echo -e "${YELLOW}Waiting for Wyze Bridge to initialize (30 seconds)...${NC}"
sleep 30

# Check Wyze Bridge logs
echo -e "${GREEN}Wyze Bridge logs:${NC}"
docker logs wyze-bridge --tail 20

# Set up systemd service
echo -e "${YELLOW}Setting up systemd service...${NC}"
SERVICE_FILE="$REPO_DIR/Roxy/deployment/roxy.service"

# Update service file with current user
sed "s/YOUR_USERNAME/$CURRENT_USER/g" "$SERVICE_FILE" > /tmp/roxy.service

# Copy to systemd
sudo cp /tmp/roxy.service /etc/systemd/system/roxy.service
sudo systemctl daemon-reload

echo ""
echo -e "${GREEN}========================================"
echo "   Setup Complete!"
echo "========================================${NC}"
echo ""
echo "Next steps:"
echo ""
echo "1. Edit configuration:"
echo "   cd $REPO_DIR/Roxy"
echo "   nano .env"
echo "   nano config_advanced.yaml"
echo ""
echo "2. Check Wyze Bridge cameras:"
echo "   docker logs wyze-bridge"
echo ""
echo "3. Test Roxy manually:"
echo "   python3 roxy_monitor.py"
echo ""
echo "4. Start Roxy service:"
echo "   sudo systemctl enable roxy"
echo "   sudo systemctl start roxy"
echo ""
echo "5. View logs:"
echo "   sudo journalctl -u roxy -f"
echo ""
echo -e "${YELLOW}Note: You may need to logout/login for docker group changes to take effect${NC}"
echo ""
