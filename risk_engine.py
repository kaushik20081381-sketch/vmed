"""Risk timeline engine: turns trend findings, medication interactions and
diagnoses into a year-by-year risk signal timeline. This is decision-support
information for clinical review -- never presented as a diagnosis."""
from collections import defaultdict
from extensions import db
from models import RiskAlert
from services.trend_analyzer import analyze_trends, get_series_by_test
from services.medication_checker import check_interactions

LEVEL_RANK = {"low": 0, "review": 1, "attention": 2, "high": 3}


def compute_risk_timeline(patient, persist=True):
    """
    Build a dict {year: {"level": ..., "messages": [...]}} summarizing risk
    signals per year, and optionally persist as RiskAlert rows.
    """
    year_signals = defaultdict(lambda: {"level": "low", "messages": [], "categories": set()})

    # 1. Diagnoses recorded per year -> baseline "low concern" entries
    for d in patient.diagnoses.all():
        y = d.diagnosis_date.year
        year_signals[y]["messages"].append(f"{d.condition_name} recorded")
        year_signals[y]["categories"].add("diagnosis")

    # 2. Lab trend findings -> attach to the year of the most recent abnormal reading
    series = get_series_by_test(patient)
    trend_findings = analyze_trends(patient)
    for finding in trend_findings:
        points = series.get(finding["test_name"], [])
        abnormal_points = [p for p in points if p[2]]
        target_points = abnormal_points or points
        if not target_points:
            continue
        y = target_points[-1][0].year
        level = "attention" if finding["severity"] == "attention" else "review"
        year_signals[y]["messages"].append(finding["message"])
        year_signals[y]["categories"].add("lab_trend")
        if LEVEL_RANK[level] > LEVEL_RANK[year_signals[y]["level"]]:
            year_signals[y]["level"] = level

    # 3. Repeated abnormal values across multiple years -> escalate the latest year to "high"
    for test_name, points in series.items():
        abnormal_years = sorted({p[0].year for p in points if p[2]})
        if len(abnormal_years) >= 2:
            latest = abnormal_years[-1]
            year_signals[latest]["messages"].append(
                f"Multiple abnormal {test_name.replace('_', ' ')} trends detected across "
                f"{len(abnormal_years)} years."
            )
            year_signals[latest]["categories"].add("repeated_abnormal")
            year_signals[latest]["level"] = "high"

    # 4. Medication interactions -> flag current year
    from datetime import date
    interactions = check_interactions(patient)
    if interactions:
        current_year = date.today().year
        for i in interactions:
            year_signals[current_year]["messages"].append(
                f"Potential interaction: {i['drug_a']} + {i['drug_b']}."
            )
            year_signals[current_year]["categories"].add("medication")
        if LEVEL_RANK["attention"] > LEVEL_RANK[year_signals[current_year]["level"]]:
            year_signals[current_year]["level"] = "attention"

    result = dict(sorted(year_signals.items()))

    if persist:
        _persist_alerts(patient, result)

    return result


def _persist_alerts(patient, year_signals):
    """Refresh the risk_alerts table for this patient (simple replace strategy)."""
    RiskAlert.query.filter_by(patient_id=patient.id).delete()
    for year, data in year_signals.items():
        for msg in data["messages"]:
            db.session.add(RiskAlert(
                patient_id=patient.id,
                year=year,
                level=data["level"],
                message=f"{msg} — Risk signals identified for clinical review.",
                category=",".join(data["categories"]) if data["categories"] else None,
            ))
    db.session.commit()


def overall_risk_level(year_signals):
    if not year_signals:
        return "low"
    latest_year = max(year_signals.keys())
    return year_signals[latest_year]["level"]
