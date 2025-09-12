import os
from flask import Flask
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_migrate import Migrate
from config import Config
from cyberhunter_3d.web.models import db, User
from cyberhunter_3d.core.reporting.email_service import mail
from cyberhunter_3d.web.api import api_bp
from cyberhunter_3d.web.routes import register_routes
from concurrent.futures import ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler
from cyberhunter_3d.core.feeds.feed_manager import check_for_new_targets
from cyberhunter_3d.common.log import get_rich_logger

# --- Extensions Initialization ---
bcrypt = Bcrypt()
login_manager = LoginManager()
migrate = Migrate()
logger = get_rich_logger(__name__)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def create_app(config_class=Config):
    """
    Creates and configures the Flask application.
    """
    app = Flask(__name__, template_folder='cyberhunter_3d/web/templates', static_folder='cyberhunter_3d/web/static')
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)

    # --- Background Task Executor ---
    app.executor = ThreadPoolExecutor(max_workers=2)

    # --- Scheduler Setup ---
    scheduler = BackgroundScheduler()
    # Run the job every 4 hours
    # We pass the app object to the job
    scheduler.add_job(check_for_new_targets, 'interval', hours=4, args=[app])
    scheduler.start()
    logger.info("Scheduler started successfully.")

    # Register blueprints and routes
    app.register_blueprint(api_bp)
    register_routes(app, bcrypt)

    return app

# --- Main Execution ---
if __name__ == '__main__':
    app = create_app()
    # The database should be initialized manually via `python init_db.py`
    # and migrations handled by `flask db` commands.
    # use_reloader=False is important to prevent the scheduler from running twice in debug mode.
    app.run(debug=True, port=5001, use_reloader=False)
