import os
import cv2
import numpy as np
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class WatermarkDetector:
    @staticmethod
    def detect_video_watermarks(video_path: str) -> List[Dict[str, Any]]:
        """
        Videodaki statik filigran, logo ve sembolleri (Kling AI, TikTok, CapCut vb.)
        farklı zamanlardaki kareleri morfolojik Top-Hat ve zamansal kararlılıkla
        analiz ederek otomatik tespit eder.
        """
        if not os.path.exists(video_path):
            return []

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return []

        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration_ms = cap.get(cv2.CAP_PROP_FRAME_COUNT) / (cap.get(cv2.CAP_PROP_FPS) or 30.0) * 1000.0

        # Farklı zamanlardan 3 kare örnekle
        sample_times_ms = [1000, 3000, 6000]

        frames = []
        for t in sample_times_ms:
            if t < duration_ms:
                cap.set(cv2.CAP_PROP_POS_MSEC, t)
                ret, frame = cap.read()
                if ret and frame is not None:
                    frames.append(frame)

        cap.release()

        if not frames:
            return []

        return WatermarkDetector._detect_from_frames(frames, w, h)

    @staticmethod
    def detect_image_watermarks(image_path: str) -> List[Dict[str, Any]]:
        """Görseldeki yüksek kontrastlı köşe filigranlarını tespit eder."""
        if not os.path.exists(image_path):
            return []
        img = cv2.imread(image_path)
        if img is None:
            return []
        h, w = img.shape[:2]
        return WatermarkDetector._detect_from_frames([img], w, h)

    @classmethod
    def _detect_from_frames(cls, frames: List[np.ndarray], w: int, h: int) -> List[Dict[str, Any]]:
        detected_boxes = []

        # Taranacak 4 köşe bölgesi (filigranların yer aldığı kritik %26-%28'lik köşe dilimleri)
        rois = [
            {
                "name": "Sağ Alt Filigran (Kling / TikTok / AI)",
                "x1": int(w * 0.72), "y1": int(h * 0.70),
                "x2": w, "y2": h,
                "priority": 1
            },
            {
                "name": "Sol Üst Filigran (TikTok / Logo)",
                "x1": 0, "y1": 0,
                "x2": int(w * 0.28), "y2": int(h * 0.26),
                "priority": 2
            },
            {
                "name": "Sağ Üst Filigran",
                "x1": int(w * 0.72), "y1": 0,
                "x2": w, "y2": int(h * 0.26),
                "priority": 3
            },
            {
                "name": "Sol Alt Filigran",
                "x1": 0, "y1": int(h * 0.70),
                "x2": int(w * 0.28), "y2": h,
                "priority": 4
            }
        ]

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25))

        for roi in rois:
            rx1, ry1, rx2, ry2 = roi["x1"], roi["y1"], roi["x2"], roi["y2"]
            roi_w = rx2 - rx1
            roi_h = ry2 - ry1

            tophats = []
            for f in frames:
                sub = f[ry1:ry2, rx1:rx2]
                gray = cv2.cvtColor(sub, cv2.COLOR_BGR2GRAY)
                th = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, kernel)
                tophats.append(th)

            if not tophats:
                continue

            if len(tophats) >= 2:
                # Zamansal minimum: video içeriği değişirken sabit kalan logo parlar
                common = np.minimum.reduce(tophats)
            else:
                common = tophats[0]

            # Eşikleme (filigran konturu)
            _, binary = cv2.threshold(common, 55, 255, cv2.THRESH_BINARY)
            
            # Boşlukları doldurma
            dilate_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, dilate_kernel)

            contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            roi_candidates = []
            for c in contours:
                bx, by, bw, bh = cv2.boundingRect(c)

                # Boyut filtreleri: 20px ile 220px arası
                if 20 <= bw <= 240 and 20 <= bh <= 200:
                    area = bw * bh
                    # Güvenlik payı (8px margin)
                    pad = 8
                    final_x = max(0, rx1 + bx - pad)
                    final_y = max(0, ry1 + by - pad)
                    final_w = min(w - final_x, bw + pad * 2)
                    final_h = min(h - final_y, bh + pad * 2)

                    # Çift sayı koordinatlar
                    final_w = final_w + (final_w % 2)
                    final_h = final_h + (final_h % 2)

                    roi_candidates.append({
                        "x": int(final_x),
                        "y": int(final_y),
                        "w": int(final_w),
                        "h": int(final_h),
                        "area": area,
                        "label": roi["name"],
                        "priority": roi["priority"]
                    })

            if roi_candidates:
                # En belirgin olanı seç
                roi_candidates.sort(key=lambda item: item["area"], reverse=True)
                detected_boxes.append(roi_candidates[0])

        # Priority'e göre sırala
        detected_boxes.sort(key=lambda b: b.get("priority", 99))

        # Eğer Sağ Alt Köşede (Kling / TikTok / AI) bir filigran bulunduysa,
        # arka plandaki sahne öğelerini (tabela, ekran yazıları vb.) korumak için
        # öncelikle sadece bu asıl filigranı döndür
        br_boxes = [b for b in detected_boxes if b.get("priority") == 1]
        if br_boxes:
            detected_boxes = br_boxes

        # Remove helper keys
        for b in detected_boxes:
            b.pop("priority", None)
            b.pop("area", None)

        return detected_boxes
