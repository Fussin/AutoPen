import logging
from typing import Dict, Any
from ..validation_engine import ValidationHandler

log = logging.getLogger(__name__)


class ContextualValidator(ValidationHandler):
    """
    A validation handler that uses contextual information to reduce false positives.
    """

    def validate(self, finding: Dict[str, Any]) -> bool:
        """
        Performs validation based on the finding's context.
        This handler is meant to be a generic, last-pass validator.
        It returns True if the finding seems legitimate, and False if it is likely a false positive.
        """
        # Example 1: If a "critical" vulnerability is on a non-routable IP, it might be a misconfiguration or a low-impact finding.
        # This is a simple check, a real implementation would be more robust.
        if finding.get('severity') == 'Critical' and self._is_internal_ip(finding.get('host')):
            log.info(f"Finding {finding.get('id')} is on an internal IP. Downgrading confidence.")
            # This doesn't necessarily mean it's a false positive, but it's a good signal to lower the confidence.
            # For the purpose of this example, we'll return False to flag it for review.
            return False

        # Example 2: If the pattern analysis engine flagged this as an anomaly, it might be a false positive.
        if finding.get('is_anomaly'):
            log.info(f"Finding {finding.get('id')} was flagged as an anomaly. Marking as potential false positive.")
            return False

        # If no specific contextual red flags are found, assume it's valid for now.
        return True

    def _is_internal_ip(self, ip_address: str) -> bool:
        """
        Checks if an IP address is in a private range.
        """
        if not ip_address:
            return False
        private_ip_ranges = [
            ('10.0.0.0', '10.255.255.255'),
            ('172.16.0.0', '172.31.255.255'),
            ('192.168.0.0', '192.168.255.255'),
            ('127.0.0.0', '127.255.255.255')
        ]
        try:
            ip_addr = list(map(int, ip_address.split('.')))
            for start, end in private_ip_ranges:
                start_addr = list(map(int, start.split('.')))
                end_addr = list(map(int, end.split('.')))
                if all(start_addr[i] <= ip_addr[i] <= end_addr[i] for i in range(4)):
                    return True
        except (ValueError, IndexError):
            # Not a valid IPv4 address
            return False
        return False
