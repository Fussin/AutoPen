from typing import Dict, Any, Set

class ScanContext:
    """
    A central data store for a single scan, holding all the data
    generated and used by the reconnaissance pipeline.
    """
    def __init__(self, target: str):
        self.target = target
        self.data: Dict[str, Any] = {
            "subdomains": set(),
            "live_hosts": set(),
            "ip_map": {},
            "tech": [],
            "takeover_vulns": [],
            "cloud_assets": [],
            "cve_results": {},
        }

    def get(self, key: str, default: Any = None) -> Any:
        """Gets a value from the context."""
        return self.data.get(key, default)

    def set(self, key: str, value: Any):
        """Sets a value in the context."""
        self.data[key] = value

    def update_set(self, key: str, value: Set):
        """Updates a set in the context with new values."""
        if key not in self.data or not isinstance(self.data[key], set):
            self.data[key] = set()
        self.data[key].update(value)
