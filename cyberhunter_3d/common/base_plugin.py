import abc
from typing import List, Dict

class Plugin(abc.ABC):
    """
    Abstract base class for all plugins.
    """

    @abc.abstractmethod
    def name(self) -> str:
        """
        Returns the name of the plugin.
        """
        pass

    @abc.abstractmethod
    def run(self, targets: List[str]) -> List[Dict]:
        """
        Runs the plugin on a list of targets.
        """
        pass

    @abc.abstractmethod
    def parse(self, raw_output: str, target: str) -> List[Dict]:
        """
        Parses the raw output of the tool into a standardized format.
        """
        pass
