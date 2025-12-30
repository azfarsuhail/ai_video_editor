#!/bin/bash

# --- COLORS ---
GREEN='\033[0;32m'
RED='\033[0;31m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${CYAN}==============================================${NC}"
echo -e "${CYAN}   TAPMAD AI STUDIO - MISSION CRITICAL MODE    ${NC}"
echo -e "${CYAN}   (Auto-Restart Enabled)                      ${NC}"
echo -e "${CYAN}==============================================${NC}"

# Cleanup function to kill the loops and the actual processes
cleanup() {
    echo -e "\n${RED}[SHUTDOWN] Stopping production services...${NC}"
    # Kill the background loop PIDs
    kill $SERVER_LOOP_PID 2>/dev/null
    kill $WORKER_LOOP_PID 2>/dev/null
    
    # Kill the actual python processes
    pkill -f "server_fastapi.py"
    pkill -f "worker.py"
    
    echo -e "${GREEN}[DONE] All services stopped.${NC}"
    exit
}

trap cleanup SIGINT

# --- FUNCTION: Keep Alive Service ---
run_service() {
    local script_name=$1
    local log_file=$2
    
    while true; do
        echo -e "${GREEN}[$(date +'%H:%M:%S')] Starting $script_name...${NC}"
        python3 "$script_name" >> "$log_file" 2>&1
        
        # If we are here, the script crashed
        echo -e "${RED}[$(date +'%H:%M:%S')] ⚠️  CRASH DETECTED: $script_name${NC}"
        echo -e "${YELLOW}Restarting in 2 seconds...${NC}"
        sleep 2
    done
}

# 1. Start Server Loop
run_service "server_fastapi.py" "server_log.txt" &
SERVER_LOOP_PID=$!
echo -e " -> Server Guardian Active (PID $SERVER_LOOP_PID)"

# 2. Start Worker Loop
run_service "worker.py" "worker_log.txt" &
WORKER_LOOP_PID=$!
echo -e " -> Worker Guardian Active (PID $WORKER_LOOP_PID)"

# 3. Status Info
echo -e "----------------------------------------------"
echo -e "   📂 Dashboard:  http://localhost:5003"
echo -e "----------------------------------------------"
echo -e "${YELLOW}System is monitoring processes. Do not close this window.${NC}"

# Keep script running
wait