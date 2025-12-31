#!/bin/bash
# Restart Branding Worker [cite: 4]
pkill -f "worker.py"
# Kill only FFmpeg processes started by the worker [cite: 2]
pkill -f "ffmpeg.*worker" 
nohup python3 -u worker.py > worker_log.txt 2>&1 &
echo "Worker Restarted."