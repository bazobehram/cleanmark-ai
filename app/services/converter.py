import os
import subprocess
import logging
from typing import Tuple
import cv2
import numpy as np
from PIL import Image, ImageFilter, ImageOps

logger = logging.getLogger(__name__)

ASPECT_RATIOS = {
    "9:16": (1080, 1920),  # Reels, TikTok, Shorts
    "4:5":  (1080, 1350),  # Instagram Feed Portrait
    "1:1":  (1080, 1080),  # Instagram Square
    "16:9": (1920, 1080),  # YouTube / Landscape
}

class MediaConverter:
    @staticmethod
    def get_target_resolution(ratio: str) -> Tuple[int, int]:
        return ASPECT_RATIOS.get(ratio, (1080, 1920))

    @staticmethod
    def has_audio_stream(video_path: str) -> bool:
        """Videoda ses akışı olup olmadığını ffprobe ile kontrol eder."""
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-select_streams", "a:0",
                "-show_entries", "stream=codec_type",
                "-of", "csv=p=0",
                video_path
            ]
            out = subprocess.check_output(cmd, stderr=subprocess.PIPE, text=True)
            return "audio" in out.lower()
        except Exception:
            return False

    @classmethod
    def convert_video(
        cls,
        input_path: str,
        output_path: str,
        target_ratio: str = "4:5",
        mode: str = "blur_background"
    ) -> str:
        """
        Videoyu belirtilen Instagram/TikTok en-boy oranına (4:5, 9:16, 1:1, 16:9) dönüştürür.
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Girdi videosu bulunamadı: {input_path}")

        target_w, target_h = cls.get_target_resolution(target_ratio)
        audio_exists = cls.has_audio_stream(input_path)
        audio_args = ["-c:a", "copy"] if audio_exists else ["-an"]

        base_cmd = ["ffmpeg", "-y", "-i", input_path]
        encode_args = [
            "-c:v", "libx264",
            "-crf", "18",
            "-preset", "fast",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart"
        ]

        if mode == "crop_center":
            # Ortadan kırparak tüm ekranı doldur (Zoom & Fill)
            vf = f"scale={target_w}:{target_h}:force_original_aspect_ratio=increase,crop={target_w}:{target_h}"
            cmd = base_cmd + ["-vf", vf] + encode_args + audio_args + [output_path]

        elif mode == "pad_black":
            # Siyah çerçeve ile oran koru (Pillarbox/Letterbox)
            vf = f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:black"
            cmd = base_cmd + ["-vf", vf] + encode_args + audio_args + [output_path]

        else:
            # Bulanık arka plan (Fit & Blur - Önerilen ve en popüler)
            # Ön plan hem genişlik hem yükseklik sınırına göre küçültülür ve H.264 için çift sayıya yuvarlanır
            filter_complex = (
                f"[0:v]scale={target_w}:{target_h}:force_original_aspect_ratio=increase,crop={target_w}:{target_h},boxblur=25:5[bg];"
                f"[0:v]scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,pad=ceil(iw/2)*2:ceil(ih/2)*2[fg];"
                f"[bg][fg]overlay=(W-w)/2:(H-h)/2"
            )
            cmd = base_cmd + ["-filter_complex", filter_complex] + encode_args + audio_args + [output_path]

        logger.info(f"Video dönüştürme başlatılıyor ({target_ratio} - {mode}): {' '.join(cmd)}")
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode != 0:
            logger.error(f"FFmpeg conversion error: {proc.stderr}")
            raise RuntimeError(f"Video dönüştürme hatası: {proc.stderr[-300:]}")

        return output_path

    @classmethod
    def convert_image(
        cls,
        input_path: str,
        output_path: str,
        target_ratio: str = "4:5",
        mode: str = "blur_background"
    ) -> str:
        """
        Görseli belirtilen Instagram en-boy oranına (4:5, 9:16, 1:1, 16:9) dönüştürür.
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Görsel bulunamadı: {input_path}")

        target_w, target_h = cls.get_target_resolution(target_ratio)
        with Image.open(input_path) as raw_img:
            img = ImageOps.exif_transpose(raw_img)
            img = img.convert("RGB")

        orig_w, orig_h = img.size

        if mode == "crop_center":
            scale = max(target_w / orig_w, target_h / orig_h)
            new_w, new_h = int(round(orig_w * scale)), int(round(orig_h * scale))
            resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            left = (new_w - target_w) // 2
            top = (new_h - target_h) // 2
            result = resized.crop((left, top, left + target_w, top + target_h))

        elif mode == "pad_black":
            scale = min(target_w / orig_w, target_h / orig_h)
            new_w, new_h = int(round(orig_w * scale)), int(round(orig_h * scale))
            resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            result = Image.new("RGB", (target_w, target_h), (0, 0, 0))
            left = (target_w - new_w) // 2
            top = (target_h - new_h) // 2
            result.paste(resized, (left, top))

        else:
            # Bulanık arka plan (Fit & Blur)
            bg_scale = max(target_w / orig_w, target_h / orig_h)
            bg_w, bg_h = int(round(orig_w * bg_scale)), int(round(orig_h * bg_scale))
            bg = img.resize((bg_w, bg_h), Image.Resampling.BILINEAR)
            left = (bg_w - target_w) // 2
            top = (bg_h - target_h) // 2
            bg = bg.crop((left, top, left + target_w, top + target_h))
            bg = bg.filter(ImageFilter.GaussianBlur(radius=25))

            # Ön planı oranını koruyarak sığdır
            fg_scale = min(target_w / orig_w, target_h / orig_h)
            fg_w, fg_h = int(round(orig_w * fg_scale)), int(round(orig_h * fg_scale))
            fg = img.resize((fg_w, fg_h), Image.Resampling.LANCZOS)

            fg_left = (target_w - fg_w) // 2
            fg_top = (target_h - fg_h) // 2
            bg.paste(fg, (fg_left, fg_top))
            result = bg

        ext = os.path.splitext(output_path)[1].lower()
        if ext in (".jpg", ".jpeg"):
            result.save(output_path, "JPEG", quality=96, subsampling=0)
        elif ext == ".webp":
            result.save(output_path, "WEBP", quality=95)
        elif ext == ".png":
            result.save(output_path, "PNG", optimize=True)
        else:
            result.save(output_path)

        return output_path
