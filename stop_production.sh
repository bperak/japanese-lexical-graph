#!/bin/bash

# Script to stop the production Gunicorn server

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

APP_DIR=$(pwd)
PID_FILE="$APP_DIR/gunicorn.pid"

echo -e "${YELLOW}Stopping Japanese Lexical Graph production server...${NC}"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo -e "${YELLOW}Stopping Gunicorn process (PID: $PID)...${NC}"
        kill -TERM "$PID"
        
        # Wait for graceful shutdown
        sleep 5
        
        # Check if still running
        if kill -0 "$PID" 2>/dev/null; then
            echo -e "${RED}Process still running, force killing...${NC}"
            kill -KILL "$PID"
            sleep 2
        fi
        
        # Clean up PID file
        rm -f "$PID_FILE"
        echo -e "${GREEN}Server stopped successfully.${NC}"
    else
        echo -e "${YELLOW}Process not running (stale PID file).${NC}"
        rm -f "$PID_FILE"
    fi
else
    echo -e "${YELLOW}No PID file found. Server may not be running.${NC}"
    
    # Check for any remaining processes
    REMAINING=$(ps aux | grep gunicorn | grep wsgi | grep -v grep)
    if [ ! -z "$REMAINING" ]; then
        echo -e "${RED}Found remaining Gunicorn processes:${NC}"
        echo "$REMAINING"
        echo -e "${YELLOW}Kill them manually with: pkill -f 'gunicorn.*wsgi'${NC}"
    fi
fi 