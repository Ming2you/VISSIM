#!/usr/bin/env python3
"""램프 결합 movement 를 유도해 낸다 — 생산 격자를 재생성하지 않고.

## 왜 이게 필요한가

생산 config(pedovrx)의 `off_ramp_to_movement` 와 `on_ramp_to_movement` 가 빈 dict 다.
그래서 vendor 의 `_drain_offramp_storage`(urban_queue_model.py:514)가 순회할 movement 가
없어 off-ramp 저류가 한 대도 못 빠지고, 용량 60 veh 를 향해 단조로 찬다(실측 스텝1/2/3 에
66.4 -> 131.2 -> 190.7 veh, 전체 모형 질량의 2.9% -> 6.7%).

원인 사슬:
  `urban_signal_selector: "core15"` + 생성기의 `--sc1-coupling auto` 규칙("core15 만 off")
  -> `build_network_override(include_freeway_interface_coupling=False)`
  -> `grid_node_legs` 에 ramp leg 가 안 심긴다(generate_..._players.py:536-542)
  -> `build_urban_movements` 가 ramp movement 를 만들지 않는다
  -> `NetworkConfig.__post_init__`(state.py:379-385)의 자동 유도가 채울 것이 없다
  -> 인덱스가 빈 채로 남는다

## 왜 재생성하지 않는가

생성 인자가 어디에도 기록돼 있지 않다. 추정 인자로 재생성해 보니 movement 가 542 대신
1184 개가 나왔다(경계 leg·비통제 집합·저류 라우팅이 전부 어긋남). 격자를 통째로 바꾸는
위험을 감수할 이유가 없다.

대신 결합이 실제로 하는 일 두 단계만 그대로 재현한다.
  1. `ramp_interface_sc` 대로 ramp leg 를 `grid_node_legs` 에 심는다
  2. vendor 의 **같은 함수**(`build_urban_movements`)로 movement 를 다시 유도한다
그러면 이름 규약이 어긋날 수 없고, 기존 542개는 그대로 나오며 차이는 ramp movement 뿐이다.
그 차이만 config 에 얹으면 `state.py` 가 인덱스를 자동으로 채운다.

산출물은 **주입할 movement 조각**이고, 이 스크립트는 생산 config 를 쓰지 않는다.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DEFAULT_CONFIG = REPO / "evaluation/configs/real_world_modi_pstack_distributed_pedovrx_20260814.json"
# 생성기 기본값과 같다(generate_real_world_distributed_players.py --ramp-interface-sc).
# D측은 SC1001, F측은 SC1004 — 실측 플랜트에 인터체인지가 둘이다.
DEFAULT_RAMP_INTERFACE = {"R_D_W": "SC1001", "R_D_E": "SC1001", "R_F_W": "SC1004", "R_F_E": "SC1004"}
RAMP_TO_FREEWAY = {"R_D_W": "FW_W", "R_F_W": "FW_W", "R_D_E": "FW_E", "R_F_E": "FW_E"}


def ensure_numsim() -> None:
    sys.path.insert(0, str(REPO / "evaluation" / "controllers"))
    import vissim_stackelberg_adapter as ad  # noqa: E402

    ad.repo_imports(Path(ad.DEFAULT_REPO_ROOT))


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)

    ensure_numsim()
    from src.models.grid_topology import build_urban_movements, derive_turning_ratios

    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    net = cfg["config_overrides"]["network"]
    legs = json.loads(json.dumps(net["grid_node_legs"]))  # 깊은 복사 - 원본 불변
    signals = list(net.get("signals") or [])
    existing = net.get("urban_movements") or {}

    # 1) 결합 없이 한 번 — 우리 재현이 생산과 같은지 먼저 확인한다. 여기서 어긋나면
    #    아래 결과도 못 믿으므로 즉시 중단한다.
    ratios_before = derive_turning_ratios(legs)
    before = build_urban_movements(legs, ratios_before, signals, RAMP_TO_FREEWAY)

    # 2) ramp leg 를 심는다 (generate_real_world_distributed_players.py:536-542 와 동일)
    ramp_legs: dict[str, dict[str, Any]] = {}
    for ramp, sid in DEFAULT_RAMP_INTERFACE.items():
        side = ramp.rsplit("_", 1)[-1]
        off_ramp = "OR_" + ramp[2:]
        spec = ramp_legs.setdefault(sid, {"type": "ramp", "on": {}, "off": {}})
        spec["on"][side] = ramp
        spec["off"][side] = off_ramp
    missing = sorted(set(ramp_legs) - set(legs))
    if missing:
        print(f"ERROR 인터페이스 SC 가 grid_node_legs 에 없다: {missing}")
        return 2
    for sid, spec in ramp_legs.items():
        legs[sid]["ramp"] = spec

    ratios_after = derive_turning_ratios(legs)
    after = build_urban_movements(legs, ratios_after, signals, RAMP_TO_FREEWAY)

    added = {k: v for k, v in after.items() if k not in before}
    removed = sorted(set(before) - set(after))
    changed = sorted(k for k in set(before) & set(after) if before[k] != after[k])

    print(f"config movement          {len(existing)}")
    print(f"결합 없이 재유도          {len(before)}   (생산과 같아야 한다)")
    print(f"결합 켜고 재유도          {len(after)}")
    print(f"  추가 {len(added)}   제거 {len(removed)}   변경 {len(changed)}")

    # 재현 검증 — 결합 없이 유도한 집합이 생산 config 와 이름 단위로 같아야 한다.
    only_cfg = sorted(set(existing) - set(before))
    only_der = sorted(set(before) - set(existing))
    ok = not only_cfg and not only_der
    print(f"\n재현 검증: {'통과' if ok else '실패'}")
    if not ok:
        print(f"  config 에만 {len(only_cfg)}개: {only_cfg[:6]}")
        print(f"  유도에만  {len(only_der)}개: {only_der[:6]}")
        print("  -> 유도 경로가 생산과 다르다. 주입하면 안 된다.")
        return 2
    # 기존 movement 가 **제거**되면 안 된다. 변경은 예상된다 - ramp leg 가 생기면 그 교차로의
    # 회전율이 재배분되므로 인터페이스 SC 의 β 가 바뀐다. 다만 그 변경이 인터페이스 SC 밖으로
    # 새면 결합이 아닌 다른 것을 건드린 것이므로 끊는다.
    if removed:
        print(f"  ERROR 결합이 기존 movement 를 제거한다 ({len(removed)}개): {removed[:6]}")
        return 2
    interface = set(DEFAULT_RAMP_INTERFACE.values())
    leaked = [k for k in changed if str((after[k] or {}).get("signal", "")) not in interface]
    if leaked:
        print(f"  ERROR 변경이 인터페이스 SC({sorted(interface)}) 밖으로 샌다: {leaked[:8]}")
        return 2
    if changed:
        print(f"\n인터페이스 SC 에서 β 가 바뀌는 기존 movement {len(changed)}개 (예상된 재배분):")
        for k in changed[:8]:
            print(f"  {k:46s} beta {before[k].get('beta')} -> {after[k].get('beta')}")

    import collections

    kinds = collections.Counter(str((s or {}).get("kind", "")) for s in added.values())
    print(f"\n추가된 movement 종류: {dict(kinds)}")
    for name, spec in list(added.items())[:10]:
        print(f"  {name:44s} kind={spec.get('kind')!r} ramp={spec.get('ramp')!r} "
              f"off_ramp={spec.get('off_ramp')!r} recv={spec.get('receiving_link')!r} beta={spec.get('beta')}")

    payload = {
        "schema_version": "ramp-coupling-movements-v1",
        "source_config": str(args.config.relative_to(REPO)).replace("\\", "/"),
        "ramp_interface_sc": DEFAULT_RAMP_INTERFACE,
        "reproduction_check": {
            "config_movements": len(existing),
            "derived_without_coupling": len(before),
            "names_identical": ok,
        },
        "added_movements": added,
        "changed_movements": {k: after[k] for k in changed},
        "changed_movements_before": {k: before[k] for k in changed},
        "note": "config_overrides.network.urban_movements 에 added + changed 를 합치면 "
                "state.py:379-385 가 on/off_ramp_to_movement 인덱스를 자동으로 채운다. "
                "changed 는 인터페이스 SC 의 회전율 재배분이라 결합의 일부이지 부작용이 아니다.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8", newline="\n")
    print(f"\n기록: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
