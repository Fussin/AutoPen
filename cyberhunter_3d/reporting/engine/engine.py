from .executive_dashboard import ExecutiveDashboard
from .technical_deep_dive import TechnicalDeepDive
from .compliance import Compliance
from .remediation import RemediationGuide
from .exporter import Exporter

class ReportEngine:
    """
    Orchestrates the generation of the 3D report.
    """
    def __init__(self, data):
        self.data = data
        self.report = {}

    def generate(self):
        """
        Generates the full report by calling each component.
        """
        self.report['executive_dashboard'] = ExecutiveDashboard(self.data).generate()
        self.report['technical_deep_dive'] = TechnicalDeepDive(self.data).generate()
        self.report['compliance'] = Compliance(self.data).generate()
        self.report['remediation_guide'] = RemediationGuide(self.data).generate()
        return self.report

    def export(self, output_dir, formats=['json', 'html']):
        """
        Exports the generated report to the specified formats.
        """
        exporter = Exporter(self.report)
        for fmt in formats:
            if fmt == 'json':
                exporter.to_json(f"{output_dir}/report.json")
            elif fmt == 'html':
                exporter.to_html(f"{output_dir}/report.html")
            elif fmt == 'pdf':
                exporter.to_pdf(f"{output_dir}/report.pdf")
