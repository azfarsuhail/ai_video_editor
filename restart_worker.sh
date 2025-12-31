#!/bin/bash
echo "🔄 Docker Worker Restart..."

# 1. Force Kill everything (Safe inside a dedicated container)
# We use -9 to ensure no GPU locks remain
pkill -9 -f "worker.py"
pkill -9 -f "ffmpeg" 

# 2. Clear old logs so we don't read history
echo "" > logs_worker.txt

# 3. Start the worker
# -u is vital for Docker logging (unbuffered)
nohup python3 -u worker.py > logs_worker.txt 2>&1 &
PID=$!
echo $PID > worker.pid

echo "✅ Worker Started (PID: $PID)"
echo "👇 STATUS CHECK (First 10 lines of log) 👇"
echo "------------------------------------------"
sleep 2
cat logs_worker.txt
echo "------------------------------------------"