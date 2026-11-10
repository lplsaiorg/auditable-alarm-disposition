"""Regression checks for the extracted study contract; no API or dataset needed."""

import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(ROOT / "examples"))
from audit_demo import run_demo, synthetic_fixture  # noqa: E402
from evidence_contract import claims_check, gate, route_score, sha  # noqa: E402


class EvidenceContractTests(unittest.TestCase):
    def setUp(self):
        self.payload, self.response, self.trusted = synthetic_fixture()

    def audit(self, response=None, payload=None):
        return gate(
            self.response if response is None else response,
            self.payload if payload is None else payload,
            self.trusted["current_hash"], self.trusted["policy_hash"],
        )

    def test_original_fifteen_injection_scenarios(self):
        result = run_demo()
        self.assertTrue(result["synthetic_example"])
        self.assertEqual(len(result["tests"]), 15)
        for case in result["tests"]:
            with self.subTest(case=case["name"]):
                self.assertEqual(case["observed"], case["expected"])
                self.assertEqual(case["isolated_numeric_route"], 1)
                self.assertEqual(case["final_guarded_route"], 1 if case["expected"] == "PASS" else -1)
        self.assertTrue(result["all_expected"])

    def test_history_changes_do_not_enter_numeric_route_or_current_binding(self):
        changed = copy.deepcopy(self.payload)
        changed["historical_cases"][0]["historical_outcome"] = "FAULT"
        changed["historical_cases"][0]["measurements"][0]["values"][0] = 999.0
        self.assertNotEqual(sha(changed), sha(self.payload))
        self.assertEqual(sha(changed["current"]), self.trusted["current_hash"])
        self.assertEqual(self.audit(payload=changed), "PASS")
        self.assertEqual(route_score(0.85, 0.20, 0.70), self.trusted["numeric_route"])

    def test_binding_failures_precede_response_checks(self):
        changed = copy.deepcopy(self.payload)
        changed["current"]["sensors"][0]["values"][0] += 1
        changed["policy_hash"] = "obsolete"
        self.assertEqual(self.audit(response={}, payload=changed), "CURRENT_BINDING_MISMATCH")
        changed["current"] = copy.deepcopy(self.payload["current"])
        self.assertEqual(self.audit(response={}, payload=changed), "STALE_POLICY")

    def test_abstain_bypasses_reference_checks_but_not_bindings(self):
        response = {"label": "ABSTAIN"}
        self.assertEqual(self.audit(response=response), "PASS")
        changed = copy.deepcopy(self.payload)
        changed["policy_hash"] = "obsolete"
        self.assertEqual(self.audit(response=response, payload=changed), "STALE_POLICY")

    def test_quotation_tolerance_and_nonempty_requirement(self):
        changed = copy.deepcopy(self.response)
        changed["claims"][0]["value"] += 0.000005
        self.assertEqual(self.audit(response=changed), "PASS")
        changed["claims"][0]["value"] += 0.00002
        self.assertEqual(self.audit(response=changed), "INVALID_NUMERIC_CLAIM")
        for claims in ([], None, "not a claim list"):
            with self.subTest(claims=claims):
                changed["claims"] = claims
                self.assertFalse(claims_check(changed, self.payload)["all_valid_nonempty"])

    def test_original_bool_numeric_behavior_is_preserved_and_documented(self):
        payload = copy.deepcopy(self.payload)
        payload["current"]["sensors"][0]["values"][0] = 1.0
        response = copy.deepcopy(self.response)
        response["claims"][0]["value"] = True
        self.assertTrue(claims_check(response, payload)["all_valid_nonempty"])

    def test_numerical_threshold_boundaries_and_current_only_veto(self):
        for score, veto, expected in [
            (0.19, None, 0), (0.20, None, 0), (0.21, None, -1),
            (0.69, None, -1), (0.70, None, 1), (0.85, None, 1),
            (0.20, False, -1), (0.20, True, 0), (0.85, False, 1),
        ]:
            with self.subTest(score=score, veto=veto):
                self.assertEqual(route_score(score, 0.20, 0.70, veto), expected)


if __name__ == "__main__":
    unittest.main()
