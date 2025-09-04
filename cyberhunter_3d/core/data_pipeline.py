from collections import deque
from typing import Deque, List, Tuple

from .target_parser import parse_targets
from .scope_validator import ScopeValidator
from .reconnaissance.utils import load_config
from .feeds.hackerone_client import get_hackerone_scopes
from .feeds.bugcrowd_client import get_bugcrowd_programs


class DataPipeline:
    """
    A data processing pipeline to validate, normalize, and prioritize targets.
    """

    def __init__(self, config: dict = None, in_scope_rules: str = None, out_of_scope_rules: str = None):
        """
        Initializes the pipeline with scope validation rules.

        :param config: A dictionary containing the application configuration.
        :param in_scope_rules: A string of in-scope rules. Overrides config if provided.
        :param out_of_scope_rules: A string of out-of-scope rules. Overrides config if provided.
        """
        if config is None:
            config = load_config()

        if in_scope_rules is None or out_of_scope_rules is None:
            pipeline_config = config.get('data_pipeline', {})
            in_scope_rules = in_scope_rules or pipeline_config.get('in_scope_rules', '')
            out_of_scope_rules = out_of_scope_rules or pipeline_config.get('out_of_scope_rules', '')

        self.scope_validator = ScopeValidator(in_scope_rules, out_of_scope_rules)
        self.processed_targets_queue: Deque[Tuple[str, str]] = deque()

        hackerone_config = config.get('hackerone', {})
        self.h1_user = hackerone_config.get('api_user')
        self.h1_key = hackerone_config.get('api_key')

        bugcrowd_config = config.get('bugcrowd', {})
        self.bc_user = bugcrowd_config.get('api_user')
        self.bc_key = bugcrowd_config.get('api_key')

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

    def run_autonomous(self) -> List[dict]:
        """
        Runs the pipeline in autonomous mode by fetching targets from HackerOne and Bugcrowd.

        :return: A list of program dictionaries, each containing targets and scope.
        """
        all_programs = []

        if self.h1_user and self.h1_key:
            print("Fetching programs from HackerOne...")
            h1_programs = get_hackerone_scopes(self.h1_user, self.h1_key)
            all_programs.extend(h1_programs)
            print(f"Found {len(h1_programs)} programs on HackerOne.")
        else:
            print("HackerOne API user or key not configured. Skipping.")

        if self.bc_user and self.bc_key:
            print("Fetching programs from Bugcrowd...")
            bc_programs = get_bugcrowd_programs(self.bc_user, self.bc_key)
            all_programs.extend(bc_programs)
            print(f"Found {len(bc_programs)} programs on Bugcrowd.")
        else:
            print("Bugcrowd API user or key not configured. Skipping.")

        return all_programs
