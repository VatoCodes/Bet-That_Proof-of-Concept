# ADR-003: Alert System Architecture

**Date:** October 21, 2025  
**Status:** Accepted  
**Deciders:** Technical Architecture Team  

## Context

The Bet-That system needs a proactive alert system to notify users when strong betting edges are detected. This ADR documents the architecture for the alert system, including notification channels, scheduling, duplicate detection, and error handling strategies.

## Decision Drivers

- **Timeliness:** Alerts must be sent quickly when edges are detected
- **Reliability:** High delivery success rate across all channels
- **User Experience:** Configurable preferences and non-intrusive notifications
- **Scalability:** System must handle multiple users and notification channels
- **Cost:** Minimize costs while maintaining reliability
- **Maintenance:** Easy to maintain and troubleshoot

## Considered Options

### Option 1: Simple Polling with Direct Notifications
- **Pros:** Simple implementation, direct control
- **Cons:** Inefficient, potential for missed alerts, no duplicate detection

### Option 2: Event-Driven Architecture with Message Queue
- **Pros:** Scalable, reliable, handles duplicates well
- **Cons:** Complex setup, additional infrastructure, overkill for current needs

### Option 3: Orchestrator-Workers Pattern with Scheduled Monitoring
- **Pros:** Balanced approach, handles complexity well, proven pattern
- **Cons:** Moderate complexity, requires coordination

### Option 4: Third-Party Alert Service (PagerDuty, etc.)
- **Pros:** Professional service, high reliability
- **Cons:** Additional cost, external dependency, overkill for betting alerts

## Decision Outcome

**Chosen:** Option 3 - Orchestrator-Workers Pattern with Scheduled Monitoring

We will implement an orchestrator-workers pattern where the orchestrator monitors edge detection and coordinates workers for different notification channels.

## Decision Rationale

### Orchestrator-Workers Pattern Benefits
- **Separation of Concerns:** Orchestrator handles coordination, workers handle delivery
- **Scalability:** Easy to add new notification channels
- **Reliability:** Workers can retry failed deliveries independently
- **Maintainability:** Clear separation makes debugging easier
- **Flexibility:** Different workers can have different retry strategies

### Scheduled Monitoring Approach
- **Predictable:** Regular intervals ensure no missed opportunities
- **Efficient:** Only runs when needed (configurable schedule)
- **Reliable:** Simple polling is more reliable than complex event systems
- **Debuggable:** Easy to trace execution and identify issues

## Architecture Overview

### Components

**Orchestrator (Edge Monitor):**
- Schedules edge detection runs
- Filters edges by tier and user preferences
- Coordinates with workers for notification delivery
- Handles duplicate detection and deduplication
- Logs all activities and delivery status

**Workers:**
- **Email Worker:** SMTP email delivery
- **SMS Worker:** Twilio SMS delivery
- **Dashboard Worker:** In-app notifications
- **Push Worker:** Web push notifications (future)

**Supporting Components:**
- **Configuration Manager:** User preferences and channel settings
- **Duplicate Detector:** Prevents duplicate alerts for same edge
- **Delivery Tracker:** Monitors delivery success rates
- **Retry Manager:** Handles failed delivery retries

### Data Flow

```
1. Orchestrator triggers edge detection (scheduled)
2. Edge detection runs find_edges.py
3. Orchestrator filters results by tier (STRONG/GOOD)
4. Duplicate detector checks against recent alerts
5. For each new edge:
   a. Orchestrator routes to appropriate workers
   b. Workers handle delivery via their channels
   c. Delivery tracker records success/failure
   d. Retry manager handles failed deliveries
6. Orchestrator logs summary and status
```

## Notification Channels

### 1. Email (Primary Channel)
**Implementation:** SMTP via Gmail or custom SMTP server
**Advantages:** Reliable, detailed content, easy to configure
**Use Case:** Detailed edge analysis with full context

**Configuration:**
```json
{
  "email": {
    "enabled": true,
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "username": "alerts@bet-that.com",
    "password": "app_password",
    "to_addresses": ["user@example.com"],
    "template": "detailed_edge_alert"
  }
}
```

