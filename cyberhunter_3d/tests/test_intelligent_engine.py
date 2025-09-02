import unittest
import os
import yaml
from cyberhunter_3d.core.intelligent_engine import IntelligentEngine

class TestIntelligentEngine(unittest.TestCase):
    def setUp(self):
        # More comprehensive test data
        self.test_findings = [
            {
                'id': 'finding-1', 'host': 'app.example.com', 'vulnerability_type': 'CWE-918', # SSRF
                'severity': 'High', 'cve_list': [{'cve': {'metrics': {'cvssMetricV31': [{'cvssData': {'baseScore': 8.0}}]}}}],
                'open_ports': [80, 443], 'technologies': ['nginx', 'React'], 'is_internal_service': False
            },
            {
                'id': 'finding-2', 'host': 'app.example.com', 'vulnerability_type': 'internal-service',
                'severity': 'Medium', 'cve_list': [],
                'open_ports': [8080], 'technologies': ['spring-boot'], 'is_internal_service': True
            },
            {
                'id': 'finding-3', 'host': 'web.example.com', 'vulnerability_name': 'apache-struts-rce',
                'severity': 'Critical', 'cve_list': [{'cve': {'metrics': {'cvssMetricV31': [{'cvssData': {'baseScore': 9.8}}]}}}],
                'open_ports': [80], 'technologies': ['IIS', 'ASP.NET'] # Mismatch, should be flagged
            },
            {
                'id': 'finding-4', 'host': 'web.example.com',
                'severity': 'Low', 'cve_list': [],
                'open_ports': [80, 443, 8080, 8443, 9000], # Anomalous port count
                'technologies': ['nginx']
            }
        ]

        # The engine uses the default config path, so we need to mock that
        self.test_config_path = "cyberhunter_3d/config/exploit_chains.yaml"
        # Ensure the directory exists
        os.makedirs(os.path.dirname(self.test_config_path), exist_ok=True)

        self.test_config = {
            "chains": [{
                "name": "SSRF to Internal Service Exposure", "risk_implication": "High",
                "steps": [
                    {"conditions": [{"type": "cwe", "value": "CWE-918"}]},
                    {"conditions": [{"type": "property", "key": "is_internal_service", "value": True}]}
                ]
            }]
        }
        with open(self.test_config_path, 'w') as f:
            yaml.dump(self.test_config, f)

    def tearDown(self):
        if os.path.exists(self.test_config_path):
            os.remove(self.test_config_path)

    def test_intelligent_engine_full_run(self):
        """Test the full run of the IntelligentEngine with the new logic."""
        engine = IntelligentEngine(self.test_findings)
        processed_findings = engine.run()

        # Finding 1 (SSRF) should have its score elevated by the chain
        f1 = next(f for f in processed_findings if f['id'] == 'finding-1')
        # Chain score = max(8.0, 0.0) + 1.0 = 9.0
        self.assertEqual(f1['contextual_risk_score'], 9.0)

        # Finding 2 (Internal Service) should also have its score elevated
        f2 = next(f for f in processed_findings if f['id'] == 'finding-2')
        self.assertEqual(f2['contextual_risk_score'], 9.0)

        # Finding 3 (Struts RCE) should be flagged as a false positive
        f3 = next(f for f in processed_findings if f['id'] == 'finding-3')
        # Base score is 9.8, but validation fails, so score is halved.
        self.assertEqual(f3['contextual_risk_score'], 4.9)
        self.assertEqual(f3.get('validation_outcome'), False)

        # Finding 4 should be flagged as an anomaly by Isolation Forest
        f4 = next(f for f in processed_findings if f['id'] == 'finding-4')
        self.assertTrue(f4['is_anomaly'])
        # Base score is 0.0, anomaly adjustment makes it 0.0 * 0.8 = 0.0
        self.assertEqual(f4['contextual_risk_score'], 0.0)

        # Test prioritization
        self.assertListEqual([f['id'] for f in processed_findings], ['finding-1', 'finding-2', 'finding-3', 'finding-4'])

if __name__ == '__main__':
    unittest.main()
