#!/bin/bash
<<<<<<< HEAD
# Emergency Shutdown [cite: 4]
echo "Stopping all Tapmad AI services..."
pkill -f "server_fastapi.py"
pkill -f "worker.py"
pkill -f "script.py"
# Force kill all FFmpeg instances to free GPU VRAM [cite: 4]
pkill -9 -f "ffmpeg"
rm -f active_sessions/*.json
echo "System Reset."
=======

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
# Only kill script.py (the AI engine)
if pgrep -f "script.py" > /dev/null; then
    pkill -f "script.py"
    echo " - All AI Match Engines killed."
else
    echo " - No active matches found."
fi

# 3. Kill the Muscle (FFmpeg)
echo -e "${YELLOW}[3/4] Cleaning up FFmpeg processes...${NC}"
# Be careful: This kills ALL ffmpeg instances. 
# On a dedicated server, this is exactly what we want to prevent zombie cameras.
pkill -f "ffmpeg" && echo " - FFmpeg zombies removed."

# 4. Reset Dashboard State
echo -e "${YELLOW}[4/4] resetting Session Data...${NC}"
# Deletes the JSON files so the dashboard doesn't show "Recording" when the process is dead
rm -f active_sessions/*.json
echo " - Active session registry cleared."

echo -e "----------------------------------------"
echo -e "${GREEN}✅ SYSTEM FULLY RESET.${NC}"
echo -e "${GREEN}You can now run ./run.sh cleanly.${NC}"
>>>>>>> origin/main
