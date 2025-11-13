from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date

db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(32), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Certificate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_name = db.Column(db.String(255), nullable=False)
    student_email = db.Column(db.String(255), nullable=False)
    course_name = db.Column(db.String(255), nullable=False)
    issue_date = db.Column(db.Date, nullable=False)
    file_path = db.Column(db.String(512), nullable=False)
    file_hash = db.Column(db.String(66), nullable=False)
    blockchain_tx = db.Column(db.String(66), nullable=True)
    contract_address = db.Column(db.String(66), nullable=True)
    issuer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    issuer = db.relationship('User', backref=db.backref('certificates', lazy=True))
