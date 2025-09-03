import unittest
from unittest.mock import patch, mock_open
import os
import shutil
import io
import sys

from cyberhunter_3d.core.code_conflict import Analyzer, Visualizer

class TestCodeConflict(unittest.TestCase):

    def setUp(self):
        self.test_dir = "test_code_conflict_temp"
        os.makedirs(self.test_dir, exist_ok=True)

        self.mock_vuln_db = {
            "django": [{
                "id": "PYSEC-2021-123",
                "affected": [{"ranges": [{"type": "ECOSYSTEM", "events": [{"introduced": "0"}, {"fixed": "2.2.17"}]}]}],
                "summary": "SQL injection in Django"
            }]
        }

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    @patch('cyberhunter_3d.core.code_conflict.analyzer.Analyzer._load_vulnerabilities')
    @patch('cyberhunter_3d.core.code_conflict.analyzer.Analyzer._find_requirements_files')
    def test_analyzer(self, mock_find_reqs, mock_load_vulns):
        # Setup mocks
        mock_load_vulns.return_value = self.mock_vuln_db
        dummy_req_path = os.path.join(self.test_dir, "requirements.txt")
        mock_find_reqs.return_value = [dummy_req_path]

        with open(dummy_req_path, "w") as f:
            f.write("django==2.0.0\n")

        # Run analyzer
        analyzer = Analyzer(self.test_dir)
        conflicts = analyzer.analyze()

        # Assertions
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]['dependency'], 'django')
        self.assertEqual(conflicts[0]['detected_version'], '2.0.0')

    @patch('os.makedirs')
    def test_visualizer_save_report(self, mock_makedirs):
        mock_conflicts = [{"type": "Vulnerable Dependency", "dependency": "django"}]
        visualizer = Visualizer(mock_conflicts)

        # Use mock_open to mock the file writing
        m = mock_open()
        with patch('builtins.open', m):
            report_path = visualizer.save_report(self.test_dir)

        # Check that a file was written to
        m.assert_called_once()
        # Check that the content written contains expected text
        handle = m()
        written_content = handle.write.call_args[0][0]
        self.assertIn("--- Code Conflict Report ---", written_content)
        self.assertIn("Dependency: django", written_content)

if __name__ == '__main__':
    unittest.main()
