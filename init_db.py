from cyberhunter_3d.web.models import db
from run_web import create_app

def init_db():
    """Initializes the database."""
    app = create_app()
    with app.app_context():
        db.create_all()
    print("Database initialized successfully.")

if __name__ == "__main__":
    init_db()
