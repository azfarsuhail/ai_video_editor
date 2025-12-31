import os
import json
import time
import subprocess
import signal
import secrets
import shutil
import logging
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import uvicorn

# --- LOGGING SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("server.log")
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI()
security = HTTPBasic()

# --- CONFIG ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

MATCHES_ROOT = os.path.join(BASE_DIR, "matches")
LOGOS_DIR = os.path.join(BASE_DIR, "logos")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
OUTPUT_ROOT = os.path.join(BASE_DIR, "branded_output")
QUEUE_DIR = os.path.join(BASE_DIR, "queue")
ERRORS_DIR = os.path.join(BASE_DIR, "errors")

# NEW: Sessions Directory for Multi-Stream Management
SESSIONS_DIR = os.path.join(BASE_DIR, "active_sessions")

# Paths
SCRIPT_PATH = os.path.join(BASE_DIR, "script.py")
INDEX_HTML = os.path.join(BASE_DIR, "index.html")
STREAMS_HTML = os.path.join(BASE_DIR, "streams.html")

# Ensure directories exist
for d in [MATCHES_ROOT, LOGOS_DIR, OUTPUT_ROOT, ASSETS_DIR, QUEUE_DIR, ERRORS_DIR, SESSIONS_DIR]:
    os.makedirs(d, exist_ok=True)

# --- AUTHENTICATION ---
def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, "tapmad")
    correct_password = secrets.compare_digest(credentials.password, "admin")
    
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# --- HELPER FUNCTIONS ---

