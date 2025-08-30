import os
import importlib
from typing import List, Dict, Set
from collections import deque
from .base import Plugin
from ..core.context import ScanContext
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
        Dynamically loads all enabled plugins from the plugin directory and sorts them by dependency.
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

        return self._resolve_dependencies(plugins)

    def _resolve_dependencies(self, plugins: List[Plugin]) -> List[Plugin]:
        """
        Sorts plugins based on their declared dependencies using topological sort.
        """
        plugin_map = {p.name: p for p in plugins}
        provides_map: Dict[str, str] = {}
        for p in plugins:
            for item in p.provides:
                provides_map[item] = p.name

        adj: Dict[str, List[str]] = {p.name: [] for p in plugins}
        in_degree: Dict[str, int] = {p.name: 0 for p in plugins}

        for p in plugins:
            for req in p.requires:
                if req in provides_map:
                    provider_plugin_name = provides_map[req]
                    if provider_plugin_name != p.name:
                        adj[provider_plugin_name].append(p.name)
                        in_degree[p.name] += 1

        queue = deque([p.name for p in plugins if in_degree[p.name] == 0])
        sorted_plugins = []

        while queue:
            plugin_name = queue.popleft()
            sorted_plugins.append(plugin_map[plugin_name])

            for dependent_name in adj[plugin_name]:
                in_degree[dependent_name] -= 1
                if in_degree[dependent_name] == 0:
                    queue.append(dependent_name)

        if len(sorted_plugins) != len(plugins):
            raise Exception("Circular dependency detected among plugins.")

        return sorted_plugins

    def get_all_plugins(self) -> List[Plugin]:
        """Returns a list of all loaded plugin instances."""
        return self.plugins

    def run_all_plugins(self, context: ScanContext):
        """
        Runs all loaded plugins in the correct order.
        """
        for plugin in self.plugins:
            try:
                # Here you might add a check if all requirements for the plugin are met in the context
                print(f"Running plugin: {plugin.name}")
                plugin.run(context)
            except Exception as e:
                print(f"Error running plugin {plugin.name}: {e}")
