from collections import deque
from typing import Deque, List, Tuple

from .target_parser import parse_targets
from .scope_validator import ScopeValidator
from .reconnaissance.utils import load_config
<<<<<<< HEAD
from .feeds.crtsh_client import get_subdomains_from_crtsh
=======

from .feeds.crtsh_client import get_subdomains_from_crtsh

from .feeds.hackerone_client import get_hackerone_scopes
from .feeds.bugcrowd_client import get_bugcrowd_programs
from .feeds.diodb_client import get_diodb_programs

>>>>>>> 525ac14ad8592b1fe5b703f44fd8b258c944c147


class DataPipeline:
    """
    A data processing pipeline to validate, normalize, and prioritize targets.
    """

    def __init__(self, config: dict = None):
        """
        Initializes the pipeline with scope validation rules from a config.

        :param config: A dictionary containing the application configuration.
                       If None, the config is loaded from the default file.
        """
        if config is None:
            config = load_config()

        pipeline_config = config.get('data_pipeline', {})
        in_scope_rules = pipeline_config.get('in_scope_rules', '')
        out_of_scope_rules = pipeline_config.get('out_of_scope_rules', '')

        self.scope_validator = ScopeValidator(in_scope_rules, out_of_scope_rules)
        self.processed_targets_queue: Deque[Tuple[str, str]] = deque()

<<<<<<< HEAD
=======

        hackerone_config = config.get('hackerone', {})
        self.h1_user = hackerone_config.get('api_user')
        self.h1_key = hackerone_config.get('api_key')

        bugcrowd_config = config.get('bugcrowd', {})
        self.bc_user = bugcrowd_config.get('api_user')
        self.bc_key = bugcrowd_config.get('api_key')


