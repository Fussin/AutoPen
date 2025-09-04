from functools import wraps
from flask import Blueprint, request, jsonify
from .models import User, db, Scan, Target, Asset
from cyberhunter_3d.core.target_parser import parse_targets
from cyberhunter_3d.core.scan_manager import run_discovery_phase
from concurrent.futures import ThreadPoolExecutor
from flask import current_app

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({'error': 'API key is missing'}), 401
        user = User.query.filter_by(api_key=api_key).first()
        if not user:
            return jsonify({'error': 'Invalid API key'}), 401
        return f(*args, **kwargs)
    return decorated_function

def get_executor():
    return current_app.executor

@api_bp.route('/ping')
@require_api_key
def ping():
    return jsonify({'message': 'pong'})

@api_bp.route('/scans', methods=['GET'])
@require_api_key
def get_scans():
    user = User.query.filter_by(api_key=request.headers.get('X-API-Key')).first()
    scans = Scan.query.filter_by(user_id=user.id).order_by(Scan.created_at.desc()).all()

    scan_list = []
    for scan in scans:
        critical_assets = Asset.query.filter_by(scan_id=scan.id, risk_level='Critical').count()
        high_assets = Asset.query.filter_by(scan_id=scan.id, risk_level='High').count()

        scan_list.append({
            'id': scan.id,
            'status': scan.status,
            'targets': [t.value for t in scan.targets],
            'created_at': scan.created_at.isoformat(),
            'critical_vulnerabilities': critical_assets,
            'high_vulnerabilities': high_assets,
        })
    return jsonify(scan_list)

@api_bp.route('/scans', methods=['POST'])
@require_api_key
def create_scan():
    data = request.get_json()
    if not data or 'targets' not in data:
        return jsonify({'error': 'Missing targets in request body'}), 400

    raw_targets = data.get('targets', [])
    if isinstance(raw_targets, str):
        raw_targets = raw_targets.splitlines()

    parsed_targets = parse_targets(raw_targets)
    if not parsed_targets:
        return jsonify({'error': 'No valid targets could be parsed'}), 400

    user = User.query.filter_by(api_key=request.headers.get('X-API-Key')).first()

    new_scan = Scan(
        user_id=user.id,
        status='QUEUED',
        in_scope_rules=data.get('in_scope_rules', ''),
        out_of_scope_rules=data.get('out_of_scope_rules', '')
    )
    db.session.add(new_scan)
    db.session.flush()

    for value, type in parsed_targets:
        db.session.add(Target(value=value, type=type, scan_id=new_scan.id))

    db.session.commit()
    get_executor().submit(run_discovery_phase, new_scan.id, current_app._get_current_object())

    return jsonify({
        'message': 'Scan created successfully',
        'scan_id': new_scan.id
    }), 202

@api_bp.route('/scans/<int:scan_id>/status', methods=['GET'])
@require_api_key
def get_scan_status(scan_id):
    scan = Scan.query.get_or_404(scan_id)
    user = User.query.filter_by(api_key=request.headers.get('X-API-Key')).first()
    if scan.user_id != user.id:
        return jsonify({'error': 'Forbidden'}), 403

    return jsonify({
        'scan_id': scan.id,
        'status': scan.status,
        'summary': scan.results,
        'created_at': scan.created_at.isoformat(),
        'updated_at': scan.updated_at.isoformat()
    })

@api_bp.route('/scans/<int:scan_id>/results', methods=['GET'])
@require_api_key
def get_scan_results(scan_id):
    scan = Scan.query.get_or_404(scan_id)
    user = User.query.filter_by(api_key=request.headers.get('X-API-Key')).first()
    if scan.user_id != user.id:
        return jsonify({'error': 'Forbidden'}), 403

    if scan.status not in ['COMPLETED', 'PENDING_REVIEW']:
        return jsonify({'message': 'Results are not available yet. Status is ' + scan.status}), 202

    risk_level = request.args.get('risk_level')

    assets_query = Asset.query.filter_by(scan_id=scan.id)
    if risk_level:
        assets_query = assets_query.filter_by(risk_level=risk_level)

    assets = []
    for asset in assets_query.all():
        assets.append({
            'id': asset.id,
            'type': asset.type,
            'value': asset.value,
            'details': asset.details,
            'risk_level': asset.risk_level,
            'cvss_score': asset.cvss_score,
            'known_exploits': asset.known_exploits,
        })

    return jsonify({'scan_id': scan.id, 'assets': assets})

@api_bp.route('/scans/<int:scan_id>/graph', methods=['GET'])
@require_api_key
def get_scan_graph(scan_id):
    scan = Scan.query.get_or_404(scan_id)
    user = User.query.filter_by(api_key=request.headers.get('X-API-Key')).first()
    if scan.user_id != user.id:
        return jsonify({'error': 'Forbidden'}), 403

    graph_definition = 'graph TD\n'
    scan_node = f'scan{scan.id}("Scan #{scan.id}")'
    graph_definition += f'    {scan_node}\n'

    for target in scan.targets:
        target_node = f'target{target.id}("{target.value} ({target.type})")'
        graph_definition += f'    {target_node}\n'
        graph_definition += f'    {scan_node} --> {target_node}\n'

    for asset in scan.assets:
        safe_value = ''.join(e for e in asset.value if e.isalnum())
        asset_node = f'asset{asset.id}{safe_value}("{asset.value} ({asset.type})")'
        graph_definition += f'    {asset_node}\n'
        graph_definition += f'    {scan_node} --> {asset_node}\n'

    return jsonify({'graph_definition': graph_definition})

@api_bp.route('/monitoring/status', methods=['GET'])
def get_monitoring_status():
    """
    Provides mock data for the 3D monitoring view.
    In a real application, this would fetch real-time data from the scan manager.
    """
    mock_data = {
        "scan_progress": [
            {"name": "Subdomain Discovery", "progress": 65},
            {"name": "URL Collection", "progress": 85},
            {"name": "XSS Testing", "progress": 40},
            {"name": "SQL Injection", "progress": 70},
            {"name": "Network Scanning", "progress": 100}
        ],
        "vulnerability_feed": [
            {"severity": "CRITICAL", "title": "XSS found in example.com/search"},
            {"severity": "HIGH", "title": "SQL Injection in api.example.com/user"},
            {"severity": "MEDIUM", "title": "CORS misconfiguration on *.example.com"},
            {"severity": "LOW", "title": "Information disclosure /backup.sql"}
        ],
        "scanner_stats": {
            "active": 127,
            "queue": 1847,
            "completed": 3492
        }
    }
    return jsonify(mock_data)
