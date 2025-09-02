import logging
import subprocess
import xml.etree.ElementTree as ET
import tempfile
import os
from typing import Dict, Any

from ..base import Plugin
from ..context import ScanContext

log = logging.getLogger(__name__)

class NmapScanPlugin(Plugin):
    """
    Nmap Scan Plugin to discover open ports and services.
    """
    @property
    def name(self) -> str:
        return "Nmap Scan"

    @property
    def description(self) -> str:
        return "Performs an Nmap scan to discover open ports and services."

    @property
    def requires(self) -> list[str]:
        return ["validated_subdomains"]

    @property
    def provides(self) -> list[str]:
        return ["open_ports", "services"]

    def run(self, context: ScanContext):
        subdomains = context.get("validated_subdomains")
        if not subdomains:
            log.info("No validated subdomains found, skipping Nmap scan.")
            return

        log.info(f"Running Nmap scan on {len(subdomains)} subdomains.")
        open_ports: Dict[str, Any] = context.get("open_ports", {})
        services: Dict[str, Any] = context.get("services", {})

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp_file:
            for subdomain in subdomains:
                tmp_file.write(subdomain + '\n')
            target_file = tmp_file.name

        try:
            # -sV: Probe open ports to determine service/version info
            # -oX -: Output scan in XML format to stdout
            # -iL: Input from list of hosts/networks
            # --open: Only show open (or possibly open) ports
            command = [
                "nmap",
                "-sV",
                "-oX",
                "-",
                "-iL",
                target_file,
                "--open"
            ]
            result = subprocess.run(command, capture_output=True, text=True, check=True)

            tree = ET.fromstring(result.stdout)

            for host in tree.findall('host'):
                ip_address = host.find('address').get('addr')
                hostname_element = host.find('hostnames/hostname')
                hostname = hostname_element.get('name') if hostname_element is not None else ip_address

                if hostname not in open_ports:
                    open_ports[hostname] = []
                if hostname not in services:
                    services[hostname] = []

                for port in host.findall('ports/port'):
                    port_id = int(port.get('portid'))
                    state = port.find('state').get('state')
                    if state == 'open':
                        open_ports[hostname].append(port_id)

                        service_info = {}
                        service_element = port.find('service')
                        if service_element is not None:
                            service_info['port'] = port_id
                            service_info['name'] = service_element.get('name', 'unknown')
                            service_info['product'] = service_element.get('product', '')
                            service_info['version'] = service_element.get('version', '')
                            service_info['extrainfo'] = service_element.get('extrainfo', '')
                            services[hostname].append(service_info)

            log.info(f"Nmap scan completed. Found open ports on {len(open_ports)} hosts.")

        except FileNotFoundError:
            log.error("nmap not found. Please ensure it is installed and in your PATH.")
        except subprocess.CalledProcessError as e:
            log.error(f"Nmap scan failed: {e.stderr}")
        except ET.ParseError as e:
            log.error(f"Failed to parse Nmap XML output: {e}")
        finally:
            os.remove(target_file)
            context.set("open_ports", open_ports)
            context.set("services", services)
