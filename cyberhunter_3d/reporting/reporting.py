import json
import os
from typing import Dict

def generate_html_report(recon_results_dir: str, output_file: str):
    """
    Generates a static HTML report from the JSON output files.
    """
    html = """
    <html>
    <head>
        <title>CyberHunter 3D Reconnaissance Report</title>
        <style>
            body { font-family: sans-serif; margin: 2em; }
            h1, h2 { color: #333; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; }
        </style>
    </head>
    <body>
        <h1>CyberHunter 3D Reconnaissance Report</h1>
    """

    # Summary Section
    summary_data = {}
    for filename in os.listdir(recon_results_dir):
        if filename.endswith(".json"):
            try:
                with open(os.path.join(recon_results_dir, filename), 'r') as f:
                    data = json.load(f)
                    summary_data[filename.replace(".json", "")] = len(data)
            except (json.JSONDecodeError, TypeError):
                summary_data[filename.replace(".json", "")] = "N/A"

    html += "<h2>Summary</h2><table>"
    for key, value in summary_data.items():
        html += f"<tr><td>{key.replace('_', ' ').title()}</td><td>{value}</td></tr>"
    html += "</table>"

    # Detailed Sections
    for filename in os.listdir(recon_results_dir):
        if filename.endswith(".json"):
            html += f"<h2>{filename.replace('_', ' ').title()}</h2>"
            try:
                with open(os.path.join(recon_results_dir, filename), 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list) and data:
                        html += "<table>"
                        headers = data[0].keys() if isinstance(data[0], dict) else [filename.replace('.json', '')]
                        html += "<tr>"
                        for header in headers:
                            html += f"<th>{header}</th>"
                        html += "</tr>"
                        for item in data:
                            html += "<tr>"
                            if isinstance(item, dict):
                                for header in headers:
                                    html += f"<td>{item.get(header, '')}</td>"
                            else:
                                html += f"<td>{item}</td>"
                            html += "</tr>"
                        html += "</table>"
                    elif isinstance(data, dict) and data:
                        html += "<table>"
                        for key, value in data.items():
                            html += f"<tr><td>{key}</td><td>{json.dumps(value, indent=4)}</td></tr>"
                        html += "</table>"
                    else:
                        html += "<p>No data found.</p>"

            except (json.JSONDecodeError, TypeError):
                html += "<p>Could not read or parse JSON file.</p>"

    html += """
    </body>
    </html>
    """

    with open(output_file, 'w') as f:
        f.write(html)
