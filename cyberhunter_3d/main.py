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
    checklist.run_cleanup_and_optimization()

    # Generate reports
    reporter = Reporter(checklist.final_data)
    reporter.generate_pdf_report()
    reporter.generate_html_report()


if __name__ == "__main__":
    main()
