import logging
import tempfile
import os
from typing import List, Set
from ..base import Plugin
from ..context import ScanContext
from ....utils.file_utils import run_command
from ...reconnaissance.utils import load_config

log = logging.getLogger(__name__)

class PermutationEnumPlugin(Plugin):
    """
    Plugin for permutation-based subdomain enumeration.
    """
    def __init__(self):
        super().__init__()
        self.config = load_config()

    @property
    def name(self) -> str:
        return "permutation_enum"

    @property
    def description(self) -> str:
        return "Generates and validates subdomains based on permutations."

    @property
    def requires(self) -> List[str]:
        return ["validated_subdomains"]

    @property
    def provides(self) -> List[str]:
        return ["permutation_subdomains"]

    def run(self, context: ScanContext):
        log.info("Running permutation enumeration plugin...")
        known_subdomains = context.get("validated_subdomains")
        if not known_subdomains:
            log.warning("No known subdomains to permute. Skipping.")
            context.set("permutation_subdomains", set())
            return

        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as subs_file:
            subs_file.write('\n'.join(known_subdomains))
            subs_filename = subs_file.name

        try:
            dnsgen_path = self.config['tools']['dnsgen']
            dnsgen_cmd = [dnsgen_path, subs_filename]
            permutations = run_command(dnsgen_cmd).strip().split('\n')
            log.info(f"Generated {len(permutations)} permutations.")

            resolvers = self.config['wordlists']['resolvers']
            validated_permutations = self._validate_subdomains(set(permutations), resolvers)

            context.set("permutation_subdomains", validated_permutations)

            # Add to the main subdomains list
            existing_subdomains = context.get("subdomains", set())
            combined_subdomains = existing_subdomains.union(validated_permutations)
            context.set("subdomains", combined_subdomains)

            log.info(f"Found {len(validated_permutations)} new validated subdomains from permutations.")

        finally:
            os.remove(subs_filename)


    def _validate_subdomains(self, subdomains: Set[str], resolvers: str) -> Set[str]:
        if not subdomains:
            return set()

        validated = set()
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp_subs:
            tmp_subs.write('\n'.join(subdomains))
            tmp_subs_path = tmp_subs.name

        try:
            validation_cmd = ["dnsx", "-l", tmp_subs_path, "-r", resolvers, "-silent"]
            result = run_command(validation_cmd)
            validated = set(result.strip().split('\n'))
            log.info(f"Validated {len(validated)} live permutation subdomains.")
        except Exception as e:
            log.error(f"Error during permutation validation: {e}")
        finally:
            os.remove(tmp_subs_path)

        return validated
