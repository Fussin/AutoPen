# cyberhunter_3d/core/reconnaissance/passive_engine.py

import concurrent.futures
import re
import os
from typing import Set, List
from pathlib import Path
import logging

from .utils import load_config, get_logger, run_command

# Plugin import
from ...plugins.recon.subfinder import SubfinderPlugin

config = load_config()
logger = get_logger(__name__)

SUBDOMAIN_RE_TEMPLATE = r'([A-Za-z0-9\-\_\.]*\.{root})'


def _extract_subdomain_from_finding(finding: dict, root_domain: str):
    """
    Try multiple common places where a plugin-adapter might put a discovered subdomain.
    Return the first matching subdomain (or None).
    """
    if not isinstance(finding, dict):
        return None

    # build a regex tailored to the root domain
    pattern = re.compile(SUBDOMAIN_RE_TEMPLATE.format(root=re.escape(root_domain)))

    # 1) evidence.* fields
    ev = finding.get('evidence') or {}
    if isinstance(ev, dict):
        for key in ('poc', 'subdomain', 'path', 'snippet', 'value', 'host', 'hostname'):
            v = ev.get(key)
            if isinstance(v, str) and v:
                m = pattern.search(v)
                if m:
                    return m.group(1)
                # if the field itself looks like a subdomain
                if v == root_domain or v.endswith('.' + root_domain):
                    return v.strip()

    # 2) top-level fields
    for key in ('target', 'host', 'url', 'value', 'name'):
        v = finding.get(key)
        if isinstance(v, str) and v:
            m = pattern.search(v)
            if m:
                return m.group(1)
            if v == root_domain or v.endswith('.' + root_domain):
                return v.strip()

    # 3) try any string values in the dict (last resort)
    def walk_strings(obj):
        if isinstance(obj, str):
            yield obj
        elif isinstance(obj, dict):
            for val in obj.values():
                yield from walk_strings(val)
        elif isinstance(obj, (list, tuple)):
            for val in obj:
                yield from walk_strings(val)

    for s in walk_strings(finding):
        if not isinstance(s, str):
            continue
        m = pattern.search(s)
        if m:
            return m.group(1)

    return None


def run_passive_enumeration(domain: str, output_dir: str = "artifacts/recon") -> Set[str]:
    """
    Run passive enumeration for domain and return set of discovered subdomains.
    Uses the Subfinder plugin first (adapter), then runs other legacy tools in parallel.
    """
    logger.info(f"Starting passive enumeration for: {domain}")
    all_subdomains: Set[str] = set()

    # --- Refactored: Use the Subfinder plugin (adapter) if available ---
    try:
        # instantiate plugin with config if supported, else without args
        try:
            subfinder_plugin = SubfinderPlugin(config=config)
        except TypeError:
            subfinder_plugin = SubfinderPlugin()

        # check dependencies if plugin exposes it
        if hasattr(subfinder_plugin, "check_dependencies") and not subfinder_plugin.check_dependencies():
            logger.warning("Subfinder plugin reports missing dependencies; skipping plugin run.")
            subfinder_findings = []
        else:
            try:
                subfinder_findings = subfinder_plugin.run([domain])
            except Exception as e:
                logger.exception("Subfinder plugin.run() failed: %s", e)
                subfinder_findings = []

        # normalize/collect results defensively
        sd_found = set()
        for f in subfinder_findings or []:
            sd = _extract_subdomain_from_finding(f, domain)
            if sd:
                sd_found.add(sd)
        all_subdomains.update(sd_found)
        logger.info("Subfinder plugin: discovered %d subdomains for %s", len(sd_found), domain)

    except Exception as e:
        # top-level safety (shouldn't happen now, but be defensive)
        logger.exception("Unexpected error while running Subfinder plugin: %s", e)

    # --- Keep other command-line tools for now (amass, assetfinder) and run them in parallel ---
    commands = [
        [config['tools']['amass'], 'enum', '-passive', '-d', '{domain}', '-o', '{output_file}'],
        [config['tools']['assetfinder'], '--subs-only', '{domain}'],
    ]

    # thread pool sized to number of commands (bounded)
    max_workers = min(8, max(1, len(commands)))
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_cmd = {}
        for cmd in commands:
            # executor will call run_command which should expand placeholders like {domain}/{output_file}
            future = executor.submit(run_command, cmd, domain)
            future_to_cmd[future] = cmd

        for future in concurrent.futures.as_completed(future_to_cmd):
            cmd = future_to_cmd[future]
            try:
                result = future.result()  # could be stdout string, or filepath, or None
            except Exception as e:
                logger.exception("Command %s failed: %s", cmd, e)
                continue

            text = ""
            # If result is a path to file, read it
            if isinstance(result, str):
                # prefer reading file if looks like a path and exists
                if os.path.exists(result):
                    try:
                        with open(result, "r", encoding="utf-8", errors="ignore") as fh:
                            text = fh.read()
                    except Exception:
                        # fallback to treat result as stdout string
                        text = result
                else:
                    text = result
            elif isinstance(result, (list, tuple)):
                # some runners may return list of lines
                text = "\n".join(map(str, result))
            elif result is None:
                text = ""
            else:
                # unknown object type: try to stringify
                text = str(result)

            # extract subdomains from the output text using regex for domain
            if text:
                pattern = re.compile(SUBDOMAIN_RE_TEMPLATE.format(root=re.escape(domain)))
                for m in pattern.findall(text):
                    all_subdomains.add(m)

    logger.info("Total discovered subdomains for %s: %d", domain, len(all_subdomains))

    # Ensure artifacts directory exists and write subdomains_all.txt (backwards-compatible)
    outdir = Path(output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    all_file = outdir / f"{domain}_subdomains_all.txt"
    try:
        with open(all_file, "w", encoding="utf-8") as fh:
            for s in sorted(all_subdomains):
                fh.write(s + "\n")
        logger.info("Wrote all subdomains to %s", all_file)
    except Exception:
        logger.exception("Failed to write subdomains_all file to %s", all_file)

    return all_subdomains
