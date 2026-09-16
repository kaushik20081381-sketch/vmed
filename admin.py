from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user

from extensions import db
from models import User, Patient, Doctor, MedicalRecord, LabResult, AccessRequest, AuditLog
from utils import role_required, notify
from services.audit_service import log_action

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/dashboard")
@login_required
@role_required("admin")
def dashboard():
    stats = {
        "total_patients": Patient.query.count(),
        "total_doctors": Doctor.query.count(),
        "verified_doctors": Doctor.query.filter_by(verification_status="verified").count(),
        "pending_doctors": Doctor.query.filter_by(verification_status="pending").count(),
        "total_records": MedicalRecord.query.count(),
        "total_labs": LabResult.query.count(),
        "total_access_requests": AccessRequest.query.count(),
        "active_users": User.query.filter_by(is_active_account=True).count(),
    }
    pending_doctors = Doctor.query.filter_by(verification_status="pending").order_by(db.desc("created_at")).limit(5).all()
    recent_logs = AuditLog.query.order_by(db.desc("timestamp")).limit(10).all()
    return render_template("admin/dashboard.html", stats=stats, pending_doctors=pending_doctors, recent_logs=recent_logs)


@admin_bp.route("/doctors")
@login_required
@role_required("admin")
def doctors():
    status = request.args.get("status", "")
    q = Doctor.query
    if status:
        q = q.filter_by(verification_status=status)
    doctor_list = q.order_by(db.desc("created_at")).all()
    return render_template("admin/doctors.html", doctors=doctor_list, status=status)


@admin_bp.route("/doctors/<int:doctor_id>/verify", methods=["POST"])
@login_required
@role_required("admin")
def verify_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    doctor.verification_status = "verified"
    db.session.commit()
    notify(doctor.user_id, "Your doctor account has been verified. You can now request patient access.", "system")
    log_action("doctor_verification", details=f"Admin verified doctor {doctor.full_name}")
    flash(f"Dr. {doctor.full_name} has been verified.", "success")
    return redirect(url_for("admin.doctors"))


@admin_bp.route("/doctors/<int:doctor_id>/reject", methods=["POST"])
@login_required
@role_required("admin")
def reject_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    doctor.verification_status = "rejected"
    db.session.commit()
    notify(doctor.user_id, "Your doctor account application was rejected. Contact support for details.", "system")
    log_action("doctor_verification", details=f"Admin rejected doctor {doctor.full_name}")
    flash(f"Dr. {doctor.full_name} has been rejected.", "info")
    return redirect(url_for("admin.doctors"))


@admin_bp.route("/users")
@login_required
@role_required("admin")
def users():
    role_filter = request.args.get("role", "")
    q = User.query
    if role_filter:
        q = q.filter_by(role=role_filter)
    user_list = q.order_by(db.desc("created_at")).all()
    return render_template("admin/users.html", users=user_list, role_filter=role_filter)


@admin_bp.route("/users/<int:user_id>/toggle-active", methods=["POST"])
@login_required
@role_required("admin")
def toggle_active(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == "admin":
        flash("Admin accounts cannot be deactivated from this panel.", "warning")
        return redirect(url_for("admin.users"))
    user.is_active_account = not user.is_active_account
    db.session.commit()
    state = "activated" if user.is_active_account else "deactivated"
    log_action("account_status_change", details=f"Admin {state} account '{user.username}'")
    flash(f"Account {state}.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/access-requests")
@login_required
@role_required("admin")
def access_requests():
    reqs = AccessRequest.query.order_by(db.desc("requested_at")).all()
    return render_template("admin/access_requests.html", requests=reqs)


@admin_bp.route("/hospitals")
@login_required
@role_required("admin")
def hospitals():
    hospital_doctors = db.session.query(Doctor.hospital, db.func.count(Doctor.id)).group_by(Doctor.hospital).all()
    return render_template("admin/hospitals.html", hospital_doctors=hospital_doctors)


@admin_bp.route("/audit-logs")
@login_required
@role_required("admin")
def audit_logs():
    logs = AuditLog.query.order_by(db.desc("timestamp")).limit(300).all()
    return render_template("admin/audit_logs.html", logs=logs)


@admin_bp.route("/analytics")
@login_required
@role_required("admin")
def analytics():
    stats = {
        "total_patients": Patient.query.count(),
        "total_doctors": Doctor.query.count(),
        "verified_doctors": Doctor.query.filter_by(verification_status="verified").count(),
        "pending_doctors": Doctor.query.filter_by(verification_status="pending").count(),
        "rejected_doctors": Doctor.query.filter_by(verification_status="rejected").count(),
        "total_records": MedicalRecord.query.count(),
        "total_labs": LabResult.query.count(),
        "total_access_requests": AccessRequest.query.count(),
        "approved_access_requests": AccessRequest.query.filter_by(status="approved").count(),
        "active_users": User.query.filter_by(is_active_account=True).count(),
    }
    return render_template("admin/analytics.html", stats=stats)
