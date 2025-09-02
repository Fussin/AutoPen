import logging
from typing import List, Dict, Any
from cyberhunter_3d.web.models import Asset

log = logging.getLogger(__name__)

class ContinuousMonitor:
    """
    Monitors for changes in assets between scans.
    """

    def __init__(self, baseline_scan_id: int, current_scan_id: int):
        """
        Initializes the monitor with a baseline and current scan.
        """
        self.baseline_scan_id = baseline_scan_id
        self.current_scan_id = current_scan_id
        log.info(f"Initializing monitor for baseline {baseline_scan_id} and current {current_scan_id}")

    def _get_assets_by_value(self, scan_id: int) -> Dict[str, Asset]:
        """Helper to retrieve assets from a scan and map them by their value."""
        assets = Asset.query.filter_by(scan_id=scan_id).all()
        # Create a unique key for each asset based on its type and value
        return {f"{asset.type}:{asset.value}": asset for asset in assets}

    def compare_assets(self) -> List[Dict[str, Any]]:
        """
        Compares the assets of the two scans and returns a list of change dictionaries.
        """
        log.info("Comparing assets...")
        baseline_assets = self._get_assets_by_value(self.baseline_scan_id)
        current_assets = self._get_assets_by_value(self.current_scan_id)

        changes = []

        # Find new and changed assets
        for key, current_asset in current_assets.items():
            baseline_asset = baseline_assets.get(key)
            if not baseline_asset:
                changes.append({
                    "title": f"New Asset: {current_asset.type} '{current_asset.value}'",
                    "description": f"A new asset was discovered.",
                    "severity": "Medium",
                    "details": {"change": "added", "type": current_asset.type, "value": current_asset.value, "details": current_asset.details}
                })
            else:
                # Compare details for changes (e.g., open ports)
                if current_asset.details != baseline_asset.details:
                    changes.append({
                        "title": f"Asset Changed: {current_asset.type} '{current_asset.value}'",
                        "description": f"The details of asset '{current_asset.value}' have changed.",
                        "severity": "Low",
                        "details": {
                            "change": "modified",
                            "type": current_asset.type,
                            "value": current_asset.value,
                            "from": baseline_asset.details,
                            "to": current_asset.details
                        }
                    })
                # Remove the asset from baseline_assets so we can find removed assets later
                del baseline_assets[key]

        # Find removed assets
        for key, baseline_asset in baseline_assets.items():
            changes.append({
                "title": f"Asset Removed: {baseline_asset.type} '{baseline_asset.value}'",
                "description": f"An asset is no longer present.",
                "severity": "Low",
                "details": {"change": "removed", "type": baseline_asset.type, "value": baseline_asset.value}
            })

        log.info(f"Asset comparison complete. Found {len(changes)} changes.")
        return changes

    def run(self):
        """
        Runs the continuous monitoring process.
        """
        log.info("Running continuous monitor...")
        # Note: This requires being run within a Flask app context to access the DB.
        # The scan_manager handles this.
        findings = self.compare_assets()
        log.info(f"Monitor run complete. Found {len(findings)} changes.")
        return findings
