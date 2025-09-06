import json
from pathlib import Path
from cyberhunter_3d.web.models import db, Scan, Target, Asset
from cyberhunter_3d.core.reconnaissance.subdomain_enum import enumerate_subdomains_v2
from cyberhunter_3d.core.reconnaissance.ip_scan import scan_ip_target
from cyberhunter_3d.core.reconnaissance.asn_lookup import get_cidrs_for_asn
from cyberhunter_3d.core.reconnaissance.org_lookup import get_assets_for_org
from cyberhunter_3d.core.reconnaissance.reverse_dns import get_hostnames_for_ips
from cyberhunter_3d.core.reconnaissance.analytics_correlation import find_related_domains_by_analytics
from cyberhunter_3d.core.scope_validator import ScopeValidator
from cyberhunter_3d.core.decision_tree import DecisionTree
from .output_manager import OutputManager


def run_discovery_phase(scan_id, app):
    """
    Performs the initial discovery and expansion phases of a scan using the DecisionTree.
    """
    with app.app_context():
        scan = Scan.query.get(scan_id)
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

            # 5. Finalize Discovery Phase
            scan.results = f"Discovery phase complete. Found {in_scope_count} new assets. Skipped {out_of_scope_count} out-of-scope items."
            scan.status = 'PENDING_REVIEW'
            print(f"Scan {scan_id} discovery phase complete.")

        except Exception as e:
            print(f"FATAL: Error in discovery phase for scan {scan_id}: {e}")
            scan.status = 'FAILED'
            scan.results = f"Discovery failed with error: {e}"
        finally:
            if om:
                om.produce_metadata()
            db.session.commit()
            print(f"Final discovery status for scan {scan_id} is {scan.status}.")


def run_execution_phase(scan_id, app):
    """
    Performs the intensive execution phase of a scan on assets that have
    already been discovered and approved.
    """
    with app.app_context():
        scan = Scan.query.get(scan_id)
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

            validator = ScopeValidator(scan.in_scope_rules, scan.out_of_scope_rules)
            out_of_scope_count = 0

            # 1. Port Scanning and Simulated Vulnerability Reporting
            ip_targets = Asset.query.filter(Asset.scan_id == scan.id, Asset.is_approved_for_scan == True, Asset.type.in_(['ip_address', 'cidr'])).all()
            all_ports_data = []
            vuln_id_counter = 1
            for target in ip_targets:
                print(f"Port scanning '{target.value}'...")
                ip_scan_assets = scan_ip_target(target.value)
                for asset_data in ip_scan_assets:
                    all_ports_data.append(asset_data)
                    if not Asset.query.filter_by(scan_id=scan.id, type=asset_data['type'], value=asset_data['value']).first():
                        db.session.add(Asset(type=asset_data['type'], value=asset_data['value'], details=asset_data.get('details'), scan_id=scan.id))

                    # This is a simulation of vulnerability reporting.
                    # In a real application, a vulnerability scanner would be used here.
                    port_info = asset_data.get('details', {})
                    port = port_info.get('port', 'N/A')
                    om.add_vulnerability({
                        "id": f"VULN-{scan.id}-{vuln_id_counter}",
                        "title": f"Informational: Port {port} Open on {target.value}",
                        "description": f"An open port ({port}) was discovered on host {target.value}. This is for informational purposes and should be reviewed to ensure it is expected.",
                        "severity": "informational",
                        "evidence": {"host": target.value, "port": port, "protocol": port_info.get('protocol', 'tcp')}
                    }, severity="informational")
                    vuln_id_counter += 1

            om.write_network_json("open_ports.json", all_ports_data)
            om.write_network_json("services.json", {})
            om.write_network_json("ssl_issues.json", {})

            om.write_discovery_file("Way_kat.txt", "# Data from Wayback Machine / Katana - Not yet implemented\n")
            om.write_discovery_file("api_endpoints.json", "[] # API endpoints - Not yet implemented\n")
            om.write_discovery_file("parameters.json", "[] # Discovered parameters - Not yet implemented\n")
            om.write_discovery_file("javascript_files.txt", "# Discovered Javascript files - Not yet implemented\n")

            db.session.commit()

            # 2. Expansion Phase (Reverse DNS)
            print("Starting Expansion: Reverse DNS")
            ip_assets = Asset.query.filter(Asset.scan_id == scan.id, Asset.type == 'host_with_open_ports').all()
            unique_ips = list(set(asset.value for asset in ip_assets))
            rdns_found_count = 0
            if unique_ips:
                hostnames = get_hostnames_for_ips(unique_ips)
                om.write_discovery_file("reverse_dns_results.txt", "\n".join(hostnames))
                for hostname in hostnames:
                    if validator.is_in_scope(hostname) and not Asset.query.filter_by(scan_id=scan.id, value=hostname).first():
                        db.session.add(Asset(type='subdomain', value=hostname, scan_id=scan.id))
                        rdns_found_count += 1
                    elif not validator.is_in_scope(hostname):
                        out_of_scope_count += 1
            print(f"rDNS complete. Found {rdns_found_count} new hostnames.")
            db.session.commit()

            # 3. Expansion Phase (Analytics Correlation)
            print("Starting Expansion: Analytics Correlation")
            domain_assets = Asset.query.filter(Asset.scan_id == scan.id, Asset.is_approved_for_scan == True, Asset.type.in_(['domain', 'subdomain'])).all()
            unique_domains = list(set(asset.value for asset in domain_assets))
            analytics_found_count = 0
            if unique_domains:
                related_domains = find_related_domains_by_analytics(unique_domains)
                om.write_discovery_file("analytics_correlation_results.txt", "\n".join(related_domains))
                for domain in related_domains:
                    if validator.is_in_scope(domain) and not Asset.query.filter_by(scan_id=scan.id, value=domain).first():
                        db.session.add(Asset(type='subdomain', value=domain, scan_id=scan.id))
                        analytics_found_count += 1
                    elif not validator.is_in_scope(domain):
                        out_of_scope_count += 1
            print(f"Analytics complete. Found {analytics_found_count} new domains.")

            # 4. Finalize Scan
            final_asset_count = Asset.query.filter_by(scan_id=scan.id).count()
            scan.results = f"Execution phase complete. Total assets: {final_asset_count}. See output directory for details."
            scan.status = 'COMPLETED'
            print(f"Scan {scan_id} execution phase complete.")


            # Run post-scan operations
            run_post_scan_operations(scan_id, app, om)

        except Exception as e:
            print(f"FATAL: Error in execution phase for scan {scan_id}: {e}")
            scan.status = 'FAILED'
            scan.results = f"Execution failed with error: {e}"
        finally:
            if om:
                summary = om.finalize(generate_pdf=True, generate_docx=True)
                print("Generated reports summary:", summary)
            db.session.commit()
            print(f"Final execution status for scan {scan_id} is {scan.status}.")
