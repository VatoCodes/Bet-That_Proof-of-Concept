#!/usr/bin/env python3
"""
Edge Monitor Script

Monitors betting edge opportunities and sends notifications when strong edges are detected.
Implements orchestrator-workers pattern for multi-channel notification delivery.

Usage:
    python scripts/edge_monitor.py --setup                    # Configure alert preferences
    python scripts/edge_monitor.py --test-alerts             # Test notification delivery
    python scripts/edge_monitor.py --week 7 --send-alerts    # Run edge detection and send alerts
    python scripts/edge_monitor.py --daemon --interval 15    # Start continuous monitoring
"""

import argparse
import json
import time
import schedule
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import subprocess
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from utils.edge_calculator import EdgeCalculator
from utils.query_tools import DatabaseQueryTools
from config import get_database_path

logger = logging.getLogger(__name__)


class EdgeMonitor:
    """Orchestrator for edge monitoring and alert delivery"""
    
    def __init__(self, project_root: Path = None):
        """Initialize edge monitor
        
        Args:
            project_root: Path to project root (auto-detected if not provided)
        """
        if project_root is None:
            current_file = Path(__file__).resolve()
            self.project_root = current_file.parent.parent
        else:
            self.project_root = Path(project_root)
        
        self.resources_dir = self.project_root / '.claude' / 'skills' / 'edge-alerter' / 'resources'
        self.scripts_dir = self.project_root / '.claude' / 'skills' / 'edge-alerter' / 'scripts'
        
        # Load configuration
        self.config = self._load_config()
        
        # Initialize components
        self.db_path = get_database_path()
        self.edge_calculator = EdgeCalculator()
        
        # Track recent alerts to prevent duplicates
        self.recent_alerts = []
        self.duplicate_window_hours = self.config['alert_config']['duplicate_window_hours']
        
    def _load_config(self) -> Dict:
        """Load alert configuration"""
        config_path = self.resources_dir / 'alert_config.json'
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Config file not found: {config_path}, using defaults")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """Get default configuration"""
        return {
            "alert_config": {
                "enabled_channels": ["email"],
                "alert_tiers": ["STRONG EDGE", "GOOD EDGE"],
                "check_interval_minutes": 15,
                "minimum_edge_percentage": 10.0,
                "duplicate_window_hours": 4
            },
            "email": {
                "enabled": True,
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "to_addresses": ["user@example.com"]
            }
        }
    
    def detect_edges(self, week: int) -> List[Dict]:
        """Detect edges for a given week
        
        Args:
            week: NFL week number
            
        Returns:
            List of edge opportunities
        """
        logger.info(f"Detecting edges for Week {week}")
        
        try:
            # Use existing edge calculator
            edges = self.edge_calculator.find_edges_for_week(
                week=week,
                threshold=self.config['alert_config']['minimum_edge_percentage']
            )
            
            logger.info(f"Found {len(edges)} edge opportunities")
            return edges
            
        except Exception as e:
            logger.error(f"Error detecting edges: {e}")
            return []
    
    def filter_edges_by_tier(self, edges: List[Dict]) -> List[Dict]:
        """Filter edges by alert tier
        
        Args:
            edges: List of edge opportunities
            
        Returns:
            Filtered list of edges
        """
        alert_tiers = self.config['alert_config']['alert_tiers']
        filtered_edges = []
        
        for edge in edges:
            tier = edge.get('bet_recommendation', {}).get('tier', '')
            if tier in alert_tiers:
                filtered_edges.append(edge)
        
        logger.info(f"Filtered to {len(filtered_edges)} edges matching alert tiers: {alert_tiers}")
        return filtered_edges
    
    def check_for_duplicates(self, edge: Dict) -> bool:
        """Check if edge is a duplicate of recent alert
        
        Args:
            edge: Edge opportunity dictionary
            
        Returns:
            True if duplicate, False otherwise
        """
        # Create edge signature
        signature = f"{edge.get('qb_name', '')}_{edge.get('opponent', '')}_{edge.get('week', '')}"
        
        # Check against recent alerts
        cutoff_time = datetime.now() - timedelta(hours=self.duplicate_window_hours)
        
        for alert in self.recent_alerts:
            if (alert['signature'] == signature and 
                alert['timestamp'] > cutoff_time):
                return True
        
        return False
    
    def add_to_recent_alerts(self, edge: Dict):
        """Add edge to recent alerts tracking
        
        Args:
            edge: Edge opportunity dictionary
        """
        signature = f"{edge.get('qb_name', '')}_{edge.get('opponent', '')}_{edge.get('week', '')}"
        
        self.recent_alerts.append({
            'signature': signature,
            'timestamp': datetime.now(),
            'edge': edge
        })
        
        # Clean up old alerts
        cutoff_time = datetime.now() - timedelta(hours=self.duplicate_window_hours)
        self.recent_alerts = [alert for alert in self.recent_alerts if alert['timestamp'] > cutoff_time]
    
    def route_to_workers(self, edges: List[Dict]) -> Dict[str, int]:
        """Route edges to appropriate notification workers
        
        Args:
            edges: List of edge opportunities
            
        Returns:
            Dictionary with delivery status by channel
        """
        delivery_status = {}
        enabled_channels = self.config['alert_config']['enabled_channels']
        
        for channel in enabled_channels:
            delivery_status[channel] = 0
            
            try:
                if channel == 'email':
                    delivery_status[channel] = self._send_email_alerts(edges)
                elif channel == 'sms':
                    delivery_status[channel] = self._send_sms_alerts(edges)
                elif channel == 'dashboard':
                    delivery_status[channel] = self._send_dashboard_alerts(edges)
                elif channel == 'push':
                    delivery_status[channel] = self._send_push_alerts(edges)
                
                logger.info(f"Sent {delivery_status[channel]} alerts via {channel}")
                
            except Exception as e:
                logger.error(f"Error sending {channel} alerts: {e}")
                delivery_status[channel] = 0
        
        return delivery_status
    
    def _send_email_alerts(self, edges: List[Dict]) -> int:
        """Send email alerts via email worker
        
        Args:
            edges: List of edge opportunities
            
        Returns:
            Number of emails sent
        """
        if not self.config['email']['enabled']:
            return 0
        
        email_script = self.scripts_dir / 'notifications' / 'email_sender.py'
        
        if not email_script.exists():
            logger.error(f"Email sender script not found: {email_script}")
            return 0
        
        try:
            # Create temporary file with edge data
            temp_file = self.project_root / 'temp_edges.json'
            with open(temp_file, 'w') as f:
                json.dump(edges, f, indent=2)
            
            # Run email sender script
            result = subprocess.run([
                'python', str(email_script),
                '--edges-file', str(temp_file),
                '--config', str(self.resources_dir / 'alert_config.json')
            ], capture_output=True, text=True)
            
            # Clean up temp file
            temp_file.unlink()
            
            if result.returncode == 0:
                return len(edges)
            else:
                logger.error(f"Email sender failed: {result.stderr}")
                return 0
                
        except Exception as e:
            logger.error(f"Error running email sender: {e}")
            return 0
    
    def _send_sms_alerts(self, edges: List[Dict]) -> int:
        """Send SMS alerts via SMS worker
        
        Args:
            edges: List of edge opportunities
            
        Returns:
            Number of SMS messages sent
        """
        if not self.config.get('sms', {}).get('enabled', False):
            return 0
        
        sms_script = self.scripts_dir / 'notifications' / 'sms_sender.py'
        
        if not sms_script.exists():
            logger.error(f"SMS sender script not found: {sms_script}")
            return 0
        
        try:
            # Create temporary file with edge data
            temp_file = self.project_root / 'temp_edges.json'
            with open(temp_file, 'w') as f:
                json.dump(edges, f, indent=2)
            
            # Run SMS sender script
            result = subprocess.run([
                'python', str(sms_script),
                '--edges-file', str(temp_file),
                '--config', str(self.resources_dir / 'alert_config.json')
            ], capture_output=True, text=True)
            
            # Clean up temp file
            temp_file.unlink()
            
            if result.returncode == 0:
                return len(edges)
            else:
                logger.error(f"SMS sender failed: {result.stderr}")
                return 0
                
        except Exception as e:
            logger.error(f"Error running SMS sender: {e}")
            return 0
    
    def _send_dashboard_alerts(self, edges: List[Dict]) -> int:
        """Send dashboard alerts
        
        Args:
            edges: List of edge opportunities
            
        Returns:
            Number of dashboard alerts sent
        """
        # Dashboard alerts would be implemented via WebSocket or polling
        # For now, just log the alerts
        logger.info(f"Dashboard alerts for {len(edges)} edges")
        return len(edges)
    
    def _send_push_alerts(self, edges: List[Dict]) -> int:
        """Send push notifications
        
        Args:
            edges: List of edge opportunities
            
        Returns:
            Number of push notifications sent
        """
        # Push notifications would be implemented via Web Push API
        # For now, just log the notifications
        logger.info(f"Push notifications for {len(edges)} edges")
        return len(edges)
    
    def monitor_week(self, week: int, send_alerts: bool = True) -> Dict:
        """Monitor edges for a specific week
        
        Args:
            week: NFL week number
            send_alerts: Whether to send alerts
            
        Returns:
            Monitoring results
        """
        logger.info(f"Monitoring Week {week}")
        
        # Detect edges
        edges = self.detect_edges(week)
        
        if not edges:
            logger.info("No edges found")
            return {
                'week': week,
                'timestamp': datetime.now().isoformat(),
                'edges_found': 0,
                'alerts_sent': 0,
                'delivery_status': {}
            }
        
        # Filter by tier
        filtered_edges = self.filter_edges_by_tier(edges)
        
        # Check for duplicates
        new_edges = []
        for edge in filtered_edges:
            if not self.check_for_duplicates(edge):
                new_edges.append(edge)
                self.add_to_recent_alerts(edge)
        
        logger.info(f"Found {len(new_edges)} new edges after duplicate filtering")
        
        # Send alerts if requested
        delivery_status = {}
        if send_alerts and new_edges:
            delivery_status = self.route_to_workers(new_edges)
        
        return {
            'week': week,
            'timestamp': datetime.now().isoformat(),
            'edges_found': len(edges),
            'filtered_edges': len(filtered_edges),
            'new_edges': len(new_edges),
            'alerts_sent': sum(delivery_status.values()),
            'delivery_status': delivery_status
        }
    
    def start_daemon(self, interval_minutes: int = 15):
        """Start continuous monitoring daemon
        
        Args:
            interval_minutes: Check interval in minutes
        """
        logger.info(f"Starting edge monitor daemon (interval: {interval_minutes} minutes)")
        
        # Schedule monitoring
        schedule.every(interval_minutes).minutes.do(self._daemon_check)
        
        # Run initial check
        self._daemon_check()
        
        # Keep running
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("Daemon stopped by user")
    
    def _daemon_check(self):
        """Perform daemon check"""
        try:
            # Get current week
            with DatabaseQueryTools(self.db_path) as db:
                current_week = db.get_current_week()
            
            if current_week:
                result = self.monitor_week(current_week, send_alerts=True)
                logger.info(f"Daemon check completed: {result['alerts_sent']} alerts sent")
            else:
                logger.warning("Could not determine current week")
                
        except Exception as e:
            logger.error(f"Error in daemon check: {e}")
    
    def setup_alerts(self):
        """Interactive setup for alert preferences"""
        print("🔔 Edge Alert Setup")
        print("=" * 40)
        
        # Email configuration
        print("\n📧 Email Configuration:")
        email_enabled = input("Enable email alerts? (y/n): ").lower() == 'y'
        
        if email_enabled:
            smtp_server = input("SMTP server (default: smtp.gmail.com): ") or "smtp.gmail.com"
            smtp_port = int(input("SMTP port (default: 587): ") or "587")
            to_addresses = input("To addresses (comma-separated): ").split(',')
            to_addresses = [addr.strip() for addr in to_addresses]
            
            self.config['email'] = {
                'enabled': True,
                'smtp_server': smtp_server,
                'smtp_port': smtp_port,
                'to_addresses': to_addresses
            }
        
        # SMS configuration
        print("\n📱 SMS Configuration:")
        sms_enabled = input("Enable SMS alerts? (y/n): ").lower() == 'y'
        
        if sms_enabled:
            twilio_sid = input("Twilio Account SID: ")
            twilio_token = input("Twilio Auth Token: ")
            twilio_number = input("Twilio Phone Number: ")
            to_numbers = input("To phone numbers (comma-separated): ").split(',')
            to_numbers = [num.strip() for num in to_numbers]
            
            self.config['sms'] = {
                'enabled': True,
                'twilio_account_sid': twilio_sid,
                'twilio_auth_token': twilio_token,
                'twilio_phone_number': twilio_number,
                'to_numbers': to_numbers
            }
        
        # Alert preferences
        print("\n⚙️ Alert Preferences:")
        min_edge = float(input("Minimum edge percentage (default: 10.0): ") or "10.0")
        alert_tiers = input("Alert tiers (STRONG EDGE, GOOD EDGE, WEAK EDGE): ").split(',')
        alert_tiers = [tier.strip() for tier in alert_tiers]
        
        self.config['alert_config'].update({
            'minimum_edge_percentage': min_edge,
            'alert_tiers': alert_tiers
        })
        
        # Save configuration
        config_path = self.resources_dir / 'alert_config.json'
        with open(config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
        
        print(f"\n✅ Configuration saved to {config_path}")
    
    def test_alerts(self):
        """Test alert delivery with mock data"""
        print("🧪 Testing Alert Delivery")
        print("=" * 40)
        
        # Create mock edge data
        mock_edge = {
            'qb_name': 'Patrick Mahomes',
            'qb_team': 'Chiefs',
            'opponent': 'Giants',
            'week': 7,
            'odds': -340,
            'true_probability': 0.92,
            'implied_probability': 0.773,
            'edge_percentage': 18.2,
            'bet_recommendation': {
                'tier': 'STRONG EDGE',
                'recommended_bet': 48.00,
                'bankroll_percentage': 4.8
            }
        }
        
        mock_edges = [mock_edge]
        
        print(f"Sending test alerts for {len(mock_edges)} mock edge...")
        
        delivery_status = self.route_to_workers(mock_edges)
        
        print("\n📊 Delivery Status:")
        for channel, count in delivery_status.items():
            status = "✅ Success" if count > 0 else "❌ Failed"
            print(f"  {channel}: {count} alerts {status}")
        
        total_sent = sum(delivery_status.values())
        print(f"\nTotal alerts sent: {total_sent}")


def main():
    """CLI interface for edge monitoring"""
    parser = argparse.ArgumentParser(description='NFL Edge Monitor')
    parser.add_argument('--setup', action='store_true', help='Setup alert preferences')
    parser.add_argument('--test-alerts', action='store_true', help='Test alert delivery')
    parser.add_argument('--week', type=int, help='NFL week number to monitor')
    parser.add_argument('--send-alerts', action='store_true', help='Send alerts for detected edges')
    parser.add_argument('--check-only', action='store_true', help='Check for edges without sending alerts')
    parser.add_argument('--daemon', action='store_true', help='Start continuous monitoring daemon')
    parser.add_argument('--interval', type=int, default=15, help='Daemon check interval in minutes')
    parser.add_argument('--stop-daemon', action='store_true', help='Stop monitoring daemon')
    parser.add_argument('--verbose', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')
    
    try:
        monitor = EdgeMonitor()
        
        if args.setup:
            monitor.setup_alerts()
        
        elif args.test_alerts:
            monitor.test_alerts()
        
        elif args.daemon:
            monitor.start_daemon(args.interval)
        
        elif args.stop_daemon:
            # In a real implementation, this would stop a running daemon
            print("Daemon stop functionality not implemented")
        
        elif args.week:
            send_alerts = args.send_alerts and not args.check_only
            result = monitor.monitor_week(args.week, send_alerts=send_alerts)
            
            print(f"\n📊 Monitoring Results - Week {args.week}")
            print(f"Edges Found: {result['edges_found']}")
            print(f"New Edges: {result['new_edges']}")
            print(f"Alerts Sent: {result['alerts_sent']}")
            
            if result['delivery_status']:
                print("\n📤 Delivery Status:")
                for channel, count in result['delivery_status'].items():
                    print(f"  {channel}: {count} alerts")
        
        else:
            parser.print_help()
        
        return 0
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
