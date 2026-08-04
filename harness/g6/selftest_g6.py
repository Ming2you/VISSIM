# G6 하네스 자체 검증 — 합성 데이터로 지표가 1.0/-1.0 을 내는지, 실제 상태 JSON 으로 파이프라인이 도는지 확인한다.
"""검증 3층.

  층 1 (합성) — 인위적으로 순위가 완전 일치/완전 반대/무작위인 데이터를 넣고
                Spearman ρ 와 top-action pairwise 가 각각 1.0/−1.0, 1.0/0.0 을 내는지.
  층 2 (레코드 계약) — 우리가 굽는 레코드가 shadow.validate_record 를 통과하는지,
                게이트 판정이 기대대로 PASS/FAIL/NOT_EVALUATED 로 갈리는지.
  층 3 (실데이터 스모크) — 저장소에 이미 있는 VISSIM state_000900.json 으로
                모델 rollout → 목적함수 경로가 실제로 도는지. 값의 옳음이 아니라
                **파이프라인이 성립하는지**만 본다.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import g6_core as core  # noqa: E402
import g6_records as rec  # noqa: E402

FAIL = rec.FAIL
NOT_EVALUATED = rec.NOT_EVALUATED
PASS = rec.PASS
evaluate_shadow_records = rec.evaluate_shadow_records
spearman_rank_correlation = rec.spearman_rank_correlation


def ranking_verdicts(report) -> dict[str, str]:
    """G6 게이트 전체가 아니라 **순위 기준 2개만** 뽑는다.

    spillback F1 은 후보 전부가 non-spillback 이면 혼동행렬이 정의되지 않아
    NOT_EVALUATED 가 되고, 그러면 게이트 전체가 NOT_EVALUATED 로 내려간다.
    순위 지표의 정확성을 검증할 때는 이 두 기준만 봐야 한다.
    """

    criteria = report["gates"]["g6_initial"]["criteria"]
    return {item["name"]: item["verdict"] for item in criteria}

REAL_STATE = (
    core.VISSIM_ROOT
    / "evaluation/runs/forced_response_grid_20260802/decisions_fw100_nc_seed13/state_000900.json"
)

_POLICY = rec.hash_payload({"policy": "g6-selftest"})
_BUILD = rec.hash_payload({"build": "g6-selftest"})
_SCHEMA = rec.hash_payload({"schema": "g6-selftest"})
_TOPO = rec.hash_payload({"topology": "g6-selftest"})
_PROGRAM = rec.hash_payload({"program": "g6-selftest"})
_STATE = rec.hash_payload({"state": "g6-selftest"})


def synth_records(pairs, *, decision_id="d_synth", spillback=None):
    """pairs = [(candidate_id, model_objective, vissim_objective), ...]"""

    out = []
    for index, (cid, model, observed) in enumerate(pairs):
        model_spill, obs_spill = (False, False) if spillback is None else spillback[index]
        out.append(
            rec.build_record(
                decision_id=decision_id,
                candidate_id=cid,
                model_objective=model,
                vissim_objective=observed,
                model_spillback=model_spill,
                vissim_spillback=obs_spill,
                action_payload={"candidate": cid},
                policy_hash=_POLICY,
                build_hash=_BUILD,
                action_schema_hash=_SCHEMA,
                topology_hash=_TOPO,
                program_hash=_PROGRAM,
                state_hash=_STATE,
                model_runtime_sec=0.01,
                decision_runtime_sec=1.0,
            )
        )
    return out


class Layer1SyntheticMetrics(unittest.TestCase):
    def test_perfect_agreement_gives_rho_one(self):
        pairs = [("c0", 100.0, 10.0), ("c1", 200.0, 20.0), ("c2", 300.0, 30.0), ("c3", 400.0, 40.0)]
        report = evaluate_shadow_records(synth_records(pairs))
        self.assertEqual(report["aggregate"]["spearman_rho"], 1.0)
        self.assertEqual(report["aggregate"]["top_action_pairwise"]["agreement"], 1.0)
        verdicts = ranking_verdicts(report)
        self.assertEqual(verdicts["spearman_rho"], PASS)
        self.assertEqual(verdicts["top_action_pairwise_agreement"], PASS)

    def test_exact_reversal_gives_rho_minus_one(self):
        pairs = [("c0", 100.0, 40.0), ("c1", 200.0, 30.0), ("c2", 300.0, 20.0), ("c3", 400.0, 10.0)]
        report = evaluate_shadow_records(synth_records(pairs))
        self.assertAlmostEqual(report["aggregate"]["spearman_rho"], -1.0)
        self.assertEqual(report["aggregate"]["top_action_pairwise"]["agreement"], 0.0)
        self.assertEqual(report["gates"]["g6_initial"]["verdict"], FAIL)

    def test_monotone_positive_rescaling_preserves_rank(self):
        """편향이 액션과 무관한 상수(배)면 순위는 보존된다 — 사용자 가설의 형식적 확인."""

        base = [10.0, 25.0, 17.0, 31.0, 22.0]
        for scale, shift in ((1.0, 0.0), (1.7, 0.0), (1.0, 250.0), (1.55, -12.5)):
            pairs = [(f"c{i}", v * scale + shift, v) for i, v in enumerate(base)]
            report = evaluate_shadow_records(synth_records(pairs))
            self.assertEqual(report["aggregate"]["spearman_rho"], 1.0, msg=f"scale={scale} shift={shift}")
            self.assertEqual(ranking_verdicts(report)["spearman_rho"], PASS)

    def test_top_action_only_swap_is_caught(self):
        """전체 상관은 높은데 최상위만 뒤집힌 경우 — G6 가 두 지표를 따로 요구하는 이유."""

        pairs = [
            ("c0", 10.0, 22.0),   # 모델 1위, 실제 3위
            ("c1", 20.0, 10.0),   # 모델 2위, 실제 1위
            ("c2", 30.0, 30.0),
            ("c3", 40.0, 40.0),
            ("c4", 50.0, 50.0),
        ]
        report = evaluate_shadow_records(synth_records(pairs))
        rho = report["aggregate"]["spearman_rho"]
        pairwise = report["aggregate"]["top_action_pairwise"]["agreement"]
        self.assertGreater(rho, 0.70)
        self.assertLess(pairwise, 0.80)
        self.assertEqual(report["gates"]["g6_initial"]["verdict"], FAIL)

    def test_spearman_helper_direct(self):
        self.assertEqual(spearman_rank_correlation([1.0, 2.0, 3.0], [5.0, 6.0, 7.0]), 1.0)
        self.assertEqual(spearman_rank_correlation([1.0, 2.0, 3.0], [7.0, 6.0, 5.0]), -1.0)

    def test_spillback_f1_perfect_and_broken(self):
        pairs = [("c0", 1.0, 1.0), ("c1", 2.0, 2.0), ("c2", 3.0, 3.0), ("c3", 4.0, 4.0)]
        perfect = [(True, True), (True, True), (False, False), (False, False)]
        report = evaluate_shadow_records(synth_records(pairs, spillback=perfect))
        self.assertEqual(report["aggregate"]["spillback"]["f1"], 1.0)
        self.assertEqual(report["gates"]["g6_release"]["verdict"], PASS)

        broken = [(True, False), (True, False), (False, True), (False, True)]
        report = evaluate_shadow_records(synth_records(pairs, spillback=broken))
        self.assertEqual(report["aggregate"]["spillback"]["f1"], 0.0)
        self.assertEqual(report["gates"]["g6_initial"]["verdict"], FAIL)


class Layer2RecordContract(unittest.TestCase):
    def test_persistence_predictor_cannot_be_ranked(self):
        """Δ=0 예측자는 모든 후보에 같은 값을 내므로 Spearman 이 정의되지 않는다.

        G5 에서 전 조합을 이겼던 대조군이 G6 에서 왜 무의미한지를 코드로 고정한다.
        """

        pairs = [("c0", 500.0, 10.0), ("c1", 500.0, 20.0), ("c2", 500.0, 30.0)]
        report = evaluate_shadow_records(synth_records(pairs))
        self.assertIsNone(report["aggregate"]["spearman_rho"])
        self.assertFalse(report["aggregate"]["ranking_oracle_complete"])
        self.assertEqual(report["gates"]["g6_initial"]["verdict"], NOT_EVALUATED)

    def test_missing_observation_is_not_evaluated_not_pass(self):
        records = synth_records([("c0", 1.0, 1.0), ("c1", 2.0, 2.0)])
        records[0].pop("vissim_observed_objective")
        report = evaluate_shadow_records(records)
        self.assertEqual(report["gates"]["g6_initial"]["verdict"], NOT_EVALUATED)
        self.assertNotEqual(report["gates"]["g6_initial"]["verdict"], PASS)

    def test_multi_decision_macro_mean(self):
        """decision 단위 매크로 평균 — 셀별 결과가 섞이지 않는지."""

        good = synth_records(
            [("c0", 1.0, 1.0), ("c1", 2.0, 2.0), ("c2", 3.0, 3.0)], decision_id="cellA_seed13_H3"
        )
        bad = synth_records(
            [("c0", 1.0, 3.0), ("c1", 2.0, 2.0), ("c2", 3.0, 1.0)], decision_id="cellB_seed13_H3"
        )
        report = evaluate_shadow_records(good + bad)
        self.assertEqual(report["decision_count"], 2)
        self.assertAlmostEqual(report["aggregate"]["spearman_rho"], 0.0)
        per = {item["decision_id"]: item for item in report["per_decision"]}
        self.assertEqual(per["cellA_seed13_H3"]["ranking_status"], PASS)
        self.assertEqual(per["cellB_seed13_H3"]["ranking_status"], FAIL)

    def test_records_round_trip_through_jsonl(self):
        import tempfile

        load_jsonl = rec.load_jsonl
        records = synth_records([("c0", 1.0, 1.0), ("c1", 2.0, 2.0)])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "records.jsonl"
            self.assertEqual(rec.write_jsonl(path, records), 2)
            loaded = load_jsonl(path)
        self.assertEqual(len(loaded), 2)
        self.assertEqual(loaded[0]["candidate_id"], "c0")

    def test_candidate_set_covers_contract_axes(self):
        axes = {c.axis for c in core.ACTIVE_CANDIDATE_SET}
        for required in ("vsl", "ramp", "green", "offset"):
            self.assertIn(required, axes, msg=f"계약 §11 G6 이 요구한 {required} perturbation 누락")
        ids = [c.candidate_id for c in core.ACTIVE_CANDIDATE_SET]
        self.assertEqual(len(ids), len(set(ids)))
        for c in core.ACTIVE_CANDIDATE_SET:
            self.assertNotIn(c.variant, core.EXCLUDED_VARIANTS)


class Layer3RealDataSmoke(unittest.TestCase):
    @unittest.skipUnless(REAL_STATE.exists(), f"실 상태 JSON 없음: {REAL_STATE}")
    def test_model_rollout_and_objective_run_on_real_state(self):
        state_json = json.loads(REAL_STATE.read_text(encoding="utf-8"))
        runtime = core.build_runtime(state_json)
        initial = core.project_observed_state(runtime, state_json)
        forecast = core.build_forecast(runtime, state_json, 5)

        results: dict[str, float] = {}
        for cand in core.ACTIVE_CANDIDATE_SET:
            control = core.build_control(runtime.cfg, runtime.ControlAction, cand)
            states = core.model_rollout_states(runtime, initial, control, forecast, 3)
            self.assertEqual(len(states), 3)
            terms = core.objective_from_states(runtime, states, control)
            self.assertTrue(terms["g6_objective"] == terms["g6_objective"])  # NaN 아님
            self.assertGreater(terms["g6_ttt_veh_h"], 0.0)
            _ = core.spillback_flag(runtime, states)
            results[cand.candidate_id] = terms["g6_objective"]

        # 후보마다 서로 다른 값이 나와야 순위를 매길 수 있다. 전부 같으면 모델이
        # 액션에 반응하지 않는다는 뜻이고 G6 는 애초에 성립하지 않는다.
        self.assertGreater(
            len(set(round(v, 6) for v in results.values())),
            1,
            msg=f"모든 후보가 같은 목적함수 값을 냈다 — 액션 무반응: {results}",
        )
        print("\n[layer3] 후보별 모델 목적함수 (H=3):")
        for cid, value in sorted(results.items(), key=lambda kv: kv[1]):
            print(f"  {cid:<22} {value:,.3f}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
