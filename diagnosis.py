from datetime import datetime
from extensions import db


class Diagnosis(db.Model):
    __tablename__ = "diagnoses"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)

    condition_name = db.Column(db.String(150), nullable=False)
    diagnosis_date = db.Column(db.Date, nullable=False)
    hospital = db.Column(db.String(150))
    doctor_name = db.Column(db.String(150))
    notes = db.Column(db.Text)
    is_demo_data = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Diagnosis {self.condition_name}>"
