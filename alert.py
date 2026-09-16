from datetime import datetime
from extensions import db


class RiskAlert(db.Model):
    """Computed risk-timeline entries -- 'Risk signals identified for clinical review', not a diagnosis."""
    __tablename__ = "risk_alerts"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)

    year = db.Column(db.Integer, nullable=False)
    level = db.Column(db.String(20), nullable=False)  # low|review|attention|high
    message = db.Column(db.String(300), nullable=False)
    category = db.Column(db.String(50))  # lab_trend|medication|diagnosis|repeated_abnormal
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    LEVEL_ICON = {"low": "🟢", "review": "🟡", "attention": "🟠", "high": "🔴"}

    @property
    def icon(self):
        return self.LEVEL_ICON.get(self.level, "🟢")

    def __repr__(self):
        return f"<RiskAlert {self.year} {self.level}>"


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    message = db.Column(db.String(300), nullable=False)
    category = db.Column(db.String(50), default="info")  # info|access_request|alert|system
    link = db.Column(db.String(300))
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User")

    def __repr__(self):
        return f"<Notification to_user={self.user_id} read={self.is_read}>"
