from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user

from extensions import db
from models import AccessRequest, DoctorPatientAccess, Notification
from utils import role_required, notify
from services.audit_service import log_action
from services.timeline_service import build_timeline, group_by_year, distinct_filter_values
from services.trend_analyzer import analyze_trends, chart_data
from services.medication_checker import check_interactions
from services.risk_engine import compute_risk_timeline
from services.ai_summary import generate_ai_summary

patient_bp = Blueprint("patient", __name__, url_prefix="/patient")


def _get_patient():
    return current_user.patient_profile


@patient_bp.route("/dashboard")
@login_required
@role_required("patient")
def dashboard():
    patient = _get_patient()
    events = build_timeline(patient)
    active_doctors = DoctorPatientAccess.query.filter_by(patient_id=patient.id, active=True).count()
    trend_findings = analyze_trends(patient)
    latest_labs = patient.lab_results.order_by(db.desc("test_date")).limit(5).all()
    return render_template(
        "patient/dashboard.html",
        patient=patient,
        record_count=patient.medical_records.count(),
        alert_count=len(trend_findings),
        active_doctors=active_doctors,
        latest_labs=latest_labs,
        recent_events=events[:6],
    )


@patient_bp.route("/profile", methods=["GET", "POST"])
@login_required
@role_required("patient")
def profile():
    patient = _get_patient()
    if request.method == "POST":
        patient.full_name = request.form.get("full_name", patient.full_name).strip()
        patient.phone = request.form.get("phone", patient.phone).strip()
        patient.gender = request.form.get("gender", patient.gender).strip()
        current_user.email = request.form.get("email", current_user.email).strip()
        db.session.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for("patient.profile"))
    return render_template("patient/profile.html", patient=patient)


@patient_bp.route("/change-password", methods=["GET", "POST"])
@login_required
@role_required("patient")
def change_password():
    if request.method == "POST":
        current_pw = request.form.get("current_password", "")
        new_pw = request.form.get("new_password", "")
        confirm_pw = request.form.get("confirm_password", "")
        if not current_user.check_password(current_pw):
            flash("Current password is incorrect.", "danger")
        elif len(new_pw) < 6:
            flash("New password must be at least 6 characters.", "danger")
        elif new_pw != confirm_pw:
            flash("New passwords do not match.", "danger")
        else:
            current_user.set_password(new_pw)
            db.session.commit()
            flash("Password changed successfully.", "success")
            return redirect(url_for("patient.profile"))
    return render_template("patient/change_password.html")


@patient_bp.route("/timeline")
@login_required
@role_required("patient")
def timeline():
    patient = _get_patient()
    filters = {k: v for k, v in request.args.items() if v}
    events = build_timeline(patient, filters)
    grouped = group_by_year(events)
    hospitals, doctors, types = distinct_filter_values(patient)
    return render_template(
        "patient/timeline.html", patient=patient, grouped=grouped,
        hospitals=hospitals, doctors=doctors, types=types, filters=filters,
    )


@patient_bp.route("/records")
@login_required
@role_required("patient")
def records():
    patient = _get_patient()
    records = patient.medical_records.order_by(db.desc("record_date")).all()
    return render_template("patient/records.html", patient=patient, records=records)


@patient_bp.route("/lab-results")
@login_required
@role_required("patient")
def lab_results():
    patient = _get_patient()
    labs = patient.lab_results.order_by(db.desc("test_date")).all()
    charts = chart_data(patient)
    return render_template("patient/lab_results.html", patient=patient, labs=labs, charts=charts)


@patient_bp.route("/diagnoses")
@login_required
@role_required("patient")
def diagnoses():
    patient = _get_patient()
    items = patient.diagnoses.order_by(db.desc("diagnosis_date")).all()
    return render_template("patient/diagnoses.html", patient=patient, items=items)


@patient_bp.route("/medications")
@login_required
@role_required("patient")
def medications():
    patient = _get_patient()
    items = patient.medications.order_by(db.desc("start_date")).all()
    interactions = check_interactions(patient)
    return render_template("patient/medications.html", patient=patient, items=items, interactions=interactions)


