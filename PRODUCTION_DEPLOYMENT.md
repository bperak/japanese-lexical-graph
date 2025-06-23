# Production Deployment Guide

This guide covers deploying the Japanese Lexical Graph application in production environments using Gunicorn and systemd.

## Overview

The production deployment setup provides:
- **Gunicorn WSGI server** for better performance than Flask's development server
- **Multi-worker processes** for handling concurrent requests
- **Automatic restart** on failures
- **Comprehensive logging** with separate access and error logs
- **Process management** with PID files
- **Systemd integration** for auto-start on boot
- **Background operation** independent of terminal sessions

## Quick Start

### 1. Install Dependencies
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # or source myenv/bin/activate

# Install all dependencies including Gunicorn
pip install -r requirements.txt
```

### 2. Start Production Server
```bash
# Make scripts executable (if not already)
chmod +x start_production.sh stop_production.sh production_status.sh

# Start the production server
./start_production.sh
```

The server will start on port 5000 and run in the background.

### 3. Verify Deployment
```bash
# Check server status
./production_status.sh

# Test the application
curl http://localhost:5000
```

## Management Scripts

### start_production.sh
Starts the Gunicorn server with production configuration:
- **Workers**: 4 processes for concurrent handling
- **Bind**: 0.0.0.0:5000 (accessible from all interfaces)
- **Timeout**: 120 seconds for request processing
- **Logging**: Separate access and error logs
- **PID File**: For process management
- **Daemon Mode**: Runs in background

**Features**:
- Automatic virtual environment detection
- Existing process cleanup
- Port availability checking
- Dependency installation verification
- Success/failure validation

### stop_production.sh
Gracefully stops the Gunicorn server:
- Sends SIGTERM for graceful shutdown
- Waits 5 seconds for cleanup
- Force kills if necessary (SIGKILL)
- Cleans up PID files
- Detects orphaned processes

### production_status.sh
Comprehensive server monitoring:
- Process status and PID information
- Port usage verification
- Resource usage (CPU, memory)
- Recent log entries (error and access)
- Network accessibility information
- Management command reference

## Production Configuration

### Gunicorn Settings
```bash
gunicorn \
    --bind 0.0.0.0:5000 \
    --workers 4 \
    --worker-class sync \
    --timeout 120 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --pid gunicorn.pid \
    --daemon \
    --access-logfile gunicorn_access.log \
    --error-logfile gunicorn.log \
    --log-level info \
    --capture-output \
    wsgi:application
```

### File Structure
```
japanese-lexical-graph/
├── start_production.sh         # Start script
├── stop_production.sh          # Stop script  
├── production_status.sh        # Status script
├── japanese-lexical-graph.service  # Systemd service
├── wsgi.py                     # WSGI entry point
├── gunicorn.pid               # Process ID file (created at runtime)
├── gunicorn.log               # Error log
├── gunicorn_access.log        # Access log
└── requirements.txt           # Updated with gunicorn
```

## Systemd Service Installation

For automatic startup on system boot:

### 1. Install Service File
```bash
# Copy service file to systemd directory
sudo cp japanese-lexical-graph.service /etc/systemd/system/

# Reload systemd configuration
sudo systemctl daemon-reload
```

### 2. Enable and Start Service
```bash
# Enable automatic startup
sudo systemctl enable japanese-lexical-graph.service

# Start the service
sudo systemctl start japanese-lexical-graph.service
```

### 3. Service Management
```bash
# Check service status
sudo systemctl status japanese-lexical-graph

# Stop the service
sudo systemctl stop japanese-lexical-graph

# Restart the service
sudo systemctl restart japanese-lexical-graph

