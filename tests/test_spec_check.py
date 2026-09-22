"""Tests for the deterministic substitution check (runs inside the sandbox)."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from spec_check import check_substitute  # noqa: E402

REQ = {
    "nrc_min": 0.85,
    "cac_min": 35,
    "fire_classes": ["Class A"],
    "size": "24x24",
    "recycled_min": 0.30,
}


def _status(result, attribute):
    return next(c for c in result["checks"] if c["attribute"] == attribute)["status"]


def test_all_requirements_met_gives_pass():
    cand = {"nrc": 0.90, "cac": 38, "fire_class": "Class A", "size": "24x24", "recycled": 0.42}
    result = check_substitute(REQ, cand)
    assert result["verdict"] == "PASS"
    assert all(c["status"] == "pass" for c in result["checks"])


def test_cac_below_minimum_gives_fail_on_that_check():
    cand = {"nrc": 0.90, "cac": 33, "fire_class": "Class A", "size": "24x24", "recycled": 0.42}
    result = check_substitute(REQ, cand)
    assert result["verdict"] == "FAIL"
    assert _status(result, "cac") == "fail"
    assert _status(result, "nrc") == "pass"


def test_fire_class_outside_allowed_set_fails():
    cand = {"nrc": 0.90, "cac": 38, "fire_class": "Class C", "size": "24x24", "recycled": 0.42}
    result = check_substitute(REQ, cand)
    assert result["verdict"] == "FAIL"
    assert _status(result, "fire_class") == "fail"


def test_missing_attribute_is_unknown_not_fail():
    cand = {"nrc": 0.90, "cac": 38, "fire_class": "Class A", "size": "24x24", "recycled": None}
    result = check_substitute(REQ, cand)
    assert result["verdict"] == "PASS_WITH_GAPS"
    assert _status(result, "recycled") == "unknown"


@pytest.mark.parametrize("actual", ["2x2", "2' x 2'", "2 ft x 2 ft", "24 in x 24 in", "600 x 600 mm"])
def test_size_written_in_feet_inches_or_mm_matches_24x24(actual):
    cand = {"nrc": 0.90, "cac": 38, "fire_class": "Class A", "size": actual, "recycled": 0.42}
    result = check_substitute(REQ, cand)
    assert _status(result, "size") == "pass", actual


def test_size_mismatch_still_fails():
    cand = {"nrc": 0.90, "cac": 38, "fire_class": "Class A", "size": "2' x 4'", "recycled": 0.42}
    assert _status(check_substitute(REQ, cand), "size") == "fail"


def test_each_check_records_requirement_and_actual_value():
    cand = {"nrc": 0.90, "cac": 38, "fire_class": "Class A", "size": "24x24", "recycled": 0.42}
    result = check_substitute(REQ, cand)
    nrc = next(c for c in result["checks"] if c["attribute"] == "nrc")
    assert nrc["required"] == ">= 0.85"
    assert nrc["actual"] == 0.90


def test_cli_reads_json_argument_and_prints_json_result():
    script = Path(__file__).resolve().parents[1] / "spec_check.py"
    payload = json.dumps({"requirements": REQ, "candidate": {"nrc": 0.70, "cac": 38, "fire_class": "Class A", "size": "24x24", "recycled": 0.4}})
    proc = subprocess.run([sys.executable, str(script), payload], capture_output=True, text=True, check=True)
    out = json.loads(proc.stdout)
    assert out["verdict"] == "FAIL"
    assert next(c for c in out["checks"] if c["attribute"] == "nrc")["status"] == "fail"
