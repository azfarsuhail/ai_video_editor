#!/usr/bin/env python3
"""
FFMPEG EXPERT PIPELINE WORKER (HYBRID EDITION)
-------------------------------------
- Handles Standard (16:9) AND Reels (9:16)
- Auto-Detects Vertical Video
- Swaps Assets (Logo/Intro/Outro) automatically
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

# Ensure directories exist
for d in [QUEUE_DIR, OUTPUT_ROOT, ERRORS_DIR]:
    os.makedirs(d, exist_ok=True)

def log(msg):
    print(msg)
    sys.stdout.flush()

def run_ffmpeg(cmd):
    """Executes FFmpeg command and captures errors safely."""
    try:
        # log(f"Executing: {' '.join(cmd)}") 
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

# --- HELPER: ASSET SELECTOR ---
def get_vertical_asset(original_path):
    """Finds the _vertical version of an asset if it exists."""
    if not original_path: return None
    
    dir_name, filename = os.path.split(original_path)
    name, ext = os.path.splitext(filename)
    
    # Try finding "logo_vertical.png" or "intro_vertical.mp4"
    vert_path = os.path.join(dir_name, f"{name}_vertical{ext}")
    
    if os.path.exists(vert_path):
        return vert_path
    return original_path # Fallback to original if vertical missing

# --- PIPELINE STEP 1: APPLY LOGO ---
def apply_logo(input_path, logo_path, output_path, is_vertical=False):
    log(f"... Pipeline: Applying Logo Overlay (Vertical: {is_vertical})")
    
    # Switch Logic
    if is_vertical:
        # Vertical: Scale logo to 25% width, Place top-right (W-w-20:60)
        # 60px down avoids the iPhone "Dynamic Island" or battery icons
        scale_expr = "iw*0.25"
        overlay_pos = "W-w-20:60"
    else:
        # Standard: Scale logo to 15% width, Place top-right
        scale_expr = "iw*0.15"
        overlay_pos = "W-w-40:40"

    filter_complex = (
        f"[0:v]setpts=PTS-STARTPTS[v_clean];"
        f"[1:v]scale={scale_expr}:-1[logo_scaled];"
        f"[v_clean][logo_scaled]overlay={overlay_pos}:shortest=1[outv];"
        f"[0:a]aresample=48000:async=1,asetpts=PTS-STARTPTS[outa]"
    )
    
    cmd = [
        'ffmpeg', '-y',
        '-i', input_path,
        '-loop', '1', '-i', logo_path,
        '-filter_complex', filter_complex,
        '-map', '[outv]', '-map', '[outa]',
        '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23',
        '-c:a', 'aac', '-b:a', '128k',
        '-max_muxing_queue_size', '4096',
        output_path
    ]
    run_ffmpeg(cmd)

# --- PIPELINE STEP 2: PREPEND INTRO ---
def prepend_intro(current_video, intro_path, output_path, is_vertical=False):
    log(f"... Pipeline: Prepending Intro (Vertical: {is_vertical})")
    
    # Resolution Handling
    target_res = "1080:1920" if is_vertical else "1920:1080"
    
    filter_complex = (
        f"[0:v]scale={target_res}:force_original_aspect_ratio=increase,crop={target_res},setsar=1,setpts=PTS-STARTPTS[v0];"
        f"[0:a]aresample=48000:async=1,asetpts=PTS-STARTPTS[a0];"
        f"[1:v]scale={target_res}:force_original_aspect_ratio=increase,crop={target_res},setsar=1,setpts=PTS-STARTPTS[v1];"
        f"[1:a]aresample=48000:async=1,asetpts=PTS-STARTPTS[a1];"
        f"[v0][a0][v1][a1]concat=n=2:v=1:a=1[outv][outa]"
    )
    cmd = [
        'ffmpeg', '-y',
        '-i', intro_path,
        '-i', current_video,
        '-filter_complex', filter_complex,
        '-map', '[outv]', '-map', '[outa]',
        '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23',
        '-c:a', 'aac', '-b:a', '128k',
        '-max_muxing_queue_size', '4096',
        output_path
    ]
    run_ffmpeg(cmd)

# --- PIPELINE STEP 3: APPEND OUTRO ---
def append_outro(current_video, outro_path, output_path, is_vertical=False):
    log(f"... Pipeline: Appending Outro (Vertical: {is_vertical})")
    
    target_res = "1080:1920" if is_vertical else "1920:1080"

    filter_complex = (
        f"[0:v]scale={target_res}:force_original_aspect_ratio=increase,crop={target_res},setsar=1,setpts=PTS-STARTPTS[v0];"
        f"[0:a]aresample=48000:async=1,asetpts=PTS-STARTPTS[a0];"
        f"[1:v]scale={target_res}:force_original_aspect_ratio=increase,crop={target_res},setsar=1,setpts=PTS-STARTPTS[v1];"
        f"[1:a]aresample=48000:async=1,asetpts=PTS-STARTPTS[a1];"
        f"[v0][a0][v1][a1]concat=n=2:v=1:a=1[outv][outa]"
    )
<<<<<<< HEAD
    # Use the NVIDIA hardware encoder (NVENC)
    cmd = [
        'ffmpeg', '-y',
        '-hwaccel', 'cuda',               # Accelerates decoding if supported
        '-i', input_path,
        # ... other inputs and filter_complex ...
        '-c:v', 'h264_nvenc',             # Use the RTX GPU for encoding
        '-preset', 'p1',                  # 'p1' is fastest for NVENC
        '-c:a', 'aac', '-b:a', '128k',
=======
    cmd = [
        'ffmpeg', '-y',
        '-i', current_video,
        '-i', outro_path,
        '-filter_complex', filter_complex,
        '-map', '[outv]', '-map', '[outa]',
        '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23',
        '-c:a', 'aac', '-b:a', '128k',
        '-max_muxing_queue_size', '4096',
>>>>>>> origin/main
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

    # 1. DETECT REEL MODE
    is_vertical = "_V.mp4" in filename or "_V.mov" in filename
    mode_label = "REEL (9:16)" if is_vertical else "STANDARD (16:9)"

    log(f"\n⚡ Processing Job: {filename} | Mode: {mode_label}")

    # 2. LOCATE SOURCE
    # Try looking in the specified subfolder first, then fallback
    original_video = os.path.join(MATCHES_ROOT, match_name, subfolder, filename)
    if not os.path.exists(original_video):
        # Fallback check
        fallback_sub = "Reel" if is_vertical else "Full Screen"
        original_video = os.path.join(MATCHES_ROOT, match_name, fallback_sub, filename)
        if not os.path.exists(original_video):
            log(f"❌ Error: Source file not found: {filename}")
            return False

    # 3. SELECT ASSETS (Standard vs Vertical)
    logo_path = None
    if logo_name:
        base_logo = os.path.join(LOGOS_DIR, logo_name)
        logo_path = get_vertical_asset(base_logo) if is_vertical else base_logo

    base_intro = os.path.join(ASSETS_DIR, "intro.mp4")
    intro_path = get_vertical_asset(base_intro) if is_vertical else base_intro

    base_outro = os.path.join(ASSETS_DIR, "outro.mp4")
    outro_path = get_vertical_asset(base_outro) if is_vertical else base_outro

    # 4. PREPARE OUTPUTS
    match_output_dir = os.path.join(OUTPUT_ROOT, match_name)
    os.makedirs(match_output_dir, exist_ok=True)
    
    final_output = os.path.join(match_output_dir, f"final_{filename}")

    ts = int(time.time())
    tmp_logo = os.path.join(match_output_dir, f"tmp_logo_{ts}.mp4")
    tmp_intro = os.path.join(match_output_dir, f"tmp_intro_{ts}.mp4")
    tmp_outro = os.path.join(match_output_dir, f"tmp_outro_{ts}.mp4")

    current_pointer = original_video
    files_to_cleanup = []

    try:
        # --- STEP A: LOGO ---
        if logo_path and os.path.exists(logo_path):
            apply_logo(current_pointer, logo_path, tmp_logo, is_vertical)
            current_pointer = tmp_logo
            files_to_cleanup.append(tmp_logo)
        
        # --- STEP B: INTRO ---
        if use_intro and os.path.exists(intro_path):
            prepend_intro(current_pointer, intro_path, tmp_intro, is_vertical)
            current_pointer = tmp_intro
            files_to_cleanup.append(tmp_intro)

        # --- STEP C: OUTRO ---
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

# --- MAIN LOOP ---
if __name__ == "__main__":
    log("🚀 Pipeline Worker Started (Hybrid Mode)...")
    while True:
        try:
            jobs = [f for f in os.listdir(QUEUE_DIR) if f.endswith(".json")]
            if jobs:
                jobs.sort()
                job_file = os.path.join(QUEUE_DIR, jobs[0])
                
                with open(job_file, 'r') as f:
                    job_data = json.load(f)
                
                process_video(job_data)
                os.remove(job_file)
            else:
                time.sleep(1)
        except Exception as main_e:
            log(f"Main Loop Error: {main_e}")
            time.sleep(5)