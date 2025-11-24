# AWS EC2 Quick Commands for Roxy

Essential AWS CLI commands for deploying and managing Roxy on EC2 with NixOS.

## 🚀 Quick Deploy (Copy-Paste)

### Option 1: Run the Script

```bash
cd Roxy/deployment
./create_aws_vm.sh
```

### Option 2: Manual Commands

#### Step 1: Configure AWS

```bash
aws configure
# Enter your AWS credentials
```

#### Step 2: Set Variables

```bash
export AWS_REGION="us-east-1"
export KEY_NAME="roxy-key"
export INSTANCE_TYPE="t3.small"
export INSTANCE_NAME="roxy-monitor"
```

#### Step 3: Create SSH Key (if needed)

```bash
aws ec2 create-key-pair \
  --key-name $KEY_NAME \
  --region $AWS_REGION \
  --query 'KeyMaterial' \
  --output text > ~/.ssh/${KEY_NAME}.pem

chmod 400 ~/.ssh/${KEY_NAME}.pem
```

#### Step 4: Create Security Group

```bash
SG_ID=$(aws ec2 create-security-group \
  --group-name roxy-sg \
  --description "Roxy monitor security group" \
  --region $AWS_REGION \
  --query 'GroupId' \
  --output text)

# Allow SSH from your IP
MY_IP=$(curl -s ifconfig.me)
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --region $AWS_REGION \
  --protocol tcp \
  --port 22 \
  --cidr ${MY_IP}/32
```

#### Step 5: Find NixOS AMI

```bash
# For us-east-1 (use corresponding AMI for other regions)
export NIXOS_AMI="ami-0c55b159cbfafe1f0"

# Or search for latest:
aws ec2 describe-images \
  --region $AWS_REGION \
  --owners 080433136561 \
  --filters "Name=name,Values=nixos/24.05*" \
  --query 'sort_by(Images, &CreationDate)[-1].ImageId' \
  --output text
```

#### Step 6: Launch Instance

```bash
INSTANCE_ID=$(aws ec2 run-instances \
  --image-id $NIXOS_AMI \
  --instance-type $INSTANCE_TYPE \
  --key-name $KEY_NAME \
  --security-group-ids $SG_ID \
  --region $AWS_REGION \
  --block-device-mappings '[{"DeviceName":"/dev/xvda","Ebs":{"VolumeSize":20,"VolumeType":"gp3"}}]' \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$INSTANCE_NAME}]" \
  --query 'Instances[0].InstanceId' \
  --output text)

echo "Instance ID: $INSTANCE_ID"
```

#### Step 7: Get Public IP

```bash
# Wait for instance to start
aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region $AWS_REGION

# Get IP
PUBLIC_IP=$(aws ec2 describe-instances \
  --instance-ids $INSTANCE_ID \
  --region $AWS_REGION \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text)

echo "Public IP: $PUBLIC_IP"
```

#### Step 8: SSH and Configure

```bash
# Wait for SSH to be ready
sleep 60

# SSH in
ssh -i ~/.ssh/${KEY_NAME}.pem root@$PUBLIC_IP

# On the instance:
# 1. Copy NixOS config
sudo cp /opt/roxy/deployment/nixos-configuration.nix /etc/nixos/configuration.nix

# 2. Add your SSH public key to the config
sudo nano /etc/nixos/configuration.nix
# Find: users.users.roxy.openssh.authorizedKeys.keys
# Add: your SSH public key

# 3. Rebuild NixOS
sudo nixos-rebuild switch

# 4. Configure Roxy
cd /opt/roxy
sudo nano .env  # Add credentials
sudo nano config_advanced.yaml  # Configure cameras

# 5. Start services
sudo systemctl enable --now wyze-bridge
sudo systemctl enable --now roxy-monitor
```

## 📊 Management Commands

### Check Instance Status

```bash
aws ec2 describe-instances \
  --instance-ids $INSTANCE_ID \
  --region $AWS_REGION \
  --query 'Reservations[0].Instances[0].State.Name'
```

### Stop Instance

```bash
aws ec2 stop-instances \
  --instance-ids $INSTANCE_ID \
  --region $AWS_REGION
```

### Start Instance

```bash
aws ec2 start-instances \
  --instance-ids $INSTANCE_ID \
  --region $AWS_REGION

# Get new IP (changes after stop/start)
aws ec2 describe-instances \
  --instance-ids $INSTANCE_ID \
  --region $AWS_REGION \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text
```

