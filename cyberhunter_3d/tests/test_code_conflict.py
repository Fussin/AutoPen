import unittest
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
            f.write("requests==2.24.0\n")   # Vulnerable
            f.write("django<2.0\n")         # Vulnerable
            f.write("requests>=2.25.0\n")  # Safe
            f.write("numpy\n")              # Not in our DB

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_analyzer_finds_vulnerable_packages(self):
        analyzer = Analyzer(self.test_dir)
        conflicts = analyzer.analyze()

        self.assertEqual(len(conflicts), 2)

        # Check the first conflict (requests)
        requests_conflict = next((c for c in conflicts if c['dependency'] == 'requests'), None)
        self.assertIsNotNone(requests_conflict)
        self.assertEqual(requests_conflict['detected_version'], "2.24.0")

        # Check the second conflict (django)
        django_conflict = next((c for c in conflicts if c['dependency'] == 'django'), None)
        self.assertIsNotNone(django_conflict)
        self.assertEqual(django_conflict['detected_version'], "2.0")

    def test_visualizer_displays_correctly(self):
        mock_conflicts = [
            {
                "type": "Vulnerable Dependency",
                "file": "requirements.txt",
                "dependency": "requests",
                "detected_version": "2.24.0",
                "affected_versions": "<2.25.0",
                "severity": "Medium",
                "description": "Requests versions before 2.25.0 are vulnerable to a CRLF injection."
            }
        ]
        visualizer = Visualizer(mock_conflicts)

        captured_output = io.StringIO()
        sys.stdout = captured_output

        visualizer.visualize()

        sys.stdout = sys.__stdout__

        output = captured_output.getvalue()
        self.assertIn("--- Code Conflict Report ---", output)
        self.assertIn("Dependency: requests", output)
        self.assertIn("Detected Version: 2.24.0", output)
        self.assertIn("Affected Versions: <2.25.0", output)

if __name__ == '__main__':
    unittest.main()
