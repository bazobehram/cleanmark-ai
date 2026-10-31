import os
import io
import pytest
from fastapi.testclient import TestClient
from PIL import Image
import numpy as np

from app.main import app, get_file_info
from app.config import settings

client = TestClient(app)

@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    uploads = tmp_path / "uploads"
    cleaned = tmp_path / "cleaned"
    temp = tmp_path / "temp"
    metadata = tmp_path / "metadata"
    for d in (uploads, cleaned, temp, metadata):
        d.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "UPLOADS_DIR", str(uploads))
    monkeypatch.setattr(settings, "CLEANED_DIR", str(cleaned))
    monkeypatch.setattr(settings, "TEMP_DIR", str(temp))
    monkeypatch.setattr(settings, "METADATA_DIR", str(metadata))

@pytest.fixture
def sample_image():
    buf = io.BytesIO()
    img = Image.new("RGB", (400, 400), color=(100, 150, 200))
    img.save(buf, format="JPEG")
    buf.seek(0)
    return ("sample.jpg", buf.getvalue(), "image/jpeg")

def test_api_upload_and_process_image(sample_image):
    fname, fbytes, mtype = sample_image
    
    # 1. Upload Test
    response = client.post(
        "/api/upload",
        files={"file": (fname, fbytes, mtype)}
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert "file_id" in data
    assert data["filename"] == fname
    assert data["is_video"] is False
    assert data["width"] == 400
    assert data["height"] == 400

    file_id = data["file_id"]
    
    # Check persistent metadata
    meta = get_file_info(file_id)
    assert meta is not None
    assert meta["width"] == 400

    # 2. Process Test (Inpaint + 4:5 Aspect Ratio)
    proc_res = client.post(
        "/api/process",
        json={
            "file_id": file_id,
            "boxes": [{"x": 10, "y": 10, "w": 50, "h": 50}],
            "clean_watermark": True,
            "method": "telea",
            "target_ratio": "4:5",
            "framing_mode": "blur_background"
        }
    )
    assert proc_res.status_code == 200, proc_res.text
    task_init = proc_res.json()
    assert "task_id" in task_init
    task_id = task_init["task_id"]

    # Poll task status until complete
    import time
    pdata = None
    for _ in range(30):
        t_res = client.get(f"/api/tasks/{task_id}")
        assert t_res.status_code == 200
        t_data = t_res.json()
        if t_data["status"] == "completed":
            pdata = t_data["result"]
            break
        elif t_data["status"] == "failed":
            pytest.fail(f"Task failed: {t_data.get('error')}")
        time.sleep(0.1)

    assert pdata is not None, "Task timed out"
    assert pdata["success"] is True
    assert pdata["target_ratio"] == "4:5"
    assert "cleaned_url" in pdata

    # 3. Serve File Test
    cleaned_filename = pdata["filename"]
    serve_res = client.get(f"/api/files/cleaned/{cleaned_filename}")
    assert serve_res.status_code == 200
    assert len(serve_res.content) > 0

    # Verify output dimensions (4:5 -> 1080x1350)
    with Image.open(io.BytesIO(serve_res.content)) as out_img:
        assert out_img.size == (1080, 1350)

def test_api_upload_no_file():
    res = client.post("/api/upload", files={})
    assert res.status_code in (400, 422)

def test_api_process_invalid_file_id():
    res = client.post(
        "/api/process",
        json={
            "file_id": "nonexistent999",
            "boxes": [],
            "clean_watermark": False,
            "target_ratio": "1:1"
        }
    )
    assert res.status_code == 404

def test_api_serve_nonexistent():
    res = client.get("/api/files/cleaned/doesnotexist.jpg")
    assert res.status_code == 404

def test_spa_serving():
    res = client.get("/")
    assert res.status_code == 200
    assert "CleanMark" in res.text or "<app-root>" in res.text or "<!doctype html>" in res.text.lower()

def test_api_upload_and_process_video(tmp_path):
    # Generate small 1s synthetic video
    import subprocess
    vid_file = tmp_path / "api_test.mp4"
    proc = subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=15",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(vid_file)
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.returncode == 0

    with open(vid_file, "rb") as f:
        vid_bytes = f.read()

    # Upload video
    up_res = client.post(
        "/api/upload",
        files={"file": ("api_test.mp4", vid_bytes, "video/mp4")}
    )
    assert up_res.status_code == 200
    up_data = up_res.json()
    assert up_data["is_video"] is True
    file_id = up_data["file_id"]

    # Process video with watermark clean and aspect ratio convert to 9:16
    proc_res = client.post(
        "/api/process",
        json={
            "file_id": file_id,
            "boxes": [{"x": 10, "y": 10, "w": 30, "h": 30}],
            "clean_watermark": True,
            "target_ratio": "9:16",
            "framing_mode": "blur_background"
        }
    )
    assert proc_res.status_code == 200
    task_init = proc_res.json()
    assert "task_id" in task_init
    task_id = task_init["task_id"]

    import time
    pdata = None
    for _ in range(50):
        t_res = client.get(f"/api/tasks/{task_id}")
        assert t_res.status_code == 200
        t_data = t_res.json()
        if t_data["status"] == "completed":
            pdata = t_data["result"]
            break
        elif t_data["status"] == "failed":
            pytest.fail(f"Video task failed: {t_data.get('error')}")
        time.sleep(0.1)

    assert pdata is not None, "Video task timed out"
    assert pdata["success"] is True
    assert pdata["is_video"] is True
    assert pdata["target_ratio"] == "9:16"

    # Download cleaned video
    serve_res = client.get(f"/api/files/cleaned/{pdata['filename']}")
    assert serve_res.status_code == 200
    assert len(serve_res.content) > 0

