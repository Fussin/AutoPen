import socket
import uuid
from collections import namedtuple

from cyberhunter_3d.web.models import db, Asset, Scan
from cyberhunter_3d.core.reconnaissance.subdomain_enum import enumerate_subdomains_v2
from cyberhunter_3d.core.reconnaissance.ip_scan import scan_ip_target
from cyberhunter_3d.core.reconnaissance.asn_lookup import get_cidrs_for_asn
from cyberhunter_3d.core.reconnaissance.org_lookup import get_assets_for_org
from cyberhunter_3d.core.scope_validator import ScopeValidator
from cyberhunter_3d.common.log import get_rich_logger

logger = get_rich_logger(__name__)


class DecisionTree:
    """
    The DecisionTree class orchestrates the reconnaissance process based on the
    type of initial targets provided. It acts as the central logic for the
    discovery phase of a scan.
    """

    def __init__(self, scan_id, app):
        self.scan_id = scan_id
        self.app = app
        with self.app.app_context():
            scan = db.session.get(Scan, self.scan_id)
            if not scan:
                # Use logger for errors that might occur
                logger.error(f"Scan with ID {self.scan_id} not found during DecisionTree initialization.")
                raise ValueError(f"Scan with ID {self.scan_id} not found.")
            self.scan = scan
            self.validator = ScopeValidator(scan.in_scope_rules, scan.out_of_scope_rules)
            self.discovered_assets = []
            self.wildcard_ips = self._check_wildcard(self.scan.targets[0].value) if self.scan.targets else set()

    def process_target(self, target):
        logger.info(f"Processing target: [bold cyan]{target.value}[/] ({target.type})")
        if target.type in ['domain', 'wildcard_domain']:
            self._handle_domain(target)
        elif target.type in ['ip_address', 'cidr']:
            self._handle_ip(target)
        elif target.type == 'asn':
            self._handle_asn(target)
        elif target.type == 'org_name':
            self._handle_org(target)
        else:
            logger.warning(f"Unknown target type '{target.type}' for value '{target.value}'")

    def _is_subdomain_alive(self, subdomain):
        try:
            ips = socket.gethostbyname_ex(subdomain)[2]
            return {ip for ip in ips if ip not in self.wildcard_ips}
        except socket.gaierror:
            return set()

    def _check_wildcard(self, domain):
        random_subdomain = f"{uuid.uuid4().hex[:10]}.{domain}"
        try:
            wildcard_ips = set(socket.gethostbyname_ex(random_subdomain)[2])
            logger.info(f"Detected wildcard DNS for [bold cyan]{domain}[/]: {wildcard_ips}")
            return wildcard_ips
        except socket.gaierror:
            return set()

    def _handle_domain(self, target):
        logger.info(f"-> Domain path: Enumerating subdomains for [bold cyan]{target.value}[/]")
        subdomains = enumerate_subdomains_v2(target.value)
        for sub in subdomains:
            self._handle_subdomain(sub['value'])

    def _handle_subdomain(self, subdomain_value):
        logger.debug(f"  -> Subdomain Found: {subdomain_value}")
        alive_ips = self._is_subdomain_alive(subdomain_value)
        if alive_ips:
            logger.info(f"    -> [green]Alive[/]: {subdomain_value} -> {alive_ips}. Adding to queue.")
            self.discovered_assets.append({'type': 'subdomain', 'value': subdomain_value})
            for ip in alive_ips:
                self.discovered_assets.append({'type': 'ip_address', 'value': ip})
        else:
            logger.debug(f"    -> [red]Dead[/]: {subdomain_value}. Marking as dead, checking for takeover.")
            # Placeholder for takeover logic
            pass

    def _handle_ip(self, target):
        logger.info(f"-> IP path: Queuing [bold cyan]{target.value}[/] for direct scanning.")
        self.discovered_assets.append({'type': target.type, 'value': target.value})

    def _handle_asn(self, target):
        logger.info(f"-> ASN path: Expanding ASN [bold cyan]{target.value}[/] to CIDRs.")
        cidrs = get_cidrs_for_asn(target.value)
        for cidr_data in cidrs:
            TempTarget = namedtuple('TempTarget', ['value', 'type'])
            new_target = TempTarget(value=cidr_data['value'], type=cidr_data['type'])
            self.process_target(new_target)

    def _handle_org(self, target):
        logger.info(f"-> Org path: Expanding Org '[bold cyan]{target.value}[/]' to assets.")
        assets = get_assets_for_org(target.value)
        for asset_data in assets:
            TempTarget = namedtuple('TempTarget', ['value', 'type'])
            new_target = TempTarget(value=asset_data['value'], type=asset_data['type'])
            self.process_target(new_target)

    def _handle_url(self, url_info):
        logger.info(f"  -> URL Discovered: [bold blue]{url_info['value']}[/]")
        # Placeholder for URL processing logic
        pass

    def persist_discovered_assets(self):
        logger.info(f"Persisting {len(self.discovered_assets)} discovered assets...")
        in_scope_count = 0
        out_of_scope_count = 0
        with self.app.app_context():
            unique_assets = { (a['type'], a['value']) for a in self.discovered_assets }
            for asset_type, asset_value in unique_assets:
                if self.validator.is_in_scope(asset_value):
                    if not Asset.query.filter_by(scan_id=self.scan_id, type=asset_type, value=asset_value).first():
                        db.session.add(Asset(type=asset_type, value=asset_value, scan_id=self.scan_id))
                        in_scope_count += 1
                else:
                    out_of_scope_count += 1
            db.session.commit()
        logger.info(f"Persisted {in_scope_count} new in-scope assets. Skipped {out_of_scope_count} out-of-scope assets.")
        return in_scope_count, out_of_scope_count
