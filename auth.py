from datetime import datetime, date
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user

from extensions import db
from models import User, Patient, Doctor, Admin
from services.audit_service import log_action

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login")
def login_select():
    if current_user.is_authenticated:
        return redirect(url_for(f"{current_user.role}.dashboard"))
    return render_template("auth/login_select.html")


def _do_login(username, password, expected_role):
    user = User.query.filter(
        (User.username == username) | (User.email == username)
    ).first()
    if not user or not user.check_password(password) or user.role != expected_role:
        flash("Invalid credentials or account type.", "danger")
        return None
    if not user.is_active_account:
        flash("This account has been deactivated. Contact the administrator.", "danger")
        return None
    login_user(user)
    user.last_login_at = datetime.utcnow()
    db.session.commit()
    target_patient_id = user.patient_profile.id if user.role == "patient" and user.patient_profile else None
    log_action("login", target_patient_id=target_patient_id, details=f"{user.role} '{user.username}' logged in.")
    return user


@auth_bp.route("/login/patient", methods=["GET", "POST"])
def patient_login():
    if request.method == "POST":
        user = _do_login(request.form.get("username", "").strip(), request.form.get("password", ""), "patient")
        if user:
            return redirect(url_for("patient.dashboard"))
    return render_template("auth/patient_login.html")


@auth_bp.route("/login/doctor", methods=["GET", "POST"])
def doctor_login():
    if request.method == "POST":
        user = _do_login(request.form.get("username", "").strip(), request.form.get("password", ""), "doctor")
        if user:
            return redirect(url_for("doctor.dashboard"))
    return render_template("auth/doctor_login.html")


@auth_bp.route("/login/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        user = _do_login(request.form.get("username", "").strip(), request.form.get("password", ""), "admin")
        if user:
            return redirect(url_for("admin.dashboard"))
    return render_template("auth/admin_login.html")


@auth_bp.route("/register/patient", methods=["GET", "POST"])
def patient_register():
    if request.method == "POST":
        f = request.form
        errors = []

        if User.query.filter_by(username=f.get("username", "").strip()).first():
            errors.append("Username already taken.")
        if User.query.filter_by(email=f.get("email", "").strip()).first():
            errors.append("Email already registered.")
        if not f.get("password") or len(f.get("password")) < 6:
            errors.append("Password must be at least 6 characters.")
        if f.get("password") != f.get("confirm_password"):
            errors.append("Passwords do not match.")
        try:
            dob = datetime.strptime(f.get("date_of_birth", ""), "%Y-%m-%d").date()
            if dob >= date.today():
                errors.append("Date of birth must be in the past.")
                dob = None
        except ValueError:
            errors.append("Please provide a valid date of birth.")
            dob = None

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("auth/patient_register.html", form=f)

        user = User(username=f["username"].strip(), email=f["email"].strip(), role="patient")
        user.set_password(f["password"])
        db.session.add(user)
        db.session.flush()

        patient = Patient(
            user_id=user.id,
            patient_code=Patient.generate_patient_code(),
            full_name=f["full_name"].strip(),
            phone=f.get("phone", "").strip(),
            date_of_birth=dob,
            gender=f.get("gender", "").strip(),
        )
        db.session.add(patient)
        db.session.commit()

        log_action("patient_registration", target_patient_id=patient.id,
                   details=f"New patient registered: {patient.patient_code}")

        flash(f"Registration successful! Your Patient ID is {patient.patient_code}. Please log in.", "success")
        return redirect(url_for("auth.patient_login"))

    return render_template("auth/patient_register.html", form={})


@auth_bp.route("/register/doctor", methods=["GET", "POST"])
def doctor_register():
    if request.method == "POST":
        f = request.form
        errors = []
        if User.query.filter_by(username=f.get("username", "").strip()).first():
            errors.append("Username already taken.")
        if User.query.filter_by(email=f.get("email", "").strip()).first():
            errors.append("Email already registered.")
        if Doctor.query.filter_by(license_number=f.get("license_number", "").strip()).first():
            errors.append("This medical registration/license number is already on file.")
        if not f.get("password") or len(f.get("password")) < 6:
            errors.append("Password must be at least 6 characters.")
        if f.get("password") != f.get("confirm_password"):
            errors.append("Passwords do not match.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("auth/doctor_register.html", form=f)

        user = User(username=f["username"].strip(), email=f["email"].strip(), role="doctor")
        user.set_password(f["password"])
        db.session.add(user)
        db.session.flush()

        doctor = Doctor(
            user_id=user.id,
            full_name=f["full_name"].strip(),
            phone=f.get("phone", "").strip(),
            specialization=f["specialization"].strip(),
            hospital=f["hospital"].strip(),
            license_number=f["license_number"].strip(),
            verification_status="pending",
        )
        db.session.add(doctor)
        db.session.commit()

        log_action("doctor_registration", details=f"New doctor registered: {doctor.full_name} (pending verification)")

        flash("Registration successful! Your account is pending admin verification before you can access patient records.", "info")
        return redirect(url_for("auth.doctor_login"))

    return render_template("auth/doctor_register.html", form={})


@auth_bp.route("/logout")
@login_required
def logout():
    log_action("logout", details=f"{current_user.role} '{current_user.username}' logged out.")
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))