# View service logs
sudo journalctl -u japanese-lexical-graph -f
```

## Logging

### Log Files
- **gunicorn.log**: Error logs, startup messages, warnings
- **gunicorn_access.log**: HTTP access logs with request details

### Log Rotation
Consider setting up logrotate for production environments:

```bash
# Create /etc/logrotate.d/japanese-lexical-graph
/home/Liks/japanese-lexical-graph/gunicorn*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 Liks Liks
    postrotate
        pid=$(cat /home/Liks/japanese-lexical-graph/gunicorn.pid 2>/dev/null)
        if [ -n "$pid" ]; then
            kill -USR1 $pid
        fi
    endscript
}
```

## Monitoring and Maintenance

### Health Checks
```bash
# Quick health check
curl -f http://localhost:5000 || echo "Server down"

# Detailed status
./production_status.sh
```

### Performance Monitoring
Monitor these metrics:
- **Process count**: Should show 1 master + 4 workers
- **Memory usage**: Watch for memory leaks
- **Response times**: Check access logs for slow requests
- **Error rates**: Monitor error log for issues

### Automatic Monitoring Script
```bash
#!/bin/bash
# monitor_app.sh - Add to cron for automatic monitoring

if ! curl -sf http://localhost:5000 > /dev/null; then
    echo "$(date): Application not responding, restarting..." >> monitor.log
    cd /home/Liks/japanese-lexical-graph
    ./stop_production.sh
    sleep 5
    ./start_production.sh
fi
```

## Troubleshooting

### Common Issues

**Port already in use**:
```bash
# Find process using port 5000
lsof -i :5000
# Kill the process
kill -9 <PID>
```

**Permission denied**:
```bash
# Make scripts executable
chmod +x *.sh
```

**Virtual environment not found**:
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Service fails to start**:
```bash
# Check systemd logs
sudo journalctl -u japanese-lexical-graph -n 50

# Check file paths in service file
sudo systemctl edit japanese-lexical-graph
```

### Log Analysis
```bash
# Monitor real-time logs
tail -f gunicorn.log gunicorn_access.log

# Check for errors
grep -i error gunicorn.log

# Analyze access patterns
awk '{print $1}' gunicorn_access.log | sort | uniq -c | sort -nr
```

## Security Considerations

### Firewall Configuration
```bash
# Allow port 5000 (if using UFW)
sudo ufw allow 5000

# Or for specific networks only
sudo ufw allow from 192.168.1.0/24 to any port 5000
```

### Reverse Proxy (Recommended)
Consider using Nginx as a reverse proxy:

```nginx
# /etc/nginx/sites-available/japanese-lexical-graph
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Environment Variables
Ensure sensitive environment variables are properly set:
```bash
# In production, set these securely
export GEMINI_API_KEY="your-secure-api-key"
export FLASK_ENV="production"
export FLASK_DEBUG="False"
```

## Performance Tuning

### Worker Configuration
Adjust workers based on your server:
```bash
# Rule of thumb: (2 x CPU cores) + 1
# For 2-core system: 5 workers
# Edit start_production.sh and change WORKERS=5
```

### Memory Management
```bash
# Monitor memory usage
ps aux | grep gunicorn
# Restart workers periodically to prevent memory leaks
# max-requests=1000 in start_production.sh handles this
```

## Backup and Recovery

### Application Backup
```bash
# Backup script
tar -czf japanese-lexical-graph-backup-$(date +%Y%m%d).tar.gz \
    --exclude=venv \
    --exclude=__pycache__ \
    --exclude="*.log" \
    --exclude="*.pid" \
    /home/Liks/japanese-lexical-graph/
```

### Database Backup
```bash
# If using Redis for caching
redis-cli BGSAVE

# Graph data backup (already versioned in git)
cp graph_models/G_synonyms_2024_09_18.pickle graph_models/backup/
```

---

## Summary

This production deployment setup provides a robust, scalable solution for running the Japanese Lexical Graph application. The combination of Gunicorn, systemd, and comprehensive monitoring ensures reliable operation in production environments.

For additional support or questions, refer to the main README.md or create an issue in the project repository. 