#!/bin/bash

# Script to check the status of the production Gunicorn server

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

APP_DIR=$(pwd)
PID_FILE="$APP_DIR/gunicorn.pid"
LOG_FILE="$APP_DIR/gunicorn.log"
ACCESS_LOG_FILE="$APP_DIR/gunicorn_access.log"
PORT=5000

echo -e "${YELLOW}Japanese Lexical Graph Production Status${NC}"
echo "============================================"

# Check PID file
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo -e "${GREEN}✓ Server is running${NC}"
        echo -e "  PID: $PID"
        echo -e "  Started: $(ps -o lstart= -p $PID 2>/dev/null || echo 'Unknown')"
        
        # Check port
        if netstat -tuln | grep ":$PORT " > /dev/null; then
            echo -e "${GREEN}✓ Port $PORT is listening${NC}"
        else
            echo -e "${RED}✗ Port $PORT is not listening${NC}"
        fi
        
        # Check process details
        echo -e "\n${YELLOW}Process Information:${NC}"
        ps aux | grep "$PID" | grep -v grep
        
        # Memory usage
        MEM_USAGE=$(ps -o pid,ppid,pcpu,pmem,cmd -p $PID 2>/dev/null | tail -n +2)
        if [ ! -z "$MEM_USAGE" ]; then
            echo -e "\n${YELLOW}Resource Usage:${NC}"
            echo "PID    PPID  %CPU %MEM COMMAND"
            echo "$MEM_USAGE"
        fi
        
    else
        echo -e "${RED}✗ Server is not running (stale PID file)${NC}"
        echo -e "  Stale PID: $PID"
        rm -f "$PID_FILE"
    fi
else
    echo -e "${RED}✗ Server is not running (no PID file)${NC}"
fi

# Check for any Gunicorn processes
GUNICORN_PROCS=$(ps aux | grep gunicorn | grep wsgi | grep -v grep)
if [ ! -z "$GUNICORN_PROCS" ]; then
    echo -e "\n${YELLOW}All Gunicorn Processes:${NC}"
    ps aux | head -n 1
    echo "$GUNICORN_PROCS"
fi

# Check port usage
echo -e "\n${YELLOW}Port $PORT Usage:${NC}"
PORT_INFO=$(netstat -tuln | grep ":$PORT ")
if [ ! -z "$PORT_INFO" ]; then
    echo "$PORT_INFO"
else
    echo "Port $PORT is not in use"
fi

# Check recent logs
if [ -f "$LOG_FILE" ]; then
    echo -e "\n${YELLOW}Recent Error Log (last 5 lines):${NC}"
    tail -n 5 "$LOG_FILE"
else
    echo -e "\n${RED}No error log file found${NC}"
fi

if [ -f "$ACCESS_LOG_FILE" ]; then
    echo -e "\n${YELLOW}Recent Access Log (last 3 lines):${NC}"
    tail -n 3 "$ACCESS_LOG_FILE"
else
    echo -e "\n${RED}No access log file found${NC}"
fi

# URL Information
SERVER_IP=$(hostname -I | awk '{print $1}')
echo -e "\n${YELLOW}Access URLs:${NC}"
echo -e "  Local:    http://localhost:$PORT"
echo -e "  Network:  http://$SERVER_IP:$PORT"

echo -e "\n${YELLOW}Management Commands:${NC}"
echo -e "  Start:    ./start_production.sh"
echo -e "  Stop:     ./stop_production.sh"
echo -e "  Restart:  ./stop_production.sh && ./start_production.sh" 