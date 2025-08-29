import concurrent.futures
import subprocess
import tempfile
import os
from typing import List, Dict, Any, Set
from cyberhunter_3d.core.plugins.base import Plugin
from cyberhunter_3d.utils.logger import setup_logger
from cyberhunter_3d.core.reconnaissance.utils import load_config, run_command

class ActiveEnumPlugin(Plugin):
    """
    Plugin for active subdomain enumeration.
    """
    @property
    def name(self) -> str:
        return "Active Enumeration"

    @property
    def description(self) -> str:
        return "Runs active subdomain enumeration tools like gobuster, puredns bruteforce, etc."

    def run(self, target: str, **kwargs) -> Dict[str, Any]:
        logger = setup_logger('ActiveEnumPlugin', 'active_enum_plugin.log')
        config = load_config()

        logger.info(f"Starting active enumeration for: {target}")

        wordlist = config['wordlists']['dns_bruteforce']
        resolvers = config['wordlists']['resolvers']

        commands = [
            [config['tools']['gobuster'], 'dns', '-d', '{domain}', '-w', wordlist, '-o', '{output_file}', '-q'],
            [config['tools']['puredns'], 'bruteforce', wordlist, '{domain}', '-r', resolvers, '-w', '{output_file}'],
            [config['tools']['nmap'], '--script', 'dns-zone-transfer', '-p', '53', '{domain}', '-oN', '{output_file}']
        ]

        all_subdomains = set()
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(commands)) as executor:
            future_to_command = {executor.submit(run_command, cmd, target, logger, wordlist): cmd for cmd in commands}
            for future in concurrent.futures.as_completed(future_to_command):
                command = future_to_command[future]
                try:
                    subdomains = future.result()
                    logger.info(f"Found {len(subdomains)} subdomains with {' '.join(map(str, command))}")
                    all_subdomains.update(subdomains)
                except Exception as exc:
                    logger.error(f"'{' '.join(map(str, command))}' generated an exception: {exc}")

        logger.info(f"Found {len(all_subdomains)} potential subdomains from initial active enumeration.")

        validated_subdomains = self._validate_subdomains(all_subdomains, resolvers, config, logger)

        logger.info(f"Total unique validated active subdomains found: {len(validated_subdomains)}")
        return {"active_subdomains": validated_subdomains}

    def _validate_subdomains(self, subdomains: Set[str], resolvers: str, config: Dict, logger) -> Set[str]:
        if not subdomains:
            return set()

        logger.info("Starting mass DNS resolution to validate potential subdomains...")
        validated_subdomains = set()
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as potential_subs_file:
            potential_subs_filename = potential_subs_file.name
            for sub in subdomains:
                potential_subs_file.write(f"{sub}\n")

        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as validated_subs_file:
            validated_subs_filename = validated_subs_file.name

        try:
            puredns_resolve_cmd = [
                config['tools']['puredns'], 'resolve', potential_subs_filename,
                '-r', resolvers, '-w', validated_subs_filename
            ]
            subprocess.run(puredns_resolve_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            with open(validated_subs_filename, 'r') as f:
                for line in f:
                    validated_subdomains.add(line.strip())
            logger.info(f"Validated {len(validated_subdomains)} live subdomains.")

        except Exception as e:
            logger.error(f"Error during puredns validation: {e}")
            return subdomains
        finally:
            os.remove(potential_subs_filename)
            os.remove(validated_subs_filename)

        return validated_subdomains
