# -*- coding: utf-8 -*-
"""망 전체 압력(network pressure) — plant 관측 부담을 회전 구조를 따라 전파한 잠재로 movement 압력을 만든다.
2026-09-06. 어댑터(`vissim_stackelberg_adapter.py`)와 분리된 순수 함수 모듈. 라이브 런은 이 모듈을 아직 임포트하지 않는다.

정의 (단위를 각 줄에 적는다)
  노드 ℓ = 모형 레그(교차로 간 접근 구간, `cfg.network.urban_link_storage_veh` 의 키) + 온램프 저수지 R_x.
  n_ℓ [veh]     = 점유 = 저장용량 − 잔여 (`state.urban_link_storage`).   N_ℓ [veh] = 저장용량.
  dep_ℓ [veh/h] = 정지선 plant 링크(커넥터 지도 from_link)를 떠난 실측 대수 / 창 시간 (차량 레코드 차분).
  gcap_ℓ [veh/h]= 녹색한계 용량 = Σ_m sat_lane·lanes_m·gf_m  (직전 결정 녹색분율).
  μ̂_ℓ [veh/h]  = 유효 서비스율: n_ℓ < n_small 이면 gcap_ℓ (큐가 없어 이탈이 적은 것을 저용량으로 오독하지 않기),
                  아니면 max(dep_ℓ, μ_floor) (큐가 있는데 이탈이 적으면 실제로 막힌 것 — 녹색이든 하류든).
  T_ℓ [h]       = min(n_ℓ/μ̂_ℓ, T_max)  : 적체 해소 시간 = 뒤에 붙는 차 한 대가 겪는(그리고 뒤에 오는 남에게 떠넘기는) 대기.
  B_ℓ [-]       = max(0, (n_ℓ/N_ℓ − θ)/(1−θ)) : 저장 장벽(spillback 위험). κ [h] 로 시간 단위화.
  e_ℓ [h]       = T_ℓ + κ·B_ℓ  : 국소 부담(잠재 씨앗). λT/μ 는 버렸다(λ=0 인 막힌 링크에서 0 이 되고, λ/μ 가 잡음·내생).
  전방 잠재  ψ↓ = e + A↓ψ↓,  A↓_ℓj = P_ℓj·γ_j,  P_ℓj = Σ_{m: ℓ→j} β_m (행합 ≤ 1 로 정규화), γ_j = exp(−τ_j/τ_c)
                  τ_j [s] = 레그 j 자유류 통행시간, τ_c [s] = 할인 시간상수(기본 = 예측지평 450 s).
                  ρ(A↓) ≤ max_j γ_j < 1 → 축약사상, 부동점 유일·수렴 보장(코드에서 확인·기록).
  후방 잠재  ψ↑ = e + A↑ψ↑,  A↑_ℓi = 1[B_ℓ>0]·Q_iℓ·γ_ℓ,  Q_iℓ = ℓ 유입 중 i 에서 오는 비율(유량 가중, 열 정규화 → 행합 ≤ 1)
                  ℓ 이 가득 차야만 상류 i 의 부담이 ℓ 을 비우는 이득으로 전파된다(spillback 사슬).
  movement m (o→d, 회전분율 β_m):
     s_eff_m [veh/s] = sat_lane·lanes_m·min(1, q_m/q_ref)·(1−B_d) : 녹색 1 s 의 한계 방류(큐 없으면 0, 하류 가득이면 0)
     π^NP_m  [veh·h/s] = s_eff_m·(ψ↓_d − ψ↑_o)                        : 망 압력(자기 링크 해소 포함, L 과 겹침)
     π^EXT_m [veh·h/s] = s_eff_m·(ψ↓_d − (κB_o + 1[B_o>0]·Σ_i A↑_oi ψ↑_i)) : 외부효과(자기 큐 해소 T_o 는 L 이 이미 봄 → 제외)
     π^1hop_m[veh·h/s] = s_eff_m·(e_d − e_o)                           : one-hop 대조
  현시 p: π_p = Σ_{m∈p} π_m.  부호: 양수 = 녹색을 늘리면 망 부담 증가 → 줄이는 방향.
  L 과 같은 통화로 맞추는 배율 local_scale = per_lane_model/sat_lane (기본 206.5/1300 = 0.159) 는 별도 보고한다.
"""
from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

