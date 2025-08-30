import subprocess
import tempfile
import os
import concurrent.futures
from typing import Set, List, Dict, Any
from cyberhunter_3d.core.plugins.base import Plugin
from cyberhunter_3d.utils.logger import setup_logger
from cyberhunter_3d.core.reconnaissance.utils import load_config, run_command
from cyberhunter_3d.core.reconnaissance.ai.wordlist_generator import generate_ai_wordlist

class PermutationEnumPlugin(Plugin):
    """
    Plugin for permutation-based subdomain enumeration.
    """
    @property
    def name(self) -> str:
        return "Permutation Enumeration"

    @property
    def description(self) -> str:
        return "Runs permutation-based subdomain enumeration tools."

    @property
    def requires(self) -> List[str]:
        return ["subdomains"]

    @property
    def provides(self) -> List[str]:
        return ["subdomains"]

    def run(self, context: 'ScanContext'):
        logger = setup_logger('PermutationEnumPlugin', 'permutation_enum_plugin.log')
        config = load_config()
        target = context.target

        known_subdomains = context.get("subdomains")
        if not known_subdomains:
            logger.warning("No known subdomains to permute. Skipping permutation engine.")
            return

        custom_wordlist_filename = self._generate_custom_wordlist(known_subdomains, logger)

        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as tmp_file:
            subdomain_filename = tmp_file.name
            for sub in known_subdomains:
                tmp_file.write(f"{sub}\n")

        generic_wordlist = config['wordlists']['dns_bruteforce']
        combined_wordlist_filename = f"combined_wordlist_{target}.txt"
        with open(combined_wordlist_filename, 'w') as outfile:
            for wordlist in [generic_wordlist, custom_wordlist_filename]:
                if os.path.exists(wordlist):
                    with open(wordlist, 'r') as infile:
                        outfile.write(infile.read())

        commands = [
            [config['tools']['dnsgen'], subdomain_filename, '-w', combined_wordlist_filename, '-o', '{output_file}'],
            [config['tools']['gotator'], '-sub', subdomain_filename, '-perm', combined_wordlist_filename, '-depth', '2', '-mindup', '>', '{output_file}']
        ]

        all_subdomains = set()
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(commands)) as executor:
            future_to_command = {executor.submit(run_command, cmd, target, logger, combined_wordlist_filename): cmd for cmd in commands}
            for future in concurrent.futures.as_completed(future_to_command):
                command = future_to_command[future]
                try:
                    subdomains = future.result()
                    all_subdomains.update(subdomains)
                except Exception as exc:
                    logger.error(f"'{' '.join(map(str, command))}' generated an exception: {exc}")

        os.remove(subdomain_filename)
        os.remove(custom_wordlist_filename)
        os.remove(combined_wordlist_filename)

        validated_subdomains = self._validate_subdomains(all_subdomains, config, logger)

        context.update_set("subdomains", validated_subdomains)

    def _generate_custom_wordlist(self, subdomains: Set[str], logger) -> str:
        custom_words = set()
        for sub in subdomains:
            parts = sub.split('.')
            if len(parts) > 2:
                subdomain_part = '.'.join(parts[:-2])
                for word in subdomain_part.replace('-', '.').split('.'):
                    if word and not word.isnumeric():
                        custom_words.add(word)

        ai_words = generate_ai_wordlist(custom_words)
        custom_words.update(ai_words)

        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as tmp_file:
            wordlist_filename = tmp_file.name
            for word in custom_words:
                tmp_file.write(f"{word}\n")
        return wordlist_filename

    def _validate_subdomains(self, subdomains: Set[str], config: Dict, logger) -> Set[str]:
        if not subdomains:
            return set()

        validated_subdomains = set()
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as potential_subs_file:
            potential_subs_filename = potential_subs_file.name
            for sub in subdomains:
                potential_subs_file.write(f"{sub}\n")

        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as validated_subs_file:
            validated_subs_filename = validated_subs_file.name

        try:
            resolvers = config['wordlists']['resolvers']
            puredns_resolve_cmd = [config['tools']['puredns'], 'resolve', potential_subs_filename, '-r', resolvers, '-w', validated_subs_filename]
            subprocess.run(puredns_resolve_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            with open(validated_subs_filename, 'r') as f:
                for line in f:
                    validated_subdomains.add(line.strip())
        except Exception as e:
            logger.error(f"Error during puredns validation: {e}")
            return subdomains
        finally:
            os.remove(potential_subs_filename)
            os.remove(validated_subs_filename)

        return validated_subdomains
