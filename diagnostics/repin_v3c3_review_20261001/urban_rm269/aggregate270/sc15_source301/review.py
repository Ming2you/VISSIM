"""Review source301 once using completed forecasts and cached native evidence."""
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
A = HERE.parent
ROOT = HERE.parents[4]
MOV = "movement:SC101_S_SC1_to_N_SC2005"


def read(p):
    return json.loads(Path(p).read_bytes())


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(p, value):
    Path(p).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf8")


def main():
    assert not (HERE / "completion.json").exists(), "Preserve completed review"
    assert not (HERE / "comparison.json").exists(), "Preserve attempted review"
    current = read(HERE / "forecast2400/summary.json")
    previous = read(A / "sc101_clock299/forecast2400/summary.json")
    old_comparison = read(A / "sc101_clock299/comparison.json")
    source_truth = read(A / "source_service300/source_audit.json")
    head_truth = read(A / "sc101_clock299/assessment.json")
    calibration = read(HERE / "calibration.json")
    assert current["status"] == "complete" and current["forecasts"] == 2
    assert current["initial_state_error"] == 0
    assert current["production_changes"] == current["optimizer_calls"] == current["native_runs"] == 0
    assert calibration["route_followup_end"] < current["start_sec"]
    pins = {}
    for report in (current, calibration):
        for path, digest in report["source_pins"].items():
            assert sha(path) == digest, path
        pins.update(report["source_pins"])
    paths = [
        HERE / "forecast2400/summary.json", A / "sc101_clock299/forecast2400/summary.json",
        A / "sc101_clock299/comparison.json", A / "source_service300/source_audit.json",
        A / "sc101_clock299/assessment.json", HERE / "calibration.json", Path(__file__),
    ]
    pins.update({str(p): sha(p) for p in paths})
    arms = {}
    for arm in ("hold", "city"):
        new = current["results"][arm]
        old = previous["results"][arm]
        assert new["writer_three_blocks"] and new["conservation_states"] == 4
        assert new["resource_max_exceedance"] < 1e-7 and new["shared_constraints"]["feasible"]
        responses = {}
        for label, folder in (("old", A / "sc101_clock299"), ("new", HERE)):
            path = folder / "forecast2400" / (arm + ".response.json.gz")
            pins[str(path)] = sha(path)
            responses[label] = json.loads(gzip.decompress(path.read_bytes()))
            assert responses[label]["model_constraint_coverage"]["complete"]
        sources = {}
        for inp, decision in (("1086", "1099"), ("1087", "1100")):
            native = [b["native_witnessed_head_crossings_lower"]
                      for b in source_truth["arms"][arm][decision]["blocks"]]
            models = {}
            for label, response in responses.items():
                rows = [t for t in response["transfers"] if t["source"] == "storage:native_" + inp + "_choice"]
                counts = [sum(t["vehicles"] for t in rows if start <= t["start_sec"] < start + 150)
                          for start in (2400, 2550, 2700)]
                models[label] = {
                    "counts": counts,
                    "mae_to_witnessed_lower_bound": sum(abs(x-y) for x, y in zip(counts, native))/3,
                }
            sources[inp] = {
                "native_crossing_lower_bounds": native, "models": models,
                "new_green_capacity_veh": calibration["inputs"][inp]["selected_service_veh_h"] * 35 / 3600,
            }
        heads = {}
        native_heads = [b["count"] for b in head_truth["native"][arm]["blocks"]]
        for label, response in responses.items():
            rows = [t for t in response["transfers"] if t["source"] == MOV and t["target"] != MOV]
            heads[label] = [sum(t["vehicles"] for t in rows if start <= t["start_sec"] < start + 150)
                            for start in (2400, 2550, 2700)]
        arms[arm] = {
            "old_omega_ttt_veh_h": old["omega_ttt_veh_h"], "new_omega_ttt_veh_h": new["omega_ttt_veh_h"],
            "source_discharge": sources, "sc101_through_departures": heads,
            "native_sc101_head_counts": native_heads, "endpoint_wall_sec": new["wall_sec"],
            "shared_feasible": new["shared_constraints"]["feasible"],
            "resource_max_exceedance": new["resource_max_exceedance"],
            "writer_three_blocks": True, "conservation_states": 4,
        }
    delta = arms["city"]["new_omega_ttt_veh_h"] - arms["hold"]["new_omega_ttt_veh_h"]
    old_delta = arms["city"]["old_omega_ttt_veh_h"] - arms["hold"]["old_omega_ttt_veh_h"]
    native_delta = old_comparison["native_city_minus_hold_veh_h"]
    budget = dict(closed_fzp_passes=1, candidate_parameter_sets=1, fitted_source_rates=2,
                  fixed450=2, optimizer=0, ad=0, native=0, production_changes=0, pushes=0)
    report = dict(
        status="complete_past_source_service_candidate_not_gain_qualified", goal_complete=False,
        initial_state_error=0, arms=arms,
        old_city_minus_hold_veh_h=old_delta, new_city_minus_hold_veh_h=delta,
        native_city_minus_hold_veh_h=native_delta, gain_direction_correct=delta*native_delta > 0,
        source_route_support={
            inp: {k: row[k] for k in ("route_counts", "route_share_identification_bounds")}
            for inp, row in calibration["inputs"].items()
        },
        budget_used=budget, source_pins=pins,
        limitations=[
            "Rates use past900-2100 queue platoons only;5s timing bounds are broad and not statistical confidence intervals.",
            "1086 departures remain below the new green capacity; do not treat the remaining gap as evidence to raise that capacity again.",
            "Source outcomes include unresolved vehicles; their downstream turns are not normalized away or provided as future rollout inputs.",
            "SC101 head-lane crossings are not exactly final through turns; the observed overlaps remain in source300.",
            "Endpoint times are fixed-command forecasts, not full SDMPC optimization or native wall times.",
            "No new independent seed/state or AD/optimizer qualification was performed for these two rates.",
        ],
    )
    save(HERE / "comparison.json", report)
    route_lines = []
    source_lines = []
    for inp in ("1086", "1087"):
        row = calibration["inputs"][inp]
        source_lines.append(f"| {inp} | {row['old_rate_veh_h']:.2f} | {row['selected_service_veh_h']:.2f} | "
                            f"{row['measurement_lower_veh_h']:.2f}–{row['measurement_upper_veh_h']:.2f} |")
        c = row["route_counts"]
        b = row["route_share_identification_bounds"]["straight"]
        route_lines.append(f"- {inp}: 직진 {c.get('straight', 0)}, 우회전 {c.get('right', 0)}, "
                           f"좌회전 {c.get('left', 0)}, 미해결 {c.get('unresolved', 0)}대. "
                           f"직진 비율 식별 범위 {100*b['lower']:.1f}–{100*b['upper']:.1f}%.")
    table = []
    for arm in ("hold", "city"):
        for inp, s in arms[arm]["source_discharge"].items():
            fmt = lambda values: " / ".join(f"{v:.2f}" for v in values)
            table.append(f"| {arm} {inp} | {fmt(s['models']['old']['counts'])} | "
                         f"{fmt(s['models']['new']['counts'])} | {fmt(s['native_crossing_lower_bounds'])} |")
    text = f"""# SC15 과거 자료 기반 방출 보정 — 공급은 개선, 도시 손익은 미검증

고속도로·램프5초/도시10초 후보에서 두 원천 방출률만 바꿔 저장2400초의 유지·도시신호450초 예측을 비교했다. **공급량 오차는 줄었지만 전체 도시 명령 손익 방향은 여전히 틀렸다.** 이득 검증 모델로 채택하지 않으며, 방출률을 더 올리는 탐색은 중단한다.

## 학습과 검증 구분

기존 완료 hold FZP의900–2100초 신호 직전 정지 대기열만 사용했다. 녹색 시작 시 앞3대를 제외한 알려진 대기 차량의 통과 간격을 합쳐 두 방출률을 한 번 추정했다. 경로 추적은2395.1초까지만 쓰고2400–2850초 검증 미래는 보정에 쓰지 않았다. 닫힌 FZP 한 번의 낮은 우선순위 추출은 E의 sc15_source301_past 캐시로 보존했다.

| 원천 | 기존 방출률 [대/시간] | 후보 | 5초 표본 시점의 측정 범위 |
|---|---:|---:|---:|
{chr(10).join(source_lines)}

이 범위는 통계적 신뢰구간이나 독립적인 포화율 검증이 아니다. 관측이 끝나지 않은 대기열은 제외했으므로 선택 편향도 남는다. 기존 seed13 망의 보수적 하한을 현재 망으로 옮긴 문제를 확인하는 한 쌍의 후보이며 계수 격자를 돌리지 않았다.

## 동일 초기 상태·명령·수요의 두 자율 예측

| 원천 방출 [대/150초, 세 구간] | 기존299 | 후보301 | native 관측 하한 |
|---|---|---|---|
{chr(10).join(table)}

1086은 후보 녹색 상한20.067대보다 실제 예측 방출이 작다. 남은 차이를 방출 상한 부족으로 단정하거나 상한을 다시 높이지 않는다. 생성 차량의 준비 시점·공급·수용을 구분해야 한다. 1087은 뒤 두 구간에서 후보 상한18.667대에 도달한다.

도시신호−유지의 전체 Ω TTT 차이는 기존 **{old_delta:+.5f}**, 후보 **{delta:+.5f}**, 실측 **{native_delta:+.5f}대·시간**이다. 후보는 도시명령의 이득을 약{abs(delta-old_delta):.3f}대·시간 더 크게 예측해 손익 오차가 조금 커졌다. 유지 SC101 직진 방출은 기존과 같은56.916대/150초에 머물고 도시조건의 뒤 두 구간 방출만 늘었다. 원천 공급 수정만으로 잘못된 도시 손익이 해소되지 않는다.

초기 상태 차이0, 세 블록 writer와 변경폭, 동일 RM/VSL/NP·NUF 명령, 각 조건4개 상태의 차량 장부, 수용량과 NP/NUF 제약을 확인했다. 원래 수요 forecast도 그대로다. 관련3시험을 통과했다. 두 예측 시간은 {arms['hold']['endpoint_wall_sec']:.2f}/{arms['city']['endpoint_wall_sec']:.2f}초이며 전체 SDMPC 시간은 아니다. 새 AD·최적화·native 런·생산 적용·push는0회다.

## 과거 유입별 경로 증거와 다음 범위

{chr(10).join(route_lines)}

두 원천의 직진 비율 범위 모두 공통 RD1014 비율 약72.3%와 맞지 않는다. RD1014 뒤에1086은4차로,1087은1차로로 진입하는 기하 증거와 일치한다. 특히1087의 미해결22대를 임의로 우회전·직진 처리하지 않는다. 이번 후보에는 경로 비율 수정이 포함되지 않았다.

다음은10528의 신호 앞 우회전 경로에 현재 SC101 신호가 잘못 걸리는지 기존 phase-authority 처리와 대조하고, 원천별 경로 태그를 집계 도착 버퍼에 보존할 범위를 검토하는 것이다. Claude STAGE3/U7 및 기존 SC15 작업은300에서 확인했다. 계수 전수 탐색이나 새 전체 런으로 작은 부호를 강제하지 않는다. 현재 native coupling268 동결 큐는 수정하지 않았다.
"""
    (HERE / "README.md").write_text(text, encoding="utf8")
    next_step = ("Check SC10110528 pre-head peeloff against existing phase authority, then retain "
                 "source-specific aggregate route tags with past-only support; no further source-rate or SC101-cap grid.")
    completion = dict(status=report["status"], goal_complete=False,
        current_goal_turn_classification="progress_past_source_fit_and_two_autonomous_forecasts",
        source_pins={str(p):sha(p) for p in (HERE/"comparison.json", HERE/"README.md", Path(__file__))},
        verified_forecast_source_pins=len(current["source_pins"]), budget=budget, next_step=next_step,
        updated_utc=datetime.now(timezone.utc).isoformat())
    save(HERE / "completion.json", completion)
    relative = (HERE / "README.md").relative_to(ROOT).as_posix()
    for parent in (A, A.parent):
        plan_path = parent / "plan.json"
        plan = read(plan_path)
        plan.update(status="fw5_urban10_runtime_verified_past_sc15_service_city_gain_unqualified",
            current_stage="sc15_source301_complete_not_gain_qualified", latest_stage=relative,
            current_workers=[], goal_complete=False, next_step=next_step,
            updated_utc=completion["updated_utc"], last_goal_turn=completion["current_goal_turn_classification"],
            sc15_source301=dict(status=completion["status"],
                completion=(HERE/"completion.json").relative_to(ROOT).as_posix(),
                completion_sha256=sha(HERE/"completion.json"),budget=budget))
        save(plan_path, plan)
        readme = parent / "README.md"
        old_text = readme.read_text(encoding="utf8")
        header = ("# 최신: SC15 과거 방출 보정(301)\n\n"
            "과거900–2100초의 대기열로 두 방출률을 한 번 추정했다. 동일2400초 상태의 두450초 예측에서 "
            "공급량은 개선했지만 도시−유지 Ω 손익은 기존−2.46408→후보−2.63720, 실제+5.28667대·시간으로 "
            "여전히 반대다. 이득 모델 채택 없이 원천별 회전/신호 적용 문제를 다음 범위로 남긴다. "
            "FW5/도시10, 현재 native 동결 큐 유지. 상세: " + relative + "\n\n---\n\n")
        readme.write_text(header + old_text, encoding="utf8")
    print("COMPLETE301", "gain", old_delta, delta, "native",native_delta)
    for arm,row in arms.items():
        for inp,s in row["source_discharge"].items():
            print(arm, inp, "old/new MAE to lower bound",
                  s["models"]["old"]["mae_to_witnessed_lower_bound"], s["models"]["new"]["mae_to_witnessed_lower_bound"])
    print("verified source pins",len(current["source_pins"]),"goal remains active")


if __name__ == "__main__":
    main()
