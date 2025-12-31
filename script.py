#!/usr/bin/env python3
"""
AD10 SRT MASTER (ULTIMATE EDITION)
-----------------------------------
- RTX 4060 GPU OCR (Visuals)
- Crowd Noise Detection (Audio)
- Motion Detection (Action)
- Auto-Vertical Reels (Socials)
"""

import sys, time, subprocess, shlex, threading
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
HEIGHT = 1080
FPS     = 25

# --- TRIGGER SETTINGS ---

# 1. OCR (Visual Text)
OCR_INTERVAL = 0.4  # Check every 0.4s (Fast GPU mode)
OCR_KEYWORDS = ["4", "6", "OUT", "WICKET", "APPEAL", "REVIEW", "BOWLED", "CAUGHT", "CENTURY"]

# 2. AUDIO (Crowd Noise)
AUDIO_ENABLED = True
AUDIO_THRESH  = 0.65  # 0.0 to 1.0 (65% Volume = Loud Cheering)
AUDIO_SUSTAIN = 3     # Must stay loud for 3 consecutive checks (0.3s) to avoid pops/clicks

# 3. MOTION (Action)
SCENE_THRESH = 12.0

# --- CLIP TIMING ---
RUNUP_SEC = 6.0 
POST_SEC  = 12.0 
BALL_MIN  = 8.0
BALL_MAX  = 25.0 

BUFFER_SEC = RUNUP_SEC + POST_SEC + BALL_MAX
BUFFER_LEN = int(FPS * BUFFER_SEC)

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

def build_srt_url(vendor: str) -> str:
    # 1. Allow Local Files for Testing
    if Path(vendor).exists(): 
        return str(Path(vendor).resolve())
    # 2. Standard Streams
    if vendor.startswith("srt://") or vendor.startswith("http") or vendor.startswith("udp"):
        return vendor
    # 3. Default
    return f"srt://{vendor}?mode=caller&transtype=live&latency=200&peerlatency=200"

# ============ AUDIO MONITOR THREAD ===================

class AudioMonitor(threading.Thread):
    def __init__(self, url):
        super().__init__()
        self.url = url
        self.running = True
        self.current_volume = 0.0
        self.trigger = False
        self.sustain_count = 0
    
    def run(self):
        print("[AUDIO] Listening for Crowd Roar...")
        
        # Command to pull raw audio (PCM 16-bit Mono 44.1kHz)
        cmd = ["ffmpeg"]
        if Path(self.url).exists(): cmd.append("-re") # Real-time sim for files
        
        cmd.extend([
            "-i", self.url,
            "-vn", "-f", "s16le", "-ac", "1", "-ar", "44100", 
            "pipe:1", "-loglevel", "quiet"
        ])
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=10**6)
        
        # Read in 0.1s chunks (4410 samples * 2 bytes = 8820 bytes)
        chunk_size = 8820 
        
        while self.running:
            raw = process.stdout.read(chunk_size)
            if len(raw) != chunk_size: break
            
            # Convert bytes to numpy array
            audio_data = np.frombuffer(raw, dtype=np.int16)
            
            # Calculate RMS Amplitude (Volume)
            # Normalize to 0.0 - 1.0 range (Max int16 is 32768)
            rms = np.sqrt(np.mean(audio_data.astype(np.float32)**2))
            norm_vol = rms / 20000.0  # 20000 is a practical "Loud" baseline
            
            self.current_volume = min(norm_vol, 1.0)
            
            # Logic: Check for Sustained Loudness
            if self.current_volume > AUDIO_THRESH:
                self.sustain_count += 1
            else:
                self.sustain_count = 0
                
            if self.sustain_count >= AUDIO_SUSTAIN:
                self.trigger = True
                self.sustain_count = 0 # Reset after trigger
                
        process.terminate()

# ============ RECORDING & PROCESSING ===================

def start_recorder(url: str):
    print(f"[RECORDER] Dumping stream → {record_ts}")
<<<<<<< HEAD
    # Added -flags +global_header to help with clipping later
    cmd = [
        "ffmpeg", "-y", "-i", url, 
        "-map", "0", "-c", "copy", 
        "-f", "mpegts", "-flags", "+global_header", str(record_ts)
    ]
=======
    cmd = ["ffmpeg", "-y", "-i", url, "-map", "0", "-c", "copy", "-f", "mpegts", str(record_ts)]
>>>>>>> origin/main
    return subprocess.Popen(cmd)

def make_vertical(inp: Path):
    out = final_dir / f"{inp.stem}_V.mp4"
    vf = "scale=-1:1920,crop=1080:1920"
