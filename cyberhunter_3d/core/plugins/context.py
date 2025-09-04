from typing import Any, Dict

import datetime

class ScanContext:
    """
    A class to hold the context of a scan, including target information
    and data produced by various plugins. It acts as a central data bus.
    """
    def __init__(self, target_domain: str, scan_id: int = None, results_dir: str = None):
        self.target_domain = target_domain
        self.scan_id = scan_id
        self.results_dir = results_dir
        self._data: Dict[str, Any] = {}
        self.scan_events = []

    def add_event(self, event_type: str, message: str, plugin_name: str = None):
        """Adds a timestamped event to the scan's history."""
        event = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "type": event_type,
            "plugin": plugin_name,
            "message": message,
        }
        self.scan_events.append(event)

    def set(self, key: str, value: Any):
        """
        Stores a piece of data in the context.
        """
        self._data[key] = value

    def get(self, key:str, default: Any = None) -> Any:
        """
        Retrieves a piece of data from the context.
        """
        return self._data.get(key, default)

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __setitem__(self, key: str, value: Any):
        self._data[key] = value

    def __contains__(self, key: str) -> bool:
        return key in self._data
