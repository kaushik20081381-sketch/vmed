from datetime import datetime
from extensions import db


class AccessRequest(db.Model):
    __tablename__ = "access_requests"

    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)

    status = db.Column(db.String(20), default="pending", nullable=False)  # pending|approved|rejected
    requested_at = db.Column(db.DateTime, default=datetime.utcnow)
    responded_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"<AccessRequest doctor={self.doctor_id} patient={self.patient_id} {self.status}>"


class DoctorPatientAccess(db.Model):
    __tablename__ = "doctor_patient_access"

    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)

    granted_at = db.Column(db.DateTime, default=datetime.utcnow)
    revoked_at = db.Column(db.DateTime, nullable=True)
    active = db.Column(db.Boolean, default=True, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("doctor_id", "patient_id", name="uq_doctor_patient"),
    )

    def __repr__(self):
        return f"<DoctorPatientAccess doctor={self.doctor_id} patient={self.patient_id} active={self.active}>"
