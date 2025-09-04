from __future__ import annotations
import os
from pathlib import Path
from typing import Dict, List
try:
    import pytesseract
    from PIL import Image
except ImportError as e:
    # Re-raise with a more informative message for debugging
    raise ImportError(f"pytesseract or Pillow not installed. Please install them to use OCR features. Original error: {e}")

def generate_ocr_tags(screenshots_root: str, logger=None) -> Dict[str, List[str]]:
    """
    Recursively scan screenshots_root for image files, run OCR (if available),
    and return a mapping: {relative_image_path: [tags...]}.
    If pytesseract is unavailable, returns empty tags but still returns paths.
    """
    root = Path(screenshots_root)
    if not root.exists():
        if logger:
            logger.warning(f"OCR: screenshots root not found: {screenshots_root}")
        return {}

    image_exts = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}
    results: Dict[str, List[str]] = {}

    for img_path in root.rglob("*"):
        if img_path.is_file() and img_path.suffix.lower() in image_exts:
            rel = str(img_path.relative_to(root))
            if logger:
                logger.debug(f"Processing image: {img_path}")
            tags: List[str] = []
            if pytesseract and Image:
                try:
                    text = pytesseract.image_to_string(Image.open(img_path))
                    text = (text or "").strip()
                    if logger:
                        logger.debug(f"OCR text for {img_path}: {text}")
                    # Simple heuristics: find suspicious keywords
                    kws = ["staging", "internal", "debug", "admin", "login", "password", "username", "token"]
                    for kw in kws:
                        if kw.lower() in text.lower():
                            tags.append(kw)
                    # If page title-like text exists, add short title tag
                    if len(text) > 0:
                        preview = " ".join(text.splitlines()[:2])[:200]
                        tags.append(f"title:{preview}")
                    if logger:
                        logger.debug(f"Tags for {img_path}: {tags}")
                except Exception as e:
                    if logger:
                        logger.exception(f"OCR failed for {img_path}")
            else:
                if logger:
                    logger.debug("pytesseract not installed; skipping OCR content.")
            results[rel] = tags

    return results
