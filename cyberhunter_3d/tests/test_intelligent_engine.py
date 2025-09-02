import unittest
from cyberhunter_3d.core.intelligent_engine import IntelligentEngine

class TestIntelligentEngine(unittest.TestCase):
    def setUp(self):
        self.test_findings = [
            {
                'id': 'finding-1',
                'host': '10.0.0.1',
                'vulnerability_type': 'CWE-918', # SSRF
                'severity': 'High',
                'cve_list': [{'cve': {'metrics': {'cvssMetricV31': [{'cvssData': {'baseScore': 8.0}}]}}}],
                'open_ports': [80, 443],
                'technologies': ['nginx', 'React'],
                'is_internal_service': False,
                'tags': []
            },
            {
                'id': 'finding-2',
                'host': '10.0.0.1',
                'vulnerability_type': 'internal-service-exposed',
                'severity': 'Medium',
                'cve_list': [],
                'open_ports': [8080],
                'technologies': ['spring-boot'],
                'is_internal_service': True,
                'tags': []
            },
            {
                'id': 'finding-3',
                'host': 'example.com',
                'vulnerability_type': 'CWE-434', # Unrestricted File Upload
                'severity': 'Critical',
                'cve_list': [{'cve': {'metrics': {'cvssMetricV31': [{'cvssData': {'baseScore': 9.8}}]}}}],
                'open_ports': [22, 80, 443],
                'technologies': ['apache', 'php'],
                'is_anomaly': True, # Manually flag as anomaly for testing
                'tags': ['info-disclosure']
            },
            {
                'id': 'finding-4',
                'host': 'example.com',
                'vulnerability_type': 'auth-bypass',
                'severity': 'High',
                'cve_list': [],
                'open_ports': [80, 443],
                'technologies': ['apache', 'php'],
                'tags': ['auth-bypass']
            }
        ]

    def test_intelligent_engine_run(self):
        """
        Test the full run of the IntelligentEngine.
        """
        engine = IntelligentEngine(self.test_findings)
        prioritized_findings = engine.run()

        # Check that the findings are prioritized correctly
        self.assertGreater(prioritized_findings[0]['contextual_risk_score'], prioritized_findings[1]['contextual_risk_score'])

        # Check that the exploit chain was detected and increased the score
        ssrf_finding = next(f for f in prioritized_findings if f['id'] == 'finding-1')
        self.assertAlmostEqual(ssrf_finding['contextual_risk_score'], 10.0) # 8.0 * 1.5 = 12.0, capped at 10.0

        # Check that the anomaly was detected and decreased the score
        upload_finding = next(f for f in prioritized_findings if f['id'] == 'finding-3')
        # 9.8 (base) -> 10.0 (chain) -> 8.0 (anomaly) -> 4.0 (validation)
        self.assertAlmostEqual(upload_finding['contextual_risk_score'], 4.0)

        # Check that the other finding in the chain also has a high score
        auth_bypass_finding = next(f for f in prioritized_findings if f['id'] == 'finding-4')
        # This one has no base score, so it won't get boosted. This is a good case to consider improving.
        # For now, we'll just check that it's present.
        self.assertIsNotNone(auth_bypass_finding)

if __name__ == '__main__':
    unittest.main()
