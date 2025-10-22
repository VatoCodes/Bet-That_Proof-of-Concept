#!/usr/bin/env python3
"""
Notification System Setup for Edge Alerter

This module sets up and configures the notification system for the edge-alerter skill,
including email and SMS configuration, template management, and delivery tracking.
"""

import json
import logging
import smtplib
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import sys

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from utils.db_manager import DatabaseManager
from config import get_database_path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NotificationSystem:
    """
    Notification system for edge alerts.
    
    This class manages email and SMS notifications for betting edge alerts,
    including template management, delivery tracking, and configuration.
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize the notification system."""
        self.db_path = db_path if db_path else get_database_path()
        self.db_manager = DatabaseManager(db_path=self.db_path)
        
        # Load configuration
        self.config = self._load_config()
        self.templates = self._load_templates()
        
        # Initialize delivery tracking
        self.delivery_tracking = {}
        
        # Setup notification channels
        self.email_setup = self._setup_email()
        self.sms_setup = self._setup_sms()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load notification configuration."""
        config_path = Path(__file__).parent / "resources" / "alert_config.json"
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Config file not found: {config_path}")
            return self._get_default_config()
    
    def _load_templates(self) -> Dict[str, str]:
        """Load notification templates."""
        templates_path = Path(__file__).parent / "resources" / "notification_templates.json"
        try:
            with open(templates_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Templates file not found: {templates_path}")
            return self._get_default_templates()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration if config file is not found."""
        return {
            "email": {
                "enabled": False,
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "username": "",
                "password": "",
                "from_email": "",
                "to_emails": []
            },
            "sms": {
                "enabled": False,
                "provider": "twilio",
                "account_sid": "",
                "auth_token": "",
                "from_number": "",
                "to_numbers": []
            },
            "alert_settings": {
                "min_edge_percentage": 0.05,
                "min_confidence": "low",
                "max_alerts_per_day": 10,
                "cooldown_minutes": 30,
                "enabled_channels": ["email"]
            },
            "delivery_tracking": {
                "enabled": True,
                "retention_days": 30
            }
        }
    
    def _get_default_templates(self) -> Dict[str, str]:
        """Get default notification templates."""
        return {
            "email": {
                "subject": "🎯 New Betting Edge Alert - Week {week}",
                "body": """
Hello,

A new betting edge has been detected:

🎯 **Edge Alert**: {qb_name} vs {defense_name}
📊 **Edge**: {edge_percent:.1%} ({edge_status})
💰 **Recommendation**: {recommendation}
📈 **Expected Value**: ${expected_value:.2f}

**Details:**
- True Probability: {true_prob:.1%}
- Implied Odds: {implied_prob:.1%}
- Confidence: {confidence_level}
- Bet Size: {bet_size:.1%} of bankroll

**Risk Factors:**
{risk_factors}

**Historical Context:**
{historical_context}

---
Bet-That Edge Alerter
Generated at: {timestamp}
""",
                "html_body": """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background-color: #2c3e50; color: white; padding: 20px; border-radius: 5px; }
        .content { margin: 20px 0; }
        .edge-info { background-color: #ecf0f1; padding: 15px; border-radius: 5px; margin: 10px 0; }
        .recommendation { background-color: #27ae60; color: white; padding: 15px; border-radius: 5px; margin: 10px 0; }
        .risk-factors { background-color: #e74c3c; color: white; padding: 15px; border-radius: 5px; margin: 10px 0; }
        .footer { font-size: 12px; color: #7f8c8d; margin-top: 30px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🎯 New Betting Edge Alert</h1>
        <p>Week {week} | {qb_name} vs {defense_name}</p>
    </div>
    
    <div class="content">
        <div class="edge-info">
            <h2>📊 Edge Summary</h2>
            <p><strong>Edge:</strong> {edge_percent:.1%} ({edge_status})</p>
            <p><strong>True Probability:</strong> {true_prob:.1%}</p>
            <p><strong>Implied Odds:</strong> {implied_prob:.1%}</p>
            <p><strong>Confidence:</strong> {confidence_level}</p>
        </div>
        
        <div class="recommendation">
            <h2>💰 Bet Recommendation</h2>
            <p><strong>Action:</strong> {recommendation}</p>
            <p><strong>Bet Size:</strong> {bet_size:.1%} of bankroll</p>
            <p><strong>Expected Value:</strong> ${expected_value:.2f}</p>
        </div>
        
        <div class="risk-factors">
            <h2>⚠️ Risk Factors</h2>
            <p>{risk_factors}</p>
        </div>
        
        <div class="content">
            <h2>📈 Historical Context</h2>
            <p>{historical_context}</p>
        </div>
    </div>
    
    <div class="footer">
        <p>Bet-That Edge Alerter | Generated at: {timestamp}</p>
    </div>
</body>
</html>
"""
            },
            "sms": {
                "body": "🎯 Edge Alert: {qb_name} vs {defense_name} - {edge_percent:.1%} edge - {recommendation} - Expected Value: ${expected_value:.2f}"
            }
        }
    
    def _setup_email(self) -> Dict[str, Any]:
        """Setup email notification system."""
        try:
            email_config = self.config.get("email", {})
            
            if not email_config.get("enabled", False):
                return {"enabled": False, "message": "Email notifications disabled"}
            
            # Validate email configuration
            required_fields = ["smtp_server", "smtp_port", "username", "password", "from_email", "to_emails"]
            missing_fields = [field for field in required_fields if not email_config.get(field)]
            
            if missing_fields:
                return {
                    "enabled": False,
                    "message": f"Missing email configuration: {missing_fields}"
                }
            
            # Test SMTP connection
            try:
                server = smtplib.SMTP(email_config["smtp_server"], email_config["smtp_port"])
                server.starttls()
                server.login(email_config["username"], email_config["password"])
                server.quit()
                
                return {
                    "enabled": True,
                    "message": "Email notifications configured successfully",
                    "config": email_config
                }
                
            except Exception as e:
                return {
                    "enabled": False,
                    "message": f"Email configuration test failed: {str(e)}"
                }
                
        except Exception as e:
            logger.error(f"Error setting up email: {e}")
            return {"enabled": False, "message": f"Email setup error: {str(e)}"}
    
    def _setup_sms(self) -> Dict[str, Any]:
        """Setup SMS notification system."""
        try:
            sms_config = self.config.get("sms", {})
            
            if not sms_config.get("enabled", False):
                return {"enabled": False, "message": "SMS notifications disabled"}
            
            # Validate SMS configuration
            required_fields = ["provider", "account_sid", "auth_token", "from_number", "to_numbers"]
            missing_fields = [field for field in required_fields if not sms_config.get(field)]
            
            if missing_fields:
                return {
                    "enabled": False,
                    "message": f"Missing SMS configuration: {missing_fields}"
                }
            
            # Test SMS provider connection (if Twilio)
            if sms_config.get("provider") == "twilio":
                try:
                    from twilio.rest import Client
                    client = Client(sms_config["account_sid"], sms_config["auth_token"])
                    # Test connection by getting account info
                    account = client.api.accounts(sms_config["account_sid"]).fetch()
                    
                    return {
                        "enabled": True,
                        "message": "SMS notifications configured successfully",
                        "config": sms_config
                    }
                    
                except Exception as e:
                    return {
                        "enabled": False,
                        "message": f"SMS configuration test failed: {str(e)}"
                    }
            else:
                return {
                    "enabled": False,
                    "message": f"Unsupported SMS provider: {sms_config.get('provider')}"
                }
                
        except Exception as e:
            logger.error(f"Error setting up SMS: {e}")
            return {"enabled": False, "message": f"SMS setup error: {str(e)}"}
    
    def send_edge_alert(self, edge_data: Dict[str, Any], channels: List[str] = None) -> Dict[str, Any]:
        """
        Send edge alert notifications.
        
        Args:
            edge_data: Edge opportunity data
            channels: List of channels to use (email, sms)
            
        Returns:
            Dictionary with delivery results
        """
        try:
            if channels is None:
                channels = self.config.get("alert_settings", {}).get("enabled_channels", ["email"])
            
            # Check cooldown period
            if not self._check_cooldown(edge_data):
                return {
                    "status": "skipped",
                    "message": "Alert skipped due to cooldown period"
                }
            
            # Check daily alert limit
            if not self._check_daily_limit():
                return {
                    "status": "skipped",
                    "message": "Daily alert limit reached"
                }
            
            # Format notification content
            content = self._format_notification_content(edge_data)
            
            # Send notifications
            delivery_results = {}
            
            for channel in channels:
                if channel == "email" and self.email_setup.get("enabled", False):
                    result = self._send_email_alert(content)
                    delivery_results["email"] = result
                elif channel == "sms" and self.sms_setup.get("enabled", False):
                    result = self._send_sms_alert(content)
                    delivery_results["sms"] = result
                else:
                    delivery_results[channel] = {
                        "status": "skipped",
                        "message": f"Channel {channel} not enabled or configured"
                    }
            
            # Track delivery
            self._track_delivery(edge_data, delivery_results)
            
            return {
                "status": "completed",
                "delivery_results": delivery_results,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error sending edge alert: {e}")
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _format_notification_content(self, edge_data: Dict[str, Any]) -> Dict[str, str]:
        """Format notification content using templates."""
        try:
            # Extract key information
            qb_name = edge_data.get('qb_name', 'Unknown QB')
            defense_name = edge_data.get('defense_name', 'Unknown Defense')
            week = edge_data.get('week', 'Unknown')
            
            # Calculate derived metrics
            true_prob = edge_data.get('true_probability', 0)
            implied_prob = edge_data.get('implied_probability', 0)
            edge_percent = edge_data.get('edge_percentage', 0)
            
            # Determine edge status
            if edge_percent >= 0.15:
                edge_status = "EXCELLENT"
            elif edge_percent >= 0.10:
                edge_status = "STRONG"
            elif edge_percent >= 0.05:
                edge_status = "MODERATE"
            else:
                edge_status = "WEAK"
            
            # Get confidence level
            confidence_level = edge_data.get('confidence_level', 'low')
            
            # Generate recommendation
            recommendation = self._generate_recommendation_text(edge_data)
            bet_size = edge_data.get('bet_size', 0)
            expected_value = edge_data.get('expected_value', 0)
            
            # Generate risk factors and historical context
            risk_factors = self._generate_risk_factors_text(edge_data)
            historical_context = self._generate_historical_context_text(edge_data)
            
            # Format content
            content = {
                "qb_name": qb_name,
                "defense_name": defense_name,
                "week": week,
                "true_prob": true_prob,
                "implied_prob": implied_prob,
                "edge_percent": edge_percent,
                "edge_status": edge_status,
                "confidence_level": confidence_level,
                "recommendation": recommendation,
                "bet_size": bet_size,
                "expected_value": expected_value,
                "risk_factors": risk_factors,
                "historical_context": historical_context,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            return content
            
        except Exception as e:
            logger.error(f"Error formatting notification content: {e}")
            return {"error": str(e)}
    
    def _generate_recommendation_text(self, edge_data: Dict[str, Any]) -> str:
        """Generate recommendation text."""
        try:
            edge_percent = edge_data.get('edge_percentage', 0)
            bet_size = edge_data.get('bet_size', 0)
            
            if edge_percent >= 0.15 and bet_size >= 0.05:
                return "STRONG BET - High edge with good Kelly sizing"
            elif edge_percent >= 0.10 and bet_size >= 0.03:
                return "MODERATE BET - Good edge with reasonable sizing"
            elif edge_percent >= 0.05 and bet_size >= 0.01:
                return "SMALL BET - Moderate edge with conservative sizing"
            else:
                return "NO BET - Insufficient edge or Kelly sizing"
                
        except Exception as e:
            logger.error(f"Error generating recommendation text: {e}")
            return "Error generating recommendation"
    
    def _generate_risk_factors_text(self, edge_data: Dict[str, Any]) -> str:
        """Generate risk factors text."""
        try:
            risk_factors = []
            
            # Check data quality
            data_quality = edge_data.get('data_quality', 0.8)
            if data_quality < 0.7:
                risk_factors.append("Low data quality")
            
            # Check sample size
            sample_size = edge_data.get('sample_size', 8)
            if sample_size < 6:
                risk_factors.append("Small sample size")
            
            # Check model reliability
            model_reliability = edge_data.get('model_reliability', 0.8)
            if model_reliability < 0.7:
                risk_factors.append("Low model reliability")
            
            # Check external factors
            external_factors = edge_data.get('external_factors', 0.2)
            if external_factors > 0.6:
                risk_factors.append("High external factor risk")
            
            if not risk_factors:
                return "Minimal risk factors identified"
            
            return "; ".join(risk_factors)
            
        except Exception as e:
            logger.error(f"Error generating risk factors text: {e}")
            return "Error generating risk factors"
    
    def _generate_historical_context_text(self, edge_data: Dict[str, Any]) -> str:
        """Generate historical context text."""
        try:
            # This would integrate with historical data analysis
            # For now, provide a template structure
            
            qb_name = edge_data.get('qb_name', 'Unknown QB')
            defense_name = edge_data.get('defense_name', 'Unknown Defense')
            
            return f"{qb_name} showing consistent TD production. {defense_name} defense performance varies. Market odds stable with no significant movement."
            
        except Exception as e:
            logger.error(f"Error generating historical context text: {e}")
            return "Error generating historical context"
    
    def _send_email_alert(self, content: Dict[str, str]) -> Dict[str, Any]:
        """Send email alert."""
        try:
            email_config = self.email_setup.get("config", {})
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = self.templates["email"]["subject"].format(**content)
            msg['From'] = email_config["from_email"]
            msg['To'] = ", ".join(email_config["to_emails"])
            
            # Create text and HTML versions
            text_body = self.templates["email"]["body"].format(**content)
            html_body = self.templates["email"]["html_body"].format(**content)
            
            # Attach parts
            text_part = MIMEText(text_body, 'plain')
            html_part = MIMEText(html_body, 'html')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send email
            server = smtplib.SMTP(email_config["smtp_server"], email_config["smtp_port"])
            server.starttls()
            server.login(email_config["username"], email_config["password"])
            
            text = msg.as_string()
            server.sendmail(email_config["from_email"], email_config["to_emails"], text)
            server.quit()
            
            return {
                "status": "success",
                "message": f"Email sent to {len(email_config['to_emails'])} recipients",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error sending email alert: {e}")
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _send_sms_alert(self, content: Dict[str, str]) -> Dict[str, Any]:
        """Send SMS alert."""
        try:
            sms_config = self.sms_setup.get("config", {})
            
            if sms_config.get("provider") == "twilio":
                from twilio.rest import Client
                
                client = Client(sms_config["account_sid"], sms_config["auth_token"])
                
                # Send SMS to each number
                results = []
                for to_number in sms_config["to_numbers"]:
                    try:
                        message = client.messages.create(
                            body=self.templates["sms"]["body"].format(**content),
                            from_=sms_config["from_number"],
                            to=to_number
                        )
                        results.append({
                            "to": to_number,
                            "status": "success",
                            "message_id": message.sid
                        })
                    except Exception as e:
                        results.append({
                            "to": to_number,
                            "status": "error",
                            "message": str(e)
                        })
                
                return {
                    "status": "completed",
                    "results": results,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "error",
                    "message": f"Unsupported SMS provider: {sms_config.get('provider')}"
                }
                
        except Exception as e:
            logger.error(f"Error sending SMS alert: {e}")
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _check_cooldown(self, edge_data: Dict[str, Any]) -> bool:
        """Check if enough time has passed since last alert for this QB."""
        try:
            cooldown_minutes = self.config.get("alert_settings", {}).get("cooldown_minutes", 30)
            qb_name = edge_data.get('qb_name', '')
            
            if not qb_name:
                return True
            
            # Check last alert time for this QB
            last_alert_key = f"last_alert_{qb_name}"
            last_alert_time = self.delivery_tracking.get(last_alert_key)
            
            if last_alert_time:
                time_diff = datetime.now() - last_alert_time
                if time_diff.total_seconds() < cooldown_minutes * 60:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking cooldown: {e}")
            return True
    
    def _check_daily_limit(self) -> bool:
        """Check if daily alert limit has been reached."""
        try:
            max_alerts = self.config.get("alert_settings", {}).get("max_alerts_per_day", 10)
            today = datetime.now().date()
            
            # Count alerts sent today
            today_alerts = 0
            for key, value in self.delivery_tracking.items():
                if key.startswith("alert_") and isinstance(value, datetime):
                    if value.date() == today:
                        today_alerts += 1
            
            return today_alerts < max_alerts
            
        except Exception as e:
            logger.error(f"Error checking daily limit: {e}")
            return True
    
    def _track_delivery(self, edge_data: Dict[str, Any], delivery_results: Dict[str, Any]):
        """Track delivery results."""
        try:
            if not self.config.get("delivery_tracking", {}).get("enabled", True):
                return
            
            qb_name = edge_data.get('qb_name', 'unknown')
            timestamp = datetime.now()
            
            # Track this alert
            alert_key = f"alert_{qb_name}_{timestamp.strftime('%Y%m%d_%H%M%S')}"
            self.delivery_tracking[alert_key] = timestamp
            
            # Track last alert time for cooldown
            last_alert_key = f"last_alert_{qb_name}"
            self.delivery_tracking[last_alert_key] = timestamp
            
            # Store delivery results
            delivery_key = f"delivery_{alert_key}"
            self.delivery_tracking[delivery_key] = delivery_results
            
        except Exception as e:
            logger.error(f"Error tracking delivery: {e}")
    
    def get_notification_status(self) -> Dict[str, Any]:
        """Get notification system status."""
        try:
            return {
                "email": self.email_setup,
                "sms": self.sms_setup,
                "config": self.config,
                "delivery_tracking": {
                    "enabled": self.config.get("delivery_tracking", {}).get("enabled", True),
                    "total_tracked": len(self.delivery_tracking)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting notification status: {e}")
            return {"error": str(e)}
    
    def test_notifications(self, test_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Test notification system with sample data."""
        try:
            if test_data is None:
                test_data = {
                    "qb_name": "Test QB",
                    "defense_name": "Test Defense",
                    "week": 1,
                    "true_probability": 0.65,
                    "implied_probability": 0.55,
                    "edge_percentage": 0.10,
                    "confidence_level": "medium",
                    "bet_size": 0.05,
                    "expected_value": 50.0
                }
            
            # Test email
            email_result = None
            if self.email_setup.get("enabled", False):
                email_result = self._send_email_alert(self._format_notification_content(test_data))
            
            # Test SMS
            sms_result = None
            if self.sms_setup.get("enabled", False):
                sms_result = self._send_sms_alert(self._format_notification_content(test_data))
            
            return {
                "status": "completed",
                "email_test": email_result,
                "sms_test": sms_result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error testing notifications: {e}")
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }

def main():
    """Main function for testing the notification system."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Notification System Setup")
    parser.add_argument('--test', action='store_true',
                       help='Test notification system')
    parser.add_argument('--status', action='store_true',
                       help='Show notification system status')
    parser.add_argument('--setup', action='store_true',
                       help='Setup notification system')
    
    args = parser.parse_args()
    
    # Initialize notification system
    notification_system = NotificationSystem()
    
    if args.status:
        status = notification_system.get_notification_status()
        print("📧 Notification System Status:")
        print(json.dumps(status, indent=2, default=str))
    elif args.test:
        test_result = notification_system.test_notifications()
        print("🧪 Notification System Test:")
        print(json.dumps(test_result, indent=2, default=str))
    elif args.setup:
        print("⚙️ Notification System Setup:")
        print("Email Setup:", notification_system.email_setup)
        print("SMS Setup:", notification_system.sms_setup)
    else:
        print("Use --help to see available options")

if __name__ == "__main__":
    main()
