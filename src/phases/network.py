import os
import asyncio
import json
from typing import List, Dict, Set
from src.common.plugin_loader import load_plugins
from src.common.config import load_config

async def run_network_phase(targets: List[str]):
    """
    Orchestrates the network scanning phase.
    """
    print(f"Starting network scanning phase for {len(targets)} targets...")

    # 1. Load config
    config = load_config()

    # 2. Load enabled network scanning plugins
    network_plugins = load_plugins("src/plugins/network", config)

    masscan_plugin = next((p for p in network_plugins if p.name() == "masscan"), None)
    nmap_plugin = next((p for p in network_plugins if p.name() == "nmap"), None)
    enum4linux_plugin = next((p for p in network_plugins if p.name() == "enum4linux"), None)

    all_findings: List[Dict] = []
    output_dir = config.get("output_dir", "outputs")
    os.makedirs(output_dir, exist_ok=True)

    # 3. Port sweep with Masscan
    open_ports_map: Dict[str, Set[int]] = {}
    if masscan_plugin:
        masscan_config = config.get("plugins", {}).get("masscan", {})
        ports = masscan_config.get("ports", "0-1024")
        rate = masscan_config.get("rate", 1000)
        masscan_findings = masscan_plugin.run(targets, ports=ports, rate=rate)
        all_findings.extend(masscan_findings)
        for finding in masscan_findings:
            ip = finding["target"]
            if ip not in open_ports_map:
                open_ports_map[ip] = set()
            open_ports_map[ip].update(finding["fingerprints"]["ports"])

    with open(os.path.join(output_dir, "ports_open.json"), "w") as f:
        json.dump({k: list(v) for k, v in open_ports_map.items()}, f, indent=4)
    print("Port sweep complete.")

    # 4. Deep fingerprinting with Nmap
    if nmap_plugin and open_ports_map:
        for ip, ports in open_ports_map.items():
            if ports:
                port_str = ",".join(map(str, ports))
                nmap_findings = nmap_plugin.run([ip], args=["-sV", "-p", port_str, "-oX", "-"])
                all_findings.extend(nmap_findings)

    with open(os.path.join(output_dir, "services_fingerprinted.json"), "w") as f:
        json.dump([f for f in all_findings if f["tool"] == "nmap"], f, indent=4)
    print("Deep fingerprinting complete.")

    # 5. Service enumeration
    if enum4linux_plugin:
        smb_targets = []
        for finding in all_findings:
            if finding["tool"] == "nmap":
                if any(p.get("port") == 445 for p in finding["fingerprints"].get("services", [])):
                    smb_targets.append(finding["target"])

        if smb_targets:
            enum_findings = enum4linux_plugin.run(list(set(smb_targets)))
            all_findings.extend(enum_findings)

            service_enum_dir = os.path.join(output_dir, "service_enum")
            os.makedirs(service_enum_dir, exist_ok=True)
            with open(os.path.join(service_enum_dir, "enum4linux.json"), "w") as f:
                json.dump(enum_findings, f, indent=4)

    print("Service enumeration complete.")
    print("Network scanning phase complete.")
    return all_findings

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        asyncio.run(run_network_phase(sys.argv[1:]))
    else:
        print("Usage: python src/phases/network.py <target1> <target2> ...")
