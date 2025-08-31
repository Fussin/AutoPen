import unittest
import os
import json
from unittest.mock import patch, MagicMock
from cyberhunter_3d.reporting.pdf_generator import generate_pdf_report
from run_web import app, db
from cyberhunter_3d.web.models import User, Scan, Target

class TestReporting(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        self.app = app.test_client()
        with app.app_context():
            db.create_all()
            user = User(username='testuser', password_hash='password', otp_secret='secret')
            db.session.add(user)
            db.session.commit()
            self.user_id = user.id

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    @patch('cyberhunter_3d.reporting.pdf_generator.pdfkit.from_string')
    def test_generate_pdf_report(self, mock_pdfkit):

        def create_dummy_pdf(html, path):
            with open(path, "w") as f:
                f.write("dummy pdf content")

        mock_pdfkit.side_effect = create_dummy_pdf

        with app.app_context():
            # Create a scan
            scan = Scan(user_id=self.user_id)
            target = Target(value='example.com', type='domain', scan_id=scan.id)
            scan.targets.append(target)
            db.session.add(scan)
            db.session.commit()
            scan_id = scan.id

            # Create a mock results directory and report file
            from cyberhunter_3d.utils.file_utils import get_results_dir
            from cyberhunter_3d.core.reconnaissance.utils import load_config
            config = load_config()
            results_dir = get_results_dir('example.com', scan_id)
            os.makedirs(results_dir, exist_ok=True)

            mock_report_data = {"domain": "example.com"}
            report_path = os.path.join(results_dir, config['final_recon_file'])
            with open(report_path, 'w') as f:
                json.dump(mock_report_data, f)

            # Run the PDF generator
            pdf_path = generate_pdf_report(scan_id, 'example.com', app)

            # Assertions
            mock_pdfkit.assert_called_once()
            self.assertIsNotNone(pdf_path)
            self.assertTrue(os.path.exists(pdf_path))

            # Clean up
            os.remove(report_path)
            os.remove(pdf_path)
            os.rmdir(results_dir)

if __name__ == '__main__':
    unittest.main()
