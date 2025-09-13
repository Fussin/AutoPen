# You no longer need to pass the app object around
from .core.scan_manager import run_discovery_phase
from .extensions import celery_app

@celery_app.task(name="run_scan_discovery")
def run_discovery_task(scan_id: int):
    """
    Celery task to run the discovery phase of a scan.
    The FlaskTask class we defined earlier automatically provides the app context.
    """
    print(f"Starting discovery task for scan ID: {scan_id}")
    run_discovery_phase(scan_id)
    print(f"Finished discovery task for scan ID: {scan_id}")

# You can define other tasks here, e.g., for the execution phase
# @celery_app.task(name="run_scan_execution")
# def run_execution_task(scan_id: int):
#     run_execution_phase(scan_id)

from .web.models import db, Finding, Asset, Scan
from .plugins.recon.subfinder import SubfinderPlugin

def process_and_save_findings(scan_id, asset_id, tool_results):
    for result in tool_results:
        new_finding = Finding(
            scan_id=scan_id,
            asset_id=asset_id,
            tool_name=result['tool'],
            type=result.get('type', 'generic_finding'),
            severity=result.get('severity'),
            details=result['evidence']
        )
        db.session.add(new_finding)
    db.session.commit()

@celery_app.task
def run_subfinder_task(scan_id, asset_id, target_domain):
    asset = db.session.get(Asset, asset_id)
    if not asset:
        return

    plugin = SubfinderPlugin()
    # This assumes the plugin returns a list of standardized dicts
    results = plugin.run([target_domain])
    process_and_save_findings(scan_id, asset_id, results)

@celery_app.task
def run_correlation_engine(scan_id):
    # 1. Fetch all findings for this scan
    findings = Finding.query.filter_by(scan_id=scan_id).all()

    # 2. De-duplicate findings (Example: multiple tools found the same port)
    unique_ports = {(f.asset_id, f.details.get('port')) for f in findings if f.type == 'open_port'}
    print(f"Found {len(unique_ports)} unique open ports.")

    # 3. Correlate findings to identify attack paths (Example Logic)
    alerts = []
    vulnerabilities = [f for f in findings if f.type == 'vulnerability' and f.severity in ['High', 'Critical']]

    for vuln in vulnerabilities:
        # Find the asset this vulnerability belongs to
        asset = db.session.get(Asset, vuln.asset_id)

        # Check if this asset is externally accessible (e.g., has an open port)
        has_open_port = any(
            f.asset_id == asset.id and f.type == 'open_port' for f in findings
        )

        if has_open_port:
            alert_message = (
                f"High-Priority Alert: Externally accessible asset '{asset.value}' "
                f"has a critical vulnerability: '{vuln.details.get('name')}' found by {vuln.tool_name}."
            )
            alerts.append(alert_message)
            # Here you would save this to a new 'Alert' table in the DB

    # 4. Store the results
    scan = db.session.get(Scan, scan_id)
    scan.results = "\n".join(alerts)
    db.session.commit()
