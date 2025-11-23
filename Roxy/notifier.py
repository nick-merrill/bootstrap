"""Notification system using Twilio for SMS and voice calls."""

import logging
from typing import Optional, List
from datetime import datetime, timedelta
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TwilioNotifier:
    """Handle notifications via Twilio SMS and voice calls."""

    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        from_number: str,
        to_numbers: List[str]
    ):
        """
        Initialize Twilio notifier.

        Args:
            account_sid: Twilio account SID
            auth_token: Twilio auth token
            from_number: Twilio phone number (from)
            to_numbers: List of phone numbers to notify
        """
        self.client = Client(account_sid, auth_token)
        self.from_number = from_number
        self.to_numbers = to_numbers
        self.last_notification = {}
        self.notification_cooldown_minutes = 15  # Prevent spam

    def send_sms(self, message: str, priority: str = "normal") -> bool:
        """
        Send SMS to all configured numbers.

        Args:
            message: Message to send
            priority: Priority level (affects cooldown)

        Returns:
            True if at least one message sent successfully
        """
        # Check cooldown
        if not self._check_cooldown("sms", priority):
            logger.info("SMS notification skipped due to cooldown")
            return False

        success = False
        for to_number in self.to_numbers:
            try:
                message_obj = self.client.messages.create(
                    body=message,
                    from_=self.from_number,
                    to=to_number
                )
                logger.info(f"SMS sent to {to_number}: {message_obj.sid}")
                success = True
            except TwilioRestException as e:
                logger.error(f"Failed to send SMS to {to_number}: {e}")

        if success:
            self._record_notification("sms")

        return success

    def make_call(self, message: str, priority: str = "high") -> bool:
        """
        Make voice call to all configured numbers.

        Args:
            message: Message to speak (will be converted to TwiML)
            priority: Priority level

        Returns:
            True if at least one call initiated successfully
        """
        # Check cooldown
        if not self._check_cooldown("call", priority):
            logger.info("Voice call skipped due to cooldown")
            return False

        # Create TwiML URL - in production, you'd host this
        # For now, we'll use Twilio's Say verb via inline TwiML
        twiml = f'<Response><Say voice="alice">{message}</Say></Response>'

        success = False
        for to_number in self.to_numbers:
            try:
                call = self.client.calls.create(
                    twiml=twiml,
                    from_=self.from_number,
                    to=to_number
                )
                logger.info(f"Call initiated to {to_number}: {call.sid}")
                success = True
            except TwilioRestException as e:
                logger.error(f"Failed to call {to_number}: {e}")

        if success:
            self._record_notification("call")

        return success

    def notify(
        self,
        message: str,
        use_sms: bool = True,
        use_call: bool = False,
        priority: str = "normal"
    ) -> bool:
        """
        Send notification via configured methods.

        Args:
            message: Message to send
            use_sms: Whether to send SMS
            use_call: Whether to make voice call
            priority: Priority level (normal, high, urgent)

        Returns:
            True if any notification sent successfully
        """
        success = False

        if use_sms:
            success |= self.send_sms(message, priority)

        if use_call:
            success |= self.make_call(message, priority)

        return success

    def _check_cooldown(self, notification_type: str, priority: str) -> bool:
        """Check if enough time has passed since last notification."""
        # Urgent messages bypass cooldown
        if priority == "urgent":
            return True

        key = f"{notification_type}_{priority}"
        last_time = self.last_notification.get(key)

        if last_time is None:
            return True

        # Different cooldowns for different priorities
        cooldown = {
            "high": 5,
            "normal": 15,
            "low": 30
        }.get(priority, 15)

        elapsed = (datetime.now() - last_time).total_seconds() / 60
        return elapsed >= cooldown

    def _record_notification(self, notification_type: str):
        """Record that a notification was sent."""
        self.last_notification[notification_type] = datetime.now()


class NotificationManager:
    """Manage notifications from multiple sources."""

    def __init__(self, twilio_config: dict):
        """
        Initialize notification manager.

        Args:
            twilio_config: Twilio configuration dict
        """
        self.twilio = None

        if all(k in twilio_config for k in ["account_sid", "auth_token", "from_number", "to_numbers"]):
            self.twilio = TwilioNotifier(
                account_sid=twilio_config["account_sid"],
                auth_token=twilio_config["auth_token"],
                from_number=twilio_config["from_number"],
                to_numbers=twilio_config["to_numbers"]
            )
            logger.info("Twilio notifier initialized")
        else:
            logger.warning("Twilio not configured - notifications will only be logged")

    def send_alert(
        self,
        title: str,
        message: str,
        priority: str = "normal",
        use_sms: bool = True,
        use_call: bool = False
    ):
        """
        Send alert via configured notification methods.

        Args:
            title: Alert title
            message: Alert message
            priority: Priority level
            use_sms: Send SMS
            use_call: Make voice call
        """
        full_message = f"{title}: {message}"

        # Always log
        logger.warning(f"ALERT [{priority.upper()}] - {full_message}")

        # Send via Twilio if configured
        if self.twilio:
            self.twilio.notify(
                message=full_message,
                use_sms=use_sms,
                use_call=use_call,
                priority=priority
            )
        else:
            logger.info("Twilio not configured - alert logged only")

    def send_bathroom_alert(self, camera_id: str, confidence: int, behaviors: List[str]):
        """Send bathroom detection alert."""
        message = f"Roxy needs bathroom! Camera: {camera_id}, Confidence: {confidence}%, Behaviors: {', '.join(behaviors)}"
        self.send_alert(
            title="🚨 Bathroom Alert",
            message=message,
            priority="high",
            use_sms=True,
            use_call=False
        )

    def send_presence_alert(self, location: str, dogs_missing: List[str], minutes: int):
        """Send dog presence alert."""
        message = f"Dogs not seen {location} for {minutes}+ minutes: {', '.join(dogs_missing)}"
        self.send_alert(
            title="⚠️ Dog Presence Alert",
            message=message,
            priority="high",
            use_sms=True,
            use_call=True  # Use call for this one since it's more urgent
        )

    def send_system_alert(self, message: str):
        """Send system alert (errors, etc.)."""
        self.send_alert(
            title="🔧 System Alert",
            message=message,
            priority="low",
            use_sms=True,
            use_call=False
        )
