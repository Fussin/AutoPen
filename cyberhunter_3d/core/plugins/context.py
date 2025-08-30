from typing import Any, Dict

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
