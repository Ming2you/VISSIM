# 4-zone freeway follower 검증: 기본(미지정) 회귀 + zone 빌더 가드 + 세그먼트별 VSL 실집행 + pstack-flagship 스모크.
"""실행 예:
    "C:/Users/alsrj/anaconda3/python.exe" scripts/test_freeway_zone_followers.py

NumSim 저장소는 NUMSIM_REPO_ROOT env 또는 어댑터 DEFAULT_REPO_ROOT(NumSim-mine)를 쓴다.
어댑터 서브프로세스는 **프로덕션 매핑/캘리브레이션**(real_world_modi_control)으로 돌린다 —
어댑터 기본값(8seg 진단용)으로 돌리면 실제 실행 경로와 다른 것을 검증하게 된다.
모든 테스트 PASS 시 종료코드 0, 실패 시 1.
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Any, Mapping

WORKSPACE = Path(__file__).resolve().parents[1]
ADAPTER_DIR = WORKSPACE / "evaluation" / "controllers"
ADAPTER_PY = ADAPTER_DIR / "vissim_stackelberg_adapter.py"
CONFIG_DIR = WORKSPACE / "evaluation" / "configs"
FLAGSHIP_TUNING = CONFIG_DIR / "real_world_modi_pstack_flagship_20260731.json"
SEGVSL_TUNING = CONFIG_DIR / "real_world_modi_pstack_flagship_segvsl_20260801.json"
ZONE4_TUNING = CONFIG_DIR / "real_world_modi_pstack_zone4_20260801.json"
# 프로덕션 실행 경로가 쓰는 매핑/캘리브레이션(어댑터 기본값이 아니다).
PROD_MAPPING = WORKSPACE / "evaluation" / "real_world_modi_control" / "control_mapping.json"
PROD_CALIBRATION = (
    WORKSPACE / "evaluation" / "calibration" / "real_world_modi_control_v0_20260719.json"
)

if str(ADAPTER_DIR) not in sys.path:
    sys.path.insert(0, str(ADAPTER_DIR))

import vissim_stackelberg_adapter as ada  # noqa: E402

REPO_ROOT = ada.DEFAULT_REPO_ROOT
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.controllers import local_freeway_plant as lfp  # noqa: E402
from src.controllers.segment_local_plant import (  # noqa: E402
    build_segment_agent_models,
)
from src.controllers.wu_faithful_follower import WuFaithfulFollower  # noqa: E402
from src.models.demand import DemandStep  # noqa: E402
from src.models.metanet import desired_speed_kmh  # noqa: E402
from src.models.state import ControlAction, TrafficState  # noqa: E402

# plan.md 4-zone 표(2026-08-01 좌표 검증) — zone id → (소유 세그먼트, 소유 ramp).
# 2026-08-01 본선 체인 격자 반영: FW_E가 link 74+10699+2+10702+24(10773.1 m), FW_W가
# link 26(10777.7 m)로 정정되면서 램프 합류 세그먼트가 R_F_E@3 / R_D_E@5 / R_D_W@2 /
# R_F_W@4로 옮겨갔고, 분할이 4:4로 균형을 되찾았다(구 격자는 6:2 / 5:3).
EXPECTED_ZONES: dict[str, list[tuple[str, list[int], list[str]]]] = {
    "FW_E": [
        ("fw_yangjae_E", [0, 1, 2, 3], ["R_F_E"]),
        ("fw_seocho_E", [4, 5, 6, 7], ["R_D_E"]),
    ],
    "FW_W": [
        ("fw_seocho_W", [0, 1, 2, 3], ["R_D_W"]),
        ("fw_yangjae_W", [4, 5, 6, 7], ["R_F_W"]),
    ],
}


class _FakeLeader:
    """예산 사영 스코프 검증용 가짜 leader(N_UF_star>0)."""

    def __init__(self, n_uf_star: float) -> None:
        self.N_UF_star = float(n_uf_star)


def _check(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def _build_cfg(tuning_path: Path):
    """어댑터 main()과 같은 방식으로 cfg를 만든다(프로덕션 캘리브레이션 + tuning override)."""
    tuning = ada.load_optional_json(str(tuning_path))
    calibration = ada.load_optional_json(str(PROD_CALIBRATION))
    calibration_override = tuning.get("calibration_override", {})
    if isinstance(calibration_override, Mapping):
        calibration = ada.deep_update(dict(calibration), calibration_override)
    cfg = ada.build_config(
        REPO_ROOT, 60.0, 180.0, "fast-smoke", calibration, tuning,
        local_observation=False, flagship=True,
    )
    return cfg, tuning


# ---------------------------------------------------------------------------
# 솔버 직접 호출용 합성 시나리오
# ---------------------------------------------------------------------------


def _make_solver_inputs(cfg):
    """(state, demand, snapshot, previous, coupling) — 혼잡 경사 + 램프 큐가 있는 합성 입력."""
    n_seg = int(cfg.network.freeway_segments_per_link)
    state = TrafficState.initial(cfg)
    for li, link in enumerate(cfg.network.freeway_links):
        state.freeway_density[link] = [18.0 + 5.0 * i + 2.0 * li for i in range(n_seg)]
        state.freeway_speed[link] = [max(15.0, 100.0 - 7.0 * i) for i in range(n_seg)]
        state.freeway_effective_lanes[link] = [float(cfg.network.freeway_lanes)] * n_seg
        state.mainline_origin_queue[link] = 6.0
    for r in cfg.network.ramps:
        state.ramp_queue[r] = 15.0
    demand = DemandStep(
        freeway_mainline={lk: 2000.0 for lk in cfg.network.freeway_links},
        urban_boundary={},
        ramp_arrival={r: 500.0 for r in cfg.network.ramps},
    )
    snapshot = ControlAction.uncontrolled(cfg)
    previous = ControlAction.uncontrolled(cfg)
    for r in cfg.network.ramps:
        previous.ramp_metering[r] = 900.0
    for link in cfg.network.freeway_links:
        previous.vsl[link] = 100.0
        for i in range(n_seg):
            previous.vsl[f"{link}__seg{i}"] = 100.0
    coupling = {f"u_on_{r}": 600.0 for r in cfg.network.ramps}
    return state, demand, snapshot, previous, coupling


def _make_follower(cfg, *, per_segment_price: bool = False) -> WuFaithfulFollower:
    follower = WuFaithfulFollower(cfg)
    follower.segment_agents = True
    follower.metering_enabled = True
    follower._seg13_diag = {}
    follower._seg_traj = {}
    if per_segment_price:
        # 세그먼트마다 부호가 반대인 g_vsl — 균일 VSL로는 재현 불가능한 분기를 강제한다.
        n_seg = int(cfg.network.freeway_segments_per_link)
        follower.vsl_marginal_price = {}
        follower.vsl_marginal_price_ref = {}
        for link in cfg.network.freeway_links:
            for i in range(n_seg):
                key = f"{link}__seg{i}"
                follower.vsl_marginal_price[key] = 2.0 if i % 2 == 0 else -2.0
                follower.vsl_marginal_price_ref[key] = 100.0
        follower.vsl_marginal_price_weight = 1.0
    return follower


def _link_ramps(cfg, link: str) -> set[str]:
    return {r for r in cfg.network.ramps if cfg.network.ramp_to_freeway.get(r) == link}


# ---------------------------------------------------------------------------
# 테스트
# ---------------------------------------------------------------------------


def test_default_unchanged() -> list[str]:
    """(1) groups 미지정: 세그먼트당 1 에이전트 — 개수·seg·소유 ramp·off-ramp가 기존 계약 그대로."""
    failures: list[str] = []
    cfg, _ = _build_cfg(FLAGSHIP_TUNING)
    _check(getattr(cfg.mpc, "freeway_agent_groups", "missing") is None,
           f"flagship cfg에 freeway_agent_groups가 남아 있다: "
           f"{getattr(cfg.mpc, 'freeway_agent_groups', 'missing')!r}", failures)
    n_seg = int(cfg.network.freeway_segments_per_link)
    for link in cfg.network.freeway_links:
        agents = build_segment_agent_models(cfg, link)
        _check(len(agents) == n_seg, f"{link} 에이전트 수={len(agents)} (기대 {n_seg})", failures)
        for i, agent in enumerate(agents):
            _check(agent.segs == [i], f"{link} agent{i}.segs={agent.segs}", failures)
            _check(agent.seg == i, f"{link} agent{i}.seg={agent.seg}", failures)
            _check(agent.zone_id == "", f"{link} agent{i}.zone_id={agent.zone_id!r}", failures)
            _check(agent.zone_mode is False,
                   f"{link} agent{i}.zone_mode={agent.zone_mode}", failures)
            _check(agent.owns_origin_queue == (i == 0),
                   f"{link} agent{i}.owns_origin_queue={agent.owns_origin_queue}", failures)
            expect_ramps = [
                r for r in agent.link_model.owned_ramps
                if agent.link_model.ramp_merge_idx[r] == i
            ]
            _check(agent.owned_ramps == expect_ramps,
                   f"{link} agent{i}.owned_ramps={agent.owned_ramps} (기대 {expect_ramps})", failures)
            expect_off = list(agent.link_model.offramps_by_segment.get(i, []))
            _check(agent.boundary_offramps == expect_off,
                   f"{link} agent{i}.boundary_offramps={agent.boundary_offramps}", failures)
    return failures


def test_zone4_mapping() -> list[str]:
    """(2) zone4 tuning: 링크당 에이전트 2개, 소유 세그먼트/램프가 설계 문서 표와 일치."""
    failures: list[str] = []
    cfg, _ = _build_cfg(ZONE4_TUNING)
    groups = getattr(cfg.mpc, "freeway_agent_groups", None)
    _check(bool(groups), f"zone4 cfg에 freeway_agent_groups가 없다: {groups!r}", failures)
    if not groups:
        return failures
    total_agents = 0
    for link, expected in EXPECTED_ZONES.items():
        agents = build_segment_agent_models(cfg, link)
        total_agents += len(agents)
        _check(len(agents) == len(expected),
               f"{link} zone 수={len(agents)} (기대 {len(expected)})", failures)
        if len(agents) != len(expected):
            continue
        for agent, (zid, segs, ramps) in zip(agents, expected):
            _check(agent.zone_id == zid, f"{link} zone_id={agent.zone_id!r} (기대 {zid!r})", failures)
            _check(agent.zone_mode is True, f"{zid}.zone_mode={agent.zone_mode}", failures)
            _check(agent.segs == segs, f"{zid}.segs={agent.segs} (기대 {segs})", failures)
            _check(agent.owned_ramps == ramps,
                   f"{zid}.owned_ramps={agent.owned_ramps} (기대 {ramps})", failures)
            _check(agent.seg == segs[0], f"{zid}.seg={agent.seg} (기대 {segs[0]})", failures)
            _check(agent.owns_origin_queue == (0 in segs),
                   f"{zid}.owns_origin_queue={agent.owns_origin_queue}", failures)
            # zone당 램프 1개 = metering 후보 곱집합이 발생하지 않는다.
            _check(len(agent.owned_ramps) == 1,
                   f"{zid} 소유 ramp가 1개가 아니다: {agent.owned_ramps}", failures)
    _check(total_agents == 4, f"freeway follower 총 수={total_agents} (기대 4)", failures)
    failures.extend(_zone_segment_vsl_checks(cfg))
    return failures


def _zone_segment_vsl_checks(cfg) -> list[str]:
    """솔버를 직접 호출해 **세그먼트별** VSL 결정·소유 ramp 전수 기입·좌표하강 영수증을 확인한다.

    ZONE-4 v2(2026-08-01 사용자 결정): zone은 에이전트 단위로만 유지하고 VSL은 소유
    세그먼트별로 따로 정한다. 따라서 zone 내부 균일성은 더 이상 계약이 아니며, 반대로
    세그먼트별 분기가 실제로 나오는지를 단언한다.
    """
    failures: list[str] = []
    n_seg = int(cfg.network.freeway_segments_per_link)
    follower = _make_follower(cfg, per_segment_price=True)
    state, demand, snapshot, previous, coupling = _make_solver_inputs(cfg)
    for link, zones in EXPECTED_ZONES.items():
        vsl_out, meter_out, evals = follower._solve_freeway_segment_agents(
            link, state, coupling, demand, snapshot, None, previous,
        )
        _check(evals > 0, f"{link} evals={evals}", failures)
        seg_vals: list[float] = []
        for i in range(n_seg):
            key = f"{link}__seg{i}"
            if key not in vsl_out:
                failures.append(f"{link} 세그먼트 VSL 키 누락: seg{i}")
                continue
            seg_vals.append(float(vsl_out[key]))
        # 세그먼트별 g_vsl 부호를 반대로 줬으므로 zone 내부에서 값이 갈려야 한다
        # (균일 VSL로 회귀하면 여기서 잡힌다).
        for zid, segs, _ramps in zones:
            if len(segs) < 2:
                continue
            vals = {float(vsl_out[f"{link}__seg{s}"]) for s in segs if f"{link}__seg{s}" in vsl_out}
            _check(len(vals) > 1,
                   f"{zid} zone 내부 VSL이 단일값이다(세그먼트별 결정 실패): {sorted(vals)}", failures)
        _check(len(seg_vals) == n_seg, f"{link} 세그먼트 VSL 수집 실패: {seg_vals}", failures)
        # 소유 ramp 전부가 metering 결과에 있어야 예산 사영 스코프가 성립한다(불변조건 3).
        _check(set(meter_out) == _link_ramps(cfg, link),
               f"{link} meter_out 키={sorted(meter_out)} (기대 {sorted(_link_ramps(cfg, link))})",
               failures)
    diag = follower._seg13_diag
    for link in ("FW_E", "FW_W"):
        _check(diag.get(f"wu_zone_count_{link}") == 2.0,
               f"wu_zone_count_{link}={diag.get(f'wu_zone_count_{link}')}", failures)
    # 좌표하강 영수증: zone 4개 전부 sweep 수·수렴 여부가 기록돼야 한다.
    for link, zones in EXPECTED_ZONES.items():
        for zid, _segs, _ramps in zones:
            dk = f"{link}_{zid}"
            _check(f"wu_zone_cd_sweeps_{dk}" in diag,
                   f"좌표하강 sweep 진단 누락: wu_zone_cd_sweeps_{dk}", failures)
            _check(f"wu_zone_cd_converged_{dk}" in diag,
                   f"좌표하강 수렴 진단 누락: wu_zone_cd_converged_{dk}", failures)
            _check(f"wu_zone_vsl_{dk}" in diag and f"wu_zone_vsl_max_{dk}" in diag,
                   f"zone VSL 진단 누락: {dk}", failures)
    return failures


def test_partition_guards() -> list[str]:
    """(3) 침묵 무효화 방지: 커버리지·연속성·정수성·zone_id 중복·알 수 없는 링크 키가 전부 RuntimeError."""
    failures: list[str] = []
    cfg, _ = _build_cfg(FLAGSHIP_TUNING)
    n_seg = int(cfg.network.freeway_segments_per_link)
    link = "FW_E"
    bad_cases: list[tuple[str, Any]] = [
        ("누락", {link: [[0, 1, 2, 3], [4, 5, 6]]}),
        ("중복", {link: [[0, 1, 2, 3, 4, 5], [5, 6, 7]]}),
        ("불연속", {link: [[0, 1, 2, 4, 5, 6], [3], [7]]}),
        ("범위밖", {link: [[0, 1, 2, 3, 4, 5], [6, 7, 8]]}),
        ("zone 순서", {link: [[6, 7], [0, 1, 2, 3, 4, 5]]}),
        ("세그먼트 역순", {link: [[5, 4, 3, 2, 1, 0], [6, 7]]}),
        ("빈 zone", {link: [[], list(range(n_seg))]}),
        ("빈 리스트", {link: []}),
        # 알 수 없는 링크 키 — 오타 하나로 zone 지정이 통째로 무시되던 침묵 무효화.
        ("알 수 없는 링크", {"FW_EE": [[0, 1, 2, 3, 4, 5], [6, 7]]}),
        ("알 수 없는 링크(유효 키 동반)", {
            link: [[0, 1, 2, 3, 4, 5], [6, 7]],
            "FW_Wrong": [[0, 1, 2, 3], [4, 5, 6, 7]],
        }),
        # 세그먼트 인덱스 float 절삭 금지(3.7 → 3은 조용한 오배정).
        ("세그먼트 3.7", {link: [[0, 1, 2, 3.7, 4, 5], [6, 7]]}),
        ("세그먼트 문자열", {link: [[0, 1, 2, "three", 4, 5], [6, 7]]}),
        # zone_id 중복 — 진단 키가 서로를 덮어쓴다.
        ("zone_id 중복", {link: [
            {"id": "dup", "segments": [0, 1, 2, 3, 4, 5]},
            {"id": "dup", "segments": [6, 7]},
        ]}),
    ]
    for name, groups in bad_cases:
        try:
            build_segment_agent_models(cfg, link, groups=groups)
        except RuntimeError:
            continue
        except Exception as exc:  # RuntimeError가 아니면 진단 불가 — 실패로 본다.
            failures.append(f"{name}: RuntimeError가 아닌 {type(exc).__name__}({exc})")
            continue
        failures.append(f"{name}: 에러 없이 통과했다(침묵 무효화)")
    # 정수 float(3.0)은 허용 — JSON은 정수를 float으로 실어 올 수 있다.
    try:
        agents = build_segment_agent_models(
            cfg, link, groups={link: [[0.0, 1.0, 2.0, 3.0, 4.0, 5.0], [6.0, 7.0]]},
        )
        _check([a.segs for a in agents] == [[0, 1, 2, 3, 4, 5], [6, 7]],
               f"정수 float 분할 결과={[a.segs for a in agents]}", failures)
    except Exception as exc:
        failures.append(f"정수 float 분할이 거부됐다: {type(exc).__name__}({exc})")
    # 정상 분할은 통과해야 한다(가드가 과하지 않은지 확인).
    try:
        agents = build_segment_agent_models(cfg, link, groups={link: [[0, 1, 2, 3, 4, 5], [6, 7]]})
        _check(len(agents) == 2, f"정상 분할 에이전트 수={len(agents)}", failures)
    except Exception as exc:
        failures.append(f"정상 분할이 거부됐다: {type(exc).__name__}({exc})")
    # 링크 부분 지정(유효한 링크 이름만 사용)은 계속 허용 — 미지정 링크는 세그먼트당 1 에이전트.
    try:
        agents = build_segment_agent_models(cfg, "FW_W", groups={link: [[0, 1, 2, 3, 4, 5], [6, 7]]})
        _check(len(agents) == n_seg, f"미지정 링크 에이전트 수={len(agents)}", failures)
        _check(all(a.zone_mode is False for a in agents),
               "미지정 링크 에이전트에 zone_mode가 켜졌다", failures)
    except Exception as exc:
        failures.append(f"미지정 링크 빌드 실패: {type(exc).__name__}({exc})")
    return failures


def test_single_segment_zone_parity() -> list[str]:
    """(4) 전부 단일 세그먼트인 zone 지정: 결정은 기본 경로와 동일, 영수증은 켜져 있어야 한다.

    zone_mode를 len(segs)>1로 판정하면 이 구성에서 영수증·안전망이 통째로 꺼진다
    (false-negative). 빌더가 명시적으로 반환하는 플래그로 판정하는지 확인한다.
    """
    failures: list[str] = []
    cfg_base, _ = _build_cfg(FLAGSHIP_TUNING)
    n_seg = int(cfg_base.network.freeway_segments_per_link)
    link = "FW_W"

    follower_base = _make_follower(cfg_base)
    state, demand, snapshot, previous, coupling = _make_solver_inputs(cfg_base)
    vsl_base, meter_base, evals_base = follower_base._solve_freeway_segment_agents(
        link, state, coupling, demand, snapshot, None, previous,
    )

    cfg_zone, _ = _build_cfg(FLAGSHIP_TUNING)
    cfg_zone.mpc.freeway_agent_groups = {
        lk: [{"id": f"{lk}_s{i}", "segments": [i]} for i in range(n_seg)]
        for lk in cfg_zone.network.freeway_links
    }
    follower_zone = _make_follower(cfg_zone)
    state_z, demand_z, snapshot_z, previous_z, coupling_z = _make_solver_inputs(cfg_zone)
    vsl_zone, meter_zone, evals_zone = follower_zone._solve_freeway_segment_agents(
        link, state_z, coupling_z, demand_z, snapshot_z, None, previous_z,
    )
    _check(vsl_base == vsl_zone, f"단일 세그먼트 zone VSL 불일치:\n{vsl_base}\n{vsl_zone}", failures)
    _check(meter_base == meter_zone,
           f"단일 세그먼트 zone metering 불일치:\n{meter_base}\n{meter_zone}", failures)
    _check(evals_base == evals_zone,
           f"단일 세그먼트 zone evals 불일치: {evals_base} vs {evals_zone}", failures)
    # 영수증은 켜져 있어야 한다.
    _check(follower_zone._seg13_diag.get(f"wu_zone_count_{link}") == float(n_seg),
           f"단일 세그먼트 zone 영수증 누락: "
           f"wu_zone_count_{link}={follower_zone._seg13_diag.get(f'wu_zone_count_{link}')}",
           failures)
    _check(not any(k.startswith("wu_zone_") for k in follower_base._seg13_diag),
           "기본 경로에 zone 진단 키가 유출됐다", failures)
    # 단일 세그먼트 zone은 좌표하강에 진입하지 않는다(sweep 0).
    _check(follower_zone._seg13_diag.get(f"wu_zone_cd_sweeps_{link}_{link}_s0") == 0.0,
           f"단일 세그먼트 zone이 좌표하강에 진입했다: "
           f"{follower_zone._seg13_diag.get(f'wu_zone_cd_sweeps_{link}_{link}_s0')}", failures)
    return failures


def test_multi_ramp_gating() -> list[str]:
    """(5) 한 세그먼트에 ramp 2개: 다중 ramp 일반화는 zone 경로에서만 발화해야 한다.

    NetworkConfig 데이터클래스 기본 ramp_merge_segment_index가 정확히 이 구성이다.
    기본 경로에서 일반화가 새면 groups 미지정인데도 meter 키가 2개로 늘고 evals가 뛴다.
    """
    failures: list[str] = []
    link = "FW_W"

    cfg_plain, _ = _build_cfg(FLAGSHIP_TUNING)
    ramps_w = sorted(_link_ramps(cfg_plain, link))
    if len(ramps_w) < 2:
        return [f"{link} 소유 ramp가 2개 미만이라 케이스를 만들 수 없다: {ramps_w}"]
    merge_seg = int(cfg_plain.network.ramp_merge_segment_index[ramps_w[0]])
    for r in ramps_w:
        cfg_plain.network.ramp_merge_segment_index[r] = merge_seg
    follower_plain = _make_follower(cfg_plain)
    state, demand, snapshot, previous, coupling = _make_solver_inputs(cfg_plain)
    _vsl, meter_plain, evals_plain = follower_plain._solve_freeway_segment_agents(
        link, state, coupling, demand, snapshot, None, previous,
    )
    # 기본 경로 = 기존 owned_ramps[0] 절삭 유지 → 대표 ramp 1개만 결정에 나온다.
    _check(len(meter_plain) == 1,
           f"기본 경로에서 다중 ramp 일반화가 발화했다: meter={meter_plain}", failures)

    cfg_zone, _ = _build_cfg(FLAGSHIP_TUNING)
    for r in ramps_w:
        cfg_zone.network.ramp_merge_segment_index[r] = merge_seg
    n_seg = int(cfg_zone.network.freeway_segments_per_link)
    cfg_zone.mpc.freeway_agent_groups = {
        lk: [
            {"id": f"{lk}_up", "segments": list(range(0, merge_seg + 1))},
            {"id": f"{lk}_dn", "segments": list(range(merge_seg + 1, n_seg))},
        ]
        for lk in cfg_zone.network.freeway_links
    }
    follower_zone = _make_follower(cfg_zone)
    state_z, demand_z, snapshot_z, previous_z, coupling_z = _make_solver_inputs(cfg_zone)
    _vsl_z, meter_zone, evals_zone = follower_zone._solve_freeway_segment_agents(
        link, state_z, coupling_z, demand_z, snapshot_z, None, previous_z,
    )
    # zone 경로에서는 두 ramp가 모두 결정에 나와야 한다(사영 스코프 = 링크 소유 ramp 전체).
    _check(set(meter_zone) == set(ramps_w),
           f"zone 경로에서 소유 ramp가 누락됐다: {sorted(meter_zone)} (기대 {ramps_w})", failures)
    _check(evals_zone > evals_plain,
           f"zone 경로 evals={evals_zone}가 기본 경로 {evals_plain}보다 크지 않다", failures)
    return failures


def test_budget_projection_scope() -> list[str]:
    """(6) N_UF_star>0 가짜 leader: 예산 사영 참가자 집합·스코프가 링크 소유 ramp 전체와 일치.

    plan.md 불변조건 3 정정(2026-08-01): Σmeter = ω_F·N_UF* 등식은 zone4/flagship
    어느 쪽에서도 성립하지 않는다 — METER-BOX 회랑 하한과 spillback 하한이 우선하는
    설계된 거동이다. 따라서 단언 대상은 등식이 아니라 **사영 스코프**다.
    """
    failures: list[str] = []
    for tag, tuning_path in (("flagship", FLAGSHIP_TUNING), ("zone4", ZONE4_TUNING)):
        cfg, _ = _build_cfg(tuning_path)
        follower = _make_follower(cfg)
        follower._wu._omega_f = {lk: 0.5 for lk in cfg.network.freeway_links}
        state, demand, snapshot, previous, coupling = _make_solver_inputs(cfg)
        leader = _FakeLeader(3200.0)
        for link in cfg.network.freeway_links:
            _vsl, meter_out, _evals = follower._solve_freeway_segment_agents(
                link, state, coupling, demand, snapshot, leader, previous,
            )
            expect = _link_ramps(cfg, link)
            _check(set(meter_out) == expect,
                   f"{tag}/{link} 사영 참가자={sorted(meter_out)} (기대 {sorted(expect)})", failures)
            diag = follower._seg13_diag
            for key in (f"wu_seg13_budget_{link}", f"wu_seg13_presplit_{link}",
                        f"wu_seg13_postsplit_{link}"):
                _check(key in diag, f"{tag}/{link} 사영 영수증 누락: {key}", failures)
            # 스코프 단언의 보강: 사영 결과가 램프 용량 안에 있어야 한다.
            for ramp, value in meter_out.items():
                cap = float(cfg.network.ramp_capacity_veh_h[ramp])
                _check(-1e-6 <= float(value) <= cap + 1e-6,
                       f"{tag}/{link} {ramp} metering={value}가 [0,{cap}] 밖이다", failures)
    return failures


# ---------------------------------------------------------------------------
# VSL 타이브레이크 규약(P1) · 예측-플랜트 vsl 배선(P2)
# outputs/vsl_sensitivity_20260801.md §1-3(C1/C2), §6(P1/P2)
# ---------------------------------------------------------------------------

_ZONE_GROUPS = {
    "FW_E": [{"id": "fw_yangjae_E", "segments": [0, 1, 2, 3]},
             {"id": "fw_seocho_E", "segments": [4, 5, 6, 7]}],
    "FW_W": [{"id": "fw_seocho_W", "segments": [0, 1, 2, 3]},
             {"id": "fw_yangjae_W", "segments": [4, 5, 6, 7]}],
}


def _uniform_solver_call(
    tuning: Path, rho: float, prev_vsl: float, *, zone: bool, tie_pref: bool,
    link: str = "FW_E",
) -> tuple[list[float], dict[str, float], int]:
    """균일밀도 상태에서 솔버 1회 — (세그먼트 VSL, 소유 ramp metering, evals).

    diagnose_vsl_channel_20260801.py `_solver_call`과 같은 합성 상태다(leader=None,
    가격 0). tie_pref는 cfg에 직접 걸어 tuning 체인과 독립적으로 A/B한다.
    """
    cfg, _ = _build_cfg(tuning)
    if zone:
        cfg.mpc.freeway_agent_groups = _ZONE_GROUPS
    cfg.mpc.vsl_tie_prefer_no_control = bool(tie_pref)
    n_seg = int(cfg.network.freeway_segments_per_link)
    state, demand, snapshot, previous, coupling = _make_solver_inputs(cfg)
    v0 = desired_speed_kmh(
        rho, cfg.network.v_free, cfg.network.rho_crit, cfg.network.metanet_a_m,
    )
    for lk in cfg.network.freeway_links:
        state.freeway_density[lk] = [float(rho)] * n_seg
        state.freeway_speed[lk] = [float(v0)] * n_seg
        state.freeway_effective_lanes[lk] = [float(cfg.network.freeway_lanes)] * n_seg
        previous.vsl[lk] = float(prev_vsl)
        snapshot.vsl[lk] = float(prev_vsl)
        for i in range(n_seg):
            previous.vsl[f"{lk}__seg{i}"] = float(prev_vsl)
            snapshot.vsl[f"{lk}__seg{i}"] = float(prev_vsl)
    follower = _make_follower(cfg)
    vsl_out, meter_out, evals = follower._solve_freeway_segment_agents(
        link, state, coupling, demand, snapshot, None, previous,
    )
    segs = [float(vsl_out[f"{link}__seg{i}"]) for i in range(n_seg)]
    meter = {r: round(float(v), 6) for r, v in sorted(meter_out.items())}
    return segs, meter, evals


def _ratchet_trajectory(
    tuning: Path, rho: float, *, zone: bool, tie_pref: bool, steps: int = 5,
    seg: int = 3, start: float = 120.0,
) -> list[float]:
    """previous를 직전 결정으로 갱신하며 다단계 시뮬레이션 — seg의 VSL 궤적."""
    prev, traj = float(start), [float(start)]
    for _ in range(steps):
        segs, _m, _e = _uniform_solver_call(
            tuning, rho, prev, zone=zone, tie_pref=tie_pref,
        )
        prev = float(segs[seg])
        traj.append(prev)
    return traj


# 수정 **전** 코드(strict '<' + vsl_set 오름차순)로 실측한 결정. 플래그 OFF는 이 값을
# 그대로 재현해야 한다(§6 P1 게이팅 계약: 기본값에서 비트 동일).
#
# 2026-08-01 본선 체인 격자로 재실측. ρ=35 두 행의 seg4가 100 -> 80으로 내려간 것 외에는
# 구 골든과 동일하고 evals/metering/래칫 궤적은 전부 불변이다. 코드 변경이 아니라 기하
# 변경의 귀결임을 다음으로 확인했다 — cfg.network의 freeway_segment_length_km(0.795059)와
# ramp_merge/off_ramp_segment_index(구 격자값)를 되돌리면 **현재 코드가** 구 골든 6행 +
# evals + metering + 래칫을 그대로 재현한다. 즉 OFF 분기의 결정 표현식은 손대지 않았다.
# 주 원인은 세그먼트 길이(0.795059 -> 1.346925 km, TTS/METANET 항 스케일)이고, seg6의
# 동률 해소는 R_D_E 합류 세그먼트가 7 -> 5로 옮겨간 결과다.
_TIE_OFF_GOLDEN: dict[tuple[float, float], list[float]] = {
    (12.0, 120.0): [120.0] * 8,
    (12.0, 100.0): [120.0] * 8,
    (12.0, 80.0): [100.0] * 8,
    (35.0, 120.0): [120.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0],
    (35.0, 100.0): [120.0, 80.0, 80.0, 80.0, 80.0, 80.0, 80.0, 80.0],
    (35.0, 80.0): [100.0, 80.0, 80.0, 80.0, 80.0, 80.0, 80.0, 80.0],
}
_TIE_OFF_GOLDEN_EVALS: dict[tuple[float, float], int] = {
    (12.0, 120.0): 32, (12.0, 100.0): 48, (12.0, 80.0): 32,
    (35.0, 120.0): 32, (35.0, 100.0): 48, (35.0, 80.0): 32,
}
_TIE_OFF_GOLDEN_METER = {"R_D_E": 1200.0, "R_F_E": 1200.0}
# §1-3 실측 래칫 — VSL-BOX 20이라 스텝당 한 칸씩 내려가 80에 고착한다.
_TIE_OFF_RATCHET = [120.0, 100.0, 80.0, 80.0, 80.0, 80.0]


def test_vsl_tie_flag_off_regression() -> list[str]:
    """(10) P1 게이팅: 플래그 OFF면 VSL/metering/evals가 수정 전 결정과 동일해야 한다.

    골든은 tie-aware 갱신을 넣기 **전** 코드로 실측한 값이다. OFF 분기가
    `cost < best_cost` + `best_cost = cost`(기존 표현식) 그대로인지를 결정 수준에서
    잠근다. 래칫 궤적까지 그대로 재현되는지도 확인한다 — 래칫은 버그지만
    플래그 OFF에서는 **보존돼야 하는** 기존 거동이다(flagship 재현성).
    """
    failures: list[str] = []
    _check(_build_cfg(FLAGSHIP_TUNING)[0].mpc.vsl_tie_prefer_no_control is False,
           "flagship tuning에 vsl_tie_prefer_no_control이 켜졌다(부모 체인 오염)", failures)
    for (rho, prev), expect in _TIE_OFF_GOLDEN.items():
        segs, meter, evals = _uniform_solver_call(
            FLAGSHIP_TUNING, rho, prev, zone=False, tie_pref=False,
        )
        _check(segs == expect,
               f"OFF rho={rho} prev={prev} VSL={segs} (기대 {expect})", failures)
        _check(meter == _TIE_OFF_GOLDEN_METER,
               f"OFF rho={rho} prev={prev} metering={meter} "
               f"(기대 {_TIE_OFF_GOLDEN_METER})", failures)
        _check(evals == _TIE_OFF_GOLDEN_EVALS[(rho, prev)],
               f"OFF rho={rho} prev={prev} evals={evals} "
               f"(기대 {_TIE_OFF_GOLDEN_EVALS[(rho, prev)]})", failures)
    traj = _ratchet_trajectory(FLAGSHIP_TUNING, 35.0, zone=False, tie_pref=False)
    _check(traj == _TIE_OFF_RATCHET,
           f"OFF 래칫 궤적={traj} (기대 {_TIE_OFF_RATCHET})", failures)
    return failures


def test_vsl_tie_flag_on_no_ratchet() -> list[str]:
    """(11) P1 본체: 플래그 ON이면 혼잡 동률 구간(ρ≈35)의 래칫이 사라지고 무제어에 머문다.

    ρ=35에서는 메뉴 [80,100,120]이 전부 비구속(ρ_bind(80)=25.84 < 35)이라 후보 비용이
    정확히 동률이다. 동률이면 무제어 우선이므로 VSL은 120에 머물러야 하고, previous를
    직전 결정으로 갱신해도 내려가지 않아야 한다.
    """
    failures: list[str] = []
    for tag, tuning, zone in (("flagship", SEGVSL_TUNING, False),
                              ("zone4", ZONE4_TUNING, True)):
        traj = _ratchet_trajectory(tuning, 35.0, zone=zone, tie_pref=True)
        _check(traj == [120.0] * 6,
               f"ON/{tag} 래칫이 남아 있다: 궤적={traj}", failures)
        # 단일 스텝 결정도 확인 — previous가 이미 내려가 있어도 무제어 쪽으로 복귀한다
        # (박스 20이라 한 스텝에 한 칸씩, 80 → 100).
        for prev, expect in ((120.0, 120.0), (100.0, 120.0), (80.0, 100.0)):
            segs, _m, _e = _uniform_solver_call(
                tuning, 35.0, prev, zone=zone, tie_pref=True,
            )
            _check(segs == [expect] * 8,
                   f"ON/{tag} rho=35 prev={prev} VSL={segs} (기대 전 세그먼트 {expect})",
                   failures)
    return failures


def test_vsl_tie_free_flow_invariant() -> list[str]:
    """(12) P1 안전성: 물리 감도가 살아있는 자유류(ρ≈12) 결정은 플래그 ON/OFF가 같아야 한다.

    ρ=12는 메뉴 전 rung이 구속하고 J(120) < J(100) < J(80)로 **엄격** 우열이 있다
    (§1-1: spread 80 vs 120 = +3.51%). 동률이 아니므로 tie-break가 개입할 여지가 없다.
    여기서 결정이 바뀌면 ε가 진짜 감도를 삼킨 것이다.
    """
    failures: list[str] = []
    for prev in (120.0, 100.0, 80.0):
        off_v, off_m, off_e = _uniform_solver_call(
            SEGVSL_TUNING, 12.0, prev, zone=False, tie_pref=False,
        )
        on_v, on_m, on_e = _uniform_solver_call(
            SEGVSL_TUNING, 12.0, prev, zone=False, tie_pref=True,
        )
        _check(off_v == on_v,
               f"자유류 rho=12 prev={prev} VSL이 플래그로 바뀌었다: OFF={off_v} ON={on_v}",
               failures)
        _check(off_m == on_m and off_e == on_e,
               f"자유류 rho=12 prev={prev} metering/evals가 바뀌었다: "
               f"OFF=({off_m},{off_e}) ON=({on_m},{on_e})", failures)
    # ε가 감도를 삼키지 않았다는 양성 확인 — prev=80이면 상향(100)이 실제로 선택된다.
    up_v, _m, _e = _uniform_solver_call(
        SEGVSL_TUNING, 12.0, 80.0, zone=False, tie_pref=True,
    )
    _check(up_v == [100.0] * 8,
           f"자유류에서 물리 감도가 죽었다(박스 상단 100 미선택): {up_v}", failures)
    return failures


def test_vsl_tie_path_parity() -> list[str]:
    """(13) 규약 정합: 같은 상태에서 단일 세그먼트 경로와 zone 좌표하강 경로의 VSL 결정이 같다.

    §7-1이 zone4 A/B를 무효화한 원인으로 지목한 것이 정확히 이 불일치다 — 단일
    세그먼트는 `best_cost=inf`라 첫 후보(최저 VSL)를 잡고, zone은 앵커(previous)를
    유지했다. 플래그 OFF에서 두 경로가 **다르다는 것**도 함께 단언한다(테스트가
    no-op이 되는 것을 막는 음성 대조).
    """
    failures: list[str] = []
    cases = [(rho, prev) for rho in (20.0, 28.0, 35.0, 45.0)
             for prev in (120.0, 100.0, 80.0)]
    diverged_off = 0
    for rho, prev in cases:
        flag_on, _m1, _e1 = _uniform_solver_call(
            SEGVSL_TUNING, rho, prev, zone=False, tie_pref=True,
        )
        zone_on, _m2, _e2 = _uniform_solver_call(
            ZONE4_TUNING, rho, prev, zone=True, tie_pref=True,
        )
        _check(flag_on == zone_on,
               f"ON rho={rho} prev={prev} 경로 불일치: 단일세그={flag_on} zone={zone_on}",
               failures)
        flag_off, _m3, _e3 = _uniform_solver_call(
            SEGVSL_TUNING, rho, prev, zone=False, tie_pref=False,
        )
        zone_off, _m4, _e4 = _uniform_solver_call(
            ZONE4_TUNING, rho, prev, zone=True, tie_pref=False,
        )
        if flag_off != zone_off:
            diverged_off += 1
    _check(diverged_off > 0,
           "플래그 OFF에서도 두 경로가 전부 일치한다 — 음성 대조가 성립하지 않으므로 "
           "(13)의 ON 단언이 규약 정합을 증명하지 못한다", failures)
    return failures


def test_prediction_plant_vsl_wiring() -> list[str]:
    """(14) P2: 예측모델이 select_anticipation_nu에 세그먼트 VSL을 넘긴다.

    플랜트(metanet.py:615)는 이미 vsl_i를 넘기는데 예측모델
    (local_freeway_plant.py `freeway_substep_local`)은 안 넘겼다. capacity_drop_anticipation
    =False인 현행에서는 effective_rho_crit이 vsl을 무시하므로 no-op이지만, 기전을 켜는
    순간 follower만 ν 전환 회피 이득을 못 보는 비정합이 된다(§1-3 C2).
    물리로 간접 확인하면 v_eff 변화와 뒤섞이므로 호출 인자를 직접 관찰한다.
    """
    failures: list[str] = []
    cfg, _ = _build_cfg(SEGVSL_TUNING)
    link = "FW_E"
    n_seg = int(cfg.network.freeway_segments_per_link)
    model = lfp.build_local_freeway_model(cfg, link)
    state, demand, snapshot, _previous, _coupling = _make_solver_inputs(cfg)
    control = ControlAction.uncontrolled(cfg)
    expect_vsl = [120.0, 110.0, 100.0, 90.0, 80.0, 90.0, 100.0, 110.0][:n_seg]
    for i, v in enumerate(expect_vsl):
        control.vsl[f"{link}__seg{i}"] = float(v)
    seen: list[tuple[float, object]] = []
    original = lfp.select_anticipation_nu

    def _spy(rho, net, vsl=None):
        seen.append((float(rho), vsl))
        return original(rho, net, vsl)

    lfp.select_anticipation_nu = _spy
    try:
        lfp.freeway_substep_local(
            model,
            list(state.freeway_density[link]),
            list(state.freeway_speed[link]),
            list(state.freeway_effective_lanes[link]),
            {},
            float(state.mainline_origin_queue.get(link, 0.0)),
            {r: float(cfg.network.ramp_capacity_veh_h[r]) for r in model.owned_ramps},
            {},
            control,
            demand,
        )
    except Exception as exc:  # noqa: BLE001 — 배선 확인이 목적이라 원인을 그대로 노출한다.
        failures.append(f"freeway_substep_local 호출 실패: {type(exc).__name__}({exc})")
        return failures
    finally:
        lfp.select_anticipation_nu = original
    _check(len(seen) == n_seg,
           f"select_anticipation_nu 호출 수={len(seen)} (기대 {n_seg})", failures)
    got = [v for _rho, v in seen]
    _check(all(v is not None for v in got),
           f"예측모델이 vsl 없이 호출했다(P2 미적용): {got}", failures)
    if all(v is not None for v in got):
        _check([float(v) for v in got] == [float(v) for v in expect_vsl],
               f"넘어간 vsl={got} (기대 {expect_vsl})", failures)
    # 현행 설정(capacity_drop_anticipation=False)에서는 no-op이어야 한다 — 배선이
    # 기본 거동을 바꾸지 않는다는 §6 P2의 "정의상 비트 동일" 확인.
    _check(getattr(cfg.network, "capacity_drop_anticipation", False) is False,
           "real-world cfg에서 capacity_drop_anticipation이 켜져 있다 — P2가 더 이상 "
           "no-op이 아니므로 비트 동일 주장을 다시 세워야 한다", failures)
    for rho, vsl in seen:
        _check(original(rho, cfg.network, vsl) == original(rho, cfg.network, None),
               f"capdrop OFF인데 vsl 전달이 ν를 바꿨다: rho={rho} vsl={vsl}", failures)
    return failures


# ---------------------------------------------------------------------------
# 어댑터 스모크(서브프로세스)
# ---------------------------------------------------------------------------


def _make_state_json(sim_sec: float, count_per_seg: float, speed_kph: float) -> dict[str, Any]:
    """VBS WriteStateJson(run_real_world_stackelberg_controller.vbs L920-959) 스키마의 합성 state."""
    def rows() -> list[dict[str, float]]:
        return [
            {"count": float(count_per_seg), "speed_sum": float(count_per_seg) * float(speed_kph),
             "length_km": 1.0, "lanes": 4}
            for _ in range(8)
        ]

    return {
        "sim_sec": float(sim_sec),
        "sim_period_sec": 3600.0,
        "control_interval_sec": 60.0,
        "total_vehicles": 500,
        "urban_vehicles": 220,
        "freeway_vehicles": 230,
        "ramp_vehicles": 30,
        "boundary_vehicles": 20,
        "other_vehicles": 0,
        "mean_speed_kph": 45.0,
        "freeway_mean_speed_kph": float(speed_kph),
        "stopped_vehicles": 40,
        "demand": {
            "urban_volume_vph": 1200.0,
            "freeway_volume_vph": 3600.0,
            "ramp_volume_vph": 0,
            "demand_profile": "baseline",
        },
        "ramp_counts": {"D": 12, "F": 6},
        "freeway_segments": {"FW_E": rows(), "FW_W": rows()},
    }


def _smoke_tuning_dict(base: Path) -> dict[str, Any]:
    """스모크 전용 저예산 tuning(base 체인 extends)."""
    return {
        "extends": str(base),
        "name": f"zone_smoke_{base.stem}",
        "config_overrides": {
            "mpc": {
                "horizon_steps": 1,
                "control_horizon_steps": 1,
                "leader_candidate_count": 3,
                "leader_refinement_candidate_count": 3,
                "max_nash_iter": 2,
                "leader_value_depth": 1,
            },
            "urban_follower": {
                "allocation_pso_particles": 4,
                "allocation_pso_iterations": 4,
            },
            "freeway_follower": {
                "horizon_beam_width": 1,
                "horizon_ramp_candidate_limit": 1,
                "horizon_vsl_candidate_limit_per_link": 1,
            },
        },
        "adapter": {"flagship": {"nash_smax": 2}},
    }


def _run_adapter(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(ADAPTER_PY)] + args
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=1800)


def _decide(tmp: Path, base: Path, tag: str) -> tuple[dict[str, Any], list[dict[str, str]], list[str]]:
    """pstack-flagship 결정 1회 — (action json payload, action csv rows, failures)."""
    failures: list[str] = []
    tuning_path = tmp / f"{tag}_tuning.json"
    tuning_path.write_text(
        json.dumps(_smoke_tuning_dict(base), ensure_ascii=False, indent=2), encoding="utf-8",
    )
    state_path = tmp / f"{tag}_state.json"
    state_path.write_text(
        json.dumps(_make_state_json(300.0, count_per_seg=110.0, speed_kph=45.0)), encoding="utf-8",
    )
    out_json, out_csv = tmp / f"{tag}_action.json", tmp / f"{tag}_action.csv"
    proc = _run_adapter([
        "--state-json", str(state_path),
        "--out-action-json", str(out_json),
        "--out-action-csv", str(out_csv),
        "--controller", "pstack-flagship",
        "--tuning-json", str(tuning_path),
        "--repo-root", str(REPO_ROOT),
        # 프로덕션 실행 경로와 동일한 매핑/캘리브레이션을 쓴다.
        "--mapping-json", str(PROD_MAPPING),
        "--calibration-json", str(PROD_CALIBRATION),
    ], cwd=tmp)
    if proc.returncode != 0:
        failures.append(
            f"{tag} returncode={proc.returncode}\nstdout={proc.stdout[-3000:]}\nstderr={proc.stderr[-3000:]}"
        )
        return {}, [], failures
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    # action csv는 utf-8-sig로 쓰인다(BOM) — DictReader가 첫 필드명을 잃지 않게 맞춘다.
    with out_csv.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    meta = payload.get("metadata", {})
    _check(meta.get("controller_status") == "ok",
           f"{tag} controller_status={meta.get('controller_status')} error={meta.get('controller_error')}",
           failures)
    _DECISION_CACHE[tag] = (payload, rows)
    return payload, rows, failures


_DECISION_CACHE: dict[str, tuple[dict[str, Any], list[dict[str, str]]]] = {}
_RAMPS = ("R_D_W", "R_F_W", "R_D_E", "R_F_E")
_N_SEG = 8
_LINKS = ("FW_E", "FW_W")


def _row_identity(rows: list[dict[str, str]]) -> list[tuple[str, str, str, str]]:
    """행 스키마 지문 — 값(speed/rate)은 빼고 어떤 액추에이터 행이 나왔는지만."""
    return sorted(
        (str(r.get("kind", "")), str(r.get("id", "")), str(r.get("dsd_no", "")),
         str(r.get("lane", "")))
        for r in rows
    )


def _vsl_speeds(rows: list[dict[str, str]]) -> list[float]:
    out: list[float] = []
    for r in rows:
        if r.get("kind") != "vsl":
            continue
        try:
            out.append(float(r.get("speed_kph", "")))
        except (TypeError, ValueError):
            continue
    return out


def _zone_diag(payload: Mapping[str, Any]) -> list[str]:
    diag = payload.get("diagnostics", {})
    if not isinstance(diag, Mapping):
        return []
    return [str(k) for k in diag if str(k).startswith("wu_zone_")]


def _segment_vsl_actuation_checks(
    payload: Mapping[str, Any], rows: list[dict[str, str]], tag: str,
) -> list[str]:
    """세그먼트 VSL이 액추에이터(action json/csv)까지 실제로 도달했는지 — [차단] 결함 회귀 방지.

    현행 tuning 체인의 actuation.vsl_segment_override_policy가 세그먼트 키를 지우면
    컨트롤러가 세그먼트별로 결정해도 CSV에는 링크 대표값 1개만 남는다. 이전 테스트는
    zone4/flagship 지문 동일성만 봐서 이 차단 결함을 잡지 못했다.
    """
    failures: list[str] = []
    meta = payload.get("metadata", {})
    vsl = payload.get("vsl", {})
    if not isinstance(vsl, Mapping):
        vsl = {}
    missing = [
        f"{link}__seg{i}" for link in _LINKS for i in range(_N_SEG)
        if f"{link}__seg{i}" not in vsl
    ]
    _check(not missing,
           f"{tag} action json에 세그먼트 VSL 키가 없다({len(missing)}개 누락): {missing[:4]}...",
           failures)
    _check("vsl_segment_overrides_cleared" not in meta,
           f"{tag} 세그먼트 VSL이 actuation 가드에 삭제됐다: "
           f"vsl_segment_overrides_cleared={meta.get('vsl_segment_overrides_cleared')}", failures)
    speeds = _vsl_speeds(rows)
    _check(len(speeds) == len(rows) - sum(1 for r in rows if r.get("kind") != "vsl") and speeds,
           f"{tag} csv kind=vsl 행의 speed 파싱 실패", failures)
    uniq = sorted(set(speeds))
    # 고유 speed 값 개수는 결정 단위(세그먼트) 수를 넘을 수 없다.
    _check(1 <= len(uniq) <= _N_SEG * len(_LINKS),
           f"{tag} csv kind=vsl 고유 speed 수={len(uniq)} (허용 1~{_N_SEG * len(_LINKS)}): {uniq}",
           failures)
    return failures


def test_zone4_smoke(tmp: Path) -> list[str]:
    """(7) zone4 tuning으로 결정 1회 — action json/csv 정상 + zone 진단 + 세그먼트 VSL 실집행."""
    payload, rows, failures = _decide(tmp, ZONE4_TUNING, "zone4")
    if not payload:
        return failures
    for key in ("ramp_metering", "vsl", "green_times"):
        _check(bool(payload.get(key)), f"zone4 action json에 {key} 없음", failures)
    _check(bool(rows), "zone4 action csv가 비었다", failures)
    _check(any(r.get("kind") == "vsl" for r in rows), "zone4 csv에 kind=vsl 행 없음", failures)
    _check(any(r.get("kind") == "ramp_meter" for r in rows),
           "zone4 csv에 kind=ramp_meter 행 없음", failures)
    # ramp 4그룹이 전부 결정에 나와야 한다(zone이 소유 ramp를 빠뜨리면 예산 사영이 샌다).
    metering = payload.get("ramp_metering", {})
    for ramp in _RAMPS:
        _check(ramp in metering, f"zone4 ramp_metering에 {ramp} 없음: {sorted(metering)}", failures)
    # zone 영수증: groups가 SEG13 경로에 실제로 도달했고 zone이 4개다.
    diag = payload.get("diagnostics", {})
    if not isinstance(diag, Mapping):
        diag = {}
    _check(float(diag.get("wu_seg13_active", 0.0)) == 1.0,
           f"zone4 wu_seg13_active={diag.get('wu_seg13_active')}", failures)
    for link in _LINKS:
        _check(float(diag.get(f"wu_zone_count_{link}", 0.0)) == 2.0,
               f"zone4 wu_zone_count_{link}={diag.get(f'wu_zone_count_{link}')}", failures)
    for link, zones in EXPECTED_ZONES.items():
        for zid, _segs, _ramps in zones:
            _check(f"wu_zone_vsl_{link}_{zid}" in diag,
                   f"zone4 진단에 wu_zone_vsl_{link}_{zid} 없음", failures)
            _check(f"wu_zone_cd_sweeps_{link}_{zid}" in diag,
                   f"zone4 진단에 wu_zone_cd_sweeps_{link}_{zid} 없음", failures)
    failures.extend(_segment_vsl_actuation_checks(payload, rows, "zone4"))
    return failures


def test_segvsl_control(tmp: Path) -> list[str]:
    """(8) 대조군: zone 없이 actuation 정책만 같은 tuning — 세그먼트 VSL이 도달하되 zone 진단은 없다."""
    payload, rows, failures = _decide(tmp, SEGVSL_TUNING, "segvsl")
    if not payload:
        return failures
    leaked = _zone_diag(payload)
    _check(not leaked, f"대조군(zone 미지정)에 zone 진단 키 유출: {leaked}", failures)
    failures.extend(_segment_vsl_actuation_checks(payload, rows, "segvsl"))
    cached = _DECISION_CACHE.get("zone4")
    if cached is not None:
        # 스키마 불변(plan.md 불변조건 2).
        _check(_row_identity(rows) == _row_identity(cached[1]),
               "zone4와 대조군의 action csv 행 스키마가 다르다", failures)
        _check(sorted(payload.get("vsl", {})) == sorted(cached[0].get("vsl", {})),
               "zone4와 대조군의 vsl 키 집합이 다르다", failures)
    return failures


def test_no_zone_regression(tmp: Path) -> list[str]:
    """(9) 회귀: zone 미지정 flagship 결정 정상 + zone 진단 무유출 + action 스키마 동일."""
    payload, rows, failures = _decide(tmp, FLAGSHIP_TUNING, "flagship")
    if not payload:
        return failures
    _check(any(r.get("kind") == "vsl" for r in rows), "flagship csv에 kind=vsl 행 없음", failures)
    _check(any(r.get("kind") == "ramp_meter" for r in rows),
           "flagship csv에 kind=ramp_meter 행 없음", failures)
    metering = payload.get("ramp_metering", {})
    for ramp in _RAMPS:
        _check(ramp in metering, f"flagship ramp_metering에 {ramp} 없음: {sorted(metering)}", failures)
    leaked = _zone_diag(payload)
    _check(not leaked, f"zone 미지정 런에 zone 진단 키 유출: {leaked}", failures)
    # flagship은 상속받은 clear 정책을 그대로 쓴다 — 세그먼트 키가 지워지는 게 정상이고,
    # 이것이 대조군(segvsl) tuning을 따로 만든 이유다.
    meta = payload.get("metadata", {})
    _check(float(meta.get("vsl_segment_overrides_cleared", 0.0)) > 0.0,
           "flagship에서 vsl_segment_overrides_cleared가 기록되지 않았다"
           "(상속 정책이 바뀌었다면 대조군 설계를 재검토해야 한다)", failures)
    # 스키마 불변(plan.md 불변조건 2): zone4와 flagship의 action 행 지문이 같아야 한다.
    cached = _DECISION_CACHE.get("zone4")
    if cached is not None:
        _check(_row_identity(rows) == _row_identity(cached[1]),
               "zone4와 flagship의 action csv 행 스키마가 다르다", failures)
        _check(sorted(payload.get("ramp_metering", {})) == sorted(cached[0].get("ramp_metering", {})),
               "zone4와 flagship의 ramp_metering 키 집합이 다르다", failures)
    return failures


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="freeway_zone_test_"))
    ctl_tmp = Path(tempfile.mkdtemp(prefix="freeway_zone_ctl_"))
    reg_tmp = Path(tempfile.mkdtemp(prefix="freeway_zone_reg_"))
    tests = [
        ("default_unchanged", test_default_unchanged),
        ("zone4_mapping", test_zone4_mapping),
        ("partition_guards", test_partition_guards),
        ("single_segment_zone_parity", test_single_segment_zone_parity),
        ("multi_ramp_gating", test_multi_ramp_gating),
        ("budget_projection_scope", test_budget_projection_scope),
        ("vsl_tie_flag_off_regression", test_vsl_tie_flag_off_regression),
        ("vsl_tie_flag_on_no_ratchet", test_vsl_tie_flag_on_no_ratchet),
        ("vsl_tie_free_flow_invariant", test_vsl_tie_free_flow_invariant),
        ("vsl_tie_path_parity", test_vsl_tie_path_parity),
        ("prediction_plant_vsl_wiring", test_prediction_plant_vsl_wiring),
        ("zone4_smoke", lambda: test_zone4_smoke(tmp)),
        ("segvsl_control", lambda: test_segvsl_control(ctl_tmp)),
        ("no_zone_regression", lambda: test_no_zone_regression(reg_tmp)),
    ]
    results: list[tuple[str, list[str]]] = []
    for name, fn in tests:
        try:
            failures = fn()
        except Exception:
            failures = [f"예외 발생:\n{traceback.format_exc()}"]
        results.append((name, failures))
        status = "PASS" if not failures else "FAIL"
        print(f"[{status}] {name}")
        for failure in failures:
            print(f"    - {failure}")
    total_fail = sum(1 for _, f in results if f)
    print(f"\n{len(results) - total_fail}/{len(results)} PASS "
          f"(작업 디렉터리: {tmp}, {ctl_tmp}, {reg_tmp})")
    return 1 if total_fail else 0


if __name__ == "__main__":
    sys.exit(main())
