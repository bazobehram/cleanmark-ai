import subprocess
import os
import logging
from typing import List, Dict, Any, Tuple, Optional, Callable
import cv2
import numpy as np
import shutil

logger = logging.getLogger(__name__)

class VideoCleaner:
    @staticmethod
    def get_video_dimensions(video_path: str) -> Tuple[int, int]:
        """Video çözünürlüğünü (genişlik, yükseklik) döndürür."""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return 0, 0
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        return w, h

    @staticmethod
    def get_video_duration(video_path: str) -> float:
        """Video süresini saniye cinsinden döndürür."""
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "csv=p=0",
                video_path
            ]
            out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True).strip()
            return max(0.1, float(out))
        except Exception:
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
            frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
            cap.release()
            return max(0.1, frames / fps if frames > 0 else 5.0)

    @staticmethod
    def get_video_fps(video_path: str) -> float:
        """Video kare hızını (FPS) döndürür."""
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=r_frame_rate",
                "-of", "csv=p=0",
                video_path
            ]
            out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True).strip()
            if "/" in out:
                num, den = out.split("/")
                return float(num) / max(1.0, float(den))
            return float(out)
        except Exception:
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            cap.release()
            return fps if fps > 0 else 30.0

    @classmethod
    def prepare_box_mask(cls, video_path: str, bx: int, by: int, bw: int, bh: int) -> np.ndarray:
        """
        Kutu içerisindeki filigran/logo siluetini (Kling AI, TikTok, CapCut vb.)
        farklı zamanlardaki kareleri karşılaştırarak hassas şekilde çıkarır.
        Böylece dikdörtgen bir bulanıklık yerine yalnızca filigran pikselleri onarılır.
        """
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        sample_frames = []
        for t_sec in [1.0, 3.0, 6.0, 15.0, 24.0, 45.0, 60.0]:
            frame_no = min(max(0, total - 1), int(t_sec * fps))
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
            ret, f = cap.read()
            if ret and f is not None and f.shape[0] >= by+bh and f.shape[1] >= bx+bw:
                sample_frames.append(f)
        cap.release()

        default_mask = np.zeros((bh, bw), dtype=np.uint8)
        cv2.ellipse(default_mask, (bw // 2, bh // 2), (max(2, bw // 2 - 4), max(2, bh // 2 - 4)), 0, 0, 360, 255, -1)

        if not sample_frames:
            return default_mask

        # Farklı karelerde filigran siluetini en net veren konturu ara
        best_contour = None
        best_score = -1

        for f in sample_frames:
            patch = f[by:by+bh, bx:bx+bw]
            gray = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)
            for th_val in (75, 60, 50, 40):
                _, thresh = cv2.threshold(gray, th_val, 255, cv2.THRESH_BINARY)
                cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                for c in cnts:
                    area = cv2.contourArea(c)
                    if 100 < area < (bw * bh * 0.7):
                        M = cv2.moments(c)
                        if M["m00"] > 0:
                            mcx = M["m10"] / M["m00"]
                            mcy = M["m01"] / M["m00"]
                            dist_center = np.hypot(mcx - bw / 2, mcy - bh / 2)
                            score = area / (1.0 + dist_center)
                            if score > best_score:
                                best_score = score
                                best_contour = c

        if best_contour is not None:
            mask = np.zeros((bh, bw), dtype=np.uint8)
            cv2.drawContours(mask, [best_contour], -1, 255, -1)
            # 3x3 hafif genişletme ile yarı saydam anti-aliased kenarları da kapsa
            mask = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
            return mask

        return default_mask

    @classmethod
    def clean(cls, video_path: str, boxes: List[Dict[str, int]], output_path: str) -> str:
        """Basit doğrudan temizleme."""
        return cls.process_pipeline(video_path, boxes, output_path, target_ratio="original", method="telea")

    @classmethod
    def process_pipeline(
        cls,
        video_path: str,
        boxes: List[Dict[str, int]],
        output_path: str,
        target_ratio: str = "original",
        framing_mode: str = "blur_background",
        method: str = "telea",
        progress_callback: Optional[Callable[[int, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
        process_tracker: Optional[Callable[[subprocess.Popen], None]] = None
    ) -> str:
        """
        Tek geçişli optimize video motoru:
        - method='telea' veya 'ns': Hassas AI Doku Onarımı (Lekesiz inpainting, pipe ile gerçek zamanlı akış).
        - method='delogo': Klasik FFmpeg delogo enterpolasyonu.
        - Anında işlem iptali desteği (cancel_check & process_tracker).
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Girdi videosu bulunamadı: {video_path}")

        duration = cls.get_video_duration(video_path)
        vid_w, vid_h = cls.get_video_dimensions(video_path)
        fps = cls.get_video_fps(video_path)

        if progress_callback:
            progress_callback(5, "Video parametreleri hazırlanıyor...")

        # Kutu koordinatlarını doğrula ve sınırlandır
        valid_boxes = []
        for b in (boxes or []):
            x = max(0, int(b.get("x", 0)))
            y = max(0, int(b.get("y", 0)))
            w = max(2, int(b.get("w", 0)))
            h = max(2, int(b.get("h", 0)))

            if vid_w > 0 and (x + w) > vid_w:
                w = max(2, vid_w - x)
            if vid_h > 0 and (y + h) > vid_h:
                h = max(2, vid_h - y)

            if vid_w > 0 and vid_h > 0:
                if x >= vid_w or y >= vid_h:
                    continue

            valid_boxes.append({"x": x, "y": y, "w": w, "h": h})

        # Ses akışı kontrolü
        has_audio = False
        try:
            probe_cmd = [
                "ffprobe", "-v", "error",
                "-select_streams", "a:0",
                "-show_entries", "stream=codec_type",
                "-of", "csv=p=0",
                video_path
            ]
            probe_out = subprocess.check_output(probe_cmd, stderr=subprocess.DEVNULL, text=True)
            has_audio = "audio" in probe_out.lower()
        except Exception:
            has_audio = False

        from app.services.converter import MediaConverter
        needs_ratio_convert = target_ratio and target_ratio != "original"

        # -------------------------------------------------------------
        # 1. AI INPAINTING MOTORU (Telea / NS) - Ultra Net, Lekesiz
        # -------------------------------------------------------------
        if valid_boxes and method in ("telea", "ns"):
            inpaint_flag = cv2.INPAINT_TELEA if method == "telea" else cv2.INPAINT_NS
            if progress_callback:
                progress_callback(8, "Filigran AI silueti analiz ediliyor...")

            # Her kutu için hassas filigran maskesini hazırla
            box_masks = []
            for b in valid_boxes:
                m = cls.prepare_box_mask(video_path, b["x"], b["y"], b["w"], b["h"])
                box_masks.append((b, m))

            # Geçici video çıktı yolu (ses miksajından önce)
            temp_vid = output_path + ".temp_noaudio.mp4"
            if os.path.exists(temp_vid):
                try: os.remove(temp_vid)
                except: pass

            base_encode = [
                "-c:v", "libx264",
                "-crf", "18",
                "-preset", "fast",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart"
            ]

            # Writer filter complex
            if needs_ratio_convert:
                target_w, target_h = MediaConverter.get_target_resolution(target_ratio)
                if framing_mode == "crop_center":
                    fc = f"scale={target_w}:{target_h}:force_original_aspect_ratio=increase,crop={target_w}:{target_h}"
                elif framing_mode == "pad_black":
                    fc = f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:black"
                else:
                    # blur_background
                    fc = (
                        f"[0:v]split=2[v_bg][v_fg];"
                        f"[v_bg]scale={target_w}:{target_h}:force_original_aspect_ratio=increase,crop={target_w}:{target_h},boxblur=25:5[bg];"
                        f"[v_fg]scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,pad=ceil(iw/2)*2:ceil(ih/2)*2[fg];"
                        f"[bg][fg]overlay=(W-w)/2:(H-h)/2"
                    )
                writer_cmd = [
                    "ffmpeg", "-y",
                    "-f", "rawvideo", "-vcodec", "rawvideo",
                    "-s", f"{vid_w}x{vid_h}", "-pix_fmt", "bgr24", "-r", f"{fps}",
                    "-i", "pipe:0",
                    "-filter_complex", fc
                ] + base_encode + [temp_vid]
            else:
                writer_cmd = [
                    "ffmpeg", "-y",
                    "-f", "rawvideo", "-vcodec", "rawvideo",
                    "-s", f"{vid_w}x{vid_h}", "-pix_fmt", "bgr24", "-r", f"{fps}",
                    "-i", "pipe:0"
                ] + base_encode + [temp_vid]

            reader_cmd = [
                "ffmpeg",
                "-i", video_path,
                "-f", "rawvideo", "-pix_fmt", "bgr24", "pipe:1"
            ]

            reader = subprocess.Popen(reader_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            writer = subprocess.Popen(writer_cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            if process_tracker:
                process_tracker(reader)
                process_tracker(writer)

            frame_size = vid_w * vid_h * 3
            total_frames = max(1, int(duration * fps))
            frame_idx = 0

            try:
                while True:
                    if cancel_check and cancel_check():
                        logger.info("Video temizleme kullanıcı tarafından iptal edildi.")
                        reader.terminate()
                        writer.terminate()
                        if os.path.exists(temp_vid):
                            try: os.remove(temp_vid)
                            except: pass
                        raise RuntimeError("İşlem kullanıcı tarafından iptal edildi.")

                    raw = reader.stdout.read(frame_size)
                    if len(raw) < frame_size:
                        break

                    frame = np.frombuffer(raw, dtype=np.uint8).reshape((vid_h, vid_w, 3)).copy()

                    # Her kutudaki filigranı inpainting ile onar
                    for b, mask in box_masks:
                        bx, by, bw, bh = b["x"], b["y"], b["w"], b["h"]
                        patch = frame[by:by+bh, bx:bx+bw]
                        cleaned_patch = cv2.inpaint(patch, mask, 3, inpaint_flag)
                        frame[by:by+bh, bx:bx+bw] = cleaned_patch

                    writer.stdin.write(frame.tobytes())
                    frame_idx += 1

                    if frame_idx % 15 == 0 and progress_callback:
                        pct = min(92, max(10, int((frame_idx / total_frames) * 82) + 10))
                        progress_callback(pct, f"AI Doku Onarımı yapılıyor (%{pct})...")

            finally:
                try: reader.stdout.close()
                except: pass
                try: writer.stdin.close()
                except: pass
                reader.wait()
                writer.wait()

            if cancel_check and cancel_check():
                raise RuntimeError("İşlem kullanıcı tarafından iptal edildi.")

            # Ses varsa hızlıca miksle (0.05 sn)
            if has_audio:
                if progress_callback:
                    progress_callback(95, "Ses akışı birleştiriliyor...")
                mux_cmd = [
                    "ffmpeg", "-y",
                    "-i", temp_vid,
                    "-i", video_path,
                    "-c:v", "copy", "-c:a", "copy",
                    "-map", "0:v:0", "-map", "1:a:0?",
                    "-shortest",
                    output_path
                ]
                mux_proc = subprocess.Popen(mux_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if process_tracker:
                    process_tracker(mux_proc)
                mux_proc.wait()
                if os.path.exists(temp_vid):
                    try: os.remove(temp_vid)
                    except: pass
            else:
                if os.path.exists(output_path):
                    try: os.remove(output_path)
                    except: pass
                shutil.move(temp_vid, output_path)

            if progress_callback:
                progress_callback(100, "Tamamlandı!")

            return output_path

        # -------------------------------------------------------------
        # 2. DELOGO / KLASİK FİLTRE VEYA SADECE FORMAT DÖNÜŞTÜRME
        # -------------------------------------------------------------
        delogo_filters = []
        if valid_boxes:
            for b in valid_boxes:
                delogo_filters.append(f"delogo=x={b['x']}:y={b['y']}:w={b['w']}:h={b['h']}:show=0")

        delogo_str = ",".join(delogo_filters)
        audio_flags = ["-c:a", "copy"] if has_audio else ["-an"]
        base_encode = [
            "-c:v", "libx264",
            "-crf", "18",
            "-preset", "fast",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart"
        ]

        if needs_ratio_convert:
            target_w, target_h = MediaConverter.get_target_resolution(target_ratio)
            if framing_mode == "crop_center":
                if delogo_str:
                    filter_complex = f"[0:v]{delogo_str},scale={target_w}:{target_h}:force_original_aspect_ratio=increase,crop={target_w}:{target_h}"
                else:
                    filter_complex = f"scale={target_w}:{target_h}:force_original_aspect_ratio=increase,crop={target_w}:{target_h}"
                cmd = ["ffmpeg", "-y", "-i", video_path, "-vf", filter_complex] + base_encode + audio_flags + ["-progress", "pipe:1", output_path]

            elif framing_mode == "pad_black":
                if delogo_str:
                    filter_complex = f"[0:v]{delogo_str},scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:black"
                else:
                    filter_complex = f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:black"
                cmd = ["ffmpeg", "-y", "-i", video_path, "-vf", filter_complex] + base_encode + audio_flags + ["-progress", "pipe:1", output_path]

            else:
                # blur_background (Fit & Blur)
                if delogo_str:
                    filter_complex = (
                        f"[0:v]{delogo_str}[cleaned];"
                        f"[cleaned]split=2[v_bg][v_fg];"
                        f"[v_bg]scale={target_w}:{target_h}:force_original_aspect_ratio=increase,crop={target_w}:{target_h},boxblur=25:5[bg];"
                        f"[v_fg]scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,pad=ceil(iw/2)*2:ceil(ih/2)*2[fg];"
                        f"[bg][fg]overlay=(W-w)/2:(H-h)/2"
                    )
                else:
                    filter_complex = (
                        f"[0:v]split=2[v_bg][v_fg];"
                        f"[v_bg]scale={target_w}:{target_h}:force_original_aspect_ratio=increase,crop={target_w}:{target_h},boxblur=25:5[bg];"
                        f"[v_fg]scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,pad=ceil(iw/2)*2:ceil(ih/2)*2[fg];"
                        f"[bg][fg]overlay=(W-w)/2:(H-h)/2"
                    )
                cmd = ["ffmpeg", "-y", "-i", video_path, "-filter_complex", filter_complex] + base_encode + audio_flags + ["-progress", "pipe:1", output_path]

        else:
            if delogo_str:
                cmd = ["ffmpeg", "-y", "-i", video_path, "-vf", delogo_str] + base_encode + audio_flags + ["-progress", "pipe:1", output_path]
            else:
                shutil.copyfile(video_path, output_path)
                if progress_callback:
                    progress_callback(100, "Tamamlandı!")
                return output_path

        logger.info(f"Video motoru başlatılıyor: {' '.join(cmd)}")
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        if process_tracker:
            process_tracker(proc)

        if progress_callback:
            progress_callback(10, "Video işleniyor (%10)...")

        for line in proc.stdout:
            if cancel_check and cancel_check():
                proc.terminate()
                if os.path.exists(output_path):
                    try: os.remove(output_path)
                    except: pass
                raise RuntimeError("İşlem kullanıcı tarafından iptal edildi.")

            line = line.strip()
            if line.startswith("out_time_us="):
                try:
                    val = line.split("=", 1)[1]
                    cur_time_sec = int(val) / 1_000_000.0
                    if duration > 0:
                        pct = min(98, max(10, int((cur_time_sec / duration) * 88) + 10))
                        if progress_callback:
                            progress_callback(pct, f"Video işleniyor (%{pct})...")
                except Exception:
                    pass

        proc.wait()
        if cancel_check and cancel_check():
            raise RuntimeError("İşlem kullanıcı tarafından iptal edildi.")

        if proc.returncode != 0:
            raise RuntimeError("FFmpeg video işleme sırasında hata oluştu.")

        if progress_callback:
            progress_callback(100, "Tamamlandı!")

        return output_path

    @staticmethod
    def extract_first_frame(video_path: str, output_image_path: str) -> str:
        """Videodan alan seçimi için ilk saniyedeki kareyi çıkarır."""
        for ss in ("00:00:01", "00:00:00"):
            cmd = [
                "ffmpeg", "-y",
                "-ss", ss,
                "-i", video_path,
                "-vframes", "1",
                "-q:v", "2",
                output_image_path
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if res.returncode == 0 and os.path.exists(output_image_path) and os.path.getsize(output_image_path) > 0:
                return output_image_path

        raise RuntimeError("Videodan önizleme karesi çıkarılamadı.")
