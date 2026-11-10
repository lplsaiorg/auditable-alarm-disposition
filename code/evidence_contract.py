"""Dependency-free extraction of the study's deterministic evidence contract.

Source provenance (research snapshot inspected 2026-11-10):
* ``code/v3_llm.py``: ``sha``, ``FIELDS``, ``claims_check``, and ``gate``.
  SHA-256: de9061a0e3b7d095399627f6b91666a22a5f18b9b1ec9658f62ff810c80f7dd4
* ``code/v2_numeric.py``: scalar equivalent of its ``route`` function.
  SHA-256: 2bd40978195d51ff9943b2c1d369a2e5f7d36433015a57babf574cd9883a6ef7
* Fault-injection examples follow ``code/v3_audit.py``.
  SHA-256: 025760741416e567b96ca81a336a90bf23cf8a73e5060cc9f261cfe9fd2627ef

The hashing representation, tolerance, check order, accepted labels, and ABSTAIN
behavior are preserved. No live reader, API queue, dataset, or model is imported.
The input payload is assumed to have the constructed current-evidence structure
used in the study; this is not a general-purpose schema validator. In particular,
the original numeric check uses Python's int/float test, which also accepts bool.

PASS means that these explicit checks passed. It does not establish semantic
support, causal correctness, equipment safety, or adversarial security. The
trusted numeric route is computed and retained outside the reader payload; the
gate neither recomputes it nor trusts the payload's ``numeric_candidate`` label.
The optional guarded release uses that trusted route on PASS and abstains on a
failed audit, while the isolated numerical branch remains a separate output.
"""

import hashlib
import json


FIELDS = [
    "z_mean", "abs_z_mean", "z_std", "z_q10", "z_q90", "z_half_change",
    "z_diff_rms",
]


def sha(value):
    """Return the original sorted-key JSON SHA-256 binding.

    JSON defaults are intentionally retained for compatibility with saved study
    bindings, including whitespace and ASCII escaping. This is a content hash,
    not a signature or an authentication mechanism.
    """
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def claims_check(response, payload):
    """Check nonempty current-reference quotations using the original tolerance."""
    refs = {record["ref"]: record for record in payload["current"]["sensors"]}
    claims = response.get("claims", [])
    if not isinstance(claims, list):
        return {"count": 0, "valid": 0, "all_valid_nonempty": False}
    valid = 0
    for claim in claims:
        try:
            value = refs[claim["ref"]]["values"][FIELDS.index(claim["field"])]
            valid += bool(
                isinstance(claim["value"], (int, float))
                and abs(claim["value"] - value) <= 1e-5
            )
        except (KeyError, ValueError, TypeError):
            pass
    return {
        "count": len(claims),
        "valid": int(valid),
        "all_valid_nonempty": bool(claims) and valid == len(claims),
    }


def gate(response, payload, current_hash, policy_hash):
    """Return the first failing contract status, or PASS, in study check order."""
    if sha(payload["current"]) != current_hash:
        return "CURRENT_BINDING_MISMATCH"
    if payload.get("policy_hash") != policy_hash:
        return "STALE_POLICY"
    if not isinstance(response, dict) or response.get("label") not in [
        "FAULT", "BENIGN", "ABSTAIN"
    ]:
        return "MALFORMED_RESPONSE"
    if response["label"] == "ABSTAIN":
        return "PASS"
    allowed = {record["ref"] for record in payload["current"]["sensors"]}
    refs = response.get("supporting_refs")
    if (
        not isinstance(refs, list)
        or not refs
        or any(not isinstance(ref, str) or ref not in allowed for ref in refs)
    ):
        return "INVALID_CURRENT_REFERENCE"
    if not claims_check(response, payload)["all_valid_nonempty"]:
        return "INVALID_NUMERIC_CLAIM"
    return "PASS"


def route_score(score, lo, hi, veto=None):
    """Scalar form of the study's numerical route: 0 benign, 1 fault, -1 abstain.

    The score comes from an upstream fixed model; this function fits no model or
    calibration thresholds. It accepts no history or generated explanation.
    The original route tests the benign branch first and uses inclusive bounds.
    A false veto prevents benign release only. Inputs are expected to use the
    ordered thresholds selected by the experiment.
    """
    benign = score <= lo and (True if veto is None else veto)
    return 0 if benign else (1 if score >= hi else -1)
