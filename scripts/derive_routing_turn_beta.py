"""movement 회전분율 `beta` 를 VISSIM **정적 경로결정**에서 유도한다 (v2).

왜 v1(.knr 기반)을 버리는가
---------------------------
`scripts/derive_measured_turn_beta.py` 는 노드평가 `.knr` 의 통과 대수로 beta 를
만들었다. 그건 **내생적**이다. 모델의 beta 는 링크 끝에 도착한 차량을 movement
큐로 나누는 **수요 배분**인데(`urban_queue_model.approach_routing`, 그 값이
`urban_movement_queue[m] += beta * arrived` 로 쓰인다), `.knr` 은 교차로를
**통과 완료**한 차량, 즉 그 방향에 준 녹색의 **결과**다. 컨트롤러가 최적화하는
변수로부터 그 입력을 역산하는 자기실현 루프가 된다.

실제로 v1 산출물이 그 병을 앓았다:
  - 미매칭 2,758/44,746 = **6.16%** (SC109 N_SC16 은 208대 전부 미매칭인데
    경계 movement 에 beta 1.0 을 박았다)
  - 매칭 못 한 대수를 "OUT" 한 덩어리로 모아 **균등 분할** — 없애려던 1/n
    기본값이 되살아난다(SC11_N_SC5 의 to_W·to_E 가 똑같이 0.3336)
  - 244개 중 **85개가 정확히 0.0**, 그 중 internal 25개. 우회전 17개와
    **직진 2개**(SC107_E_SC108_to_W_SC1004, SC7_S_SC108_to_N_SC11)가 포함된다.
    beta=0 이면 그 movement 큐에 도착이 영영 안 꽂혀 큐가 항상 0 이고,
    리더는 빈 현시를 굶기는 비용이 0 이라 green_min 으로 민다 —
    동서축 관측 실명과 **같은 실패 모드**다.

무엇을 대신 쓰는가
------------------
`.inpx` 의 `vehicleRoutingDecisionStatic` / `vehicleRouteStatic`. 이건 VISSIM 이
차량을 실제로 배분할 때 쓰는 **입력**이라 신호 타이밍과 무관하다(외생적).
정의가 모델의 beta 와 같은 양이다.

    <vehicleRoutingDecisionStatic link="359" name="구룡초교_EB" no="11">
      <vehicleRouteStatic name="좌" destLink="1220008501" relFlow="2 0:122">
      <vehicleRouteStatic name="직" destLink="1220008301" relFlow="2 0:284">
      <vehicleRouteStatic name="우" destLink="1220006803" relFlow="2 0:117">

경로가 **사슬**이다 — 위 "직" 의 destLink 1220008301 이 곧 SC11 접근로
결정(no=21)의 link 다. 그래서 v1 을 무너뜨린 leg 이름 접기가 통째로 필요 없다:

    결정 link  --권역-->  (출발 신호, 출발 접근로)
    route destLink --권역-->  (도착 신호, 도착 leg)   또는 없으면 망 밖 유출

모델은 같은 물리적 회전을 internal/boundary_out **쌍**으로 쪼개 둔다
((signal, approach, turn) 조합 396개 중 78개가 중복, 전부 이 쌍이다).
destLink 권역 판정이 그 쌍을 갈라 준다 — 하류 신호가 잡히면 internal,
안 잡히면 boundary_out.

안전장치
--------
1. **증거 없는 movement 를 0 으로 만들지 않는다.** 조사에 없는 turn 범주
   (주로 u_turn)는 기존 몫을 그대로 두고, 실측 turn 들이 나머지를 채운다.
2. **현시 전체가 0 이 되는 일을 막는다.** 한 현시의 movement 가 전부 beta 0 이면
   그 현시는 영구히 큐 0 이 되어 굶는다. 그런 현시가 생기면 실패로 끝낸다.
3. 접근로 합은 1.0 을 유지한다(단, 이건 정규화의 항등식이라 **검증 근거가
   아니다** — 중복 계상도 미매칭 쓰레기도 합 1.0 을 만족한다. 진짜 검증은
   미매칭 대수와 0 이 된 movement 목록이다).
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]

if hasattr(sys.stdout, "reconfigure"):  # 한글 경로/출력 — cp949 콘솔에서 깨진다
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# VISSIM 경로 이름 -> 모델 turn. 이 망의 정적 경로결정은 좌/직/우 세 글자만 쓴다.
TURN_OF_NAME = {"좌": "left", "직": "through", "우": "right", "유턴": "u_turn"}


def _rel_flow(route: ET.Element) -> float:
    """relFlow="2 0:122" -> 122.0.

    **비어 있으면 1 이다. 0 이 아니다** (CLAUDE.md 의 되돌리면 안 되는 규칙 4).
    0 으로 읽으면 지하차도 경로가 통째로 사라진다. 이 망의 정적 경로결정 130개 중
    52개는 전 경로가 비어 있고(= 균등 분배가 실제 설정값이다) **18개는 섞여 있다** —
    섞인 쪽에서 빈 경로를 0 으로 읽으면 그 경로만 조용히 없어진다.
    """
    raw = (route.get("relFlow") or "").strip()
    if not raw:
        return 1.0
    total = 0.0
    for token in raw.split():
        if ":" in token:
            try:
                total += float(token.rsplit(":", 1)[1])
            except ValueError:
                continue
    return total


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--network", default="network/real_world_gaepo_modi/modi_eval_userfix_20260814e.inpx")
    ap.add_argument("--territory", default="outputs/urban_player_territory_v1_20260819.json")
    ap.add_argument("--movements-config",
                    default="evaluation/configs/real_world_modi_pstack_distributed_core17legs4b_20260819.json")
    ap.add_argument("--out", default="outputs/movement_beta_routing_20260824.json")
    args = ap.parse_args()

    terr = json.loads((ROOT / args.territory).read_text(encoding="utf-8"))["territory"]["urban"]
    owner: dict[str, tuple[str, str]] = {}
    for sig, legs in terr.items():
        for leg, ids in legs.items():
            for link_id in ids:
                owner.setdefault(str(link_id), (sig, leg))

    cfg = json.loads((ROOT / args.movements_config).read_text(encoding="utf-8"))
    um = cfg["config_overrides"]["network"]["urban_movements"]

    # 접근로 -> movement 들. 그리고 movement -> (turn, 하류 신호 또는 None)
    by_app: dict[tuple[str, str], list[str]] = collections.defaultdict(list)
    for key, spec in um.items():
        sig, app = str(spec.get("signal", "")), str(spec.get("approach", ""))
        if sig and app:
            by_app[(sig, app)].append(key)

    def downstream_of(movement: str) -> str | None:
        """movement 가 향하는 하류 신호. 경계 유출이면 None."""
        spec = um[movement]
        if str(spec.get("kind", "")) == "boundary_out":
            return None
        dest = str(spec.get("destination", ""))
        # "SC1_to_SC105" -> "SC105"
        return dest.split("_to_", 1)[1] if "_to_" in dest else None

    root = ET.parse(ROOT / args.network).getroot()

    out_beta: dict[str, float] = {}
    records: list[dict] = []
    skipped: collections.Counter = collections.Counter()
    skipped_stage: dict[tuple[str, str], float] = {}
    unnamed_routes = 0

    # 접근로별 하류 신호 집합. 결정을 어느 접근로에 붙일지 이걸로 역추론한다.
    downstream_set = {a: {d for d in (downstream_of(m) for m in ms) if d}
                      for a, ms in by_app.items()}

    # ---- 1차: 결정을 접근로에 붙이고 증거를 **누적**한다 ----
    #
    # 결정 링크의 권역을 그대로 접근로로 쓰면 안 된다. 정적 경로결정은 교차로가 아니라
    # **상류 대기 구간**에 놓여 있어서, 결정 링크를 소유한 leg 와 회전이 실제로 일어나는
    # 교차로가 다르다. 실측: 결정 24 '개포고교_NB' 는 링크 권역이 (SC7, S_SC108) 인데
    # 목적지 집합 {SC1, SC12, SC5} 는 SC11 의 이웃이다 — 실제 접근로는 (SC11, S_SC7) 이고
    # 개포고교는 결정 21~23 이 말해 주듯 SC11 이다. 권역을 믿으면 13개가 틀린다.
    #
    # 그래서 **목적지 집합으로 역추론**한다. 목적지가 둘 이상이면 그 집합을 포함하는
    # 접근로가 대개 유일하고, 그 판정은 권역과 독립이라 서로 검산이 된다.
    # 목적지가 하나뿐이면 정보가 부족하므로 권역 판정으로 되돌린다.
    #
    # 그리고 한 접근로에 결정이 여럿 붙는다(15개 접근로). 상류 대기 결정과 교차로 결정이
    # 같은 leg 를 가리키기 때문이다. **덮어쓰지 말고 더해야** 한다.
    evidence: dict[tuple[str, str], dict[tuple[str | None, str | None], float]] =         collections.defaultdict(lambda: collections.defaultdict(float))
    sources: dict[tuple[str, str], list[dict]] = collections.defaultdict(list)

    for dec in root.iter("vehicleRoutingDecisionStatic"):
        routes = [(rt, _rel_flow(rt)) for rt in dec.iter("vehicleRouteStatic")]
        routes = [(rt, v) for rt, v in routes if v > 0.0]
        if not routes:
            skipped["경로 없음"] += 1
            continue

        dests = {owner[str(rt.get("destLink"))][0] for rt, _ in routes
                 if str(rt.get("destLink")) in owner}
        by_link = owner.get(str(dec.get("link")))

        app = None
        how = ""
        if len(dests) >= 2:
            cands = [a for a, ss in downstream_set.items() if ss and dests <= ss]
            if cands:
                tightest = min(len(downstream_set[a]) for a in cands)
                tight = [a for a in cands if len(downstream_set[a]) == tightest]
                # 권역과 일치하는 후보가 있으면 그걸 쓴다(독립 두 신호의 합치).
                agree = [a for a in tight if a == by_link]
                if agree:
                    app, how = agree[0], "목적지집합+권역 합치"
                elif len(tight) == 1:
                    app, how = tight[0], "목적지집합 역추론"
        if app is None and by_link is not None and by_link in by_app:
            # 권역으로 되돌린다. 단 그 접근로가 목적지를 설명할 수 있어야 한다.
            if not dests or dests <= downstream_set.get(by_link, set()):
                app, how = by_link, "권역"
        if app is None:
            skipped["접근로 특정 실패"] += 1
            continue

        # 목적지가 출발 접근로 자신이면 교차로 회전이 아니라 **구간 연장**이다 — 버린다.
        # (결정 112 '우리은행포이_WB' 의 직진 479대가 그렇다. 이걸 세면 그 접근로가
        #  통째로 미매칭이 된다.)
        kept = 0.0
        for rt, vol in routes:
            dest_owner = owner.get(str(rt.get("destLink")))
            if dest_owner is not None and dest_owner == app:
                skipped_stage[app] = skipped_stage.get(app, 0.0) + vol
                continue
            turn = TURN_OF_NAME.get((rt.get("name") or "").strip())
            if turn is None:
                unnamed_routes += 1
            evidence[app][(dest_owner[0] if dest_owner else None, turn)] += vol
            kept += vol
        if kept > 0.0:
            sources[app].append({"no": dec.get("no"), "name": dec.get("name"),
                                 "link": dec.get("link"), "veh": round(kept, 1), "how": how})

    # ---- 2차: 증거를 beta 로 바꾼다 ----
    for app, ev in evidence.items():
        movements = by_app[app]
        # 증거가 닿는 movement 를 먼저 정한다. 안 닿는 것은 기존 몫을 지킨다 —
        # 증거 없이 0 으로 만들면 그 movement 큐에 도착이 영영 안 꽂히고
        # (urban_queue_model:1018 `queue[m] += beta * arrived`) 리더가 그 현시를 굶는다.
        reachable: set[str] = set()
        for dest_sig, turn in ev:
            for m in movements:
                if dest_sig is not None:
                    if downstream_of(m) == dest_sig:
                        reachable.add(m)
                elif downstream_of(m) is None and (turn is None
                                                   or str(um[m].get("turn", "")) == turn):
                    reachable.add(m)
        held = {m: float(um[m].get("beta", 0.0)) for m in movements if m not in reachable}
        held_mass = min(0.99, sum(held.values()))
        share_mass = 1.0 - held_mass

        total_vol = sum(ev.values())
        assigned: dict[str, float] = dict(held)
        unmatched_vol = 0.0
        for (dest_sig, turn), vol in ev.items():
            if dest_sig is not None:
                # 하류 신호가 실재하면 movement 가 유일하다 —
                # (signal, approach, 하류신호) 조합 413개 중 중복 43개가 전부
                # 하류=None 인 경계 유출 쌍이다.
                hits = [m for m in movements if downstream_of(m) == dest_sig]
            else:
                outs = [m for m in movements if downstream_of(m) is None]
                hits = [m for m in outs if str(um[m].get("turn", "")) == turn] if turn else outs
            if not hits:
                unmatched_vol += vol
                continue
            per = vol / total_vol * share_mass / len(hits)
            for m in hits:
                assigned[m] = assigned.get(m, 0.0) + per

        for m in movements:
            assigned.setdefault(m, 0.0)
        total = sum(assigned.values())
        if total <= 0.0:
            skipped["배분 총합 0"] += 1
            continue
        for m, v in assigned.items():
            out_beta[m] = round(v / total, 4)

        records.append({
            "signal": app[0], "approach": app[1],
            "decisions": sources[app],
            "veh": round(total_vol, 1), "unmatched": round(unmatched_vol, 1),
            "staging_dropped": round(skipped_stage.get(app, 0.0), 1),
            "held_mass": round(held_mass, 4),
            "beta": {m: out_beta[m] for m in movements},
            "beta_prev": {m: float(um[m].get("beta", 0.0)) for m in movements},
        })

    # --- 안전장치 2: 현시 전체가 0 이 되면 그 현시는 영구히 굶는다 ---
    by_phase: dict[str, list[str]] = collections.defaultdict(list)
    for m, spec in um.items():
        phase = str(spec.get("phase", ""))
        if phase:
            by_phase[phase].append(m)
    starved = []
    for phase, ms in by_phase.items():
        effective = [out_beta.get(m, float(um[m].get("beta", 0.0))) for m in ms]
        if ms and max(effective) <= 0.0:
            starved.append(phase)

    doc = {
        "schema": "movement_beta_routing/core17legs4b",
        "generated": "2026-08-24",
        "source": str(args.network),
        "definition": ("VISSIM 정적 경로결정(vehicleRoutingDecisionStatic)의 relFlow. "
                       "결정 link 를 권역으로 접어 출발 접근로를, route destLink 를 권역으로 "
                       "접어 하류 신호를 얻는다. 신호 타이밍과 무관한 외생 입력이다."),
        "supersedes": "outputs/movement_beta_measured_20260824.json",
        "beta": out_beta,
        "approaches": records,
    }
    (ROOT / args.out).write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")

    # --- 보고 ---
    tot_veh = sum(r["veh"] for r in records)
    tot_un = sum(r["unmatched"] for r in records)
    print(f"접근로 {len(records)}개 · movement {len(out_beta)}개 · 경로 대수 {tot_veh:,.0f}")
    print(f"미매칭 {tot_un:,.0f} = {100 * tot_un / tot_veh if tot_veh else 0:.2f}%"
          f" · 이름 없는 경로 {unnamed_routes}")
    print(f"건너뜀 {dict(skipped)}")

    zeros = [m for m, v in out_beta.items() if v == 0.0]
    zk = collections.Counter((str(um[m].get("kind")), str(um[m].get("turn"))) for m in zeros)
    print(f"\nbeta 0 이 된 movement {len(zeros)}/{len(out_beta)}")
    for k, v in sorted(zk.items(), key=lambda x: -x[1]):
        print(f"    {k[0]:14s} {k[1]:9s} {v:3d}")
    inner = [m for m in zeros if str(um[m].get("kind")) == "internal"]
    if inner:
        print(f"  internal 0 ({len(inner)}개) — 실제로 통행이 없는지 확인 필요:")
        for m in inner:
            print(f"    {m}")

    diffs = sorted(abs(out_beta[m] - float(um[m].get("beta", 0.0))) for m in out_beta)
    if diffs:
        print(f"\n기존 대비 차이: 중앙 {diffs[len(diffs) // 2]:.3f}"
              f" · 90% {diffs[int(len(diffs) * 0.9)]:.3f} · 최대 {diffs[-1]:.3f}")

    if starved:
        print(f"\n[실패] 전 movement 가 beta 0 인 현시 {len(starved)}개: {starved}")
        return 1
    print("\n[검사] 전 movement 가 0 인 현시 없음 — 굶는 현시 없음")
    print(f"저장: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
