from __future__ import annotations

import json
import io
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout

from src.vissim_strict.shadow import (
    FAIL,
    NOT_EVALUATED,
    PASS,
    RECORD_SCHEMA_VERSION,
    ShadowRecorder,
    ShadowValidationError,
    canonical_json_text,
    evaluate_com_readback_records,
    evaluate_shadow_records,
    load_jsonl,
    main,
    spearman_rank_correlation,
    verify_report_digest,
    write_report,
)
from src.vissim_strict.topology import canonical_json_sha256, canonical_json_text as topology_canonical_json_text


def candidate(decision: str, candidate_id: str, predicted: float, observed: float | None, **updates):
    value = {
        "schema_version": RECORD_SCHEMA_VERSION,
        "decision_id": decision,
        "candidate_id": candidate_id,
        "strict_predicted_objective": predicted,
        "strict_status": "OK",
        "strict_runtime_sec": 1.0,
        "action_hash": (candidate_id[0].lower() if candidate_id[0].lower() in "abcdef" else "a") * 64,
        "policy_hash": "7" * 64,
        "build_hash": "8" * 64,
        "action_schema_hash": "9" * 64,
        "topology_hash": "1" * 64,
        "program_hash": "2" * 64,
        "strict_predicted_spillback": False,
        "vissim_observed_spillback": False,
        "fallback_required": False,
        "shadow_mode": True,
        "actuation_attempted": False,
        "stale_fault_injection_observed": False,
        "fallback_fault_injection_observed": False,
        "readback_fault_injection_observed": False,
    }
    if observed is not None:
        value["vissim_observed_objective"] = observed
    value.update(updates)
    return value


class RankingTests(unittest.TestCase):
    def test_spearman_uses_average_ranks_for_ties(self):
        self.assertEqual(spearman_rank_correlation([1.0, 1.0, 3.0], [2.0, 2.0, 9.0]), 1.0)

        report = evaluate_shadow_records(
            [
                candidate("d1", "a", 1.0, 2.0),
                candidate("d1", "b", 1.0, 2.0),
                candidate(
                    "d1",
                    "c",
                    3.0,
                    9.0,
                    strict_predicted_spillback=True,
                    vissim_observed_spillback=True,
                ),
            ]
        )
        self.assertEqual(report["aggregate"]["spearman_rho"], 1.0)
        self.assertEqual(report["aggregate"]["top_action_pairwise"]["agreement"], 1.0)
        self.assertEqual(report["gates"]["g6_initial"]["verdict"], PASS)

    def test_reversed_ranking_fails_g6(self):
        report = evaluate_shadow_records(
            [
                candidate("d1", "a", 1.0, 30.0),
                candidate("d1", "b", 2.0, 20.0),
                candidate(
                    "d1",
                    "c",
                    3.0,
                    10.0,
                    strict_predicted_spillback=True,
                    vissim_observed_spillback=True,
                ),
            ]
        )
        self.assertAlmostEqual(report["aggregate"]["spearman_rho"], -1.0)
        self.assertEqual(report["aggregate"]["top_action_pairwise"]["agreement"], 0.0)
        self.assertEqual(report["gates"]["g6_initial"]["verdict"], FAIL)

    def test_missing_oracle_is_not_evaluated(self):
        report = evaluate_shadow_records(
            [candidate("d1", "a", 1.0, None), candidate("d1", "b", 2.0, 2.0)]
        )
        self.assertFalse(report["aggregate"]["ranking_oracle_complete"])
        self.assertEqual(report["gates"]["g6_initial"]["verdict"], NOT_EVALUATED)
        self.assertNotEqual(report["gates"]["g6_initial"]["verdict"], PASS)

    def test_known_g6_failure_outranks_missing_spillback_evidence(self):
        records = [
            candidate("d1", "a", 1.0, 3.0),
            candidate("d1", "b", 2.0, 2.0),
            candidate("d1", "c", 3.0, 1.0),
        ]
        for record in records:
            record.pop("vissim_observed_spillback")
        report = evaluate_shadow_records(records)
        self.assertFalse(report["aggregate"]["spillback_oracle_complete"])
        self.assertEqual(report["gates"]["g6_initial"]["verdict"], FAIL)


