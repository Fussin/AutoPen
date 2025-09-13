from flask import Flask
from cyberhunter_3d.web.models import db, User
from cyberhunter_3d.web.api import api_bp
from cyberhunter_3d.web.routes import register_routes
from cyberhunter_3d.core.reporting.email_service import mail
from cyberhunter_3d.extensions import celery_app, bcrypt, login_manager

def create_app():
    """Application Factory Function"""
    app = Flask(__name__, template_folder='cyberhunter_3d/web/templates', static_folder='cyberhunter_3d/web/static')

    # Load configuration (from a config file or object)
    # Make sure you have a config.py or similar
    app.config.from_object('config.Config')

    # Initialize extensions with the app
    db.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Configure Celery
    celery_app.config_from_object(app.config, namespace='CELERY')
    celery_app.conf.update(app.config)

    class ContextTask(celery_app.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app.Task = ContextTask

    # Register blueprints for your routes and API
    app.register_blueprint(api_bp)
    # Add other blueprints if you have them
    register_routes(app, bcrypt)

    return app

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all() # A simple way to ensure DB is created on run
    app.run(debug=True, host='0.0.0.0', port=5001)
