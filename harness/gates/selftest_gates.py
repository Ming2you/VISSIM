# 공용 하네스 자체 검증 — 합성 케이스로 G5/G6 지표가 알려진 정답을 내는지 확인한다.
"""검증 4층.

  층 1 (G6 합성) — 순위 완전일치 -> rho=+1.0, 완전반대 -> rho=-1.0, Delta=0 -> 정의불가.
  층 2 (G5 합성) — 오차를 손으로 심은 가짜 Episode 에서 MAE/MAPE 가 정확히 그 값을 내는지.
                   집계 수준(cell vs link)이 실제로 갈리는지, 임계가 수준마다 다시
                   계산되는지.
  층 3 (공용성)  — G5 와 G6 가 **같은 build_episode** 를 쓰는지 코드로 고정한다.
  층 4 (실데이터) — 저장소의 실제 런으로 rolling-origin 이 돌고, 앵커마다 상태가
                   실측으로 리셋되는지(teacher forcing 성립) 확인한다.
"""

from __future__ import annotations

import sys
import unittest
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import episode as ep  # noqa: E402
import g5_metrics as g5  # noqa: E402
import g6_core as core  # noqa: E402
import g6_records as rec  # noqa: E402

PASS, FAIL, NOT_EVALUATED = g5.PASS, g5.FAIL, g5.NOT_EVALUATED

_H = {k: rec.hash_payload({k: "gates-selftest"}) for k in
      ("policy", "build", "schema", "topology", "program", "state")}


# ---------------------------------------------------------------------------
# 합성 상태 — TrafficState 대신 필요한 필드만 가진 최소 대역
# ---------------------------------------------------------------------------


@dataclass
class FakeState:
    freeway_density: dict
    freeway_speed: dict
    urban_link_storage: dict
    urban_movement_queue: dict
    ramp_queue: dict
    time_sec: float = 0.0


def fake_episode(*, densities_pred, densities_obs, speeds_pred, speeds_obs,
                 horizon=1, links=("FW_E",), n_seg=8, length=1.0, lanes=1.0) -> ep.Episode:
    """셀별 (rho, v) 를 손으로 지정한 Episode. count = rho x 1.0 x 1.0 = rho 가 되게 둔다."""

    geometry = ep.CellGeometry(
        length_km={l: [length] * n_seg for l in links},
        lanes={l: [lanes] * n_seg for l in links},
    )

    def make(rho_list, v_list):
        return FakeState(
            freeway_density={l: list(rho_list) for l in links},
            freeway_speed={l: list(v_list) for l in links},
            urban_link_storage={}, urban_movement_queue={}, ramp_queue={},
        )

    return ep.Episode(
        anchor_t_sec=900, horizon=horizon, interval_sec=60, action_id="synthetic",
        action_payload={},
        pred_states=[make(densities_pred, speeds_pred) for _ in range(horizon)],
        obs_states=[make(densities_obs, speeds_obs) for _ in range(horizon)],
        geometry=geometry,
    )


def synth_g6(pairs, *, decision_id="d", spillback=None):
    out = []
    for index, (cid, model, observed) in enumerate(pairs):
        ms, os_ = (False, False) if spillback is None else spillback[index]
        out.append(rec.build_record(
            decision_id=decision_id, candidate_id=cid, model_objective=model,
            vissim_objective=observed, model_spillback=ms, vissim_spillback=os_,
            action_payload={"c": cid}, policy_hash=_H["policy"], build_hash=_H["build"],
            action_schema_hash=_H["schema"], topology_hash=_H["topology"],
            program_hash=_H["program"], state_hash=_H["state"],
            model_runtime_sec=0.01, decision_runtime_sec=1.0))
    return out


# ---------------------------------------------------------------------------
# 층 1 — G6 순위 지표
# ---------------------------------------------------------------------------


