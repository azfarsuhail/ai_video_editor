#!/usr/bin/env python3
"""
FFMPEG EXPERT PIPELINE WORKER (NUCLEAR FIX EDITION)
---------------------------------------------------
- FIXES LAST-SECOND FREEZE: Uses NVENC to force frame-perfect trimming.
- FIXES LOGO: 1:1 Overlay (No resizing).
- ENGINE: RTX 4060 (NVENC).
"""

import os
import sys
import time
import json
import subprocess
import shutil

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
QUEUE_DIR = os.path.join(BASE_DIR, "queue")
MATCHES_ROOT = os.path.join(BASE_DIR, "matches")
LOGOS_DIR = os.path.join(BASE_DIR, "logos")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
OUTPUT_ROOT = os.path.join(BASE_DIR, "branded_output")
ERRORS_DIR = os.path.join(BASE_DIR, "errors")

for d in [QUEUE_DIR, OUTPUT_ROOT, ERRORS_DIR]:
    os.makedirs(d, exist_ok=True)

def log(msg):
    print(msg)
    sys.stdout.flush()

def run_ffmpeg(cmd):
    try:
        # Increase queue size to prevent buffer overflows
        cmd.extend(['-max_muxing_queue_size', '9999'])
        result = subprocess.run(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode != 0:
            raise Exception(f"FFmpeg Failed:\n{result.stderr[-1000:]}")
        return True
    except Exception as e:
        raise e

def get_vertical_asset(original_path):
    if not original_path: return None
    dir_name, filename = os.path.split(original_path)
    name, ext = os.path.splitext(filename)
    vert_path = os.path.join(dir_name, f"{name}_vertical{ext}")
    return vert_path if os.path.exists(vert_path) else original_path

# --- STEP 0: NUCLEAR SANITIZATION (THE REAL FIX) ---
def sanitize_source(input_path, output_path):
    """
    Re-encodes the input to force frame-perfect trimming.
    This guarantees Video stops EXACTLY when Audio stops.
    """
    log(f"... Pipeline: Sanitizing Source (Frame-Perfect Trim)")
    cmd = [
        'ffmpeg', '-y',
        '-hwaccel', 'cuda',         # Use GPU for decoding
        '-fflags', '+genpts',       # Fix timestamps
        '-i', input_path,
        
        # VIDEO: Re-encode to allow cutting at ANY frame (not just keyframes)
        '-c:v', 'h264_nvenc', '-preset', 'p1', 
        
        # AUDIO: Re-encode to AAC to ensure clean headers
        '-c:a', 'aac', 
        
        # CRITICAL: Stop writing video the moment audio ends
        '-shortest',
        
        # SAFETY: Force standard 25fps to prevent variable framerate drifts
        '-r', '25',
        
        output_path
    ]
    run_ffmpeg(cmd)

# --- STEP 1: APPLY LOGO ---
def apply_logo(input_path, logo_path, output_path, is_vertical=False):
    log(f"... Pipeline: Applying Logo (1:1 Overlay)")
    
    # Simple 1:1 Overlay
    filter_complex = (
        f"[0:v]setpts=PTS-STARTPTS[v_clean];"
        f"[1:v]setpts=PTS-STARTPTS[logo_layer];"
        f"[v_clean][logo_layer]overlay=0:0[outv];"
        f"[0:a]aresample=48000:async=1,asetpts=PTS-STARTPTS[outa]"
    )
    
    cmd = [
        'ffmpeg', '-y', '-hwaccel', 'cuda',
        '-i', input_path,
        '-loop', '1', '-i', logo_path,
        '-filter_complex', filter_complex,
        '-map', '[outv]', '-map', '[outa]',
        '-c:v', 'h264_nvenc', '-preset', 'p1', '-rc', 'constqp', '-qp', '23',
        '-c:a', 'aac', '-b:a', '128k',
        # Safety: Use shortest again just in case logo loop causes issues
        '-shortest', 
        output_path
    ]
    run_ffmpeg(cmd)

# --- STEP 2: PREPEND INTRO ---
def prepend_intro(current_video, intro_path, output_path, is_vertical=False):
    log(f"... Pipeline: Prepending Intro")
    target_res = "1080:1920" if is_vertical else "1920:1080"
    
    filter_complex = (
        f"[0:v]scale={target_res}:force_original_aspect_ratio=increase,crop={target_res},setsar=1,fps=25,setpts=PTS-STARTPTS[v0];"
        f"[0:a]aresample=48000:async=1,asetpts=PTS-STARTPTS[a0];"
        f"[1:v]scale={target_res}:force_original_aspect_ratio=increase,crop={target_res},setsar=1,fps=25,setpts=PTS-STARTPTS[v1];"
        f"[1:a]aresample=48000:async=1,asetpts=PTS-STARTPTS[a1];"
        f"[v0][a0][v1][a1]concat=n=2:v=1:a=1[outv][outa]"
    )
    cmd = [
        'ffmpeg', '-y', '-hwaccel', 'cuda',
        '-i', intro_path,
        '-i', current_video,
        '-filter_complex', filter_complex,
        '-map', '[outv]', '-map', '[outa]',
        '-c:v', 'h264_nvenc', '-preset', 'p1', '-rc', 'constqp', '-qp', '23',
        '-c:a', 'aac', '-b:a', '128k',
        output_path
    ]
    run_ffmpeg(cmd)

# --- STEP 3: APPEND OUTRO ---
def append_outro(current_video, outro_path, output_path, is_vertical=False):
    log(f"... Pipeline: Appending Outro")
    target_res = "1080:1920" if is_vertical else "1920:1080"

    filter_complex = (
        f"[0:v]scale={target_res}:force_original_aspect_ratio=increase,crop={target_res},setsar=1,fps=25,setpts=PTS-STARTPTS[v0];"
        f"[0:a]aresample=48000:async=1,asetpts=PTS-STARTPTS[a0];"
        f"[1:v]scale={target_res}:force_original_aspect_ratio=increase,crop={target_res},setsar=1,fps=25,setpts=PTS-STARTPTS[v1];"
        f"[1:a]aresample=48000:async=1,asetpts=PTS-STARTPTS[a1];"
        f"[v0][a0][v1][a1]concat=n=2:v=1:a=1[outv][outa]"
    )

    cmd = [
        'ffmpeg', '-y', '-hwaccel', 'cuda',
        '-i', current_video,
        '-i', outro_path,
        '-filter_complex', filter_complex,
        '-map', '[outv]', '-map', '[outa]',
        '-c:v', 'h264_nvenc', '-preset', 'p1',
        '-c:a', 'aac', '-b:a', '128k',
        output_path
    ]
    run_ffmpeg(cmd)

# --- ORCHESTRATOR ---
def process_video(job):
    filename = job.get('filename')
    match_name = job.get('match')
    subfolder = job.get('subfolder')
    logo_name = job.get('logo')
    use_intro = job.get('use_intro', False)
    use_outro = job.get('use_outro', False)

    is_vertical = "_V.mp4" in filename or "_V.mov" in filename
    mode_label = "REEL (9:16)" if is_vertical else "STANDARD (16:9)"

    log(f"\n⚡ Processing Job: {filename} | Mode: {mode_label}")

    original_video = os.path.join(MATCHES_ROOT, match_name, subfolder, filename)
    if not os.path.exists(original_video):
        fallback_sub = "Reel" if is_vertical else "Full Screen"
        original_video = os.path.join(MATCHES_ROOT, match_name, fallback_sub, filename)
        if not os.path.exists(original_video):
            log(f"❌ Error: Source file not found: {filename}")
            return False

    # Asset Selection
    logo_path = None
    if logo_name:
        base_logo = os.path.join(LOGOS_DIR, logo_name)
        logo_path = get_vertical_asset(base_logo) if is_vertical else base_logo

    base_intro = os.path.join(ASSETS_DIR, "intro.mp4")
    intro_path = get_vertical_asset(base_intro) if is_vertical else base_intro

    base_outro = os.path.join(ASSETS_DIR, "outro.mp4")
    outro_path = get_vertical_asset(base_outro) if is_vertical else base_outro

    # Prepare Outputs
    match_output_dir = os.path.join(OUTPUT_ROOT, match_name)
    os.makedirs(match_output_dir, exist_ok=True)
    
    final_output = os.path.join(match_output_dir, f"final_{filename}")
    ts = int(time.time())
    
    # Temporary Files
    tmp_sanitized = os.path.join(match_output_dir, f"tmp_clean_{ts}.mp4")
    tmp_logo = os.path.join(match_output_dir, f"tmp_logo_{ts}.mp4")
    tmp_intro = os.path.join(match_output_dir, f"tmp_intro_{ts}.mp4")
    tmp_outro = os.path.join(match_output_dir, f"tmp_outro_{ts}.mp4")

    current_pointer = original_video
    files_to_cleanup = []

    try:
        # STEP 0: SANITIZE (Always run this to fix freeze)
        sanitize_source(original_video, tmp_sanitized)
        current_pointer = tmp_sanitized
        files_to_cleanup.append(tmp_sanitized)

        # STEP A: LOGO
        if logo_path and os.path.exists(logo_path):
            apply_logo(current_pointer, logo_path, tmp_logo, is_vertical)
            current_pointer = tmp_logo
            files_to_cleanup.append(tmp_logo)
        
        # STEP B: INTRO
        if use_intro and os.path.exists(intro_path):
            prepend_intro(current_pointer, intro_path, tmp_intro, is_vertical)
            current_pointer = tmp_intro
            files_to_cleanup.append(tmp_intro)

        # STEP C: OUTRO
        if use_outro and os.path.exists(outro_path):
            append_outro(current_pointer, outro_path, tmp_outro, is_vertical)
            current_pointer = tmp_outro
            files_to_cleanup.append(tmp_outro)

        # Finalize
        if os.path.exists(final_output): os.remove(final_output)

        if current_pointer == original_video:
            shutil.copy(original_video, final_output)
        else:
            os.rename(current_pointer, final_output)
        
        log(f"✅ Job Complete: final_{filename}")
        
        err_file = os.path.join(ERRORS_DIR, f"{filename}.json")
        if os.path.exists(err_file): os.remove(err_file)
        return True

    except Exception as e:
        log(f"❌ Critical Error: {e}")
        err_path = os.path.join(ERRORS_DIR, f"{filename}.json")
        try:
            with open(err_path, "w") as f:
                json.dump({"message": str(e), "timestamp": time.time()}, f)
        except: pass
        return False
        
    finally:
        for f in files_to_cleanup:
            if os.path.exists(f) and f != current_pointer:
                try: os.remove(f)
                except: pass

if __name__ == "__main__":
    log("🚀 Pipeline Worker Started (Nuclear Fix Edition)...")
    while True:
        try:
            jobs = [f for f in os.listdir(QUEUE_DIR) if f.endswith(".json")]
            if jobs:
                jobs.sort()
                job_file = os.path.join(QUEUE_DIR, jobs[0])
                
                with open(job_file, 'r') as f:
                    job_data = json.load(f)
                
                process_video(job_data)
                
                if os.path.exists(job_file):
                    os.remove(job_file)
            else:
                time.sleep(1)
        except Exception as main_e:
            log(f"Main Loop Error: {main_e}")
            time.sleep(5)