import json
import os
from .engine import ReportEngine

def generate_3d_report(output_dir: str):
    """
    Generates a 3D report using the new report engine.
    """
    final_recon_path = os.path.join(output_dir, "final_recon_data.json")
    if not os.path.exists(final_recon_path):
        print(f"Error: final_recon_data.json not found in {output_dir}")
        return

    with open(final_recon_path, 'r') as f:
        data = json.load(f)

    engine = ReportEngine(data)
    engine.generate()
    engine.export(output_dir, formats=['json', 'html'])
    print(f"3D report generated in {output_dir}")


def generate_html_report(output_dir: str, report_path: str):
    """
    Generates a simple HTML report from the final_recon_data.json file.
    """
    final_recon_path = os.path.join(output_dir, "final_recon_data.json")
    if not os.path.exists(final_recon_path):
        print(f"Error: final_recon_data.json not found in {output_dir}")
        return

    with open(final_recon_path, 'r') as f:
        data = json.load(f)

    html = f"""
    <html>
    <head>
        <title>CyberHunter 3D - Reconnaissance Report for {data.get('domain')}</title>
        <style>
            body {{ font-family: sans-serif; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #dddddd; text-align: left; padding: 8px; }}
            th {{ background-color: #f2f2f2; }}
            .critical {{ color: red; font-weight: bold; }}
            .high {{ color: orange; }}
            .medium {{ color: yellow; }}
        </style>
    </head>
    <body>
        <h1>Reconnaissance Report for {data.get('domain')}</h1>
        <h2>Risk Summary</h2>
        <table>
            <tr>
                <th>Host</th>
                <th>Risk Level</th>
                <th>Highest CVSS Score</th>
                <th>Known Exploits</th>
                <th>CVEs</th>
            </tr>
    """

    # Sort hosts by CVSS score in descending order
    sorted_hosts = sorted(data.get('hosts', []), key=lambda x: x.get('cvss_score', 0.0), reverse=True)

    for host_data in sorted_hosts:
        risk_level = host_data.get('risk_level', 'None')
        html += f"""
            <tr>
                <td>{host_data.get('host')}</td>
                <td class="{risk_level.lower()}">{risk_level}</td>
                <td>{host_data.get('cvss_score', 0.0)}</td>
                <td>{'Yes' if host_data.get('known_exploits') else 'No'}</td>
                <td>{', '.join(host_data.get('cve_ids', []))}</td>
            </tr>
        """

    html += """
        </table>
    </body>
    </html>
    """

    with open(report_path, 'w') as f:
        f.write(html)

    print(f"HTML report generated at {report_path}")
