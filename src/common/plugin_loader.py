import os
import importlib
from typing import List, Dict
from src.common.base_plugin import Plugin

def load_plugins(plugin_dir: str, config: Dict) -> List[Plugin]:
    """
    Loads all enabled plugins from a directory.
    """
    plugins = []
    plugin_phase = os.path.basename(plugin_dir)
    for filename in os.listdir(plugin_dir):
        if filename.endswith(".py") and not filename.startswith("__"):
            plugin_name = filename[:-3]
            # Check if the plugin is enabled in the config
            if config.get("plugins", {}).get(plugin_name, {}).get("enabled", False):
                module_name = f"src.plugins.{plugin_phase}.{plugin_name}"
                try:
                    module = importlib.import_module(module_name)
                    for item in dir(module):
                        obj = getattr(module, item)
                        if isinstance(obj, type) and issubclass(obj, Plugin) and obj is not Plugin:
                            plugins.append(obj())
                except ImportError as e:
                    print(f"Error loading plugin {module_name}: {e}")
    return plugins
