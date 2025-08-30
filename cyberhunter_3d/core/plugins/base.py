from abc import ABC, abstractmethod
from typing import List
from ..context import ScanContext

class Plugin(ABC):
    """
    Abstract base class for all plugins.
    """
    @property
    @abstractmethod
    def name(self) -> str:
        """The name of the plugin."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """A brief description of what the plugin does."""
        pass

    @property
    def requires(self) -> List[str]:
        """A list of data keys that this plugin requires from the ScanContext."""
        return []

    @property
    def provides(self) -> List[str]:
        """A list of data keys that this plugin provides to the ScanContext."""
        return []

    @abstractmethod
    def run(self, context: ScanContext):
        """
        The main execution method for the plugin.

        :param context: The shared ScanContext object containing all scan data.
        """
        pass
