import unittest
import os
import json
from cyberhunter_3d.reporting.reporting import generate_delta_report

class TestReporting(unittest.TestCase):

    def setUp(self):
        """Set up a temporary directory for test output."""
        self.output_dir = "test_recon_results"
        os.makedirs(self.output_dir, exist_ok=True)

    def tearDown(self):
        """Clean up the temporary directory."""
        import shutil
        shutil.rmtree(self.output_dir)

    def test_generate_delta_report(self):
        """
        Test that the delta report is generated correctly.
        """
        # 1. Create mock delta files
        new_subs = ["new1.example.com", "new2.example.com"]
        removed_subs = ["old1.example.com"]

        new_subs_path = os.path.join(self.output_dir, "new_subdomains.json")
        removed_subs_path = os.path.join(self.output_dir, "removed_subdomains.json")

        with open(new_subs_path, 'w') as f:
            json.dump(new_subs, f)
        with open(removed_subs_path, 'w') as f:
            json.dump(removed_subs, f)

        delta_paths = {
            "new_subdomains": new_subs_path,
            "removed_subdomains": removed_subs_path
        }

        # 2. Generate the report
        generate_delta_report(self.output_dir, delta_paths)

        # 3. Assert the report was created and has the correct content
        report_path = os.path.join(self.output_dir, "delta_report.html")
        self.assertTrue(os.path.exists(report_path))

        with open(report_path, 'r') as f:
            content = f.read()
            self.assertIn("<h2>New Subdomains (2)</h2>", content)
            self.assertIn('<li class="added">new1.example.com</li>', content)
            self.assertIn("<h2>Removed Subdomains (1)</h2>", content)
            self.assertIn('<li class="removed">old1.example.com</li>', content)

if __name__ == '__main__':
    unittest.main()
