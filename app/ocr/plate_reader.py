"""
ocr/plate_reader.py
Standalone number plate OCR utility.
Can be run independently for testing OCR on any image file.

Usage:
  python app/ocr/plate_reader.py --image path/to/image.jpg
  python app/ocr/plate_reader.py --demo
"""

import argparse
import random
import sys
from pathlib import Path

import cv2
import numpy as np

# ── Try EasyOCR ───────────────────────────────────────────────────────────────
try:
    import easyocr
    EASYOCR = True
except ImportError:
    EASYOCR = False

# ── Try Tesseract ─────────────────────────────────────────────────────────────
try:
    import pytesseract
    TESSERACT = True
except ImportError:
    TESSERACT = False

FAKE_PLATES = [
    "DL01AB1234", "MH12CD5678", "KA03EF9012",
    "TN09GH3456", "UP32IJ7890", "RJ14KL2345",
]


class PlateReader:
    """High-level plate reader that tries EasyOCR then Tesseract then fakes."""

    def __init__(self):
        self.reader = None
        if EASYOCR:
            try:
                self.reader = easyocr.Reader(["en"], gpu=False, verbose=False)
                print("✅  EasyOCR initialised")
            except Exception as e:
                print(f"⚠️  EasyOCR init failed: {e}")

    def read(self, image: np.ndarray) -> dict:
        """
        Attempt to read a number plate from the given BGR image.
        Returns { plate, confidence, method }.
        """
        # ── Pre-process ──────────────────────────────────────────────────────
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Upscale small images for better OCR
        h, w = gray.shape
        if w < 200:
            scale = 200 / w
            gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

        # Contrast enhancement
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)

        # Bilateral filter to remove noise while keeping edges
        gray = cv2.bilateralFilter(gray, 11, 17, 17)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # ── EasyOCR ──────────────────────────────────────────────────────────
        if self.reader:
            result = self._easyocr_read(thresh)
            if result:
                return result

        # ── Tesseract ────────────────────────────────────────────────────────
        if TESSERACT:
            result = self._tesseract_read(thresh)
            if result:
                return result

        # ── Fallback ─────────────────────────────────────────────────────────
        return {
            "plate": random.choice(FAKE_PLATES),
            "confidence": 0.0,
            "method": "simulated",
        }

    def _easyocr_read(self, gray_img: np.ndarray) -> dict | None:
        try:
            results = self.reader.readtext(
                gray_img,
                allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
                detail=1,
            )
            candidates = []
            for _, text, conf in results:
                clean = text.strip().replace(" ", "").upper()
                if 5 <= len(clean) <= 12 and conf > 0.35:
                    candidates.append((clean, conf))

            if candidates:
                best = max(candidates, key=lambda x: x[1])
                return {"plate": best[0], "confidence": round(best[1], 3), "method": "EasyOCR"}
        except Exception as e:
            print(f"EasyOCR read error: {e}")
        return None

    def _tesseract_read(self, gray_img: np.ndarray) -> dict | None:
        try:
            cfg = "--psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
            text = pytesseract.image_to_string(gray_img, config=cfg).strip()
            clean = text.replace(" ", "").replace("\n", "").upper()
            if 5 <= len(clean) <= 12:
                return {"plate": clean, "confidence": 0.7, "method": "Tesseract"}
        except Exception as e:
            print(f"Tesseract read error: {e}")
        return None

    def annotate(self, image: np.ndarray, result: dict) -> np.ndarray:
        """Draw bounding box and plate text on image."""
        out = image.copy()
        h, w = out.shape[:2]
        plate = result["plate"]
        method = result["method"]
        conf = result["confidence"]

        color = (0, 255, 0) if conf > 0.5 else (0, 165, 255) if conf > 0.3 else (0, 0, 255)
        cv2.rectangle(out, (10, h - 55), (w - 10, h - 5), (0, 0, 0), -1)
        cv2.putText(out, f"PLATE: {plate}", (20, h - 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        cv2.putText(out, f"Method: {method}  Conf: {conf:.0%}", (20, h - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)
        return out


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Smart Traffic AI – Plate OCR")
    parser.add_argument("--image", type=str, help="Path to image file")
    parser.add_argument("--demo", action="store_true", help="Run on a synthetic demo image")
    args = parser.parse_args()

    reader = PlateReader()

    if args.demo or not args.image:
        # Synthetic plate image
        img = np.zeros((100, 300, 3), dtype=np.uint8)
        img[:] = (30, 30, 30)
        cv2.rectangle(img, (5, 5), (295, 95), (255, 255, 200), -1)
        plate_text = random.choice(FAKE_PLATES)
        cv2.putText(img, plate_text, (20, 65),
                    cv2.FONT_HERSHEY_DUPLEX, 1.4, (0, 0, 0), 3)
        print(f"🎬  Demo plate: {plate_text}")
    elif args.image:
        img = cv2.imread(args.image)
        if img is None:
            print(f"❌  Cannot read image: {args.image}")
            sys.exit(1)
    else:
        print("Use --image <path> or --demo")
        sys.exit(0)

    result = reader.read(img)
    annotated = reader.annotate(img, result)

    print(f"\n{'='*40}")
    print(f"  Plate     : {result['plate']}")
    print(f"  Confidence: {result['confidence']:.1%}")
    print(f"  Method    : {result['method']}")
    print(f"{'='*40}\n")

    cv2.imshow("Plate Recognition Result", annotated)
    print("Press any key to close…")
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
