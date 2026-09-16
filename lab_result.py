from datetime import datetime
from extensions import db


# Configurable reference ranges for common labs used by the trend engine.
# (low, high, unit) -- values outside this band are flagged abnormal.
REFERENCE_RANGES = {
    "glucose": (70, 140, "mg/dL"),
    "cholesterol": (0, 200, "mg/dL"),
    "hdl": (40, 60, "mg/dL"),
    "ldl": (0, 100, "mg/dL"),
    "hemoglobin": (12.0, 17.0, "g/dL"),
    "creatinine": (0.6, 1.3, "mg/dL"),
    "systolic_bp": (90, 120, "mmHg"),
    "diastolic_bp": (60, 80, "mmHg"),
    "triglycerides": (0, 150, "mg/dL"),
}


class LabResult(db.Model):
    __tablename__ = "lab_results"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    medical_record_id = db.Column(db.Integer, db.ForeignKey("medical_records.id"), nullable=True)

    test_name = db.Column(db.String(80), nullable=False, index=True)  # normalized key e.g. "glucose"
    display_name = db.Column(db.String(120))
    value = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(30))
    test_date = db.Column(db.Date, nullable=False)
    hospital = db.Column(db.String(150))
    is_demo_data = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def is_abnormal(self):
        rng = REFERENCE_RANGES.get(self.test_name)
        if not rng:
            return False
        low, high, _ = rng
        return self.value < low or self.value > high

    def __repr__(self):
        return f"<LabResult {self.test_name}={self.value} on {self.test_date}>"
