# AWS EC2 Deployment with NixOS

Complete guide to deploy Roxy on AWS EC2 using NixOS for enhanced security and reproducibility.

## 🎯 Why NixOS?

- **Declarative Configuration**: Entire system in one file
- **Reproducible**: Same config = same system
- **Secure by Default**: Easy to harden and audit
- **Atomic Updates**: Rollback if anything breaks
- **Immutable**: No configuration drift

## 📋 Prerequisites

1. **AWS Account** - [Sign up](https://aws.amazon.com/)
2. **AWS CLI** - [Install](https://aws.amazon.com/cli/)
3. **SSH Key Pair** - Create one in AWS Console
4. **Anthropic API Key** - [Get one](https://console.anthropic.com/)
5. **Twilio Account** (optional) - [Sign up](https://www.twilio.com/)

## 🚀 Quick Start

### Step 1: Configure AWS CLI

```bash
aws configure
# Enter your:
# - AWS Access Key ID
# - AWS Secret Access Key
# - Default region (e.g., us-east-1)
# - Output format (json)
```

### Step 2: Create SSH Key Pair (if you don't have one)

```bash
# Create key pair
aws ec2 create-key-pair \
  --key-name roxy-key \
  --query 'KeyMaterial' \
  --output text > ~/.ssh/roxy-key.pem

# Set permissions
chmod 400 ~/.ssh/roxy-key.pem
```

### Step 3: Set Variables

```bash
export AWS_REGION="us-east-1"
export KEY_NAME="roxy-key"
export INSTANCE_TYPE="t3.small"  # or t3.micro, t3.medium
export INSTANCE_NAME="roxy-monitor"
```

### Step 4: Find NixOS AMI

```bash
# Get latest NixOS 24.05 AMI for your region
aws ec2 describe-images \
  --region $AWS_REGION \
  --owners 080433136561 \
  --filters "Name=name,Values=nixos/24.05*" \
  --query 'sort_by(Images, &CreationDate)[-1].ImageId' \
  --output text
```

Or use these pre-found AMIs:

| Region | AMI ID |
|--------|--------|
| us-east-1 | ami-0c55b159cbfafe1f0 |
| us-west-2 | ami-0d1cd67c26f5fca19 |
| eu-west-1 | ami-0d2a4a5d69e46ea0b |

### Step 5: Create Security Group

```bash
# Create security group
SG_ID=$(aws ec2 create-security-group \
  --group-name roxy-security-group \
  --description "Security group for Roxy monitor" \
  --query 'GroupId' \
  --output text)

echo "Security Group ID: $SG_ID"

# Allow SSH from your IP only
MY_IP=$(curl -s ifconfig.me)
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 22 \
  --cidr ${MY_IP}/32

# Optional: Allow RTSP and Wyze Bridge Web UI
# aws ec2 authorize-security-group-ingress \
#   --group-id $SG_ID \
#   --protocol tcp \
#   --port 8554 \
#   --cidr 0.0.0.0/0

# aws ec2 authorize-security-group-ingress \
#   --group-id $SG_ID \
#   --protocol tcp \
#   --port 8888 \
#   --cidr 0.0.0.0/0
```

### Step 6: Create User Data Script

```bash
cat > /tmp/nixos-userdata.sh << 'EOF'
#!/bin/bash
# NixOS initial setup script

# Create roxy user if doesn't exist
if ! id roxy &>/dev/null; then
    useradd -m -G wheel,docker roxy
fi

# Clone repository
mkdir -p /opt/roxy
cd /opt
git clone https://github.com/nick-merrill/bootstrap.git || true
cp -r bootstrap/Roxy/* /opt/roxy/
chown -R roxy:users /opt/roxy

# Install Python packages
cd /opt/roxy
python3 -m pip install --user -r requirements.txt

# Create .env from template
cp .env.example .env
chmod 600 .env
chown roxy:users .env

# Copy NixOS configuration
cp /opt/roxy/deployment/nixos-configuration.nix /etc/nixos/configuration.nix

# Mark as configured
echo "NixOS configured at $(date)" > /var/log/roxy-configured.log
EOF
```

### Step 7: Launch EC2 Instance

```bash
# Set NixOS AMI (update for your region)
export NIXOS_AMI="ami-0c55b159cbfafe1f0"  # us-east-1

# Launch instance
INSTANCE_ID=$(aws ec2 run-instances \
  --image-id $NIXOS_AMI \
  --instance-type $INSTANCE_TYPE \
  --key-name $KEY_NAME \
  --security-group-ids $SG_ID \
  --user-data file:///tmp/nixos-userdata.sh \
  --block-device-mappings '[{"DeviceName":"/dev/xvda","Ebs":{"VolumeSize":20,"VolumeType":"gp3"}}]' \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$INSTANCE_NAME}]" \
  --query 'Instances[0].InstanceId' \
  --output text)

echo "Instance ID: $INSTANCE_ID"
```

### Step 8: Wait for Instance

```bash
echo "Waiting for instance to be running..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID

# Get public IP
PUBLIC_IP=$(aws ec2 describe-instances \
  --instance-ids $INSTANCE_ID \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text)

echo "✅ Instance running!"
echo "Public IP: $PUBLIC_IP"
```

### Step 9: SSH and Configure

```bash
# Wait a bit for system to fully boot
echo "Waiting 60 seconds for NixOS to initialize..."
sleep 60

# SSH into instance
ssh -i ~/.ssh/roxy-key.pem root@$PUBLIC_IP

# Or if user is already created:
ssh -i ~/.ssh/roxy-key.pem roxy@$PUBLIC_IP
```

## 🔧 Post-Installation Configuration

### 1. Update NixOS Configuration

```bash
# On the EC2 instance
sudo nano /etc/nixos/configuration.nix

# Add your SSH public key to:
# users.users.roxy.openssh.authorizedKeys.keys = [ "ssh-rsa ..." ];

# Rebuild NixOS with new configuration
sudo nixos-rebuild switch
```

### 2. Configure Roxy

```bash
cd /opt/roxy

# Edit .env with your credentials
sudo nano .env

# Edit camera configuration
sudo nano config_advanced.yaml
```

### 3. Start Services

```bash
# Start Wyze Bridge
sudo systemctl start wyze-bridge
sudo docker logs -f wyze-bridge

# Start Roxy Monitor
sudo systemctl start roxy-monitor
sudo journalctl -u roxy-monitor -f
```

### 4. Enable Auto-Start

```bash
# Enable services on boot
sudo systemctl enable wyze-bridge
sudo systemctl enable roxy-monitor
```

## 🔒 Security Features Built-In

The NixOS configuration includes:

- ✅ **SSH hardening**: Key-only auth, no root login
- ✅ **Fail2ban**: Auto-ban brute force attempts
- ✅ **Firewall**: Only essential ports open
- ✅ **Service isolation**: NoNewPrivileges, PrivateTmp
- ✅ **Resource limits**: Memory and CPU quotas
- ✅ **Automatic updates**: Security patches applied automatically
- ✅ **Minimal attack surface**: Only necessary packages installed

## 💰 Cost Estimation

### Instance Types

| Type | vCPU | RAM | Monthly Cost* | Use Case |
|------|------|-----|---------------|----------|
| t3.micro | 2 | 1 GB | ~$7 | 1-2 cameras, testing |
| t3.small | 2 | 2 GB | ~$15 | 3-5 cameras (recommended) |
| t3.medium | 2 | 4 GB | ~$30 | 6+ cameras, heavy use |

*Approximate US East costs, may vary by region

### Additional Costs
- **Storage**: ~$2/month for 20GB gp3
- **Data transfer**: Free tier covers most use cases
- **Anthropic API**: ~$0.003 per image
- **Twilio**: ~$0.01 per SMS, ~$0.02 per minute call

## 📊 Managing Your Instance

### View Logs

```bash
# Roxy logs
sudo journalctl -u roxy-monitor -f

# Wyze Bridge logs
sudo docker logs -f wyze-bridge

# System logs
sudo journalctl -xe
```

### Update Roxy

```bash
cd /opt/roxy
sudo git pull
sudo systemctl restart roxy-monitor
```

### Update NixOS

```bash
# Update channel
sudo nix-channel --update

# Rebuild system
sudo nixos-rebuild switch

# Or just security updates
sudo nixos-rebuild switch --upgrade
```

### Rollback if Something Breaks

```bash
# NixOS makes rollbacks easy!
sudo nixos-rebuild switch --rollback

# Or select previous generation at boot
# (GRUB menu shows all previous configurations)
```

## 🛡️ Additional Security Hardening

### 1. Use AWS Systems Manager

Instead of SSH, use AWS Systems Manager Session Manager:

```bash
# Install SSM agent (add to nixos-configuration.nix)
services.amazon-ssm-agent.enable = true;

# Then connect without SSH
aws ssm start-session --target $INSTANCE_ID
```

### 2. Enable CloudWatch Monitoring

```bash
# Add to nixos-configuration.nix
services.amazon-cloudwatch-agent.enable = true;
```

### 3. Use IAM Roles

Create an IAM role for the instance instead of using credentials:

```bash
aws iam create-role --role-name RoxyMonitorRole \
  --assume-role-policy-document file://trust-policy.json

# Attach to instance
aws ec2 associate-iam-instance-profile \
  --instance-id $INSTANCE_ID \
  --iam-instance-profile Name=RoxyMonitorRole
```

### 4. Enable VPC Flow Logs

```bash
# Monitor network traffic for security
aws ec2 create-flow-logs \
  --resource-type Instance \
  --resource-ids $INSTANCE_ID \
  --traffic-type ALL \
  --log-destination-type cloud-watch-logs \
  --log-group-name /aws/ec2/roxy-monitor
```

## 🔄 Backup and Recovery

### Backup Configuration

```bash
# Create AMI snapshot
aws ec2 create-image \
  --instance-id $INSTANCE_ID \
  --name "roxy-monitor-backup-$(date +%Y%m%d)" \
  --description "Roxy monitor backup"

# Backup to S3
aws s3 sync /opt/roxy/ s3://my-bucket/roxy-backup/
```

### Restore from Backup

```bash
# Launch from AMI
aws ec2 run-instances \
  --image-id ami-xxxxx \
  # ... other parameters
```

## 📱 Monitoring and Alerts

### Set Up CloudWatch Alarms

```bash
# CPU alarm
aws cloudwatch put-metric-alarm \
  --alarm-name roxy-high-cpu \
  --alarm-description "Alert when CPU exceeds 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/EC2 \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=InstanceId,Value=$INSTANCE_ID \
  --evaluation-periods 2

# Memory alarm (requires CloudWatch agent)
aws cloudwatch put-metric-alarm \
  --alarm-name roxy-high-memory \
  --metric-name mem_used_percent \
  --threshold 80
```

## 🆘 Troubleshooting

### Can't SSH into instance

```bash
# Check security group
aws ec2 describe-security-groups --group-ids $SG_ID

# Check instance status
aws ec2 describe-instance-status --instance-ids $INSTANCE_ID

# Get system log
aws ec2 get-console-output --instance-id $INSTANCE_ID
```

### NixOS rebuild fails

```bash
# Check syntax
sudo nix-instantiate --parse /etc/nixos/configuration.nix

# Rollback
sudo nixos-rebuild switch --rollback
```

### Service won't start

```bash
# Check service status
sudo systemctl status roxy-monitor

# View detailed logs
sudo journalctl -u roxy-monitor -n 100

# Test manually
cd /opt/roxy
python3 roxy_monitor.py
```

## 📚 Next Steps

1. ✅ Instance created and running
2. ✅ NixOS configured
3. ⏭️ Edit `/opt/roxy/.env` with credentials
4. ⏭️ Configure cameras in `config_advanced.yaml`
5. ⏭️ Start services
6. ⏭️ Test notifications
7. ⏭️ Set up CloudWatch monitoring
8. ⏭️ Create backup AMI

## 🔗 Resources

- [NixOS Manual](https://nixos.org/manual/nixos/stable/)
- [AWS EC2 Documentation](https://docs.aws.amazon.com/ec2/)
- [NixOS Security](https://nixos.wiki/wiki/Security)
- [AWS Security Best Practices](https://aws.amazon.com/security/best-practices/)

---

**Ready to deploy?** Run the commands above and you'll have a secure, reproducible Roxy monitor running on AWS in minutes!