# ---------------------------------------------------------------------------
# 모든 파라미터는 여기 한 곳. magic number 금지.
# ---------------------------------------------------------------------------
DEFAULT_PARAMS: Dict[str, float] = {
    "sat_lane_veh_h": 1300.0,     # 실측 포화유율 [veh/h/lane] (SC1002 좌회전 차로 실측 ≈ 1,300)
    "per_lane_model_veh_h": 206.5,  # 국소 모형 용량 척도 [veh/h/lane] → local_scale
    "window_sec": 150.0,          # 상태 기록 간격 [s]
    "windows": 3,                 # 이탈 계수 평균 창 수
    "n_small_veh": 8.0,           # 이 미만이면 큐가 없다고 보고 μ̂ = gcap
    "mu_floor_veh_h": 48.0,       # μ̂ 바닥 [veh/h] (창당 2대)
    "T_max_h": 0.5,               # 해소시간 상한 [h]
    "theta_storage": 0.5,         # 저장 장벽 시작 점유율 [-] (plant 는 모형 N 의 ~0.68 에서 정체: SC101→SC1002 400/588)
    "propagation": "avg",         # "avg": ψ=(1−γ)e+γPψ (볼록결합, 척도 = e) / "sum": ψ=e+γPψ (누적, 하류 과대)
    "kappa_h": 0.25,              # 장벽 시간 환산 [h] (가득 찬 링크 = +0.25 h)
    "tau_c_sec": 450.0,           # 전파 할인 시간상수 [s] = 예측지평
    "v_free_kph": 40.0,           # 레그 자유류 속도 [km/h]
    "k_jam_veh_km_lane": 133.0,   # 저장용량 → 길이 환산용 jam 밀도 [veh/km/lane]
    "default_lanes": 2.0,         # 차로수 미상 레그
    "q_ref_veh": 5.0,             # s_eff 포화 큐 [veh]
    "fixed_point_tol": 1e-7,      # 부동점 허용오차 [h]
    "fixed_point_max_iter": 500,
    "power_iter": 60,             # 스펙트럼 반경 거듭제곱 반복
    "max_abs_price": 1.0,         # 현시 가격 클립 [veh·h/s]
    "min_abs_price": 0.0,         # 불감대 [veh·h/s] (진단은 0)
    "ramp_nodes": 1.0,            # 1 이면 온램프 저수지를 노드로 포함(램프행 movement 에 압력). 0 이면 램프행 movement 제외.
    "ramp_burden": "storage",     # "storage": e_r = κ·B_r (spillback 위험만; 램프 큐 대기 T_r 은 리더의 미터율·λ 몫) / "full": T_r + κB_r
}

MODEL_PHASES = ("p1", "p2", "p3", "p4")
RAMP_NODES = ("R_D_W", "R_D_E", "R_F_W", "R_F_E")
RAMP_OF_EXIT = {("SC1001", "onW"): "R_D_W", ("SC1001", "onE"): "R_D_E", ("SC1004", "onW"): "R_F_W", ("SC1004", "onE"): "R_F_E"}


def _f(x: Any, default: float = 0.0) -> float:
    try:
        v = float(x)
        return v if math.isfinite(v) else default
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# 1. plant 관측: 차량 레코드 차분으로 링크 이탈 계수
# ---------------------------------------------------------------------------
def previous_state_paths(previous_action_path: str, windows: int) -> List[Path]:
    """decisions_x/action_%06d.json → [state_{t}, state_{t-150}, ...] (존재하는 것만)."""
    out: List[Path] = []
    p = Path(str(previous_action_path))
    m = re.match(r"^action_(\d+)\.json$", p.name)
    if not m:
        return out
    t, width = int(m.group(1)), len(m.group(1))
    for k in range(int(windows) + 1):
        tk = t - int(150 * k)
        if tk < 0:
            break
        cand = p.with_name("state_%0*d.json" % (width, tk))
        if cand.is_file():
            out.append(cand)
    return out


def records_by_link(doc: Mapping[str, Any]) -> Dict[int, str]:
    recs = (doc.get("vehicle_records") or {}).get("records") or []
    out: Dict[int, str] = {}
    for r in recs:
        if isinstance(r, Mapping) and r.get("veh_no") is not None and r.get("link_no") is not None:
            out[int(r["veh_no"])] = str(r["link_no"])
    return out


