import logging
from .plugins.manager import PluginManager
from .plugins.context import ScanContext

log = logging.getLogger(__name__)

class SpecializedScanManager:
    """
    Orchestrates the running of specialized, post-reconnaissance scanning plugins.
    This includes artifact extraction and expanded reconnaissance.
    """
    def __init__(self, context: ScanContext):
        self.context = context
        self.plugin_manager = PluginManager()

    def run(self):
        """
        Runs the full pipeline of specialized scanning plugins.
        """
        log.info("Starting specialized scan manager...")

        # Define the sequence of plugins to run for this phase.
        # The PluginManager will resolve the dependencies.
        # We add our new plugins to this flow.
        plugin_sequence = [
            "URL Processor", # This should provide live_urls_2xx
            "Artifact Extractor",
            "Expanded Reconnaissance",
            # Other specialized scanners would go here
        ]

        self.plugin_manager.run_all_plugins(
            self.context,
            include_plugins=plugin_sequence
        )

        log.info("Specialized scan manager finished.")
        return self.context
