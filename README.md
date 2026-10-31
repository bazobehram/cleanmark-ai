# 🧼 CleanMark AI — Watermark Inpainter & Social Media Format Studio

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Angular 22](https://img.shields.io/badge/Angular-22-DD0031?logo=angular&logoColor=white)](https://angular.dev/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.9%2B-5C3EE8?logo=opencv&logoColor=white)](https://opencv.org/)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-Powered-007808?logo=ffmpeg&logoColor=white)](https://ffmpeg.org/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](./LICENSE)

**CleanMark AI** is a full-stack web studio that removes unwanted watermarks, logos, and text overlays from images and videos without degrading original quality, while simultaneously converting media into social-ready aspect ratios (**Instagram 4:5 Portrait Feed**, **9:16 Reels/TikTok/Shorts**, **1:1 Square**, and **16:9 Landscape**).

---

## ✨ Key Features

### 1. Intelligent Watermark Detection & Inpainting
* **Automatic Watermark Detection (`WatermarkDetector`):** Uses morphological Top-Hat filtering and multi-frame temporal stability analysis across corner regions of interest (ROIs) to automatically locate static logos and watermarks (e.g., AI video generator badges, TikTok/CapCut overlays).
* **Silhouette-Aware Video Inpainting (`VideoCleaner`):** Rather than blurring an entire rectangular bounding box, CleanMark extracts the exact contour silhouette of the watermark across sampled video frames and inpaints only the watermark pixels using **Telea** (`cv2.INPAINT_TELEA`) or **Navier-Stokes** (`cv2.INPAINT_NS`) algorithms via real-time FFmpeg raw-video piping.
* **Classic FFmpeg `delogo` Mode:** Optional ultra-fast spatial interpolation filter for simple rectangular watermark removal.
* **Interactive Canvas Studio:** Click-to-place smart bounding boxes, drag-to-draw custom multi-region masks, or use one-click presets for common watermark positions.

### 2. Social Media Aspect Ratio & Framing Converter
* **Target Aspect Ratios (`MediaConverter`):**
  * **4:5 Vertical Feed (`1080×1350`):** Maximum screen real estate on the Instagram main feed without cropping.
  * **9:16 Full Vertical (`1080×1920`):** Full-screen vertical format for Instagram Reels, TikTok, and YouTube Shorts.
  * **1:1 Square (`1080×1080`):** Classic square post layout.
  * **16:9 Widescreen (`1920×1080`):** Standard horizontal video/image format.
* **Framing Modes:**
  * **Fit & Blur (`blur_background`):** Preserves 100% of the original frame centered over a Gaussian-blurred, scaled background projection.
  * **Fill & Zoom (`crop_center`):** Scales and center-crops media to fill the entire target canvas.
  * **Letterbox / Pillarbox (`pad_black`):** Preserves aspect ratio with clean black bars.
* **Live Interactive Showcase Preview:** Real-time social UI simulation showing how your media will look on Instagram/TikTok before processing.

### 3. Asynchronous Task Pipeline & Process Control
* **Non-Blocking Background Processing:** Long-running video jobs run in background worker threads with real-time progress percentage reporting (`/api/tasks/{task_id}`).
* **Instant Task Cancellation:** Cancel active video encodings at any time (`/api/tasks/{task_id}/cancel`) with immediate FFmpeg subprocess termination and cleanup.
* **Session Persistence:** Automatically restores active uploads and in-progress tasks across page reloads.

---

## 🏗️ Architecture & Tech Stack

```
cleanmark/
├── app/
│   ├── main.py                      # FastAPI application, REST endpoints & async task manager
│   ├── config.py                    # Environment settings & storage directory setup
│   ├── services/
│   │   ├── watermark_detector.py    # Morphological Top-Hat & temporal watermark auto-detection
│   │   ├── image_cleaner.py         # OpenCV Telea/NS image inpainting (EXIF & RGBA aware)
│   │   ├── video_cleaner.py         # Single-pass FFmpeg + OpenCV silhouette video inpainting engine
│   │   └── converter.py             # FFmpeg & Pillow aspect-ratio & framing converter
│   └── static/                      # Pre-built Angular 22 production SPA bundle
├── frontend/                        # Angular 22 standalone frontend source (Signals + Tailwind CSS)
│   └── src/app/
│       ├── components/              # Uploader, Interactive Canvas Selector, Showcase & Preview UI
│       ├── services/                # Reactive state & API polling service
│       └── models/                  # TypeScript interfaces
├── tests/                           # Pytest unit & integration suites (API, cleaners, converters)
├── data/                            # Runtime working directories (uploads, cleaned, temp, metadata)
├── Dockerfile                       # Container image definition (Python 3.11 + FFmpeg + OpenCV)
└── docker-compose.yml               # Single-command container orchestration
```

---

## 🚀 Getting Started

### Option 1: Run with Docker (Recommended)

Make sure [Docker](https://docs.docker.com/get-docker/) and Docker Compose are installed.

```bash
# 1. Clone the repository
git clone https://github.com/bazobehram/cleanmark-ai.git
cd cleanmark-ai

# 2. (Optional) Create a custom .env file from the example template
cp .env.example .env

# 3. Build and start the container
docker compose up -d --build
```

Open **`http://localhost:8001`** in your browser.

---

### Option 2: Local Development Setup

#### Prerequisites
* **Python 3.10+**
* **FFmpeg** (`ffmpeg` and `ffprobe` available in your system `PATH`)
* **Node.js 20+** & **npm** (only required if modifying the Angular frontend)

#### 1. Backend Setup
```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows PowerShell

# Install Python dependencies
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env

# Start the FastAPI server (serves both API and built frontend on port 8001)
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

#### 2. Frontend Development (Optional)
If you want to edit the Angular UI with live reload:
```bash
cd frontend
npm install

# Starts Angular dev server on http://localhost:4200 (proxying /api to localhost:8001)
npm start

# To build production static assets into ../app/static:
npm run build
cp -r dist/cleanmark-frontend/browser/* ../app/static/
```

---

## 🔌 API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/upload` | Upload an image (`.jpg`, `.png`, `.webp`) or video (`.mp4`, `.mov`, `.webm`). Extracts dimensions, preview frame, and auto-detected watermark boxes. |
| `POST` | `/api/detect-watermark` | Run automatic watermark detection on an uploaded `file_id`. |
| `POST` | `/api/process` | Start an asynchronous job to remove watermarks and/or convert aspect ratio. Returns a `task_id`. |
| `GET` | `/api/tasks/{task_id}` | Poll real-time progress (`0-100%`), current step description, and final download URLs. |
| `POST` | `/api/tasks/{task_id}/cancel` | Immediately terminate a running processing task and its underlying FFmpeg processes. |
| `GET` | `/api/files/{folder}/{filename}` | Stream or download original, preview, or processed media files. |

---

## 🧪 Running Tests

The repository includes unit and integration tests covering image/video inpainting, RGBA transparency preservation, aspect-ratio conversions, and FastAPI endpoints.

```bash
pytest -v
```

---

## 🌐 Reverse Proxy (Nginx Example)

If deploying behind Nginx in production, increase `client_max_body_size` and proxy timeouts to support large video uploads:

```nginx
server {
    listen 80;
    server_name your-domain.example.com;

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        client_max_body_size 500M;
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
    }
}
```

---

## 📄 License

This project is free software: you can redistribute it and/or modify it under the terms of the **[GNU General Public License v3.0](./LICENSE)** as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