def link_departures(now_doc: Mapping[str, Any], prev_paths: List[Path]) -> Tuple[Dict[str, float], Dict[str, float], int]:
    """(이탈[veh], 유입[veh]) 링크별 합, 사용한 창 수. 창 = 연속 두 스냅샷."""
    dep: Dict[str, float] = defaultdict(float)
    arr: Dict[str, float] = defaultdict(float)
    later = records_by_link(now_doc)
    used = 0
    for path in prev_paths:
        try:
            earlier = records_by_link(json.loads(Path(path).read_text(encoding="utf-8")))
        except Exception:  # noqa: BLE001
            break
        if not earlier or not later:
            break
        for veh, link in earlier.items():
            if later.get(veh) != link:
                dep[link] += 1.0
        for veh, link in later.items():
            if earlier.get(veh) != link:
                arr[link] += 1.0
        used += 1
        later = earlier
    return dict(dep), dict(arr), used


# ---------------------------------------------------------------------------
# 2. 토폴로지: 레그 그래프 + movement → (origin leg, dest leg, lanes, plant 정지선 링크)
# ---------------------------------------------------------------------------
def load_connector_map(root: Path) -> Mapping[str, Any]:
    path = root / "outputs/movement_connector_map_20260824.json"
    return json.loads(path.read_text(encoding="utf-8")).get("approaches") or {}


def build_topology(cfg, connector_map: Mapping[str, Any]) -> Dict[str, Any]:
    """movement spec(origin/destination/beta/phase/kind, intersection/approach/exit) + 커넥터 지도로
    노드(레그)·간선(movement)·plant 정지선 링크·차로수를 만든다. 검사 결과(행합, sink, dead-end, 루프)도 돌려준다."""
    net = cfg.network
    specs = dict(net.urban_movements or {})
    storage = dict(net.urban_link_storage_veh or {})
    nodes: Dict[str, Dict[str, Any]] = {}
    edges: List[Dict[str, Any]] = []
    for m, sp in specs.items():
        kind = str(sp.get("kind", ""))
        o = str(sp.get("origin", "")); d = str(sp.get("destination", "")); beta = max(0.0, _f(sp.get("beta")))
        sig = str(sp.get("intersection") or sp.get("signal") or "")
        approach = str(sp.get("approach", "")); exit_leg = str(sp.get("exit", ""))
        phase = str(sp.get("phase", ""))
        turns = list((connector_map.get("%s|%s" % (sig, approach)) or {}).get("turns") or [])
        if not turns:
            turns = list((connector_map.get("%s|%s_RAMP" % (sig, approach)) or {}).get("turns") or [])
        from_links = sorted({str(t.get("from_link")) for t in turns if t.get("from_link") is not None})
        lanes_o = float(sum(int(t.get("lanes") or 1) for t in turns)) if turns else DEFAULT_PARAMS["default_lanes"]
        dsc = exit_leg.split("_", 1)[1] if "_SC" in exit_leg else ""
        my_turns = [t for t in turns if dsc and str(t.get("dest_signal")) == dsc]
        lanes_m = float(sum(int(t.get("lanes") or 1) for t in my_turns)) if my_turns else 1.0
        ramp = RAMP_OF_EXIT.get((sig, exit_leg))
        dest_node = ramp if ramp is not None else d
        for node, is_origin in ((o, True), (dest_node, False)):
            if not node:
                continue
            nd = nodes.setdefault(node, {"N": _f(storage.get(node), 0.0), "stop_links": set(), "lanes": 0.0, "kind": "leg", "signal": "", "out_movements": [], "in_movements": []})
            if is_origin:
                nd["stop_links"].update(from_links)
                nd["lanes"] = max(nd["lanes"], lanes_o)
                nd["signal"] = sig
        if ramp is not None:
            nodes[ramp]["kind"] = "ramp"
        # 압력 대상: internal + boundary_in(관측되는 경계 접근로, 예 in_SC1001_W = 링크 32) + boundary_out(출구 sink, e=0 → 해소만).
        # off_ramp(OR_x 저장고는 레그 점유가 없음)·on_ramp 는 제외 — 램프 결합은 리더 몫.
        e = {"m": m, "o": o, "d": dest_node, "beta": beta, "phase": phase, "kind": kind, "signal": sig, "lanes_m": lanes_m,
             "internal": kind in ("internal", "boundary_in", "boundary_out") or ramp is not None}
        edges.append(e)
        if o:
            nodes[o]["out_movements"].append(m)
        if dest_node:
            nodes[dest_node]["in_movements"].append(m)
    for nd in nodes.values():
        nd["stop_links"] = sorted(nd["stop_links"])
        if nd["lanes"] <= 0.0:
            nd["lanes"] = DEFAULT_PARAMS["default_lanes"]
    # 검사: 행합(원점별 β 합), sink(나가는 간선 없음), dead-end(N=0), 자기루프
    checks: Dict[str, Any] = {"row_sum_over_1": [], "sinks": [], "no_storage": [], "self_loops": []}
    beta_sum: Dict[str, float] = defaultdict(float)
    for e in edges:
        beta_sum[e["o"]] += e["beta"]
        if e["o"] == e["d"]:
            checks["self_loops"].append(e["m"])
    for node, nd in nodes.items():
        if beta_sum.get(node, 0.0) > 1.0 + 1e-6:
            checks["row_sum_over_1"].append((node, round(beta_sum[node], 3)))
        if not nd["out_movements"]:
            checks["sinks"].append(node)
        if nd["N"] <= 0.0 and nd["kind"] == "leg":
            checks["no_storage"].append(node)
    return {"nodes": nodes, "edges": edges, "beta_sum": dict(beta_sum), "checks": checks}


