import unittest
from unittest.mock import MagicMock
from cyberhunter_3d.core.triage_engine import TriageEngine
from cyberhunter_3d.core.plugins.context import ScanContext

class TestTriageEngine(unittest.TestCase):

    def setUp(self):
        self.context = ScanContext(target_domain="example.com", scan_id="test_scan")

    def test_correlation_of_leaked_key_and_vulnerable_api(self):
        # Arrange
        mock_js_secrets = {
            "http://example.com/main.js": [
                {"Raw": "var api_key = 'supersecretkey'"}
            ]
        }
        mock_api_vulns = {
            "example.com": [
                {"template-id": "CVE-2021-1234", "host": "example.com", "info": {"name": "Test API Vulnerability", "severity": "High"}}
            ]
        }
        specialized_results = {
            "js_secrets": mock_js_secrets,
            "api_vulnerabilities": mock_api_vulns
        }
        self.context.set("specialized_scan_results", specialized_results)

        engine = TriageEngine(self.context)

        # Act
        triaged_findings = engine.run()

        # Assert
        self.assertEqual(len(triaged_findings), 1)
        finding = triaged_findings[0]
        self.assertEqual(finding['severity'], "Critical")
        self.assertEqual(finding['title'], "Critical Risk: Leaked API Key for Vulnerable API")
        self.assertIn("Leaked API Key", finding['title'])

    def test_individual_findings_are_created(self):
        # Arrange
        mock_api_vulns = {
            "api.example.com": [
                {"template-id": "CVE-2022-5678", "host": "api.example.com", "info": {"name": "Another API Vuln", "severity": "Medium"}}
            ]
        }
        specialized_results = {
            "api_vulnerabilities": mock_api_vulns,
            "js_secrets": {} # No secrets to correlate
        }
        self.context.set("specialized_scan_results", specialized_results)

        engine = TriageEngine(self.context)

        # Act
        triaged_findings = engine.run()

        # Assert
        self.assertEqual(len(triaged_findings), 1)
        finding = triaged_findings[0]
        self.assertEqual(finding['severity'], "Medium")
        self.assertEqual(finding['title'], "API Vulnerability: Another API Vuln on api.example.com")

if __name__ == '__main__':
    unittest.main()
