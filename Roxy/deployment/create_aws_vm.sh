#!/bin/bash
set -e

# Automated AWS EC2 NixOS Deployment for Roxy Monitor

echo "========================================"
echo "   Roxy Monitor - AWS EC2 Deployment"
echo "========================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default values
DEFAULT_REGION="us-east-1"
DEFAULT_INSTANCE_TYPE="t3.small"
DEFAULT_INSTANCE_NAME="roxy-monitor"
DEFAULT_KEY_NAME="roxy-key"

# Prompt for configuration
echo -e "${BLUE}AWS Configuration${NC}"
echo ""

read -p "AWS Region [$DEFAULT_REGION]: " AWS_REGION
AWS_REGION=${AWS_REGION:-$DEFAULT_REGION}

read -p "Instance name [$DEFAULT_INSTANCE_NAME]: " INSTANCE_NAME
INSTANCE_NAME=${INSTANCE_NAME:-$DEFAULT_INSTANCE_NAME}

read -p "SSH Key Pair name [$DEFAULT_KEY_NAME]: " KEY_NAME
KEY_NAME=${KEY_NAME:-$DEFAULT_KEY_NAME}

echo ""
echo -e "${BLUE}Instance Type Selection:${NC}"
echo "  1) t3.micro   (2 vCPU, 1 GB RAM)  - ~$7/month  - 1-2 cameras"
echo "  2) t3.small   (2 vCPU, 2 GB RAM)  - ~$15/month - 3-5 cameras (recommended)"
echo "  3) t3.medium  (2 vCPU, 4 GB RAM)  - ~$30/month - 6+ cameras"
read -p "Select instance type [2]: " TYPE_CHOICE

case $TYPE_CHOICE in
    1) INSTANCE_TYPE="t3.micro" ;;
    3) INSTANCE_TYPE="t3.medium" ;;
    *) INSTANCE_TYPE="t3.small" ;;
esac

echo ""
echo -e "${YELLOW}Configuration:${NC}"
echo "  Region: $AWS_REGION"
echo "  Instance Name: $INSTANCE_NAME"
echo "  Instance Type: $INSTANCE_TYPE"
echo "  Key Pair: $KEY_NAME"
echo ""
read -p "Create EC2 instance with these settings? [y/N]: " CONFIRM

if [[ ! $CONFIRM =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

# Check if key pair exists
echo -e "${YELLOW}Checking SSH key pair...${NC}"
if ! aws ec2 describe-key-pairs --key-names $KEY_NAME --region $AWS_REGION &>/dev/null; then
    echo -e "${RED}Key pair '$KEY_NAME' not found!${NC}"
    read -p "Create new key pair? [y/N]: " CREATE_KEY

    if [[ $CREATE_KEY =~ ^[Yy]$ ]]; then
        echo "Creating key pair..."
        mkdir -p ~/.ssh
        aws ec2 create-key-pair \
            --key-name $KEY_NAME \
            --region $AWS_REGION \
            --query 'KeyMaterial' \
            --output text > ~/.ssh/${KEY_NAME}.pem
        chmod 400 ~/.ssh/${KEY_NAME}.pem
        echo -e "${GREEN}Key pair created: ~/.ssh/${KEY_NAME}.pem${NC}"
    else
        echo "Please create a key pair first:"
        echo "  aws ec2 create-key-pair --key-name $KEY_NAME --region $AWS_REGION"
        exit 1
    fi
fi

# Get NixOS AMI
echo -e "${YELLOW}Finding NixOS AMI...${NC}"

# NixOS AMI IDs (24.05 stable)
case $AWS_REGION in
    us-east-1) NIXOS_AMI="ami-0c55b159cbfafe1f0" ;;
    us-west-2) NIXOS_AMI="ami-0d1cd67c26f5fca19" ;;
    eu-west-1) NIXOS_AMI="ami-0d2a4a5d69e46ea0b" ;;
    *)
        echo "Searching for NixOS AMI in $AWS_REGION..."
        NIXOS_AMI=$(aws ec2 describe-images \
            --region $AWS_REGION \
            --owners 080433136561 \
            --filters "Name=name,Values=nixos/24.05*" \
            --query 'sort_by(Images, &CreationDate)[-1].ImageId' \
            --output text)

        if [ -z "$NIXOS_AMI" ]; then
            echo -e "${RED}No NixOS AMI found in $AWS_REGION${NC}"
            exit 1
        fi
        ;;
esac

echo "Using NixOS AMI: $NIXOS_AMI"

