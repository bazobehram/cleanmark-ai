import os
import uuid
import json
import logging
from typing import List, Optional
from pydantic import BaseModel
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ImageOps

from app.config import settings
from app.services.image_cleaner import ImageCleaner
from app.services.video_cleaner import VideoCleaner
from app.services.converter import MediaConverter
from app.services.watermark_detector import WatermarkDetector

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("cleanmark")

app = FastAPI(
    title="CleanMark AI - Inpainter & Social Media Converter",
    description="Resim ve videolardan filigran silme ve Instagram/TikTok boyut dönüştürücü",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)

class BoxModel(BaseModel):
    x: int
    y: int
    w: int
    h: int

class ProcessRequest(BaseModel):
    file_id: str
    boxes: Optional[List[BoxModel]] = []
    clean_watermark: Optional[bool] = True
    method: Optional[str] = "telea"
    target_ratio: Optional[str] = "original"  # "original", "9:16", "4:5", "1:1", "16:9"
    framing_mode: Optional[str] = "blur_background"  # "blur_background", "crop_center", "pad_black"

files_registry = {}

def save_file_info(file_id: str, data: dict):
    files_registry[file_id] = data
    meta_path = os.path.join(settings.METADATA_DIR, f"{file_id}.json")
    try:
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Metadata kaydedilemedi ({file_id}): {e}")

