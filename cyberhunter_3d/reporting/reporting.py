import json
import os

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

def generate_delta_report(output_dir: str, delta_paths: dict):
    """
    Generates a visual diff report for new and removed subdomains.
    """
    new_subdomains_path = delta_paths.get('new_subdomains')
    removed_subdomains_path = delta_paths.get('removed_subdomains')

    new_subdomains = []
    if new_subdomains_path and os.path.exists(new_subdomains_path):
        with open(new_subdomains_path, 'r') as f:
            new_subdomains = json.load(f)

    removed_subdomains = []
    if removed_subdomains_path and os.path.exists(removed_subdomains_path):
        with open(removed_subdomains_path, 'r') as f:
            removed_subdomains = json.load(f)

    html = f"""
    <html>
    <head>
        <title>CyberHunter 3D - Delta Report</title>
        <style>
            body {{ font-family: sans-serif; }}
            .added {{ color: green; }}
            .removed {{ color: red; }}
        </style>
    </head>
    <body>
        <h1>Delta Report</h1>
        <h2>New Subdomains ({len(new_subdomains)})</h2>
        <ul>
    """
    for sub in new_subdomains:
        html += f'<li class="added">{sub}</li>'

    html += f"""
        </ul>
        <h2>Removed Subdomains ({len(removed_subdomains)})</h2>
        <ul>
    """
    for sub in removed_subdomains:
        html += f'<li class="removed">{sub}</li>'

    html += """
        </ul>
    </body>
    </html>
    """

    report_path = os.path.join(output_dir, "delta_report.html")
    with open(report_path, 'w') as f:
        f.write(html)

    print(f"Delta report generated at {report_path}")
