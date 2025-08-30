import os
import importlib
import inspect
import logging
from typing import List, Any, Dict
from .base import Plugin
from .context import ScanContext

log = logging.getLogger(__name__)

class OldPluginWrapper(Plugin):
    """A wrapper for old-style plugins to make them compatible with the new system."""
    def __init__(self, old_plugin_instance: Any):
        self._plugin = old_plugin_instance
        self._name = self._plugin.name
        self._description = self._plugin.description
        self._requires, self._provides = self._map_dependencies()

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def requires(self) -> List[str]:
        return self._requires

    @property
    def provides(self) -> List[str]:
        return self._provides

    def run(self, context: ScanContext):
        log.info(f"Running old-style plugin '{self.name}' via wrapper.")
        target = context.target_domain

        # This is a simplified mapping from new context to old **kwargs
        kwargs = {
            "subdomains": context.get("subdomains", set()),
            "live_hosts": context.get("validated_subdomains", set()),
            "tech_fingerprinting": context.get("tech_fingerprints", {}),
            "known_subdomains": context.get("subdomains", set()),
        }

        results = self._plugin.run(target, **kwargs)

        # Map results back to the context
        for key, value in results.items():
            context.set(key, value)

    def _map_dependencies(self) -> (List[str], List[str]):
        """A simple mapping from old plugin names to new dependency keys."""
        # This would need to be more robust in a real application
        if self.name == "Permutation Enumeration":
            return ["subdomains"], ["permutation_subdomains"]
        if self.name == "JS and Code Analysis":
            return ["validated_subdomains"], ["js_subdomains", "secrets"]
        if self.name == "Technology Fingerprinting":
            return ["validated_subdomains"], ["tech_fingerprinting", "open_ports"]
        if self.name == "Subdomain Takeover":
            return ["validated_subdomains"], ["takeover_vulnerabilities"]
        if self.name == "Cloud Enumeration":
            return ["subdomains"], ["cloud_assets"]
        if self.name == "CVE Mapper":
            return ["tech_fingerprinting"], ["cve_results"]
        # Passive plugins have no requirements
        return [], [f"{self.name.lower().replace(' ', '_')}_subdomains"]


class PluginManager:
    """
    Manages the discovery, loading, dependency resolution, and execution of plugins.
    """
    def __init__(self, new_plugin_dir="cyberhunter_3d/core/plugins/impl", old_plugin_dir="plugins"):
        self.new_plugin_dir = new_plugin_dir
        self.old_plugin_dir = old_plugin_dir
        self.plugins = self._discover_plugins()
        self.run_order: List[Plugin] = []

    def _discover_plugins(self) -> List[Plugin]:
        """
        Dynamically discovers and loads all plugins from both old and new directories.
        """
        all_plugins = []
        # Discover new-style plugins
        if os.path.exists(self.new_plugin_dir):
            print(f"Files in new_plugin_dir: {os.listdir(self.new_plugin_dir)}")
            for filename in os.listdir(self.new_plugin_dir):
                if filename.endswith(".py") and not filename.startswith("__"):
                    # Convert file path to module path
                    relative_path = os.path.relpath(self.new_plugin_dir, 'cyberhunter_3d')
                    module_base = relative_path.replace(os.sep, '.')
                    module_name = f"cyberhunter_3d.{module_base}.{filename[:-3]}"
                    try:
                        module = importlib.import_module(module_name)
                        for name, obj in inspect.getmembers(module):
                            if inspect.isclass(obj) and issubclass(obj, Plugin) and obj is not OldPluginWrapper and obj is not Plugin:
                                all_plugins.append(obj())
                    except Exception as e:
                        log.error(f"Error loading new plugin from {filename}: {e}")

        # Discover and wrap old-style plugins
        if os.path.exists(self.old_plugin_dir):
            for filename in os.listdir(self.old_plugin_dir):
                if filename.endswith(".py") and not filename.startswith("__"):
                    # Old plugins are not in a package, so we need to load them differently
                    spec = importlib.util.spec_from_file_location(filename[:-3], os.path.join(self.old_plugin_dir, filename))
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    for name, obj in inspect.getmembers(module):
                        # Heuristic to find old plugin classes
                        if inspect.isclass(obj) and hasattr(obj, 'name') and hasattr(obj, 'run') and 'Plugin' in str(obj.__bases__):
                             # Avoid wrapping the new base class if it's imported there
                            if 'cyberhunter_3d.core.plugins.base.Plugin' in str(obj.__bases__):
                                continue
                            try:
                                instance = obj()
                                all_plugins.append(OldPluginWrapper(instance))
                            except Exception as e:
                                log.error(f"Error wrapping old plugin from {filename}: {e}")

        log.info(f"Discovered {len(all_plugins)} plugins: {[p.name for p in all_plugins]}")
        return all_plugins

    def resolve_dependencies(self) -> List[Plugin]:
        """
        Resolves plugin dependencies using a topological sort algorithm.
        """
        plugins_dict = {p.name: p for p in self.plugins}
        provides_map = {}
        for p in self.plugins:
            for item in p.provides:
                provides_map[item] = p.name

        adj = {p.name: [] for p in self.plugins}
        in_degree = {p.name: 0 for p in self.plugins}

        for p in self.plugins:
            for req in p.requires:
                if req not in provides_map:
                    raise ValueError(f"Unresolvable dependency: Plugin '{p.name}' requires '{req}', which is not provided by any plugin.")

                provider_name = provides_map[req]
                if provider_name != p.name:
                    adj[provider_name].append(p.name)
                    in_degree[p.name] += 1

        queue = [p.name for p in self.plugins if in_degree[p.name] == 0]
        sorted_order = []

        while queue:
            plugin_name = queue.pop(0)
            sorted_order.append(plugins_dict[plugin_name])

            for neighbor_name in adj.get(plugin_name, []):
                in_degree[neighbor_name] -= 1
                if in_degree[neighbor_name] == 0:
                    queue.append(neighbor_name)

        if len(sorted_order) != len(self.plugins):
            raise ValueError("Circular dependency detected among plugins.")

        return sorted_order

    def run_all_plugins(self, context: ScanContext):
        """
        Runs all registered plugins in an order that respects their dependencies.
        """
        self.run_order = self.resolve_dependencies()
        log.info(f"Plugin execution order: {[p.name for p in self.run_order]}")

        for plugin in self.run_order:
            log.info(f"Running plugin: {plugin.name}")
            try:
                plugin.run(context)
            except Exception as e:
                log.error(f"Error running plugin {plugin.name}: {e}")
