import logging
from typing import Dict, Any
from ..validation_engine import ValidationHandler

log = logging.getLogger(__name__)


class ContextualValidator(ValidationHandler):
    """
    A validation handler that uses contextual information to reduce false positives.
    """

    def __init__(self):
        """
        Initializes the ContextualValidator with a mapping of vulnerability signatures
        to the technologies they are associated with.
        """
        self.tech_map = {
            "apache-struts-rce": "Struts",
            "joomla-rce": "Joomla",
            "wordpress-plugin-xss": "WordPress",
            "confluence-cve-2021-26084": "Confluence",
            "Apache Log4j RCE": "Log4j",
        }

    def validate(self, finding: Dict[str, Any]) -> bool:
        """
        Performs validation based on the finding's context.
        Returns True if the finding seems legitimate, and False if it is likely a false positive.
        """
        # 1. Technology Mismatch Check
        finding_signature = self._get_finding_signature(finding)
        required_tech = self.tech_map.get(finding_signature)
        host_techs = finding.get("technologies", [])

        if required_tech and required_tech not in host_techs:
            log.info(f"Finding '{finding_signature}' is likely a false positive. Requires '{required_tech}', but host has: {host_techs}")
            return False

        # 2. Internal IP Check
        if finding.get('severity') == 'Critical' and self._is_internal_ip(finding.get('host')):
            log.info(f"Finding {finding.get('id', '')} is on an internal IP. Downgrading confidence.")
            return False

        # 3. Anomaly Check
        if finding.get('is_anomaly'):
            log.info(f"Finding {finding.get('id', '')} was flagged as an anomaly. Marking as potential false positive.")
            return False

        return True

    def _get_finding_signature(self, finding: Dict[str, Any]) -> str:
        """Extracts a consistent signature from a finding."""
        if 'template-id' in finding: # From Nuclei
            return finding['template-id']
        return finding.get('vulnerability_name', '')

    def _is_internal_ip(self, ip_address: str) -> bool:
        """Checks if an IP address is in a private range."""
        if not ip_address:
            return False
        private_ip_ranges = [
            ('10.0.0.0', '10.255.255.255'),
            ('172.16.0.0', '172.31.255.255'),
            ('192.168.0.0', '192.168.255.255'),
            ('127.0.0.0', '127.255.255.255')
        ]
        try:
            if not all(c.isdigit() or c == '.' for c in ip_address):
                return False # Not a simple IP address
            ip_addr = list(map(int, ip_address.split('.')))
            for start, end in private_ip_ranges:
                start_addr = list(map(int, start.split('.')))
                end_addr = list(map(int, end.split('.')))
                if all(start_addr[i] <= ip_addr[i] <= end_addr[i] for i in range(4)):
                    return True
        except (ValueError, IndexError):
            return False
        return False
