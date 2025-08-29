import pytest
import os
from unittest.mock import patch, MagicMock
from pathlib import Path
from cyberhunter_3d.core.reconnaissance.ai.ocr_tagger import generate_ocr_tags
from cyberhunter_3d.utils.logger import setup_logger

logger = setup_logger('TestOcrTagger', 'test_ocr_tagger.log')

@patch('cyberhunter_3d.core.reconnaissance.ai.ocr_tagger.pytesseract.image_to_string')
@patch('cyberhunter_3d.core.reconnaissance.ai.ocr_tagger.Image')
def test_generate_ocr_tags(mock_image, mock_image_to_string, tmp_path: Path):
    """
    Tests that generate_ocr_tags correctly processes image files, calls OCR,
    and generates tags from the OCR output.
    """
    # Create some dummy screenshot files
    (tmp_path / "login.png").touch()
    (tmp_path / "dashboard.jpg").touch()
    (tmp_path / "other").mkdir(parents=True, exist_ok=True)
    (tmp_path / "other" / "nested.png").touch()

    # Mock Image.open to return a specific value for each path
    def open_side_effect(path):
        mock_img = MagicMock()
        mock_img.name = path
        return mock_img

    mock_image.open.side_effect = open_side_effect

    # Define the mock OCR output based on the mock image object
    def ocr_side_effect(mock_img):
        path = mock_img.name
        if "login" in str(path):
            return "Welcome, please login with your username and password."
        if "dashboard" in str(path):
            return "Admin Dashboard"
        if "nested" in str(path):
            return "API Documentation"
        return ""

    mock_image_to_string.side_effect = ocr_side_effect

    # Call the function to be tested
    ocr_results = generate_ocr_tags(str(tmp_path), logger)

    # Assertions
    assert len(ocr_results) == 3

    assert "login.png" in ocr_results
    assert "login" in ocr_results["login.png"]
    assert "username" in ocr_results["login.png"]
    assert "password" in ocr_results["login.png"]

    assert "dashboard.jpg" in ocr_results
    assert "admin" in ocr_results["dashboard.jpg"]

    assert os.path.join("other", "nested.png") in ocr_results
    assert any(tag.startswith("title:") for tag in ocr_results[os.path.join("other", "nested.png")])
