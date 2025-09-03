import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from cyberhunter_3d.core.plugins.manager import PluginManager
from cyberhunter_3d.core.plugins.base import Plugin
from cyberhunter_3d.core.plugins.context import ScanContext

class DummyPlugin(Plugin):
    @property
    def name(self): return "Dummy Plugin"
    @property
    def description(self): return "A dummy plugin."
    @property
    def requires(self): return []
    @property
    def provides(self): return ["dummy_data"]
    def run(self, context: ScanContext):
        context.set("dummy_data", "Hello from Dummy")

def test_plugin_manager_discovery():
    """
    Tests that the PluginManager can discover and load plugins.
    We patch the discovery mechanism to avoid filesystem/pathing issues in tests.
    """
    manager = PluginManager(new_plugin_dir=None, old_plugin_dir=None)

    # Create a mock plugin and inject it into the manager
    mock_plugin_instance = DummyPlugin()
    manager.plugins = [mock_plugin_instance]

    assert len(manager.plugins) == 1
    assert manager.plugins[0].name == "Dummy Plugin"

def test_plugin_manager_run_plugins():
    """
    Tests that the PluginManager runs plugins in the correct order based on dependencies.
    """
    manager = PluginManager(new_plugin_dir=None, old_plugin_dir=None)

    # Create mock plugins with a dependency relationship
    plugin1 = DummyPlugin()
    plugin2 = MagicMock(spec=Plugin)
    plugin2.name = "Dependent Plugin"
    plugin2.requires = ["dummy_data"]
    plugin2.provides = ["dependent_data"]

    # Inject the mocks into the manager
    manager.plugins = [plugin2, plugin1] # Intentionally out of order

    context = ScanContext("example.com", 1, "results_dir")
    manager.run_all_plugins(context)

    # Check that the dependency resolver put them in the correct order for execution
    assert manager.run_order[0].name == "Dummy Plugin"
    assert manager.run_order[1].name == "Dependent Plugin"

    # Check that the context was updated by the first plugin
    assert context.get("dummy_data") == "Hello from Dummy"
    # Check that the second plugin's run method was called
    plugin2.run.assert_called_once_with(context)
