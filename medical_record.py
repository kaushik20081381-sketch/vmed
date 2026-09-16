from datetime import datetime
from extensions import db


class MedicalRecord(db.Model):
    __tablename__ = "medical_records"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    uploaded_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    hospital = db.Column(db.String(150))
    doctor_name = db.Column(db.String(150))
    record_type = db.Column(db.String(50), nullable=False)  # hospital_visit|lab_report|prescription|diagnosis|other
    description = db.Column(db.Text)
    file_path = db.Column(db.String(300))
    original_filename = db.Column(db.String(300))
    record_date = db.Column(db.Date, nullable=False)
    is_demo_data = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    uploaded_by = db.relationship("User", foreign_keys=[uploaded_by_user_id], backref="medical_records_uploaded")

    ICONS = {
        "hospital_visit": "🏥",
        "diagnosis": "🩺",
        "lab_report": "🧪",
        "medication": "💊",
        "report": "📄",
        "alert": "⚠",
        "other": "📄",
    }

    @property
    def icon(self):
        return self.ICONS.get(self.record_type, "📄")

    def __repr__(self):
        return f"<MedicalRecord {self.record_type} {self.record_date}>"
