#!/usr/bin/env python3
"""
AD10 SRT MASTER (ULTIMATE EDITION - DUAL PIPE)
----------------------------------------------
- Single Connection Architecture (Solves Backlog Issues)
- Dual-Pipe Extraction: Video (stdout) + Audio (stderr)
- Features: RTX 4060 OCR + Crowd Noise + Motion + Reels
"""

import sys, time, subprocess, shlex, threading, os
from collections import deque
from pathlib import Path
import cv2
import numpy as np

# Try importing EasyOCR
try:
    import easyocr
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("⚠️ EasyOCR not found. OCR features disabled.")

# =============== CONFIG ==================

WIDTH   = 1920
HEIGHT  = 1080
FPS     = 25

# --- TRIGGER SETTINGS ---

# 1. OCR (Visual Text)
OCR_INTERVAL = 0.4  # Check every 0.4s
OCR_KEYWORDS = ["4", "6", "OUT", "WICKET", "APPEAL", "REVIEW", "BOWLED", "CAUGHT", "CENTURY"]

# 2. AUDIO (Crowd Noise)
# ENABLED via Dual-Pipe (No extra connection required)
AUDIO_ENABLED = True
AUDIO_THRESH  = 0.65  
AUDIO_SUSTAIN = 3     

# 3. MOTION (Action)
SCENE_THRESH = 12.0

# --- CLIP TIMING ---
RUNUP_SEC = 6.0 
POST_SEC  = 12.0 
BALL_MIN  = 8.0
BALL_MAX  = 25.0 

BUFFER_SEC = RUNUP_SEC + POST_SEC + BALL_MAX
BUFFER_LEN = int(FPS * BUFFER_SEC)

# Default Vendor URL
VENDOR_SRT = "203.130.9.34:7001" 

# ============ PATH SETUP =====================

BASE_DIR = Path(__file__).parent.resolve()
MATCHES_ROOT = BASE_DIR / "matches"

if len(sys.argv) > 1:
    match_name = sys.argv[1]
else:
    match_name = f"match_{int(time.time())}"

if len(sys.argv) > 2:
    target_url = sys.argv[2]
else:
    target_url = VENDOR_SRT

current_match_dir = MATCHES_ROOT / match_name
balls_dir = current_match_dir / "Full Screen"
final_dir = current_match_dir / "Reel"
record_ts = current_match_dir / "full_match.ts"

print(f"\n[CONFIG] Match: {match_name}")
print(f"[CONFIG] Source: {target_url}")

balls_dir.mkdir(parents=True, exist_ok=True)
final_dir.mkdir(parents=True, exist_ok=True)

# ============ HELPERS ====================

def cleanup_zombies():
    """Force kill any lingering FFmpeg processes to free the port."""
    print("[STARTUP] Cleaning potential zombie processes...")
    try:
        subprocess.run(["pkill", "-9", "-f", "ffmpeg"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1) 
    except: pass

def build_srt_url(vendor: str) -> str:
    if Path(vendor).exists(): 
        return str(Path(vendor).resolve())
    if any(vendor.startswith(s) for s in ["srt://", "http", "udp"]):
        return vendor
    # Optimized Latency for Stability
    return f"srt://{vendor}?mode=caller&transtype=live&latency=1000&peerlatency=1000"

# ============ AUDIO MONITOR THREAD (Dual Pipe Version) ===================

class AudioMonitor(threading.Thread):
    def __init__(self, pipe_source):
        super().__init__()
        self.pipe = pipe_source
        self.running = True
        self.current_volume = 0.0
        self.trigger = False
        self.sustain_count = 0
    
    def run(self):
        print("[AUDIO] Listening for Crowd Roar (via Pipe)...")
        
        # Read in 0.1s chunks (4410 samples * 2 bytes = 8820 bytes)
        chunk_size = 8820 
        
        while self.running:
            try:
                # Read directly from the passed pipe (proc.stderr)
                raw = self.pipe.read(chunk_size)
                if not raw or len(raw) != chunk_size: 
                    # If pipe is empty/closed, wait briefly or break
                    time.sleep(0.01)
                    continue
                
                # Convert bytes to numpy array
                audio_data = np.frombuffer(raw, dtype=np.int16)
                
                # Calculate RMS Amplitude
                rms = np.sqrt(np.mean(audio_data.astype(np.float32)**2))
                norm_vol = rms / 20000.0  
                
                self.current_volume = min(norm_vol, 1.0)
                
                # Logic: Check for Sustained Loudness
                if self.current_volume > AUDIO_THRESH:
                    self.sustain_count += 1
                else:
                    self.sustain_count = 0
                    
                if self.sustain_count >= AUDIO_SUSTAIN:
                    self.trigger = True
                    self.sustain_count = 0 
            except Exception as e:
                print(f"[AUDIO ERROR] {e}")
                break

# ============ CLIPPING & VERTICAL ===================

def make_vertical(inp: Path):
    out = final_dir / f"{inp.stem}_V.mp4"
    vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
    
    # RTX 4060 OPTIMIZATION: Use h264_nvenc
    cmd = f"ffmpeg -y -i {inp} -vf \"{vf}\" -c:v h264_nvenc -preset p1 -c:a aac -b:a 128k {out}"
    subprocess.call(shlex.split(cmd), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"[VERTICAL READY] {out.name}")

def cut_job(t1, t2, out_path):
    time.sleep(15) # Wait for disk flush
    
    duration = t2 - t1
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{t1:.2f}",      
        "-i", str(record_ts), 
        "-t", f"{duration:.2f}", 
        "-map", "0:v", "-map", "0:a", 
        "-c", "copy", 
        "-avoid_negative_ts", "make_zero",
        str(out_path)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"[CLIP SAVED] {out_path.name}")
        make_vertical(out_path)
    else:
        print(f"[ERROR] FFmpeg failed to cut: {result.stderr}")