>>>>>>> 525ac14ad8592b1fe5b703f44fd8b258c944c147
    def run(self, raw_targets: List[str]) -> Deque[Tuple[str, str]]:
        """
        Executes the full data processing pipeline on a list of raw targets.

        :param raw_targets: A list of strings, where each string is a potential target.
        :return: A deque of processed, validated, and prioritized targets.
        """
        # 1. Raw Input & Validation Stage
        validated_targets = self._parse_and_validate(raw_targets)

        # 2. Normalization Stage
        normalized_targets = self._normalize(validated_targets)

        # 3. Processing Stage (Prioritization & Queuing)
        self.processed_targets_queue = self._prioritize(normalized_targets)

        return self.processed_targets_queue

    def _parse_and_validate(self, raw_targets: List[str]) -> List[Tuple[str, str]]:
        """
        Parses raw target strings and validates them against scope rules.
        """
        # Use target_parser to get (value, type) tuples
        parsed_targets = parse_targets(raw_targets)

        # Filter based on scope rules
        scoped_targets = []
        for value, target_type in parsed_targets:
            # Scope validation is typically applied to domains/subdomains.
            # You might extend this to IPs or other types if needed.
            if target_type in ['domain', 'wildcard_domain']:
                if self.scope_validator.is_in_scope(value):
                    scoped_targets.append((value, target_type))
            else:
                # For now, we assume non-domain targets are in scope.
                # This could be adjusted based on requirements.
                scoped_targets.append((value, target_type))

        return scoped_targets

    def _normalize(self, targets: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        """
        Normalizes and deduplicates a list of targets.
        """
        # Deduplication using a set for efficiency
        # The (value, type) tuples are already reasonably normalized by the parser.
        unique_targets = list(set(targets))
        return unique_targets

    def _prioritize(self, targets: List[Tuple[str, str]]) -> Deque[Tuple[str, str]]:
        """
        Prioritizes targets and loads them into a deque.
        For now, a simple prioritization scheme: domains > wildcards > IPs > CIDRs > others.
        """
        priority_order = {
            'domain': 1,
            'wildcard_domain': 2,
            'ip_address': 3,
            'cidr': 4,
            'asn': 5,
            'org_name': 6
        }

        # Sort targets based on the priority order
        sorted_targets = sorted(
            targets,
            key=lambda t: priority_order.get(t[1], 99) # Default to low priority
        )

        return deque(sorted_targets)

    def get_next_target(self) -> Tuple[str, str] | None:
        """
        Returns the next target from the queue, or None if empty.
        """
        try:
            return self.processed_targets_queue.popleft()
        except IndexError:
            return None

    def _fetch_autonomous_targets(self, seed_domain: str) -> List[str]:
        """
        Fetches a list of potential targets from autonomous sources.
<<<<<<< HEAD

        :param seed_domain: The domain to use as a seed for discovery.
        :return: A list of raw target strings.
        """
        print(f"Fetching autonomous targets for seed: {seed_domain}")
        # For now, we'll just use crt.sh. This can be expanded later.
        subdomains = get_subdomains_from_crtsh(seed_domain)
        # We also include the seed domain itself as a target.
        subdomains.append(seed_domain)
        return subdomains

    def _generate_dynamic_scope(self, seed_domain: str):
        """
        Generates a dynamic scope based on a seed domain and re-initializes
        the scope validator.

        This will override any scope rules loaded from the config.

        :param seed_domain: The domain to use for generating the scope.
        """
        print(f"Generating dynamic scope for seed: {seed_domain}")
        # A simple dynamic scope: the domain and all its subdomains.
        in_scope_rule = f"*.{seed_domain}\n{seed_domain}"

        # For this simple case, we assume no out-of-scope rules are
        # dynamically generated, but this could be expanded.
        out_of_scope_rules = ""

        # Re-initialize the scope validator with the new dynamic rules.
        self.scope_validator = ScopeValidator(in_scope_rule, out_of_scope_rules)

    def run_autonomous(self, seed_domain: str) -> Deque[Tuple[str, str]]:
        """
        Runs the pipeline in autonomous mode.

        1. Generates a dynamic scope from the seed domain.
        2. Fetches targets from autonomous sources.
        3. Runs the standard processing pipeline on the fetched targets.

        :param seed_domain: The domain to use as a seed for the run.
        :return: A deque of processed, validated, and prioritized targets.
        """
        # Step 1: Generate dynamic scope
        self._generate_dynamic_scope(seed_domain)

        # Step 2: Fetch targets from autonomous sources
        raw_targets = self._fetch_autonomous_targets(seed_domain)

        # Step 3: Run the standard pipeline on the fetched targets
        return self.run(raw_targets)
=======

        :param seed_domain: The domain to use as a seed for discovery.
        :return: A list of raw target strings.
        """

        Runs the pipeline in autonomous mode by fetching targets from multiple sources.

        print(f"Fetching autonomous targets for seed: {seed_domain}")
        # For now, we'll just use crt.sh. This can be expanded later.
        subdomains = get_subdomains_from_crtsh(seed_domain)
        # We also include the seed domain itself as a target.
        subdomains.append(seed_domain)
        return subdomains

    def _generate_dynamic_scope(self, seed_domain: str):
        """
        Generates a dynamic scope based on a seed domain and re-initializes
        the scope validator.

        This will override any scope rules loaded from the config.

        :param seed_domain: The domain to use for generating the scope.
        """

        print(f"Generating dynamic scope for seed: {seed_domain}")
        # A simple dynamic scope: the domain and all its subdomains.
        in_scope_rule = f"*.{seed_domain}\n{seed_domain}"

        Runs the pipeline in autonomous mode by fetching targets from HackerOne and Bugcrowd.



        # For this simple case, we assume no out-of-scope rules are
        # dynamically generated, but this could be expanded.
        out_of_scope_rules = ""

        # Re-initialize the scope validator with the new dynamic rules.
        self.scope_validator = ScopeValidator(in_scope_rule, out_of_scope_rules)

    def run_autonomous(self, seed_domain: str) -> Deque[Tuple[str, str]]:
        """

        Runs the pipeline in autonomous mode.

        1. Generates a dynamic scope from the seed domain.
        2. Fetches targets from autonomous sources.
        3. Runs the standard processing pipeline on the fetched targets.

        :param seed_domain: The domain to use as a seed for the run.
        :return: A deque of processed, validated, and prioritized targets.
        """
        # Step 1: Generate dynamic scope
        self._generate_dynamic_scope(seed_domain)

        # Step 2: Fetch targets from autonomous sources
        raw_targets = self._fetch_autonomous_targets(seed_domain)

        # Step 3: Run the standard pipeline on the fetched targets
        return self.run(raw_targets)

        all_programs = []
        program_names = set()

        # Helper to process and deduplicate programs
        def process_programs(programs, source_name):
            count = 0
            for prog in programs:
                name = prog.get('name')
                if name and name.lower() not in program_names:
                    program_names.add(name.lower())
                    all_programs.append(prog)
                    count += 1
            print(f"Found {count} new programs from {source_name}.")

        # Fetch from HackerOne
        if self.h1_user and self.h1_key:
            print("Fetching programs from HackerOne...")
            h1_programs = get_hackerone_scopes(self.h1_user, self.h1_key)
            process_programs(h1_programs, "HackerOne")
        else:
            print("HackerOne API user or key not configured. Skipping.")

        # Fetch from Bugcrowd
        if self.bc_user and self.bc_key:
            print("Fetching programs from Bugcrowd...")
            bc_programs = get_bugcrowd_programs(self.bc_user, self.bc_key)
            process_programs(bc_programs, "Bugcrowd")
        else:
            print("Bugcrowd API user or key not configured. Skipping.")

        # Fetch from diodb
        print("Fetching programs from diodb...")
        diodb_programs = get_diodb_programs()
        process_programs(diodb_programs, "diodb")

        print(f"Total unique programs found: {len(all_programs)}")
        return all_programs

>>>>>>> 525ac14ad8592b1fe5b703f44fd8b258c944c147
