# -*- coding: utf-8 -*-
"""이 런에서 **실제로 살아 있는** 컨트롤러 구성을 찍는다. 추론하지 말고 이걸 돌려라.

왜 있나
-------
2026-08-20 하루에만 구성을 여섯 번 오독했다. 코드를 읽고 추론했기 때문이다.

  green_sec 을 녹색 길이로 읽음        실제로는 플랜 주기 (CSV 컬럼 재사용)
  현시 녹색과 SG 창을 맞댐              SG 는 현시 일부만 녹색인 설계가 있다
  flagship=True 로 오프라인 검증        실런은 -Controller stackelberg -> flagship=False
  N_P 를 누적량으로 읽음                horizon 순유입[veh] 이다
  450초 예측과 900초 실측을 맞댐        창이 달랐다
  가격이 어느 컨트롤러에 있는지         분산 팔엔 없고 flagship 팔에만 있다

저장소에 컨트롤러가 27개 있고 게이트가 층층이라, 한 자리만 잘못 봐도 결론이 뒤집힌다.
**작업 전에 이걸 먼저 돌린다.** 삭제 대신 이 도구를 두기로 한 이유다 — vendor 파일을
지우면 앵커의 `anchor_python_file_set`(121개 핀)이 깨지고, 삭제는 `local_patches`
스키마로 표현할 수도 없다(`patched_blob` 이 40-hex OID 를 요구한다).

쓰는 법
-------
러너에 넘기는 것과 **같은 인자**로 부른다.

    python scripts/resolve_live_controller.py \
        --tuning evaluation/configs/real_world_modi_pstack_distributed_core17legs4b_20260819.json \
        --controller stackelberg

`--controller` 가 `flagship` 분기를 정한다(`flagship = controller == "pstack-flagship"`).
이 한 글자가 leader_value_depth 를 0 과 3 으로 가른다.
"""
from __future__ import annotations

import argparse
import collections
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NUMSIM = ROOT / "vendor" / "NumSim-mine"

# 2026-08-27. 종전 기본값(core17legs4b_20260819)은 정본 통합 때 격리됐다. 없는 경로를
# 넘기면 load_optional_json 이 조용히 {} 를 돌려주므로, 이 해석기가 config 를 읽은 것처럼
# 헤더에 파일명을 찍으면서 실제로는 base+flagship 합성망(신호 5개)을 "살아 있는 구성"으로
# 인쇄했다. 이 도구의 존재 이유가 바로 그런 오독을 막는 것이라 특히 나쁘다.
DEFAULT_TUNING = ROOT / "evaluation/configs/canon_plantfix_20260827.json"
DEFAULT_CALIBRATION = ROOT / "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json"

# `build_pstack_flagship_controller` 가 코드로 켜는 값(adapter:2601~). config 가 아니라
# 빌더 안에 있으므로 cfg 만 봐서는 안 보인다. 여기 옮겨 적고 출처를 같이 찍는다.
FLAGSHIP_PRICE_FLAGS = {
    "signal_price_enabled": True,
    "metering_price_enabled": True,
    "vsl_price_enabled": True,
    "offset_price_enabled": True,
    "green_offset_cross_price_enabled": False,
    "vsl_meter_cross_price_enabled": False,
    "price_far_enabled": False,
    "price_hinge_enabled": False,
}
# `StackelbergWuMeteredController.__init__` 클래스 기본값.
WU_CLASS_PRICE_DEFAULTS = {
    "signal_price_enabled": True,
    "metering_price_enabled": False,
    "vsl_price_enabled": False,
    "offset_price_enabled": False,
    "green_offset_cross_price_enabled": False,
    "vsl_meter_cross_price_enabled": False,
    "price_far_enabled": False,
    "price_hinge_enabled": False,
}