def cut_ball(t1, t2, reason):
    dur = min(max(t2 - t1, BALL_MIN), BALL_MAX)
    ts = int(time.time())
    out = balls_dir / f"ball_{ts}.mp4"
    print(f"[QUEUE] {reason} Detected! Processing...")
    threading.Thread(target=cut_job, args=(t1, t2 + dur, out), daemon=True).start()
    return out

# ============ MAIN ENGINE ===================

def run_engine(vendor: str):
    cleanup_zombies() 
    url = build_srt_url(vendor)
    
    # Init OCR
    reader = None
    if OCR_AVAILABLE:
        print("[OCR] Initializing RTX 4060...")
        reader = easyocr.Reader(['en'], gpu=True) 
        print("[OCR] System Ready.")

    print(f"[SYSTEM LIVE] Watching: Visuals + Audio + Motion")

    while True: # --- WATCHDOG RESTART LOOP ---
        print("[WATCHDOG] Starting Engine Processes...")
        
        # COMBINED VIDEO + AUDIO PIPELINE (1 Connection)
        cmd = [
            "ffmpeg", "-y",
            "-err_detect", "ignore_err",
            "-i", url,
            
            # 1. Disk Recording
            "-map", "0", "-c", "copy", "-f", "mpegts", "-flags", "+global_header", str(record_ts),
            
            # 2. Visuals to STDOUT (pipe:1)
            "-map", "0:v", "-f", "rawvideo", "-pix_fmt", "bgr24", "-an", "pipe:1",
            
            # 3. Audio to STDERR (pipe:2)
            # We treat stderr as a data pipe for audio to avoid a 2nd connection
            "-map", "0:a", "-f", "s16le", "-ac", "1", "-ar", "44100", "pipe:2",
            
            # Quiet mode is ESSENTIAL so logs don't corrupt the audio stream
            "-loglevel", "quiet"
        ]

        # Open process with both pipes
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=10**8)
        
        # Start Audio Monitor attached to stderr
        audio_mon = None
        if AUDIO_ENABLED:
            audio_mon = AudioMonitor(proc.stderr)
            audio_mon.start()

        prev_gray = None
        frame_id = 0
        ball_start = 0.0
        last_ocr_time = 0.0
        last_data_time = time.time()

        try:
            while True:
                # --- Watchdog Check ---
                if time.time() - last_data_time > 10:
                    print("[WATCHDOG] No data for 10s. Restarting...")
                    break 

                # Read Video Frame from stdout
                raw = proc.stdout.read(WIDTH * HEIGHT * 3)
                if len(raw) != WIDTH * HEIGHT * 3: 
                    print("[SRT] Pipe Empty. Possible stream drop.")
                    break
                
                last_data_time = time.time()
                frame = np.frombuffer(raw, np.uint8).reshape((HEIGHT, WIDTH, 3))
                frame_id += 1
                t = frame_id / FPS
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                # --- A. AUDIO TRIGGER (Checking Monitor) ---
                if audio_mon and audio_mon.trigger:
                    if t - ball_start > 10.0: # Debounce
                        print(f"[EVENT] 🔊 CROWD ROAR! (Vol: {audio_mon.current_volume:.2f})")
                        cut_ball(max(0, t - RUNUP_SEC), t + POST_SEC, reason="Audio-Roar")
                        ball_start = t
                    audio_mon.trigger = False

                # --- B. OCR TRIGGER (Visuals) ---
                if reader and (t - last_ocr_time) > OCR_INTERVAL and (t - ball_start > 5.0):
                    last_ocr_time = t
                    roi = gray[int(HEIGHT*0.75):HEIGHT, int(WIDTH*0.15):int(WIDTH*0.85)]
                    _, roi_thresh = cv2.threshold(roi, 130, 255, cv2.THRESH_BINARY)
                    try:
                        res = reader.readtext(roi_thresh, detail=0)
                        text = " ".join(res).upper()
                        for k in OCR_KEYWORDS:
                            if k in text:
                                if k in ["4", "6"] and f" {k} " not in f" {text} ": continue
                                print(f"[EVENT] 👁️ OCR FOUND: {k}")
                                cut_ball(max(0, t - RUNUP_SEC), t + POST_SEC, reason=f"OCR-{k}")
                                ball_start = t
                                break
                    except: pass

                # --- C. MOTION TRIGGER (Action) ---
                if prev_gray is not None:
                    diff = cv2.absdiff(prev_gray, gray)
                    score = np.sum(diff) / (WIDTH * HEIGHT)
                    if score > SCENE_THRESH and t - ball_start > 8.0:
                        if score > 20.0: 
                            print(f"[EVENT] 🏃 MASSIVE MOTION (Score: {score:.1f})")
                            cut_ball(max(0, t - RUNUP_SEC), t + POST_SEC, reason="Motion")
                            ball_start = t

                prev_gray = gray

        except KeyboardInterrupt:
            print("\n[EXIT] User stopped script.")
            proc.terminate()
            sys.exit(0)
            
        finally:
            print("[WATCHDOG] Cleaning up processes...")
            if audio_mon: audio_mon.running = False
            proc.terminate()
            try: proc.wait(timeout=2)
            except: proc.kill()
            time.sleep(2) # Cooldown for network socket

if __name__ == "__main__":
    run_engine(target_url)