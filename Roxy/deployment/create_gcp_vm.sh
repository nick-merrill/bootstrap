#!/bin/bash
set -e

# GCP VM Creation Script for Roxy Monitor

echo "========================================"
echo "   Create GCP VM for Roxy Monitor"
echo "========================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default values
DEFAULT_PROJECT_ID=$(gcloud config get-value project 2>/dev/null || echo "")
DEFAULT_ZONE="us-central1-a"
DEFAULT_MACHINE_TYPE="e2-medium"
DEFAULT_INSTANCE_NAME="roxy-monitor"

# Prompt for configuration
echo -e "${BLUE}GCP Configuration${NC}"
echo ""

read -p "Project ID [$DEFAULT_PROJECT_ID]: " PROJECT_ID
PROJECT_ID=${PROJECT_ID:-$DEFAULT_PROJECT_ID}

if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Error: Project ID is required${NC}"
    exit 1
fi

read -p "Instance name [$DEFAULT_INSTANCE_NAME]: " INSTANCE_NAME
INSTANCE_NAME=${INSTANCE_NAME:-$DEFAULT_INSTANCE_NAME}

read -p "Zone [$DEFAULT_ZONE]: " ZONE
ZONE=${ZONE:-$DEFAULT_ZONE}

echo ""
echo -e "${BLUE}Machine Type Selection:${NC}"
echo "  1) e2-micro   (2 vCPU, 1 GB RAM)  - ~$7/month  - 1-2 cameras"
echo "  2) e2-small   (2 vCPU, 2 GB RAM)  - ~$14/month - 3-5 cameras"
echo "  3) e2-medium  (2 vCPU, 4 GB RAM)  - ~$28/month - 6+ cameras"
read -p "Select machine type [2]: " MACHINE_CHOICE

case $MACHINE_CHOICE in
    1) MACHINE_TYPE="e2-micro" ;;
    3) MACHINE_TYPE="e2-medium" ;;
    *) MACHINE_TYPE="e2-small" ;;
esac

read -p "Use preemptible instance? (80% cheaper, can be stopped by GCP) [y/N]: " USE_PREEMPTIBLE

echo ""
echo -e "${YELLOW}Configuration:${NC}"
echo "  Project ID: $PROJECT_ID"
echo "  Instance: $INSTANCE_NAME"
echo "  Zone: $ZONE"
echo "  Machine Type: $MACHINE_TYPE"
echo "  Preemptible: ${USE_PREEMPTIBLE:-N}"
echo ""
read -p "Create VM with these settings? [y/N]: " CONFIRM

if [[ ! $CONFIRM =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

# Set project
echo -e "${YELLOW}Setting project...${NC}"
gcloud config set project "$PROJECT_ID"

# Create startup script
STARTUP_SCRIPT='#!/bin/bash
apt-get update
apt-get install -y docker.io docker-compose git python3-pip
systemctl enable docker
systemctl start docker
usermod -aG docker $SUDO_USER
echo "Startup script completed" > /var/log/startup-complete.log
'

# Build create command
CREATE_CMD="gcloud compute instances create $INSTANCE_NAME \
  --zone=$ZONE \
  --machine-type=$MACHINE_TYPE \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=20GB \
  --boot-disk-type=pd-standard \
  --tags=roxy-monitor \
  --metadata=startup-script='$STARTUP_SCRIPT'"

# Add preemptible flag if requested
if [[ $USE_PREEMPTIBLE =~ ^[Yy]$ ]]; then
    CREATE_CMD="$CREATE_CMD --preemptible"
fi

# Create VM
echo -e "${YELLOW}Creating VM instance...${NC}"
eval $CREATE_CMD

# Wait for VM to be ready
echo -e "${YELLOW}Waiting for VM to start...${NC}"
sleep 10

# Get external IP
EXTERNAL_IP=$(gcloud compute instances describe $INSTANCE_NAME \
    --zone=$ZONE \
    --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

echo ""
echo -e "${GREEN}========================================"
echo "   VM Created Successfully!"
echo "========================================${NC}"
echo ""
echo "  Instance: $INSTANCE_NAME"
echo "  Zone: $ZONE"
echo "  External IP: $EXTERNAL_IP"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo ""
echo "1. Wait for startup script to complete (~2 minutes):"
echo "   gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command='cat /var/log/startup-complete.log'"
echo ""
echo "2. SSH into the VM:"
echo "   gcloud compute ssh $INSTANCE_NAME --zone=$ZONE"
echo ""
echo "3. Run the setup script:"
echo "   wget https://raw.githubusercontent.com/YOUR_REPO/bootstrap/main/Roxy/deployment/setup_vm.sh"
echo "   chmod +x setup_vm.sh"
echo "   ./setup_vm.sh"
echo ""
echo "Or manually clone and setup:"
echo "   git clone https://github.com/YOUR_REPO/bootstrap.git"
echo "   cd bootstrap/Roxy/deployment"
echo "   ./setup_vm.sh"
echo ""
echo -e "${YELLOW}Estimated monthly cost: \$${NC}"
case $MACHINE_TYPE in
    e2-micro) echo "~\$7" ;;
    e2-small) echo "~\$14" ;;
    e2-medium) echo "~\$28" ;;
esac
echo ""

# Offer to create firewall rule
read -p "Create firewall rule to allow SSH? [y/N]: " CREATE_FIREWALL

if [[ $CREATE_FIREWALL =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Creating firewall rule...${NC}"

    read -p "Restrict to your current IP? [Y/n]: " RESTRICT_IP

    if [[ ! $RESTRICT_IP =~ ^[Nn]$ ]]; then
        CURRENT_IP=$(curl -s ifconfig.me)
        SOURCE_RANGE="$CURRENT_IP/32"
        echo "Restricting to: $SOURCE_RANGE"
    else
        SOURCE_RANGE="0.0.0.0/0"
        echo -e "${YELLOW}Warning: Allowing SSH from anywhere${NC}"
    fi

    gcloud compute firewall-rules create allow-ssh-roxy \
        --allow=tcp:22 \
        --target-tags=roxy-monitor \
        --source-ranges=$SOURCE_RANGE \
        --description="SSH access for Roxy monitor" \
        || echo -e "${YELLOW}Firewall rule may already exist${NC}"
fi

echo ""
echo -e "${GREEN}Setup complete!${NC}"
echo ""
