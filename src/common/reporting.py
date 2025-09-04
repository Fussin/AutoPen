import json
import csv
from typing import List, Dict
from fpdf import FPDF

def generate_html_report(findings: List[Dict], output_file: str):
    """
    Generates an HTML report from a list of findings with sorting and filtering.
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
            th { cursor: pointer; }
            .severity-high { color: red; font-weight: bold; }
            .severity-medium { color: orange; }
            .severity-low { color: #5d5d5d; }
            .severity-info { color: blue; }
        </style>
    </head>
    <body>
        <h1>Security Scan Report</h1>
        <input type="text" id="filterInput" onkeyup="filterTable()" placeholder="Filter results...">
        <table id="findingsTable">
            <thead>
                <tr>
                    <th onclick="sortTable(0)">Risk Score</th>
                    <th onclick="sortTable(1)">Target</th>
                    <th onclick="sortTable(2)">Tool</th>
                    <th onclick="sortTable(3)">Vulnerability</th>
                    <th onclick="sortTable(4)">Severity</th>
                    <th onclick="sortTable(5)">Evidence</th>
                </tr>
            </thead>
            <tbody>
    """

    for finding in findings:
        vuln = finding.get("vuln", {})
        evidence = finding.get("evidence", {})
        html += f"""
            <tr>
                <td>{finding.get("risk_score", "N/A")}</td>
                <td>{finding.get("target")}</td>
                <td>{finding.get("tool")}</td>
                <td>{vuln.get("name")}</td>
                <td class="severity-{vuln.get("severity", "info")}">{vuln.get("severity", "info")}</td>
                <td><pre>{json.dumps(evidence, indent=2)}</pre></td>
            </tr>
        """

    html += """
            </tbody>
        </table>
        <script>
            function sortTable(n) {
                var table, rows, switching, i, x, y, shouldSwitch, dir, switchcount = 0;
                table = document.getElementById("findingsTable");
                switching = true;
                dir = "asc";
                while (switching) {
                    switching = false;
                    rows = table.rows;
                    for (i = 1; i < (rows.length - 1); i++) {
                        shouldSwitch = false;
                        x = rows[i].getElementsByTagName("TD")[n];
                        y = rows[i + 1].getElementsByTagName("TD")[n];
                        if (dir == "asc") {
                            if (isNaN(parseFloat(x.innerHTML)) || isNaN(parseFloat(y.innerHTML))) {
                                if (x.innerHTML.toLowerCase() > y.innerHTML.toLowerCase()) {
                                    shouldSwitch = true;
                                    break;
                                }
                            } else {
                                if (parseFloat(x.innerHTML) > parseFloat(y.innerHTML)) {
                                    shouldSwitch = true;
                                    break;
                                }
                            }
                        } else if (dir == "desc") {
                            if (isNaN(parseFloat(x.innerHTML)) || isNaN(parseFloat(y.innerHTML))) {
                                if (x.innerHTML.toLowerCase() < y.innerHTML.toLowerCase()) {
                                    shouldSwitch = true;
                                    break;
                                }
                            } else {
                                if (parseFloat(x.innerHTML) < parseFloat(y.innerHTML)) {
                                    shouldSwitch = true;
                                    break;
                                }
                            }
                        }
                    }
                    if (shouldSwitch) {
                        rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
                        switching = true;
                        switchcount++;
                    } else {
                        if (switchcount == 0 && dir == "asc") {
                            dir = "desc";
                            switching = true;
                        }
                    }
                }
            }

            function filterTable() {
                var input, filter, table, tr, td, i, txtValue;
                input = document.getElementById("filterInput");
                filter = input.value.toUpperCase();
                table = document.getElementById("findingsTable");
                tr = table.getElementsByTagName("tr");
                for (i = 1; i < tr.length; i++) {
                    td = tr[i].getElementsByTagName("td");
                    let rowVisible = false;
                    for (let j = 0; j < td.length; j++) {
                        if (td[j]) {
                            txtValue = td[j].textContent || td[j].innerText;
                            if (txtValue.toUpperCase().indexOf(filter) > -1) {
                                rowVisible = true;
                                break;
                            }
                        }
                    }
                    if (rowVisible) {
                        tr[i].style.display = "";
                    } else {
                        tr[i].style.display = "none";
                    }
                }
            }
        </script>
    </body>
    </html>
    """

    with open(output_file, "w") as f:
        f.write(html)

    print(f"HTML report generated at {output_file}")

def generate_csv_report(findings: List[Dict], output_file: str):
    """
    Generates a CSV report from a list of findings.
    """
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Risk Score", "Target", "Tool", "Vulnerability", "Severity", "Evidence"])

        for finding in findings:
            vuln = finding.get("vuln", {})
            evidence = finding.get("evidence", {})
            writer.writerow([
                finding.get("risk_score", "N/A"),
                finding.get("target"),
                finding.get("tool"),
                vuln.get("name"),
                vuln.get("severity"),
                json.dumps(evidence)
            ])
    print(f"CSV report generated at {output_file}")

def generate_pdf_report(findings: List[Dict], output_file: str):
    """
    Generates a PDF report from a list of findings.
    """
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt="Security Scan Report", ln=1, align="C")

    for finding in findings:
        pdf.ln(10)
        pdf.multi_cell(0, 10, f"Risk Score: {finding.get('risk_score', 'N/A')}")
        pdf.multi_cell(0, 10, f"Target: {finding.get('target')}")
        pdf.multi_cell(0, 10, f"Tool: {finding.get('tool')}")
        vuln = finding.get("vuln", {})
        pdf.multi_cell(0, 10, f"Vulnerability: {vuln.get('name')}")
        pdf.multi_cell(0, 10, f"Severity: {vuln.get('severity')}")
        evidence = finding.get("evidence", {})
        pdf.multi_cell(0, 10, f"Evidence: {json.dumps(evidence, indent=2)}")

    pdf.output(output_file)
    print(f"PDF report generated at {output_file}")

def generate_reports(findings: List[Dict], output_dir: str):
    """
    Generates all reports (HTML, CSV, PDF), sorted by risk score.
    """
    sorted_findings = sorted(findings, key=lambda x: x.get("risk_score", 0), reverse=True)

    generate_html_report(sorted_findings, f"{output_dir}/report.html")
    generate_csv_report(sorted_findings, f"{output_dir}/report.csv")
    generate_pdf_report(sorted_findings, f"{output_dir}/report.pdf")

if __name__ == "__main__":
    sample_findings = [
        {
            "target": "http://example.com",
            "tool": "nuclei",
            "vuln": {"name": "Exposed Panel", "severity": "high"},
            "evidence": {"poc": "http://example.com/admin"},
            "risk_score": 0.95
        },
        {
            "target": "example.com",
            "tool": "subfinder",
            "vuln": {"name": "Subdomain Discovered", "severity": "info"},
            "evidence": {"poc": "test.example.com"},
            "risk_score": 0.1
        }
    ]
    generate_reports(sample_findings, "reports")
