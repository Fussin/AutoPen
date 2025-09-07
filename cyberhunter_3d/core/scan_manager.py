import json
from pathlib import Path
from cyberhunter_3d.web.models import db, Scan, Target, Asset, Vulnerability
from cyberhunter_3d.core.reconnaissance.subdomain_enum import enumerate_subdomains_v2
from cyberhunter_3d.core.reconnaissance.ip_scan import scan_ip_target
from cyberhunter_3d.plugins.vulnerability.nuclei import run_nuclei_scan
from cyberhunter_3d.plugins.recon.gospider import run_gospider_scan
from cyberhunter_3d.core.reconnaissance.asn_lookup import get_cidrs_for_asn
from cyberhunter_3d.core.reconnaissance.org_lookup import get_assets_for_org
from cyberhunter_3d.core.reconnaissance.reverse_dns import get_hostnames_for_ips
from cyberhunter_3d.core.reconnaissance.analytics_correlation import find_related_domains_by_analytics
from cyberhunter_3d.core.scope_validator import ScopeValidator
from cyberhunter_3d.core.decision_tree import DecisionTree
from .output_manager import OutputManager
from .post_scan_operations import run_post_scan_operations
from cyberhunter_3d.core.analysis.prioritization_engine import prioritize_vulnerabilities
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=2)

def run_discovery_phase(scan_id, app):
    """
    Performs the initial discovery and expansion phases of a scan using the DecisionTree.
    """
    with app.app_context():
        scan = db.session.get(Scan, scan_id)
        if not scan:
            print(f"Error: Scan {scan_id} not found for discovery phase.")
            return

        om = None
        try:
            # 1. Initialization
            scan.status = 'RUNNING'
            om = OutputManager.create_for_timestamp(Path("scan_results"))
            scan.output_dir = str(om.base_dir)
            db.session.commit()
            print(f"Scan {scan_id} discovery phase started. Output at: {scan.output_dir}")

            # 2. Use DecisionTree to process targets
            decision_tree = DecisionTree(scan_id, app)
            initial_targets = list(scan.targets)
            for target in initial_targets:
                decision_tree.process_target(target)

            # 3. Write discovery results to files
            subdomains = [a['value'] for a in decision_tree.discovered_assets if a['type'] == 'subdomain']
            dns_records = {}
            alive_subdomains = []
            dead_subdomains = []
            for s in subdomains:
                ips = decision_tree._is_subdomain_alive(s)
                if ips:
                    alive_subdomains.append(s)
                    dns_records[s] = list(ips)
                else:
                    dead_subdomains.append(s)

            om.write_recon_file("Subdomain.txt", "\n".join(subdomains))
            om.write_recon_file("subdomains_alive.txt", "\n".join(alive_subdomains))
            om.write_recon_file("subdomains_dead.txt", "\n".join(dead_subdomains))
            om.write_recon_file("dns_records.json", json.dumps(dns_records, indent=2))

            # 4. Persist the results from the DecisionTree
            in_scope_count, out_of_scope_count = decision_tree.persist_discovered_assets()
            scan.results = f"Discovery phase complete. Found {in_scope_count} new assets. Skipped {out_of_scope_count} out-of-scope items."
            db.session.commit()

            # 5. Auto-Approval Phase
            print(f"AUTONOMOUS_MODE: Starting auto-approval for scan {scan_id}...")
            validator = ScopeValidator(scan.in_scope_rules, scan.out_of_scope_rules)
            unapproved_assets = Asset.query.filter_by(scan_id=scan.id, is_approved_for_scan=False).all()
            approved_count = 0
            for asset in unapproved_assets:
                if validator.is_in_scope(asset.value):
                    asset.is_approved_for_scan = True
                    approved_count += 1

            db.session.commit()
            print(f"AUTONOMOUS_MODE: Auto-approved {approved_count} assets.")

            # 6. Chain to Execution Phase
            print(f"AUTONOMOUS_MODE: Chaining scan {scan_id} to execution phase.")
            executor.submit(run_execution_phase, scan_id, app)

        except Exception as e:
            print(f"FATAL: Error in discovery phase for scan {scan_id}: {e}")
            scan.status = 'FAILED'
            scan.results = f"Discovery failed with error: {e}"
        finally:
            db.session.commit()
            print(f"Final discovery status for scan {scan_id} is {scan.status}.")


