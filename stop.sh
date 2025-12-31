#!/bin/bash
# Emergency Shutdown [cite: 4]
echo "Stopping all Tapmad AI services..."
pkill -f "server_fastapi.py"
pkill -f "worker.py"
pkill -f "script.py"
# Force kill all FFmpeg instances to free GPU VRAM [cite: 4]
pkill -9 -f "ffmpeg"
rm -f active_sessions/*.json
echo "System Reset."