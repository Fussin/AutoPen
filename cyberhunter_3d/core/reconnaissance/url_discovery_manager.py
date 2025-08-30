import logging
from ..plugins.manager import PluginManager
from ..plugins.context import ScanContext
from cyberhunter_3d.utils.file_utils import get_results_dir
from ...web.models import Scan, db

log = logging.getLogger(__name__)

def discover_urls(domain: str, scan_id: int, app):
    """
    Orchestrates the URL discovery process using the plugin architecture.
    """
    log.info(f"Starting URL Discovery for: {domain}")

    with app.app_context():
        scan = Scan.query.get(scan_id)
        if not scan:
            log.error(f"Scan with ID {scan_id} not found.")
            return

        results_dir = get_results_dir(domain, scan_id)
        context = ScanContext(target_domain=domain, scan_id=scan_id, results_dir=results_dir)

        plugin_manager = PluginManager()
        plugin_manager.run_all_plugins(
            context,
            include_plugins=["URL Discovery", "URL Processor"]
        )

        log.info(f"URL Discovery for {domain} completed.")
