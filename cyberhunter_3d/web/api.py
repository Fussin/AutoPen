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

from cyberhunter_3d.web.models import db, Scan, Target, Asset
from cyberhunter_3d.core.target_parser import parse_targets
from cyberhunter_3d.core.scan_manager import run_discovery_phase
from concurrent.futures import ThreadPoolExecutor
from flask import current_app

# This is a bit of a hack to get access to the executor defined in run_web.py
# In a real app, this would be handled by a proper application factory or shared context.
def get_executor():
    return current_app.executor

@api_bp.route('/ping')
@require_api_key
def ping():
    """A simple protected endpoint to test authentication."""
    return jsonify({'message': 'pong'})

@api_bp.route('/scans', methods=['POST'])
@require_api_key
def create_scan():
    """
    Creates a new scan. Expects a JSON payload with targets.
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

    # Trigger discovery phase
    get_executor().submit(run_discovery_phase, new_scan.id, current_app._get_current_object())

    return jsonify({
        'message': 'Scan created successfully',
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