**Template Example:**
```
Subject: 🔥 STRONG EDGE Detected - Week 7

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

### 2. SMS (Secondary Channel)
**Implementation:** Twilio API
**Advantages:** Instant delivery, mobile-friendly
**Use Case:** Urgent alerts for time-sensitive opportunities

**Configuration:**
```json
{
  "sms": {
    "enabled": true,
    "twilio_account_sid": "AC...",
    "twilio_auth_token": "...",
    "twilio_phone_number": "+1234567890",
    "to_numbers": ["+1234567890"],
    "template": "urgent_edge_alert"
  }
}
```

**Template Example:**
```
🔥 STRONG EDGE: Mahomes Over 0.5 TD vs Giants
Edge: +18.2% | Bet: $48 (4.8% bankroll)
Game starts in 4 hours
Dashboard: http://localhost:5001/edges?week=7
```

### 3. Dashboard Alerts (Tertiary Channel)
**Implementation:** WebSocket or polling-based in-app notifications
**Advantages:** No external dependencies, integrated with dashboard
**Use Case:** Users actively using dashboard

**Configuration:**
```json
{
  "dashboard": {
    "enabled": true,
    "notification_duration": 30,
    "max_notifications": 5,
    "template": "dashboard_alert"
  }
}
```

### 4. Push Notifications (Future)
**Implementation:** Web Push API
**Advantages:** Browser notifications, works offline
**Use Case:** Users with dashboard open in browser

## Scheduling Strategy

### Monitoring Schedule
- **Frequency:** Every 15 minutes during active hours (9 AM - 11 PM)
- **Peak Hours:** Every 10 minutes during game days (Thursday-Sunday)
- **Off Hours:** Every 30 minutes during non-peak hours
- **Game Day:** Every 5 minutes during last 2 hours before games

### Schedule Configuration
```json
{
  "schedule": {
    "default_interval_minutes": 15,
    "peak_hours_interval_minutes": 10,
    "off_hours_interval_minutes": 30,
    "game_day_interval_minutes": 5,
    "active_hours": {
      "start": "09:00",
      "end": "23:00"
    },
    "peak_days": ["thursday", "friday", "saturday", "sunday"],
    "game_day_hours": {
      "start": "17:00",
      "end": "23:00"
    }
  }
}
```

## Duplicate Detection Strategy

### Problem
Prevent sending multiple alerts for the same edge opportunity.

### Solution
**Time-based Deduplication:**
- Track alerts sent in last 4 hours
- Compare edge signature (QB + opponent + prop type)
- Skip duplicate alerts within time window

**Edge Signature:**
```python
def generate_edge_signature(edge):
    return f"{edge['qb_name']}_{edge['opponent']}_{edge['prop_type']}_{edge['week']}"
```

**Deduplication Logic:**
```python
def is_duplicate_edge(edge, recent_alerts):
    signature = generate_edge_signature(edge)
    cutoff_time = datetime.now() - timedelta(hours=4)
    
    for alert in recent_alerts:
        if (alert['signature'] == signature and 
            alert['timestamp'] > cutoff_time):
            return True
    return False
```

## Error Handling and Retry Strategy

### Error Categories

**1. Network Errors (Temporary)**
- SMTP connection timeout
- Twilio API timeout
- Network connectivity issues
- **Retry Strategy:** Exponential backoff, max 3 retries

**2. Authentication Errors (Permanent)**
- Invalid SMTP credentials
- Invalid Twilio credentials
- **Retry Strategy:** No retry, alert administrator

**3. Rate Limiting (Temporary)**
- SMTP rate limits
- Twilio rate limits
- **Retry Strategy:** Wait and retry, max 2 retries

**4. Validation Errors (Permanent)**
- Invalid email addresses
- Invalid phone numbers
- **Retry Strategy:** No retry, log error

### Retry Implementation
```python
def retry_delivery(worker, edge, max_retries=3):
    for attempt in range(max_retries):
        try:
            result = worker.send_notification(edge)
            if result.success:
                return result
        except TemporaryError as e:
            wait_time = 2 ** attempt  # Exponential backoff
            time.sleep(wait_time)
        except PermanentError as e:
            log_error(e)
            break
    
    return DeliveryResult(success=False, error="Max retries exceeded")
