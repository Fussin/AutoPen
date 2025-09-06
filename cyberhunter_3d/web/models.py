import secrets
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

# Association table for User and Workspace membership
workspace_members = db.Table('workspace_members',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('workspace_id', db.Integer, db.ForeignKey('workspace.id'), primary_key=True)
)

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

    # Owned workspaces
    owned_workspaces = db.relationship('Workspace', backref='owner', lazy='dynamic', foreign_keys='Workspace.owner_id')

    # Workspaces the user is a member of
    workspaces = db.relationship('Workspace', secondary=workspace_members,
                                 backref=db.backref('members', lazy='dynamic'), lazy='dynamic')

    def __repr__(self):
        return f'<User {self.username}>'

    def regenerate_api_key(self):
        self.api_key = secrets.token_hex(32)

class Workspace(db.Model):
    """
    Workspace model to group scans and collaborators.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    scans = db.relationship('Scan', backref='workspace', lazy='dynamic', cascade="all, delete-orphan")
    notes = db.relationship('Note', backref='workspace', lazy='dynamic', cascade="all, delete-orphan")
    schedules = db.relationship('ScanSchedule', backref='workspace', lazy='dynamic', cascade="all, delete-orphan")

    # Notification settings
    slack_webhook_url = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f'<Workspace {self.name}>'

class ScanSchedule(db.Model):
    """
    Model for storing scan schedules.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    is_enabled = db.Column(db.Boolean, default=True)

    # Storing targets as a simple text field, one per line
    targets = db.Column(db.Text, nullable=False)

    # Schedule interval, e.g., 'daily', 'weekly', 'monthly'
    interval = db.Column(db.String(50), nullable=False)

    # Time of day to run the scan, e.g., '03:00'
    run_time = db.Column(db.String(5), nullable=True)

    last_run_at = db.Column(db.DateTime, nullable=True)
    next_run_at = db.Column(db.DateTime, nullable=True)

    workspace_id = db.Column(db.Integer, db.ForeignKey('workspace.id'), nullable=False)

    def __repr__(self):
        return f'<ScanSchedule {self.name} ({self.interval})>'

class Scan(db.Model):
    """
    Scan model to track a reconnaissance job.
    """
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20), nullable=False, default='QUEUED')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Foreign key to Workspace
    workspace_id = db.Column(db.Integer, db.ForeignKey('workspace.id'), nullable=False)

    # Keep track of the user who initiated this specific scan
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    owner = db.relationship('User', backref='scans')

    targets = db.relationship('Target', backref='scan', lazy=True, cascade="all, delete-orphan")
    results = db.Column(db.Text, nullable=True)
    in_scope_rules = db.Column(db.Text, nullable=True)
    out_of_scope_rules = db.Column(db.Text, nullable=True)
    assets = db.relationship('Asset', backref='scan', lazy=True, cascade="all, delete-orphan")

    output_dir = db.Column(db.String(255), nullable=True)

    findings = db.relationship('Finding', backref='scan', lazy='dynamic', cascade="all, delete-orphan")


    def __repr__(self):
        return f'<Scan {self.id} - {self.status}>'

class Finding(db.Model):
    """
    Model for storing security findings from scans.
    """
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(50), nullable=False) # e.g., Critical, High, Medium, Low, Informational
    is_validated = db.Column(db.Boolean, default=False)
    is_triaged = db.Column(db.Boolean, default=False) # For automated triage
    confidence = db.Column(db.String(50), nullable=True) # e.g., High, Medium, Low
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    scan_id = db.Column(db.Integer, db.ForeignKey('scan.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # User who reported the finding

    user = db.relationship('User', backref='findings')

    def __repr__(self):
        return f'<Finding {self.title}>'

class Note(db.Model):
    """

    Model for collaborative notes within a workspace.
    """
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    workspace_id = db.Column(db.Integer, db.ForeignKey('workspace.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    user = db.relationship('User', backref='notes')

    def __repr__(self):
        return f'<Note by {self.user.username}>'

class Target(db.Model):
    """
    Target model to store individual targets for a scan.
    """
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.String(255), nullable=False)
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
    first_seen = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    scan_id = db.Column(db.Integer, db.ForeignKey('scan.id'), nullable=False)

    def __repr__(self):
        return f'<Asset {self.value} ({self.type})>'
