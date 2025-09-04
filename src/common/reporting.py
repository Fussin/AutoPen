import json
from typing import List, Dict

def generate_html_report(findings: List[Dict], output_file: str):
    """
    Generates an HTML report from a list of findings.
    """
    html = """
    <html>
    <head>
        <title>Security Scan Report</title>
        <style>
            body { font-family: sans-serif; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #dddddd; text-align: left; padding: 8px; }
            tr:nth-child(even) { background-color: #f2f2f2; }
            .severity-high { color: red; font-weight: bold; }
            .severity-medium { color: orange; }
            .severity-low { color: #5d5d5d; }
            .severity-info { color: blue; }
        </style>
    </head>
    <body>
        <h1>Security Scan Report</h1>
        <table>
            <tr>
                <th>Target</th>
                <th>Tool</th>
                <th>Vulnerability</th>
                <th>Severity</th>
                <th>Evidence</th>
            </tr>
    """

    for finding in findings:
        vuln = finding.get("vuln", {})
        evidence = finding.get("evidence", {})
        html += f"""
            <tr>
                <td>{finding.get("target")}</td>
                <td>{finding.get("tool")}</td>
                <td>{vuln.get("name")}</td>
                <td class="severity-{vuln.get("severity", "info")}">{vuln.get("severity", "info")}</td>
                <td><pre>{json.dumps(evidence, indent=2)}</pre></td>
            </tr>
        """

    html += """
        </table>
    </body>
    </html>
    """

    with open(output_file, "w") as f:
        f.write(html)

    print(f"HTML report generated at {output_file}")

if __name__ == "__main__":
    # Example usage
    sample_findings = [
        {
            "target": "http://example.com",
            "tool": "nuclei",
            "vuln": {"name": "Exposed Panel", "severity": "high"},
            "evidence": {"poc": "http://example.com/admin"}
        },
        {
            "target": "example.com",
            "tool": "subfinder",
            "vuln": {"name": "Subdomain Discovered", "severity": "info"},
            "evidence": {"poc": "test.example.com"}
        }
    ]
    generate_html_report(sample_findings, "reports/report.html")
