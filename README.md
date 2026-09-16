# MedTimeline AI — Intelligent Longitudinal Medical Record Analysis Platform

Turn fragmented medical records into one intelligent, chronological health story —
with laboratory trend detection, medication-interaction review, a risk timeline,
and an AI clinical summary to support (never replace) a doctor's judgment.

Built with **Flask + Jinja2** (frontend), **Python/Flask** (backend), and **MySQL**
via **SQLAlchemy** (database).

> ⚠️ All patient data referenced in this README (Priya Kumar / `MTA-2026-00001`) is
> **synthetic demo data**, clearly flagged in the database with `is_demo_data=True`.
> This project is a hackathon decision-support prototype, not a certified medical
> device, and never presents its output as an autonomous diagnosis.

---

## 1. Features

- Three roles — **Patient**, **Doctor**, **Admin** — with role-based auth (Flask-Login).
- Unique, permanent Patient ID generation (`MTA-2026-00001`).
- Doctor verification workflow (pending → verified/rejected) by Admin.
- Patient-controlled doctor access requests (search → request → approve/reject → revoke).
- Unified medical timeline merging hospital visits, diagnoses, lab results, and
  medications into one chronological, filterable, icon-coded view.
- Medical record upload (PDF / TXT / CSV / images) with metadata stored in MySQL.
- Laboratory trend engine (increasing/decreasing/repeated-abnormal detection) with
  Chart.js visualizations.
- Configurable medication-interaction checker (small demo ruleset).
- Rule-based **AI Clinical Summary** with an optional Anthropic API narrative mode
  (falls back automatically if no key / the call fails, so the demo always works).
- Year-by-year **Risk Timeline** (🟢🟡🟠🔴) — decision-support only, never a diagnosis.
- Admin dashboard: doctor verification, user management, access-request oversight,
  hospital/clinic directory, system analytics, and a full audit log.
- CSRF protection, hashed passwords, restricted file uploads, and an audit trail on
  every sensitive action.

---

## 2. Project structure

```
MedTimeline-AI/
├── app.py                  # App factory + entrypoint
├── config.py                # Env-driven configuration (MySQL, uploads, secrets)
├── extensions.py             # db / login_manager / csrf singletons
├── utils.py                  # role_required, verified_doctor_required, notify()
├── requirements.txt
├── .env.example
├── seed_demo_data.py          # Creates admin/doctor/patient demo accounts + history
├── database/schema.sql        # Reference MySQL schema (mirrors the models)
├── models/                    # SQLAlchemy models (one file per entity)
├── routes/                    # auth, patient, doctor, admin, records, api blueprints
├── services/                  # timeline, trend analyzer, medication checker,
│                               # risk engine, AI summary, audit logging
├── templates/                 # Jinja2 templates (base, auth, patient, doctor, admin)
├── static/css/style.css       # Design system (clinical ink/teal palette)
├── static/js/app.js           # Chart rendering, confirm dialogs, nav highlighting
└── uploads/                   # Uploaded medical record files (created at runtime)
```

---

## 3. Prerequisites

- Python 3.10+
- MySQL Server 8.0+ (running locally or reachable over the network)
- pip

---

## 4. Setup

### 4.1 Clone / unzip and install dependencies

```bash
cd MedTimeline-AI
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4.2 Create the MySQL database

Log into MySQL and either let the app create tables automatically (recommended),
or run the provided schema by hand:

```bash
mysql -u root -p -e "CREATE DATABASE medtimeline_ai CHARACTER SET utf8mb4;"
# Optional — manually apply the reference schema instead of auto-create:
mysql -u root -p medtimeline_ai < database/schema.sql
```

### 4.3 Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

```
SECRET_KEY=<a long random string>
DB_USER=root
DB_PASSWORD=<your mysql password>
DB_HOST=localhost
DB_PORT=3306
DB_NAME=medtimeline_ai
```

Leave `ANTHROPIC_API_KEY` blank to use the built-in rule-based AI summary engine
(fully offline), or set it to enable a richer narrative summary.

> Quick local demo without MySQL installed? Set `DATABASE_URL=sqlite:///demo.db`
> in `.env` instead of the `DB_*` vars. The schema and app code are otherwise
> identical — only the connection string changes. For anything beyond a quick
> personal demo, use MySQL as specified.

### 4.4 Create tables and seed demo data

The tables are created automatically the first time you run the seed script
(it calls `db.create_all()`), so you don't need a separate migration step:

```bash
python seed_demo_data.py
```

This creates:

| Role    | Username         | Password     | Notes                                   |
|---------|------------------|--------------|------------------------------------------|
| Admin   | `admin`          | `Admin@123`  | Full admin dashboard access               |
| Doctor  | `dr.arun`        | `Doctor@123` | Pre-verified, pre-granted access to demo patient |
| Patient | `priya.kumar52`  | `Patient@123`| Patient ID generated as `MTA-2026-00001`, 2023-2026 synthetic history |

**Change these passwords (or delete the demo accounts) before any real deployment.**

### 4.5 Run the app

```bash
python app.py
```

Visit **http://localhost:5000**. Use the landing page's Patient / Doctor / Admin
login buttons, or register a new patient/doctor account directly.

---

## 5. Suggested demo flow (hackathon presentation)

1. Open the landing page → register a new patient → note the generated Patient ID.
2. Log in as `priya.kumar52` (or your new patient) → view **Medical Timeline**,
   **Lab Results**, **Medications**, **Diagnoses**, **Health Trends**, **AI Insights**.
3. As the patient, go to **Doctor Access** to see the request/approval flow.
4. Log in as `dr.arun` → **Search Patient** by Patient ID / username / name.
5. Show the "Access Restricted" state on an unauthorized patient, then use
   **Request Access** — log back in as that patient to approve it.
6. Open the authorized patient's chart → full timeline, lab trend charts,
   medication interaction flag, AI Clinical Summary, and Risk Timeline.
7. Add a clinical note as the doctor.
8. Log in as `admin` → verify a pending doctor, view system analytics and the
   audit log (shows every login, upload, request, approval, and record view).

---

## 6. Security notes

- Passwords are hashed with Werkzeug's `generate_password_hash` (never stored in
  plain text).
- All state-changing routes are CSRF-protected (Flask-WTF).
- Doctors can only view a patient's records after an explicit, patient-approved
  access grant (`doctor_patient_access`, enforced in `utils.verified_doctor_required`
  and per-route ownership checks) — never merely from a search match.
- Every login, logout, registration, upload, and access-control action is written
  to `audit_logs`.
- Secrets (DB credentials, `SECRET_KEY`, optional `ANTHROPIC_API_KEY`) are read
  from environment variables via `.env` — never hardcoded.
- All AI-generated and risk-engine output is explicitly labeled as decision-support
  requiring professional review, never as an autonomous diagnosis.

---

## 7. Notes on scope (hackathon MVP)

- File upload processing focuses on reliably storing PDF/TXT/CSV/image metadata
  and structured form fields; OCR is intentionally out of scope so the demo
  never breaks on it, per the project brief.
- The medication-interaction dataset and lab reference ranges
  (`services/medication_checker.py`, `models/lab_result.py`) are small,
  clearly-labeled demo rule sets — not a substitute for a clinical
  pharmacology database.
