from abc import ABC, abstractmethod
from typing import Dict, Any

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

    @abstractmethod
    def run(self, target: str, **kwargs) -> Dict[str, Any]:
        """
        The main execution method for the plugin.

        :param target: The main target for the plugin to run against (e.g., a domain).
        :param kwargs: A dictionary of additional data that the plugin might need
                       (e.g., a list of known subdomains, live hosts).
        :return: A dictionary of results from the plugin.
        """
        pass