class Layer1G6Ranking(unittest.TestCase):
    def test_perfect_agreement_is_plus_one(self):
        report = rec.evaluate_shadow_records(synth_g6(
            [("c0", 100.0, 10.0), ("c1", 200.0, 20.0), ("c2", 300.0, 30.0), ("c3", 400.0, 40.0)]))
        self.assertEqual(report["aggregate"]["spearman_rho"], 1.0)
        self.assertEqual(report["aggregate"]["top_action_pairwise"]["agreement"], 1.0)

    def test_exact_reversal_is_minus_one(self):
        report = rec.evaluate_shadow_records(synth_g6(
            [("c0", 100.0, 40.0), ("c1", 200.0, 30.0), ("c2", 300.0, 20.0), ("c3", 400.0, 10.0)]))
        self.assertAlmostEqual(report["aggregate"]["spearman_rho"], -1.0)
        self.assertEqual(report["aggregate"]["top_action_pairwise"]["agreement"], 0.0)
        self.assertEqual(report["gates"]["g6_initial"]["verdict"], FAIL)

    def test_persistence_cannot_be_ranked(self):
        """Delta=0 는 모든 후보에 같은 값 -> Spearman 정의불가 -> NOT_EVALUATED.

        G5 에서 persistence 가 이겼다는 사실이 G6 에서는 아무 의미가 없다는 것을
        지표가 스스로 드러내야 한다. PASS 로 새지 않는지 확인한다.
        """

        report = rec.evaluate_shadow_records(synth_g6(
            [("c0", 500.0, 10.0), ("c1", 500.0, 20.0), ("c2", 500.0, 30.0)]))
        self.assertIsNone(report["aggregate"]["spearman_rho"])
        self.assertFalse(report["aggregate"]["ranking_oracle_complete"])
        self.assertEqual(report["gates"]["g6_initial"]["verdict"], NOT_EVALUATED)
        self.assertNotEqual(report["gates"]["g6_initial"]["verdict"], PASS)

    def test_top_action_swap_caught_even_with_high_rho(self):
        report = rec.evaluate_shadow_records(synth_g6([
            ("c0", 10.0, 22.0), ("c1", 20.0, 10.0), ("c2", 30.0, 30.0),
            ("c3", 40.0, 40.0), ("c4", 50.0, 50.0)]))
        self.assertGreater(report["aggregate"]["spearman_rho"], 0.70)
        self.assertLess(report["aggregate"]["top_action_pairwise"]["agreement"], 0.80)
        self.assertEqual(report["gates"]["g6_initial"]["verdict"], FAIL)

    def test_spillback_f1_perfect_and_inverted(self):
        pairs = [("c0", 1.0, 1.0), ("c1", 2.0, 2.0), ("c2", 3.0, 3.0), ("c3", 4.0, 4.0)]
        good = rec.evaluate_shadow_records(synth_g6(
            pairs, spillback=[(True, True), (True, True), (False, False), (False, False)]))
        self.assertEqual(good["aggregate"]["spillback"]["f1"], 1.0)
        bad = rec.evaluate_shadow_records(synth_g6(
            pairs, spillback=[(True, False), (True, False), (False, True), (False, True)]))
        self.assertEqual(bad["aggregate"]["spillback"]["f1"], 0.0)


# ---------------------------------------------------------------------------
# 층 2 — G5 상태오차 지표
# ---------------------------------------------------------------------------


