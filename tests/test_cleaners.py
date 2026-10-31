import os
import shutil
import tempfile
import pytest
import numpy as np
import cv2
from PIL import Image

from app.services.image_cleaner import ImageCleaner
from app.services.video_cleaner import VideoCleaner
from app.services.converter import MediaConverter, ASPECT_RATIOS

@pytest.fixture
def test_dir():
    temp_d = tempfile.mkdtemp(prefix="cleanmark_test_")
    yield temp_d
    shutil.rmtree(temp_d, ignore_errors=True)

def test_image_cleaner_telea_and_ns(test_dir):
    # 200x200 test görseli oluştur
    img_path = os.path.join(test_dir, "test_input.jpg")
    img_data = np.full((200, 200, 3), 120, dtype=np.uint8)
    # 20x20 beyaz logo çiz
    img_data[80:100, 80:100] = 255
    cv2.imwrite(img_path, img_data)

    out_telea = os.path.join(test_dir, "out_telea.jpg")
    ImageCleaner.clean(img_path, [{"x": 80, "y": 80, "w": 20, "h": 20}], out_telea, method="telea")
    assert os.path.exists(out_telea)
    result_telea = cv2.imread(out_telea)
    assert result_telea.shape == (200, 200, 3)
    # Filigran alanının artık saf beyaz (255, 255, 255) olmadığını doğrula
    center_val = result_telea[90, 90]
    assert np.mean(center_val) < 240

    out_ns = os.path.join(test_dir, "out_ns.jpg")
    ImageCleaner.clean(img_path, [{"x": 80, "y": 80, "w": 20, "h": 20}], out_ns, method="ns")
    assert os.path.exists(out_ns)

def test_image_cleaner_rgba_transparency(test_dir):
    png_path = os.path.join(test_dir, "test_rgba.png")
    # 100x100 RGBA görsel
    rgba_data = np.zeros((100, 100, 4), dtype=np.uint8)
    rgba_data[:, :] = [50, 100, 150, 180]  # yarı şeffaf arka plan
    rgba_data[10:30, 10:30] = [255, 0, 0, 255]  # kırmızı logo
    Image.fromarray(rgba_data).save(png_path)

    out_png = os.path.join(test_dir, "out_rgba.png")
    ImageCleaner.clean(png_path, [{"x": 10, "y": 10, "w": 20, "h": 20}], out_png)
    assert os.path.exists(out_png)
    with Image.open(out_png) as res_im:
        assert res_im.mode == "RGBA"
        assert res_im.size == (100, 100)

def test_image_converter_ratios_and_modes(test_dir):
    # 800x600 görsel oluştur (Landscape)
    img_path = os.path.join(test_dir, "landscape.jpg")
    im = Image.new("RGB", (800, 600), color=(70, 130, 180))
    im.save(img_path)

    modes = ["blur_background", "crop_center", "pad_black"]
    for ratio_key, (tw, th) in ASPECT_RATIOS.items():
        for mode in modes:
            out_file = os.path.join(test_dir, f"conv_{ratio_key.replace(':', '_')}_{mode}.jpg")
            MediaConverter.convert_image(img_path, out_file, target_ratio=ratio_key, mode=mode)
            assert os.path.exists(out_file)
            with Image.open(out_file) as res_im:
                assert res_im.size == (tw, th), f"Expected {(tw, th)} for {ratio_key} {mode}, got {res_im.size}"

def test_video_cleaner_and_converter(test_dir):
    # FFmpeg ile 1 saniyelik 640x360 sentetik test videosu üret
    video_path = os.path.join(test_dir, "synth.mp4")
    import subprocess
    proc = subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=1:size=640x360:rate=24",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", video_path
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.returncode == 0
    assert os.path.exists(video_path)

    # 1. Video Boyut Tespiti
    w, h = VideoCleaner.get_video_dimensions(video_path)
    assert (w, h) == (640, 360)

    # 2. İlk Kare Çıkarma
    preview_path = os.path.join(test_dir, "preview.jpg")
    VideoCleaner.extract_first_frame(video_path, preview_path)
    assert os.path.exists(preview_path)
    with Image.open(preview_path) as prev_im:
        assert prev_im.size == (640, 360)

    # 3. Video Delogo ile Temizleme (Sağ alt köşe ve sınır aşma testi)
    cleaned_video = os.path.join(test_dir, "cleaned.mp4")
    # Video 640x360, x=550, w=100 sınır dışına taşar; clamping test edilir
    boxes = [{"x": 550, "y": 300, "w": 100, "h": 70}]
    VideoCleaner.clean(video_path, boxes, cleaned_video)
    assert os.path.exists(cleaned_video)
    cw, ch = VideoCleaner.get_video_dimensions(cleaned_video)
    assert (cw, ch) == (640, 360)

    # 4. Video Boyut Dönüştürme (4:5 Fit & Blur)
    conv_video = os.path.join(test_dir, "converted_4_5.mp4")
    MediaConverter.convert_video(cleaned_video, conv_video, target_ratio="4:5", mode="blur_background")
    assert os.path.exists(conv_video)
    vw, vh = VideoCleaner.get_video_dimensions(conv_video)
    assert (vw, vh) == (1080, 1350)
