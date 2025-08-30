import concurrent.futures
from typing import List, Dict, Any, Set
from cyberhunter_3d.core.plugins.base import Plugin
from cyberhunter_3d.utils.logger import setup_logger
from cyberhunter_3d.core.reconnaissance.utils import load_config, run_command

class PassiveEnumPlugin(Plugin):
    """
    Plugin for passive subdomain enumeration.
    """
    @property
    def name(self) -> str:
        return "Passive Enumeration"

    @property
    def description(self) -> str:
        return "Runs passive subdomain enumeration tools like subfinder, amass, etc."

    @property
    def provides(self) -> List[str]:
        return ["subdomains"]

    def run(self, context: 'ScanContext'):
        logger = setup_logger('PassiveEnumPlugin', 'passive_enum_plugin.log')
        config = load_config()
        target = context.target

        logger.info(f"Starting passive enumeration for: {target}")

        commands = [
            [config['tools']['subfinder'], '-d', '{domain}', '-o', '{output_file}', '-silent'],
            [config['tools']['amass'], 'enum', '-passive', '-d', '{domain}', '-o', '{output_file}'],
            [config['tools']['assetfinder'], '--subs-only', '{domain}'],
            [config['tools']['waybackurls'], '{domain}'],
        ]

        all_subdomains = set()
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(commands)) as executor:
            future_to_command = {executor.submit(run_command, cmd, target, logger): cmd for cmd in commands}
            for future in concurrent.futures.as_completed(future_to_command):
                command = future_to_command[future]
                try:
                    subdomains = future.result()
                    logger.info(f"Found {len(subdomains)} subdomains with {' '.join(map(str, command))}")
                    all_subdomains.update(subdomains)
                except Exception as exc:
                    logger.error(f"'{' '.join(map(str, command))}' generated an exception: {exc}")

        logger.info(f"Total unique passive subdomains found: {len(all_subdomains)}")
        context.update_set("subdomains", all_subdomains)
