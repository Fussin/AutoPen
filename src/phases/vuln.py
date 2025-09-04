import os
import asyncio
import json
from typing import List, Dict
from src.common.plugin_loader import load_plugins
from src.common.config import load_config

async def run_vuln_phase(targets: Dict[str, List[str]]):
    """
    Orchestrates the vulnerability discovery phase.
    """
    print(f"Starting vulnerability discovery phase...")

    # 1. Load config
    config = load_config()

    # 2. Load enabled vulnerability scanning plugins
    vuln_plugins = load_plugins("src/plugins/vuln", config)

    # 3. Run scanners in parallel
    all_findings: List[Dict] = []
    tasks = []

    for plugin in vuln_plugins:
        if plugin.name() == "sqlmap" and "urls" in targets:
            task = asyncio.to_thread(plugin.run, targets["urls"])
            tasks.append(task)
        elif plugin.name() == "nuclei" and "urls" in targets:
            task = asyncio.to_thread(plugin.run, targets["urls"])
            tasks.append(task)
        elif plugin.name() == "trufflehog" and "git_repos" in targets:
            task = asyncio.to_thread(plugin.run, targets["git_repos"])
            tasks.append(task)

    results = await asyncio.gather(*tasks)
    for result in results:
        if result:
            all_findings.extend(result)

    # 4. Normalize and deduplicate (placeholder)
    aggregated_findings = all_findings
    deduped_findings = aggregated_findings

    # 5. Produce outputs
    output_dir = config.get("output_dir", "outputs")
    os.makedirs(output_dir, exist_ok=True)

    with open(os.path.join(output_dir, "findings_aggregated.json"), "w") as f:
        json.dump(aggregated_findings, f, indent=4)

    with open(os.path.join(output_dir, "findings_dedup.json"), "w") as f:
        json.dump(deduped_findings, f, indent=4)

    print("Vulnerability discovery phase complete.")
    return deduped_findings

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        try:
            target_data = json.loads(sys.argv[1])
            asyncio.run(run_vuln_phase(target_data))
        except json.JSONDecodeError:
            print("Error: Invalid JSON format for targets.")
    else:
        print("Usage: python src/phases/vuln.py '<json_string>'")
