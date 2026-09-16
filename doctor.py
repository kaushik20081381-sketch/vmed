from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user

from extensions import db
from models import Patient, AccessRequest, DoctorPatientAccess, ClinicalNote
from utils import role_required, verified_doctor_required, notify
from services.audit_service import log_action
from services.timeline_service import build_timeline, group_by_year, distinct_filter_values
from services.trend_analyzer import analyze_trends, chart_data
from services.medication_checker import check_interactions
from services.risk_engine import compute_risk_timeline
from services.ai_summary import generate_ai_summary

doctor_bp = Blueprint("doctor", __name__, url_prefix="/doctor")


def _has_access(doctor_id, patient_id):
    return DoctorPatientAccess.query.filter_by(
        doctor_id=doctor_id, patient_id=patient_id, active=True
    ).first() is not None


@doctor_bp.route("/dashboard")
@login_required
@role_required("doctor")
def dashboard():
    doctor = current_user.doctor_profile
    authorized_count = doctor.patient_access.filter_by(active=True).count()
    pending_requests = doctor.access_requests.filter_by(status="pending").count()
    recent_grants = (
        doctor.patient_access.filter_by(active=True)
        .order_by(db.desc("granted_at")).limit(5).all()
    )
    return render_template(
        "doctor/dashboard.html", doctor=doctor,
        authorized_count=authorized_count, pending_requests=pending_requests,
        recent_grants=recent_grants,
    )


@doctor_bp.route("/search", methods=["GET"])
@login_required
@role_required("doctor")
def search():
    query = request.args.get("q", "").strip()
    results = []
    if query:
        results = Patient.query.filter(
            db.or_(
                Patient.patient_code.ilike(f"%{query}%"),
                Patient.full_name.ilike(f"%{query}%"),
            )
        ).all()
        # also allow searching by linked username
        from models import User
        user_match = User.query.filter(User.username.ilike(f"%{query}%"), User.role == "patient").all()
        for u in user_match:
            if u.patient_profile and u.patient_profile not in results:
                results.append(u.patient_profile)

    doctor = current_user.doctor_profile
    enriched = []
    for p in results:
        enriched.append({
            "patient": p,
            "has_access": _has_access(doctor.id, p.id),
            "pending_request": AccessRequest.query.filter_by(
                doctor_id=doctor.id, patient_id=p.id, status="pending"
            ).first() is not None,
            "record_count": p.medical_records.count(),
            "alert_count": p.risk_alerts.count(),
        })
    return render_template("doctor/search.html", query=query, results=enriched)


@doctor_bp.route("/request-access/<int:patient_id>", methods=["POST"])
@login_required
@role_required("doctor")
def request_access(patient_id):
    doctor = current_user.doctor_profile
    if not doctor.is_verified:
        flash("Your account must be verified by an admin before requesting patient access.", "warning")
        return redirect(url_for("doctor.search", q=request.form.get("q", "")))

    patient = Patient.query.get_or_404(patient_id)
    existing = AccessRequest.query.filter_by(doctor_id=doctor.id, patient_id=patient.id, status="pending").first()
    if existing:
        flash("An access request is already pending for this patient.", "info")
    else:
        req = AccessRequest(doctor_id=doctor.id, patient_id=patient.id, status="pending")
        db.session.add(req)
        db.session.commit()
        notify(patient.user_id,
               f"Dr. {doctor.full_name} ({doctor.specialization}, {doctor.hospital}) has requested access to your records.",
               "access_request")
        log_action("patient_access_request", target_patient_id=patient.id,
                   details=f"Doctor {doctor.full_name} requested access")
        flash("Access request sent to the patient.", "success")
    return redirect(url_for("doctor.search", q=request.form.get("q", "")))


@doctor_bp.route("/patient/<int:patient_id>")
@login_required
@verified_doctor_required
def view_patient(patient_id):
    doctor = current_user.doctor_profile
    patient = Patient.query.get_or_404(patient_id)
    if not _has_access(doctor.id, patient.id):
        flash("You do not have authorized access to this patient's records.", "danger")
        return redirect(url_for("doctor.search"))

    events = build_timeline(patient)
    trend_findings = analyze_trends(patient)
    interactions = check_interactions(patient)
    risk_timeline = compute_risk_timeline(patient)
    notes = patient.clinical_notes.order_by(db.desc("created_at")).all()

    log_action("medical_record_viewed", target_patient_id=patient.id,
               details=f"Dr. {doctor.full_name} viewed patient {patient.patient_code}")

    return render_template(
        "doctor/patient_view.html", patient=patient, events=events[:10],
        trend_findings=trend_findings, interactions=interactions,
        risk_timeline=risk_timeline, notes=notes,
    )


@doctor_bp.route("/patient/<int:patient_id>/timeline")
@login_required
@verified_doctor_required
def patient_timeline(patient_id):
    doctor = current_user.doctor_profile
    patient = Patient.query.get_or_404(patient_id)
    if not _has_access(doctor.id, patient.id):
        abort(403)
    filters = {k: v for k, v in request.args.items() if v}
    events = build_timeline(patient, filters)
    grouped = group_by_year(events)
    hospitals, doctors, types = distinct_filter_values(patient)
    return render_template(
        "doctor/patient_timeline.html", patient=patient, grouped=grouped,
        hospitals=hospitals, doctors=doctors, types=types, filters=filters,
    )


@doctor_bp.route("/patient/<int:patient_id>/lab-trends")
@login_required
@verified_doctor_required
def patient_lab_trends(patient_id):
    doctor = current_user.doctor_profile
    patient = Patient.query.get_or_404(patient_id)
    if not _has_access(doctor.id, patient.id):
        abort(403)
    findings = analyze_trends(patient)
    charts = chart_data(patient)
    return render_template("doctor/patient_lab_trends.html", patient=patient, findings=findings, charts=charts)


@doctor_bp.route("/patient/<int:patient_id>/ai-insights")
@login_required
@verified_doctor_required
def patient_ai_insights(patient_id):
    doctor = current_user.doctor_profile
    patient = Patient.query.get_or_404(patient_id)
    if not _has_access(doctor.id, patient.id):
        abort(403)
    summary = generate_ai_summary(patient)
    risk_timeline = compute_risk_timeline(patient)
    return render_template("doctor/patient_ai_insights.html", patient=patient, summary=summary, risk_timeline=risk_timeline)


@doctor_bp.route("/patient/<int:patient_id>/add-note", methods=["POST"])
@login_required
@verified_doctor_required
def add_note(patient_id):
    doctor = current_user.doctor_profile
    patient = Patient.query.get_or_404(patient_id)
    if not _has_access(doctor.id, patient.id):
        abort(403)
    note_text = request.form.get("note_text", "").strip()
    note_type = request.form.get("note_type", "consultation")
    if note_text:
        note = ClinicalNote(doctor_id=doctor.id, patient_id=patient.id, note_text=note_text, note_type=note_type)
        db.session.add(note)
        db.session.commit()
        log_action("clinical_note_added", target_patient_id=patient.id,
                   details=f"Dr. {doctor.full_name} added a {note_type} note")
        flash("Clinical note added.", "success")
    return redirect(url_for("doctor.view_patient", patient_id=patient.id))


@doctor_bp.route("/profile")
@login_required
@role_required("doctor")
def profile():
    return render_template("doctor/profile.html", doctor=current_user.doctor_profile)
