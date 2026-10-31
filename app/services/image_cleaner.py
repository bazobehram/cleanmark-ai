import os
import logging
from typing import List, Dict, Any
import cv2
import numpy as np
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

class ImageCleaner:
    @staticmethod
    def clean(image_path: str, boxes: List[Dict[str, int]], output_path: str, method: str = "telea") -> str:
        """
        Görsel üzerindeki belirtilen kutu alanlarındaki filigran/imza/logoları
        OpenCV inpainting algoritmalarıyla çevre dokudan yeniden yapılandırarak siler.
        EXIF yönelimini korur ve RGBA/RGB formatlarını destekler.
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Görsel bulunamadı: {image_path}")

        try:
            with Image.open(image_path) as pil_img:
                pil_img = ImageOps.exif_transpose(pil_img)
                has_alpha = pil_img.mode in ("RGBA", "LA") or (pil_img.mode == "P" and "transparency" in pil_img.info)
                if has_alpha:
                    pil_img = pil_img.convert("RGBA")
                    alpha = np.array(pil_img.split()[-1])
                    rgb_img = pil_img.convert("RGB")
                else:
                    pil_img = pil_img.convert("RGB")
                    alpha = None
                    rgb_img = pil_img

                np_rgb = np.array(rgb_img)
                # PIL RGB -> OpenCV BGR
                cv_img = cv2.cvtColor(np_rgb, cv2.COLOR_RGB2BGR)
        except Exception as e:
            logger.error(f"Görsel okuma hatası: {e}")
            raise ValueError(f"Görsel yüklenemedi veya desteklenmeyen format: {e}")

        height, width = cv_img.shape[:2]
        mask = np.zeros((height, width), dtype=np.uint8)

        # Kutuları maskeye çiz ve sınır kontrolü yap
        for b in boxes:
            x = max(0, int(b.get("x", 0)))
            y = max(0, int(b.get("y", 0)))
            w = int(b.get("w", 0))
            h = int(b.get("h", 0))

            x2 = min(width, x + w)
            y2 = min(height, y + h)

            if x2 > x and y2 > y:
                mask[y:y2, x:x2] = 255

        # Kenarları hafif genişleterek kenar izi kalmasını engelle (5x5 eliptik kernel)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.dilate(mask, kernel, iterations=1)

        # Inpaint algoritması
        flag = cv2.INPAINT_TELEA if method == "telea" else cv2.INPAINT_NS
        cleaned_bgr = cv2.inpaint(cv_img, mask, inpaintRadius=3, flags=flag)

        # OpenCV BGR -> RGB
        cleaned_rgb = cv2.cvtColor(cleaned_bgr, cv2.COLOR_BGR2RGB)
        result_pil = Image.fromarray(cleaned_rgb)

        if has_alpha and alpha is not None:
            # Alpha kanalını koru
            r, g, b = result_pil.split()
            a = Image.fromarray(alpha)
            result_pil = Image.merge("RGBA", (r, g, b, a))

        ext = os.path.splitext(output_path)[1].lower()
        if ext in (".jpg", ".jpeg"):
            if result_pil.mode == "RGBA":
                result_pil = result_pil.convert("RGB")
            result_pil.save(output_path, "JPEG", quality=96, subsampling=0)
        elif ext == ".webp":
            result_pil.save(output_path, "WEBP", quality=95)
        elif ext == ".png":
            result_pil.save(output_path, "PNG", optimize=True)
        else:
            result_pil.save(output_path)

        return output_path