# ---------------------------------------------------------------------------
# 3. 노드 부담 e, 4. 잠재 ψ↓/ψ↑, 5. movement/현시 압력
# ---------------------------------------------------------------------------
def node_burdens(topo, state, state_json, prev_action_doc, dep, used_windows, params) -> Dict[str, Dict[str, float]]:
    P = params
    window_h = P["window_sec"] / 3600.0 * max(used_windows, 1)
    greens = {str(k): _f(v) for k, v in (prev_action_doc.get("green_times") or {}).items()}
    meters = {str(k): _f(v) for k, v in (prev_action_doc.get("ramp_metering") or {}).items()}
    cycle = _f(getattr(state, "cycle_length", 150.0), 150.0) if hasattr(state, "cycle_length") else 150.0
    remaining = dict(state.urban_link_storage or {})
    ramp_q = dict(state.ramp_queue or {})
    ramp_max = dict(getattr(state, "ramp_queue_max_veh_by_ramp", {}) or {})
    out: Dict[str, Dict[str, float]] = {}
    for node, nd in topo["nodes"].items():
        if nd["kind"] == "ramp":
            if not P.get("ramp_nodes", 0.0):
                out[node] = {"n": 0.0, "N": 0.0, "occ": 0.0, "dep": 0.0, "gcap": 0.0, "mu": P["mu_floor_veh_h"], "mu_from_gcap": 0.0, "T": 0.0, "B": 0.0, "e": 0.0}
                continue
            n = _f(ramp_q.get(node)); N = _f(ramp_max.get(node), 150.0) or 150.0
            dep_rate = _f(meters.get(node), 1800.0)
            gcap = dep_rate
            if str(P.get("ramp_burden", "storage")).lower() == "storage":
                # 램프 저수지 부담 = 저장 장벽만. 램프 큐 대기(T_r)는 미터율(리더 레버)의 결과라 리더의 N_UF*·λ 가 이미 값을 매긴다 —
                # 여기서 또 매기면 같은 결합의 이중 가격이고, 미터 0 이면 T_r→상한이 되어 리더의 폐쇄를 도시 가격이 증폭한다(h2 t=3600 SC1001 p3 69→21).
                occ = n / N if N > 0 else 0.0
                B = min(1.0, max(0.0, (occ - P["theta_storage"]) / (1.0 - P["theta_storage"])))
                out[node] = {"n": n, "N": N, "occ": occ, "dep": dep_rate, "gcap": gcap, "mu": max(dep_rate, P["mu_floor_veh_h"]), "mu_from_gcap": 0.0, "T": 0.0, "B": B, "e": P["kappa_h"] * B}
                continue
        else:
            N = _f(nd["N"]); n = max(0.0, N - _f(remaining.get(node), N)) if N > 0 else 0.0
            dep_rate = sum(_f(dep.get(l)) for l in nd["stop_links"]) / window_h if nd["stop_links"] else 0.0
            gcap = 0.0
            for m in nd["out_movements"]:
                e = next(x for x in topo["edges"] if x["m"] == m)
                ph = e["phase"]; gf = greens.get(ph, 0.0) / max(cycle, 1e-9)
                gcap += P["sat_lane_veh_h"] * e["lanes_m"] * gf
        if n < P["n_small_veh"]:
            mu = max(gcap, P["mu_floor_veh_h"])
            mu_src = 1.0  # gcap
        else:
            mu = max(dep_rate, P["mu_floor_veh_h"])
            mu_src = 0.0  # dep
        T = min(n / mu, P["T_max_h"]) if n > 0 else 0.0
        occ = n / N if N > 0 else 0.0
        B = max(0.0, (occ - P["theta_storage"]) / (1.0 - P["theta_storage"])) if N > 0 else 0.0
        B = min(B, 1.0)
        e_val = T + P["kappa_h"] * B
        out[node] = {"n": n, "N": N, "occ": occ, "dep": dep_rate, "gcap": gcap, "mu": mu, "mu_from_gcap": mu_src, "T": T, "B": B, "e": e_val}
    return out


