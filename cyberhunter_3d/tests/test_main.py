import os
import unittest
from unittest.mock import patch
from cyberhunter_3d import main

class TestMain(unittest.TestCase):

    @patch('cyberhunter_3d.main.run_passive_enumeration')
    def test_main_workflow_and_cleanup(self, mock_run_passive_enumeration):
        """
        Test the main workflow and that temporary files are cleaned up.
        """
        # Mock the passive enumeration to return some subdomains
        mock_run_passive_enumeration.return_value = {"a.test.com", "b.test.com"}

        # Define the files that should be created and then deleted
        results_file = "final_recon_data.json"
        report_files = ["report.pdf", "report.html", "report.json", "report.csv"]
        archive_files = [results_file + ".tar.gz", results_file + ".sha256"]
        all_temp_files = [results_file] + report_files + archive_files
        stats_file = "scan_statistics.txt"

        # Ensure files don't exist before the run
        for f in all_temp_files + [stats_file]:
            if os.path.exists(f):
                os.remove(f)

        # Run the main function with a dummy domain
        with patch('sys.argv', ['main.py', 'example.com']):
            main.main()

        # After the run, check that all temporary files have been deleted
        for f in all_temp_files:
            self.assertFalse(os.path.exists(f), f"File {f} was not cleaned up.")

        # And check that the statistics file exists
        self.assertTrue(os.path.exists(stats_file), "Statistics file was not created.")
        os.remove(stats_file) # clean up after the test

if __name__ == '__main__':
    unittest.main()
