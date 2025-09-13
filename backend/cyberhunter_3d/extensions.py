from celery import Celery
from flask_bcrypt import Bcrypt
from flask_login import LoginManager

# Instantiate the Celery object.
# It will be configured by the Flask app factory.
celery_app = Celery()
bcrypt = Bcrypt()
login_manager = LoginManager()
