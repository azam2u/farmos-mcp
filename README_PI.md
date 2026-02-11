
# FarmOS MCP Robot Controller - Raspberry Pi 5 Setup Guide

This guide details how to set up the FarmOS Robot Controller on a Raspberry Pi 5.

## Prerequisites
- Raspberry Pi 5 (8GB RAM recommended for LeRobot)
- Raspberry Pi OS (Bookworm) 64-bit
- Robot Arm (SO-100) connected via USB
- Robot Camera (Cam 0) connected via USB
- Secondary Camera (Cam 2) connected via USB (Different Controller recommended)
- Internet connection

## 1. System Dependencies
Install system libraries required for OpenCV and LeRobot:

```bash
sudo apt update
sudo apt install -y git python3-pip python3-venv \
    libopencv-dev python3-opencv \
    libatlas-base-dev gfortran \
    ffmpeg libsm6 libxext6 # OpenCV dependencies
```

## 2. Clone Repository
```bash
git clone https://github.com/azam2u/farmos-mcp.git
cd farmos-mcp
```

## 3. Python Environment
Create a virtual environment to avoid conflicts:

```bash
python3 -m venv venv
source venv/bin/activate
```

## 4. Install Python Packages
```bash
pip install -r requirements.txt
```

*Note: LeRobot installation on Pi might require building from source if wheels aren't available.*
```bash
# Ensure you have the latest version to support policies with embedded stats
pip install --upgrade "lerobot[pi]" 
# OR if that fails:
git clone https://github.com/huggingface/lerobot.git
cd lerobot
git pull
pip install -e .
cd ..
```

## 5. Configuration
Set your FarmOS credentials and LeRobot paths in `.env` (or export them):

```bash
export FARMOS_HOST="https://your.farmos.net"
export FARMOS_USER="admin"
export FARMOS_PASSWORD="password"
export LEROBOT_PYTHON_PATH="/home/pi/farmos-mcp/venv/bin/python" # Point to your venv python
```

## 6. Connectivity Test
Run the probe script to verify cameras are detected and bandwidth is managed:

```bash
# This verifies if both cameras can run simultaneously
python probe_concurrent.py
```

## 7. Run the MCP Server
```bash
python farmos_mcp.py
```

## Troubleshooting
- **Camera Failures**: If `probe_concurrent.py` fails, try moving the second camera to a different USB port. The Pi 5 has two USB 3.0 and two USB 2.0 ports; try splitting them.
- **LeRobot Lag**: Reduce the neural network size or quantization if the Pi 5 NPU isn't utilized.
