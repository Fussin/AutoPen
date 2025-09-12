import asyncio
import shlex
import os
from typing import List, Dict

from ...common.log import get_rich_logger as get_logger

logger = get_logger(__name__)

async def run_cmd(cmd: str, outpath: str) -> str:
    """
    Runs a command asynchronously and writes its stdout to a file.

    Args:
        cmd: The command to run.
        outpath: The path to the output file.

    Returns:
        The path to the output file.
    """
    logger.info(f"Running command: {cmd}")
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        logger.error(f"Command failed with exit code {proc.returncode}: {cmd}")
        logger.error(stderr.decode())

    with open(outpath, "wb") as f:
        f.write(stdout)

    logger.info(f"Command finished successfully: {cmd}")
    return outpath

async def run_enumerators(domain: str, tools: List[Dict], output_dir: str) -> List[str]:
    """
    Runs a list of enumeration tools in parallel.

    Args:
        domain: The target domain.
        tools: A list of tool dictionaries. Each dictionary should have 'name', 'cmd', and optional 'args'.
        output_dir: The directory to store the output files.

    Returns:
        A list of paths to the output files.
    """
    tasks = []
    os.makedirs(output_dir, exist_ok=True)

    for tool in tools:
        cmd_template = tool.get('cmd')
        if not cmd_template:
            logger.warning(f"Tool '{tool.get('name')}' is missing the 'cmd' key. Skipping.")
            continue

        args = tool.get('args', '')
        # Safely substitute domain and args
        cmd = cmd_template.format(domain=domain, args=args)

        output_file = os.path.join(output_dir, f"{domain}_{tool['name']}.txt")
        tasks.append(run_cmd(cmd, output_file))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    output_paths = []
    for result in results:
        if isinstance(result, str):
            output_paths.append(result)
        elif isinstance(result, Exception):
            logger.error(f"An enumerator task failed: {result}")

    return output_paths
