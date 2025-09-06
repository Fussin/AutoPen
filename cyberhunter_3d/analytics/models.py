from cyberhunter_3d.web.models import db
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

class ScanMetrics(db.Model):
    """
    Model for storing analytics and metrics for a scan.
    """
    id = db.Column(db.Integer, primary_key=True)
    scan_id = db.Column(db.Integer, db.ForeignKey('scan.id'), nullable=False, unique=True)

    # Using a generic JSON type for broader database support (e.g., SQLite, MySQL)
    # For PostgreSQL, JSONB would be more efficient.
    metrics = db.Column(JSON, nullable=False, default=lambda: {})

    # Establish the one-to-one relationship with the Scan model
    scan = db.relationship('Scan', backref=db.backref('metrics', uselist=False, cascade="all, delete-orphan"))

    def __repr__(self):
        return f'<ScanMetrics for Scan {self.scan_id}>'

    def get_metric(self, key, default=None):
        """Helper to safely retrieve a top-level metric."""
        return self.metrics.get(key, default)

    def set_metric(self, key, value):
        """Helper to set a top-level metric."""
        # This approach replaces the whole dict. For frequent updates,
        # a mutable JSON setup would be needed.
        new_metrics = self.metrics.copy()
        new_metrics[key] = value
        self.metrics = new_metrics
