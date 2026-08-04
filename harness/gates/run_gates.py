# G5/G6 공용 하네스 오케스트레이터 — 같은 rollout 을 한 번 굴려 G5 상태오차와 G6 순위일치를 함께 낸다.
"""사용법.

  # G5 (teacher-forced rolling-origin) + G6 (후보 스윕) 를 한 번에
  python run_gates.py --g5-run-dir <decisions_*> [--g5-run-dir ...] \
                      --g6-run-dir <branch grid run dir> --g6-t0 900 \
                      --horizons 1,3,5 --out-dir <outputs>

  # G5 만
  python run_gates.py --g5-run-dir <decisions_*> --out-dir <outputs>

산출물.
  <out>/g5_report.json          G5 지표·게이트 (전체)
  <out>/g5_by_stratum.json      seed/demand/policy 계층별 G5 + holdout fold 분리표
  <out>/g5_free_run.json        참고 지표 (B) 개루프 자유주행
  <out>/g6_records.jsonl        shadow.py 가 먹는 레코드
  <out>/g6_report.json          shadow.py 판정 (Spearman / pairwise / spillback F1)
  <out>/gates_summary.json      두 게이트 한 장 요약

★ 프로토콜. 본 시험은 (A) teacher-forced rolling-origin 이다. 매 제어시점 t 에서 실측
  (rho, v, 큐) 로 앵커하고 H=1/3/5 (60/180/300 s) 를 예측한다. 매 시점 새로 앵커한다.
  (B) 개루프 자유주행은 `--free-run` 으로 별도 기록만 한다(판정에 쓰지 않는다).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import episode as ep  # noqa: E402
import g5_metrics as g5  # noqa: E402
import g6_core as core  # noqa: E402
import g6_records as rec  # noqa: E402


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str),
                    encoding="utf-8")


# ---------------------------------------------------------------------------
# G5 — 앵커 시각을 스윕한다
# ---------------------------------------------------------------------------


def collect_g5_episodes(
    rt: core.G6Runtime,
    decision_dir: Path,
    horizons: list[int],
    *,
    t_min: int,
    t_max: int | None,
    stride: int,
) -> tuple[list[ep.Episode], list[ep.Episode], dict[str, Any]]:
    """한 런에서 rolling-origin 에피소드를 모은다.

    반환 = (모델 에피소드, persistence 대조군 에피소드, 진단).
    앵커마다 **그 시각에 실제 집행된 액션**으로 굴린다(teacher forcing 의 액션 쪽).
    """

    observed = ep.state_series(decision_dir)
    interval = int(round(float(rt.cfg.simulation.control_interval)))
    times = [t for t in observed if t >= t_min and (t_max is None or t <= t_max)]
    times = [t for t in times if (t - t_min) % (stride * interval) == 0]

    model_eps: list[ep.Episode] = []
    persist_eps: list[ep.Episode] = []
    skipped: list[dict[str, Any]] = []
    max_h = max(horizons)

    for t in times:
        # 지평 끝까지 관측이 있어야 한 앵커가 성립한다.
        need = [t + interval * k for k in range(1, max_h + 1)]
        if any(sec not in observed for sec in need):
            skipped.append({"t_sec": t, "reason": "관측 궤적이 지평 끝까지 없음"})
            continue
        anchor = ep.build_anchor(rt, observed[t], t, max_h)
        control = ep.executed_control(rt, decision_dir, t)
        for horizon in horizons:
            model_eps.append(ep.build_episode(
                rt, anchor, control, horizon, observed=observed,
                action_id=f"executed@{t}", action_payload={"source": "action_json", "t_sec": t}))
            persist_eps.append(ep.build_episode(
                rt, anchor, control, horizon, observed=observed,
                action_id=f"persistence@{t}", persistence=True,
                action_payload={"source": "persistence_delta0", "t_sec": t}))
    diag = {
        "decision_dir": str(decision_dir),
        "observed_state_count": len(observed),
        "observed_range_sec": [min(observed), max(observed)] if observed else None,
        "anchor_count": len(times) - len(skipped),
        "skipped": skipped[:10],
        "skipped_count": len(skipped),
    }
    return model_eps, persist_eps, diag


def run_g5(args, horizons: list[int]) -> dict[str, Any] | None:
    dirs = [Path(d).resolve() for d in (args.g5_run_dir or [])]
    dirs = [d for d in dirs if d.is_dir()]
    if not dirs:
        return None

    all_model: list[ep.Episode] = []
    all_persist: list[ep.Episode] = []
    by_stratum: dict[str, dict[str, Any]] = {}
    diagnostics: list[dict[str, Any]] = []
    free_run: list[dict[str, Any]] = []
    runtime_ref: core.G6Runtime | None = None

    for decision_dir in dirs:
        observed = ep.state_series(decision_dir)
        if not observed:
            diagnostics.append({"decision_dir": str(decision_dir), "error": "state_*.json 없음"})
            continue
        anchor_json = ep.read_json(observed[min(observed)])
        rt = core.build_runtime(
            anchor_json,
            mapping_json=args.mapping_json, detector_mapping_json=args.detector_mapping_json,
            calibration_json=args.calibration_json, tuning_json=args.tuning_json)
        runtime_ref = runtime_ref or rt

        model_eps, persist_eps, diag = collect_g5_episodes(
            rt, decision_dir, horizons,
            t_min=args.g5_t_min, t_max=args.g5_t_max, stride=args.g5_stride)
        diagnostics.append(diag)
        all_model.extend(model_eps)
        all_persist.extend(persist_eps)

        stratum = ep.stratum_of(decision_dir)
        if model_eps:
            by_stratum[stratum.key()] = {
                "seed": stratum.seed, "demand": stratum.demand, "policy": stratum.policy,
                "decision_dir": str(decision_dir),
                "report": g5.evaluate_g5(model_eps, net=rt.cfg.network,
                                         detector_mapping=rt.detector_mapping,
                                         persistence_episodes=persist_eps,
                                         label=stratum.key()),
            }

        if args.free_run:
            times = sorted(observed)
            t0 = next((t for t in times if t >= args.g5_t_min), None)
            if t0 is not None:
                interval = int(round(float(rt.cfg.simulation.control_interval)))
                steps = (max(times) - t0) // interval
                if steps >= 1:
                    anchor = ep.build_anchor(rt, observed[t0], t0, int(steps))
                    control = ep.executed_control(rt, decision_dir, t0)
                    fr = ep.build_free_run_episode(rt, anchor, control, int(steps),
                                                   observed=observed, action_id=f"free_run@{t0}")
                    free_run.append({
                        "decision_dir": str(decision_dir), "t0_sec": t0, "steps": int(steps),
                        "report": g5.evaluate_g5([fr], net=rt.cfg.network,
                                                 detector_mapping=rt.detector_mapping,
                                                 label=f"free_run:{decision_dir.name}"),
                    })

    if not all_model or runtime_ref is None:
        return {"error": "G5 에피소드 0개", "diagnostics": diagnostics}

    overall = g5.evaluate_g5(all_model, net=runtime_ref.cfg.network,
                             detector_mapping=runtime_ref.detector_mapping,
                             persistence_episodes=all_persist, label="all")
    overall["diagnostics"] = diagnostics

    # 지평별 재채점 — H=1/3/5 를 따로 본다.
    overall["by_horizon"] = {}
    for horizon in horizons:
        subset = [e for e in all_model if e.horizon == horizon]
        base = [e for e in all_persist if e.horizon == horizon]
        if subset:
            overall["by_horizon"][str(horizon)] = g5.evaluate_g5(
                subset, net=runtime_ref.cfg.network, detector_mapping=runtime_ref.detector_mapping,
                persistence_episodes=base, label=f"H={horizon}")

    strata = [ep.stratum_of(Path(v["decision_dir"])) for v in by_stratum.values()]
    holdout = {axis: {k: [s.key() for s in v] for k, v in ep.holdout_split(strata, axis).items()}
               for axis in ("seed", "demand", "policy")}
    separation = {axis: len(groups) for axis, groups in holdout.items()}

    return {
        "overall": overall,
        "by_stratum": by_stratum,
        "holdout": {
            "axes": holdout,
            "distinct_values": separation,
            "separable": {axis: count >= 2 for axis, count in separation.items()},
            "note": "계약 §11 G5 는 seed/demand profile/control policy 단위 holdout 분리를 요구한다. "
                    "distinct_values 가 1 이면 그 축은 분리 불가(단일 값)다.",
        },
        "free_run_reference": free_run,
    }


# ---------------------------------------------------------------------------
# G6 — 후보 액션을 스윕한다 (같은 build_episode 를 쓴다)
# ---------------------------------------------------------------------------


def run_g6(args, horizons: list[int]) -> dict[str, Any] | None:
    if not args.g6_run_dir:
        return None
    run_dir = Path(args.g6_run_dir).resolve()
    if not run_dir.is_dir():
        return {"error": f"없는 디렉터리: {run_dir}"}

    cells = _discover_cells(run_dir, args.g6_t0)
    if not cells:
        return {"error": f"후보 셀 0개 (run_dir={run_dir}, t0={args.g6_t0})"}

    policy_hash = rec.hash_payload({"tuning": str(args.tuning_json),
                                    "calibration": str(args.calibration_json)})
    build_hash = rec.file_hash(core.ADAPTER_DIR / "vissim_stackelberg_adapter.py")
    schema_hash = rec.hash_payload({"candidate_set": [c.candidate_id for c in core.ACTIVE_CANDIDATE_SET]})

    records: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []

    for (cell, seed), arms in sorted(cells.items()):
        anchor_dir = arms[sorted(arms)[0]]
        anchor_path = anchor_dir / f"state_{args.g6_t0:06d}.json"
        init_json = ep.read_json(anchor_path)
        rt = core.build_runtime(
            init_json, mapping_json=args.mapping_json,
            detector_mapping_json=args.detector_mapping_json,
            calibration_json=args.calibration_json, tuning_json=args.tuning_json)

        # 초기상태 동일성 = 공통 접두 리플레이가 성립했다는 증거. 어긋나면 셀을 버린다.
        hashes = {arm: rec.file_hash(path / f"state_{args.g6_t0:06d}.json")
                  for arm, path in arms.items()}
        if len(set(hashes.values())) != 1:
            print(f"ERROR=INITIAL_STATE_MISMATCH cell={cell} seed={seed}")
            continue
        state_hash = next(iter(hashes.values()))

        anchor = ep.build_anchor(rt, anchor_path, args.g6_t0, max(horizons))
        topology_hash = rec.hash_payload({"mapping": str(args.mapping_json)})
        program_hash = rec.hash_payload({"cell": cell, "seed": seed, "t0": args.g6_t0})

        for horizon in horizons:
            decision_id = f"{cell}_seed{seed}_H{horizon}"
            for arm, decision_dir in sorted(arms.items()):
                try:
                    cand = core.candidate_by_id(arm)
                except KeyError:
                    continue
                control = ep.candidate_control(rt, cand)
                observed = ep.state_series(decision_dir)
                episode = ep.build_episode(
                    rt, anchor, control, horizon, observed=observed, action_id=arm,
                    action_payload={"variant": cand.variant, "vsl_kph": cand.vsl_kph,
                                    "d_ramp_vph": cand.d_ramp_vph, "f_ramp_vph": cand.f_ramp_vph,
                                    "major_green_sec": cand.major_green_sec,
                                    "minor_green_sec": cand.minor_green_sec,
                                    "offset_sec": cand.offset_sec, "horizon_steps": horizon})

                model_terms = core.objective_from_states(rt, episode.pred_states, control)
                model_spill = core.spillback_flag(rt, episode.pred_states,
                                                  threshold=args.spillback_threshold)
                if episode.complete:
                    obs_terms = core.objective_from_states(rt, episode.obs_states, control)
                    obs_spill = core.spillback_flag(rt, episode.obs_states,
                                                    threshold=args.spillback_threshold)
                else:
                    obs_terms, obs_spill = None, None

                records.append(rec.build_record(
                    decision_id=decision_id, candidate_id=arm,
                    model_objective=model_terms["g6_objective"],
                    vissim_objective=None if obs_terms is None else obs_terms["g6_objective"],
                    model_spillback=model_spill, vissim_spillback=obs_spill,
                    action_payload=episode.action_payload,
                    policy_hash=policy_hash, build_hash=build_hash, action_schema_hash=schema_hash,
                    topology_hash=topology_hash, program_hash=program_hash, state_hash=state_hash,
                    model_runtime_sec=episode.model_runtime_sec))
                rows.append({
                    "decision_id": decision_id, "candidate_id": arm, "axis": cand.axis,
                    "horizon_steps": horizon,
                    "model_objective": model_terms["g6_objective"],
                    "vissim_objective": None if obs_terms is None else obs_terms["g6_objective"],
                    "model_ttt_veh_h": model_terms["g6_ttt_veh_h"],
                    "vissim_ttt_veh_h": None if obs_terms is None else obs_terms["g6_ttt_veh_h"],
                    "model_spillback": model_spill, "vissim_spillback": obs_spill,
                    "missing_obs_sec": episode.missing_sec,
                })

        # Delta=0 대조군 — 모든 후보에 같은 값이라 Spearman 이 정의되지 않는다는 사실이
        # 리포트에 드러나야 한다. 별도 decision 으로 넣는다.
        if args.g6_persistence:
            for horizon in horizons:
                decision_id = f"{cell}_seed{seed}_H{horizon}__PERSISTENCE"
                for arm, decision_dir in sorted(arms.items()):
                    try:
                        cand = core.candidate_by_id(arm)
                    except KeyError:
                        continue
                    control = ep.candidate_control(rt, cand)
                    observed = ep.state_series(decision_dir)
                    episode = ep.build_episode(
                        rt, anchor, control, horizon, observed=observed,
                        action_id=f"{arm}__persist", persistence=True,
                        action_payload={"candidate": arm, "predictor": "persistence_delta0",
                                        "horizon_steps": horizon})
                    model_terms = core.objective_from_states(rt, episode.pred_states, control)
                    if episode.complete:
                        obs_terms = core.objective_from_states(rt, episode.obs_states, control)
                        obs_spill = core.spillback_flag(rt, episode.obs_states,
                                                        threshold=args.spillback_threshold)
                    else:
                        obs_terms, obs_spill = None, None
                    records.append(rec.build_record(
                        decision_id=decision_id, candidate_id=arm,
                        model_objective=model_terms["g6_objective"],
                        vissim_objective=None if obs_terms is None else obs_terms["g6_objective"],
                        model_spillback=core.spillback_flag(rt, episode.pred_states,
                                                            threshold=args.spillback_threshold),
                        vissim_spillback=obs_spill, action_payload=episode.action_payload,
                        policy_hash=policy_hash, build_hash=build_hash,
                        action_schema_hash=schema_hash, topology_hash=topology_hash,
                        program_hash=program_hash, state_hash=state_hash,
                        model_runtime_sec=episode.model_runtime_sec))

    # ★ persistence 레코드는 **반드시 분리**한다. Delta=0 는 설계상 rho 가 정의되지
    # 않으므로, 같은 리포트에 섞으면 shadow 의 ranking_oracle_complete 가 False 로
    # 내려가고 본 시험의 FAIL 이 NOT_EVALUATED 로 **가려진다**. 실제로 그렇게 나왔다.
    main_records = [r for r in records if "__PERSISTENCE" not in r["decision_id"]]
    persistence_records = [r for r in records if "__PERSISTENCE" in r["decision_id"]]
    return {"records": main_records, "persistence_records": persistence_records, "rows": rows}


def _discover_cells(run_dir: Path, t0: int) -> dict[tuple[str, str], dict[str, Path]]:
    import re
    known = sorted((c.candidate_id for c in core.ACTIVE_CANDIDATE_SET), key=len, reverse=True)
    cells: dict[tuple[str, str], dict[str, Path]] = {}
    for child in sorted(run_dir.glob("decisions_*")):
        if not child.is_dir() or not (child / f"state_{int(t0):06d}.json").exists():
            continue
        name = child.name[len("decisions_"):]
        match = re.match(r"^(?P<head>.+)_seed(?P<seed>\d+)$", name)
        if not match:
            continue
        head, seed = match.group("head"), match.group("seed")
        arm = next((cid for cid in known if head == cid or head.endswith("_" + cid)), None)
        if arm is None:
            continue
        cell = head[: len(head) - len(arm)].rstrip("_") or "default"
        cells.setdefault((cell, seed), {})[arm] = child
    return cells


# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--horizons", default="1,3,5",
                        help="제어스텝 단위. 60 s 간격이므로 1,3,5 = 60/180/300 s")
    # G5
    parser.add_argument("--g5-run-dir", action="append", default=[],
                        help="decisions_* 디렉터리. 여러 번 줄 수 있다(계층 분리에 쓰인다).")
    parser.add_argument("--g5-t-min", type=int, default=900)
    parser.add_argument("--g5-t-max", type=int, default=None)
    parser.add_argument("--g5-stride", type=int, default=1, help="앵커 간격(제어스텝 배수)")
    parser.add_argument("--free-run", action="store_true",
                        help="참고 지표 (B) 개루프 자유주행을 함께 기록한다")
    # G6
    parser.add_argument("--g6-run-dir", type=Path, default=None)
    parser.add_argument("--g6-t0", type=int, default=900)
    parser.add_argument("--g6-persistence", action="store_true", default=True)
    parser.add_argument("--spillback-threshold", type=float, default=0.90)
    # 공통 설정
    parser.add_argument("--mapping-json", type=Path, default=core.DEFAULT_MAPPING)
    parser.add_argument("--detector-mapping-json", type=Path, default=core.DEFAULT_DETECTOR_MAPPING)
    parser.add_argument("--calibration-json", type=Path, default=core.DEFAULT_CALIBRATION)
    parser.add_argument("--tuning-json", type=Path, default=core.DEFAULT_TUNING)
    args = parser.parse_args()

    horizons = [int(h) for h in str(args.horizons).split(",") if h.strip()]
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    summary: dict[str, Any] = {"horizons_steps": horizons, "protocol": "teacher_forced_rolling_origin"}

    g5_result = run_g5(args, horizons)
    if g5_result and "overall" in g5_result:
        _write(out / "g5_report.json", g5_result["overall"])
        _write(out / "g5_by_stratum.json",
               {"by_stratum": g5_result["by_stratum"], "holdout": g5_result["holdout"]})
        if g5_result["free_run_reference"]:
            _write(out / "g5_free_run.json", g5_result["free_run_reference"])
        gates = g5_result["overall"]["gates"]
        summary["g5"] = {
            "episode_count": g5_result["overall"]["episode_count"],
            "initial": gates["g5_initial"]["verdict"],
            "promotion": gates["g5_promotion"]["verdict"],
            "criteria": {c["name"]: {"value": c["value"], "threshold": c["threshold"],
                                     "verdict": c["verdict"]}
                         for c in gates["g5_initial"]["criteria"]},
            "by_horizon": {h: {c["name"]: c["verdict"]
                               for c in r["gates"]["g5_initial"]["criteria"]}
                           for h, r in g5_result["overall"].get("by_horizon", {}).items()},
            "holdout": g5_result["holdout"]["distinct_values"],
        }
        print(f"G5 initial={gates['g5_initial']['verdict']} "
              f"promotion={gates['g5_promotion']['verdict']} "
              f"episodes={g5_result['overall']['episode_count']}")
        for c in gates["g5_initial"]["criteria"]:
            print(f"   {c['name']:<38} {c['value']} <= {c['threshold']}  {c['verdict']}")
    elif g5_result:
        summary["g5"] = g5_result
        print(f"G5 SKIPPED: {g5_result.get('error')}")

    g6_result = run_g6(args, horizons)
    if g6_result and "records" in g6_result:
        rec.write_jsonl(out / "g6_records.jsonl", g6_result["records"])
        _write(out / "g6_rows.json", g6_result["rows"])
        report = rec.evaluate_and_write(g6_result["records"], out / "g6_report.json")
        # 완결 decision 만 모은 부분집합 — 게이트가 NOT_EVALUATED 로 내려가도
        # 측정된 rho/pairwise 가 임계를 넘는지 못 넘는지는 드러나야 한다.
        complete_ids = {d["decision_id"] for d in report["per_decision"]
                        if d["ranking_status"] != rec.NOT_EVALUATED}
        complete = [r for r in g6_result["records"] if r["decision_id"] in complete_ids]

        by_h = {}
        for horizon in horizons:
            subset = [r for r in complete if r["decision_id"].endswith(f"_H{horizon}")]
            if subset:
                by_h[str(horizon)] = rec.evaluate_shadow_records(subset)
        _write(out / "g6_by_horizon.json",
               {h: {"horizon_sec": int(h) * 60,
                    "spearman_rho": r["aggregate"]["spearman_rho"],
                    "pairwise": r["aggregate"]["top_action_pairwise"]["agreement"],
                    "spillback_f1": r["aggregate"]["spillback"]["f1"],
                    "spillback_oracle_complete": r["aggregate"]["spillback_oracle_complete"],
                    "g6_initial": r["gates"]["g6_initial"]["verdict"],
                    "criteria": {c["name"]: c["verdict"]
                                 for c in r["gates"]["g6_initial"]["criteria"]}}
                for h, r in by_h.items()})
        strict = rec.evaluate_shadow_records(complete) if complete else None
        if strict is not None:
            _write(out / "g6_report_complete_only.json", strict)

        persistence = g6_result.get("persistence_records") or []
        if persistence:
            rec.write_jsonl(out / "g6_records_persistence.jsonl", persistence)
            persistence_report = rec.evaluate_and_write(
                persistence, out / "g6_report_persistence.json")
            summary["g6_persistence_control"] = {
                "decision_count": persistence_report["decision_count"],
                "spearman_rho": persistence_report["aggregate"]["spearman_rho"],
                "ranking_oracle_complete":
                    persistence_report["aggregate"]["ranking_oracle_complete"],
                "verdict": persistence_report["gates"]["g6_initial"]["verdict"],
                "note": "Delta=0 는 후보마다 같은 목적함수 값을 내므로 Spearman 이 정의되지 "
                        "않는다(rho=None, NOT_EVALUATED). G5 에서 persistence 가 이겼다는 "
                        "사실이 G6 순위 판정에는 아무 근거도 되지 못한다는 것을 지표가 "
                        "스스로 드러낸다.",
            }

        summary["g6"] = {
            "decision_count": report["decision_count"],
            "spearman_rho": report["aggregate"]["spearman_rho"],
            "pairwise": report["aggregate"]["top_action_pairwise"]["agreement"],
            "spillback_f1": report["aggregate"]["spillback"]["f1"],
            "initial": report["gates"]["g6_initial"]["verdict"],
            "release": report["gates"]["g6_release"]["verdict"],
            "complete_decisions_only": None if strict is None else {
                "decision_count": strict["decision_count"],
                "spearman_rho": strict["aggregate"]["spearman_rho"],
                "pairwise": strict["aggregate"]["top_action_pairwise"]["agreement"],
                "spillback_f1": strict["aggregate"]["spillback"]["f1"],
                "initial": strict["gates"]["g6_initial"]["verdict"],
                "release": strict["gates"]["g6_release"]["verdict"],
            },
        }
        print(f"G6 initial={report['gates']['g6_initial']['verdict']} "
              f"rho={report['aggregate']['spearman_rho']} "
              f"pairwise={report['aggregate']['top_action_pairwise']['agreement']} "
              f"f1={report['aggregate']['spillback']['f1']}")
    elif g6_result:
        summary["g6"] = g6_result
        print(f"G6 SKIPPED: {g6_result.get('error')}")

    _write(out / "gates_summary.json", summary)
    print(f"OUT={out / 'gates_summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
