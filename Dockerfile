# 1. Use NVIDIA CUDA base image instead of plain Python
# This is required for GPU acceleration
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

# --- Suggestion 3: Set environment variables ---
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# 2. Install Python and system dependencies
# We need to install python3-pip manually since we aren't using a python image
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3-pip \
    python3-dev \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# 3. Fix Python alias (since ubuntu uses 'python3')
RUN ln -s /usr/bin/python3 /usr/bin/python

# Copy requirements
COPY requirements.txt .

# 1. Upgrade pip
# 2. Install Torch with CUDA 11.8 support explicitly
# 3. Install the rest of the requirements
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118 && \
    pip install --no-cache-dir -r requirements.txt

# 4. Pre-download EasyOCR models (during build)
# This ensures the models are ready and verified before you start the app
RUN python3 -c "import easyocr; reader = easyocr.Reader(['en'], gpu=True)"

# Ensure necessary directories exist
RUN mkdir -p matches branded_output queue errors

# Copy the entire project
COPY . .

# Expose the FastAPI port
EXPOSE 5003

# Give execution permissions
RUN chmod +x run.sh run_production.sh restart_worker.sh stop.sh

# Use run.sh as the starting command
CMD ["./run.sh"]