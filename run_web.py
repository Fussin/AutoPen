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
from apscheduler.schedulers.background import BackgroundScheduler
from cyberhunter_3d.core.feeds.feed_manager import check_for_new_targets
from cyberhunter_3d.common.log import get_rich_logger
from celery import Celery, Task

# --- Extensions Initialization ---
bcrypt = Bcrypt()
login_manager = LoginManager()
migrate = Migrate()
logger = get_rich_logger(__name__)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def celery_init_app(app: Flask) -> Celery:
    """
    Factory to create and configure a Celery instance that is integrated
    with a Flask application.
    """
    class FlaskTask(Task):
        def __call__(self, *args: object, **kwargs: object) -> object:
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app = Celery(app.name, task_cls=FlaskTask)
    celery_app.config_from_object(app.config["CELERY"])
    celery_app.set_default()
    app.extensions["celery"] = celery_app
    return celery_app

def create_app(config_class=Config):
    """
    Creates and configures the Flask application.
    """
    app = Flask(__name__, template_folder='cyberhunter_3d/web/templates', static_folder='cyberhunter_3d/web/static')
    app.config.from_object(config_class)

    # Add Celery config from your main config file or object
    app.config.from_mapping(
        CELERY=dict(
            broker_url=app.config["CELERY_BROKER_URL"],
            result_backend=app.config["CELERY_RESULT_BACKEND"],
            task_ignore_result=True,
        ),
    )

    # Initialize extensions
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    celery_init_app(app) # Initialize Celery

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

# The main app and celery app instances for discovery by the 'celery' command
app = create_app()
celery_app = app.extensions["celery"]


# --- Main Execution ---
if __name__ == '__main__':
    # The database should be initialized manually via `python init_db.py`
    # and migrations handled by `flask db` commands.
    # use_reloader=False is important to prevent the scheduler from running twice in debug mode.
    app.run(debug=True, port=5001, use_reloader=False)