def kill_process_tree(pid: int):
    """
    Safely kills a process and its children (FFmpeg zombies).
    Uses 'pkill -P' to target children before killing the parent.
    """
    try:
        # 1. Kill Child Processes (The FFmpeg workers)
        subprocess.run(["pkill", "-P", str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # 2. Kill the Process Group (The Python Script)
        os.killpg(os.getpgid(pid), signal.SIGTERM)
        logger.info(f"Successfully killed process tree for PID {pid}")
    except ProcessLookupError:
        logger.warning(f"Process {pid} already dead.")
    except Exception as e:
        logger.error(f"Failed to kill process {pid}: {e}")

# --- ROUTES ---

@app.get("/", response_class=HTMLResponse)
async def read_root():
    if os.path.exists(INDEX_HTML):
        with open(INDEX_HTML, "r") as f:
            return f.read()
    return "index.html not found"

# --- STREAM MANAGER (PROTECTED) ---

@app.get("/manager", response_class=HTMLResponse)
async def stream_manager_page(username: str = Depends(verify_credentials)):
    if os.path.exists(STREAMS_HTML):
        with open(STREAMS_HTML, "r") as f:
            return f.read()
    return "streams.html not found"

@app.get("/api/stream_status")
async def stream_status(username: str = Depends(verify_credentials)):
    sessions = []
    
    if os.path.exists(SESSIONS_DIR):
        for f in os.listdir(SESSIONS_DIR):
            if not f.endswith(".json"):
                continue
                
            path = os.path.join(SESSIONS_DIR, f)
            try:
                with open(path, 'r') as jf:
                    data = json.load(jf)
                
                pid = data.get('pid')
                start_time = data.get('start_time', 0)
                
                # Check if process is still alive
                is_alive = False
                try:
                    if pid:
                        os.kill(pid, 0)
                        is_alive = True
                except OSError:
                    is_alive = False

                # Logic: Keep if alive OR if it's in the 5-second grace period
                is_new = (time.time() - start_time) < 5
                
                if is_alive or is_new:
                    sessions.append(data)
                else:
                    logger.info(f"Removing dead session: {f}")
                    os.remove(path)

            except (json.JSONDecodeError, IOError, KeyError) as e:
                # If file is unreadable or corrupted, clean it up
                logger.error(f"Error processing session file {f}: {e}")
                if os.path.exists(path):
                    os.remove(path)
                    
    return {"active_sessions": sessions}

@app.post("/api/start_stream")
async def start_stream_api(request: Request, username: str = Depends(verify_credentials)):
    data = await request.json()
    match_name = data.get("match_name")
    srt_url = data.get("srt_url", "")
    
    if not match_name:
        return {"status": "error", "message": "Match Name is required"}

    # Check if this specific match is already running
    session_file = os.path.join(SESSIONS_DIR, f"{match_name}.json")
    if os.path.exists(session_file):
        return {"status": "error", "message": f"Stream '{match_name}' is already running!"}
        
    # Prepare Command: python3 script.py "Match Name" "URL"
    cmd = ["python3", SCRIPT_PATH, match_name]
    if srt_url:
        cmd.append(srt_url)
    
    # Log file specific to this match
    log_file_path = os.path.join(BASE_DIR, f"log_{match_name}.txt")
    
    logger.info(f"Starting Stream: {match_name} [Source: {srt_url}]")
    
    try:
        with open(log_file_path, "w") as log_file:
            # preexec_fn=os.setsid creates a new process group (Critical for clean killing later)
            proc = subprocess.Popen(cmd, stdout=log_file, stderr=log_file, preexec_fn=os.setsid)
        
        # Save Session Info
        session_data = {
            "match": match_name,
            "url": srt_url,
            "pid": proc.pid,
            "start_time": time.time()
        }
        
        with open(session_file, "w") as f:
            json.dump(session_data, f)
            
        return {"status": "started", "match": match_name, "pid": proc.pid}
        
    except Exception as e:
        logger.error(f"Failed to start stream: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/api/stop_stream")
async def stop_stream_api(request: Request, username: str = Depends(verify_credentials)):
    data = await request.json()
    match_name = data.get("match_name")
    
    if not match_name:
        return {"status": "error", "message": "Match Name required to stop"}

    session_file = os.path.join(SESSIONS_DIR, f"{match_name}.json")
    
    if os.path.exists(session_file):
        try:
            with open(session_file, "r") as f:
                session = json.load(f)
            
            pid = session['pid']
            logger.info(f"Stopping Stream: {match_name} (PID: {pid})")
            
            # Use the new robust killer
            kill_process_tree(pid)
            
        except Exception as e:
            logger.error(f"Error stopping stream {match_name}: {e}")
            pass
        
        # Remove session file
        if os.path.exists(session_file):
            os.remove(session_file)
        return {"status": "stopped", "match": match_name}
    
    return {"status": "error", "message": "Session not found"}

# --- STANDARD API ROUTES ---

@app.get("/api/matches")
async def api_matches():
    if not os.path.exists(MATCHES_ROOT): return []
    return sorted([d for d in os.listdir(MATCHES_ROOT) if os.path.isdir(os.path.join(MATCHES_ROOT, d))])

@app.get("/api/config")
async def api_config():
    """
    Returns config state, now including checks for Vertical/Reel assets.
    """
    logos = []
    if os.path.exists(LOGOS_DIR):
        logos = sorted([f for f in os.listdir(LOGOS_DIR) if os.path.splitext(f)[1].lower() in ['.png', '.jpg', '.jpeg']])
    
    return {
        "logos": logos,
        # Standard Assets
        "has_intro": os.path.exists(os.path.join(ASSETS_DIR, "intro.mp4")),
        "has_outro": os.path.exists(os.path.join(ASSETS_DIR, "outro.mp4")),
        # Vertical / Reel Assets
        "has_intro_vertical": os.path.exists(os.path.join(ASSETS_DIR, "intro_vertical.mp4")),
        "has_outro_vertical": os.path.exists(os.path.join(ASSETS_DIR, "outro_vertical.mp4")),
        "has_logo_vertical": os.path.exists(os.path.join(ASSETS_DIR, "logo_vertical.png")),
    }

@app.get("/api/videos/{match_name}")
async def api_videos(match_name: str):
    match_path = os.path.join(MATCHES_ROOT, match_name)
    if not os.path.exists(match_path): return {}
    
    subfolders = sorted([d for d in os.listdir(match_path) if os.path.isdir(os.path.join(match_path, d))])
    data = {}
    
    for sub in subfolders:
        vid_path = os.path.join(match_path, sub)
        videos = sorted([f for f in os.listdir(vid_path) if os.path.splitext(f)[1].lower() in ['.mp4', '.mov', '.avi']])
        
        video_list = []
        for v in videos:
            output_path = os.path.join(OUTPUT_ROOT, match_name, f"final_{v}")
            is_ready = os.path.exists(output_path)
            is_queued = False
            error_msg = None 
            
            # Check Queue
            try:
                for qf in os.listdir(QUEUE_DIR):
                    if v in qf: 
                        is_queued = True
                        break
            except: pass
            
            if is_queued: is_ready = False
            elif is_ready and os.path.getsize(output_path) == 0: is_ready = False

            # Check Errors
            error_path = os.path.join(ERRORS_DIR, f"{v}.json")
            if os.path.exists(error_path):
                try:
                    with open(error_path, 'r') as f:
                        error_msg = json.load(f).get("message", "Unknown Error")
                except: error_msg = "Error file corrupted"
                is_queued = False 
                is_ready = False 

            video_list.append({
                "filename": v,
                "ready": is_ready,
                "queued": is_queued,
                "error": error_msg,
                "url": f"/stream/{match_name}/{sub}/{v}",
                "download_url": f"/download/{match_name}/{v}"
            })
        data[sub] = video_list
    return data

@app.post("/api/queue")
async def api_queue(request: Request):
    req = await request.json()
    filename = req['filename']
    match = req['match']
    
    job_id = f"{int(time.time())}_{filename}"
    job_path = os.path.join(QUEUE_DIR, f"{job_id}.json")
    
    # Clean previous errors for this file
    error_path = os.path.join(ERRORS_DIR, f"{filename}.json")
    if os.path.exists(error_path): os.remove(error_path)
        
    with open(job_path, "w") as f: 
        json.dump(req, f)
    
    logger.info(f"Queued Job: {filename} (Match: {match})")
    return {"status": "ok"}

@app.post("/api/delete_output")
async def api_delete(request: Request):
    req = await request.json()
    output_path = os.path.join(OUTPUT_ROOT, req['match'], f"final_{req['filename']}")
    if os.path.exists(output_path): 
        os.remove(output_path)
        logger.info(f"Deleted Output: {req['filename']}")
    return {"status": "deleted"}

@app.post("/api/dismiss_error")
async def dismiss_error(request: Request):
    req = await request.json()
    filename = req.get('filename')
    error_path = os.path.join(ERRORS_DIR, f"{filename}.json")
    if os.path.exists(error_path): os.remove(error_path)
    return {"status": "cleared"}

@app.get("/stream/{match}/{subfolder}/{filename}")
async def serve_video(match: str, subfolder: str, filename: str):
    path = os.path.join(MATCHES_ROOT, match, subfolder, filename)
    return FileResponse(path)

@app.get("/download/{match}/{filename}")
async def serve_download(match: str, filename: str):
    path = os.path.join(OUTPUT_ROOT, match, f"final_{filename}")
    return FileResponse(path, filename=f"final_{filename}")
    # --- NEW ROUTE: LOG VIEWER ---
@app.get("/api/logs/{match_name}")
async def get_logs(match_name: str):
    """Reads the last 50 lines of the match log file."""
    log_path = os.path.join(BASE_DIR, f"log_{match_name}.txt")
    
    if not os.path.exists(log_path):
        return {"logs": ["Waiting for logs... (File not created yet)"]}
    
    try:
        # Efficiently read last 50 lines using a deque
        from collections import deque
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = deque(f, 50) # Keep only last 50 lines
            return {"logs": list(lines)}
    except Exception as e:
        return {"logs": [f"Error reading log: {str(e)}"]}

if __name__ == "__main__":
    # Kept port 5003 as requested
    uvicorn.run(app, host="0.0.0.0", port=5003)