# 러너(VBS)가 실제로 합성하는 주기와 모델 주기를 같은 식으로 묶는 계산기 (v3 N4-5 잔여)
"""모델 주기와 플랜트 주기는 **같은 항등식**인데 상수 하나가 다르다.

    모델   cycle_length      == green_p1 + green_p2 + lost_time
           (`src/evaluation/metrics.py:242`, `controllers/classical_hierarchical.py:233`
            이 이미 이 항등식을 위반 카운트로 재고 있다. 즉 모델의 주기는 자유
            파라미터가 아니라 녹색 예산 + lost_time 으로 결정된 값이다.)

    플랜트 cycle             == major + AMBER_SEC + ALL_RED_SEC
                                + minor + AMBER_SEC + ALL_RED_SEC
           (`scripts/run_real_world_stackelberg_controller.vbs:764`)

`major`/`minor` 는 어댑터가 모델의 `green_p2`/`green_p1` 을 그대로 실은 값이므로
(`vissim_stackelberg_adapter.py:5120-5123`), 두 식의 차이는 정확히

    lost_time  대  2 x (AMBER_SEC + ALL_RED_SEC)

하나뿐이다. 그래서 `cycle_length_by_signal` 에 native 주기를 채우는 것으로는 이 간극이
닫히지 않는다 — 애초에 native 주기는 제어 런에서 재생되지 않는다. 러너는 제어 15 SC 의
모든 SG 에 `ContrByCOM = True` 를 걸어(:1402) inpx 프로그램을 통째로 우회하고, 위 식으로
합성한 주기를 매초 COM 으로 밀어 넣는다.

이 모듈은 그 상수를 **러너 원문에서 읽어** 한 곳에 모은다. 숫자를 복사해 두면 러너가
바뀌었을 때 조용히 어긋난다.
"""

from __future__ import annotations

import re
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
RUNNER_VBS = WORKSPACE_ROOT / "scripts" / "run_real_world_stackelberg_controller.vbs"

# 어댑터가 `signal` 행에 major/minor 를 쓸 때 거는 안전 클램프.
# 모델의 [green_min, green_max] 가 이 밖으로 나가면 플랜트가 지시받은 녹색을 그대로
# 재생하지 못하고, 그만큼 플랜트 주기가 모델 주기보다 짧아진다.
SIGNAL_GREEN_WRITE_CLAMP_SEC = (5.0, 90.0)


class RunnerConstantMissing(RuntimeError):
    """러너 원문에서 clearance 상수를 못 찾았다."""


def _const_from_runner(name: str, vbs_path: Path | None = None) -> float:
    source = Path(vbs_path) if vbs_path is not None else RUNNER_VBS
    text = source.read_text(encoding="utf-8", errors="replace")
    found = re.search(rf"^Const\s+{re.escape(name)}\s*=\s*([0-9]+(?:\.[0-9]+)?)\s*$",
                      text, flags=re.MULTILINE)
    if found is None:
        raise RunnerConstantMissing(f"{source.name} 에 Const {name} 이 없다")
    return float(found.group(1))


def runner_clearance_sec(vbs_path: Path | None = None) -> tuple[float, float]:
    """러너의 (amber, all_red) [s]."""
    return (
        _const_from_runner("AMBER_SEC", vbs_path),
        _const_from_runner("ALL_RED_SEC", vbs_path),
    )


def plant_lost_time_sec(vbs_path: Path | None = None) -> float:
    """플랜트가 한 주기에서 녹색이 아닌 채로 쓰는 시간 [s] = 2 x (amber + all_red).

    모델의 `network.lost_time` 이 이 값과 같아야 두 주기가 같아진다.
    """
    amber, all_red = runner_clearance_sec(vbs_path)
    return 2.0 * (amber + all_red)


def written_axis_green_sec(green_sec: float) -> float:
    """어댑터가 action CSV 에 실제로 싣는 축 녹색 [s] (클램프 적용 후)."""
    low, high = SIGNAL_GREEN_WRITE_CLAMP_SEC
    return min(max(float(green_sec), low), high)


def plant_cycle_sec(p1_green_sec: float, p2_green_sec: float,
                    vbs_path: Path | None = None) -> float:
    """모델 녹색 (p1, p2) 를 지시했을 때 러너가 재생하는 주기 [s].

    어댑터는 major <- p2, minor <- p1 로 싣는다. 축 대응(major_maps_to)이 뒤집힌
    교차로도 두 값의 **합**은 같으므로 주기는 축 대응과 무관하다.
    """
    return (
        written_axis_green_sec(p2_green_sec)
        + written_axis_green_sec(p1_green_sec)
        + plant_lost_time_sec(vbs_path)
    )


def leader_green_box(net) -> list[tuple[float, float]]:
    """리더가 고를 수 있는 (p1, p2) 중 **극값이 잡히는 점 전부**.

    `distributed_coordinator._bounded_leader_green` 의 사영과 같은 규칙이다 —
    p1 을 [green_min, green_max] 로 자른 뒤 p2 = total - p1 이 상자를 벗어나면
    p2 를 자르고 p1 을 되돌린다.

    `plant_cycle_sec` 은 p1 의 조각별 선형 함수다(예산면에서 p2 = total - p1).
    꺾이는 곳은 상자 끝과 **write clamp 경계** 뿐이므로, 그 점들만 보면 최댓값·
    최솟값이 정확히 잡힌다. 상자 끝만 보면 클램프가 상자 안쪽에서 물 때를 놓친다.
    """
    total = float(net.effective_green_total)
    g_min = float(net.green_min)
    g_max = float(net.green_max)
    clamp_low, clamp_high = SIGNAL_GREEN_WRITE_CLAMP_SEC
    breakpoints = (
        g_min, g_max, total / 2.0, total - g_min, total - g_max,
        clamp_low, clamp_high, total - clamp_low, total - clamp_high,
    )
    out: list[tuple[float, float]] = []
    for raw in breakpoints:
        p1 = min(max(float(raw), g_min), g_max)
        p2 = total - p1
        if p2 < g_min:
            p2 = g_min
            p1 = total - p2
        if p2 > g_max:
            p2 = g_max
            p1 = total - p2
        out.append((p1, p2))
    return out


def cycle_disagreement_sec(net, vbs_path: Path | None = None) -> float:
    """리더 액션 상자 전체에서 |플랜트 주기 - 모델 주기| 의 최댓값 [s]. 0 이어야 한다."""
    model_cycle = float(net.cycle_length)
    return max(
        abs(plant_cycle_sec(p1, p2, vbs_path) - model_cycle)
        for p1, p2 in leader_green_box(net)
    )


def green_fraction_overestimate(net, vbs_path: Path | None = None) -> float:
    """모델이 g/C 를 얼마나 과대평가하는지의 최댓값 (비율).

    모델은 g/`cycle_length`, 플랜트는 g/`plant_cycle_sec` 이므로 같은 g 에 대해
    비는 plant_cycle / model_cycle - 1 이다.
    """
    model_cycle = float(net.cycle_length)
    return max(
        plant_cycle_sec(p1, p2, vbs_path) / model_cycle - 1.0
        for p1, p2 in leader_green_box(net)
    )
