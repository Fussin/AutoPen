import subprocess
from typing import List, Dict
from ...common.utils import check_tool
from ...common.exceptions import ToolNotFoundError
from ...common.log import get_rich_logger

logger = get_rich_logger(__name__)

def get_cidrs_for_asn(asn: str) -> List[Dict[str, str]]:
    """
    Uses amass to find all CIDR ranges for a given ASN.

    :param asn: The Autonomous System Number (as a string, e.g., "15169").
    :return: A list of asset dictionaries, e.g., [{'type': 'cidr', 'value': '...'}].
    """
    logger.info(f"Starting ASN lookup for [bold cyan]AS{asn}[/] using amass...")
    assets = []
    try:
        amass_path = check_tool("amass", "go install -v github.com/owasp-amass/amass/v3/cmd/amass@latest")
        command = [amass_path, 'intel', '-asn', asn]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            timeout=300 # 5 minute timeout for amass intel
        )

        output = result.stdout
        if not output:
            logger.warning(f"Amass produced no output for AS{asn}")
            return assets

        # Amass output for this command is one CIDR per line
        for line in output.strip().splitlines():
            # Basic validation that it looks like a CIDR
            if '/' in line and '.' in line:
                assets.append({'type': 'cidr', 'value': line.strip()})

        logger.info(f"Found [bold green]{len(assets)}[/] CIDRs for AS{asn}.")

    except ToolNotFoundError as e:
        logger.error(f"[bold red]✘ {e.tool_name} not found.[/bold red] Cannot perform ASN lookup.")
        logger.error(f"  To install, run: [yellow]{e.install_cmd}[/yellow]")
    except subprocess.TimeoutExpired:
        logger.error(f"Amass command timed out for AS{asn}. The ASN might be too large.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running amass for AS{asn}: {e}")
        logger.error(f"Stderr: {e.stderr}")

    return assets
