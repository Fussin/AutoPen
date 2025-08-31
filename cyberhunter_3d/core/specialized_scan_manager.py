import logging
from .plugins.base import Plugin
from .plugins.context import ScanContext
from .plugins.manager import PluginManager

log = logging.getLogger(__name__)

class SpecializedScanManager(Plugin):
    """
    A plugin to manage and run the specialized scanning phase.
    """
    @property
    def name(self) -> str:
        return "Specialized Scan Manager"

    @property
    def description(self) -> str:
        return "Manages and runs the specialized scanning phase."

    @property
    def requires(self) -> list[str]:
        return ["live_hosts", "js_files_urls", "validated_subdomains", "wordpress_urls"]

    @property
    def provides(self) -> list[str]:
        return ["specialized_scan_results"]

    def run(self, context: ScanContext):
        log.info("Running Specialized Scan Manager...")

        # These are the plugins that will be run by this manager
        specialized_plugins = [
            "WordPress Scanner",
            "JavaScript Analyzer",
            "API Spec Finder",
            "API Security Scanner",
            "Cloud Enumeration",
        ]

        # The main plugin manager should be passed in or accessed globally,
        # but for now, creating a new one and telling it to run a subset is okay.
        plugin_manager = PluginManager()

        log.info(f"Running specialized plugins: {specialized_plugins}")

        # Run only the specified plugins
        plugin_manager.run_all_plugins(context, include_plugins=specialized_plugins)

        # Aggregate results from the specialized scanning phase
        results = {
            "wordpress_vulnerabilities": context.get("wordpress_vulnerabilities"),
            "js_secrets": context.get("js_secrets"),
            "js_vulnerable_libraries": context.get("js_vulnerable_libraries"),
            "api_endpoints": context.get("api_endpoints"),
            "spec_endpoints": context.get("spec_endpoints"),
            "new_urls_from_js": context.get("new_urls_from_js"),
            "api_vulnerabilities": context.get("api_vulnerabilities"),
            "cloud_assets": context.get("cloud_assets"),
        }

        context.set("specialized_scan_results", results)
        log.info("Specialized Scan Manager finished.")
