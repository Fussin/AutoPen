import pytest
from unittest.mock import patch
from cyberhunter_3d.core.plugins.manager import PluginManager
from cyberhunter_3d.core.plugins.base import Plugin
from cyberhunter_3d.core.context import ScanContext

# Define dummy plugins for testing
class DummyPluginA(Plugin):
    @property
    def name(self): return "A"
    @property
    def description(self): return "Provides A"
    @property
    def provides(self): return ["A_data"]
    def run(self, context: ScanContext): context.set("A_data", "A_result")

class DummyPluginB(Plugin):
    @property
    def name(self): return "B"
    @property
    def description(self): return "Requires A, provides B"
    @property
    def requires(self): return ["A_data"]
    @property
    def provides(self): return ["B_data"]
    def run(self, context: ScanContext):
        a_data = context.get("A_data")
        context.set("B_data", f"{a_data}_B_result")

class DummyPluginC(Plugin):
    @property
    def name(self): return "C"
    @property
    def description(self): return "Requires B"
    @property
    def requires(self): return ["B_data"]
    def run(self, context: ScanContext):
        b_data = context.get("B_data")
        context.set("C_data", f"{b_data}_C_result")

def test_dependency_resolution():
    """
    Tests that the PluginManager correctly sorts plugins based on dependencies.
    """
    # Unordered plugins
    plugins = [DummyPluginC(), DummyPluginA(), DummyPluginB()]

    manager = PluginManager(plugin_dir="dummy")
    # Manually set the plugins to test the sorting logic
    manager.plugins = manager._resolve_dependencies(plugins)

    # Check the order
    assert manager.plugins[0].name == "A"
    assert manager.plugins[1].name == "B"
    assert manager.plugins[2].name == "C"

def test_plugin_manager_run_plugins():
    """
    Tests that the PluginManager runs plugins in the correct order and updates the context.
    """
    plugins = [DummyPluginC(), DummyPluginA(), DummyPluginB()]

    with patch.object(PluginManager, '_load_plugins', return_value=plugins):
        manager = PluginManager(plugin_dir="dummy")
        # Manually sort them for the test
        manager.plugins = manager._resolve_dependencies(plugins)

        context = ScanContext(target="example.com")
        manager.run_all_plugins(context)

        # Assert that the context was updated correctly
        assert context.get("A_data") == "A_result"
        assert context.get("B_data") == "A_result_B_result"
        assert context.get("C_data") == "A_result_B_result_C_result"
