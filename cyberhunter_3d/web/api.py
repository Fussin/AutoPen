from functools import wraps
from flask import Blueprint, request, jsonify
from cyberhunter_3d.web.models import User

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

def require_api_key(f):
    """Decorator to protect API routes with an API key."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({'error': 'API key is missing'}), 401

        user = User.query.filter_by(api_key=api_key).first()
        if not user:
            return jsonify({'error': 'Invalid API key'}), 401

        # You could attach the user to the request context if needed
        # g.user = user
        return f(*args, **kwargs)
    return decorated_function

from cyberhunter_3d.web.models import db, Scan, Target, Asset, Vulnerability
from cyberhunter_3d.core.target_parser import parse_targets
from cyberhunter_3d.tasks import run_discovery_task
from ..extensions import celery_app

@api_bp.route('/ping')
@require_api_key
def ping():
    """A simple protected endpoint to test authentication."""
    return jsonify({'message': 'pong'})

@api_bp.route('/scans', methods=['POST'])
@require_api_key
def create_scan():
    """
    Create and launch a new reconnaissance scan.
    This endpoint queues a new scan based on the provided targets and scope rules.
    ---
    tags:
      - Scans
    security:
      - ApiKeyAuth: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          id: ScanRequest
          required:
            - targets
          properties:
            targets:
              type: array
              items:
                type: string
              description: A list of targets (domains, IPs, CIDRs, etc.).
              example: ["example.com", "*.example.com"]
            in_scope_rules:
              type: string
              description: Newline-separated in-scope rules. Wildcards (*) are supported.
              example: "*.example.com"
            out_of_scope_rules:
              type: string
              description: Newline-separated out-of-scope rules.
              example: "dev.example.com"
    responses:
      202:
        description: Scan successfully queued for discovery.
        schema:
          properties:
            message:
              type: string
            scan_id:
              type: integer
      400:
        description: Bad Request - Missing or invalid targets.
      401:
        description: Unauthorized - API key is missing or invalid.
    """
    data = request.get_json()
    if not data or 'targets' not in data:
        return jsonify({'error': 'Missing targets in request body'}), 400

    raw_targets = data.get('targets', [])
    if isinstance(raw_targets, str):
        raw_targets = raw_targets.splitlines()

    parsed_targets = parse_targets(raw_targets)
    if not parsed_targets:
        return jsonify({'error': 'No valid targets could be parsed'}), 400

    # Get user from API key to associate the scan
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

    # --- THIS IS THE KEY CHANGE ---
    # Instead of submitting to a ThreadPoolExecutor, you call .delay() on your task.
    # This sends a message to Redis with the scan_id as the argument.
    run_discovery_task.delay(new_scan.id)

    return jsonify({
        'message': 'Scan successfully queued for discovery',
        'scan_id': new_scan.id
    }), 202

@api_bp.route('/scans/<int:scan_id>/status', methods=['GET'])
@require_api_key
def get_scan_status(scan_id):
    scan = Scan.query.get_or_404(scan_id)
    # Simple authorization check
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

    assets = []
    for asset in scan.assets:
        assets.append({
            'id': asset.id,
            'type': asset.type,
            'value': asset.value,
            'details': asset.details,
            'is_approved_for_scan': asset.is_approved_for_scan,
            'first_seen': asset.first_seen.isoformat()
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

    # Add targets as nodes
    for target in scan.targets:
        target_node = f'target{target.id}("{target.value} ({target.type})")'
        graph_definition += f'    {target_node}\n'
        graph_definition += f'    {scan_node} --> {target_node}\n'

    # Add assets as nodes and link them
    # A more advanced version would link assets to the target that found them
    for asset in scan.assets:
        # Sanitize value for mermaid id
        safe_value = ''.join(e for e in asset.value if e.isalnum())
        asset_node = f'asset{asset.id}{safe_value}("{asset.value} ({asset.type})")'
        graph_definition += f'    {asset_node}\n'
        # For now, link all assets back to the main scan node
        graph_definition += f'    {scan_node} --> {asset_node}\n'

    return jsonify({'graph_definition': graph_definition})

@api_bp.route('/scans/<int:scan_id>/graph_data', methods=['GET'])
@require_api_key
def get_scan_graph_data(scan_id):
    scan = Scan.query.get_or_404(scan_id)
    user = User.query.filter_by(api_key=request.headers.get('X-API-Key')).first()
    if scan.user_id != user.id:
        return jsonify({'error': 'Forbidden'}), 403

    nodes = []
    links = []

    # Scan node
    scan_node_id = f"scan_{scan.id}"
    nodes.append({"id": scan_node_id, "name": f"Scan #{scan.id}", "type": "scan"})

    # Asset nodes and links from scan to assets
    for asset in scan.assets:
        asset_node_id = f"asset_{asset.id}"
        nodes.append({"id": asset_node_id, "name": asset.value, "type": "asset"})
        links.append({"source": scan_node_id, "target": asset_node_id})

        # Vulnerability nodes and links from assets to vulnerabilities
        for vuln in asset.vulnerabilities:
            vuln_node_id = f"vuln_{vuln.id}"
            nodes.append({"id": vuln_node_id, "name": vuln.title, "type": "vulnerability", "severity": vuln.severity})
            links.append({"source": asset_node_id, "target": vuln_node_id})

    return jsonify({"nodes": nodes, "links": links})

@api_bp.route('/health')
def health_check():
    """
    Health check endpoint to verify service status.
    Checks the status of the database and the message broker (Redis).
    ---
    tags:
      - Health
    responses:
      200:
        description: Service is healthy.
      503:
        description: One or more services are unhealthy.
    """
    try:
        # 1. Check database connectivity
        db.session.execute('SELECT 1')

        # 2. Check Celery worker connectivity to Redis
        celery_app.control.ping()

        return jsonify({"status": "ok"}), 200
    except Exception as e:
        # In a real app, you would log the error 'e' here
        return jsonify({
            "status": "error",
            "details": "One or more downstream services are unavailable."
        }), 503