```

## Configuration Management

### User Preferences
```json
{
  "user_preferences": {
    "user_id": "user123",
    "enabled_channels": ["email", "sms"],
    "alert_tiers": ["STRONG EDGE", "GOOD EDGE"],
    "minimum_edge_percentage": 10.0,
    "quiet_hours": {
      "enabled": true,
      "start": "22:00",
      "end": "08:00"
    },
    "team_preferences": {
      "chiefs": {
        "enabled": true,
        "channels": ["email", "sms"]
      },
      "bengals": {
        "enabled": false
      }
    }
  }
}
```

### System Configuration
```json
{
  "system_config": {
    "max_alerts_per_hour": 10,
    "max_alerts_per_day": 50,
    "duplicate_window_hours": 4,
    "retry_attempts": 3,
    "retry_delay_seconds": 60,
    "log_level": "INFO",
    "metrics_enabled": true
  }
}
```

## Monitoring and Metrics

### Key Metrics
- **Delivery Success Rate:** >99% target
- **Alert Latency:** <60 seconds from detection to delivery
- **Duplicate Rate:** <5% of total alerts
- **User Satisfaction:** Positive feedback on alert relevance

### Monitoring Dashboard
- Real-time delivery status
- Success rates by channel
- Alert volume trends
- Error rates and types
- User engagement metrics

### Alerting on System Issues
- Delivery failure rate >5%
- Alert latency >2 minutes
- System errors or exceptions
- Configuration validation failures

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

### Data Privacy
- Minimize data in notifications
- Use secure transmission (TLS/SSL)
- Log minimal personal information
- Comply with data retention policies

## Implementation Timeline

### Week 1: Core Infrastructure
- Day 1: Orchestrator implementation
- Day 2: Email worker implementation
- Day 3: SMS worker implementation
- Day 4: Configuration management

### Week 2: Advanced Features
- Day 5: Duplicate detection
- Day 6: Retry mechanism
- Day 7: Dashboard alerts
- Day 8: Monitoring and metrics

### Week 3: Testing and Optimization
- Day 9: Integration testing
- Day 10: Performance optimization
- Day 11: User acceptance testing
- Day 12: Documentation and handoff

## Success Criteria

### Technical Success
- **Delivery Success Rate:** >99%
- **Alert Latency:** <60 seconds
- **System Uptime:** >99.9%
- **Error Rate:** <1%

### Business Success
- **User Adoption:** >80% of users enable alerts
- **Engagement:** >50% of alerts result in user action
- **Satisfaction:** >4.5/5 user rating
- **ROI:** Time saved > cost of implementation

## Risks and Mitigations

### High Risk
- **Delivery Failures:** Multiple channels, retry logic, monitoring
- **Rate Limiting:** Respect limits, implement backoff, monitor usage

### Medium Risk
- **Configuration Errors:** Validation, testing, documentation
- **User Fatigue:** Configurable preferences, quiet hours, relevance filtering

### Low Risk
- **System Overload:** Rate limiting, monitoring, scaling
- **Security Issues:** Secure credentials, minimal data, compliance

## Alternatives Considered

### Alternative 1: Simple Polling
- **Rejected:** Inefficient, unreliable, no duplicate detection
- **Reason:** Orchestrator-workers provides better reliability and features

### Alternative 2: Event-Driven Architecture
- **Rejected:** Overkill for current needs, complex setup
- **Reason:** Scheduled monitoring is simpler and sufficient

### Alternative 3: Third-Party Service
- **Rejected:** Additional cost, external dependency
- **Reason:** Custom solution provides better control and integration

## Consequences

### Positive
- **High Reliability:** Multiple channels and retry logic ensure delivery
- **User Control:** Configurable preferences and quiet hours
- **Scalable:** Easy to add new channels and users
- **Maintainable:** Clear separation of concerns

### Negative
- **Complexity:** Moderate complexity for setup and maintenance
- **Dependencies:** Relies on external services (SMTP, Twilio)
- **Cost:** Ongoing costs for SMS and email services
- **Monitoring:** Requires monitoring and maintenance

### Neutral
- **Development Time:** 2-3 weeks for full implementation
- **Learning Curve:** Team needs to understand notification systems
- **Documentation:** Comprehensive documentation required

## Review and Updates

This ADR will be reviewed:
- After Week 1 implementation
- After Week 2 integration
- Monthly during active development
- Quarterly for ongoing optimization

Updates will be made based on:
- Delivery success metrics
- User feedback
- Performance benchmarks
- New requirements

---

**Approved by:** Technical Architecture Team  
**Date:** October 21, 2025  
**Next Review:** November 21, 2025
