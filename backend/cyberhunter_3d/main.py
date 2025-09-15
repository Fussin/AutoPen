import sys
import os
import subprocess
import argparse
from typing import Set

from .core.reconnaissance.passive_engine import run_passive_enumeration
from .core.reconnaissance.ip_scan import scan_ip_target
from .common.utils import is_valid_domain, resolve_domain, check_tool
from .common.exceptions import ToolNotFoundError
from .common.log import get_rich_logger

logger = get_rich_logger(__name__)

def print_banner():
    """Prints the tool's ASCII art banner."""
    banner = """
============================================================
|   ____ _             _           _   _   _                |
|  / ___| |_   _ _ __ | |__   __ _| |_| |_| | ___   _ __    |
| | |   | | | | | '_ \| '_ \ / _` | __| __| |/ _ \ | '_ \   |
| | |___| | |_| | | | | | | | (_| | |_| |_| |  __/ | | | |  |
|  \____|_|\__,_|_| |_|_| |_|\__,_|\__|\__|_|\___|_|_| |_|  |
|                                                          |
|         CyberHunter 3D - Recon & Vulnerability Scanner   |
============================================================
    """
    print(banner)

def display_menu(header: str, options: dict) -> str:
    """Generic function to display a menu and get user choice."""
    print(f"\n--- {header} ---")
    for key, value in options.items():
        print(f"{key}. {value}")
    print("-" * (len(header) + 8))

    while True:
        choice = input("> ").strip()
        if choice in options:
            return choice
        else:
            logger.error("Invalid option, please try again.")

def get_domain_input() -> str:
    """Prompts the user for a domain and validates it."""
    while True:
        domain = input("Enter the target domain (e.g., example.com): ").strip().lower()
        if is_valid_domain(domain):
            return domain
        else:
            logger.error("Invalid domain format. Please enter a valid domain.")

def run_active_scan(subdomains: Set[str]):
    """
    Resolves subdomains to IPs and runs an active scan on them.
    """
    if not subdomains:
        logger.warning("No subdomains provided to active scan. Skipping.")
        return

    logger.info("--- Starting Active Scan Phase ---")
    try:
        check_tool("nmap")
    except ToolNotFoundError:
        logger.error("[bold red]Active Scan requires 'nmap'. Please install it and try again.[/bold red]")
        return

    # Resolve subdomains to unique IP addresses
    unique_ips = set()
    for sub in subdomains:
        ip = resolve_domain(sub)
        if ip:
            unique_ips.add(ip)

    if not unique_ips:
        logger.warning("Could not resolve any subdomains to IP addresses. Cannot perform active scan.")
        return

    logger.info(f"Resolved {len(subdomains)} subdomains to {len(unique_ips)} unique IP addresses.")

    # Run nmap on each unique IP
    all_scan_results = []
    for ip in unique_ips:
        results = scan_ip_target(ip)
        if results:
            all_scan_results.extend(results)

    # Display results
    if not all_scan_results:
        logger.info("Active scan completed. No open ports found.")
        return

    logger.info("--- Active Scan Results (Open Ports) ---")
    for result in all_scan_results:
        ip = result.get('value')
        ports = result.get('details', {}).get('ports', [])
        print(f"\n[+] Host: {ip}")
        for port_info in ports:
            service = port_info.get('service_name', 'unknown')
            product = port_info.get('service_product', '')
            version = port_info.get('service_version', '')
            print(f"  - Port {port_info['portid']}/{port_info['protocol']}: {service} ({product} {version})")

