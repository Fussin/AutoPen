import unittest
from unittest.mock import patch
import os
import shutil
import io
import sys

from cyberhunter_3d.core.code_conflict import Analyzer, Visualizer

class TestCodeConflict(unittest.TestCase):

    def setUp(self):
        self.test_dir = "test_code_conflict_temp"
        os.makedirs(self.test_dir, exist_ok=True)
        with open(os.path.join(self.test_dir, "requirements.txt"), "w") as f:
            f.write("requests==2.24.0\n")   # Vulnerable in our mock db
            f.write("django<2.0\n")         # Vulnerable in our mock db
            f.write("requests>=2.25.0\n")  # Safe
            f.write("numpy\n")              # Not in our mock db

        self.mock_vuln_db = {
            "django": {"affected_versions": "<2.2.17", "severity": "High", "description": "..."},
            "requests": {"affected_versions": "<2.25.0", "severity": "Medium", "description": "..."}
        }

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    @patch('cyberhunter_3d.core.code_conflict.analyzer.Analyzer._load_vulnerabilities')
    def test_analyzer_finds_vulnerable_packages(self, mock_load_vulns):
        mock_load_vulns.return_value = self.mock_vuln_db

        analyzer = Analyzer(self.test_dir)
        conflicts = analyzer.analyze()

        self.assertEqual(len(conflicts), 2)

        requests_conflict = next((c for c in conflicts if c['dependency'] == 'requests'), None)
        self.assertIsNotNone(requests_conflict)
        self.assertEqual(requests_conflict['detected_version'], "2.24.0")

        django_conflict = next((c for c in conflicts if c['dependency'] == 'django'), None)
        self.assertIsNotNone(django_conflict)
        self.assertEqual(django_conflict['detected_version'], "2.0")

    def test_visualizer_displays_correctly(self):
        mock_conflicts = [
            {
                "type": "Vulnerable Dependency",
                "dependency": "requests",
                "detected_version": "2.24.0",
                "affected_versions": "<2.25.0",
            }
        ]
        visualizer = Visualizer(mock_conflicts)

        captured_output = io.StringIO()
        sys.stdout = captured_output
        visualizer.visualize()
        sys.stdout = sys.__stdout__

        output = captured_output.getvalue()
        self.assertIn("Detected Version: 2.24.0", output)
        self.assertIn("Affected Versions: <2.25.0", output)

if __name__ == '__main__':
    unittest.main()
