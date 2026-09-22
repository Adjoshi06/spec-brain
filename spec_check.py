"""Deterministic substitution check.

Runs inside the sandbox container: stdlib only, no network, no LLM. The agent passes
requirement thresholds and the candidate's attributes; this script returns pass/fail per
attribute so the model never does the comparison itself.

CLI: python spec_check.py '{"requirements": {...}, "candidate": {...}}'
"""

import json
import re
import sys

_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


def _num(value):
    """Return a float for numbers or numeric strings ('35 dB', '42%'), else None."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = _NUMBER.search(str(value))
    if not match:
        return None
    number = float(match.group())
    if "%" in str(value) and number > 1:
        number = number / 100.0
    return number


def _norm_size(value):
    """Normalise a panel size to whole inches, 'AxB': 2x2, 2' x 2', 600 x 600 mm -> 24x24."""
    if value is None:
        return None
    text = str(value).lower().replace("×", "x").replace("”", '"').replace("’", "'")
    numbers = [float(n) for n in _NUMBER.findall(text)]
    if len(numbers) < 2:
        return re.sub(r"\s", "", text)
    first, second = numbers[0], numbers[1]
    if "mm" in text:
        first, second = first / 25.4, second / 25.4
    elif "'" in text or "ft" in text or "feet" in text or "foot" in text or (first <= 4 and second <= 4):
        first, second = first * 12, second * 12
    return f"{round(first)}x{round(second)}"


def _check_min(attribute, required_min, actual):
    actual_num = _num(actual)
    check = {"attribute": attribute, "required": f">= {required_min}", "actual": actual}
    if actual_num is None:
        check["status"] = "unknown"
    elif actual_num >= float(required_min):
        check["status"] = "pass"
    else:
        check["status"] = "fail"
    return check


def check_substitute(requirements, candidate):
    """Compare a candidate product against requirement thresholds.

    requirements keys (all optional): nrc_min, cac_min, fire_classes (list), size, recycled_min
    candidate keys: nrc, cac, fire_class, size, recycled (None when the source does not say)
    """
    checks = []

    if "nrc_min" in requirements:
        checks.append(_check_min("nrc", requirements["nrc_min"], candidate.get("nrc")))

    if "cac_min" in requirements:
        checks.append(_check_min("cac", requirements["cac_min"], candidate.get("cac")))

    if "fire_classes" in requirements:
        allowed = [str(c).strip().lower() for c in requirements["fire_classes"]]
        actual = candidate.get("fire_class")
        check = {"attribute": "fire_class", "required": f"one of {requirements['fire_classes']}", "actual": actual}
        if actual is None:
            check["status"] = "unknown"
        elif str(actual).strip().lower() in allowed:
            check["status"] = "pass"
        else:
            check["status"] = "fail"
        checks.append(check)

    if "size" in requirements:
        actual = candidate.get("size")
        check = {"attribute": "size", "required": f"== {requirements['size']}", "actual": actual}
        if actual is None:
            check["status"] = "unknown"
        elif _norm_size(actual) == _norm_size(requirements["size"]):
            check["status"] = "pass"
        else:
            check["status"] = "fail"
        checks.append(check)

    if "recycled_min" in requirements:
        checks.append(_check_min("recycled", requirements["recycled_min"], candidate.get("recycled")))

    statuses = {c["status"] for c in checks}
    if "fail" in statuses:
        verdict = "FAIL"
    elif "unknown" in statuses:
        verdict = "PASS_WITH_GAPS"
    else:
        verdict = "PASS"

    return {"verdict": verdict, "checks": checks}


def main(argv):
    if len(argv) != 2:
        print(json.dumps({"error": "usage: spec_check.py '<json with requirements and candidate>'"}))
        return 2
    payload = json.loads(argv[1])
    result = check_substitute(payload.get("requirements", {}), payload.get("candidate", {}))
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
