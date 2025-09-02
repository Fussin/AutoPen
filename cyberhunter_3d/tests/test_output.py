import os
import json
import unittest
import zipfile
from unittest.mock import patch, mock_open
from cyberhunter_3d.output.file_handler import generate_output_files
from cyberhunter_3d.output.archive import create_archive
from cyberhunter_3d.output.integrations.slack import send_slack_notification
from cyberhunter_3d.output.integrations.jira import create_jira_issue

class TestOutputModule(unittest.TestCase):

    def setUp(self):
        self.results = {
            "hosts": [
                {"host": "test.com", "alive": True},
                {"host": "dead.com", "alive": False},
            ],
            "url_discovery": {
                "alive_urls": ["http://test.com/1"],
                "redirect_urls": ["http://test.com/2"],
            },
            "vulnerabilities": [
                {"name": "SQL Injection", "severity": "High"}
            ]
        }
        self.output_dir = "test_output"

    def tearDown(self):
        if os.path.exists(self.output_dir):
            for file in os.listdir(self.output_dir):
                os.remove(os.path.join(self.output_dir, file))
            os.rmdir(self.output_dir)

    @patch("os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    def test_generate_output_files(self, mock_file, mock_makedirs):
        generate_output_files(self.results, self.output_dir)

        mock_makedirs.assert_called_once_with(self.output_dir)

        # Check that the correct files were opened for writing
        expected_files = [
            os.path.join(self.output_dir, 'Subdomain.txt'),
            os.path.join(self.output_dir, 'alive_domain.txt'),
            os.path.join(self.output_dir, 'dead_domain.txt'),
            os.path.join(self.output_dir, 'Way_kat.txt'),
            os.path.join(self.output_dir, 'all_vulns.json'),
        ]

        opened_files = {call[0][0] for call in mock_file.call_args_list}
        self.assertEqual(set(expected_files), opened_files)

    @patch("zipfile.ZipFile")
    def test_create_archive(self, mock_zipfile):
        # Create a dummy file in the output directory
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        with open(os.path.join(self.output_dir, "test.txt"), "w") as f:
            f.write("test")

        archive_path = os.path.join(self.output_dir, "archive.zip")
        create_archive(self.output_dir, archive_path)

        mock_zipfile.assert_called_once_with(archive_path, 'w', zipfile.ZIP_DEFLATED)

    @patch("pyzipper.AESZipFile")
    def test_create_encrypted_archive(self, mock_zipfile):
        # Create a dummy file in the output directory
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        with open(os.path.join(self.output_dir, "test.txt"), "w") as f:
            f.write("test")

        archive_path = os.path.join(self.output_dir, "archive.zip")
        create_archive(self.output_dir, archive_path, "password")

        mock_zipfile.assert_called_once_with(archive_path, 'w', compression=unittest.mock.ANY, encryption=unittest.mock.ANY)

    @patch("requests.post")
    def test_send_slack_notification(self, mock_post):
        config = {"webhook_url": "http://fake.slack.webhook"}
        send_slack_notification("test message", config)
        mock_post.assert_called_once_with(config["webhook_url"], json={"text": "test message"})

    @patch("requests.post")
    def test_create_jira_issue(self, mock_post):
        config = {
            "url": "http://fake.jira.url",
            "user": "user",
            "token": "token",
            "project_key": "PROJ"
        }
        vuln = {"name": "test vuln", "description": "test desc"}
        create_jira_issue(vuln, config)
        mock_post.assert_called_once()


if __name__ == '__main__':
    unittest.main()
