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

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()
    target_domain = args.domain

    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)

    print(f"Starting V2 reconnaissance pipeline for {target_domain}...")

    # Run the full V2 enumeration pipeline
    enumerate_subdomains_v2(target_domain)

    config = load_config()
    output_file = os.path.join(config['recon_output_dir'], config['final_recon_file'])

    print(f"\nReconnaissance complete for {target_domain}.")
    print(f"Detailed results have been saved to {output_file}")

if __name__ == "__main__":
    main()
