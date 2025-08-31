import logging
import os
import json
from ..reconnaissance.utils import load_config, run_command

log = logging.getLogger(__name__)

def run_semgrep_scan(target_dir: str, context) -> list:
    """
    Runs a Semgrep scan on a given directory.

    Args:
        target_dir: The directory to scan.
        context: The scan context, used for getting config and results dir.

    Returns:
        A list of vulnerabilities found by Semgrep.
    """
    log.info(f"Running Semgrep SAST scan on directory: {target_dir}")
    if not os.path.isdir(target_dir):
        log.error(f"Target directory for SAST scan does not exist: {target_dir}")
        return []

    config = context.get("config", {})
    semgrep_command_template = config.get("tool_commands", {}).get("semgrep_scan")
    if not semgrep_command_template:
        log.error("Semgrep command template not found in config.")
        return []

    output_filename = f"semgrep_results_{os.path.basename(target_dir)}.json"
    output_filepath = os.path.join(context.results_dir, output_filename)

    command = semgrep_command_template.format(
        target_dir=target_dir,
        output_file=output_filepath
    )

    stdout, stderr = run_command(command, "Semgrep")

    vulnerabilities = []
    if os.path.exists(output_filepath):
        try:
            with open(output_filepath, 'r') as f:
                data = json.load(f)
                # The 'results' key contains the list of findings
                vulnerabilities = data.get("results", [])
        except (json.JSONDecodeError, KeyError) as e:
            log.error(f"Could not parse Semgrep output file {output_filepath}: {e}")

    log.info(f"Semgrep scan on {target_dir} completed. Found {len(vulnerabilities)} potential issues.")
    return vulnerabilities
