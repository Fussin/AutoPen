from flask import Blueprint, render_template
from flask_login import login_required, current_user

dashboard_bp = Blueprint('dashboard_v2', __name__, template_folder='../templates', url_prefix='/dashboard/v2')

@dashboard_bp.route('/')
@login_required
def dashboard_home():
    """
    Renders the new interactive dashboard home page.
    """
    return render_template('new_dashboard.html')

@dashboard_bp.route('/scan/<int:scan_id>')
@login_required
def scan_detail(scan_id):
    """
    Renders the new interactive scan detail page.
    """
    # We just need to pass the scan_id to the template.
    # The actual data will be fetched by JavaScript.
    return render_template('scan_detail_new.html', scan_id=scan_id)
