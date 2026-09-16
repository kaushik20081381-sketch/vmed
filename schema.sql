-- MedTimeline AI -- MySQL schema
-- This mirrors the SQLAlchemy models exactly. You normally do NOT need to run
-- this by hand -- `flask --app app shell` / seed_demo_data.py calls
-- db.create_all() which creates these tables automatically the first time
-- the app runs against an empty database. This file is provided for
-- reference, manual setup, or review by hackathon judges.

CREATE DATABASE IF NOT EXISTS medtimeline_ai
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE medtimeline_ai;

-- ---------------------------------------------------------------------
-- users : shared login table for all three roles
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(80) NOT NULL UNIQUE,
  email VARCHAR(120) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(20) NOT NULL,                 -- patient | doctor | admin
  is_active_account BOOLEAN NOT NULL DEFAULT TRUE,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  last_login_at DATETIME NULL,
  INDEX idx_users_username (username),
  INDEX idx_users_email (email)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- patients
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS patients (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL UNIQUE,
  patient_code VARCHAR(20) NOT NULL UNIQUE,  -- e.g. MTA-2026-00001
  full_name VARCHAR(150) NOT NULL,
  phone VARCHAR(20),
  date_of_birth DATE NOT NULL,
  gender VARCHAR(20),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_patients_code (patient_code),
  CONSTRAINT fk_patients_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- doctors
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS doctors (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL UNIQUE,
  full_name VARCHAR(150) NOT NULL,
  phone VARCHAR(20),
  specialization VARCHAR(120) NOT NULL,
  hospital VARCHAR(150) NOT NULL,
  license_number VARCHAR(80) NOT NULL UNIQUE,
  verification_status VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending|verified|rejected
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_doctors_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- admins
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS admins (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL UNIQUE,
  full_name VARCHAR(150) NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_admins_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- medical_records : uploaded source documents / visit metadata
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS medical_records (
  id INT AUTO_INCREMENT PRIMARY KEY,
  patient_id INT NOT NULL,
  uploaded_by_user_id INT NOT NULL,
  hospital VARCHAR(150),
  doctor_name VARCHAR(150),
  record_type VARCHAR(50) NOT NULL,          -- hospital_visit|lab_report|medication|diagnosis|other
  description TEXT,
  file_path VARCHAR(300),
  original_filename VARCHAR(300),
  record_date DATE NOT NULL,
  is_demo_data BOOLEAN DEFAULT FALSE,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_records_patient (patient_id),
  CONSTRAINT fk_records_patient FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
  CONSTRAINT fk_records_uploader FOREIGN KEY (uploaded_by_user_id) REFERENCES users(id)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- lab_results
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS lab_results (
  id INT AUTO_INCREMENT PRIMARY KEY,
  patient_id INT NOT NULL,
  medical_record_id INT NULL,
  test_name VARCHAR(80) NOT NULL,            -- normalized key e.g. "glucose"
  display_name VARCHAR(120),
  value FLOAT NOT NULL,
  unit VARCHAR(30),
  test_date DATE NOT NULL,
  hospital VARCHAR(150),
  is_demo_data BOOLEAN DEFAULT FALSE,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_labs_patient (patient_id),
  INDEX idx_labs_test_name (test_name),
  CONSTRAINT fk_labs_patient FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
  CONSTRAINT fk_labs_record FOREIGN KEY (medical_record_id) REFERENCES medical_records(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- medications
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS medications (
  id INT AUTO_INCREMENT PRIMARY KEY,
  patient_id INT NOT NULL,
  medicine_name VARCHAR(120) NOT NULL,
  dose VARCHAR(60),
  frequency VARCHAR(60),
  start_date DATE NOT NULL,
  end_date DATE NULL,
  prescribing_doctor VARCHAR(150),
  hospital VARCHAR(150),
  is_demo_data BOOLEAN DEFAULT FALSE,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_meds_patient (patient_id),
  CONSTRAINT fk_meds_patient FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- diagnoses
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS diagnoses (
  id INT AUTO_INCREMENT PRIMARY KEY,
  patient_id INT NOT NULL,
  condition_name VARCHAR(150) NOT NULL,
  diagnosis_date DATE NOT NULL,
  hospital VARCHAR(150),
  doctor_name VARCHAR(150),
  notes TEXT,
  is_demo_data BOOLEAN DEFAULT FALSE,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_diag_patient (patient_id),
  CONSTRAINT fk_diag_patient FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- access_requests : doctor -> patient access requests (pending review)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS access_requests (
  id INT AUTO_INCREMENT PRIMARY KEY,
  doctor_id INT NOT NULL,
  patient_id INT NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending|approved|rejected
  requested_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  responded_at DATETIME NULL,
  INDEX idx_req_doctor (doctor_id),
  INDEX idx_req_patient (patient_id),
  CONSTRAINT fk_req_doctor FOREIGN KEY (doctor_id) REFERENCES doctors(id) ON DELETE CASCADE,
  CONSTRAINT fk_req_patient FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- doctor_patient_access : the granted/active permission itself
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS doctor_patient_access (
  id INT AUTO_INCREMENT PRIMARY KEY,
  doctor_id INT NOT NULL,
  patient_id INT NOT NULL,
  granted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  revoked_at DATETIME NULL,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  UNIQUE KEY uq_doctor_patient (doctor_id, patient_id),
  INDEX idx_dpa_doctor (doctor_id),
  INDEX idx_dpa_patient (patient_id),
  CONSTRAINT fk_dpa_doctor FOREIGN KEY (doctor_id) REFERENCES doctors(id) ON DELETE CASCADE,
  CONSTRAINT fk_dpa_patient FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- clinical_notes : doctor consultation / follow-up / observation notes
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS clinical_notes (
  id INT AUTO_INCREMENT PRIMARY KEY,
  doctor_id INT NOT NULL,
  patient_id INT NOT NULL,
  note_type VARCHAR(30) DEFAULT 'consultation', -- consultation|follow_up|observation
  note_text TEXT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_notes_doctor (doctor_id),
  INDEX idx_notes_patient (patient_id),
  CONSTRAINT fk_notes_doctor FOREIGN KEY (doctor_id) REFERENCES doctors(id) ON DELETE CASCADE,
  CONSTRAINT fk_notes_patient FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- risk_alerts : computed risk-timeline entries (decision support, not diagnosis)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS risk_alerts (
  id INT AUTO_INCREMENT PRIMARY KEY,
  patient_id INT NOT NULL,
  year INT NOT NULL,
  level VARCHAR(20) NOT NULL,                 -- low|review|attention|high
  message VARCHAR(300) NOT NULL,
  category VARCHAR(50),                       -- lab_trend|medication|diagnosis|repeated_abnormal
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_risk_patient (patient_id),
  CONSTRAINT fk_risk_patient FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- notifications
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS notifications (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  message VARCHAR(300) NOT NULL,
  category VARCHAR(50) DEFAULT 'info',        -- info|access_request|alert|system
  link VARCHAR(300),
  is_read BOOLEAN DEFAULT FALSE,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_notif_user (user_id),
  CONSTRAINT fk_notif_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- audit_logs
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_logs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  actor_user_id INT NULL,
  action VARCHAR(80) NOT NULL,                -- login|logout|upload_record|access_approved|...
  target_patient_id INT NULL,
  details VARCHAR(400),
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_audit_actor (actor_user_id),
  INDEX idx_audit_patient (target_patient_id),
  CONSTRAINT fk_audit_actor FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE SET NULL,
  CONSTRAINT fk_audit_patient FOREIGN KEY (target_patient_id) REFERENCES patients(id) ON DELETE SET NULL
) ENGINE=InnoDB;
