import subprocess
import tempfile
import os
import re
import shutil
from typing import Set, Dict, Any
from cyberhunter_3d.core.plugins.base import Plugin
from cyberhunter_3d.utils.logger import setup_logger
from cyberhunter_3d.core.reconnaissance.utils import load_config

class JsAndCodePlugin(Plugin):
    """
    Plugin for JS and Code analysis.
    """
    @property
    def name(self) -> str:
        return "JS and Code Analysis"

    @property
    def description(self) -> str:
        return "Crawls JS files and searches code repositories for subdomains and secrets."

    @property
    def requires(self) -> List[str]:
        return ["live_hosts"]

    @property
    def provides(self) -> List[str]:
        return ["subdomains"]

    def run(self, context: 'ScanContext'):
        logger = setup_logger('JsAndCodePlugin', 'js_and_code_plugin.log')
        config = load_config()
        target = context.target

        live_hosts = context.get("live_hosts")
        if not live_hosts:
            logger.info("No live hosts to analyze. Skipping JS/Code analysis.")
            return

        all_raw_text = []

        # Katana
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as hosts_file:
            hosts_filename = hosts_file.name
            for host in live_hosts:
                hosts_file.write(f"{host}\n")

        with tempfile.NamedTemporaryFile(mode='r', delete=False, suffix=".txt") as katana_output:
            katana_output_filename = katana_output.name

        try:
            katana_cmd = [config['tools']['katana'], '-l', hosts_filename, '-silent', '-o', katana_output_filename]
            subprocess.run(katana_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            all_raw_text.append(katana_output.read())
        except Exception as e:
            logger.error(f"Katana execution failed: {e}")
        finally:
            os.remove(hosts_filename)
            os.remove(katana_output_filename)

        # GitHub Dorking
        github_findings = self._run_github_dorking(target, config, logger)
        if github_findings:
            all_raw_text.append(github_findings)

        combined_text = "\n".join(all_raw_text)
        extracted_subdomains = self._extract_subdomains_from_text(combined_text, target)

        context.update_set("subdomains", extracted_subdomains)
        # In the future, we can add secrets and endpoints to the context as well
        # context.set("secrets", secrets)

    def _extract_subdomains_from_text(self, text: str, domain: str) -> Set[str]:
        generic_domain_regex = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9-]{1,61}[a-zA-Z0-9](?:\.[a-zA-Z]{2,})+")
        potential_domains = generic_domain_regex.findall(text)
        subdomains = {host.lower() for host in potential_domains if host.lower().endswith(f".{domain}") and host.lower() != domain}
        return subdomains

    def _run_github_dorking(self, domain: str, config: Dict, logger) -> str:
        dorks_file = config['wordlists'].get('github_dorks')
        gh_dork_tool = config['tools'].get('gh_dork')
        if not all([dorks_file, gh_dork_tool]):
            return ""

        org_name = domain.split('.')[0]
        output_dir = f"gh_dork_results_{org_name}"

        try:
            gh_dork_command = ['python3', gh_dork_tool, '-d', dorks_file, '-o', org_name, '-n', output_dir]
            subprocess.run(gh_dork_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            findings = []
            if os.path.exists(output_dir):
                for filename in os.listdir(output_dir):
                    with open(os.path.join(output_dir, filename), 'r', errors='ignore') as f:
                        findings.append(f.read())
            return "\n".join(findings)
        except Exception as e:
            logger.error(f"An error occurred during GitHub dorking: {e}")
            return ""
        finally:
            if os.path.exists(output_dir):
                shutil.rmtree(output_dir)
