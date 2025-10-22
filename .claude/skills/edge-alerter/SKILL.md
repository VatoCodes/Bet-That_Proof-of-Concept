---
name: edge-alerter
description: Monitor betting edge opportunities and send proactive notifications via email, SMS, or dashboard alerts when STRONG or GOOD edges are detected. Use when setting up automated monitoring, configuring alert preferences, or troubleshooting notification delivery.
allowed-tools: [bash_tool, read_file]
---

# Edge Alerter

Proactive notification system for high-value betting opportunities.

## What It Does

Continuously monitors edge detection results and sends instant notifications when:
- **STRONG EDGE** detected (≥15% edge)
- **GOOD EDGE** detected (≥10% edge)
- **Line movements** create new edge opportunities
- **Time-sensitive** opportunities (game starting soon)

## Notification Channels

1. **Email** (via SMTP)
2. **SMS** (via Twilio API)
3. **Push Notifications** (via web push API)
4. **Dashboard Alerts** (in-app banner)

## When to Use

- "Set up alerts for STRONG edges"
- "Configure email notifications for week 8 edges"
- "Send me SMS when edges appear for Chiefs game"
- "Test alert system with mock edge"

## How It Works

1. Runs `find_edges.py` on schedule (configurable interval)
2. Filters edges by tier (STRONG/GOOD)
3. Checks for duplicates (avoid re-alerting)
4. Formats notification message
5. Sends via configured channels
6. Logs delivery status

## Configuration

See `resources/alert_config.json`:

```json
{
  "enabled_channels": ["email", "sms"],
  "alert_tiers": ["STRONG EDGE", "GOOD EDGE"],
  "check_interval_minutes": 15,
  "minimum_edge_percentage": 10.0,
  "email": {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "to_addresses": ["user@example.com"]
  },
  "sms": {
    "twilio_account_sid": "...",
    "twilio_auth_token": "...",
    "to_numbers": ["+1234567890"]
  }
}
```

## Example Alert

**Subject:** 🔥 STRONG EDGE Detected - Week 7

**Body:**

```
Patrick Mahomes Over 0.5 TD vs Giants

Edge: +18.2%
Tier: STRONG EDGE
True Probability: 92%
Implied Odds: 77.3% (at -340)

Recommendation: $48.00 bet (4.8% of $1000 bankroll)
Kelly Fraction: 19.2% Kelly (conservative)

Stats:
- Mahomes: 1.8 TD/game (10 games)
- Giants Defense: 2.1 TD/game allowed
- Home field advantage: +10%

Action Required: Place bet soon - game starts in 4 hours
Dashboard Link: http://localhost:5001/edges?week=7
```

## Integration

- `utils/edge_calculator.py` - Detects edges
- `scripts/notifications/email_sender.py` - Email delivery
- `scripts/notifications/sms_sender.py` - SMS delivery
- `dashboard/app.py` - In-app alerts via WebSocket

## Usage Examples

### Setup Alerts
```bash
# Configure alert preferences
python scripts/edge_monitor.py --setup

# Test notification delivery
python scripts/edge_monitor.py --test-alerts
```

### Manual Monitoring
```bash
# Run edge detection and send alerts
python scripts/edge_monitor.py --week 7 --send-alerts

# Check for edges without sending alerts
python scripts/edge_monitor.py --week 7 --check-only
```

### Scheduled Monitoring
```bash
# Start continuous monitoring
python scripts/edge_monitor.py --daemon --interval 15

# Stop monitoring
python scripts/edge_monitor.py --stop-daemon
```

## Alert Templates

### Email Template
```html
<!DOCTYPE html>
<html>
<head>
    <title>Bet-That Edge Alert</title>
</head>
<body>
    <h2>🔥 {{tier}} Detected - Week {{week}}</h2>
    
    <h3>{{qb_name}} {{prop_type}} vs {{opponent}}</h3>
    
    <p><strong>Edge:</strong> {{edge_percentage}}%</p>
    <p><strong>Tier:</strong> {{tier}}</p>
    <p><strong>True Probability:</strong> {{true_probability}}%</p>
    <p><strong>Implied Odds:</strong> {{implied_odds}}% (at {{odds}})</p>
    
    <h4>Recommendation</h4>
    <p><strong>Bet Amount:</strong> ${{bet_amount}} ({{bet_percentage}}% of ${{bankroll}} bankroll)</p>
    <p><strong>Kelly Fraction:</strong> {{kelly_fraction}}% Kelly ({{kelly_type}})</p>
    
    <h4>Stats</h4>
    <ul>
        <li>{{qb_name}}: {{qb_td_per_game}} TD/game ({{qb_games}} games)</li>
        <li>{{opponent}} Defense: {{defense_td_allowed}} TD/game allowed</li>
        <li>Home field advantage: {{home_advantage}}%</li>
    </ul>
    
    <p><strong>Action Required:</strong> {{action_message}}</p>
    <p><a href="{{dashboard_link}}">View in Dashboard</a></p>
</body>
</html>
```

### SMS Template
```
🔥 {{tier}}: {{qb_name}} {{prop_type}} vs {{opponent}}
Edge: {{edge_percentage}}% | Bet: ${{bet_amount}} ({{bet_percentage}}% bankroll)
{{action_message}}
Dashboard: {{dashboard_link}}
```

## Error Handling

### Common Issues
- **SMTP Authentication**: Check email credentials and app passwords
- **Twilio API Errors**: Verify account SID and auth token
- **Network Connectivity**: Ensure stable internet connection
- **Rate Limiting**: Respect API rate limits

### Troubleshooting
```bash
# Test email configuration
python scripts/notifications/email_sender.py --test

# Test SMS configuration
python scripts/notifications/sms_sender.py --test

# Check alert logs
tail -f logs/edge_alerts.log

# Verify edge detection
python find_edges.py --week 7 --model v2 --threshold 10
```

## Performance

- **Check Interval**: 15 minutes (configurable)
- **Delivery Latency**: <60 seconds from edge detection
- **Success Rate**: >99% notification delivery
- **Token Usage**: ~5,100 tokens per check cycle

## Success Metrics

- **Delivery Success**: >99% notification delivery rate
- **Latency**: Alerts sent within 60 seconds of edge detection
- **Relevance**: <5% false alerts (user feedback)
- **Coverage**: Captures 100% of STRONG edges

## Security Considerations

### API Key Management
- Store credentials in environment variables
- Use app-specific passwords for Gmail
- Rotate Twilio credentials regularly
- Never commit credentials to version control

### Rate Limiting
- Respect SMTP rate limits
- Respect Twilio rate limits
- Implement internal rate limiting
- Monitor for abuse patterns

## Future Enhancements

- **Custom Alert Rules**: User-defined alert conditions
- **Quiet Hours**: Configurable notification schedules
- **Team Alerts**: Multi-user notification management
- **Advanced Filtering**: Team-specific, player-specific alerts
