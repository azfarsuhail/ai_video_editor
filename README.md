# Video Branding & Automated Highlights System

## 📖 Project Overview
This project is an automated video processing pipeline designed to handle sports highlights and video branding. It utilizes a decoupled architecture where a **FastAPI** backend receives requests and queues them for a dedicated **Background Worker**. The worker processes videos by overlaying branding (logos), stitching intros/outros, and performing OCR (Optical Character Recognition) tasks to detect game states or events.

---

## 📂 System Architecture
The system follows a **Producer-Consumer** pattern to ensure the API remains responsive even during heavy video rendering tasks.

1.  **The Producer (API):** `server_fastapi.py` serves the web interface and API endpoints. It accepts video processing requests and writes a "job file" to the `queue/` directory.
2.  **The Queue:** The `queue/` folder acts as a simple file-based message broker.
3.  **The Consumer (Worker):** `worker.py` constantly watches the `queue/` directory. When a new job appears, it executes `script.py` to process the video using FFmpeg and Computer Vision libraries.

### Directory Structure
```text
.
├── assets/                  # Static video assets (Intro.mp4, Outro.mp4)
├── logos/                   # Branding overlays (transparent PNGs)
├── matches/                 # Storage for processed output videos
├── queue/                   # Job queue directory (API writes here, Worker reads here)
├── index.html               # Main Control Dashboard (Web UI)
├── streams.html             # Live Stream Monitor UI
├── server_fastapi.py        # Backend Application (FastAPI)
├── worker.py                # Background Task Manager
├── script.py                # Core Processing Logic (FFmpeg/OCR)
├── requirements.txt         # Python Dependencies
└── *.sh                     # Operation Control Scripts

```

---

## ⚙️ Configuration & Parameters

Since the system relies on specific assets and paths, ensure the following configurations are set. These are typically modified within `script.py` or `server_fastapi.py` depending on your implementation preference (Environment Variables are recommended).

### 1. File Paths

* **`QUEUE_DIR`**: Path to the folder monitored by the worker (Default: `./queue`).
* **`OUTPUT_DIR`**: Path where finished videos are saved (Default: `./matches`).
* **`ASSETS_DIR`**: Location of intro/outro clips (Default: `./assets`).

### 2. Branding Assets

The system expects specific filenames in the `logos/` and `assets/` directories.

* **Intro Video:** `assets/intro.mp4`
* **Outro Video:** `assets/outro.mp4`
* **Watermark:** `logos/HLS TAPMAD LOGO.png` (Used for HLS streams)
* **Overlay:** `logos/MOMENT TAPMAD LOGO.png` (Used for highlight moments)

### 3. Processing Variables (in `script.py`)

* **`OCR_CONFIDENCE`**: (Optional) Threshold for text detection accuracy.
* **`VIDEO_BITRATE`**: Target bitrate for the output video (e.g., `4000k`).
* **`FFMPEG_PRESET`**: Encoding speed (e.g., `ultrafast` for speed, `medium` for quality).

---

## 🔍 How It Works (Workflow)

### Step 1: Ingestion

The user opens `index.html` and selects a video source or stream. The frontend sends a request to the FastAPI server (`server_fastapi.py`).

### Step 2: Queuing

The server does not process the video immediately. Instead, it creates a simplified text or JSON file in the `queue/` directory containing the job details:

```json
{
  "job_id": "12345",
  "source_url": "rtmp://...",
  "branding_type": "full_match"
}

```

### Step 3: Execution

The `worker.py` process detects this new file. It parses the instructions and calls `script.py` with the necessary arguments.

### Step 4: Processing (`script.py`)

This script performs the heavy lifting:

1. **Download/Stream:** Fetches the source video.
2. **Stitch:** Concatenates `assets/intro.mp4` + [Main Video] + `assets/outro.mp4`.
3. **Overlay:** Applies the PNG from `logos/` to the specific coordinates defined in the script.
4. **OCR (Optional):** Scans specific frames to read scoreboards or detect game events if enabled.
5. **Render:** Exports the final file to the `matches/` directory.

### Step 5: Cleanup

Once processing is complete, the worker removes the job file from `queue/` and marks the task as done.

---

## 🚀 Deployment Guide (Linux/Ubuntu)

### 1. System Preparation

Update the server and install **FFmpeg** (crucial for video processing) and Python tools.

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install ffmpeg python3-venv unzip -y

```

### 2. Installation

Clone the project to your server and set up the environment.

```bash
# 1. Setup Virtual Environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install Dependencies
pip install -r requirements.txt

# 3. Make Scripts Executable
chmod +x *.sh

```

### 3. Production Run (Detached Mode)

Use the included `run_production.sh` script to start both the Server and the Worker in the background. This ensures they keep running even if you close your terminal.

```bash
./run_production.sh

```

### 4. Stopping the System

To stop all running processes safely:

```bash
./stop.sh

```

### 5. Maintenance (Restart Worker)

If the worker process hangs or you deploy code changes to `script.py`:

```bash
./restart_worker.sh

```

---

## 🔌 API Reference (Internal)

Although the system is primarily driven by the UI, the backend exposes endpoints (default port: 8000).

* **`GET /`**: Serves the `index.html` dashboard.
* **`GET /streams`**: Serves the `streams.html` monitoring page.
* **`POST /process`** (Example): Accepts JSON payload to trigger a new job.
* *Payload:* `{"url": "...", "type": "highlight"}`


* **`GET /status`**: Returns the current length of the queue.

---

## 🛠 Troubleshooting

| Issue | Possible Cause | Solution |
| --- | --- | --- |
| **Video output is missing** | FFmpeg failure | Check if `ffmpeg` is installed: `ffmpeg -version` |
| **Worker not processing** | Queue permissions | Ensure the `queue/` folder is writable by the user running the script. |
| **Scripts won't run** | Permission denied | Run `chmod +x *.sh` to make them executable. |
| **"Module not found"** | Venv not active | Ensure you ran `source .venv/bin/activate` before starting. |



