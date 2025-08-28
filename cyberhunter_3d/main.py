import argparse
import sys
import os
import sys
from core.reconnaissance.subdomain_enum import enumerate_subdomains_v2
from core.reconnaissance.utils import load_config

def main():
    """
    Main function to run the CyberHunter 3D reconnaissance V2 pipeline.
    """
    print("Welcome to CyberHunter 3D - Reconnaissance Module (V2)")

    parser = argparse.ArgumentParser(description="A futuristic bug bounty automation platform.")
    parser.add_argument("-d", "--domain", required=True, help="The target domain to perform reconnaissance on.")
    parser.add_argument("--save-to-db", action="store_true", help="Save the scan results to the database.")
    parser.add_argument("--previous-scan-dir", help="Path to the previous scan's output directory for delta detection.")

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()
    target_domain = args.domain

    print(f"Starting V2 reconnaissance pipeline for {target_domain}...")

    # Run the full V2 enumeration pipeline
    output_files = enumerate_subdomains_v2(
        target_domain,
        previous_scan_dir=args.previous_scan_dir,
        save_to_db=args.save_to_db
    )

    if not args.save_to_db:
        print("\nReconnaissance complete.")
        print("Output files generated:")
        for name, path in output_files.items():
            print(f"- {name.replace('_', ' ').title()}: {path}")
    else:
        print("\nReconnaissance complete and results saved to the database.")

if __name__ == "__main__":
    main()
