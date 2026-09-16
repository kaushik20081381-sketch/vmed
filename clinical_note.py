from datetime import datetime
from extensions import db


class ClinicalNote(db.Model):
    __tablename__ = "clinical_notes"

    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)

    note_type = db.Column(db.String(30), default="consultation")  # consultation|follow_up|observation
    note_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ClinicalNote patient={self.patient_id} by_doctor={self.doctor_id}>"
