"""AI Clinical Summary generator.

Primary path: rule-based summarizer built from the trend/risk/medication
engines -- always available, no external dependency, and fully deterministic
for demo purposes.

Optional path: if ANTHROPIC_API_KEY is configured, ask the model to turn the
same structured findings into a more natural clinical narrative. If the
call fails for any reason (no key, no network, API error), we transparently
fall back to the rule-based summary so the app always works.
"""
import os
import json
import urllib.request
import urllib.error

from services.trend_analyzer import analyze_trends
from services.medication_checker import check_interactions
from services.risk_engine import compute_risk_timeline, overall_risk_level

DISCLAIMER = (
    "AI-generated information is intended to support clinical review and does "
    "not replace professional medical judgment or diagnosis."
)


def _gather_structured_findings(patient):
    diagnoses = patient.diagnoses.order_by(None).all()
    diagnosis_names = sorted({d.condition_name for d in diagnoses})

    trend_findings = analyze_trends(patient)
    interactions = check_interactions(patient)
    risk_timeline = compute_risk_timeline(patient, persist=True)
    risk_level = overall_risk_level(risk_timeline)

    repeated = [f for f in trend_findings if f["severity"] == "attention"]
    recent_years = sorted(risk_timeline.keys())[-1:] if risk_timeline else []
    recent_changes = []
    for y in recent_years:
        recent_changes.extend(risk_timeline[y]["messages"])

    return {
        "diagnosis_names": diagnosis_names,
        "trend_findings": trend_findings,
        "interactions": interactions,
        "risk_timeline": risk_timeline,
        "risk_level": risk_level,
        "repeated_findings": repeated,
        "recent_changes": recent_changes,
    }


def _rule_based_summary(patient, structured=None):
    if structured is None:
        structured = _gather_structured_findings(patient)

    overview = (
        f"{patient.full_name} ({patient.age if patient.age is not None else 'unknown'} yrs) has "
        f"{len(structured['diagnosis_names'])} recorded condition(s) and "
        f"{patient.lab_results.count()} laboratory result(s) on file."
    )

    important_conditions = structured["diagnosis_names"] or ["No conditions recorded yet."]

    abnormal_trends = [f["message"] for f in structured["trend_findings"]] or [
        "No significant laboratory trends detected yet."
    ]

    medication_review = (
        [f"{i['drug_a']} + {i['drug_b']}: {i['message']}" for i in structured["interactions"]]
        or ["No known medication interactions detected in the current regimen."]
    )

    repeated_findings = [f["message"] for f in structured["repeated_findings"]] or [
        "No repeated abnormal findings identified."
    ]

    recent_changes = structured["recent_changes"] or ["No notable recent changes recorded."]

    warning_signals = []
    if structured["risk_level"] in ("attention", "high"):
        warning_signals.append(
            f"Overall risk signal level is currently '{structured['risk_level']}' based on recorded trends."
        )
    if structured["interactions"]:
        warning_signals.append("Potential medication interaction(s) require verification.")
    if not warning_signals:
        warning_signals = ["No high-priority warning signals identified at this time."]

    suggested_review = []
    if structured["trend_findings"]:
        suggested_review.append("Review flagged laboratory trends against clinical history.")
    if structured["interactions"]:
        suggested_review.append("Reconcile current medication list for interaction risk.")
    if structured["repeated_findings"]:
        suggested_review.append("Investigate repeated abnormal laboratory findings.")
    if not suggested_review:
        suggested_review = ["Routine follow-up as clinically indicated."]

    return {
        "source": "rule_based",
        "overview": overview,
        "important_conditions": important_conditions,
        "abnormal_trends": abnormal_trends,
        "medication_review": medication_review,
        "repeated_findings": repeated_findings,
        "recent_changes": recent_changes,
        "warning_signals": warning_signals,
        "suggested_review": suggested_review,
        "risk_level": structured["risk_level"],
        "disclaimer": DISCLAIMER,
    }


def _try_anthropic_narrative(patient, structured):
    """Best-effort call to the Anthropic API for a richer narrative summary.
    Returns a narrative string, or None if unavailable/failed."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None

    prompt = (
        "You are assisting a clinician by summarizing structured, already-computed "
        "findings about a patient's longitudinal record into a short clinical-style "
        "summary (5-8 bullet points). Do not invent findings beyond what is given. "
        "Always frame findings as decision-support requiring professional verification, "
        "never as a diagnosis.\n\n"
        f"Structured findings (JSON):\n{json.dumps(structured, default=str)}\n"
    )

    body = json.dumps({
        "model": "claude-sonnet-4-6",
        "max_tokens": 600,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            parts = [b.get("text", "") for b in payload.get("content", []) if b.get("type") == "text"]
            text = "\n".join(p for p in parts if p).strip()
            return text or None
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, OSError):
        return None


def generate_ai_summary(patient):
    """Public entry point used by routes. Always returns a usable summary dict."""
    structured = _gather_structured_findings(patient)
    summary = _rule_based_summary(patient, structured)
    narrative = _try_anthropic_narrative(patient, structured)
    if narrative:
        summary["source"] = "anthropic_api"
        summary["narrative"] = narrative
    return summary
