from abc import ABC, abstractmethod
from typing import List
from .context import ScanContext

class Plugin(ABC):
    """
    Abstract base class for all plugins in the new architecture.
    """
    @property
    @abstractmethod
    def name(self) -> str:
        """The unique name of the plugin."""
        raise NotImplementedError

    @property
    @abstractmethod
    def description(self) -> str:
        """A brief description of what the plugin does."""
        raise NotImplementedError

    @property
    def requires(self) -> List[str]:
        """
        A list of data keys that this plugin requires to be present in the
        ScanContext before it can run.
        """
        return []

    @property
    def provides(self) -> List[str]:
        """
        A list of data keys that this plugin promises to provide in the
        ScanContext after it has run.
        """
        return []

    @property
    def fallback(self) -> str:
        """The name of the plugin to fall back to if this one fails."""
        return None

    @abstractmethod
    def run(self, context: ScanContext):
        """
        The main execution method for the plugin. It should use the context
        to get its required data and to store its output data.

        :param context: The shared ScanContext object.
        """
        raise NotImplementedError
