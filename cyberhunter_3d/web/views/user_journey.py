from flask import Blueprint, render_template
from flask_login import login_required

user_journey_bp = Blueprint('user_journey', __name__, template_folder='../templates')

@user_journey_bp.route('/user-journey')
@login_required
def show_user_journey():
    """
    Renders the user journey map page.
    """
    return render_template('user_journey.html')
