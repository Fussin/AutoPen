import pytest
import logging
from pathlib import Path
from unittest.mock import MagicMock
from cyberhunter_3d.core import post_scan_operations as pso
from cyberhunter_3d.core.post_scan_operations import (
    backup_creation,
    data_archival,
    cleanup_operations,
)

@pytest.fixture
def mock_om(tmp_path):
    """Creates a mock OutputManager object with a temporary base directory."""
    om = MagicMock()
    om.base_dir = tmp_path / "scan_results"
    om.base_dir.mkdir()
    # Create a dummy file in the scan results directory
    (om.base_dir / "result.txt").write_text("dummy content")
    om.vulnerabilities = []
    return om

def test_backup_creation(mock_om):
    """Tests that a zip archive is created."""
    scan_id = "test_scan_123"
    backup_creation(scan_id, mock_om)

    archive_path = mock_om.base_dir.parent / f"{mock_om.base_dir.name}.zip"
    assert archive_path.exists()
    assert archive_path.is_file()

def test_data_archival(mock_om):
    """Tests that the backup archive is moved to the archive directory."""
    scan_id = "test_scan_123"

    # First, create the backup
    backup_creation(scan_id, mock_om)

    # Then, run the archival
    data_archival(scan_id, mock_om)

    archive_path = Path("archive") / f"{mock_om.base_dir.name}.zip"
    assert archive_path.exists()
    assert archive_path.is_file()

    # Check that the original archive is gone
    original_archive_path = mock_om.base_dir.parent / f"{mock_om.base_dir.name}.zip"
    assert not original_archive_path.exists()

def test_cleanup_operations(mock_om):
    """Tests that the scan results directory is deleted."""
    scan_id = "test_scan_123"

    assert mock_om.base_dir.exists()
    cleanup_operations(scan_id, mock_om)
    assert not mock_om.base_dir.exists()

def test_final_validation_success(mock_om, caplog):
    """Tests final_validation when the archive exists."""
    caplog.set_level(logging.INFO)
    scan_id = "test_scan_123"
    # Create a dummy archive file
    archive_dir = Path("archive")
    archive_dir.mkdir(exist_ok=True)
    archive_file = archive_dir / f"{mock_om.base_dir.name}.zip"
    archive_file.touch()

    pso.final_validation(scan_id, mock_om)
    assert "Validation successful" in caplog.text

    archive_file.unlink()

def test_final_validation_failure(mock_om, caplog):
    """Tests final_validation when the archive does not exist."""
    caplog.set_level(logging.INFO)
    scan_id = "test_scan_123"

    archive_path = Path("archive") / f"{mock_om.base_dir.name}.zip"
    if archive_path.exists():
        archive_path.unlink()

    pso.final_validation(scan_id, mock_om)
    assert "Validation failed" in caplog.text

def test_report_generation(mock_om, caplog):
    """Tests the report_generation function."""
    caplog.set_level(logging.INFO)
    scan_id = "test_scan_123"
    mock_om.finalize.return_value = {"pdf": "path/to/report.pdf"}
    pso.report_generation(scan_id, mock_om)
    mock_om.finalize.assert_called_once_with(generate_pdf=True, generate_docx=True)
    assert "Generating reports" in caplog.text

def test_notification_dispatch(caplog):
    """Tests the notification_dispatch function."""
    caplog.set_level(logging.INFO)
    scan_id = "test_scan_123"
    pso.notification_dispatch(scan_id)
    assert "Dispatching notifications" in caplog.text

def test_integration_updates(caplog, monkeypatch):
    """Tests the integration_updates function."""
    caplog.set_level(logging.INFO)
    scan_id = "test_scan_123"

    # Mock requests.post to avoid actual network calls
    mock_post = MagicMock()
    monkeypatch.setattr(pso.requests, "post", mock_post)

    pso.integration_updates(scan_id)
    assert "Sending integration updates" in caplog.text
    assert mock_post.call_count == 2

def test_analytics_update(mock_om, caplog):
    """Tests the analytics_update function."""
    caplog.set_level(logging.INFO)
    scan_id = "test_scan_123"
    pso.analytics_update(scan_id, mock_om)
    assert "Updating analytics" in caplog.text

def test_session_termination(caplog):
    """Tests the session_termination function."""
    caplog.set_level(logging.INFO)
    scan_id = "test_scan_123"
    pso.session_termination(scan_id)
    assert "Terminating session" in caplog.text

def test_monitoring_activation(caplog):
    """Tests the monitoring_activation function."""
    caplog.set_level(logging.INFO)
    scan_id = "test_scan_123"
    pso.monitoring_activation(scan_id)
    assert "Activating monitoring" in caplog.text

def test_platform_logout(caplog):
    """Tests the platform_logout function."""
    caplog.set_level(logging.INFO)
    scan_id = "test_scan_123"
    pso.platform_logout(scan_id)
    assert "Logging out of platform" in caplog.text

def test_session_closed(caplog):
    """Tests the session_closed function."""
    caplog.set_level(logging.INFO)
    scan_id = "test_scan_123"
    pso.session_closed(scan_id)
    assert "Closing session" in caplog.text
