import argparse
import subprocess
import sys
from .core.reconnaissance.passive_engine import run_passive_enumeration
from .common.utils import check_tool
from .common.exceptions import ToolNotFoundError

def print_check(name, is_found, install_cmd):
    """Helper to print dependency check status."""
    status = "✓" if is_found else "✘"
    color = "\033[92m" if is_found else "\033[91m"
    reset_color = "\033[0m"
    print(f"[{color}{status}{reset_color}] {name}", end="")
    if not is_found:
        print(f" - MISSING (Install: {install_cmd})")
    else:
        print()

def check_dependencies():
    """Checks for all required external tools."""
    print("--- Checking Dependencies ---")

    tools = {
        "amass": "go install -v github.com/owasp-amass/amass/v3/cmd/amass@latest",
        "assetfinder": "go install -v github.com/tomnomnom/assetfinder@latest",
        "subfinder": "go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest",
        "httpx": "go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest",
        "nuclei": "go install -v github.com/projectdiscovery/nuclei/v2/cmd/nuclei@latest",
        "gowitness": "go install -v github.com/sensepost/gowitness@latest",
    }

    all_found = True
    for tool, install_cmd in tools.items():
        try:
            check_tool(tool)
            print_check(tool, True, install_cmd)
        except ToolNotFoundError:
            all_found = False
            print_check(tool, False, install_cmd)

    print("-" * 29)
    if all_found:
        print("\033[92mAll dependencies are installed!\033[0m")
        return True
    else:
        print("\033[91mSome dependencies are missing. Please install them or run with --install-deps.\033[0m")
        return False

def install_dependencies():
    """Attempts to install all missing dependencies using the install script."""
    print("--- Installing Dependencies ---")
    script_path = "cyberhunter_3d/scripts/install_tools.sh"
    try:
        # Give executable permission to the script
        subprocess.run(['chmod', '+x', script_path], check=True)
        # Run the script
        subprocess.run([script_path], check=True)
        print("\n\033[92mDependency installation script finished.\033[0m")
        print("Please verify the installation by running --check-deps again.")
    except FileNotFoundError:
        print(f"\033[91mError: Installation script not found at '{script_path}'.\033[0m")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"\033[91mError: The installation script failed with exit code {e.returncode}.\033[0m")
        print("Please run the script manually to debug.")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="CyberHunter 3D - A recon and vulnerability scanning platform.")
    parser.add_argument("domain", nargs='?', default=None, help="The root domain to target for a passive scan.")
    parser.add_argument("--check-deps", action="store_true", help="Check if all external tool dependencies are installed.")
    parser.add_argument("--install-deps", action="store_true", help="Attempt to install all external tool dependencies.")

    args = parser.parse_args()

    if args.check_deps:
        check_dependencies()
        sys.exit(0)

    if args.install_deps:
        install_dependencies()
        sys.exit(0)

    if args.domain:
        print(f"Running passive enumeration for {args.domain}...")
        subdomains = run_passive_enumeration(args.domain)
        print(f"Found {len(subdomains)} subdomains:")
        for sub in sorted(list(subdomains)):
            print(sub)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
