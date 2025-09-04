import os
import asyncio
import json
from typing import List, Dict
from src.common.plugin_loader import load_plugins
from src.common.config import load_config

async def run_osint_phase(targets: Dict[str, List[str]]):
    """
    Orchestrates the OSINT phase.
    """
    print(f"Starting OSINT phase...")

    # 1. Load config
    config = load_config()

    # 2. Load enabled OSINT plugins
    osint_plugins = load_plugins("src/plugins/osint", config)

    all_findings: List[Dict] = []
    new_seeds = {"domains": [], "urls": [], "ips": []}

    # 3. Run OSINT plugins
    for plugin in osint_plugins:
        if plugin.name() == "sherlock" and "usernames" in targets:
            findings = plugin.run(targets["usernames"])
            all_findings.extend(findings)
        elif plugin.name() == "aquatone" and "urls" in targets:
            findings = plugin.run(targets["urls"])
            all_findings.extend(findings)

    # 4. Feedback loop (placeholder)
    # TODO: Implement a proper queueing mechanism.

    print("OSINT phase complete.")
    return all_findings, new_seeds

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        try:
            target_data = json.loads(sys.argv[1])
            asyncio.run(run_osint_phase(target_data))
        except json.JSONDecodeError:
            print("Error: Invalid JSON format for targets.")
    else:
        print("Usage: python src/phases/osint.py '<json_string>'")
