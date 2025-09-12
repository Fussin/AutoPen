import subprocess
from typing import List, Dict
from ...common.utils import check_tool
from ...common.exceptions import ToolNotFoundError
from ...common.log import get_rich_logger

# Import the parser from the sibling module to help classify the output
from ..target_parser import parse_single_target

logger = get_rich_logger(__name__)

def get_assets_for_org(org_name: str) -> List[Dict[str, str]]:
    """
    Uses amass to find all assets (domains, CIDRs) for a given organization.

    :param org_name: The name of the organization (e.g., "Google LLC").
    :return: A list of asset dictionaries, e.g., [{'type': 'domain', 'value': '...'}]
    """
    logger.info(f"Starting organization lookup for [bold cyan]'{org_name}'[/] using amass...")
    assets = []
    # Use a set to avoid duplicate assets before returning as a list
    found_assets = set()
    try:
        amass_path = check_tool("amass", "go install -v github.com/owasp-amass/amass/v3/cmd/amass@latest")
        command = [amass_path, 'intel', '-org', org_name]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            timeout=600 # 10 minute timeout for amass intel -org
        )

        output = result.stdout
        if not output:
            logger.warning(f"Amass produced no output for organization '{org_name}'")
            return assets

        for line in output.strip().splitlines():
            clean_line = line.split('[')[0].strip()
            if clean_line:
                value, asset_type = parse_single_target(clean_line)
                if asset_type not in ['unknown', 'empty']:
                    found_assets.add((value, asset_type))

        logger.info(f"Found [bold green]{len(found_assets)}[/] unique assets for organization '{org_name}'.")

        # Convert set of tuples to list of dictionaries
        assets = [{'type': asset_type, 'value': value} for value, asset_type in found_assets]

    except ToolNotFoundError as e:
        logger.error(f"[bold red]✘ {e.tool_name} not found.[/bold red] Cannot perform organization lookup.")
        logger.error(f"  To install, run: [yellow]{e.install_cmd}[/yellow]")
    except subprocess.TimeoutExpired:
        logger.error(f"Amass command timed out for organization '{org_name}'. The organization might be too large.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running amass for organization '{org_name}': {e}")
        logger.error(f"Stderr: {e.stderr}")

    return assets
