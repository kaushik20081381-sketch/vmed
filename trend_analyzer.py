"""Laboratory trend analysis engine: increasing/decreasing trends, repeated
abnormal values, and sudden changes across a patient's lab history."""
from collections import defaultdict
from models.lab_result import REFERENCE_RANGES

SUDDEN_CHANGE_THRESHOLD = 0.20  # 20% jump between consecutive readings


def get_series_by_test(patient):
    """Return {test_name: [(date, value, is_abnormal), ...]} sorted by date."""
    series = defaultdict(list)
    for lab in patient.lab_results.all():
        series[lab.test_name].append((lab.test_date, lab.value, lab.is_abnormal, lab.unit))
    for key in series:
        series[key].sort(key=lambda t: t[0])
    return dict(series)


def analyze_trends(patient):
    """
    Returns a list of trend findings, e.g.:
    {test_name, display_name, direction, abnormal_count, total, message, severity}
    """
    series = get_series_by_test(patient)
    findings = []

    for test_name, points in series.items():
        if len(points) < 2:
            continue

        values = [p[1] for p in points]
        abnormal_count = sum(1 for p in points if p[2])
        total = len(points)
        display_name = test_name.replace("_", " ").title()

        # Direction: compare first vs last, using simple average of deltas
        first, last = values[0], values[-1]
        pct_change = (last - first) / first if first else 0
        direction = "increasing" if last > first else ("decreasing" if last < first else "stable")

        # Sudden change: any single jump between consecutive readings > threshold
        sudden = any(
            abs(values[i] - values[i - 1]) / values[i - 1] > SUDDEN_CHANGE_THRESHOLD
            for i in range(1, len(values))
            if values[i - 1]
        )

        severity = "info"
        message = None

        if abnormal_count >= 2:
            severity = "attention"
            message = (
                f"{display_name} has shown repeated abnormal values across "
                f"{abnormal_count} of {total} recorded results."
            )
        elif direction != "stable" and abs(pct_change) >= 0.10:
            severity = "review"
            message = (
                f"{display_name} has shown a persistent {direction} trend across "
                f"recorded laboratory results."
            )
        elif sudden:
            severity = "review"
            message = f"{display_name} showed a sudden change between two consecutive readings."

        if message:
            findings.append({
                "test_name": test_name,
                "display_name": display_name,
                "direction": direction,
                "pct_change": round(pct_change * 100, 1),
                "abnormal_count": abnormal_count,
                "total": total,
                "message": message,
                "severity": severity,
                "note": "This is a potential trend for professional review, not a diagnosis.",
            })

    return findings


def chart_data(patient):
    """Data shaped for Chart.js line charts: {test_name: {labels: [...], values: [...], unit}}"""
    series = get_series_by_test(patient)
    out = {}
    for test_name, points in series.items():
        out[test_name] = {
            "display_name": test_name.replace("_", " ").title(),
            "labels": [p[0].isoformat() for p in points],
            "values": [p[1] for p in points],
            "unit": points[-1][3] if points else "",
            "reference_range": REFERENCE_RANGES.get(test_name),
        }
    return out
