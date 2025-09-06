import secrets
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timezone

# This db object will be initialized in our main application file (run_web.py)
db = SQLAlchemy()

class User(UserMixin, db.Model):
    """
    User model for authentication and storing user data.
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    otp_secret = db.Column(db.String(16), nullable=False)
    api_key = db.Column(db.String(64), unique=True, nullable=False, default=lambda: secrets.token_hex(32))
    hackerone_api_key = db.Column(db.String(255), nullable=True)
    scans = db.relationship('Scan', backref='user', lazy=True)
    monitoring_settings = db.relationship('MonitoringSettings', uselist=False, back_populates='user', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<User {self.username}>'

    def regenerate_api_key(self):
        self.api_key = secrets.token_hex(32)

class Scan(db.Model):
    """
    Scan model to track a reconnaissance job.
    """
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20), nullable=False, default='QUEUED')
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    targets = db.relationship('Target', backref='scan', lazy=True, cascade="all, delete-orphan")
    results = db.Column(db.Text, nullable=True)

    # Fields for scope definition
    in_scope_rules = db.Column(db.Text, nullable=True)
    out_of_scope_rules = db.Column(db.Text, nullable=True)

    # Relationship to discovered assets
    assets = db.relationship('Asset', backref='scan', lazy=True, cascade="all, delete-orphan")
    output_dir = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f'<Scan {self.id} - {self.status}>'

class Target(db.Model):
    """
    Target model to store individual targets for a scan.
    """
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.String(255), nullable=False)
    # The type of target, e.g., 'domain', 'ip_address', 'cidr', 'wildcard_domain'
    type = db.Column(db.String(50), nullable=False, default='unknown')
    scan_id = db.Column(db.Integer, db.ForeignKey('scan.id'), nullable=False)

    def __repr__(self):
        return f'<Target {self.value} ({self.type})>'

class Asset(db.Model):
    """
    Asset model to store individual discovered assets from a scan.
    """
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False) # e.g., 'subdomain', 'ip_address', 'open_port'
    value = db.Column(db.String(255), nullable=False)
    details = db.Column(db.JSON, nullable=True) # For extra info like port details
    is_approved_for_scan = db.Column(db.Boolean, nullable=False, default=True)
    first_seen = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    last_seen = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    scan_id = db.Column(db.Integer, db.ForeignKey('scan.id'), nullable=False)

    def __repr__(self):
        return f'<Asset {self.value} ({self.type})>'

class MonitoringSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    user = db.relationship('User', back_populates='monitoring_settings')

    # Asset Monitoring
    asset_new_subdomain_detection = db.Column(db.Boolean, default=False, nullable=False)
    asset_certificate_changes = db.Column(db.Boolean, default=False, nullable=False)
    asset_dns_record_modifications = db.Column(db.Boolean, default=False, nullable=False)
    asset_technology_updates = db.Column(db.Boolean, default=False, nullable=False)
    asset_new_endpoints = db.Column(db.Boolean, default=False, nullable=False)

    # Vulnerability Monitoring
    vuln_cve_feed_integration = db.Column(db.Boolean, default=False, nullable=False)
    vuln_zero_day_alerts = db.Column(db.Boolean, default=False, nullable=False)
    vuln_patch_status_tracking = db.Column(db.Boolean, default=False, nullable=False)
    vuln_regression_testing = db.Column(db.Boolean, default=False, nullable=False)
    vuln_threat_intelligence_correlation = db.Column(db.Boolean, default=False, nullable=False)

    # Schedule Configuration
    schedule_quick_scans = db.Column(db.Boolean, default=False, nullable=False)
    schedule_full_scans = db.Column(db.Boolean, default=False, nullable=False)
    schedule_deep_scans = db.Column(db.Boolean, default=False, nullable=False)
    schedule_compliance_scans = db.Column(db.Boolean, default=False, nullable=False)
    schedule_custom_schedules = db.Column(db.String(255), nullable=True)
