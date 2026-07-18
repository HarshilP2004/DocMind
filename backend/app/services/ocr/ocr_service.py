import os
import hashlib
from pathlib import Path
from PIL import Image
import numpy as np
import cv2
from app.core.config import settings
from app.services.ocr.preprocessor import preprocessor
import google.generativeai as genai

class OCRService:
    def __init__(self):
        self.cache_dir = settings.UPLOAD_DIR / ".ocr_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._paddle_ocr = None

    def _get_paddle_ocr(self):
        """
        Lazy-loads PaddleOCR to avoid slowing down API startup.
        """
        if self._paddle_ocr is None:
            try:
                from paddleocr import PaddleOCR
                # Initialize PaddleOCR with English and disable logging spam
                self._paddle_ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
            except Exception as e:
                print(f"Warning: PaddleOCR could not be initialized: {e}. Fallback to Gemini Multimodal OCR will be used.")
                self._paddle_ocr = False
        return self._paddle_ocr

    def _get_image_hash(self, image_path: Path) -> str:
        """
        Generates MD5 hash of an image file to use as a cache key.
        """
        hasher = hashlib.md5()
        with open(image_path, 'rb') as f:
            buf = f.read()
            hasher.update(buf)
        return hasher.hexdigest()

    def _get_cached_text(self, cache_key: str) -> str:
        cache_path = self.cache_dir / f"{cache_key}.txt"
        if cache_path.exists():
            with open(cache_path, 'r', encoding='utf-8') as f:
                return f.read()
        return ""

    def _set_cached_text(self, cache_key: str, text: str):
        cache_path = self.cache_dir / f"{cache_key}.txt"
        with open(cache_path, 'w', encoding='utf-8') as f:
            f.write(text)

    def extract_text_from_image(self, image_path: Path) -> str:
        """
        Extracts text from an image with preprocessing, caching, and PaddleOCR/Gemini fallback.
        """
        # 1. Check cache
        cache_key = self._get_image_hash(image_path)
        cached_text = self._get_cached_text(cache_key)
        if cached_text:
            return cached_text

        # 2. Preprocess image using OpenCV (deskew & noise removal)
        try:
            processed_img_np = preprocessor.preprocess_for_ocr(str(image_path))
            # Save temporary preprocessed image for PaddleOCR
            temp_processed_path = settings.UPLOAD_DIR / f"temp_{cache_key}.png"
            cv2.imwrite(str(temp_processed_path), processed_img_np)
        except Exception as e:
            print(f"Preprocessing error: {e}. Using original image.")
            temp_processed_path = image_path

        # 3. Perform OCR
        extracted_text = ""
        ocr_engine = self._get_paddle_ocr()
        
        # Try local PaddleOCR first if available
        if ocr_engine:
            try:
                # PaddleOCR result is a list of lists containing boxes, text, confidence
                result = ocr_engine.ocr(str(temp_processed_path), cls=True)
                if result and result[0]:
                    lines = []
                    for line in result[0]:
                        text_info = line[1]
                        text = text_info[0]
                        lines.append(text)
                    extracted_text = "\n".join(lines)
            except Exception as e:
                print(f"PaddleOCR failed: {e}. Falling back to Gemini.")

        # Fallback to Gemini Multimodal API if PaddleOCR failed or is not installed
        if not extracted_text:
            try:
                # Load the preprocessed image using PIL
                pil_img = Image.open(temp_processed_path)
                
                # Make sure Gemini API Key is configured
                if not settings.GEMINI_API_KEY:
                    raise ValueError("GEMINI_API_KEY is not set in environment variables")
                
                genai.configure(api_key=settings.GEMINI_API_KEY)
                model = genai.GenerativeModel(settings.GEMINI_MODEL)
                
                prompt = (
                    "Extract all visible text from this document image. "
                    "Maintain the logical reading order and spacing. "
                    "Provide ONLY the extracted text, with absolutely no conversational preamble or postamble."
                )
                
                response = model.generate_content([pil_img, prompt])
                extracted_text = response.text.strip()
            except Exception as e:
                print(f"Gemini OCR fallback failed: {e}")
                extracted_text = ""

        # Clean up temporary preprocessed image if created
        if temp_processed_path != image_path and temp_processed_path.exists():
            try:
                os.remove(temp_processed_path)
            except Exception:
                pass

        # 4. Cache and return
        if extracted_text:
            self._set_cached_text(cache_key, extracted_text)
            
        return extracted_text

ocr_service = OCRService()
