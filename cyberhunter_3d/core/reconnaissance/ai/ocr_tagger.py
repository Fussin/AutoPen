from typing import Dict, List
import os
import re
try:
    from PIL import Image
except ImportError:
    import Image
import pytesseract
from cyberhunter_3d.utils.logger import setup_logger

def generate_ocr_tags(screenshots_dir: str, logger) -> Dict[str, List[str]]:
    """
    Performs OCR on screenshots and generates descriptive tags.
    This function recursively scans the given directory for images.
    """
    logger.info("AI OCR Tagger: Performing OCR on screenshots...")

    ocr_results = {}
    if not os.path.isdir(screenshots_dir):
        logger.warning(f"Screenshots directory '{screenshots_dir}' not found. Cannot perform OCR.")
        return ocr_results

    for root, _, files in os.walk(screenshots_dir):
        for filename in files:
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                hostname = os.path.splitext(filename)[0]
                image_path = os.path.join(root, filename)

                try:
                    # Perform OCR
                    text = pytesseract.image_to_string(Image.open(image_path), timeout=30)

                    # Generate tags from OCR text (simple keyword matching)
                    tags = set()
                    text_lower = text.lower()

                    if "login" in text_lower or "sign in" in text_lower:
                        tags.add("login-page")
                    if "404" in text_lower or "not found" in text_lower:
                        tags.add("404-not-found")
                    if "error" in text_lower or "exception" in text_lower:
                        tags.add("error-page")
                    if "dashboard" in text_lower or "admin" in text_lower:
                        tags.add("dashboard")
                    if "api" in text_lower or "documentation" in text_lower:
                        tags.add("api-docs")

                    # Add some generic tags
                    tags.add("webpage")
                    tags.add("screenshot")

                    ocr_results[hostname] = sorted(list(tags))

                except pytesseract.TesseractNotFoundError:
                    logger.error("Tesseract is not installed or not in your PATH. Cannot perform OCR.")
                    return {} # Stop processing if Tesseract is not found
                except Exception as e:
                    logger.error(f"Error performing OCR on {image_path}: {e}")

    logger.info(f"Generated OCR tags for {len(ocr_results)} screenshots.")
    return ocr_results