### Terminate Instance

```bash
aws ec2 terminate-instances \
  --instance-ids $INSTANCE_ID \
  --region $AWS_REGION
```

### View Console Output

```bash
aws ec2 get-console-output \
  --instance-id $INSTANCE_ID \
  --region $AWS_REGION
```

## 🔧 On-Instance Commands

### View Logs

```bash
# Roxy logs
sudo journalctl -u roxy-monitor -f

# Wyze Bridge logs
sudo docker logs -f wyze-bridge

# System logs
sudo journalctl -xe
```

### Restart Services

```bash
sudo systemctl restart roxy-monitor
sudo systemctl restart wyze-bridge
```

### Update Roxy

```bash
cd /opt/roxy
sudo git pull
sudo systemctl restart roxy-monitor
```

### Update NixOS

```bash
# Update and rebuild
sudo nixos-rebuild switch --upgrade

# Or rollback if issues
sudo nixos-rebuild switch --rollback
```

## 💾 Backup Commands

### Create AMI Snapshot

```bash
aws ec2 create-image \
  --instance-id $INSTANCE_ID \
  --region $AWS_REGION \
  --name "roxy-backup-$(date +%Y%m%d)" \
  --description "Roxy monitor backup"
```

### Backup to S3

```bash
# On instance
aws s3 sync /opt/roxy/ s3://my-backup-bucket/roxy/
```

## 🔒 Security Commands

### Update Security Group

```bash
# Allow additional IP
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --region $AWS_REGION \
  --protocol tcp \
  --port 22 \
  --cidr NEW_IP/32

# Revoke old IP
aws ec2 revoke-security-group-ingress \
  --group-id $SG_ID \
  --region $AWS_REGION \
  --protocol tcp \
  --port 22 \
  --cidr OLD_IP/32
```

### Check Security Group Rules

```bash
aws ec2 describe-security-groups \
  --group-ids $SG_ID \
  --region $AWS_REGION
```

## 📈 Monitoring Commands

### Get Instance Metrics

```bash
# CPU utilization
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=$INSTANCE_ID \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average \
  --region $AWS_REGION
```

### Create CloudWatch Alarm

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name roxy-high-cpu \
  --alarm-description "Alert when CPU > 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/EC2 \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=InstanceId,Value=$INSTANCE_ID \
  --evaluation-periods 2 \
  --region $AWS_REGION
```

## 🔍 Troubleshooting Commands

### Can't SSH

```bash
# Check if running
aws ec2 describe-instance-status \
  --instance-ids $INSTANCE_ID \
  --region $AWS_REGION

# Check security group
aws ec2 describe-security-groups \
  --group-ids $SG_ID \
  --region $AWS_REGION

# Get console output
aws ec2 get-console-output \
  --instance-id $INSTANCE_ID \
  --region $AWS_REGION
```

### Check Setup Status

```bash
# SSH and check log
ssh -i ~/.ssh/${KEY_NAME}.pem root@$PUBLIC_IP 'cat /var/log/roxy-setup.log'
```

## 💰 Cost Management

### Estimate Costs

```bash
# Get cost estimate for last 7 days
aws ce get-cost-and-usage \
  --time-period Start=$(date -d '7 days ago' +%Y-%m-%d),End=$(date +%Y-%m-%d) \
  --granularity DAILY \
  --metrics BlendedCost \
  --group-by Type=DIMENSION,Key=SERVICE
```

### Set Billing Alert

```bash
# Create SNS topic
aws sns create-topic --name billing-alerts

# Subscribe to topic
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:ACCOUNT_ID:billing-alerts \
  --protocol email \
  --notification-endpoint your-email@example.com
```

## 🎯 Quick Reference

| Task | Command |
|------|---------|
| SSH to instance | `ssh -i ~/.ssh/${KEY_NAME}.pem root@$PUBLIC_IP` |
| View Roxy logs | `sudo journalctl -u roxy-monitor -f` |
| Restart Roxy | `sudo systemctl restart roxy-monitor` |
| Update Roxy | `cd /opt/roxy && sudo git pull && sudo systemctl restart roxy-monitor` |
| Stop instance | `aws ec2 stop-instances --instance-ids $INSTANCE_ID` |
| Start instance | `aws ec2 start-instances --instance-ids $INSTANCE_ID` |

---

**Need help?** See [AWS_DEPLOYMENT.md](./AWS_DEPLOYMENT.md) for detailed documentation.
