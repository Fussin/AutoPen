import asyncio
import os
from typing import List, Dict

from .enumerator_runner import run_enumerators
from ...common.utils import load_config
from ...common.log import get_rich_logger as get_logger
from ...common.utils import check_tool
from ...common.exceptions import ToolNotFoundError

config = load_config()
logger = get_logger(__name__)

def run_passive_enumeration(domain: str, output_dir: str) -> List[str]:
    """
    Run passive enumeration for a domain and return a list of output file paths.
    """
    logger.info(f"Starting passive enumeration for: {domain}")

    passive_tools_config = config.get('settings', {}).get('passive_engine', {}).get('tools', [])
    all_tools_config = config.get('tools', {})

    tools_to_run = []
    for tool_config in passive_tools_config:
        tool_name = tool_config.get('name')
        if not tool_name:
            logger.warning("Skipping a tool in passive_engine config because it's missing a 'name'.")
            continue

        try:
            # Check if the tool is installed
            check_tool(tool_name)

            # Get the command for the tool
            tool_cmd_config = all_tools_config.get(tool_name)
            if not tool_cmd_config or 'cmd' not in tool_cmd_config:
                logger.warning(f"Skipping tool '{tool_name}' because its command is not defined in the 'tools' section of the config.")
                continue

            # Add the tool to the list of tools to run
            tools_to_run.append({
                'name': tool_name,
                'cmd': tool_cmd_config['cmd'],
                'args': tool_cmd_config.get('args', '')
            })

        except ToolNotFoundError as e:
            logger.warning(f"[✘] {e.tool_name} not found. Skipping.")
            logger.warning(f"  To install, run: {e.install_cmd}")


    if not tools_to_run:
        logger.error("No passive reconnaissance tools found or configured. Aborting.")
        return []

    # Run the enumerators in parallel
    output_paths = asyncio.run(run_enumerators(domain, tools_to_run, output_dir))

    logger.info(f"Passive enumeration finished for {domain}. Output files at: {output_dir}")
    return output_paths
