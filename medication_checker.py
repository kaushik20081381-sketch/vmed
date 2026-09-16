"""Small configurable medication-interaction dataset for the hackathon MVP.
This is NOT a clinical decision engine -- flagged pairs must be verified by a
qualified healthcare professional."""

# Interaction pairs are stored as a frozenset of two lowercase generic names.
INTERACTION_RULES = [
    {
        "pair": frozenset({"warfarin", "aspirin"}),
        "message": "Combined use may increase bleeding risk.",
    },
    {
        "pair": frozenset({"metformin", "contrast dye"}),
        "message": "Potential risk of lactic acidosis around imaging procedures using contrast dye.",
    },
    {
        "pair": frozenset({"lisinopril", "potassium"}),
        "message": "Combined use may raise potassium to abnormal levels (hyperkalemia risk).",
    },
    {
        "pair": frozenset({"simvastatin", "clarithromycin"}),
        "message": "Combined use may increase the risk of muscle toxicity (myopathy).",
    },
    {
        "pair": frozenset({"ibuprofen", "lisinopril"}),
        "message": "NSAIDs may reduce the effectiveness of blood-pressure medication and affect kidney function.",
    },
    {
        "pair": frozenset({"metformin", "furosemide"}),
        "message": "Diuretics may affect blood glucose control when combined with metformin.",
    },
    {
        "pair": frozenset({"sertraline", "tramadol"}),
        "message": "Combined use may increase the risk of serotonin syndrome.",
    },
]


def _normalize(name):
    return (name or "").strip().lower()


def check_interactions(patient):
    """Check the patient's currently-active + recent medications against the ruleset."""
    meds = patient.medications.all()
    names = {_normalize(m.medicine_name) for m in meds}

    findings = []
    for rule in INTERACTION_RULES:
        if rule["pair"].issubset(names):
            drug_a, drug_b = tuple(rule["pair"])
            findings.append({
                "drug_a": drug_a.title(),
                "drug_b": drug_b.title(),
                "message": rule["message"],
                "disclaimer": (
                    "These medications may have a clinically relevant interaction. "
                    "Please verify with a qualified healthcare professional."
                ),
            })
    return findings
