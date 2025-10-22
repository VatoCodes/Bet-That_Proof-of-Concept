# Backup Solution 2: Supervisord (Most Robust)

This is the **most robust solution** for production environments with advanced process management.

## Features
- ✅ Auto-restart on crash
- ✅ Process monitoring
- ✅ Web-based dashboard
- ✅ Email alerts on failures
- ✅ Resource limits
- ✅ Multiple process groups
- ✅ Cross-platform (Linux/macOS)

## Installation

### 1. Install Supervisord

```bash
# Using pip
pip install supervisor

# Or using Homebrew (macOS)
brew install supervisor
```

### 2. Create Configuration File

Copy the provided config:

```bash
# Create config directory
sudo mkdir -p /etc/supervisor/conf.d

# Copy config (or use local config)
cp deployment/supervisord/supervisord.conf /usr/local/etc/supervisord.conf
```

### 3. Start Supervisord

```bash
# Start supervisor daemon
supervisord -c /usr/local/etc/supervisord.conf

# Or on Linux with systemd
sudo systemctl start supervisord
sudo systemctl enable supervisord  # Auto-start on boot
```

## Configuration File

See `deployment/supervisord/supervisord.conf` for the full configuration.

Key sections:

```ini
[program:betthat-scheduler]
command=/usr/bin/python3 scheduler.py
directory=/Users/vato/work/Bet-That_(Proof of Concept)
autostart=true
autorestart=true
stderr_logfile=/Users/vato/work/Bet-That_(Proof of Concept)/logs/scheduler.err.log
stdout_logfile=/Users/vato/work/Bet-That_(Proof of Concept)/logs/scheduler.out.log

[program:betthat-scheduler-odds]
command=/usr/bin/python3 scheduler_odds.py
directory=/Users/vato/work/Bet-That_(Proof of Concept)
autostart=true
autorestart=true
stderr_logfile=/Users/vato/work/Bet-That_(Proof of Concept)/logs/scheduler_odds.err.log
stdout_logfile=/Users/vato/work/Bet-That_(Proof of Concept)/logs/scheduler_odds.out.log
```

## Management Commands

### Check status
```bash
supervisorctl status
```

### Start services
```bash
supervisorctl start betthat-scheduler
supervisorctl start betthat-scheduler-odds

# Or start all
supervisorctl start all
```

### Stop services
```bash
supervisorctl stop betthat-scheduler
supervisorctl stop betthat-scheduler-odds

# Or stop all
supervisorctl stop all
```

### Restart services
```bash
supervisorctl restart betthat-scheduler
supervisorctl restart betthat-scheduler-odds

# Or restart all
supervisorctl restart all
```

### Reload config
```bash
supervisorctl reread
supervisorctl update
```

### View logs
```bash
supervisorctl tail betthat-scheduler
supervisorctl tail betthat-scheduler-odds

# Follow logs
supervisorctl tail -f betthat-scheduler
```

## Web Dashboard

Supervisord includes a web-based dashboard:

1. Configured in `supervisord.conf`:
   ```ini
   [inet_http_server]
   port=127.0.0.1:9001
   username=admin
   password=betthat_admin_2025
   ```

2. Access at: http://localhost:9001
   - Username: `admin`
   - Password: `betthat_admin_2025`

3. Features:
   - View process status
   - Start/stop/restart processes
   - View logs
   - Real-time monitoring

## Auto-Start on System Boot

### macOS (Homebrew)
```bash
# Enable auto-start
brew services start supervisor
```

### Linux (systemd)
```bash
# Enable auto-start
sudo systemctl enable supervisord
sudo systemctl start supervisord
```

### Manual (any OS)
Use launchd or cron to start supervisord on boot.

## Advanced Features

### Email Alerts on Failure

Add to config:
```ini
[eventlistener:crashmail]
command=crashmail -a -m your-email@example.com
events=PROCESS_STATE_EXITED
```

### Process Groups

Manage both schedulers as a group:
```bash
supervisorctl start betthat:*
supervisorctl stop betthat:*
```

### Resource Limits

Add to program config:
```ini
priority=1
user=vato
numprocs=1
process_name=%(program_name)s
```

## Why Choose Supervisord?

**Best for:**
- ✅ Production environments
- ✅ Need process monitoring
- ✅ Want web dashboard
- ✅ Require auto-restart on crash
- ✅ Running multiple services
- ✅ Need alerts on failures

**Not needed for:**
- ❌ Simple single-user setup
- ❌ macOS with launchd working fine
- ❌ Don't need web dashboard
- ❌ Prefer simpler solutions

## Comparison with Other Solutions

| Feature | Launchd | Cron | Supervisord |
|---------|---------|------|-------------|
| Auto-start | ✅ | ✅ | ✅ |
| Auto-restart | ✅ | ❌ | ✅ |
| Web UI | ❌ | ❌ | ✅ |
| Logging | ✅ | ⚠️ | ✅ |
| macOS Native | ✅ | ⚠️ | ❌ |
| Cross-platform | ❌ | ✅ | ✅ |
| Complexity | Low | Low | Medium |
| Best for | macOS | Linux cron jobs | Production |

## Installation Script

See `deployment/supervisord/install.sh` for automated setup.

```bash
# Run installation script
chmod +x deployment/supervisord/install.sh
./deployment/supervisord/install.sh
```

## Logs

- **Supervisor logs**: `/usr/local/var/log/supervisord.log`
- **Process stdout**: `logs/scheduler.out.log`
- **Process stderr**: `logs/scheduler.err.log`
- **Application logs**: `scheduler.log`, `scheduler_odds.log`

## Troubleshooting

### Supervisord not starting
```bash
# Check config syntax
supervisord -c /usr/local/etc/supervisord.conf -n
```

### Process not starting
```bash
# View process logs
supervisorctl tail betthat-scheduler stderr

# Check config
supervisorctl status
```

### Permission issues
```bash
# Run as specific user
# Add to program config:
user=vato
```
