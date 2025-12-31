#!/bin/bash

# --- COLORS ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${RED}========================================${NC}"
echo -e "${RED}   ⚠️  EMERGENCY SHUTDOWN PROTOCOL  ⚠️   ${NC}"
echo -e "${RED}========================================${NC}"

# 1. Kill the Brains (Python Scripts)
echo -e "${YELLOW}[1/4] Stopping Python Services...${NC}"
pkill -f "server_fastapi.py" && echo " - Dashboard Server stopped." 
pkill -f "worker.py" && echo " - Branding Worker stopped." 

# 2. Kill the Recorders (Match Engines)
echo -e "${YELLOW}[2/4] Stopping Active Match Recorders...${NC}"
# Targeted kill for the match engine
if pgrep -f "script.py" > /dev/null;  then
    pkill -f "script.py" 
    echo " - All AI Match Engines killed." 
else
    echo " - No active matches found." 
fi

# 3. Kill the Muscle (FFmpeg)
echo -e "${YELLOW}[3/4] Cleaning up FFmpeg processes...${NC}"
# Use -9 (SIGKILL) to ensure GPU VRAM is immediately released 
pkill -9 -f "ffmpeg" && echo " - Forcefully cleared FFmpeg and freed GPU VRAM." 

# 4. Reset Dashboard State
echo -e "${YELLOW}[4/4] Resetting Session Data...${NC}"
# Clear JSON files so the UI doesn't show ghost recordings 
rm -f active_sessions/*.json 
echo " - Active session registry cleared." 

echo -e "----------------------------------------"
echo -e "${GREEN}✅ SYSTEM FULLY RESET.${NC}" 
echo -e "${GREEN}You can now run ./run.sh cleanly.${NC}"