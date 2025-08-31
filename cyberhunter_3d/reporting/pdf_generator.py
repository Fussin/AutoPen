import pdfkit
import os
import json
from datetime import datetime
from flask import render_template
from ..core.reconnaissance.utils import load_config
from ..utils.file_utils import get_results_dir

def generate_pdf_report(scan_id, domain, app):
    """
    Generates a PDF report for a given scan.
    """
    config = load_config()
    results_dir = get_results_dir(domain, scan_id)
    final_report_path = os.path.join(results_dir, config['final_recon_file'])
    pdf_report_path = os.path.join(results_dir, f"scan_report_{scan_id}.pdf")

    if not os.path.exists(final_report_path):
        print(f"Final report for scan {scan_id} not found. Cannot generate PDF.")
        return None

    with open(final_report_path, 'r') as f:
        try:
            report_data = json.load(f)
        except json.JSONDecodeError:
            print(f"Error decoding final report for scan {scan_id}.")
            return None

    report_context = {
        "domain": domain,
        "scan_id": scan_id,
        "report_date": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
        "vulnerabilities": report_data.get("vulnerabilities", []),
        "content_discovery": report_data.get("content_discovery", {}),
        "js_analysis": report_data.get("js_analysis", {}),
    }

    with app.app_context():
        html = render_template('report_template.html', **report_context)

    try:
        pdfkit.from_string(html, pdf_report_path)
        print(f"PDF report generated successfully: {pdf_report_path}")
        return pdf_report_path
    except Exception as e:
        print(f"Error generating PDF report: {e}")
        return None
