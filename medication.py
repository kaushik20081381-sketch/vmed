from datetime import datetime
from extensions import db


class Medication(db.Model):
    __tablename__ = "medications"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)

    medicine_name = db.Column(db.String(120), nullable=False)
    dose = db.Column(db.String(60))
    frequency = db.Column(db.String(60))
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    prescribing_doctor = db.Column(db.String(150))
    hospital = db.Column(db.String(150))
    is_demo_data = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def is_active(self):
        return self.end_date is None

    def __repr__(self):
        return f"<Medication {self.medicine_name}>"
