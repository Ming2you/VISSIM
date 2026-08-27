# -*- coding: utf-8 -*-
"""정본 파라미터 단일 출처. 값은 `evaluation/parameters.json` 에만 있다.

왜 이 모듈이 있나. 2026-08-27 까지 같은 값을 여러 곳에서 따로 정하다가 실효값이
의도와 달라지는 사고가 반복됐다.

  leader_value_depth  config 에 3 을 넣으면 리더 롤아웃 깊이가 3 이 아니라 3+3=6 이 됐다.
                      `horizon_steps` 는 3 인데 파생식이 다른 곳에 있었다.
  FD 3종             `build_config` 가 123.825/20.401/4574.818 을 넣은 뒤,
                      `calibration_to_config_overrides` 가 "키 없으면 상수" 폴백으로
                      100/33.5/4000 을 덮었다. 재적합값 119.505/16.354/4914 는 도달한 적이 없다.
                      실측 밀도 최대가 32.7 이라 rho_crit 33.5 를 한 번도 못 넘었고,
                      그래서 VSL 이 켜질 수 없었다.

규칙 셋.
  1. 값은 parameters.json 에만 쓴다. 코드에 상수를 박지 않는다.
  2. 없는 키는 **예외를 낸다**. 조용한 폴백이 위 사고의 공통 원인이다.
  3. 파생량은 여기 함수로만 계산한다. 같은 식을 두 곳에 쓰지 않는다.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

PARAMS_PATH = Path(__file__).resolve().parent / "parameters.json"

_CACHE: dict[str, Any] | None = None


class ParameterMissing(KeyError):
    """폴백하지 않는다. 키가 없으면 여기서 멈춘다."""


def load(force: bool = False) -> dict[str, Any]:
    global _CACHE
    if _CACHE is None or force:
        _CACHE = json.loads(PARAMS_PATH.read_text(encoding="utf-8"))
    return _CACHE


def require(section: str, key: str) -> Any:
    """값을 읽는다. 없으면 예외. **기본값 인자를 일부러 두지 않았다.**"""
    doc = load()
    sec = doc.get(section)
    if not isinstance(sec, Mapping):
        raise ParameterMissing("parameters.json 에 '%s' 절이 없다" % section)
    if key not in sec:
        raise ParameterMissing(
            "parameters.json['%s']['%s'] 가 없다. 코드에 폴백을 넣지 말고 "
            "parameters.json 에 값을 적어라." % (section, key))
    return sec[key]


def section(name: str) -> dict[str, Any]:
    """한 절 전체를 dict 로. `_` 로 시작하는 주석 키는 뺀다."""
    doc = load()
    sec = doc.get(name)
    if not isinstance(sec, Mapping):
        raise ParameterMissing("parameters.json 에 '%s' 절이 없다" % name)
    return {k: v for k, v in sec.items() if not str(k).startswith("_")}


# ---------------------------------------------------------------- 파생량
# 같은 식을 두 곳에 쓰지 않기 위한 자리. 읽는 쪽은 전부 여기를 부른다.

def leader_rollout_depth(cfg=None) -> int:
    """리더가 실제로 굴리는 제어스텝 수.

    `rollout_endpoint.py:188` 이 쓰는 식과 같아야 한다 —
    depth = horizon_steps + max(0, leader_value_depth).
    follower 는 `depth_override=horizon_steps` 만 쓰므로 둘이 다를 수 있고,
    그 차이가 2026-08-27 이전의 '지평 3인 줄 알았는데 6' 사고였다.
    """
    if cfg is not None:
        h = int(getattr(cfg.mpc, "horizon_steps"))
        d = int(getattr(cfg.mpc, "leader_value_depth", 0))
    else:
        h = int(require("mpc", "horizon_steps"))
        d = int(require("mpc", "leader_value_depth"))
    return h + max(0, d)


def follower_rollout_depth(cfg=None) -> int:
    """follower 가 굴리는 제어스텝 수. 리더와 같은지 항상 확인할 수 있게 짝으로 둔다."""
    if cfg is not None:
        return int(getattr(cfg.mpc, "horizon_steps"))
    return int(require("mpc", "horizon_steps"))


def phase_green_max(signal_green_total: float, live_phase_count: int) -> float:
    """현시 하나가 가질 수 있는 최대 녹색.

    = 신호 녹색예산 - (살아있는 현시 - 1) x green_min.
    150초 4현시면 138 - 3x20 = 78 이고, 이것이 '녹색상한 78' 의 정체다.
    전역 상수가 아니라 신호별로 다르다(SC107 은 141 - 2x20 = 101).
    """
    gmin = float(require("network", "green_min"))
    return max(gmin, float(signal_green_total) - max(0, int(live_phase_count) - 1) * gmin)


def urban_occupancy(state, cfg, storage_link: str) -> float:
    """저류 점유[veh]. `urban_link_storage` 는 **빈 공간**이라 용량에서 빼야 한다.

    `capacity - urban_link_storage` 식이 코드 10곳에 흩어져 있어 부호를 뒤집어 읽는
    사고가 났다(2026-08-27). 읽는 쪽은 이 함수를 쓴다.
    """
    cap = float(cfg.network.urban_link_storage_veh.get(storage_link, 0.0))
    free = float(state.urban_link_storage.get(storage_link, cap))
    return max(0.0, cap - free)


def effective_green_total(cfg=None) -> float:
    """신호 하나의 녹색 예산[초] = cycle_length - lost_time.

    값으로 중복 저장하지 않는다. 종전에는 이 파생량이 config 에도 있고 코드에도 있어
    갈릴 여지가 있었다. `state.py:462·535` 와 `urban_queue_model.py:677` 이 같은 식을
    각자 계산한다 — 읽는 쪽은 여기를 부른다.
    """
    if cfg is not None:
        return float(cfg.network.cycle_length) - float(cfg.network.lost_time)
    return float(require("network", "cycle_length")) - float(require("network", "lost_time"))


def default_phase_green(cfg=None, num_phases: int | None = None) -> float:
    """현시 하나의 기본 녹색[초] = effective_green_total / 현시 수."""
    n = int(num_phases if num_phases is not None
            else getattr(getattr(cfg, "network", None), "num_phases", 4))
    return effective_green_total(cfg) / max(1, n)


def runtime_overrides() -> dict[str, dict[str, Any]]:
    """생성자 필드가 아니라 cfg 구성 **뒤에** setattr 로 붙일 것들."""
    doc = load()
    rt = doc.get("runtime")
    if not isinstance(rt, Mapping):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for sec, block in rt.items():
        if str(sec).startswith("_") or not isinstance(block, Mapping):
            continue
        vals = {k: v for k, v in block.items() if not str(k).startswith("_")}
        if vals:
            out[sec] = vals
    return out


def apply_runtime(cfg) -> dict[str, Any]:
    """runtime 절을 cfg 에 심는다. 심은 것을 돌려준다(진단용)."""
    applied: dict[str, Any] = {}
    for sec, block in runtime_overrides().items():
        obj = getattr(cfg, sec, None)
        if obj is None:
            continue
        for k, v in block.items():
            setattr(obj, k, v)
            applied["%s.%s" % (sec, k)] = v
    return applied


def network_overrides() -> dict[str, Any]:
    """`build_config` 에 넣을 network 블록. 폴백 없음 — 전부 parameters.json 에서."""
    return section("network")


def mpc_overrides() -> dict[str, Any]:
    """`build_config` 에 넣을 mpc 블록. 폴백 없음."""
    return section("mpc")


def audit_against(cfg) -> list[str]:
    """실효 cfg 가 parameters.json 과 어긋나면 목록으로 돌려준다. 빈 목록이면 일치."""
    bad = []
    for sec_name, obj in (("network", cfg.network), ("mpc", cfg.mpc)):
        for k, want in section(sec_name).items():
            if not hasattr(obj, k):
                continue
            got = getattr(obj, k)
            if isinstance(want, bool) or isinstance(got, bool):
                ok = bool(want) == bool(got)
            elif isinstance(want, (int, float)) and isinstance(got, (int, float)):
                ok = abs(float(want) - float(got)) <= 1e-9
            else:
                ok = want == got
            if not ok:
                bad.append("%s.%s: parameters=%r 실효=%r" % (sec_name, k, want, got))
    return bad
