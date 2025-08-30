import concurrent.futures
import logging
import subprocess
import tempfile
import os
from typing import List, Set
from ..base import Plugin
from ..context import ScanContext
from ...reconnaissance.utils import load_config, run_command

log = logging.getLogger(__name__)

class ActiveEnumPlugin(Plugin):
    """
    Plugin for active subdomain enumeration and validation.
    """
    def __init__(self):
        super().__init__()
        self.config = load_config()

    @property
    def name(self) -> str:
        return "active_enum"

    @property
    def description(self) -> str:
        return "Performs DNS bruteforcing and validates subdomains."

    @property
    def requires(self) -> List[str]:
        return ["passive_subdomains"]

    @property
    def provides(self) -> List[str]:
        return ["active_subdomains", "validated_subdomains"]

    def run(self, context: ScanContext):
        log.info("Running active enumeration plugin...")
        target = context.target_domain

        wordlist = self.config['wordlists']['dns_bruteforce']
        resolvers = self.config['wordlists']['resolvers']
        dnsx_path = self.config['tools']['dnsx']

        bruteforce_cmd = [dnsx_path, "-d", target, "-w", wordlist, "-silent"]
        bruteforce_subdomains = set(run_command(bruteforce_cmd, target, log).strip().split('\n'))
        log.info(f"Found {len(bruteforce_subdomains)} subdomains via bruteforce.")

        passive_subdomains = context.get("passive_subdomains", set())
        all_potential_subdomains = bruteforce_subdomains.union(passive_subdomains)

        log.info(f"Validating {len(all_potential_subdomains)} total potential subdomains...")
        validated_subdomains = self._validate_subdomains(all_potential_subdomains, resolvers)

        context.set("active_subdomains", bruteforce_subdomains)
        context.set("validated_subdomains", validated_subdomains)

        existing_subdomains = context.get("subdomains", set())
        combined_subdomains = existing_subdomains.union(validated_subdomains)
        context.set("subdomains", combined_subdomains)

        log.info(f"Found {len(validated_subdomains)} validated active subdomains.")

    def _validate_subdomains(self, subdomains: Set[str], resolvers: str) -> Set[str]:
        if not subdomains:
            return set()

        validated = set()
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp_subs:
            tmp_subs.write('\n'.join(subdomains))
            tmp_subs_path = tmp_subs.name

        try:
            dnsx_path = self.config['tools']['dnsx']
            validation_cmd = [dnsx_path, "-l", tmp_subs_path, "-r", resolvers, "-silent"]
            result = run_command(validation_cmd, "", log)
            validated = set(result.strip().split('\n'))
            log.info(f"Validated {len(validated)} live subdomains.")
        except Exception as e:
            log.error(f"Error during subdomain validation: {e}")
        finally:
            os.remove(tmp_subs_path)

        return validated
