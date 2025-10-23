"""
Alert mechanisms for data quality issues
Supports: Logging, Email, Slack, Discord
"""

import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class AlertManager:
    """Manages alerts for data quality issues"""

    def __init__(self, config: Optional[dict] = None):
        """
        Initialize alert manager

        Args:
            config: Configuration dictionary with alert settings
                   Example:
                   {
                       'enabled_channels': ['log', 'slack'],
                       'slack': {'webhook_url': 'https://...'},
                       'email': {'to_address': 'admin@example.com', ...}
                   }
        """
        self.config = config or {'enabled_channels': ['log']}
        self.enabled_channels = self.config.get('enabled_channels', ['log'])

    def send_alert(self, title: str, message: str, severity: str = "warning"):
        """
        Send alert through all enabled channels

        Args:
            title: Alert title
            message: Alert message body
            severity: 'info', 'warning', 'error', 'critical'
        """
        for channel in self.enabled_channels:
            try:
                if channel == 'log':
                    self._log_alert(title, message, severity)
                elif channel == 'email':
                    self._email_alert(title, message, severity)
                elif channel == 'slack':
                    self._slack_alert(title, message, severity)
                elif channel == 'discord':
                    self._discord_alert(title, message, severity)
            except Exception as e:
                logger.error(f"Failed to send alert via {channel}: {e}")

    def _log_alert(self, title: str, message: str, severity: str):
        """Log alert (always enabled)"""
        level = getattr(logging, severity.upper(), logging.WARNING)
        logger.log(level, f"{title}: {message}")

    def _email_alert(self, title: str, message: str, severity: str):
        """Send email alert"""
        if 'email' not in self.config:
            logger.warning("Email alerting not configured")
            return

        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            email_config = self.config['email']

            msg = MIMEMultipart()
            msg['From'] = email_config.get('from_address', 'noreply@betthat.com')
            msg['To'] = email_config['to_address']
            msg['Subject'] = f"[{severity.upper()}] BetThat Alert: {title}"

            body = f"""
BetThat Data Quality Alert

Severity: {severity.upper()}
Title: {title}

Details:
{message}

Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """

            msg.attach(MIMEText(body, 'plain'))

            with smtplib.SMTP(email_config['smtp_server'], email_config.get('smtp_port', 587)) as server:
                server.starttls()
                if 'username' in email_config and 'password' in email_config:
                    server.login(email_config['username'], email_config['password'])
                server.send_message(msg)

            logger.info(f"Email alert sent: {title}")

        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")

    def _slack_alert(self, title: str, message: str, severity: str):
        """Send Slack alert via webhook"""
        if 'slack' not in self.config:
            logger.warning("Slack alerting not configured")
            return

        try:
            import requests

            webhook_url = self.config['slack']['webhook_url']

            color_map = {
                'info': '#36a64f',      # Green
                'warning': '#ff9900',   # Orange
                'error': '#ff0000',     # Red
                'critical': '#8b0000'   # Dark red
            }

            payload = {
                'attachments': [{
                    'color': color_map.get(severity, '#808080'),
                    'title': title,
                    'text': message,
                    'footer': 'BetThat Monitor',
                    'ts': int(datetime.now().timestamp())
                }]
            }

            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()

            logger.info(f"Slack alert sent: {title}")

        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")

    def _discord_alert(self, title: str, message: str, severity: str):
        """Send Discord alert via webhook"""
        if 'discord' not in self.config:
            logger.warning("Discord alerting not configured")
            return

        try:
            import requests

            webhook_url = self.config['discord']['webhook_url']

            embed = {
                'title': title,
                'description': message,
                'color': {
                    'info': 3447003,      # Blue
                    'warning': 16776960,  # Yellow
                    'error': 15158332,    # Red
                    'critical': 10038562  # Dark red
                }.get(severity, 8421504),  # Gray
                'footer': {
                    'text': 'BetThat Monitor'
                },
                'timestamp': datetime.now().isoformat()
            }

            payload = {'embeds': [embed]}

            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()

            logger.info(f"Discord alert sent: {title}")

        except Exception as e:
            logger.error(f"Failed to send Discord alert: {e}")


# Example configuration
ALERT_CONFIG_EXAMPLE = {
    'enabled_channels': ['log'],  # Start with just logging

    # Uncomment and configure to enable email alerts:
    # 'enabled_channels': ['log', 'email'],
    # 'email': {
    #     'from_address': 'alerts@betthat.com',
    #     'to_address': 'admin@betthat.com',
    #     'smtp_server': 'smtp.gmail.com',
    #     'smtp_port': 587,
    #     'username': 'your_email@gmail.com',
    #     'password': 'your_app_password'
    # },

    # Uncomment and configure to enable Slack alerts:
    # 'enabled_channels': ['log', 'slack'],
    # 'slack': {
    #     'webhook_url': 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
    # },

    # Uncomment and configure to enable Discord alerts:
    # 'enabled_channels': ['log', 'discord'],
    # 'discord': {
    #     'webhook_url': 'https://discord.com/api/webhooks/YOUR/WEBHOOK/URL'
    # }
}


if __name__ == "__main__":
    # Test alerting
    logging.basicConfig(level=logging.INFO)

    alert_manager = AlertManager(ALERT_CONFIG_EXAMPLE)

    print("\nTesting alerts...")
    alert_manager.send_alert(
        title="Test Alert",
        message="This is a test alert to verify the alerting system is working.",
        severity="info"
    )
    print("✓ Test alert sent")
