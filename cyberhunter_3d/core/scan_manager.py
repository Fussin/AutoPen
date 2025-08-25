from cyberhunter_3d.web.models import db, Scan, Target, Asset
from cyberhunter_3d.core.reconnaissance.subdomain_enum import enumerate_subdomains
from cyberhunter_3d.core.reconnaissance.ip_scan import scan_ip_target
from cyberhunter_3d.core.reconnaissance.asn_lookup import get_cidrs_for_asn
from cyberhunter_3d.core.reconnaissance.org_lookup import get_assets_for_org
from cyberhunter_3d.core.scope_validator import ScopeValidator

def run_scan(scan_id, app):
    """
    The core function that executes a scan. It dispatches targets to recon
    modules, validates the findings, and persists them to the database
    as structured Asset objects.
    """
    with app.app_context():
        scan = Scan.query.get(scan_id)
        if not scan:
            print(f"Error: Scan with id {scan_id} not found.")
            return

        try:
            # 1. Initialization
            scan.status = 'RUNNING'
            db.session.commit()
            print(f"Scan {scan_id} started. Initializing validator.")
            validator = ScopeValidator(scan.in_scope_rules, scan.out_of_scope_rules)

            # Prepare for processing
            discovered_assets = []
            out_of_scope_count = 0
            targets_to_scan = list(scan.targets)

            # 2. Expansion and Discovery Loop
            i = 0
            while i < len(targets_to_scan):
                target = targets_to_scan[i]
                i += 1

                if target.type == 'asn':
                    print(f"Expanding ASN: AS{target.value}")
                    cidrs = get_cidrs_for_asn(target.value)
                    for asset_data in cidrs:
                        targets_to_scan.append(Target(value=asset_data['value'], type=asset_data['type']))
                    continue

                elif target.type == 'org_name':
                    print(f"Expanding Organization: {target.value}")
                    assets = get_assets_for_org(target.value)
                    for asset_data in assets:
                        targets_to_scan.append(Target(value=asset_data['value'], type=asset_data['type']))
                    continue

                elif target.type in ['domain', 'wildcard_domain']:
                    print(f"Finding subdomains for '{target.value}'...")
                    assets = enumerate_subdomains(target.value)
                    discovered_assets.extend(assets)

                elif target.type in ['ip_address', 'cidr']:
                    print(f"Scanning IP/CIDR '{target.value}'...")
                    assets = scan_ip_target(target.value)
                    discovered_assets.extend(assets)
                else:
                    print(f"Skipping target with unknown type: {target.type}")

            # 3. Validation and Persistence
            print(f"Validating and persisting {len(discovered_assets)} discovered assets...")
            in_scope_count = 0
            for asset_data in discovered_assets:
                if validator.is_in_scope(asset_data['value']):
                    new_asset = Asset(
                        type=asset_data['type'],
                        value=asset_data['value'],
                        details=asset_data.get('details'),
                        scan_id=scan.id
                    )
                    db.session.add(new_asset)
                    in_scope_count += 1
                else:
                    out_of_scope_count += 1

            # 4. Finalize Scan
            summary = (
                f"Scan complete. Found {in_scope_count} in-scope assets. "
                f"Skipped {out_of_scope_count} out-of-scope assets."
            )
            scan.results = summary
            scan.status = 'COMPLETED'
            print(summary)

        except Exception as e:
            print(f"FATAL: Error running scan {scan_id}: {e}")
            scan.status = 'FAILED'
            scan.results = f"Scan failed with error: {e}"

        finally:
            # Commit all changes: status, assets, results
            db.session.commit()
            print(f"Final status for scan {scan_id} is {scan.status}.")
