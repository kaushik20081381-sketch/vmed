import os
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, send_from_directory, abort
from flask_login import login_required, current_user

from extensions import db
from models import Patient, MedicalRecord, LabResult, Medication, Diagnosis, DoctorPatientAccess
from utils import allowed_file
from services.audit_service import log_action
from services.risk_engine import compute_risk_timeline

records_bp = Blueprint("records", __name__, url_prefix="/records")


def _resolve_target_patient():
    """Patients upload for themselves; verified doctors upload for an authorized patient (patient_id in form)."""
    if current_user.role == "patient":
        return current_user.patient_profile
    if current_user.role == "doctor":
        patient_id = request.form.get("patient_id") or request.args.get("patient_id")
        if not patient_id:
            return None
        patient = db.session.get(Patient, int(patient_id))
        if not patient:
            return None
        has_access = DoctorPatientAccess.query.filter_by(
            doctor_id=current_user.doctor_profile.id, patient_id=patient.id, active=True
        ).first()
        return patient if has_access else None
    return None


@records_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if current_user.role not in ("patient", "doctor"):
        flash("Only patients and authorized doctors can upload records.", "danger")
        return redirect(url_for("main.index"))

    patient = _resolve_target_patient()

    if request.method == "POST":
        if not patient:
            flash("Unable to determine the target patient for this upload.", "danger")
            return redirect(url_for("records.upload"))

        record_type = request.form.get("record_type", "other")
        description = request.form.get("description", "").strip()
        hospital = request.form.get("hospital", "").strip()
        doctor_name = request.form.get("doctor_name", "").strip()
        try:
            record_date = datetime.strptime(request.form.get("record_date", ""), "%Y-%m-%d").date()
        except ValueError:
            flash("Please provide a valid record date.", "danger")
            return redirect(url_for("records.upload"))

        file = request.files.get("file")
        file_path = None
        original_filename = None
        if file and file.filename:
            if not allowed_file(file.filename, current_app.config["ALLOWED_EXTENSIONS"]):
                flash("Unsupported file type. Allowed: PDF, TXT, CSV, PNG, JPG.", "danger")
                return redirect(url_for("records.upload"))
            original_filename = secure_filename(file.filename)
            safe_name = f"{patient.patient_code}_{int(datetime.utcnow().timestamp())}_{original_filename}"
            full_path = os.path.join(current_app.config["UPLOAD_FOLDER"], safe_name)
            file.save(full_path)
            file_path = safe_name

        record = MedicalRecord(
            patient_id=patient.id,
            uploaded_by_user_id=current_user.id,
            hospital=hospital, doctor_name=doctor_name, record_type=record_type,
            description=description, file_path=file_path, original_filename=original_filename,
            record_date=record_date,
        )
        db.session.add(record)
        db.session.flush()

        # Optional structured extras submitted alongside the upload (lab value, medication, diagnosis)
        if record_type == "lab_report" and request.form.get("test_name"):
            lab = LabResult(
                patient_id=patient.id, medical_record_id=record.id,
                test_name=request.form["test_name"].strip().lower().replace(" ", "_"),
                display_name=request.form["test_name"].strip(),
                value=float(request.form.get("test_value", 0) or 0),
                unit=request.form.get("test_unit", "").strip(),
                test_date=record_date, hospital=hospital,
            )
            db.session.add(lab)

        if record_type == "medication" and request.form.get("medicine_name"):
            med = Medication(
                patient_id=patient.id,
                medicine_name=request.form["medicine_name"].strip(),
                dose=request.form.get("dose", "").strip(),
                frequency=request.form.get("frequency", "").strip(),
                start_date=record_date,
                prescribing_doctor=doctor_name, hospital=hospital,
            )
            db.session.add(med)

        if record_type == "diagnosis" and request.form.get("condition_name"):
            diag = Diagnosis(
                patient_id=patient.id,
                condition_name=request.form["condition_name"].strip(),
                diagnosis_date=record_date, hospital=hospital, doctor_name=doctor_name,
                notes=description,
            )
            db.session.add(diag)

        db.session.commit()
        compute_risk_timeline(patient)  # refresh cached risk alerts

        log_action("medical_record_upload", target_patient_id=patient.id,
                   details=f"{current_user.role} '{current_user.username}' uploaded a {record_type} record")

        flash("Medical record uploaded successfully.", "success")
        if current_user.role == "patient":
            return redirect(url_for("patient.records"))
        return redirect(url_for("doctor.view_patient", patient_id=patient.id))

    return render_template("records/upload.html", patient=patient)


@records_bp.route("/file/<int:record_id>")
@login_required
def download_file(record_id):
    """Serve an uploaded record's file only to its owning patient or a doctor with active access."""
    record = MedicalRecord.query.get_or_404(record_id)
    patient = record.patient

    allowed = False
    if current_user.role == "patient" and current_user.patient_profile and current_user.patient_profile.id == patient.id:
        allowed = True
    elif current_user.role == "doctor" and current_user.doctor_profile:
        allowed = DoctorPatientAccess.query.filter_by(
            doctor_id=current_user.doctor_profile.id, patient_id=patient.id, active=True
        ).first() is not None
    elif current_user.role == "admin":
        allowed = True

    if not allowed or not record.file_path:
        abort(403)

    log_action("medical_record_viewed", target_patient_id=patient.id,
               details=f"{current_user.role} '{current_user.username}' downloaded file for record #{record.id}")
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], record.file_path, as_attachment=False)
