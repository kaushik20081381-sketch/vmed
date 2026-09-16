"""
Seed synthetic demo data for the MedTimeline AI hackathon demo.

Run once, after the database exists and dependencies are installed:

    python seed_demo_data.py

Safe to re-run: it skips creation of any record that already exists
(matched by unique username/email/license number).

All medical data created here is SYNTHETIC / DEMO DATA and is flagged
with is_demo_data=True where applicable.
"""
from datetime import date

from app import create_app
from extensions import db
from models import (
    User, Patient, Doctor, Admin,
    MedicalRecord, LabResult, Medication, Diagnosis,
    DoctorPatientAccess,
)

app = create_app()


def get_or_create_user(username, email, password, role):
    user = User.query.filter_by(username=username).first()
    if user:
        return user, False
    user = User(username=username, email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()
    return user, True


def seed():
    with app.app_context():
        db.create_all()

        # ---------------- Admin ----------------
        admin_user, created = get_or_create_user("admin", "admin@medtimeline.ai", "Admin@123", "admin")
        if created:
            db.session.add(Admin(user_id=admin_user.id, full_name="System Administrator"))
            print("Created admin account: admin / Admin@123")
        else:
            print("Admin account already exists, skipping.")

        # ---------------- Demo doctor ----------------
        doctor_user, created = get_or_create_user("dr.arun", "arun.nair@cityhospital.example", "Doctor@123", "doctor")
        if created:
            doctor = Doctor(
                user_id=doctor_user.id,
                full_name="Arun Nair",
                phone="9876543210",
                specialization="Internal Medicine",
                hospital="City General Hospital",
                license_number="MCI-2015-004821",
                verification_status="verified",
            )
            db.session.add(doctor)
            print("Created verified demo doctor: dr.arun / Doctor@123")
        else:
            doctor = doctor_user.doctor_profile
            print("Demo doctor already exists, skipping.")

        db.session.flush()

        # ---------------- Demo patient: Priya Kumar ----------------
        patient_user = User.query.filter_by(username="priya.kumar52").first()
        if patient_user:
            print("Demo patient already exists, skipping patient creation.")
            db.session.commit()
            return

        patient_user, _ = get_or_create_user(
            "priya.kumar52", "priya.kumar@example.com", "Patient@123", "patient"
        )
        db.session.flush()

        patient = Patient(
            user_id=patient_user.id,
            patient_code=Patient.generate_patient_code(),
            full_name="Priya Kumar",
            phone="9123456780",
            date_of_birth=date(1985, 6, 12),
            gender="Female",
        )
        db.session.add(patient)
        db.session.flush()
        print(f"Created demo patient: priya.kumar52 / Patient@123  (Patient ID: {patient.patient_code})")

        # ---- 2023: Hospital visit + diagnosis: Hypertension ----
        rec_2023 = MedicalRecord(
            patient_id=patient.id, uploaded_by_user_id=doctor_user.id,
            hospital="City General Hospital", doctor_name="Dr. Arun Nair",
            record_type="hospital_visit",
            description="Routine check-up; elevated blood pressure noted (140/90).",
            record_date=date(2023, 3, 14), is_demo_data=True,
        )
        db.session.add(rec_2023)
        db.session.add(Diagnosis(
            patient_id=patient.id, condition_name="Hypertension",
            diagnosis_date=date(2023, 3, 14), hospital="City General Hospital",
            doctor_name="Dr. Arun Nair", notes="Stage 1 hypertension, lifestyle changes advised.",
            is_demo_data=True,
        ))
        db.session.add(LabResult(
            patient_id=patient.id, test_name="systolic_bp", display_name="Systolic BP",
            value=140, unit="mmHg", test_date=date(2023, 3, 14),
            hospital="City General Hospital", is_demo_data=True,
        ))
        db.session.add(LabResult(
            patient_id=patient.id, test_name="diastolic_bp", display_name="Diastolic BP",
            value=90, unit="mmHg", test_date=date(2023, 3, 14),
            hospital="City General Hospital", is_demo_data=True,
        ))
        db.session.add(Medication(
            patient_id=patient.id, medicine_name="Lisinopril", dose="10mg",
            frequency="Once daily", start_date=date(2023, 3, 15),
            prescribing_doctor="Dr. Arun Nair", hospital="City General Hospital",
            is_demo_data=True,
        ))

        # ---- 2024: Laboratory test -- cholesterol & glucose creeping up ----
        db.session.add(LabResult(
            patient_id=patient.id, test_name="cholesterol", display_name="Total Cholesterol",
            value=225, unit="mg/dL", test_date=date(2024, 4, 2),
            hospital="Sunrise Diagnostics Lab", is_demo_data=True,
        ))
        db.session.add(LabResult(
            patient_id=patient.id, test_name="glucose", display_name="Fasting Glucose",
            value=145, unit="mg/dL", test_date=date(2024, 4, 2),
            hospital="Sunrise Diagnostics Lab", is_demo_data=True,
        ))
        db.session.add(MedicalRecord(
            patient_id=patient.id, uploaded_by_user_id=doctor_user.id,
            hospital="Sunrise Diagnostics Lab", doctor_name=None,
            record_type="lab_report", description="Annual bloodwork panel.",
            record_date=date(2024, 4, 2), is_demo_data=True,
        ))

        # ---- 2025: Hospital visit -- diagnosis: Diabetes + medication prescribed ----
        db.session.add(MedicalRecord(
            patient_id=patient.id, uploaded_by_user_id=doctor_user.id,
            hospital="City General Hospital", doctor_name="Dr. Arun Nair",
            record_type="hospital_visit",
            description="Follow-up visit; new diagnosis of type 2 diabetes.",
            record_date=date(2025, 5, 20), is_demo_data=True,
        ))
        db.session.add(Diagnosis(
            patient_id=patient.id, condition_name="Type 2 Diabetes",
            diagnosis_date=date(2025, 5, 20), hospital="City General Hospital",
            doctor_name="Dr. Arun Nair", notes="Started on metformin; dietary counseling provided.",
            is_demo_data=True,
        ))
        db.session.add(Medication(
            patient_id=patient.id, medicine_name="Metformin", dose="500mg",
            frequency="Twice daily", start_date=date(2025, 5, 21),
            prescribing_doctor="Dr. Arun Nair", hospital="City General Hospital",
            is_demo_data=True,
        ))
        # Also prescribed ibuprofen around the same time -- creates a known
        # interaction signal with the existing Lisinopril for the demo.
        db.session.add(Medication(
            patient_id=patient.id, medicine_name="Ibuprofen", dose="400mg",
            frequency="As needed for joint pain", start_date=date(2025, 6, 1),
            prescribing_doctor="Dr. Arun Nair", hospital="City General Hospital",
            is_demo_data=True,
        ))

        # ---- 2026: Laboratory test -- cholesterol & glucose worse; persistent trend ----
        db.session.add(LabResult(
            patient_id=patient.id, test_name="cholesterol", display_name="Total Cholesterol",
            value=245, unit="mg/dL", test_date=date(2026, 3, 10),
            hospital="Sunrise Diagnostics Lab", is_demo_data=True,
        ))
        db.session.add(LabResult(
            patient_id=patient.id, test_name="glucose", display_name="Fasting Glucose",
            value=168, unit="mg/dL", test_date=date(2026, 3, 10),
            hospital="Sunrise Diagnostics Lab", is_demo_data=True,
        ))
        db.session.add(MedicalRecord(
            patient_id=patient.id, uploaded_by_user_id=doctor_user.id,
            hospital="Sunrise Diagnostics Lab", doctor_name=None,
            record_type="lab_report", description="Annual bloodwork panel -- persistent upward trend noted.",
            record_date=date(2026, 3, 10), is_demo_data=True,
        ))

        # ---- Grant the demo doctor active access to the demo patient ----
        db.session.add(DoctorPatientAccess(doctor_id=doctor.id, patient_id=patient.id))

        db.session.commit()
        print("Demo medical history (2023-2026) seeded for Priya Kumar.")
        print("Doctor 'dr.arun' has been granted access to this patient for the demo.")
        print("\nDemo accounts:")
        print("  Patient : priya.kumar52 / Patient@123")
        print("  Doctor  : dr.arun       / Doctor@123")
        print("  Admin   : admin         / Admin@123")


if __name__ == "__main__":
    seed()