def _load_adapter():
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(NUMSIM))
    spec = importlib.util.spec_from_file_location(
        "vsa", ROOT / "evaluation/controllers/vissim_stackelberg_adapter.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _unused_controllers(reachable_seeds: list[str]) -> tuple[list[str], dict[str, list[str]]]:
    """이 팔에서 import 로 도달하지 않는 controllers/ 파일과, 그것을 쓰는 바깥 참조."""
    cdir = NUMSIM / "src" / "controllers"
    files = {p.name: p.read_text(encoding="utf-8") for p in cdir.glob("*.py")}
    edges: dict[str, set[str]] = collections.defaultdict(set)
    for name, src in files.items():
        for m in re.finditer(r"from\s+src\.controllers\.(\w+)\s+import|import\s+src\.controllers\.(\w+)", src):
            target = (m.group(1) or m.group(2)) + ".py"
            if target in files:
                edges[name].add(target)
    seen: set[str] = set()
    stack = [s for s in reachable_seeds if s in files]
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        stack.extend(edges.get(cur, ()))
    unused = sorted(set(files) - seen - {"__init__.py"})

    outside: dict[str, list[str]] = {}
    roots = [NUMSIM / "src", ROOT / "evaluation", ROOT / "scripts"]
    for name in unused:
        stem = name[:-3]
        hits = []
        for root in roots:
            for p in root.rglob("*.py"):
                if p.name == name or "_archive" in p.as_posix():
                    continue
                try:
                    if f"controllers.{stem}" in p.read_text(encoding="utf-8"):
                        hits.append(p.relative_to(ROOT).as_posix())
                except (OSError, UnicodeError):
                    continue
        outside[name] = sorted(hits)[:4]
    return unused, outside


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--tuning", type=Path, default=DEFAULT_TUNING)
    ap.add_argument("--calibration", type=Path, default=DEFAULT_CALIBRATION)
    ap.add_argument("--controller", default="stackelberg",
                    help="러너의 -Controller 와 같은 값. pstack-flagship 이면 flagship 분기")
    ap.add_argument("--control-interval-sec", type=float, default=150.0)
    ap.add_argument("--sim-period-sec", type=float, default=1800.0)
    ap.add_argument("--local-observation", type=int, default=1)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    vsa = _load_adapter()
    flagship = args.controller in ("pstack-flagship", "wu-link")
    if not Path(args.tuning).exists():
        raise SystemExit(
            "!! tuning 을 못 읽었다: %s"
            "  —  빈 dict 로 진행하면 base+flagship 합성망(신호 5개)을 '살아 있는 구성'으로"
            " 인쇄한다. 정본: evaluation/configs/canon_{tau,bstoA,plantfix,fdfit}_20260827.json"
            % args.tuning)
    tuning = vsa.load_optional_json(str(args.tuning))
    calibration = vsa.load_optional_json(str(args.calibration))
    cfg = vsa.build_config(
        NUMSIM, args.control_interval_sec, args.sim_period_sec, "stackelberg",
        calibration, tuning, local_observation=bool(args.local_observation), flagship=flagship,
    )

    from src.controllers.distributed_coordinator import build_agent_specs  # noqa: E402

    mode = str(getattr(cfg.mpc, "follower_solver_mode", "?"))
    if args.controller == "wu-link":
        controller_cls = "PricedWuLinkStackelbergController"
        follower_cls = "LinkAgentWuFollower (WuFaithfulFollower · segment_agents=False)"
        seeds = ["priced_wu_link_controller.py"]
        price = dict(FLAGSHIP_PRICE_FLAGS)
        price_src = "build_priced_wu_link_controller (코드 주입)"
    elif flagship:
        controller_cls, follower_cls = "F1StackelbergWuMeteredController", "WuFaithfulFollower"
        seeds = ["f1_wu_faithful_follower.py", "stackelberg_wu_metered.py"]
        price = dict(FLAGSHIP_PRICE_FLAGS)
        price_src = "build_pstack_flagship_controller (코드 주입)"
    else:
        controller_cls = "StackelbergMPCController"
        follower_cls = "DistributedCoordinator" if mode == "distributed" else "NashSolver"
        seeds = ["stackelberg_mpc.py", "distributed_coordinator.py"]
        price = {k: False for k in WU_CLASS_PRICE_DEFAULTS}
        price_src = "해당 없음 — 이 팔에 가격 채널이 없다"

    net = cfg.network
    if follower_cls.startswith(("WuFaithfulFollower", "LinkAgentWuFollower")):
        # wu 팔로워는 자기 agent 목록을 따로 갖는다 — build_agent_specs 는 분산 코디네이터 것이다.
        class _A:
            def __init__(self, i): self.id = i
        seg = follower_cls.endswith("segment_agents=False)") is False
        urban = [_A(f"U_{s}") for s in net.signals]
        freeway = (
            [_A(f"F_{l.split('_')[-1]}{i}") for l in net.freeway_links
             for i in range(net.freeway_segments_per_link)]
            if (flagship and args.controller == "pstack-flagship")
            else [_A(f"F_{l.split('_')[-1]}") for l in net.freeway_links]
        )
    else:
        urban, freeway = build_agent_specs(cfg)
    live_phases = sum(
        1 for sig in net.signals
        for ph in range(1, 5)
        if True
    )

    lines: list[str] = []
    def p(text: str = "") -> None:
        lines.append(text)
        print(text)

    p(f"=== 살아 있는 구성 · tuning={args.tuning.name} · --controller {args.controller} ===")
    p(f"  flagship 분기        {flagship}   (leader_value_depth 를 가르는 자리)")
    p()
    p("--- 컨트롤러 ---")
    p(f"  리더                 {controller_cls}")
    p(f"  팔로워               {follower_cls}   (follower_solver_mode={mode})")
    p()
    p("--- player ---")
    p(f"  도시 agent           {len(urban):3d}   {', '.join(a.id for a in urban[:6])}{' …' if len(urban) > 6 else ''}")
    p(f"  고속 agent           {len(freeway):3d}   {', '.join(a.id for a in freeway[:8])}{' …' if len(freeway) > 8 else ''}")
    _gran = (
        ("segment" if args.controller == "pstack-flagship" else "link")
        + "  (wu: segment_agents 스위치)"
        if follower_cls.startswith(("WuFaithfulFollower", "LinkAgentWuFollower"))
        else str(getattr(cfg.mpc, "freeway_agent_granularity", "segment"))
        + "  (분산: freeway_agent_granularity)"
    )
    p(f"  freeway 입도         {_gran}")
    p("                       agent 분할만 바꾼다 — plant 모델은 불변")
    p(f"  freeway 셀           {len(net.freeway_links)} 링크 x {net.freeway_segments_per_link} 세그먼트 = "
      f"{len(net.freeway_links) * net.freeway_segments_per_link}   <- 롤아웃이 굴리는 것")
    p()
    p("--- 레버 ---")
    p(f"  신호                 {len(net.signals)}  (현시 4 -> green 자유도 {len(net.signals) * 4})")
    p(f"  offset               {len(net.signals)}")
    p(f"  VSL                  {len(net.freeway_links)}  (링크당 1개)")
    p(f"  ramp metering        {len(net.ramps)}   총용량 {net.total_ramp_capacity:.0f} veh/h")
    p()
    p("--- budget ---")
    p(f"  N_P_star_range       {cfg.leader.N_P_star_range}   [veh · horizon 순유입]")
    p(f"  N_UF_star_range      {cfg.leader.N_UF_star_range}   [veh/h · 램프 미터링 합]")
    p(f"  N_P_crit_veh         {cfg.leader.N_P_crit_veh}")
    p()
    p(f"--- 가격 채널  ({price_src}) ---")
    for key, value in price.items():
        p(f"  {key:36s} {'ON' if value else 'off'}")
    p(f"  {'λ_P (np_price_enabled)':36s} {'ON' if flagship else 'off'}")
    p(f"  {'λ_UF (nuf_coordination_mode)':36s} "
      f"{str(getattr(cfg.mpc, 'wu_faithful_nuf_coordination_mode', 'equality'))}"
      f"   (equality=hard 등식 · dual=듀얼가격)")
    p()
    p("--- 게이트 ---")
    for key, label in (
        ("stackelberg_enable_fallback", "폴백(PFO/no_control)"),
        ("stackelberg_allocation_mode", "allocation 모드"),
        ("stackelberg_prefilter_top_k", "프리필터 top_k(global)"),
        ("stackelberg_prefilter_local_top_k", "프리필터 top_k(local)"),
        ("horizon_steps", "롤아웃 스텝"),
        ("leader_value_depth", "leader_value_depth"),
        ("leader_mfd_far_at_d0", "far @ 리더 채점"),
        ("leader_mfd_far_enabled", "far 전역 스위치"),
        ("distributed_rollout_far_enabled", "far @ 팔로워 그리드"),
        ("max_nash_iter", "Nash 반복"),
    ):
        p(f"  {label:28s} {getattr(cfg.mpc, key, '(미설정)')}")
    p()
    p("--- 리더 목적함수 가중치 ---")
    for key in ("objective_mode", "mfd_penalty_mode", "w_P", "mfd_storage_weight",
                "w_F", "w_ramp_queue", "w_boundary_in"):
        p(f"  {key:28s} {getattr(cfg.leader, key, '(미설정)')}")
    p()

    unused, outside = _unused_controllers(seeds)
    p(f"--- 이 팔이 import 로 닿지 않는 controllers/ 파일 {len(unused)}개 ---")
    for name in unused:
        refs = outside.get(name) or []
        tail = ("바깥 참조: " + ", ".join(refs)) if refs else "**바깥 참조 없음**"
        p(f"  {name:34s} {tail}")
    p("  (지우지 마라 — vendor 삭제는 앵커의 anchor_python_file_set 121개 핀을 깬다)")

    if args.out:
        out = args.out if args.out.is_absolute() else ROOT / args.out
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\n-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