def _tau_sec(nd: Dict[str, Any], params) -> float:
    N = _f(nd.get("N")); lanes = max(_f(nd.get("lanes"), params["default_lanes"]), 1.0)
    length_km = N / (lanes * params["k_jam_veh_km_lane"]) if N > 0 else 0.2
    return length_km / params["v_free_kph"] * 3600.0


def potentials(topo, burdens, params) -> Dict[str, Any]:
    P = params
    nodes = list(topo["nodes"].keys()); idx = {n: i for i, n in enumerate(nodes)}
    nN = len(nodes)
    e = [burdens[n]["e"] for n in nodes]
    gamma = [math.exp(-_tau_sec(topo["nodes"][n], P) / P["tau_c_sec"]) for n in nodes]
    # A↓: P_oj γ_j (행 = origin). β 행합 > 1 이면 정규화.
    rows_fw: Dict[int, Dict[int, float]] = defaultdict(dict)
    bsum = topo["beta_sum"]
    for ed in topo["edges"]:
        if not ed["o"] or not ed["d"] or ed["o"] not in idx or ed["d"] not in idx:
            continue
        i, j = idx[ed["o"]], idx[ed["d"]]
        norm = max(1.0, _f(bsum.get(ed["o"]), 1.0))
        rows_fw[i][j] = rows_fw[i].get(j, 0.0) + ed["beta"] / norm * gamma[j]
    # A↑: 1[B_ℓ>0]·Q_iℓ·γ_ℓ, Q_iℓ = ℓ 유입 중 i 비율(유량 = β_m·μ̂_i 가중)
    inflow: Dict[int, Dict[int, float]] = defaultdict(dict)
    for ed in topo["edges"]:
        if not ed["o"] or not ed["d"] or ed["o"] not in idx or ed["d"] not in idx:
            continue
        i, j = idx[ed["o"]], idx[ed["d"]]
        w = ed["beta"] * max(burdens[ed["o"]]["mu"], 1.0)
        inflow[j][i] = inflow[j].get(i, 0.0) + w
    rows_bw: Dict[int, Dict[int, float]] = defaultdict(dict)
    for j, srcs in inflow.items():
        if burdens[nodes[j]]["B"] <= 0.0:
            continue
        tot = sum(srcs.values()) or 1.0
        for i, w in srcs.items():
            rows_bw[j][i] = w / tot * gamma[j]

    def spectral_radius(rows: Dict[int, Dict[int, float]]) -> float:
        v = [1.0] * nN; lam = 0.0
        for _ in range(int(P["power_iter"])):
            w = [sum(a * v[k] for k, a in rows.get(i, {}).items()) for i in range(nN)]
            norm = max(abs(x) for x in w) if w else 0.0
            if norm <= 0.0:
                return 0.0
            lam = norm; v = [x / norm for x in w]
        return lam

    def solve(rows: Dict[int, Dict[int, float]]) -> Tuple[List[float], int, float]:
        psi = list(e)
        it = 0; resid = float("inf")
        for it in range(1, int(P["fixed_point_max_iter"]) + 1):
            new = [e[i] + sum(a * psi[k] for k, a in rows.get(i, {}).items()) for i in range(nN)]
            resid = max(abs(new[i] - psi[i]) for i in range(nN)) if nN else 0.0
            psi = new
            if resid < P["fixed_point_tol"]:
                break
        return psi, it, resid

    rho_fw = spectral_radius(rows_fw); rho_bw = spectral_radius(rows_bw)
    if rho_fw >= 1.0 or rho_bw >= 1.0:
        raise ValueError("network_pressure: spectral radius >= 1 (fw %.3f, bw %.3f) — 부동점 수렴 보장 없음" % (rho_fw, rho_bw))
    # "sum": ψ = e + Aψ (누적 비용-to-go; 하류를 홉 수만큼 과대).  "avg": ψ = (1 − γ·r)e + Aψ 로 가중치 합 = 1 인 볼록결합
    #   (r = 행합 P; sink 는 r=0 → ψ=e). 경로를 따라 마주칠 부담의 할인 평균이라 척도가 e 와 같고, ρ ≤ max γ < 1.
    def solve_avg(rows: Dict[int, Dict[int, float]], gam_row: List[float]) -> Tuple[List[float], int, float]:
        r_sum = [sum(rows.get(i, {}).values()) for i in range(nN)]  # = γ·r (이미 γ 포함)
        own = [max(0.0, 1.0 - r_sum[i]) for i in range(nN)]
        psi = list(e); it = 0; resid = float("inf")
        for it in range(1, int(P["fixed_point_max_iter"]) + 1):
            new = [own[i] * e[i] + sum(a * psi[k] for k, a in rows.get(i, {}).items()) for i in range(nN)]
            resid = max(abs(new[i] - psi[i]) for i in range(nN)) if nN else 0.0
            psi = new
            if resid < P["fixed_point_tol"]:
                break
        return psi, it, resid
    psi_fw_sum, it_fw_s, r_fw_s = solve(rows_fw)
    psi_bw_sum, it_bw_s, r_bw_s = solve(rows_bw)
    psi_fw_avg, it_fw_a, r_fw_a = solve_avg(rows_fw, gamma)
    psi_bw_avg, it_bw_a, r_bw_a = solve_avg(rows_bw, gamma)
    for name, arr in (("psi_fw_sum", psi_fw_sum), ("psi_bw_sum", psi_bw_sum), ("psi_fw_avg", psi_fw_avg), ("psi_bw_avg", psi_bw_avg)):
        if any(not math.isfinite(x) for x in arr):
            raise ValueError("network_pressure: %s 에 NaN/inf" % name)
    use_avg = str(P.get("propagation", "avg")).lower() != "sum"
    psi_fw = psi_fw_avg if use_avg else psi_fw_sum
    psi_bw = psi_bw_avg if use_avg else psi_bw_sum
    it_fw, r_fw, it_bw, r_bw = (it_fw_a, r_fw_a, it_bw_a, r_bw_a) if use_avg else (it_fw_s, r_fw_s, it_bw_s, r_bw_s)
    up_relief = {}  # 외부효과용: κB_o + 1[B_o>0]·Σ_i A↑_oi ψ↑_i (자기 T_o 제외)
    for j in range(nN):
        s = sum(a * psi_bw[k] for k, a in rows_bw.get(j, {}).items())
        up_relief[nodes[j]] = P["kappa_h"] * burdens[nodes[j]]["B"] + s
    return {
        "nodes": nodes, "gamma": dict(zip(nodes, gamma)), "propagation": "avg" if use_avg else "sum",
        "psi_fw": dict(zip(nodes, psi_fw)), "psi_bw": dict(zip(nodes, psi_bw)), "up_relief": up_relief,
        "psi_fw_sum": dict(zip(nodes, psi_fw_sum)), "psi_fw_avg": dict(zip(nodes, psi_fw_avg)),
        "rho_fw": rho_fw, "rho_bw": rho_bw, "iters_fw": it_fw, "iters_bw": it_bw, "resid_fw": r_fw, "resid_bw": r_bw,
        "max_gamma": max(gamma) if gamma else 0.0, "n_edges_fw": sum(len(r) for r in rows_fw.values()), "n_edges_bw": sum(len(r) for r in rows_bw.values()),
    }