class VulnerabilityScanningPhase:
    """
    Encapsulates the logic for the vulnerability scanning phase.
    """
    def __init__(self, scan_id, app, output_manager):
        self.scan_id = scan_id
        self.app = app
        self.om = output_manager
        self.scan = db.session.get(Scan, self.scan_id)
        self.nuclei_output_dir = self.om.base_dir / "nuclei"
        self.nuclei_output_dir.mkdir(exist_ok=True)

    def run(self):
        """
        Runs the vulnerability scanning process using Nuclei.
        """
        print("Starting Vulnerability Scanning Phase...")

        self._run_url_discovery()

        web_targets = self._get_web_targets()
        if not web_targets:
            print("No web targets found to scan.")
            return

        nuclei_findings = self._run_nuclei_on_targets(web_targets)
        if nuclei_findings:
            self._save_nuclei_findings(nuclei_findings)

        print("Vulnerability Scanning Phase complete.")

    def _run_url_discovery(self):
        """
        Runs gospider to discover URLs for all approved web assets.
        """
        print("URL_DISCOVERY: Starting URL discovery...")
        # Get approved subdomains and domains to use as a base for crawling
        base_targets = Asset.query.filter(
            Asset.scan_id == self.scan_id,
            Asset.is_approved_for_scan == True,
            Asset.type.in_(['subdomain', 'domain'])
        ).all()

        all_discovered_urls = set()
        for asset in base_targets:
            # We should ideally use httpx to find live http/https services first
            # For now, we'll just try https
            site_url = f"https://{asset.value}"
            discovered_urls = run_gospider_scan(site_url)
            for url in discovered_urls:
                all_discovered_urls.add(url)

        print(f"URL_DISCOVERY: Found {len(all_discovered_urls)} unique URLs.")

        # Save the discovered URLs as new assets
        for url in all_discovered_urls:
            # Avoid adding duplicates
            if not Asset.query.filter_by(scan_id=self.scan_id, value=url).first():
                new_asset = Asset(
                    type='url',
                    value=url,
                    scan_id=self.scan_id,
                    is_approved_for_scan=True # URLs from in-scope assets are also in-scope
                )
                db.session.add(new_asset)

        db.session.commit()
        print(f"URL_DISCOVERY: Saved new URL assets to the database.")

    def _get_web_targets(self) -> list[tuple[Asset, str]]:
        """
        Gets all assets of type 'url' to be scanned by Nuclei.
        Returns a list of tuples, where each tuple contains the Asset object and the URL.
        """
        targets = []
        # Query for all approved URLs discovered by gospider
        url_assets = Asset.query.filter(
            Asset.scan_id == self.scan_id,
            Asset.is_approved_for_scan == True,
            Asset.type == 'url'
        ).all()

        for asset in url_assets:
            targets.append((asset, asset.value))

        print(f"Found {len(targets)} URLs for Nuclei scanning.")
        return targets

    def _run_nuclei_on_targets(self, targets: list[tuple[Asset, str]]) -> list[dict]:
        """
        Runs Nuclei on a list of target URLs.
        """
        all_findings = []
        for asset, url in targets:
            findings = run_nuclei_scan(url, self.nuclei_output_dir)
            # Add asset context to each finding for later use
            for finding in findings:
                finding['asset_id'] = asset.id
            all_findings.extend(findings)
        return all_findings

    def _save_nuclei_findings(self, findings: list[dict]):
        """
        Parses Nuclei's JSON output and saves it to the database.
        """
        print(f"Saving {len(findings)} findings to the database...")
        for finding in findings:
            info = finding.get('info', {})

            # Create a new Vulnerability object
            new_vulnerability = Vulnerability(
                title=info.get('name', 'N/A'),
                severity=info.get('severity', 'unknown'),
                description=info.get('description', 'No description provided.'),
                evidence={
                    'host': finding.get('host'),
                    'matched-at': finding.get('matched-at'),
                    'template': finding.get('template'),
                    'curl-command': finding.get('curl-command'),
                    'matcher-name': finding.get('matcher-name'),
                },
                scan_id=self.scan_id,
                asset_id=finding.get('asset_id')
            )

            # Add to session and commit
            db.session.add(new_vulnerability)
            self.om.add_vulnerability(finding, severity=info.get('severity', 'unknown'))

        db.session.commit()
        print("Successfully saved findings.")


