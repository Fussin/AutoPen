import unittest
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from cyberhunter_3d.core.scope_validator import ScopeValidator

class TestScopeValidator(unittest.TestCase):

    def test_in_scope_match(self):
        validator = ScopeValidator("*.example.com", "")
        self.assertTrue(validator.is_in_scope("www.example.com"))
        self.assertTrue(validator.is_in_scope("api.example.com"))
        self.assertFalse(validator.is_in_scope("www.google.com"))

    def test_out_of_scope_match(self):
        validator = ScopeValidator("*.example.com", "api.example.com")
        self.assertTrue(validator.is_in_scope("www.example.com"))
        self.assertFalse(validator.is_in_scope("api.example.com"))

    def test_out_of_scope_wildcard(self):
        validator = ScopeValidator("*.example.com", "*.dev.example.com")
        self.assertTrue(validator.is_in_scope("www.example.com"))
        self.assertFalse(validator.is_in_scope("test.dev.example.com"))
        self.assertTrue(validator.is_in_scope("dev.example.com"))

    def test_no_in_scope_rules(self):
        # If no in-scope rules, everything is in-scope unless it's out-of-scope
        validator = ScopeValidator("", "test.google.com")
        self.assertTrue(validator.is_in_scope("anything.com"))
        self.assertFalse(validator.is_in_scope("test.google.com"))

    def test_no_rules(self):
        # If no rules at all, everything is in-scope
        validator = ScopeValidator("", "")
        self.assertTrue(validator.is_in_scope("anything.goes.com"))

    def test_exact_match_precedence(self):
        # Out-of-scope exact match should override in-scope wildcard
        validator = ScopeValidator("*.example.com", "www.example.com")
        self.assertFalse(validator.is_in_scope("www.example.com"))
        self.assertTrue(validator.is_in_scope("ftp.example.com"))

    def test_no_match(self):
        validator = ScopeValidator("example.com", "")
        self.assertFalse(validator.is_in_scope("google.com"))

    def test_empty_input_target(self):
        validator = ScopeValidator("*.example.com", "")
        self.assertFalse(validator.is_in_scope("   "))

if __name__ == '__main__':
    unittest.main()
