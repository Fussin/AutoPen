import json
import csv
from jinja2 import Environment, FileSystemLoader
import os
from weasyprint import HTML
from ..common.utils import LOG

class Reporter:
    """
    Handles the generation of different report formats.
    """

    def __init__(self, data):
        """
        Initializes the Reporter with the data to be reported.
        """
        self.data = data

    def generate_pdf_report(self, output_file="report.pdf"):
        """
        Generates a PDF report.
        """
        LOG.info("Generating PDF report...")
        try:
            html_content = self.generate_html_report(return_content=True)
            if html_content:
                HTML(string=html_content).write_pdf(output_file)
                LOG.info(f"PDF report generated at {output_file}")
        except Exception as e:
            LOG.error(f"Failed to generate PDF report: {e}")

    def generate_html_report(self, template_name="report_template.html", output_file="report.html", return_content=False):
        """
        Generates an HTML report from a template.
        """
        LOG.info("Generating HTML report...")
        try:
            template_dir = os.path.join(os.path.dirname(__file__), "templates")
            env = Environment(loader=FileSystemLoader(template_dir))
            template = env.get_template(template_name)
            html_content = template.render(data=self.data)
            if return_content:
                return html_content
            with open(output_file, 'w') as f:
                f.write(html_content)
            LOG.info(f"HTML report generated at {output_file}")
        except Exception as e:
            LOG.error(f"Failed to generate HTML report: {e}")
            return None

    def generate_json_export(self, output_file="report.json"):
        """
        Generates a raw JSON data export.
        """
        LOG.info("Generating JSON export...")
        try:
            with open(output_file, 'w') as f:
                json.dump(self.data, f, indent=4)
            LOG.info(f"JSON report generated at {output_file}")
        except Exception as e:
            LOG.error(f"Failed to generate JSON report: {e}")

    def generate_csv_summaries(self, output_file="report.csv"):
        """
        Generates CSV summaries.
        """
        LOG.info("Generating CSV summaries...")
        try:
            with open(output_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Subdomain"])
                for subdomain in self.data.get("subdomains", []):
                    writer.writerow([subdomain])
            LOG.info(f"CSV report generated at {output_file}")
        except Exception as e:
            LOG.error(f"Failed to generate CSV report: {e}")
