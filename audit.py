from datetime import datetime
from extensions import db


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    actor_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(80), nullable=False)  # login|logout|upload_record|access_approved|...
    target_patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=True)
    details = db.Column(db.String(400))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    actor = db.relationship("User")
    target_patient = db.relationship("Patient")

    def __repr__(self):
        return f"<AuditLog {self.action} by={self.actor_user_id}>"
