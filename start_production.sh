#!/bin/bash

# Production deployment script for Japanese Lexical Graph
# Runs the application persistently on port 5000 using Gunicorn

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

APP_NAME="japanese-lexical-graph"
PORT=5000
WORKERS=4
BIND="0.0.0.0:$PORT"
USER=$(whoami)
APP_DIR=$(pwd)
PID_FILE="$APP_DIR/gunicorn.pid"
LOG_FILE="$APP_DIR/gunicorn.log"
ACCESS_LOG_FILE="$APP_DIR/gunicorn_access.log"

echo -e "${GREEN}Starting Japanese Lexical Graph in production mode...${NC}"

# Check if running in virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -d "venv" ]; then
        echo -e "${YELLOW}Activating virtual environment...${NC}"
        source venv/bin/activate
    elif [ -d "myenv" ]; then
        echo -e "${YELLOW}Activating virtual environment...${NC}"
        source myenv/bin/activate
    else
        echo -e "${RED}Warning: No virtual environment found. Consider creating one.${NC}"
    fi
fi

# Install/upgrade gunicorn if needed
echo -e "${YELLOW}Ensuring Gunicorn is installed...${NC}"
pip install -r requirements.txt

# Stop existing instance if running
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo -e "${YELLOW}Stopping existing Gunicorn process (PID: $OLD_PID)...${NC}"
        kill -TERM "$OLD_PID"
        sleep 3
        
        # Force kill if still running
        if kill -0 "$OLD_PID" 2>/dev/null; then
            echo -e "${RED}Process still running, force killing...${NC}"
            kill -KILL "$OLD_PID"
        fi
    fi
    rm -f "$PID_FILE"
fi

# Check if port is available
if netstat -tuln | grep ":$PORT " > /dev/null; then
    echo -e "${RED}Port $PORT is already in use!${NC}"
    echo -e "${YELLOW}Processes using port $PORT:${NC}"
    lsof -i :$PORT
    exit 1
fi

# Start Gunicorn
echo -e "${YELLOW}Starting Gunicorn on port $PORT...${NC}"
gunicorn \
    --bind "$BIND" \
    --workers $WORKERS \
    --worker-class sync \
    --timeout 120 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --pid "$PID_FILE" \
    --daemon \
    --access-logfile "$ACCESS_LOG_FILE" \
    --error-logfile "$LOG_FILE" \
    --log-level info \
    --capture-output \
    wsgi:application

# Check if started successfully
sleep 2
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo -e "${GREEN}Successfully started Japanese Lexical Graph!${NC}"
        echo -e "${YELLOW}PID: $PID${NC}"
        echo -e "${YELLOW}URL: http://$(hostname -I | awk '{print $1}'):$PORT${NC}"
        echo -e "${YELLOW}Log file: $LOG_FILE${NC}"
        echo -e "${YELLOW}Access log: $ACCESS_LOG_FILE${NC}"
        echo -e "${YELLOW}PID file: $PID_FILE${NC}"
        echo ""
        echo -e "${GREEN}Commands:${NC}"
        echo -e "  Check status: ./production_status.sh"
        echo -e "  Stop server:  ./stop_production.sh"
        echo -e "  View logs:    tail -f $LOG_FILE"
        echo -e "  View access:  tail -f $ACCESS_LOG_FILE"
    else
        echo -e "${RED}Failed to start application. Check logs: $LOG_FILE${NC}"
        exit 1
    fi
else
    echo -e "${RED}Failed to start application. No PID file created.${NC}"
    exit 1
fi 