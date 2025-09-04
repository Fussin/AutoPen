import logging

log = logging.getLogger(__name__)

class AIScanConfigSelector:
    """
    A class to dynamically select scan plugins based on target characteristics.
    This simulates an AI making decisions about the scan strategy.
    """

    def __init__(self):
        # In a real scenario, this might load a trained model or complex rule sets.
        self.full_scan_plugins = [
            "Passive Enumeration",
            "Active Enumeration",
            "Permutation Enumeration",
            "URL Discovery",
            "URL Aggregation",
            "URL Processor",
            "Visual Recon",
            "JavaScript Analyzer",
            "Technology Fingerprinting",
            "Subdomain Takeover",
            "Cloud Enumeration",
            "CVE Mapper",
            "Vulnerability Scanner", # This is a heavy plugin, only for full scans
        ]
        self.passive_scan_plugins = [
            "Passive Enumeration",
            "URL Discovery",
            "URL Aggregation",
            "Technology Fingerprinting",
        ]

    def select_plugins(self, target_info: dict) -> list[str]:
        """
        Selects a list of plugins to run based on the provided target information.

        Args:
            target_info: A dictionary containing details about the target.
                         Expected keys: 'scan_type' ('full' or 'passive').

        Returns:
            A list of plugin names recommended for the scan.
        """
        scan_type = target_info.get('scan_type', 'passive')
        log.info(f"AI Selector: Received request for a '{scan_type}' scan.")

        if scan_type == 'full':
            log.info(f"AI Selector: Recommending a full scan with {len(self.full_scan_plugins)} plugins.")
            return self.full_scan_plugins

        # Default to a passive scan for safety and speed
        log.info(f"AI Selector: Recommending a passive scan with {len(self.passive_scan_plugins)} plugins.")
        return self.passive_scan_plugins
