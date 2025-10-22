#!/usr/bin/env python3
"""
SMS Sender Script

Sends SMS notifications for betting edge opportunities via Twilio API.
Part of the edge-alerter skill notification system.

Usage:
    python scripts/notifications/sms_sender.py --edges-file edges.json --config config.json
    python scripts/notifications/sms_sender.py --test
"""

import argparse
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

# Twilio imports (would need to install: pip install twilio)
try:
    from twilio.rest import Client
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Twilio not available. Install with: pip install twilio")

logger = logging.getLogger(__name__)


class SMSSender:
    """SMS notification worker for edge alerts"""
    
    def __init__(self, config: Dict):
        """Initialize SMS sender
        
        Args:
            config: SMS configuration dictionary
        """
        self.config = config.get('sms', {})
        self.templates = self._load_templates()
        
        # Initialize Twilio client if available
        self.twilio_client = None
        if TWILIO_AVAILABLE and self.config.get('enabled', False):
            try:
                self.twilio_client = Client(
                    self.config['twilio_account_sid'],
                    self.config['twilio_auth_token']
                )
                logger.info("Twilio client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Twilio client: {e}")
    
    def _load_templates(self) -> Dict:
        """Load SMS templates"""
        return {
            'urgent_edge_alert': '🔥 {tier}: {qb_name} {prop_type} vs {opponent}\nEdge: {edge_percentage}% | Bet: ${bet_amount} ({bet_percentage}% bankroll)\n{action_message}\nDashboard: {dashboard_link}',
            'detailed_edge_alert': '🔥 {tier}: {qb_name} {prop_type} vs {opponent}\nEdge: {edge_percentage}% | True Prob: {true_probability}%\nBet: ${bet_amount} ({bet_percentage}% bankroll)\nKelly: {kelly_fraction}% ({kelly_type})\n{action_message}\nDashboard: {dashboard_link}',
            'line_movement_alert': '📈 LINE MOVEMENT: {qb_name} {prop_type}\nMoved from {old_odds} to {new_odds}\nEdge: {edge_percentage}%\nRecommendation: {recommendation}\nDashboard: {dashboard_link}'
        }
    
    def format_edge_message(self, edge: Dict) -> Dict[str, str]:
        """Format edge data for SMS template
        
        Args:
            edge: Edge opportunity dictionary
            
        Returns:
            Dictionary with formatted message data
        """
        bet_rec = edge.get('bet_recommendation', {})
        
        # Calculate action message based on edge tier
        tier = bet_rec.get('tier', '')
        if tier == 'STRONG EDGE':
            action_message = "Place bet soon - high confidence"
        elif tier == 'GOOD EDGE':
            action_message = "Consider betting - good opportunity"
        else:
            action_message = "Review opportunity"
        
        # Format data for template
        formatted_data = {
            'tier': tier,
            'qb_name': edge.get('qb_name', ''),
            'prop_type': 'Over 0.5 TD',  # Default prop type
            'opponent': edge.get('opponent', ''),
            'edge_percentage': f"{edge.get('edge_percentage', 0):.1f}",
            'true_probability': f"{edge.get('true_probability', 0) * 100:.1f}",
            'bet_amount': f"{bet_rec.get('recommended_bet', 0):.2f}",
            'bet_percentage': f"{bet_rec.get('bankroll_percentage', 0):.1f}",
            'kelly_fraction': f"{bet_rec.get('kelly_fraction', 0):.1f}",
            'kelly_type': bet_rec.get('kelly_type', 'conservative'),
            'action_message': action_message,
            'dashboard_link': f"http://localhost:5001/edges?week={edge.get('week', '')}"
        }
        
        return formatted_data
    
    def send_edge_alert(self, edge: Dict) -> bool:
        """Send SMS alert for a single edge
        
        Args:
            edge: Edge opportunity dictionary
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.config.get('enabled', False):
            logger.warning("SMS alerts not enabled")
            return False
        
        if not self.twilio_client:
            logger.error("Twilio client not available")
            return False
        
        try:
            # Format message data
            message_data = self.format_edge_message(edge)
            
            # Choose template based on edge tier
            tier = edge.get('bet_recommendation', {}).get('tier', '')
            if tier == 'STRONG EDGE':
                template = 'urgent_edge_alert'
            else:
                template = 'detailed_edge_alert'
            
            # Format message
            message_text = self.templates[template].format(**message_data)
            
            # Send SMS to all configured numbers
            sent_count = 0
            for to_number in self.config.get('to_numbers', []):
                try:
                    message = self.twilio_client.messages.create(
                        body=message_text,
                        from_=self.config['twilio_phone_number'],
                        to=to_number
                    )
                    
                    logger.info(f"SMS sent to {to_number}: {message.sid}")
                    sent_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to send SMS to {to_number}: {e}")
            
            return sent_count > 0
            
        except Exception as e:
            logger.error(f"Error sending SMS: {e}")
            return False
    
    def send_edge_alerts(self, edges: List[Dict]) -> int:
        """Send SMS alerts for multiple edges
        
        Args:
            edges: List of edge opportunities
            
        Returns:
            Number of SMS messages sent successfully
        """
        if not edges:
            return 0
        
        sent_count = 0
        
        for edge in edges:
            if self.send_edge_alert(edge):
                sent_count += 1
        
        logger.info(f"Sent {sent_count}/{len(edges)} SMS alerts")
        return sent_count
    
    def test_sms_config(self) -> bool:
        """Test SMS configuration
        
        Returns:
            True if configuration is valid, False otherwise
        """
        if not TWILIO_AVAILABLE:
            logger.error("Twilio not available. Install with: pip install twilio")
            return False
        
        if not self.config.get('enabled', False):
            logger.warning("SMS alerts not enabled")
            return False
        
        try:
            # Test Twilio client initialization
            test_client = Client(
                self.config['twilio_account_sid'],
                self.config['twilio_auth_token']
            )
            
            # Test by fetching account info
            account = test_client.api.accounts(self.config['twilio_account_sid']).fetch()
            logger.info(f"SMS configuration test successful for account: {account.friendly_name}")
            return True
            
        except Exception as e:
            logger.error(f"SMS configuration test failed: {e}")
            return False
    
    def send_test_message(self) -> bool:
        """Send a test SMS message
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.twilio_client:
            logger.error("Twilio client not available")
            return False
        
        try:
            test_message = "🧪 Test message from Bet-That Edge Finder"
            
            sent_count = 0
            for to_number in self.config.get('to_numbers', []):
                try:
                    message = self.twilio_client.messages.create(
                        body=test_message,
                        from_=self.config['twilio_phone_number'],
                        to=to_number
                    )
                    
                    logger.info(f"Test SMS sent to {to_number}: {message.sid}")
                    sent_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to send test SMS to {to_number}: {e}")
            
            return sent_count > 0
            
        except Exception as e:
            logger.error(f"Error sending test SMS: {e}")
            return False


