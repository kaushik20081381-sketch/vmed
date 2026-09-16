"""Builds the unified longitudinal timeline out of scattered record types."""
from collections import defaultdict


def build_timeline(patient, filters=None):
    """
    Merge medical_records, diagnoses, lab_results and medications into one
    chronologically sorted list of timeline events, optionally filtered.

    filters: dict with optional keys: year, hospital, doctor, diagnosis, record_type
    """
    filters = filters or {}
    events = []

    for r in patient.medical_records.all():
        events.append({
            "date": r.record_date,
            "type": r.record_type,
            "icon": r.icon,
            "title": r.description or r.record_type.replace("_", " ").title(),
            "hospital": r.hospital,
            "doctor": r.doctor_name,
            "detail": r.description,
            "file_path": r.file_path,
            "source": "medical_record",
        })

    for d in patient.diagnoses.all():
        events.append({
            "date": d.diagnosis_date,
            "type": "diagnosis",
            "icon": "🩺",
            "title": f"Diagnosis: {d.condition_name}",
            "hospital": d.hospital,
            "doctor": d.doctor_name,
            "detail": d.notes,
            "file_path": None,
            "source": "diagnosis",
        })

    for lab in patient.lab_results.all():
        label = (lab.display_name or lab.test_name.replace("_", " ").title())
        events.append({
            "date": lab.test_date,
            "type": "lab_report",
            "icon": "🧪",
            "title": f"{label}: {lab.value} {lab.unit or ''}".strip(),
            "hospital": lab.hospital,
            "doctor": None,
            "detail": "Abnormal value" if lab.is_abnormal else "Within reference range",
            "file_path": None,
            "source": "lab_result",
            "abnormal": lab.is_abnormal,
        })

    for m in patient.medications.all():
        events.append({
            "date": m.start_date,
            "type": "medication",
            "icon": "💊",
            "title": f"Medication started: {m.medicine_name} ({m.dose or ''})".strip(),
            "hospital": m.hospital,
            "doctor": m.prescribing_doctor,
            "detail": m.frequency,
            "file_path": None,
            "source": "medication",
        })

    # Apply filters
    def matches(e):
        if filters.get("year") and (not e["date"] or e["date"].year != int(filters["year"])):
            return False
        if filters.get("hospital") and (e.get("hospital") or "").lower() != filters["hospital"].lower():
            return False
        if filters.get("doctor") and (e.get("doctor") or "").lower() != filters["doctor"].lower():
            return False
        if filters.get("record_type") and e["type"] != filters["record_type"]:
            return False
        if filters.get("diagnosis") and filters["diagnosis"].lower() not in e["title"].lower():
            return False
        return True

    events = [e for e in events if matches(e)]
    events.sort(key=lambda e: e["date"] or 0, reverse=True)
    return events


def group_by_year(events):
    grouped = defaultdict(list)
    for e in events:
        year = e["date"].year if e["date"] else "Unknown"
        grouped[year].append(e)
    return dict(sorted(grouped.items(), key=lambda kv: str(kv[0]), reverse=True))


def distinct_filter_values(patient):
    """Collect distinct hospitals / doctors / record types present in a patient's data, for filter dropdowns."""
    hospitals, doctors, types = set(), set(), set()
    for r in patient.medical_records.all():
        if r.hospital:
            hospitals.add(r.hospital)
        if r.doctor_name:
            doctors.add(r.doctor_name)
        types.add(r.record_type)
    for d in patient.diagnoses.all():
        if d.hospital:
            hospitals.add(d.hospital)
        if d.doctor_name:
            doctors.add(d.doctor_name)
        types.add("diagnosis")
    for m in patient.medications.all():
        if m.hospital:
            hospitals.add(m.hospital)
        if m.prescribing_doctor:
            doctors.add(m.prescribing_doctor)
        types.add("medication")
    types.add("lab_report")
    return sorted(hospitals), sorted(doctors), sorted(types)
