# Wyze Bridge with Two-Factor Authentication (2FA)

If you have 2FA enabled on your Wyze account (recommended for security!), you have a few options to make docker-wyze-bridge work.

## Option 1: TOTP Key (Recommended)

This is the most automated approach - the bridge generates its own 2FA codes.

### Steps:

1. **Get your TOTP key from Wyze:**
   - Open Wyze app → Account → Two-Factor Authentication
   - Tap "Set Up" or "Change"
   - Choose "Authenticator App"
   - Instead of scanning the QR code, tap "Can't scan?"
   - **Copy the secret key** (long string of letters/numbers)

2. **Add to your .env file:**
   ```bash
   WYZE_EMAIL=your-email@example.com
   WYZE_PASSWORD=your-password
   TOTP_KEY=your_totp_secret_key_here
   ```

3. **Update docker-compose.yml:**
   ```yaml
   wyze-bridge:
     image: mrlt8/wyze-bridge:latest
     environment:
       - WYZE_EMAIL=${WYZE_EMAIL}
       - WYZE_PASSWORD=${WYZE_PASSWORD}
       - TOTP_KEY=${TOTP_KEY}  # Add this line
       # ... other settings
   ```

4. **Restart:**
   ```bash
   docker-compose down
   docker-compose up -d
   ```

The bridge will now generate 2FA codes automatically!

## Option 2: API Key/Token (Alternative)

Use Wyze API keys instead of email/password.

### Steps:

1. **Generate API Key:**
   - Visit: https://developer-api-console.wyze.com/
   - Sign in with your Wyze account
   - Create a new API key

2. **Update .env:**
   ```bash
   # Instead of WYZE_EMAIL and WYZE_PASSWORD, use:
   WYZE_API_KEY=your_api_key
   WYZE_API_ID=your_api_id
   ```

3. **Update docker-compose.yml:**
   ```yaml
   wyze-bridge:
     environment:
       - WYZE_API_KEY=${WYZE_API_KEY}
       - WYZE_API_ID=${WYZE_API_ID}
       # Don't include WYZE_EMAIL or WYZE_PASSWORD
   ```

**Note:** API access may have limitations depending on your Wyze account type.

## Option 3: One-Time Verification Code (Manual)

If you can't get the TOTP key, you can manually enter codes.

### Steps:

1. **First run without TOTP:**
   ```bash
   docker-compose up wyze-bridge
   ```

2. **Watch the logs:**
   ```bash
   docker logs -f wyze-bridge
   ```

3. **When prompted for 2FA code:**
   - Check your authenticator app
   - Enter the code in the bridge console (if interactive mode available)

   OR

   - Set the verification code temporarily:
   ```bash
   docker-compose down
   docker-compose run -e WYZE_2FA_CODE=123456 wyze-bridge
   ```

**Limitation:** This only works temporarily until the session expires.

## Option 4: Disable 2FA (Not Recommended)

⚠️ **Security Warning:** Only do this if you understand the risks.

1. Wyze App → Account → Two-Factor Authentication → Turn Off
2. Use bridge normally with email/password
3. Consider re-enabling 2FA after setup if needed

## Recommended Setup for GCP Deployment

Update your deployment files:

### Update `.env`:
```bash
# Wyze Configuration with 2FA
WYZE_EMAIL=your-email@example.com
WYZE_PASSWORD=your-password
TOTP_KEY=your_totp_secret_key

# Alternative: API Key method
# WYZE_API_KEY=your_api_key
# WYZE_API_ID=your_api_id
```

### Update `docker-compose.yml`:
```yaml
wyze-bridge:
  image: mrlt8/wyze-bridge:latest
  container_name: wyze-bridge
  restart: unless-stopped
  ports:
    - "8554:8554"
    - "8888:8888"
  environment:
    - WYZE_EMAIL=${WYZE_EMAIL}
    - WYZE_PASSWORD=${WYZE_PASSWORD}
    - TOTP_KEY=${TOTP_KEY}              # Add this for 2FA
    - QUALITY=${WYZE_QUALITY:-HD120}
    - SNAPSHOT=${WYZE_SNAPSHOT:-API}
    - ON_DEMAND=${WYZE_ON_DEMAND:-False}
  volumes:
    - wyze-bridge-data:/config
  networks:
    - roxy-network
```

## Testing Your Setup

After configuration:

```bash
# Restart the bridge
docker-compose down
docker-compose up -d wyze-bridge

# Check logs for successful connection
docker logs wyze-bridge

# You should see:
# [Camera Name] Connected
# [Another Camera] Connected

# If you see 2FA errors, check your TOTP_KEY
```

## Troubleshooting 2FA Issues

### Error: "Invalid verification code"

**Fix:**
1. Make sure TOTP_KEY is the secret key, not the 6-digit code
2. Check for spaces in the key - remove them
3. Verify time sync on your server:
   ```bash
   sudo apt-get install ntpdate
   sudo ntpdate time.google.com
   ```

### Error: "Too many failed attempts"

**Fix:**
1. Wait 15-30 minutes
2. Try again with correct TOTP_KEY
3. Consider temporarily disabling 2FA, setting up bridge, then re-enabling

### Can't find TOTP secret key

**Fix:**
1. You may need to re-setup 2FA to see the secret
2. Wyze App → Account → 2FA → Change/Reset
3. Choose authenticator app method
4. Tap "Can't scan" to see the secret key

### API Key not working

**Fix:**
1. Verify API key is active in Wyze developer console
2. Check account type supports API access
3. Fall back to TOTP_KEY method

## Complete Example with 2FA

Here's a working example:

**`.env` file:**
```bash
# Wyze with 2FA
WYZE_EMAIL=john@example.com
WYZE_PASSWORD=MySecurePassword123
TOTP_KEY=JBSWY3DPEHPK3PXP

# Other settings
WYZE_QUALITY=HD120
WYZE_ON_DEMAND=False

# Roxy settings
ANTHROPIC_API_KEY=sk-ant-...
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_FROM_NUMBER=+1234567890
TWILIO_TO_NUMBER_1=+1234567890
```

**Start it up:**
```bash
docker-compose up -d wyze-bridge

# Wait 30 seconds for initialization
sleep 30

# Check success
docker logs wyze-bridge | grep -i "connected\|error"
```

You should see your cameras listed as connected!

## Security Best Practices

1. ✅ **Keep 2FA enabled** - Use TOTP_KEY method to work with it
2. ✅ **Use strong passwords** - Even with 2FA
3. ✅ **Secure your .env file**:
   ```bash
   chmod 600 .env
   ```
4. ✅ **Don't commit .env** - Already in .gitignore
5. ✅ **Store secrets in GCP Secret Manager** (advanced):
   ```bash
   gcloud secrets create wyze-totp-key --data-file=-
   # Paste key, then Ctrl+D
   ```

## Reference Links

- docker-wyze-bridge docs: https://github.com/mrlt8/docker-wyze-bridge
- Wyze 2FA setup: https://support.wyze.com/hc/en-us/articles/360031942432
- TOTP standard: https://en.wikipedia.org/wiki/Time-based_One-Time_Password

---

**TL;DR:** Get your TOTP secret key from Wyze app when setting up 2FA, add it to `.env` as `TOTP_KEY`, and the bridge handles everything automatically!
