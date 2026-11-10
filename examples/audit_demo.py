"""Replay the 15 study audit scenarios on an explicitly synthetic small example.

Run from any working directory with ``python path/to/examples/audit_demo.py``.
No network, credentials, raw data, fitted model, or third-party package is used.
These are illustrative inputs, not saved experimental observations or metrics.
Case names and expected statuses follow the original ``code/v3_audit.py``;
see ``code/evidence_contract.py`` for source provenance and contract limits.
"""

import copy
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
from evidence_contract import FIELDS, gate, route_score, sha  # noqa: E402


def synthetic_fixture():
    """Construct reader-visible data and separately held trusted bindings."""
    current = {
        "fields": list(FIELDS),
        "sensors": [{
            "ref": "E:0",
            "variable": "SYNTHETIC_SENSOR_A",
            "values": [0.42, 0.42, 1.10, -0.20, 0.80, 0.12, 0.05],
        }],
        "global_features": [],
    }
    # An illustrative upstream score is held fixed; no classifier is trained.
    policy = {"lo": 0.20, "hi": 0.70, "model_id": "synthetic-fixed-model"}
    score = 0.85
    policy_hash = sha(policy)
    trusted = {
        "current_hash": sha(current),
        "policy_hash": policy_hash,
        "numeric_route": route_score(score, policy["lo"], policy["hi"]),
    }
    payload = {
        "query_id": "synthetic-demo-001",
        "current": current,
        "policy_hash": policy_hash,
        "numeric_candidate": {
            "fault_score": score,
            "label": "FAULT",
            "benign_threshold": policy["lo"],
            "fault_threshold": policy["hi"],
            "normal_veto_pass": True,
        },
        "historical_cases": [{
            "case_id": "H1",
            "measurements": [{
                "ref": "H1:E:0", "variable": "SYNTHETIC_SENSOR_A",
                "values": [0.40, 0.40, 1.05, -0.18, 0.78, 0.10, 0.04],
            }],
            "historical_outcome": "BENIGN",
            "regime": "illustrative",
            "record_status": "synthetic",
        }],
    }
    response = {
        "label": "FAULT",
        "supporting_refs": ["E:0"],
        "claims": [{"ref": "E:0", "field": "z_mean", "value": 0.42}],
    }
    return payload, response, trusted


def run_demo():
    """Return the original 15 fault-injection outcomes on synthetic inputs."""
    payload, response, trusted = synthetic_fixture()
    tests = []

    def check(name, candidate_response, candidate_payload, expected):
        observed = gate(
            candidate_response, candidate_payload,
            trusted["current_hash"], trusted["policy_hash"],
        )
        tests.append({
            "name": name,
            "expected": expected,
            "observed": observed,
            "pass": observed == expected,
            "isolated_numeric_route": trusted["numeric_route"],
            "final_guarded_route": trusted["numeric_route"] if observed == "PASS" else -1,
        })

    check("valid_bound_record", response, payload, "PASS")
    for name, refs in [
        ("missing_reference", []),
        ("forged_reference", ["E:999"]),
        ("historical_reference", ["H1:E:0"]),
        ("nonstring_reference", [{}]),
    ]:
        changed = copy.deepcopy(response)
        changed["supporting_refs"] = refs
        check(name, changed, payload, "INVALID_CURRENT_REFERENCE")

    changed = copy.deepcopy(response)
    changed["claims"][0]["value"] += 1
    check("misquoted_numeric_value", changed, payload, "INVALID_NUMERIC_CLAIM")
    changed = copy.deepcopy(response)
    changed["claims"][0]["field"] = "imaginary_field"
    check("forged_measurement_field", changed, payload, "INVALID_NUMERIC_CLAIM")
    changed = copy.deepcopy(response)
    changed["claims"] = []
    check("missing_numeric_claim", changed, payload, "INVALID_NUMERIC_CLAIM")

    changed = copy.deepcopy(payload)
    changed["current"]["sensors"][0]["values"][0] += 1
    check("changed_current_evidence", response, changed, "CURRENT_BINDING_MISMATCH")
    changed = copy.deepcopy(payload)
    changed["policy_hash"] = "obsolete"
    check("stale_calibration_binding", response, changed, "STALE_POLICY")
    check("unparseable_response", None, payload, "MALFORMED_RESPONSE")
    changed = copy.deepcopy(response)
    changed["label"] = "NORMAL"
    check("invalid_label_enum", changed, payload, "MALFORMED_RESPONSE")

    changed = copy.deepcopy(payload)
    changed["historical_cases"] = []
    check("history_removed_does_not_change_bound_route", response, changed, "PASS")
    changed = copy.deepcopy(response)
    changed["explanation"] = "This value proves that a valve is physically broken."
    check("semantic_overclaim_is_NOT_detected_by_syntactic_gate", changed, payload, "PASS")
    changed = copy.deepcopy(payload)
    changed["numeric_candidate"]["label"] = "BENIGN"
    check("reader_candidate_tampering_cannot_override_external_frozen_route", response, changed, "PASS")

    return {
        "synthetic_example": True,
        "scope": (
            "Illustrative replay of the binding/reference/quotation contract, not "
            "a reproduction of paper results or an adversarial security certificate. "
            "The isolated numeric route is external to the reader payload. "
            "The optional guarded release abstains on audit failure. "
            "A semantic overclaim intentionally passes the syntactic gate."
        ),
        "route_codes": {"benign": 0, "fault": 1, "abstain": -1},
        "tests": tests,
        "all_expected": all(test["pass"] for test in tests),
    }


if __name__ == "__main__":
    result = run_demo()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["all_expected"] else 1)
