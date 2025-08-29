import os
import importlib
from typing import List
from .base import Plugin

from cyberhunter_3d.core.reconnaissance.utils import load_config

class PluginManager:
    """
    Manages the discovery, loading, and execution of plugins.
    """
    def __init__(self, plugin_dir: str):
        self.plugin_dir = plugin_dir
        self.config = load_config()
        self.plugins = self._load_plugins()

    def _load_plugins(self) -> List[Plugin]:
        """
        Dynamically loads all enabled plugins from the plugin directory.
        """
        plugins = []
        enabled_plugins = self.config.get('plugins', {}).get('enabled', [])

        if not os.path.exists(self.plugin_dir):
            return plugins

        for filename in os.listdir(self.plugin_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                module_name = filename[:-3]
                module_path = f"plugins.{module_name}"

                try:
                    module = importlib.import_module(module_path)
                    for item_name in dir(module):
                        item = getattr(module, item_name)
                        if isinstance(item, type) and issubclass(item, Plugin) and item is not Plugin:
                            plugin_instance = item()
                            if plugin_instance.name in enabled_plugins:
                                plugins.append(plugin_instance)
                except Exception as e:
                    print(f"Error loading plugin {module_name}: {e}")

        return plugins

    def get_all_plugins(self) -> List[Plugin]:
        """Returns a list of all loaded plugin instances."""
        return self.plugins

    def run_all_plugins(self, target: str, **kwargs):
        """
        Runs all loaded plugins.
        """
        all_results = {}
        for plugin in self.plugins:
            try:
                results = plugin.run(target, **kwargs)
                all_results[plugin.name] = results
            except Exception as e:
                print(f"Error running plugin {plugin.name}: {e}")
        return all_results
