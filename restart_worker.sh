#!/bin/bash

echo "🔄 Restarting FFmpeg Worker..."

# 1. Activate Environment (just in case)
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# 2. Kill the running worker
# Try using the PID file first
if [ -f worker.pid ]; then
    PID=$(cat worker.pid)
    if ps -p $PID > /dev/null; then
        kill $PID
        echo "   - Killed PID $PID"
    fi
    rm worker.pid
fi

# Also force kill any ghost processes matching the name
pkill -f worker.py 2>/dev/null

sleep 1

# 3. Start the worker again (Background mode, logging to file)
nohup python3 -u worker.py > logs_worker.txt 2>&1 &
NEW_PID=$!
echo $NEW_PID > worker.pid

echo "✅ Worker is active (New PID: $NEW_PID)"
echo "   - Logs: tail -f logs_worker.txt"
