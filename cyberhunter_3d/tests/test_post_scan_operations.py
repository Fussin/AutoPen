import pytest
import logging
from pathlib import Path
from unittest.mock import MagicMock
from cyberhunter_3d.core import post_scan_operations as pso
from cyberhunter_3d.core.output_manager import OutputManager

@pytest.fixture
def mock_om(tmp_path):
    """Creates a mock OutputManager object with a temporary base directory."""
    om = MagicMock()
    om.base_dir = tmp_path / "scan_results"
    om.base_dir.mkdir()
    # Create a dummy file in the scan results directory
    (om.base_dir / "result.txt").write_text("dummy content")
    om.vulnerabilities = []
    om.assets = []
    return om

@pytest.fixture
def real_om(tmp_path):
    """Creates a real OutputManager instance with a temporary base directory."""
    return OutputManager(tmp_path / "scan_results")

@pytest.fixture
def mock_scan_obj():
    """A pytest fixture to create a mock scan object."""
    mock_scan = MagicMock()
    mock_scan.id = "test_scan_123"
    mock_scan.in_scope_rules = "*.example.com"
    mock_scan.out_of_scope_rules = "private.example.com"
    return mock_scan

def test_backup_creation(mock_scan_obj, mock_om):
    """Tests that a zip archive is created."""
    pso.backup_creation(mock_scan_obj, mock_om)

    archive_path = mock_om.base_dir.parent / f"{mock_om.base_dir.name}.zip"
    assert archive_path.exists()
    assert archive_path.is_file()

def test_data_archival(mock_scan_obj, mock_om):
    """Tests that the backup archive is moved to the archive directory."""
    # First, create the backup
    pso.backup_creation(mock_scan_obj, mock_om)

    # Then, run the archival
    pso.data_archival(mock_scan_obj, mock_om)

    archive_path = Path("archive") / f"{mock_om.base_dir.name}.zip"
    assert archive_path.exists()
    assert archive_path.is_file()

    # Check that the original archive is gone
    original_archive_path = mock_om.base_dir.parent / f"{mock_om.base_dir.name}.zip"
    assert not original_archive_path.exists()

def test_cleanup_operations(mock_scan_obj, mock_om):
    """Tests that the scan results directory is deleted."""
    assert mock_om.base_dir.exists()
    pso.cleanup_operations(mock_scan_obj, mock_om)
    assert not mock_om.base_dir.exists()

def test_final_validation_success(mock_scan_obj, mock_om, caplog):
    """Tests final_validation when the archive exists."""
    caplog.set_level(logging.INFO)
    # Create a dummy archive file
    archive_dir = Path("archive")
    archive_dir.mkdir(exist_ok=True)
    archive_file = archive_dir / f"{mock_om.base_dir.name}.zip"
    archive_file.touch()

    pso.final_validation(mock_scan_obj, mock_om)
    assert "Validation successful" in caplog.text

    archive_file.unlink()

def test_final_validation_failure(mock_scan_obj, mock_om, caplog):
    """Tests final_validation when the archive does not exist."""
    caplog.set_level(logging.INFO)

    archive_path = Path("archive") / f"{mock_om.base_dir.name}.zip"
    if archive_path.exists():
        archive_path.unlink()

    pso.final_validation(mock_scan_obj, mock_om)
    assert "Validation failed" in caplog.text

def test_report_generation(real_om, mock_scan_obj, caplog):
    """Tests the report_generation function."""
    caplog.set_level(logging.INFO)

    # Add some dummy data to the output manager
    real_om.add_vulnerability({"id": "VULN-001", "title": "Test Vuln", "severity": "High", "description": "A test vulnerability."})
    real_om.add_asset({'type': 'subdomain', 'value': 'test.example.com', 'details': {}})

    pso.report_generation(mock_scan_obj, real_om)

    assert "Generating PDF report" in caplog.text
    assert "Generating DOCX report" in caplog.text

    pdf_path = real_om.reports_dir / "scan_report.pdf"
    docx_path = real_om.reports_dir / "scan_report.docx"

    assert pdf_path.exists()
    assert docx_path.exists()

def test_notification_dispatch(mock_scan_obj, caplog):
    """Tests the notification_dispatch function."""
    caplog.set_level(logging.INFO)
    pso.notification_dispatch(mock_scan_obj)
    assert "Dispatching notifications" in caplog.text

def test_integration_updates(mock_scan_obj, caplog, monkeypatch):
    """Tests the integration_updates function."""
    caplog.set_level(logging.INFO)

    # Mock requests.post to avoid actual network calls
    mock_post = MagicMock()
    monkeypatch.setattr(pso.requests, "post", mock_post)

    pso.integration_updates(mock_scan_obj)
    assert "Sending integration updates" in caplog.text
    assert mock_post.call_count == 2

def test_analytics_update(mock_scan_obj, mock_om, caplog):
    """Tests the analytics_update function."""
    caplog.set_level(logging.INFO)
    pso.analytics_update(mock_scan_obj, mock_om)
    assert "Updating analytics" in caplog.text

def test_session_termination(mock_scan_obj, caplog):
    """Tests the session_termination function."""
    caplog.set_level(logging.INFO)
    pso.session_termination(mock_scan_obj)
    assert "Terminating session" in caplog.text

def test_monitoring_activation(mock_scan_obj, caplog):
    """Tests the monitoring_activation function."""
    caplog.set_level(logging.INFO)
    pso.monitoring_activation(mock_scan_obj)
    assert "Activating monitoring" in caplog.text

def test_platform_logout(mock_scan_obj, caplog):
    """Tests the platform_logout function."""
    caplog.set_level(logging.INFO)
    pso.platform_logout(mock_scan_obj)
    assert "Logging out of platform" in caplog.text

def test_session_closed(mock_scan_obj, caplog):
    """Tests the session_closed function."""
    caplog.set_level(logging.INFO)
    pso.session_closed(mock_scan_obj)
    assert "Closing session" in caplog.text