<<<<<<< HEAD
    # Switch to h264_nvenc for real-time reel generation
    cmd = ["ffmpeg", "-y", "-i", str(inp), "-vf", vf, "-c:v", "h264_nvenc", "-preset", "p1", "-c:a", "copy", str(out)]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def cut_job(t1, t2, out_path):
    # Give the recorder time to actually write the data to disk
    time.sleep(10) 
    
    # CRITICAL CHANGE: -ss BEFORE -i for live files
    # Added -ss (start) and -t (duration) instead of -to
    duration = t2 - t1
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{t1:.2f}",      # Seek before input
        "-i", str(record_ts), 
        "-t", f"{duration:.2f}", # Use duration
        "-map", "0", 
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
=======
    cmd = ["ffmpeg", "-y", "-i", str(inp), "-vf", vf, "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "copy", str(out)]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"[REEL READY] {out.name}")

def cut_job(t1, t2, out_path):
    time.sleep(15) # Wait for buffer
    cmd = ["ffmpeg", "-y", "-ss", f"{t1:.2f}", "-to", f"{t2:.2f}", "-i", str(record_ts), "-map", "0", "-c", "copy", str(out_path)]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"[CLIP SAVED] {out_path.name}")
    make_vertical(out_path)
>>>>>>> origin/main

def cut_ball(t1, t2, reason):
    dur = min(max(t2 - t1, BALL_MIN), BALL_MAX)
    ts = int(time.time())
    out = balls_dir / f"ball_{ts}.mp4"
    print(f"[QUEUE] {reason} Detected! Processing...")
    threading.Thread(target=cut_job, args=(t1, t2 + dur, out), daemon=True).start()
    return out

# ============ MAIN ENGINE ===================

def run_engine(vendor: str):
    url = build_srt_url(vendor)
    
    # 1. Start Audio Listener
    audio_mon = None
    if AUDIO_ENABLED:
        audio_mon = AudioMonitor(url)
        audio_mon.start()

    # 2. Start Full Match Recorder
    recorder = start_recorder(url)
    
    # 3. Start Video Pipe
    cmd = ["ffmpeg"]
    if Path(url).exists(): cmd.append("-re") # Test Mode Sim
    cmd.extend(["-i", url, "-an", "-pix_fmt", "bgr24", "-f", "rawvideo", "pipe:1", "-loglevel", "quiet"])
    
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=10**8)
    stdout = proc.stdout

    # 4. Init OCR
    reader = None
    if OCR_AVAILABLE:
        print("[OCR] Initializing RTX 4060...")
        reader = easyocr.Reader(['en'], gpu=True) 
        print("[OCR] System Ready.")

    prev_gray = None
    frame_id = 0
    ball_start = 0.0
    last_ocr_time = 0.0

    print(f"[SYSTEM LIVE] Watching: Visuals + Audio + Motion")

    try:
        while True:
            raw = stdout.read(WIDTH * HEIGHT * 3)
            if len(raw) != WIDTH * HEIGHT * 3: break

            frame = np.frombuffer(raw, np.uint8).reshape((HEIGHT, WIDTH, 3))
            frame_id += 1
            t = frame_id / FPS
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # --- A. AUDIO TRIGGER (Crowd Roar) ---
            if audio_mon and audio_mon.trigger:
                if t - ball_start > 10.0: # Debounce
                    print(f"[EVENT] 🔊 CROWD ROAR! (Vol: {audio_mon.current_volume:.2f})")
                    cut_ball(max(0, t - RUNUP_SEC), t + POST_SEC, reason="Audio-Roar")
                    ball_start = t
                audio_mon.trigger = False # Reset

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

            # --- C. MOTION TRIGGER (Backup) ---
            if prev_gray is not None:
                diff = cv2.absdiff(prev_gray, gray)
                score = np.sum(diff) / (WIDTH * HEIGHT)
                if score > SCENE_THRESH and t - ball_start > 8.0:
                    # Only trigger motion if it's HUGE (Wicket celebration)
                    if score > 20.0: 
                        print(f"[EVENT] 🏃 MASSIVE MOTION (Score: {score:.1f})")
                        cut_ball(max(0, t - RUNUP_SEC), t + POST_SEC, reason="Motion")
                        ball_start = t

            prev_gray = gray

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        if audio_mon: audio_mon.running = False
        if proc: proc.terminate()
        if recorder: recorder.terminate()

if __name__ == "__main__":
    run_engine(target_url)