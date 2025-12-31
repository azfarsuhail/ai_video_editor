# Video Branding & Automated Highlights System (v2.0 - RTX 4060 Optimized)

## 📖 Project Overview

This project is a mission-critical, high-performance automated video processing pipeline designed for sports highlights and real-time branding. It utilizes a decoupled architecture where a **FastAPI** backend orchestrates multiple **AI Match Engines** and a dedicated **Hybrid Branding Worker**. The system is fully optimized for **NVIDIA RTX 4060** hardware, leveraging GPU-accelerated OCR and hardware-accelerated video encoding.

---

## 📂 System Architecture

The system follows a **Producer-Consumer** pattern to ensure the API remains responsive while heavy AI analysis and video rendering tasks occur in the background.

1. 
**The Brain (API):** `server_fastapi.py` manages multi-stream sessions and job orchestration.


2. 
**The Eye (AI Engine):** `script.py` connects to live SRT/UDP streams and uses a triple-trigger system (OCR, Audio, and Motion) to detect events and cut clips.


3. **The Muscle (Worker):** `worker.py` is a dedicated branding pipeline that uses **FFmpeg with NVENC** for near-instant video stitching and logo overlays.
4. 
**The Guardian (Ops):** Shell scripts manage auto-restarts and prevent "zombie" processes from locking hardware resources.



### Directory Structure

```text
.
[cite_start]├── active_sessions/         # Tracks live recording processes [cite: 4]
├── assets/                  # Intro/outro clips (Standard and Vertical)
[cite_start]├── branded_output/          # Final production-ready branded videos [cite: 4]
[cite_start]├── logos/                   # Branding overlays (transparent PNGs) [cite: 4]
[cite_start]├── matches/                 # Raw clip storage and full match recordings [cite: 3, 4]
[cite_start]├── queue/                   # File-based job queue for the worker [cite: 4]
[cite_start]├── errors/                  # Error logs for failed branding attempts [cite: 4]
[cite_start]├── server_fastapi.py        # Central management & API hub [cite: 4]
[cite_start]├── script.py                # AI event detection & clipping logic [cite: 3]
├── worker.py                # Hybrid FFmpeg processing pipeline
[cite_start]├── Dockerfile               # NVIDIA CUDA-optimized environment [cite: 1]
[cite_start]└── *.sh                     # Operation control and safety scripts [cite: 5]

```

---

## ⚙️ Core Technical Features

### 1. AI-Powered Event Detection (`script.py`)

The system monitors live streams using three concurrent detection methods:

* 
**RTX 4060 GPU OCR:** Scans the scorebar ROI every 0.4s for keywords like "4", "6", "WICKET", or "OUT".


* 
**Audio Sustain Analysis:** Monitors crowd roars by calculating RMS volume levels. A trigger occurs if loud audio (above 0.65) is sustained for 0.3s.


* 
**Motion Spikes:** Identifies massive visual changes (e.g., wicket celebrations) using frame differencing.



### 2. Hybrid Branding Pipeline (`worker.py`)

The worker handles both standard (16:9) and social-ready vertical (9:16) formats:

* **Auto-Vertical Detection:** Detects if a clip is a "Reel" based on filename and automatically swaps to vertical-optimized assets.
* **Logo Overlays:** Applies scaled logos (15% for standard, 25% for reels) to specific top-right coordinates.
* 
**Hardware Acceleration:** Configured to use NVIDIA hardware features for lower latency rendering.



### 3. Management Dashboard

* 
**Live Stream Manager:** A protected interface to launch and monitor multiple engines simultaneously.


* **Batch Mode:** A specialized UI in `index.html` allowing users to select multiple clips and apply branding in bulk.
* 
**Live Terminal Logs:** Real-time log streaming directly to the browser for match monitoring.



---

## 🚀 Deployment Guide (Docker / Cloud)

### 1. System Preparation

* 
**Drivers:** NVIDIA drivers and the NVIDIA Container Toolkit must be installed on the host.


* **Storage:** Ensure significant free space; 1080p recordings can result in 10-15GB files per match.



### 2. Build and Launch

```bash
# Start the mission-critical environment
docker compose up -d --build

```

### 3. Operations & Maintenance

* 
**`run_production.sh`:** Starts server and worker guardians that auto-restart if a service crashes.


* **`stop.sh`:** Emergency protocol that stops all services and forcefully clears FFmpeg "zombies" to free GPU VRAM.
* **`restart_worker.sh`:** Restarts the branding engine without interrupting active stream recording.

---

## 🛠 Troubleshooting

| Issue | Possible Cause | Solution |
| --- | --- | --- |
| **GPU not used** | Missing Docker reservation | Check `deploy` block in `docker-compose.yml`.

 |
| **OCR Error** | Corrupted models | Clear `~/.EasyOCR/model/*` and rebuild.

 |
| **Build Failure** | Missing CUDA Torch | Ensure `requirements.txt` uses the CUDA index for torch. |
| **No Clipping** | Seeking error | Ensure `-ss` is placed before `-i` in `script.py`.

 |

---