def movement_pressures(topo, burdens, pot, state, params) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Dict[str, float]]]]:
    P = params
    q = dict(state.urban_movement_queue or {})
    rows: List[Dict[str, Any]] = []
    KEYS = ("NP", "EXT", "ONEHOP", "NP_SUM")
    phase_sum: Dict[str, Dict[str, Dict[str, float]]] = defaultdict(lambda: defaultdict(lambda: {k: 0.0 for k in KEYS}))
    for ed in topo["edges"]:
        o, d, m = ed["o"], ed["d"], ed["m"]
        if not ed["internal"] or o not in burdens or d not in burdens:
            continue
        if topo["nodes"][d]["kind"] == "ramp" and not P.get("ramp_nodes", 0.0):
            continue  # 램프행 movement 는 도시 압력에서 제외 (보상도 벌칙도 없음)
        bo, bd = burdens[o], burdens[d]
        # 큐: 모형 정지선 큐가 없는 movement(램프 게이트 등)는 접근 점유의 회전분율 몫으로 본다 [veh]
        qm = max(max(0.0, _f(q.get(m))), ed["beta"] * bo["n"])
        s_eff = P["sat_lane_veh_h"] * ed["lanes_m"] * min(1.0, qm / P["q_ref_veh"]) * (1.0 - bd["B"]) / 3600.0  # [veh/s]
        psi_d = pot["psi_fw"][d]; psi_o_bw = pot["psi_bw"][o]
        np_ = s_eff * (psi_d - psi_o_bw)
        np_sum = s_eff * (pot["psi_fw_sum"][d] - bo["e"])
        ext = s_eff * (psi_d - pot["up_relief"][o])
        one = s_eff * (bd["e"] - bo["e"])
        pid = ed["phase"].split("_", 1)[1] if "_" in ed["phase"] else ""
        rows.append({"m": m, "signal": ed["signal"], "phase": pid, "o": o, "d": d, "beta": ed["beta"], "q_m": qm, "s_eff": s_eff,
                     "e_o": bo["e"], "e_d": bd["e"], "psi_fw_d": psi_d, "psi_bw_o": psi_o_bw, "up_relief_o": pot["up_relief"][o],
                     "pi_NP": np_, "pi_EXT": ext, "pi_1hop": one, "pi_NP_sum": np_sum})
        if pid in MODEL_PHASES:
            ps = phase_sum[ed["signal"]][pid]
            ps["NP"] += np_; ps["EXT"] += ext; ps["ONEHOP"] += one; ps["NP_SUM"] += np_sum
    # 클립·불감대
    for sig in phase_sum:
        for pid in phase_sum[sig]:
            for k in KEYS:
                v = max(-P["max_abs_price"], min(P["max_abs_price"], phase_sum[sig][pid][k]))
                phase_sum[sig][pid][k] = v if abs(v) >= P["min_abs_price"] else 0.0
    return rows, {s: {p: dict(v) for p, v in d.items()} for s, d in phase_sum.items()}


def compute(cfg, state, state_json, previous_action_path: str, root: Path, params: Optional[Mapping[str, float]] = None) -> Dict[str, Any]:
    """한 결정 시점의 전체 계산. 반환: burdens, potentials, movement rows, phase prices, 검사·진단."""
    P = dict(DEFAULT_PARAMS); P.update(params or {})
    cm = load_connector_map(root)
    topo = build_topology(cfg, cm)
    prev_paths = previous_state_paths(previous_action_path, int(P["windows"]))
    dep, arr, used = link_departures(state_json, prev_paths)
    try:
        prev_doc = json.loads(Path(previous_action_path).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        prev_doc = {}
    burdens = node_burdens(topo, state, state_json, prev_doc, dep, used, P)
    pot = potentials(topo, burdens, P)
    rows, phase = movement_pressures(topo, burdens, pot, state, P)
    return {"params": P, "topology": topo, "windows_used": used, "burdens": burdens, "potentials": pot, "movements": rows, "phase_prices": phase,
            "local_scale": P["per_lane_model_veh_h"] / P["sat_lane_veh_h"]}
