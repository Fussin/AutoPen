import os
from jinja2 import Environment, FileSystemLoader
from typing import Dict, Any

from ...common.log import get_rich_logger as get_logger

logger = get_logger(__name__)

def generate_html_report(data: Dict[str, Any], output_dir: str):
    """
    Generates an HTML report from the reconnaissance data.

    Args:
        data: The final reconnaissance data.
        output_dir: The directory to save the report to.
    """
    logger.info("Generating HTML report...")

    try:
        # Assuming the templates are in cyberhunter_3d/reporting/templates
        template_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'reporting', 'templates')
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template('report.html')

        report_path = os.path.join(output_dir, 'report.html')

        with open(report_path, 'w') as f:
            f.write(template.render(data=data))

        logger.info(f"HTML report saved to: {report_path}")

    except Exception as e:
        logger.error(f"Failed to generate HTML report: {e}")
