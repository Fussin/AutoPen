import argparse
import subprocess
import sys
import os
from .core.reconnaissance.passive_engine import run_passive_enumeration
from .common.utils import check_tool
from .common.exceptions import ToolNotFoundError
from .common.log import get_rich_logger

logger = get_rich_logger(__name__)

def print_check(name, is_found, install_cmd):
    """Helper to print dependency check status."""
    if is_found:
        logger.info(f"[green]✓[/green] {name}")
    else:
        logger.warning(f"[red]✘[/red] {name} - MISSING (Install: {install_cmd})")

def check_dependencies():
    """Checks for all required external tools."""
    logger.info("--- Checking Dependencies ---")

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

    logger.info("-" * 29)
    if all_found:
        logger.info("[bold green]All dependencies are installed![/bold green]")
        return True
    else:
        logger.error("[bold red]Some dependencies are missing. Please install them or run with --install-deps.[/bold red]")
        return False

def install_dependencies():
    """Attempts to install all missing dependencies using the install script."""
    logger.info("--- Installing Dependencies ---")
    # Construct a robust path to the script relative to this file's location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(script_dir, '..', 'scripts', 'install_tools.sh')

    try:
        # Give executable permission to the script
        subprocess.run(['chmod', '+x', script_path], check=True)
        # Run the script
        subprocess.run([script_path], check=True)
        logger.info("[bold green]Dependency installation script finished.[/bold green]")
        logger.info("Please verify the installation by running --check-deps again.")
    except FileNotFoundError:
        logger.error(f"Error: Installation script not found at '{script_path}'.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error: The installation script failed with exit code {e.returncode}.")
        logger.error("Please run the script manually to debug.")
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
        logger.info(f"Running passive enumeration for {args.domain}...")
        subdomains = run_passive_enumeration(args.domain)
        # Print the final output directly to the console for user consumption
        logger.info(f"Found {len(subdomains)} subdomains:")
        for sub in sorted(list(subdomains)):
            print(sub) # This print is intentional for clean CLI output
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