class Layer2G5Metrics(unittest.TestCase):
    def test_zero_error_gives_zero_mae_and_mape(self):
        rho = [10.0] * 8
        v = [100.0] * 8
        episode = fake_episode(densities_pred=rho, densities_obs=rho,
                               speeds_pred=v, speeds_obs=v)
        samples = g5.freeway_samples(episode)
        self.assertEqual(g5.aggregate(samples, "cell_count")["mae"], 0.0)
        self.assertEqual(g5.aggregate(samples, "cell_speed")["mape"], 0.0)
        self.assertEqual(g5.aggregate(samples, "link_speed")["mape"], 0.0)

    def test_planted_count_error_is_recovered_exactly(self):
        """모든 셀에 +3 veh 를 심으면 cell count MAE 는 정확히 3.0 이어야 한다."""

        obs = [10.0] * 8
        pred = [13.0] * 8
        episode = fake_episode(densities_pred=pred, densities_obs=obs,
                               speeds_pred=[100.0] * 8, speeds_obs=[100.0] * 8)
        stats = g5.aggregate(g5.freeway_samples(episode), "cell_count")
        self.assertAlmostEqual(stats["mae"], 3.0)
        self.assertAlmostEqual(stats["bias"], 3.0)
        self.assertEqual(stats["entity_count"], 8)

    def test_planted_speed_error_is_recovered_exactly(self):
        """관측 100 kph, 예측 110 kph -> MAPE = 0.10 (임계와 정확히 같은 지점)."""

        episode = fake_episode(densities_pred=[10.0] * 8, densities_obs=[10.0] * 8,
                               speeds_pred=[110.0] * 8, speeds_obs=[100.0] * 8)
        samples = g5.freeway_samples(episode)
        self.assertAlmostEqual(g5.aggregate(samples, "cell_speed")["mape"], 0.10)
        self.assertAlmostEqual(g5.aggregate(samples, "link_speed")["mape"], 0.10)

    def test_cell_and_link_levels_diverge_on_cancelling_errors(self):
        """★ 이전 보고의 '링크평균은 통과, 셀 단위는 실패'를 재현하는 케이스.

        셀 오차가 부호가 엇갈려 상쇄되면 링크 총량은 맞는데 셀은 크게 틀린다.
        두 수준을 다 보고해야 하는 이유가 이것이다.
        """

        obs = [10.0] * 8
        pred = [16.0, 4.0] * 4          # 셀마다 +-6, 링크 합은 동일
        episode = fake_episode(densities_pred=pred, densities_obs=obs,
                               speeds_pred=[100.0] * 8, speeds_obs=[100.0] * 8)
        samples = g5.freeway_samples(episode)
        cell = g5.aggregate(samples, "cell_count")
        link = g5.aggregate(samples, "link_count")
        self.assertAlmostEqual(cell["mae"], 6.0)
        self.assertAlmostEqual(link["mae"], 0.0)
        # 임계는 수준마다 다시 계산된다: 셀은 max(5, 0.1*10)=5, 링크는 max(5, 0.1*80)=8
        self.assertAlmostEqual(g5.count_threshold(cell, g5.DEFAULT_THRESHOLDS), 5.0)
        self.assertAlmostEqual(g5.count_threshold(link, g5.DEFAULT_THRESHOLDS), 8.0)

    def test_gate_requires_both_levels(self):
        """느슨한 수준만 통과하면 게이트는 PASS 가 아니어야 한다."""

        class FakeNet:
            urban_link_storage_veh: dict = {}
            movement_links: list = []

        episode = fake_episode(densities_pred=[16.0, 4.0] * 4, densities_obs=[10.0] * 8,
                               speeds_pred=[100.0] * 8, speeds_obs=[100.0] * 8)
        report = g5.evaluate_g5([episode], net=FakeNet(), detector_mapping={})
        verdicts = {c["name"]: c["verdict"] for c in report["gates"]["g5_initial"]["criteria"]}
        self.assertEqual(verdicts["cell_count_mae"], FAIL)     # 6.0 > 5.0
        self.assertEqual(verdicts["link_count_mae"], PASS)     # 0.0 <= 8.0
        self.assertEqual(report["gates"]["g5_initial"]["verdict"], FAIL)

    def test_urban_gate_is_not_evaluated_when_coverage_incomplete(self):
        """관측이 도시부를 덮지 않으면 NOT_EVALUATED — PASS 로 위장하지 않는다."""

        class FakeNet:
            urban_link_storage_veh = {f"L{i}_out": 220.0 for i in range(20)}
            movement_links = [f"M{i}" for i in range(10)]

        episode = fake_episode(densities_pred=[10.0] * 8, densities_obs=[10.0] * 8,
                               speeds_pred=[100.0] * 8, speeds_obs=[100.0] * 8)
        report = g5.evaluate_g5([episode], net=FakeNet(),
                                detector_mapping={"ramp_link_to_queues": {"10480": ["R_D_W"]}})
        urban = report["urban"]
        self.assertLess(urban["coverage"]["ratio"], 1.0)
        self.assertFalse(urban["evaluable"])
        criterion = [c for c in report["gates"]["g5_initial"]["criteria"]
                     if c["name"] == "urban_one_step_queue_storage_error"][0]
        self.assertEqual(criterion["verdict"], NOT_EVALUATED)
        self.assertEqual(report["gates"]["g5_initial"]["verdict"], NOT_EVALUATED)

    def test_persistence_skill_score_sign(self):
        class FakeNet:
            urban_link_storage_veh: dict = {}
            movement_links: list = []

        model = fake_episode(densities_pred=[11.0] * 8, densities_obs=[10.0] * 8,
                             speeds_pred=[100.0] * 8, speeds_obs=[100.0] * 8)
        worse = fake_episode(densities_pred=[14.0] * 8, densities_obs=[10.0] * 8,
                             speeds_pred=[100.0] * 8, speeds_obs=[100.0] * 8)
        report = g5.evaluate_g5([model], net=FakeNet(), detector_mapping={},
                                persistence_episodes=[worse])
        self.assertAlmostEqual(report["persistence_baseline"]["skill_score"]["cell_count"], 0.75)


