import logging
from ..plugins.manager import PluginManager
from ..plugins.context import ScanContext
from cyberhunter_3d.utils.file_utils import get_results_dir
from ...web.models import Scan, db
import os

log = logging.getLogger(__name__)

MAX_RECURSION_DEPTH = 3

def run_plugin_by_name(plugin_name: str, context: ScanContext):
    """Helper function to run a single plugin by name."""
    plugin_manager = PluginManager()
    plugin_manager.run_all_plugins(context, include_plugins=[plugin_name])

def run_subdomain_enum(context: ScanContext):
    """Runs the subdomain enumeration plugins."""
    log.info("Running subdomain enumeration plugins...")
    subdomain_plugins = [
        "Passive Enumeration",
        "Active Enumeration",
        "Permutation Enumeration"
    ]
    for plugin_name in subdomain_plugins:
        run_plugin_by_name(plugin_name, context)

    subdomains = context.get("subdomains", set())
    log.info(f"Found {len(subdomains)} subdomains after enumeration.")
    log.info("Subdomain enumeration finished.")


def discover_urls(domain: str, scan_id: int, app, sast_dir=None):
    """
    Orchestrates the expanded URL discovery and vulnerability scanning pipeline.
    """
    log.info(f"Starting Expanded URL Discovery & Enrichment Pipeline for: {domain}")

    with app.app_context():
        scan = Scan.query.get(scan_id)
        if not scan:
            log.error(f"Scan with ID {scan_id} not found.")
            return

        results_dir = get_results_dir(domain, scan_id)
        context = ScanContext(target_domain=domain, scan_id=scan_id, results_dir=results_dir)
        if sast_dir:
            context.set("sast_dir", sast_dir)

        # Run subdomain enumeration first to get targets for URL discovery
        run_subdomain_enum(context)

        # Initial URL Discovery
        run_plugin_by_name("URL Discovery", context)

        for depth in range(MAX_RECURSION_DEPTH):
            log.info(f"Pipeline recursion depth: {depth + 1}")

            # 2. Aggregation, Normalization & Deduplication
            run_plugin_by_name("URL Aggregation", context)

            # 3. Liveness & Enrichment Probe
            run_plugin_by_name("URL Processor", context)

            # 4B. Visual Recon
            run_plugin_by_name("Visual Recon", context)

            # 5. JavaScript Recursive Analysis
            run_plugin_by_name("JavaScript Analyzer", context)

            new_urls = context.get("new_urls_from_js")
            if not new_urls:
                log.info("No new URLs found from JavaScript analysis. Ending recursion.")
                break

            log.info(f"Found {len(new_urls)} new URLs from JS. Feeding back into the pipeline.")

            # Append new URLs to the main list for the next iteration
            existing_urls = context.get("urls", [])

            # Avoid adding duplicates
            unique_new_urls = [url for url in new_urls if url not in existing_urls]
            if not unique_new_urls:
                log.info("All new URLs from JS were already discovered. Ending recursion.")
                break

            log.info(f"Adding {len(unique_new_urls)} unique new URLs to the main list.")
            context.set("urls", existing_urls + unique_new_urls)

            # Clear the new_urls_from_js for the next iteration
            context.set("new_urls_from_js", [])
        else:
            log.warning(f"Reached max recursion depth of {MAX_RECURSION_DEPTH}.")

        # Final step: Vulnerability Scanning on all discovered assets
        log.info("All discovery phases complete. Starting vulnerability scanning.")
        run_plugin_by_name("Vulnerability Scanner", context)

        log.info(f"URL Discovery and Enrichment Pipeline for {domain} completed.")
