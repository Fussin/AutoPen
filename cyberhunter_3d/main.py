import argparse
import sys
import os
from core.reconnaissance.subdomain_enum import enumerate_subdomains, save_results

def main():
    """
    Main function to run the CyberHunter 3D reconnaissance.
    """
    print("Welcome to CyberHunter 3D - Reconnaissance Module")

    parser = argparse.ArgumentParser(description="A futuristic bug bounty automation platform.")
    parser.add_argument("-d", "--domain", required=True, help="The target domain to perform reconnaissance on.")

    # A simple check to guide the user if no arguments are provided.
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()

    target_domain = args.domain

    # Change to the project root so that Sublist3r path is correct.
    # This is a bit of a hack for now, a better config management would be needed for a real app.
    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)

    # 1. Run the subdomain enumeration
    found_subdomains = enumerate_subdomains(target_domain)

    # 2. Save the results
    output_filename = "Subdomain.txt"
    save_results(found_subdomains, output_filename)

    print(f"\nReconnaissance complete for {target_domain}.")
    print(f"Results have been saved to {output_filename}")

if __name__ == "__main__":
    main()
