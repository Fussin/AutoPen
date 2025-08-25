import re

class ScopeValidator:
    """
    A class to validate if a target is within a defined scope,
    supporting simple domain-based wildcard rules.
    """

    def __init__(self, in_scope_rules: str, out_of_scope_rules: str):
        """
        Initializes the validator with in-scope and out-of-scope rules.

        :param in_scope_rules: A string containing one rule per line.
        :param out_of_scope_rules: A string containing one rule per line.
        """
        self.in_scope_patterns = self._compile_rules(in_scope_rules)
        self.out_of_scope_patterns = self._compile_rules(out_of_scope_rules)

    def _compile_rules(self, rules_str: str) -> list:
        """
        Converts a string of newline-separated rules into a list of
        compiled regex patterns.
        """
        patterns = []
        if not rules_str:
            return patterns

        rules = [r.strip() for r in rules_str.strip().splitlines() if r.strip()]
        for rule in rules:
            # Escape regex special characters, then replace wildcard '*' with '.*'
            pattern_str = re.escape(rule).replace(r'\*', r'[^.]+')
            # Anchor the pattern to match the whole string
            patterns.append(re.compile(f"^{pattern_str}$"))
        return patterns

    def is_in_scope(self, target: str) -> bool:
        """
        Checks if a target string is within the defined scope.

        A target is in scope if:
        1. It matches at least one in-scope rule (if any are defined).
        2. It does not match any out-of-scope rules.

        :param target: The target string to check (e.g., a domain or subdomain).
        :return: True if the target is in scope, False otherwise.
        """
        target = target.strip().lower()

        # 1. Check against out-of-scope rules first.
        # If it matches any out-of-scope rule, it's definitively out.
        for pattern in self.out_of_scope_patterns:
            if pattern.match(target):
                return False

        # 2. Check against in-scope rules.
        # If no in-scope rules are defined, everything that is not
        # explicitly out-of-scope is considered in-scope.
        if not self.in_scope_patterns:
            return True

        # If in-scope rules are defined, it must match at least one.
        for pattern in self.in_scope_patterns:
            if pattern.match(target):
                return True

        # If in-scope rules exist but none matched, it's out of scope.
        return False

if __name__ == '__main__':
    # Example Usage for direct testing
    in_scope = """
    *.example.com
    sub.another.net
    """
    out_of_scope = """
    api.example.com
    *.dev.example.com
    """

    validator = ScopeValidator(in_scope, out_of_scope)

    # Test cases
    test_targets = {
        "www.example.com": True,      # Matches *.example.com
        "sub.another.net": True,      # Matches exact rule
        "api.example.com": False,     # Matches out-of-scope rule
        "test.dev.example.com": False, # Matches *.dev.example.com
        "another.example.com": True, # Matches *.example.com
        "google.com": False,          # Does not match any in-scope rule
        "dev.example.com": True,      # This is an interesting case. It does not match *.dev, but matches *.example
    }

    print("--- Running ScopeValidator Tests ---")
    for t, expected in test_targets.items():
        actual = validator.is_in_scope(t)
        status = "✅" if actual == expected else "❌"
        print(f"{status} Target: {t}, Expected: {expected}, Got: {actual}")
