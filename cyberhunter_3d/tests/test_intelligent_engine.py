import unittest
import os
import yaml
from cyberhunter_3d.core.intelligent_engine import IntelligentEngine

class TestIntelligentEngine(unittest.TestCase):
    def setUp(self):
        self.test_findings = [
            {
                'id': 'finding-1', 'host': 'app.example.com', 'vulnerability_type': 'CWE-918',
                'severity': 'High', 'cve_list': [{'cve': {'metrics': {'cvssMetricV31': [{'cvssData': {'baseScore': 8.0}}]}}}],
                'open_ports': [80, 443], 'technologies': ['nginx', 'React'], 'is_internal_service': False,
                'vulnerability_name': 'SSRF'
            },
            {
                'id': 'finding-2', 'host': 'app.example.com', 'vulnerability_type': 'internal-service',
                'severity': 'Medium', 'cve_list': [],
                'open_ports': [8080], 'technologies': ['spring-boot'], 'is_internal_service': True,
                'vulnerability_name': 'Internal Service Exposed'
            },
            {
                'id': 'finding-3', 'host': 'web.example.com', 'vulnerability_name': 'apache-struts-rce',
                'severity': 'Critical', 'cve_list': [{'cve': {'metrics': {'cvssMetricV31': [{'cvssData': {'baseScore': 9.8}}]}}}],
                'open_ports': [80], 'technologies': ['IIS', 'ASP.NET']
            },
            {
                'id': 'finding-4', 'host': 'web.example.com', 'vulnerability_name': 'Anomalous Finding',
                'severity': 'Low', 'cve_list': [],
                'open_ports': [80, 443, 8080, 8443, 9000], 'technologies': ['nginx']
            }
        ]

        self.test_config_path = "cyberhunter_3d/config/exploit_chains.yaml"
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

        f1 = next(f for f in processed_findings if f['id'] == 'finding-1')
        self.assertEqual(f1['contextual_risk_score'], 9.0)

        f3 = next(f for f in processed_findings if f['id'] == 'finding-3')
        self.assertEqual(f3['contextual_risk_score'], 4.9)
        self.assertEqual(f3.get('validation_outcome'), False)

        f4 = next(f for f in processed_findings if f['id'] == 'finding-4')
        self.assertTrue(f4['is_anomaly'])

        self.assertListEqual([f['id'] for f in processed_findings], ['finding-1', 'finding-2', 'finding-3', 'finding-4'])

if __name__ == '__main__':
    unittest.main()
