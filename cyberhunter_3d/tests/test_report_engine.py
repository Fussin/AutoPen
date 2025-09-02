import unittest
import os
import json
import shutil
from cyberhunter_3d.reporting.engine import ReportEngine

class TestReportEngine(unittest.TestCase):

    def setUp(self):
        self.test_dir = "test_output"
        os.makedirs(self.test_dir, exist_ok=True)
        self.recon_data = {
            "domain": "example.com",
            "vulnerabilities": [
                {"cve": "CVE-2023-1234", "severity": "High"},
                {"cve": "CVE-2023-5678", "severity": "Medium"}
            ]
        }
        self.recon_file = os.path.join(self.test_dir, "final_recon_data.json")
        with open(self.recon_file, 'w') as f:
            json.dump(self.recon_data, f)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_report_engine(self):
        # 1. Instantiate the ReportEngine
        engine = ReportEngine(self.recon_data)

        # 2. Run the generate method
        report = engine.generate()
        self.assertIn('executive_dashboard', report)
        self.assertEqual(report['executive_dashboard']['kpi_metrics']['total_vulnerabilities'], 2)
        self.assertEqual(report['executive_dashboard']['kpi_metrics']['high_vulnerabilities'], 1)
        self.assertIn('technical_deep_dive', report)
        self.assertEqual(len(report['technical_deep_dive']['vulnerabilities']), 2)
        self.assertIn('compliance', report)
        self.assertIn('CVE-2023-1234', report['compliance']['owasp_top_10'])
        self.assertIn('remediation_guide', report)
        self.assertIn('CVE-2023-5678', report['remediation_guide']['recommendations'])


        # 3. Run the export method
        engine.export(self.test_dir, formats=['json', 'html'])

        # 4. Assert that the output files are created
        json_report_path = os.path.join(self.test_dir, "report.json")
        html_report_path = os.path.join(self.test_dir, "report.html")
        self.assertTrue(os.path.exists(json_report_path))
        self.assertTrue(os.path.exists(html_report_path))

        # 5. Check the content of the exported files
        with open(json_report_path, 'r') as f:
            json_data = json.load(f)
            self.assertEqual(json_data['executive_dashboard']['kpi_metrics']['total_vulnerabilities'], 2)

        with open(html_report_path, 'r') as f:
            html_data = f.read()
            self.assertIn("<h1>3D Security Report</h1>", html_data)
            self.assertIn("CVE: CVE-2023-1234 (High)", html_data)


if __name__ == '__main__':
    unittest.main()
