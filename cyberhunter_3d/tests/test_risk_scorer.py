import unittest
from cyberhunter_3d.core.scoring.risk_scorer import calculate_host_risk

class TestRiskScorer(unittest.TestCase):

    def test_no_risk(self):
        """Test a host with no identifiable risks."""
        host_data = {
            "host": "safe.example.com",
            "cves": [],
            "open_ports": [80, 443],
            "technologies": ["nginx"],
            "takeover_risk": False,
            "screenshot_tags": ["homepage"]
        }
        risk_info = calculate_host_risk(host_data)
        self.assertEqual(risk_info["risk_level"], "None")
        self.assertEqual(risk_info["total_risk_score"], 0)

    def test_critical_cve_risk(self):
        """Test risk calculation for a host with a critical CVE."""
        host_data = {
            "host": "vuln.example.com",
            "cves": [
                {"cve": {"id": "CVE-2022-12345", "metrics": {"cvssMetricV31": [{"cvssData": {"baseScore": 9.8}}]}}}
            ],
            "open_ports": [443],
            "technologies": ["apache"],
        }
        risk_info = calculate_host_risk(host_data)
        self.assertEqual(risk_info["risk_level"], "Medium") # 10 from CVE
        self.assertGreater(risk_info["total_risk_score"], 0)

    def test_known_exploit_risk(self):
        """Test risk calculation for a CVE in CISA's KEV catalog."""
        host_data = {
            "host": "exploited.example.com",
            "cves": [
                {"cve": {"id": "CVE-2021-44228", "cisaExploitAdd": "2021-12-15", "metrics": {"cvssMetricV31": [{"cvssData": {"baseScore": 10.0}}]}}}
            ],
        }
        risk_info = calculate_host_risk(host_data)
        self.assertEqual(risk_info["risk_level"], "High") # 10 (Critical) + 15 (KEV) = 25
        self.assertEqual(risk_info["total_risk_score"], 25)

    def test_takeover_risk(self):
        """Test risk calculation for a host with takeover risk."""
        host_data = {
            "host": "takeover.example.com",
            "takeover_risk": True,
        }
        risk_info = calculate_host_risk(host_data)
        self.assertEqual(risk_info["risk_level"], "Medium") # 20 from takeover
        self.assertEqual(risk_info["total_risk_score"], 20)

    def test_high_risk_port(self):
        """Test risk calculation for a host with a high-risk open port."""
        host_data = {
            "host": "db.example.com",
            "open_ports": [5432], # PostgreSQL
        }
        risk_info = calculate_host_risk(host_data)
        self.assertEqual(risk_info["risk_level"], "Low")
        self.assertEqual(risk_info["total_risk_score"], 3) # 3 from high-risk port

    def test_login_page_risk(self):
        """Test risk calculation for a host with a login page."""
        host_data = {
            "host": "login.example.com",
            "screenshot_tags": ["login", "form"],
        }
        risk_info = calculate_host_risk(host_data)
        self.assertEqual(risk_info["risk_level"], "Low")
        self.assertEqual(risk_info["total_risk_score"], 5) # 5 from login page

    def test_risk_cluster(self):
        """Test the risk clustering bonus for a critical CVE on a login page."""
        host_data = {
            "host": "admin.example.com",
            "cves": [
                {"cve": {"id": "CVE-2022-CRITICAL", "metrics": {"cvssMetricV31": [{"cvssData": {"baseScore": 9.0}}]}}}
            ],
            "screenshot_tags": ["admin", "dashboard"],
        }
        risk_info = calculate_host_risk(host_data)
        # 10 (Critical CVE) + 8 (Admin Panel) + 10 (Cluster Bonus) = 28
        self.assertEqual(risk_info["risk_level"], "High")
        self.assertEqual(risk_info["total_risk_score"], 28)
        self.assertTrue(any(f['factor'] == 'Risk Cluster' for f in risk_info['contributing_factors']))

    def test_full_scenario(self):
        """Test a complex scenario with multiple risk factors."""
        host_data = {
            "host": "very-risky.example.com",
            "cves": [
                {"cve": {"id": "CVE-2022-HIGH", "metrics": {"cvssMetricV31": [{"cvssData": {"baseScore": 8.0}}]}}}
            ],
            "open_ports": [22, 6379], # Critical + High-risk
            "takeover_risk": False,
            "screenshot_tags": ["login"],
            "cloud_asset": True
        }
        # 7 (High CVE) + 5 (Crit Port) + 3 (High Port) + 5 (Login) + 2 (Cloud) = 22
        risk_info = calculate_host_risk(host_data)
        self.assertEqual(risk_info["risk_level"], "Medium")
        self.assertEqual(risk_info["total_risk_score"], 22)

if __name__ == '__main__':
    unittest.main()