def main():
    """CLI interface for SMS sender"""
    parser = argparse.ArgumentParser(description='SMS Sender for Edge Alerts')
    parser.add_argument('--edges-file', help='JSON file containing edge data')
    parser.add_argument('--config', help='Configuration file path')
    parser.add_argument('--test', action='store_true', help='Test SMS configuration')
    parser.add_argument('--test-message', action='store_true', help='Send test SMS message')
    parser.add_argument('--verbose', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')
    
    try:
        # Load configuration
        if args.config:
            with open(args.config, 'r') as f:
                config = json.load(f)
        else:
            # Use default config
            config = {
                'sms': {
                    'enabled': True,
                    'twilio_account_sid': 'AC...',
                    'twilio_auth_token': '...',
                    'twilio_phone_number': '+1234567890',
                    'to_numbers': ['+1234567890']
                }
            }
        
        sender = SMSSender(config)
        
        if args.test:
            success = sender.test_sms_config()
            if success:
                print("✅ SMS configuration test successful")
            else:
                print("❌ SMS configuration test failed")
            return 0 if success else 1
        
        elif args.test_message:
            success = sender.send_test_message()
            if success:
                print("✅ Test SMS message sent")
            else:
                print("❌ Test SMS message failed")
            return 0 if success else 1
        
        elif args.edges_file:
            # Load edge data
            with open(args.edges_file, 'r') as f:
                edges = json.load(f)
            
            # Send alerts
            sent_count = sender.send_edge_alerts(edges)
            print(f"📱 Sent {sent_count}/{len(edges)} SMS alerts")
            return 0
        
        else:
            parser.print_help()
            return 1
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
