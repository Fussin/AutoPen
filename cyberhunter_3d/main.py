import argparse
import json
from .core.reconnaissance.passive_engine import run_passive_enumeration
from .reporting.exit_checklist import ExitChecklist
from .reporting.reporter import Reporter

def main():
    parser = argparse.ArgumentParser(description="CyberHunter 3D - Minimal Refactoring Demo")
    parser.add_argument("domain", help="The root domain to target.")
    args = parser.parse_args()

    print(f"Running passive enumeration for {args.domain}...")
    subdomains = run_passive_enumeration(args.domain)
    print(f"Found {len(subdomains)} subdomains:")
    for sub in sorted(list(subdomains)):
        print(sub)

    # Save results to a file
    results_file = "final_recon_data.json"
    with open(results_file, 'w') as f:
        json.dump({"subdomains": list(subdomains)}, f)

    # Run the exit checklist
    checklist = ExitChecklist(results_file)
    checklist.run_data_finalization()

    # Generate reports
    reporter = Reporter(checklist.final_data)
    report_files = []

    pdf_file = "report.pdf"
    reporter.generate_pdf_report(output_file=pdf_file)
    report_files.append(pdf_file)

    html_file = "report.html"
    reporter.generate_html_report(output_file=html_file)
    report_files.append(html_file)

    json_file = "report.json"
    reporter.generate_json_export(output_file=json_file)
    report_files.append(json_file)

    csv_file = "report.csv"
    reporter.generate_csv_summaries(output_file=csv_file)
    report_files.append(csv_file)

    # Run post-reporting checklist items
    checklist.run_quality_assurance(html_report_file=html_file)
    checklist.run_distribution()

    # Final cleanup
    checklist.run_cleanup_and_optimization(report_files=report_files)


if __name__ == "__main__":
    main()
