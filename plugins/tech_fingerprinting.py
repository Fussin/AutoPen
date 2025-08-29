import subprocess
import tempfile
import os
import json
from typing import Set, List, Dict, Any
from cyberhunter_3d.core.plugins.base import Plugin
from cyberhunter_3d.utils.logger import setup_logger
from cyberhunter_3d.core.reconnaissance.utils import load_config

class TechFingerprintingPlugin(Plugin):
    """
    Plugin for technology fingerprinting and port scanning.
    """
    @property
    def name(self) -> str:
        return "Technology Fingerprinting"

    @property
    def description(self) -> str:
        return "Performs technology fingerprinting with Wappalyzer and port scanning with Naabu/Nmap."

    def run(self, target: str, **kwargs) -> Dict[str, Any]:
        logger = setup_logger('TechFingerprintingPlugin', 'tech_fingerprinting_plugin.log')
        config = load_config()

        live_hosts = kwargs.get('live_hosts')
        if not live_hosts:
            logger.info("No live hosts provided for technology fingerprinting.")
            return {}

        tech_results = {}

        # Wappalyzer
        for host in live_hosts:
            try:
                target_url = host if host.startswith(('http://', 'https://')) else f"http://{host}"
                wappalyzer_command = [config['tools']['wappalyzer'], target_url, '--pretty']
                result = subprocess.run(wappalyzer_command, capture_output=True, text=True, check=True)
                wappalyzer_data = json.loads(result.stdout)
                if host not in tech_results:
                    tech_results[host] = {}
                tech_results[host]['technologies'] = wappalyzer_data.get('technologies', [])
            except Exception as e:
                logger.error(f"Wappalyzer failed for {host}: {e}")

        # Naabu and Nmap
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as live_hosts_file:
            live_hosts_filename = live_hosts_file.name
            for host in live_hosts:
                live_hosts_file.write(f"{host}\n")

        try:
            naabu_results_file = os.path.join(config['recon_output_dir'], 'naabu_results.json')
            naabu_command = [config['tools']['naabu'], '-list', live_hosts_filename, '-top-ports', '1000', '-json', '-o', naabu_results_file]
            subprocess.run(naabu_command)

            if os.path.exists(naabu_results_file):
                with open(naabu_results_file, 'r') as f_in:
                    for line in f_in:
                        try:
                            data = json.loads(line)
                            host = data['host']
                            port = data['port']
                            if host not in tech_results:
                                tech_results[host] = {}
                            if 'ports' not in tech_results[host]:
                                tech_results[host]['ports'] = []

                            nmap_output_dir = os.path.join(config['recon_output_dir'], config['nmap_output_dir'])
                            os.makedirs(nmap_output_dir, exist_ok=True)
                            nmap_output_file = os.path.join(nmap_output_dir, f'nmap_{host}_{port}.txt')
                            nmap_command = [config['tools']['nmap'], '-sV', '-p', str(port), host, '-oN', nmap_output_file]
                            subprocess.run(nmap_command)

                            with open(nmap_output_file, 'r') as f_nmap:
                                nmap_output = f_nmap.read()
                                tech_results[host]['ports'].append({'port': port, 'service': nmap_output})
                        except Exception as e:
                            logger.warning(f"Could not parse naabu/nmap output line: {line}. Error: {e}")
        except Exception as e:
            logger.error(f"An error occurred during port scanning: {e}")
        finally:
            os.remove(live_hosts_filename)
            if os.path.exists(naabu_results_file):
                os.remove(naabu_results_file)

        return {"tech_fingerprinting": tech_results}