def get_file_info(file_id: str) -> Optional[dict]:
    if file_id in files_registry:
        return files_registry[file_id]
    meta_path = os.path.join(settings.METADATA_DIR, f"{file_id}.json")
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                files_registry[file_id] = data
                return data
        except Exception as e:
            logger.warning(f"Metadata okunamadı ({file_id}): {e}")
    return None

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Dosya seçilmedi.")

    file_id = str(uuid.uuid4())[:8]
    ext = os.path.splitext(file.filename)[1].lower()
    save_name = f"{file_id}{ext}"
    save_path = os.path.join(settings.UPLOADS_DIR, save_name)

    with open(save_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    is_video = ext in (".mp4", ".mov", ".avi", ".mkv", ".webm")
    width, height = 0, 0
    preview_url = f"/api/files/uploads/{save_name}"

    if is_video:
        preview_img_name = f"{file_id}_preview.jpg"
        preview_img_path = os.path.join(settings.TEMP_DIR, preview_img_name)
        try:
            VideoCleaner.extract_first_frame(save_path, preview_img_path)
            preview_url = f"/api/files/temp/{preview_img_name}"
            with Image.open(preview_img_path) as im:
                width, height = im.size
        except Exception as e:
            logger.warning(f"Video preview extraction error: {e}")
            vid_w, vid_h = VideoCleaner.get_video_dimensions(save_path)
            width, height = (vid_w, vid_h) if vid_w > 0 else (1280, 720)
    else:
        try:
            with Image.open(save_path) as im:
                im = ImageOps.exif_transpose(im)
                width, height = im.size
        except Exception:
            width, height = 800, 600

    info = {
        "file_id": file_id,
        "original_name": file.filename,
        "path": save_path,
        "is_video": is_video,
        "ext": ext,
        "width": width,
        "height": height
    }

    suggested_boxes = []
    try:
        if is_video:
            suggested_boxes = WatermarkDetector.detect_video_watermarks(save_path)
        else:
            suggested_boxes = WatermarkDetector.detect_image_watermarks(save_path)
    except Exception as e:
        logger.warning(f"Watermark auto-detection error ({file_id}): {e}")

    info["suggested_boxes"] = suggested_boxes
    save_file_info(file_id, info)

    return {
        "file_id": file_id,
        "filename": file.filename,
        "is_video": is_video,
        "width": width,
        "height": height,
        "preview_url": preview_url,
        "original_url": f"/api/files/uploads/{save_name}",
        "suggested_boxes": suggested_boxes
    }

class DetectRequest(BaseModel):
    file_id: str

@app.post("/api/detect-watermark")
def detect_watermark_endpoint(req: DetectRequest):
    file_info = get_file_info(req.file_id)
    if not file_info:
        raise HTTPException(status_code=404, detail="Dosya bulunamadı.")
    
    file_path = file_info["path"]
    is_video = file_info.get("is_video", False)
    try:
        if is_video:
            boxes = WatermarkDetector.detect_video_watermarks(file_path)
        else:
            boxes = WatermarkDetector.detect_image_watermarks(file_path)
        return {"suggested_boxes": boxes}
    except Exception as e:
        logger.error(f"Detection error ({req.file_id}): {e}")
        return {"suggested_boxes": []}

@app.get("/api/video-frame/{file_id}")
def get_video_frame(file_id: str, time: float = 1.0):
    import subprocess
    file_info = get_file_info(file_id)
    if not file_info or not file_info.get("is_video"):
        raise HTTPException(status_code=404, detail="Video bulunamadı.")
    
    output_name = f"{file_id}_frame_{int(time*10)}.jpg"
    output_path = os.path.join(settings.TEMP_DIR, output_name)
    if not os.path.exists(output_path):
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(time),
            "-i", file_info["path"],
            "-vframes", "1",
            "-q:v", "2",
            output_path
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    if os.path.exists(output_path):
        return FileResponse(output_path, media_type="image/jpeg")
    raise HTTPException(status_code=500, detail="Kare çıkarılamadı.")

import threading

tasks_store = {}
cancellation_events = {}
active_task_processes = {}

def process_task_worker(task_id: str, req_data: dict):
    cancel_event = threading.Event()
    cancellation_events[task_id] = cancel_event
    active_task_processes[task_id] = []

    try:
        file_id = req_data["file_id"]
        raw_boxes = req_data.get("boxes", [])
        boxes = [b if isinstance(b, dict) else (b.model_dump() if hasattr(b, "model_dump") else b.dict()) for b in raw_boxes]
        clean_watermark = req_data.get("clean_watermark", True)
        method = req_data.get("method", "telea")
        target_ratio = req_data.get("target_ratio", "original")
        framing_mode = req_data.get("framing_mode", "blur_background")

        file_info = get_file_info(file_id)
        if not file_info:
            tasks_store[task_id] = {
                "task_id": task_id,
                "file_id": file_id,
                "status": "failed",
                "progress": 0,
                "step": "Dosya bulunamadı",
                "error": "Yüklenen dosya bulunamadı.",
                "result": None
            }
            return

        input_file = file_info["path"]
        is_video = file_info["is_video"]
        ext = file_info["ext"]
        final_output_name = f"processed_{task_id}_{file_id}{ext}"
        final_output_path = os.path.join(settings.CLEANED_DIR, final_output_name)

        def update_progress(pct: int, msg: str):
            if task_id in tasks_store and tasks_store[task_id]["status"] != "cancelled":
                tasks_store[task_id]["progress"] = pct
                tasks_store[task_id]["step"] = msg

        if is_video:
            # Video: Tek geçişli optimize motor ile AI inpainting veya delogo ve format dönüştürme
            boxes_to_clean = boxes if clean_watermark else []
            VideoCleaner.process_pipeline(
                video_path=input_file,
                boxes=boxes_to_clean,
                output_path=final_output_path,
                target_ratio=target_ratio,
                framing_mode=framing_mode,
                method=method,
                progress_callback=update_progress,
                cancel_check=lambda: cancel_event.is_set(),
                process_tracker=lambda p: active_task_processes.setdefault(task_id, []).append(p)
            )
        else:
            # Görsel işleme
            current_working_file = input_file
            update_progress(15, "Görsel yükleniyor...")

            if clean_watermark and boxes:
                update_progress(40, f"Filigran {method.upper()} algoritmasıyla siliniyor...")
                temp_cleaned_name = f"step1_{file_id}{ext}"
                temp_cleaned_path = os.path.join(settings.TEMP_DIR, temp_cleaned_name)
                ImageCleaner.clean(input_file, boxes, temp_cleaned_path, method=method)
                current_working_file = temp_cleaned_path

            if cancel_event.is_set():
                raise RuntimeError("İşlem kullanıcı tarafından iptal edildi.")

            if target_ratio and target_ratio != "original":
                update_progress(75, f"Instagram {target_ratio} formatına dönüştürülüyor...")
                MediaConverter.convert_image(
                    current_working_file,
                    final_output_path,
                    target_ratio=target_ratio,
                    mode=framing_mode
                )
            else:
                import shutil
                shutil.copyfile(current_working_file, final_output_path)

        if cancel_event.is_set():
            tasks_store[task_id] = {
                "task_id": task_id,
                "file_id": file_id,
                "status": "cancelled",
                "progress": 0,
                "step": "İşlem iptal edildi.",
                "error": None,
                "result": None
            }
            return

        result_payload = {
            "success": True,
            "processed_file_id": file_id,
            "is_video": is_video,
            "target_ratio": target_ratio,
            "cleaned_url": f"/api/files/cleaned/{final_output_name}",
            "filename": final_output_name,
            "download_url": f"/api/files/cleaned/{final_output_name}"
        }

        tasks_store[task_id] = {
            "task_id": task_id,
            "file_id": file_id,
            "status": "completed",
            "progress": 100,
            "step": "İşlem başarıyla tamamlandı!",
            "error": None,
            "result": result_payload
        }

    except Exception as e:
        if cancel_event.is_set() or "iptal" in str(e).lower():
            logger.info(f"Task cancelled ({task_id})")
            tasks_store[task_id] = {
                "task_id": task_id,
                "file_id": req_data.get("file_id"),
                "status": "cancelled",
                "progress": 0,
                "step": "İşlem kullanıcı tarafından iptal edildi.",
                "error": None,
                "result": None
            }
        else:
            logger.exception(f"Background task error ({task_id}): {e}")
            tasks_store[task_id] = {
                "task_id": task_id,
                "file_id": req_data.get("file_id"),
                "status": "failed",
                "progress": 0,
                "step": "Hata oluştu",
                "error": str(e),
                "result": None
            }
    finally:
        active_task_processes.pop(task_id, None)

@app.post("/api/process")
def process_media(req: ProcessRequest):
    file_info = get_file_info(req.file_id)
    if not file_info:
        raise HTTPException(status_code=404, detail="Yüklenen dosya bulunamadı.")

    task_id = str(uuid.uuid4())[:8]
    tasks_store[task_id] = {
        "task_id": task_id,
        "file_id": req.file_id,
        "status": "processing",
        "progress": 5,
        "step": "İşlem sıraya alındı...",
        "error": None,
        "result": None
    }

    req_dict = req.model_dump() if hasattr(req, "model_dump") else req.dict()
    worker_thread = threading.Thread(target=process_task_worker, args=(task_id, req_dict), daemon=True)
    worker_thread.start()

    return {
        "task_id": task_id,
        "status": "processing"
    }

@app.get("/api/tasks/{task_id}")
def get_task_status(task_id: str):
    task = tasks_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Görev bulunamadı.")
    return task

@app.post("/api/tasks/{task_id}/cancel")
def cancel_task_endpoint(task_id: str):
    task = tasks_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Görev bulunamadı.")

    # İptal bayrağını tetikle
    if task_id in cancellation_events:
        cancellation_events[task_id].set()

    # Çalışan FFmpeg süreçlerini anında sonlandır
    procs = active_task_processes.get(task_id, [])
    for p in procs:
        try:
            p.terminate()
            p.kill()
        except Exception:
            pass

    task["status"] = "cancelled"
    task["step"] = "İşlem kullanıcı tarafından iptal edildi."

    return {
        "success": True,
        "task_id": task_id,
        "status": "cancelled",
        "message": "Görev başarıyla iptal edildi."
    }

@app.get("/api/files/{folder}/{filename}")
def serve_file(folder: str, filename: str):
    safe_filename = os.path.basename(filename)
    if folder == "uploads":
        base_path = settings.UPLOADS_DIR
    elif folder == "cleaned":
        base_path = settings.CLEANED_DIR
    elif folder == "temp":
        base_path = settings.TEMP_DIR
    else:
        raise HTTPException(status_code=400, detail="Geçersiz dizin.")

    file_path = os.path.join(base_path, safe_filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Dosya bulunamadı.")

    media_type = "video/mp4" if safe_filename.endswith((".mp4", ".mov", ".webm")) else "image/jpeg"
    return FileResponse(
        file_path,
        media_type=media_type,
        filename=safe_filename,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )

@app.api_route("/{full_path:path}", methods=["GET", "HEAD"])
async def serve_angular(request: Request, full_path: str):
    safe_path = os.path.normpath(full_path).lstrip("/\\")
    candidate = os.path.join(static_dir, safe_path)
    if full_path and os.path.exists(candidate) and os.path.isfile(candidate):
        return FileResponse(candidate)

    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)

    return JSONResponse(
        status_code=200,
        content={"message": "CleanMark AI API çalışıyor."}
    )
