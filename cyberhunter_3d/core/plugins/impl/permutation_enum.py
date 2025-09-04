import logging
import tempfile
import os
from typing import List, Set
from ..base import Plugin
from ..context import ScanContext
from ...reconnaissance.utils import load_config, run_command
from ...reconnaissance.ai.wordlist_generator import extract_keywords_from_subdomains, generate_intelligent_wordlist
from ....web.models import Asset, Target

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

        previous_subdomains = self._get_previous_subdomains(context.target_domain)
        keywords = extract_keywords_from_subdomains(previous_subdomains)
        intelligent_wordlist = generate_intelligent_wordlist(keywords)

        if not intelligent_wordlist:
            log.warning("No intelligent wordlist generated. Skipping permutation.")
            context.set("permutation_subdomains", set())
            return

        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as wordlist_file:
            wordlist_file.write('\n'.join(intelligent_wordlist))
            wordlist_filename = wordlist_file.name

        try:
            dnsgen_path = self.config['tools']['dnsgen']
            dnsgen_cmd = [dnsgen_path, "-w", wordlist_filename, context.target_domain]
            permutations = run_command(dnsgen_cmd, context.target_domain, log).strip().split('\n')
            log.info(f"Generated {len(permutations)} permutations with intelligent wordlist.")

            resolvers = self.config['wordlists']['resolvers']
            validated_permutations = self._validate_subdomains(set(permutations), resolvers)

            context.set("permutation_subdomains", validated_permutations)

            existing_subdomains = context.get("subdomains", set())
            combined_subdomains = existing_subdomains.union(validated_permutations)
            context.set("subdomains", combined_subdomains)

            log.info(f"Found {len(validated_permutations)} new validated subdomains from permutations.")

        finally:
            os.remove(wordlist_filename)

    def _get_previous_subdomains(self, target_domain: str) -> List[str]:
        try:
            from run_web import app
            with app.app_context():
                targets = Target.query.filter_by(value=target_domain).all()
                scan_ids = {t.scan_id for t in targets}
                assets = Asset.query.filter(Asset.scan_id.in_(scan_ids), Asset.type == 'subdomain').all()
                return [a.value for a in assets]
        except Exception as e:
            log.error(f"Could not fetch previous subdomains from database: {e}")
            return []


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
            log.info(f"Validated {len(validated)} live permutation subdomains.")
        except Exception as e:
            log.error(f"Error during permutation validation: {e}")
        finally:
            os.remove(tmp_subs_path)

        return validated
