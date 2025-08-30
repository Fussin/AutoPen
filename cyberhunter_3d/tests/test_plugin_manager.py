import unittest
from unittest.mock import MagicMock, patch
from cyberhunter_3d.core.plugins.manager import PluginManager
from cyberhunter_3d.core.plugins.base import Plugin
from cyberhunter_3d.core.plugins.context import ScanContext

class TestPluginManager(unittest.TestCase):

    def test_dependency_resolution_simple(self):
        with patch('cyberhunter_3d.core.plugins.manager.PluginManager._discover_plugins', return_value=[]):
            plugin_manager = PluginManager()

        p1 = MagicMock(spec=Plugin)
        p1.name = "P1"
        p1.requires = []
        p1.provides = ["A"]
        p2 = MagicMock(spec=Plugin)
        p2.name = "P2"
        p2.requires = ["A"]
        p2.provides = ["B"]
        p3 = MagicMock(spec=Plugin)
        p3.name = "P3"
        p3.requires = ["B"]
        p3.provides = ["C"]
        plugin_manager.plugins = [p3, p2, p1]

        sorted_plugins = plugin_manager.resolve_dependencies()
        self.assertEqual([p.name for p in sorted_plugins], ["P1", "P2", "P3"])

    def test_dependency_resolution_missing(self):
        with patch('cyberhunter_3d.core.plugins.manager.PluginManager._discover_plugins', return_value=[]):
            plugin_manager = PluginManager()

        p1 = MagicMock(spec=Plugin)
        p1.name = "P1"
        p1.requires = ["Z"]
        p1.provides = ["A"]
        plugin_manager.plugins = [p1]

        with self.assertRaises(ValueError):
            plugin_manager.resolve_dependencies()

    def test_dependency_resolution_circular(self):
        with patch('cyberhunter_3d.core.plugins.manager.PluginManager._discover_plugins', return_value=[]):
            plugin_manager = PluginManager()

        p1 = MagicMock(spec=Plugin)
        p1.name = "P1"
        p1.requires = ["B"]
        p1.provides = ["A"]
        p2 = MagicMock(spec=Plugin)
        p2.name = "P2"
        p2.requires = ["A"]
        p2.provides = ["B"]
        plugin_manager.plugins = [p1, p2]

        with self.assertRaises(ValueError):
            plugin_manager.resolve_dependencies()

    def test_run_all_plugins_with_dependencies(self):
        call_order_mock = MagicMock()

        plugin1 = MagicMock(spec=Plugin, name="Plugin1", provides=["data1"], requires=[], run=MagicMock(side_effect=lambda ctx: call_order_mock("plugin1")))
        plugin2 = MagicMock(spec=Plugin, name="Plugin2", provides=["data2"], requires=["data1"], run=MagicMock(side_effect=lambda ctx: call_order_mock("plugin2")))
        plugin3 = MagicMock(spec=Plugin, name="Plugin3", provides=[], requires=["data2"], run=MagicMock(side_effect=lambda ctx: call_order_mock("plugin3")))

        with patch('cyberhunter_3d.core.plugins.manager.PluginManager._discover_plugins', return_value=[plugin3, plugin1, plugin2]):
            plugin_manager = PluginManager()

        context = ScanContext(target_domain="example.com")
        plugin_manager.run_all_plugins(context)

        plugin1.run.assert_called_once_with(context)
        plugin2.run.assert_called_once_with(context)
        plugin3.run.assert_called_once_with(context)

        expected_calls = [unittest.mock.call("plugin1"), unittest.mock.call("plugin2"), unittest.mock.call("plugin3")]
        self.assertEqual(call_order_mock.call_args_list, expected_calls)

if __name__ == '__main__':
    unittest.main()
