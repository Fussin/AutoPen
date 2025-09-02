import secrets
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

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
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    targets = db.relationship('Target', backref='scan', lazy=True, cascade="all, delete-orphan")
    results = db.Column(db.Text, nullable=True)

    # Fields for scope definition
    in_scope_rules = db.Column(db.Text, nullable=True)
    out_of_scope_rules = db.Column(db.Text, nullable=True)

    # Relationship to discovered assets
    assets = db.relationship('Asset', backref='scan', lazy=True, cascade="all, delete-orphan")
    findings = db.relationship('Finding', backref='scan', lazy=True, cascade="all, delete-orphan")

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
    is_monitoring_enabled = db.Column(db.Boolean, default=False, nullable=False)

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
    risk_level = db.Column(db.String(50), nullable=True, default='None')
    cvss_score = db.Column(db.Float, nullable=True, default=0.0)
    known_exploits = db.Column(db.Boolean, nullable=True, default=False)
    is_approved_for_scan = db.Column(db.Boolean, nullable=False, default=True)
    first_seen = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    scan_id = db.Column(db.Integer, db.ForeignKey('scan.id'), nullable=False)

    def __repr__(self):
        return f'<Asset {self.value} ({self.type})>'

class Finding(db.Model):
    """
    Finding model to store triaged and correlated findings. This model also
    includes fields for the ML feedback loop.
    """
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    severity = db.Column(db.String(50), nullable=False)
    # The confidence score will be updated by the ML model
    confidence = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), nullable=False, default='New')
    description = db.Column(db.Text, nullable=False)
    raw_evidence = db.Column(db.JSON, nullable=False)
    scan_id = db.Column(db.Integer, db.ForeignKey('scan.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # --- Fields for ML Feedback Loop ---
    # A unique signature for the finding type, e.g., 'nuclei:cve-2021-44228'
    finding_signature = db.Column(db.String(255), nullable=False, index=True)
    # Context about the asset, e.g., {'is_production': true, 'tech_stack': ['nginx', 'react']}
    asset_context = db.Column(db.JSON, nullable=True)
    # Ground truth from the validation engine: True (TP), False (FP), or None (Not Validated)
    validation_outcome = db.Column(db.Boolean, nullable=True)
    # Final action taken, e.g., 'ticket_created', 'false_positive', 'ignored'
    disposition = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return f'<Finding {self.title} ({self.severity})>'


class Alert(db.Model):
    """
    Alert model to store alerts generated by the continuous monitor.
    """
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='New') # e.g., New, Acknowledged, Resolved
    details = db.Column(db.JSON, nullable=True)
    scan_id = db.Column(db.Integer, db.ForeignKey('scan.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<Alert {self.title} ({self.severity})>'
