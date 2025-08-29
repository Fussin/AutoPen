from __future__ import annotations
import os
from pathlib import Path
from typing import List, Tuple, Set
import subprocess
import tempfile

def run_visual_recon(master_subdomains: Set[str], output_dir: str = None) -> Tuple[List[str], str]:
    """
    Run visual reconnaissance:
    - Write domains to a temp file
    - Run gowitness/aquatone (if available) against that list
    - Ensure screenshots are collected under one root directory and return (live_hosts, screenshots_root)

    Returns:
      (live_hosts_list, screenshots_root_dir)
    """
    # Prepare output dir
    if output_dir is None:
        output_dir = os.path.join(os.getcwd(), "data", "results", "screenshots")
    screenshots_root = Path(output_dir)
    screenshots_root.mkdir(parents=True, exist_ok=True)

    # Prepare input list
    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".txt") as tf:
        for sub in sorted(master_subdomains):
            tf.write(sub + "\n")
        tmpname = tf.name

    # Try gowitness first; if missing, skip but still return directory
    gowitness_cmd = ["gowitness", "file", tmpname, "--destination", str(screenshots_root)]
    try:
        subprocess.run(gowitness_cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError:
        # gowitness not found: fallback to httpx probing to collect live hosts, no screenshots
        live_hosts = []
        import httpx
        for d in sorted(master_subdomains):
            try:
                r = httpx.get(f"http://{d}", timeout=8.0)
                if r.status_code:
                    live_hosts.append(d)
            except Exception:
                pass
        # Return live hosts and the screenshots_root (empty)
        os.unlink(tmpname)
        return sorted(set(live_hosts)), str(screenshots_root)
    except subprocess.CalledProcessError:
        # gowitness failed for some hosts — but proceed
        pass

    # If gowitness produced artifacts, attempt to list screenshot files to determine live hosts
    live_hosts = []
    for p in screenshots_root.rglob("*"):
        if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg"}:
            # assume file name contains hostname or path; use parent folder names to infer host
            try:
                parts = p.parts
                # last folder before filename might be host; fallback to filename
                host = parts[-2] if len(parts) >= 2 else p.stem
                live_hosts.append(host)
            except Exception:
                pass

    os.unlink(tmpname)
    return sorted(set(live_hosts)), str(screenshots_root)
