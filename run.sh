#!/bin/bash

# --- COLOR CONFIG ---
GREEN='\033[0;32m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}=======================================${NC}"
echo -e "${CYAN}   TAPMAD AI STUDIO - PRODUCTION START  ${NC}"
echo -e "${CYAN}=======================================${NC}"

# 1. Cleanup Function (Runs when you hit Ctrl+C)
cleanup() {
    echo -e "\n${RED}[SHUTDOWN] Stopping all services...${NC}"
    
    if [ ! -z "$SERVER_PID" ]; then
        kill $SERVER_PID
        echo " - Killed Server (PID $SERVER_PID)"
    fi
    
    if [ ! -z "$WORKER_PID" ]; then
        kill $WORKER_PID
        echo " - Killed Worker (PID $WORKER_PID)"
    fi
    
    echo -e "${GREEN}[DONE] System stopped safely.${NC}"
    exit
}

# Trap Keyboard Interrupt (Ctrl+C)
trap cleanup SIGINT

# 2. Start Backend Server
echo -e "${GREEN}[1/3] Starting FastAPI Server...${NC}"
python3 server_fastapi.py > server_log.txt 2>&1 &
SERVER_PID=$!
echo "      -> Server PID: $SERVER_PID"
sleep 2

# 3. Start Branding Worker
echo -e "${GREEN}[2/3] Starting Branding Worker...${NC}"
python3 worker.py > worker_log.txt 2>&1 &
WORKER_PID=$!
echo "      -> Worker PID: $WORKER_PID"

# 4. Final Success Message
echo -e "${GREEN}[3/3] SYSTEM ONLINE!${NC}"
echo -e "---------------------------------------"
echo -e "   📂 Dashboard:  http://localhost:5003"
echo -e "   🎛️  Manager:    http://localhost:5003/manager"
echo -e "---------------------------------------"
echo -e "${CYAN}Logs are being written to 'server_log.txt' and 'worker_log.txt'${NC}"
echo -e "${RED}Press Ctrl+C to stop the system.${NC}"

# 5. Keep Script Running (waiting for Ctrl+C)
wait