# ---------------------------------------------------------------------------
# 층 3 — 공용성: 두 게이트가 같은 rollout 함수를 쓰는지
# ---------------------------------------------------------------------------


class Layer3SharedRollout(unittest.TestCase):
    def test_both_gates_call_build_episode(self):
        import inspect
        import run_gates
        g5_src = inspect.getsource(run_gates.collect_g5_episodes)
        g6_src = inspect.getsource(run_gates.run_g6)
        self.assertIn("build_episode", g5_src)
        self.assertIn("build_episode", g6_src)

    def test_candidate_set_covers_contract_axes(self):
        axes = {c.axis for c in core.ACTIVE_CANDIDATE_SET}
        for required in ("vsl", "ramp", "green", "offset"):
            self.assertIn(required, axes, f"계약 §11 G6 이 요구한 {required} perturbation 누락")

    def test_horizon_is_60s_based(self):
        """★ 지평 정정 확인 — control_interval 이 60 s 라야 H=1/3/5 = 60/180/300 s 다."""

        state_json = {"control_interval_sec": 60.0, "sim_period_sec": 1200.0}
        self.assertEqual(ep.control_interval_of(state_json), 60)


# ---------------------------------------------------------------------------
# 층 4 — 실데이터 rolling-origin
# ---------------------------------------------------------------------------

REAL_RUN = (core.VISSIM_ROOT /
            "evaluation/runs/new_baseline_ab_20260801/"
            "decisions_pstack_flagship_scale135_warm900_eval3600_seed13")


class Layer4RealRollingOrigin(unittest.TestCase):
    @unittest.skipUnless(REAL_RUN.exists(), f"실 런 없음: {REAL_RUN}")
    def test_rolling_origin_reanchors_every_step(self):
        series = ep.state_series(REAL_RUN)
        self.assertGreater(len(series), 20)
        anchor_json = ep.read_json(series[min(series)])
        rt = core.build_runtime(anchor_json)
        self.assertEqual(int(round(float(rt.cfg.simulation.control_interval))), 60,
                         "운영 control_interval 은 60 s 여야 한다")

        times = [t for t in sorted(series) if 900 <= t <= 1200]
        anchors = [ep.build_anchor(rt, series[t], t, 3) for t in times]
        # 앵커마다 상태가 실제로 다르다 = 매 시점 실측으로 다시 잡았다.
        signatures = {tuple(round(x, 6) for x in a.state.freeway_density["FW_E"]) for a in anchors}
        self.assertEqual(len(signatures), len(anchors), "앵커가 실측으로 리셋되지 않았다")

        episodes = []
        for anchor, t in zip(anchors, times):
            control = ep.executed_control(rt, REAL_RUN, t)
            episodes.append(ep.build_episode(rt, anchor, control, 3, observed=series,
                                             action_id=f"executed@{t}"))
        self.assertTrue(all(e.complete for e in episodes))
        report = g5.evaluate_g5(episodes, net=rt.cfg.network,
                                detector_mapping=rt.detector_mapping)
        for level in ("cell_count", "cell_speed", "link_count", "link_speed"):
            self.assertGreater(report["aggregate"][level]["sample_count"], 0)
        print(f"\n[layer4] anchors={len(episodes)} "
              f"cell_count_MAE={report['aggregate']['cell_count']['mae']:.3f} "
              f"cell_speed_MAPE={report['aggregate']['cell_speed']['mape']:.4f} "
              f"link_speed_MAPE={report['aggregate']['link_speed']['mape']:.4f}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