def main_cli_loop():
    """The main interactive loop for the CLI."""
    while True:
        print_banner()
        main_menu_choice = display_menu("Main Menu", {"1": "Enter a domain", "2": "Exit"})

        if main_menu_choice == "2":
            logger.info("Exiting CyberHunter 3D. Goodbye!")
            sys.exit(0)

        domain = get_domain_input()

        engine_menu_choice = display_menu(
            f"Select scan type for '{domain}'",
            {"1": "Passive Engine", "2": "Active Engine", "3": "Both"}
        )

        subdomains: Set[str] = set()

        # --- Passive Scan ---
        if engine_menu_choice in ["1", "3"]:
            logger.info(f"--- Starting Passive Scan for {domain} ---")
            subdomains = run_passive_enumeration(domain)
            if subdomains:
                logger.info(f"Found {len(subdomains)} subdomains:")
                for sub in sorted(list(subdomains)):
                    print(sub) # Clean output for the user
            else:
                logger.warning("Passive scan finished. No subdomains found.")

        # --- Active Scan ---
        if engine_menu_choice in ["2", "3"]:
            if not subdomains:
                logger.info("Active scan requires subdomains. Running a passive scan first...")
                subdomains = run_passive_enumeration(domain)
                if not subdomains:
                    logger.error("Could not find any subdomains for the active scan. Aborting.")
                else:
                    logger.info(f"Found {len(subdomains)} subdomains to target.")

            if subdomains:
                run_active_scan(subdomains)

        # --- Scan Again? ---
        scan_again_choice = display_menu("Scan Complete", {"1": "Scan Again", "2": "Exit"})
        if scan_again_choice == "2":
            logger.info("Exiting CyberHunter 3D. Goodbye!")
            sys.exit(0)

# --- Dependency Management Functions ---

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
        "nmap": "sudo apt-get install nmap -y (or use your package manager)",
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
        logger.error("[bold red]Some dependencies are missing. Please install them.[/bold red]")
        return False

def install_dependencies():
    """Attempts to install all missing dependencies using the install script."""
    logger.info("--- Installing Dependencies ---")
    # Correctly locate the script relative to this file's location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # The script is in `backend/scripts/`, so we go up one dir from `main.py`'s location
    script_path = os.path.join(script_dir, '..', 'scripts', 'install_tools.sh')

    # Check if the script exists before trying to run it
    if not os.path.exists(script_path):
        logger.error(f"Error: Installation script not found at '{script_path}'.")
        logger.error("Please install dependencies manually based on the --check-deps command.")
        sys.exit(1)

    try:
        subprocess.run(['chmod', '+x', script_path], check=True)
        subprocess.run([script_path], check=True)
        logger.info("[bold green]Dependency installation script finished.[/bold green]")
        logger.info("Please verify the installation by running --check-deps again.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error: The installation script failed with exit code {e.returncode}.")
        sys.exit(1)

def main():
    """
    Main entry point. Handles dependency checks and then starts the CLI.
    """
    parser = argparse.ArgumentParser(
        description="CyberHunter 3D - A recon and vulnerability scanning platform.",
        formatter_class=argparse.RawTextHelpFormatter # To improve help text formatting
    )
    parser.add_argument(
        "domain",
        nargs='?',
        default=None,
        help="The root domain to target. If provided, runs a non-interactive scan.\n"
             "If not provided, starts the interactive CLI."
    )
    parser.add_argument(
        "--check-deps",
        action="store_true",
        help="Check if all external tool dependencies are installed."
    )
    parser.add_argument(
        "--install-deps",
        action="store_true",
        help="Attempt to install all external tool dependencies."
    )

    args = parser.parse_args()

    if args.check_deps:
        check_dependencies()
        sys.exit(0)

    if args.install_deps:
        install_dependencies()
        sys.exit(0)

    if args.domain:
        # Non-interactive mode (legacy behavior)
        print_banner()
        logger.info(f"Running non-interactive scan for {args.domain}...")
        subdomains = run_passive_enumeration(args.domain)
        if subdomains:
            logger.info(f"Found {len(subdomains)} subdomains:")
            for sub in sorted(list(subdomains)):
                print(sub)
            run_active_scan(subdomains)
        else:
            logger.warning("Scan finished. No subdomains found.")
    else:
        # Interactive mode
        main_cli_loop()

if __name__ == "__main__":
    main()