class ExpansionPhase:
    """
    Encapsulates the logic for the asset expansion phase.
    """
    def __init__(self, scan_id, app, output_manager):
        self.scan_id = scan_id
        self.app = app
        self.om = output_manager
        self.scan = db.session.get(Scan, self.scan_id)
        self.validator = ScopeValidator(self.scan.in_scope_rules, self.scan.out_of_scope_rules)
        self.out_of_scope_count = 0

    def run(self):
        print("Starting Expansion Phase...")
        self._run_reverse_dns()
        self._run_analytics_correlation()
        print("Expansion Phase complete.")

    def _run_reverse_dns(self):
        print("Starting Expansion: Reverse DNS")
        ip_assets = Asset.query.filter(Asset.scan_id == self.scan_id, Asset.type == 'host_with_open_ports').all()
        unique_ips = list(set(asset.value for asset in ip_assets))
        rdns_found_count = 0
        if unique_ips:
            hostnames = get_hostnames_for_ips(unique_ips)
            self.om.write_discovery_file("reverse_dns_results.txt", "\n".join(hostnames))
            for hostname in hostnames:
                self.om.add_asset({'type': 'subdomain', 'value': hostname})
                if self.validator.is_in_scope(hostname) and not Asset.query.filter_by(scan_id=self.scan_id, value=hostname).first():
                    db.session.add(Asset(type='subdomain', value=hostname, scan_id=self.scan_id))
                    rdns_found_count += 1
                elif not self.validator.is_in_scope(hostname):
                    self.out_of_scope_count += 1
        print(f"rDNS complete. Found {rdns_found_count} new hostnames.")
        db.session.commit()

    def _run_analytics_correlation(self):
        print("Starting Expansion: Analytics Correlation")
        domain_assets = Asset.query.filter(Asset.scan_id == self.scan_id, Asset.is_approved_for_scan == True, Asset.type.in_(['domain', 'subdomain'])).all()
        unique_domains = list(set(asset.value for asset in domain_assets))
        analytics_found_count = 0
        if unique_domains:
            related_domains = find_related_domains_by_analytics(unique_domains)
            self.om.write_discovery_file("analytics_correlation_results.txt", "\n".join(related_domains))
            for domain in related_domains:
                self.om.add_asset({'type': 'subdomain', 'value': domain})
                if self.validator.is_in_scope(domain) and not Asset.query.filter_by(scan_id=self.scan_id, value=domain).first():
                    db.session.add(Asset(type='subdomain', value=domain, scan_id=self.scan_id))
                    analytics_found_count += 1
                elif not self.validator.is_in_scope(domain):
                    self.out_of_scope_count += 1
        print(f"Analytics complete. Found {analytics_found_count} new domains.")
        db.session.commit()

def run_execution_phase(scan_id, app):
    """
    Performs the intensive execution phase of a scan on assets that have
    already been discovered and approved.
    """
    with app.app_context():
        scan = db.session.get(Scan, scan_id)
        if not scan:
            print(f"Error: Scan {scan_id} not found for execution phase.")
            return

        om = None
        try:
            scan.status = 'RUNNING'
            db.session.commit()
            print(f"Scan {scan_id} execution phase started.")

            if not scan.output_dir:
                print(f"Error: scan.output_dir not set for scan {scan_id}. Cannot create reports.")
                om = OutputManager.create_for_timestamp(Path("scan_results"))
                scan.output_dir = str(om.base_dir)
            else:
                om = OutputManager(Path(scan.output_dir))

            # 1. Vulnerability Scanning
            vuln_scanning_phase = VulnerabilityScanningPhase(scan_id, app, om)
            vuln_scanning_phase.run()

            # 2. Prioritization
            prioritize_vulnerabilities(scan_id)

            # 3. Expansion
            expansion_phase = ExpansionPhase(scan_id, app, om)
            expansion_phase.run()

            # 4. Finalize Scan
            final_asset_count = Asset.query.filter_by(scan_id=scan.id).count()
            scan.results = f"Execution phase complete. Total assets: {final_asset_count}. See output directory for details."
            scan.status = 'COMPLETED'
            db.session.commit()
            print(f"Scan {scan_id} execution phase complete.")

            # Populate OutputManager with all assets from the scan for reporting
            all_db_assets = Asset.query.filter_by(scan_id=scan.id).all()
            for asset in all_db_assets:
                om.add_asset({'type': asset.type, 'value': asset.value, 'details': asset.details})

            # Run post-scan operations in the finally block to ensure they always run
            # run_post_scan_operations(scan_id, app, om)

        except Exception as e:
            print(f"FATAL: Error in execution phase for scan {scan_id}: {e}")
            scan.status = 'FAILED'
            scan.results = f"Execution failed with error: {e}"
        finally:
            if om:
                om.produce_metadata()
                # Run post-scan operations after everything else is complete
                run_post_scan_operations(scan_id, app, om)
            db.session.commit()
            print(f"Final execution status for scan {scan_id} is {scan.status}.")