# Create security group
echo -e "${YELLOW}Creating security group...${NC}"
SG_NAME="roxy-sg-$(date +%s)"

SG_ID=$(aws ec2 create-security-group \
    --group-name $SG_NAME \
    --description "Security group for Roxy monitor" \
    --region $AWS_REGION \
    --query 'GroupId' \
    --output text) || true

if [ -z "$SG_ID" ]; then
    echo -e "${RED}Failed to create security group${NC}"
    exit 1
fi

echo "Security Group ID: $SG_ID"

# Allow SSH from current IP
MY_IP=$(curl -s ifconfig.me)
echo "Adding SSH rule for your IP: $MY_IP"

aws ec2 authorize-security-group-ingress \
    --group-id $SG_ID \
    --region $AWS_REGION \
    --protocol tcp \
    --port 22 \
    --cidr ${MY_IP}/32

# Create user data script
cat > /tmp/nixos-userdata.sh << 'EOF'
#!/bin/bash
set -e

# Create roxy user
if ! id roxy &>/dev/null; then
    useradd -m -G wheel roxy
fi

# Clone repository
mkdir -p /opt
cd /opt
git clone https://github.com/nick-merrill/bootstrap.git || true
mkdir -p /opt/roxy
cp -r bootstrap/Roxy/* /opt/roxy/ || true
chown -R roxy:users /opt/roxy

# Install Python packages
cd /opt/roxy
nix-env -iA nixos.python311Packages.pip || true
python3 -m pip install --user -r requirements.txt || true

# Create .env
cp .env.example .env 2>/dev/null || true
chmod 600 .env
chown roxy:users .env

echo "Setup complete at $(date)" > /var/log/roxy-setup.log
EOF

# Launch instance
echo -e "${YELLOW}Launching EC2 instance...${NC}"

INSTANCE_ID=$(aws ec2 run-instances \
    --image-id $NIXOS_AMI \
    --instance-type $INSTANCE_TYPE \
    --key-name $KEY_NAME \
    --security-group-ids $SG_ID \
    --region $AWS_REGION \
    --user-data file:///tmp/nixos-userdata.sh \
    --block-device-mappings '[{"DeviceName":"/dev/xvda","Ebs":{"VolumeSize":20,"VolumeType":"gp3"}}]' \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$INSTANCE_NAME}]" \
    --query 'Instances[0].InstanceId' \
    --output text)

if [ -z "$INSTANCE_ID" ]; then
    echo -e "${RED}Failed to launch instance${NC}"
    exit 1
fi

echo "Instance ID: $INSTANCE_ID"

# Wait for instance to be running
echo -e "${YELLOW}Waiting for instance to start...${NC}"
aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region $AWS_REGION

# Get public IP
PUBLIC_IP=$(aws ec2 describe-instances \
    --instance-ids $INSTANCE_ID \
    --region $AWS_REGION \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text)

echo ""
echo -e "${GREEN}========================================"
echo "   Instance Created Successfully!"
echo "========================================${NC}"
echo ""
echo "  Instance ID: $INSTANCE_ID"
echo "  Public IP: $PUBLIC_IP"
echo "  Region: $AWS_REGION"
echo "  SSH Key: ~/.ssh/${KEY_NAME}.pem"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo ""
echo "1. Wait 60 seconds for instance to initialize:"
echo "   sleep 60"
echo ""
echo "2. SSH into the instance:"
echo "   ssh -i ~/.ssh/${KEY_NAME}.pem root@$PUBLIC_IP"
echo ""
echo "3. Configure NixOS:"
echo "   sudo cp /opt/roxy/deployment/nixos-configuration.nix /etc/nixos/configuration.nix"
echo "   sudo nano /etc/nixos/configuration.nix  # Add your SSH key"
echo "   sudo nixos-rebuild switch"
echo ""
echo "4. Configure Roxy:"
echo "   cd /opt/roxy"
echo "   sudo nano .env  # Add credentials"
echo "   sudo nano config_advanced.yaml  # Configure cameras"
echo ""
echo "5. Start services:"
echo "   sudo systemctl start wyze-bridge"
echo "   sudo systemctl start roxy-monitor"
echo ""
echo -e "${YELLOW}Estimated monthly cost: \$${NC}"
case $INSTANCE_TYPE in
    t3.micro) echo "~\$7" ;;
    t3.small) echo "~\$15" ;;
    t3.medium) echo "~\$30" ;;
esac
echo ""
echo -e "${GREEN}Deployment complete!${NC}"
