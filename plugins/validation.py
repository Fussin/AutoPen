from typing import List, Dict, Any
from cyberhunter_3d.core.plugins.base import Plugin
from cyberhunter_3d.core.context import ScanContext
from cyberhunter_3d.utils.logger import setup_logger
from cyberhunter_3d.core.reconnaissance.utils import detect_wildcard_ips, resolve_and_validate

class ValidationPlugin(Plugin):
    """
    Plugin for validating discovered subdomains and identifying live hosts.
    """
    @property
    def name(self) -> str:
        return "Validation"

    @property
    def description(self) -> str:
        return "Validates subdomains and identifies live hosts."

    @property
    def requires(self) -> List[str]:
        return ["subdomains"]

    @property
    def provides(self) -> List[str]:
        return ["live_hosts", "ip_map"]

    def run(self, context: ScanContext):
        logger = setup_logger('ValidationPlugin', 'validation_plugin.log')
        target = context.target
        subdomains = context.get("subdomains")

        if not subdomains:
            logger.info("No subdomains to validate.")
            return

        logger.info("Validating all discovered subdomains...")
        wildcard_ips = detect_wildcard_ips(target, logger)
        live_subdomains_map = resolve_and_validate(subdomains, wildcard_ips, logger)

        context.set("live_hosts", set(live_subdomains_map.keys()))
        context.set("ip_map", live_subdomains_map)