class RuntimeAndRecordingTests(unittest.TestCase):
    def test_runtime_fallback_and_failure_accounting(self):
        records = []
        for index in range(20):
            records.extend(
                [
                    candidate(
                        f"d{index:02d}",
                        "a",
                        1.0,
                        1.0,
                        decision_runtime_sec=10.0 + index,
                        fallback_required=index == 0,
                        fallback_event_logged=index == 0,
                        fallback_fault_injection_observed=index == 0,
                        stale_fault_injection_observed=index == 1,
                        stale_action_detected=index == 1,
                        stale_action_rejected=False if index == 1 else None,
                        stale_action_failure=index == 1,
                        state_hash="3" * 64 if index == 1 else None,
                        based_on_state_hash="4" * 64 if index == 1 else None,
                        readback_fault_injection_observed=index == 2,
                        readback_ok=index != 2,
                    ),
                    candidate(
                        f"d{index:02d}",
                        "b",
                        2.0,
                        2.0,
                        decision_runtime_sec=10.0 + index,
                    ),
                ]
            )
        report = evaluate_shadow_records(records)
        aggregate = report["aggregate"]
        self.assertEqual(aggregate["fallback_rate"], 0.05)
        self.assertEqual(aggregate["silent_fallback_rate"], 0.0)
        self.assertEqual(aggregate["stale_action"]["failure_count"], 1)
        self.assertEqual(aggregate["readback"]["failure_count"], 1)
        self.assertEqual(aggregate["runtime"]["max_sec"], 29.0)
        self.assertEqual(report["gates"]["g7_shadow_runtime"]["verdict"], FAIL)

    def test_g7_requires_explicit_shadow_fault_injection_evidence(self):
        no_evidence = evaluate_shadow_records(
            [candidate("d1", "a", 1.0, 1.0), candidate("d1", "b", 2.0, 2.0)]
        )
        self.assertEqual(no_evidence["aggregate"]["fault_injection"]["stale_observation_count"], 0)
        self.assertEqual(no_evidence["aggregate"]["fault_injection"]["fallback_observation_count"], 0)
        self.assertEqual(no_evidence["aggregate"]["fault_injection"]["readback_observation_count"], 0)
        self.assertEqual(no_evidence["gates"]["g7_shadow_runtime"]["verdict"], NOT_EVALUATED)

        known_runtime_failure = evaluate_shadow_records(
            [
                candidate("d2", "a", 1.0, 1.0, decision_runtime_sec=60.0),
                candidate("d2", "b", 2.0, 2.0, decision_runtime_sec=60.0),
            ]
        )
        self.assertEqual(
            known_runtime_failure["gates"]["g7_shadow_runtime"]["verdict"], FAIL
        )

        records = [
            candidate(
                "d1",
                "a",
                1.0,
                1.0,
                state_hash="3" * 64,
                based_on_state_hash="4" * 64,
                stale_fault_injection_observed=True,
                stale_action_detected=True,
                stale_action_rejected=True,
                stale_action_failure=False,
            ),
            candidate(
                "d1",
                "b",
                2.0,
                2.0,
                fallback_fault_injection_observed=True,
                fallback_required=True,
                fallback_event_logged=True,
                readback_fault_injection_observed=True,
                readback_ok=True,
            ),
        ]
        passed = evaluate_shadow_records(
            records, thresholds={"fallback_rate_max_exclusive": 1.1}
        )
        self.assertEqual(passed["gates"]["g7_shadow_runtime"]["verdict"], PASS)

    def test_shadow_record_contract_rejects_non_shadow_or_implicit_evidence(self):
        unsafe = candidate("d1", "a", 1.0, 1.0)
        unsafe["shadow_mode"] = False
        with self.assertRaisesRegex(ShadowValidationError, "shadow_mode=true"):
            evaluate_shadow_records([unsafe])

        implicit = candidate("d1", "a", 1.0, 1.0)
        implicit.pop("stale_fault_injection_observed")
        with self.assertRaisesRegex(ShadowValidationError, "missing required fields"):
            evaluate_shadow_records([implicit])

        fake_stale = candidate(
            "d1",
            "a",
            1.0,
            1.0,
            state_hash="3" * 64,
            based_on_state_hash="3" * 64,
            stale_fault_injection_observed=True,
            stale_action_detected=True,
            stale_action_rejected=True,
            stale_action_failure=False,
        )
        with self.assertRaisesRegex(ShadowValidationError, "stale hash mismatch"):
            evaluate_shadow_records([fake_stale])

    def test_recorder_preserves_hashes_and_forbids_actuation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "shadow.jsonl"
            recorder = ShadowRecorder(path)
            rows = recorder.record_decision(
                decision_id="d1",
                topology_hash="1" * 64,
                state_hash="2" * 64,
                candidates=[candidate("d1", "a", 1.0, 1.0)],
            )
            self.assertEqual(rows[0]["topology_hash"], "1" * 64)
            self.assertEqual(rows[0]["state_hash"], "2" * 64)
            self.assertEqual(rows[0]["action_hash"], "a" * 64)
            self.assertTrue(rows[0]["shadow_mode"])
            self.assertFalse(rows[0]["actuation_attempted"])
            self.assertEqual(load_jsonl(path), rows)

            unsafe = candidate("d2", "b", 1.0, 1.0, topology_hash="1" * 64, state_hash="2" * 64)
            unsafe["actuation_attempted"] = True
            with self.assertRaises(ShadowValidationError):
                recorder.record(unsafe)

            with self.assertRaises(ShadowValidationError):
                recorder.record_decision(
                    decision_id="d3",
                    topology_hash="1" * 64,
                    state_hash="2" * 64,
                    candidates=[candidate("different-decision", "c", 1.0, 1.0)],
                )

    def test_report_is_byte_deterministic(self):
        records = [candidate("d1", "a", 1.0, 1.0), candidate("d1", "b", 2.0, 2.0)]
        first = evaluate_shadow_records(records)
        second = evaluate_shadow_records(list(reversed(records)))
        self.assertEqual(canonical_json_text(first), canonical_json_text(second))

        with tempfile.TemporaryDirectory() as directory:
            first_path = Path(directory) / "first.json"
            second_path = Path(directory) / "second.json"
            write_report(first_path, first)
            write_report(second_path, second)
            self.assertEqual(first_path.read_bytes(), second_path.read_bytes())
            self.assertEqual(json.loads(first_path.read_text(encoding="utf-8")), first)
            self.assertTrue(verify_report_digest(first))

    def test_g6_provenance_and_digest_are_release_requirements(self):
        records = [candidate("d1", "a", 1.0, 1.0), candidate("d1", "b", 2.0, 2.0)]
        report = evaluate_shadow_records(records)
        self.assertEqual(report["provenance"]["topology_hash"], "1" * 64)
        self.assertEqual(report["provenance"]["program_hashes"], ["2" * 64])
        self.assertTrue(verify_report_digest(report))
        tampered = dict(report)
        tampered["record_count"] += 1
        self.assertFalse(verify_report_digest(tampered))

    def test_g8_requires_one_hundred_percent_com_readback(self):
        authority = {str(sc_no): [1] for sc_no in range(1, 16)}
        action_hash = "3" * 64
        base = {
            "topology_hash": "1" * 64,
            "program_hash": "2" * 64,
            "action_hash": action_hash,
            "action_set_sha256": canonical_json_sha256({"action_hashes": [action_hash]}),
            "runtime_action_hash": "5" * 64,
            "policy_hash": "7" * 64,
            "build_hash": "8" * 64,
            "action_schema_hash": "9" * 64,
            "runtime_action_hmac_sha256": "6" * 64,
            "csv_payload_sha256": "a" * 64,
            "envelope_hmac_sha256": "b" * 64,
            "envelope_hmac_valid": True,
            "row_contract_sha256": "4" * 64,
            "interval_id": "i1",
            "evidence_kind": "sigstate",
            "requested_state": "GREEN",
            "state_readback": "GREEN",
            "contr_by_com_requested": True,
            "contr_by_com_readback": True,
            "readback_ok": True,
            "run_id": "run-1", "build_id": "build-1", "network_id": "network-1",
            "seed": "13", "demand_identity": "demand-1",
        }
        rows = [{**base, "sc_no": sc_no, "sg_no": 1} for sc_no in range(1, 16)]
        release_rows = [{
            **base,
            "sc_no": sc_no,
            "sg_no": 1,
            "interval_id": "release-1",
            "evidence_kind": "native_release",
            "requested_state": "CONTRBYCOM:false",
            "state_readback": "CONTRBYCOM:false",
            "contr_by_com_requested": False,
            "contr_by_com_readback": False,
            "parent_runtime_action_hash": "5" * 64,
            "parent_action_interval_id": "i1",
        } for sc_no in range(1, 16)]
        passed = evaluate_com_readback_records(rows + release_rows, expected_authority=authority)
        self.assertEqual(passed["gates"]["g8_readback"]["verdict"], PASS)
        self.assertEqual(passed["gates"]["g8_native_release"]["verdict"], PASS)
        self.assertTrue(verify_report_digest(passed))
        for bad_rows, metric in (
            (rows[:-1], "missing_authority_pair_count"),
            (rows + [dict(rows[0])], "duplicate_authority_pair_count"),
            (rows + [{**base, "sc_no": 16, "sg_no": 1}], "extra_authority_pair_count"),
        ):
            failed = evaluate_com_readback_records(bad_rows + release_rows, expected_authority=authority)
            self.assertEqual(failed["gates"]["g8_readback"]["verdict"], FAIL)
            self.assertGreater(failed["aggregate"][metric], 0)

        contr_only = [{**rows[0], "evidence_kind": "contr_by_com", "interval_id": "i2"}]
        failed = evaluate_com_readback_records(rows + release_rows + contr_only, expected_authority=authority)
        self.assertEqual(failed["gates"]["g8_readback"]["verdict"], FAIL)
        self.assertGreater(failed["aggregate"]["missing_authority_pair_count"], 0)

        false_request = [dict(row) for row in rows]
        false_request[0]["contr_by_com_requested"] = False
        failed = evaluate_com_readback_records(false_request + release_rows, expected_authority=authority)
        self.assertEqual(failed["gates"]["g8_readback"]["verdict"], FAIL)

        partial_second_release = [{
            **release_rows[0], "interval_id": "release-2", "parent_action_interval_id": "i2"
        }]
        failed = evaluate_com_readback_records(
            rows + release_rows + partial_second_release,
            expected_authority=authority,
        )
        self.assertEqual(failed["gates"]["g8_native_release"]["verdict"], FAIL)

        invalid_envelope = [dict(row) for row in rows]
        invalid_envelope[0]["envelope_hmac_valid"] = False
        failed = evaluate_com_readback_records(invalid_envelope + release_rows, expected_authority=authority)
        self.assertEqual(failed["gates"]["g8_readback"]["verdict"], FAIL)
        self.assertEqual(failed["aggregate"]["envelope_hmac_failure_count"], 1)

    def test_report_digest_uses_topology_canonical_float_bytes(self):
        payload = {"small": 1.0e-7, "zero": 0.0}
        self.assertIs(canonical_json_text, topology_canonical_json_text)
        self.assertEqual(canonical_json_text(payload), '{"small":1e-7,"zero":0.0}')
        report = {"schema_version": "test", **payload}
        from src.vissim_strict.shadow import _with_report_digest
        signed = _with_report_digest(report)
        self.assertEqual(signed["report_digest_sha256"], canonical_json_sha256(report))

    def test_cli_writes_canonical_report(self):
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "input.jsonl"
            output_path = Path(directory) / "report.json"
            input_path.write_text(
                "\n".join(
                    canonical_json_text(row)
                    for row in (
                        candidate("d1", "a", 1.0, 1.0, strict_predicted_spillback=True, vissim_observed_spillback=True),
                        candidate("d1", "b", 2.0, 2.0),
                    )
                )
                + "\n",
                encoding="utf-8",
            )
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main([str(input_path), "--output", str(output_path)]), 0)
            report = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(output_path.read_text(encoding="utf-8"), canonical_json_text(report) + "\n")
            self.assertEqual(report["gates"]["g6_initial"]["verdict"], PASS)


if __name__ == "__main__":
    unittest.main()
