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

def run_active_enumeration(domain: str, output_dir: str) -> List[str]:
    """
    Run active enumeration for a domain and return a list of output file paths.
    """
    logger.info(f"Starting active enumeration for: {domain}")

    active_engine_config = config.get('settings', {}).get('active_engine', {})
    active_tools_config = active_engine_config.get('tools', [])
    all_tools_config = config.get('tools', {})

    wordlist = active_engine_config.get('wordlist')
    resolvers = active_engine_config.get('resolvers')

    if not wordlist or not os.path.exists(wordlist):
        logger.error(f"Wordlist not found at: {wordlist}. Aborting active enumeration.")
        return []

    if not resolvers or not os.path.exists(resolvers):
        logger.error(f"Resolvers file not found at: {resolvers}. Aborting active enumeration.")
        return []

    tools_to_run = []

    # Define the placeholders and their values
    replacements = {
        "{domain}": domain,
        "{wordlist}": wordlist,
        "{resolvers}": resolvers,
    }

    for tool_config in active_tools_config:
        tool_name = tool_config.get('name')
        if not tool_name:
            logger.warning("Skipping a tool in active_engine config because it's missing a 'name'.")
            continue

        try:
            check_tool(tool_name)
            tool_cmd_config = all_tools_config.get(tool_name)
            if not tool_cmd_config or 'cmd' not in tool_cmd_config:
                logger.warning(f"Skipping tool '{tool_name}' because its command is not defined in the 'tools' section of the config.")
                continue

            # Safely format the command string
            cmd = tool_cmd_config['cmd']
            for placeholder, value in replacements.items():
                if placeholder in cmd:
                    cmd = cmd.replace(placeholder, value)

            tools_to_run.append({
                'name': tool_name,
                'cmd': cmd,
                'args': tool_cmd_config.get('args', '')
            })
        except ToolNotFoundError as e:
            logger.warning(f"[✘] {e.tool_name} not found. Skipping.")
            logger.warning(f"  To install, run: {e.install_cmd}")

    if not tools_to_run:
        logger.error("No active reconnaissance tools found or configured. Aborting.")
        return []

    output_paths = asyncio.run(run_enumerators(domain, tools_to_run, output_dir))

    logger.info(f"Active enumeration finished for {domain}. Output files at: {output_dir}")
    return output_paths