@patient_bp.route("/health-trends")
@login_required
@role_required("patient")
def health_trends():
    patient = _get_patient()
    findings = analyze_trends(patient)
    charts = chart_data(patient)
    return render_template("patient/health_trends.html", patient=patient, findings=findings, charts=charts)


@patient_bp.route("/ai-insights")
@login_required
@role_required("patient")
def ai_insights():
    patient = _get_patient()
    summary = generate_ai_summary(patient)
    risk_timeline = compute_risk_timeline(patient)
    return render_template("patient/ai_insights.html", patient=patient, summary=summary, risk_timeline=risk_timeline)


@patient_bp.route("/doctor-access", methods=["GET"])
@login_required
@role_required("patient")
def doctor_access():
    patient = _get_patient()
    pending_requests = patient.access_requests.filter_by(status="pending").order_by(db.desc("requested_at")).all()
    history_requests = patient.access_requests.filter(AccessRequest.status != "pending").order_by(db.desc("requested_at")).all()
    active_grants = patient.doctor_access.filter_by(active=True).all()
    return render_template(
        "patient/doctor_access.html", patient=patient,
        pending_requests=pending_requests, history_requests=history_requests, active_grants=active_grants,
    )


@patient_bp.route("/doctor-access/<int:request_id>/approve", methods=["POST"])
@login_required
@role_required("patient")
def approve_access(request_id):
    patient = _get_patient()
    req = AccessRequest.query.filter_by(id=request_id, patient_id=patient.id, status="pending").first_or_404()
    req.status = "approved"
    req.responded_at = datetime.utcnow()

    grant = DoctorPatientAccess.query.filter_by(doctor_id=req.doctor_id, patient_id=patient.id).first()
    if grant:
        grant.active = True
        grant.revoked_at = None
    else:
        grant = DoctorPatientAccess(doctor_id=req.doctor_id, patient_id=patient.id, active=True)
        db.session.add(grant)

    db.session.commit()
    notify(req.doctor.user_id, f"Your access request for patient {patient.patient_code} was approved.", "access_request")
    log_action("access_approved", target_patient_id=patient.id,
               details=f"Patient approved access for doctor_id={req.doctor_id}")
    flash("Access approved.", "success")
    return redirect(url_for("patient.doctor_access"))


@patient_bp.route("/doctor-access/<int:request_id>/reject", methods=["POST"])
@login_required
@role_required("patient")
def reject_access(request_id):
    patient = _get_patient()
    req = AccessRequest.query.filter_by(id=request_id, patient_id=patient.id, status="pending").first_or_404()
    req.status = "rejected"
    req.responded_at = datetime.utcnow()
    db.session.commit()
    notify(req.doctor.user_id, f"Your access request for patient {patient.patient_code} was rejected.", "access_request")
    log_action("access_rejected", target_patient_id=patient.id,
               details=f"Patient rejected access for doctor_id={req.doctor_id}")
    flash("Access request rejected.", "info")
    return redirect(url_for("patient.doctor_access"))


@patient_bp.route("/doctor-access/<int:grant_id>/revoke", methods=["POST"])
@login_required
@role_required("patient")
def revoke_access(grant_id):
    patient = _get_patient()
    grant = DoctorPatientAccess.query.filter_by(id=grant_id, patient_id=patient.id).first_or_404()
    grant.active = False
    grant.revoked_at = datetime.utcnow()
    db.session.commit()
    notify(grant.doctor.user_id, f"Your access to patient {patient.patient_code} has been revoked.", "access_request")
    log_action("access_revoked", target_patient_id=patient.id,
               details=f"Patient revoked access for doctor_id={grant.doctor_id}")
    flash("Access revoked.", "info")
    return redirect(url_for("patient.doctor_access"))


@patient_bp.route("/notifications")
@login_required
@role_required("patient")
def notifications():
    items = Notification.query.filter_by(user_id=current_user.id).order_by(db.desc("created_at")).all()
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    return render_template("patient/notifications.html", items=items)
