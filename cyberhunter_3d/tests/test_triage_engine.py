import unittest
from unittest.mock import MagicMock
from cyberhunter_3d.core.triage_engine import TriageEngine
from cyberhunter_3d.core.plugins.context import ScanContext

class TestTriageEngine(unittest.TestCase):

    def setUp(self):
        self.context = MagicMock(spec=ScanContext)
        self.triage_engine = TriageEngine(self.context)

    def test_correlation_of_leaked_key_and_vulnerable_api(self):
        """
        Tests that a leaked API key is correctly correlated with a vulnerability
        on the same host, resulting in a single 'Critical' finding.
        """
        # 1. Setup: Mock the raw results in the context
        raw_results = {
            "js_secrets": {
                "http://api.example.com/main.js": [
                    {"Raw": "var access_key = 'some_secret_key'"}
                ]
            },
            "api_vulnerabilities": {
                "api.example.com": [
                    {
                        "template-id": "sql-injection",
                        "info": {
                            "name": "SQL Injection",
                            "severity": "high",
                            "description": "A SQL injection vulnerability."
                        },
                        "host": "api.example.com"
                    }
                ]
            }
        }
        self.context.get.return_value = raw_results

        # 2. Execute
        findings = self.triage_engine.run()

        # 3. Assertions
        self.assertEqual(len(findings), 1, "Should produce one correlated finding")

        finding = findings[0]
        self.assertEqual(finding['severity'], "Critical")
        self.assertEqual(finding['host'], "api.example.com")
        self.assertIn("Leaked API Key for Vulnerable API", finding['title'])
        self.assertIn("Correlation", finding['tags'])
        self.assertEqual(len(finding['raw_evidence']), 2, "Should contain evidence from both sources")

    def test_individual_findings_are_created(self):
        """
        Tests that raw results that do not match a correlation rule are
        turned into individual, deduplicated findings.
        """
        # 1. Setup: Mock raw results for two different vulnerabilities
        raw_results = {
            "api_vulnerabilities": {
                "api.example.com": [
                    {
                        "template-id": "xss",
                        "info": {"name": "Cross-Site Scripting", "severity": "medium"},
                        "host": "api.example.com"
                    }
                ]
            },
            "wordpress_scan": {
                "wp.example.com": [
                    {"vulnerability_type": "outdated_plugin", "plugin_name": "old-plugin"}
                ]
            }
        }
        # To test normalization, we need to add a normalizer for wpscan results.
        # Let's add it to the engine for this test.
        def normalize_wpscan(results):
            wp_vulns = results.get("wordpress_scan", {})
            for host, vulns in wp_vulns.items():
                for vuln in vulns:
                    self.triage_engine.normalized_findings.append({
                        "source": "wpscan",
                        "host": host,
                        "type": vuln["vulnerability_type"],
                        "details": vuln,
                        "confidence": self.triage_engine.CONFIDENCE_MAP.get("wpscan")
                    })

        original_normalize = self.triage_engine._normalize_results
        def side_effect(results):
            original_normalize(results)
            normalize_wpscan(results)

        self.triage_engine._normalize_results = MagicMock(side_effect=side_effect)

        self.context.get.return_value = raw_results

        # 2. Execute
        findings = self.triage_engine.run()

        # 3. Assertions
        self.assertEqual(len(findings), 2, "Should produce two individual findings")

        hosts = {f['host'] for f in findings}
        self.assertIn("api.example.com", hosts)
        self.assertIn("wp.example.com", hosts)

    def test_deduplication_of_similar_findings(self):
        """
        Tests that multiple raw results for the same type of vulnerability on the
        same host are deduplicated into a single TriagedFinding.
        """
        # 1. Setup: Mock multiple nuclei results for the same host and type
        raw_results = {
            "api_vulnerabilities": {
                "api.example.com": [
                    {
                        "template-id": "misconfig-1",
                        "info": {"name": "Security Misconfiguration", "severity": "low", "classification": {"cwe-id": "CWE-2"}},
                        "host": "api.example.com"
                    },
                    {
                        "template-id": "misconfig-2",
                        "info": {"name": "Another Security Misconfiguration", "severity": "low", "classification": {"cwe-id": "CWE-2"}},
                        "host": "api.example.com"
                    }
                ]
            }
        }
        self.context.get.return_value = raw_results

        # 2. Execute
        findings = self.triage_engine.run()

        # 3. Assertions
        self.assertEqual(len(findings), 1, "Should deduplicate similar findings")

        finding = findings[0]
        self.assertEqual(finding['host'], "api.example.com")
        self.assertEqual(finding['vulnerability_type'], "CWE-2")
        self.assertEqual(len(finding['raw_evidence']), 2, "Should contain evidence from both raw results")

if __name__ == '__main__':
    unittest.main()
