# 러너(VBS)가 실제로 합성하는 주기와 모델 주기를 같은 식으로 묶는 계산기 (v3 N4-5 / N4-0)
"""모델 주기와 플랜트 주기는 **같은 항등식**인데 상수 하나가 다르다.

    모델   cycle_length      == Σ(현시 녹색) + lost_time
           (`src/evaluation/metrics.py:242`, `controllers/classical_hierarchical.py:233`
            이 이미 이 항등식을 위반 카운트로 재고 있다. 즉 모델의 주기는 자유
            파라미터가 아니라 녹색 예산 + lost_time 으로 결정된 값이다.)

    플랜트 cycle             == Σ(녹색 있는 현시의 녹색) + (녹색 있는 현시 수) x clearance
           (`scripts/run_real_world_stackelberg_controller.vbs:800` 의
            `SignalCycleFromPhases` = `PhaseGreenSum + LivePhaseCount x (AMBER+ALL_RED)`)

## clearance 계수는 상수가 아니다 — 현시 수다 (N4-0)

v3 은 축이 둘이라 러너가 축 경계에서만 전이했고, 그래서 계수가 늘 2 였다. N4-0 이
dual-ring 4현시로 가면서 축 **안의** 현시 경계도 전이가 됐다. 러너는 이미 그렇게
세고 있다(`LivePhaseCount`). 그러므로 이 모듈도 2 를 박아두면 안 된다.

    N = 4  ->  lost_time 12,  effective 138,  green_max 78
    N = 3  ->  lost_time  9,  effective 141,  green_max 101

**N 은 SC 마다 다르다.** "현시는 그 현시에 녹색을 받는 SG 가 있을 때만 존재한다" 는
유도 규칙 때문이다. 실 `.sig` 15개에서 영구적색 SG 20개가 현시를 지워 SC107·108·109 만
N=3 이 된다(`scripts/build_dual_ring_signal_programs.py` 실측). 그래서 SC별 N 을 다루는
자리를 `plan_live_phase_counts` / `model_effective_green_sec` 로 열어 둔다.

`major`/`minor` 는 어댑터가 모델의 현시 녹색을 그대로 실은 값이므로
(`vissim_stackelberg_adapter.py:5192-5201`), 두 식의 차이는 정확히

    lost_time  대  N x (AMBER_SEC + ALL_RED_SEC)

하나뿐이다. 그래서 `cycle_length_by_signal` 에 native 주기를 채우는 것으로는 이 간극이
닫히지 않는다 — 애초에 native 주기는 제어 런에서 재생되지 않는다. 러너는 제어 15 SC 의
모든 SG 에 `ContrByCOM = True` 를 걸어(:1402) inpx 프로그램을 통째로 우회하고, 위 식으로
합성한 주기를 매초 COM 으로 밀어 넣는다.

이 모듈은 그 상수를 **러너 원문에서 읽어** 한 곳에 모은다. 숫자를 복사해 두면 러너가
바뀌었을 때 조용히 어긋난다.

## 녹색 예산 계약 — 다섯 값 중 자유 파라미터는 셋뿐이다

    자유  cycle_length  플랜트가 한 주기에 쓰는 시간 [s]
    자유  lost_time     = 현시 수 x (AMBER_SEC + ALL_RED_SEC). 러너 원문이 정한다
    자유  green_min     현시 하나에 보장하는 최소 녹색 [s]

    유도  effective_green_total = cycle_length - lost_time     (state.py:400)
    유도  green_max             = effective_green_total - (N-1) x green_min

`green_max` 가 유도값인 이유는 컨트롤러가 예외 없이 예산 전체를 나눠 쓰기 때문이다
(`distribute_phase_green`, `allocate_phase_green`, distributed_coordinator:1256, ...).
한 현시를 끝까지 밀면 나머지 (N-1) 현시가 각각 `green_min` 에 앉아야 하므로

    green_min x (N-1) + green_max == effective_green_total

이 성립해야 상자 양끝이 서로의 거울상이다. 합이 total 보다 크면 `green_max` 가, 작으면
`green_min` 이 절대 도달할 수 없는 죽은 상한/하한이 된다.

`green_box_residual_sec` 이 그 어긋남을 초 단위로 잰다. 0 이 계약이다.
N=2 에서는 `green_min + green_max == total` 이라 v3 규칙과 정확히 같다.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping

from evaluation.controllers import signal_group_plan

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
RUNNER_VBS = WORKSPACE_ROOT / "scripts" / "run_real_world_stackelberg_controller.vbs"

# 모델이 들고 있는 현시 어휘의 크기. 상류(`NumSim-mine/src/models/state.py:MODEL_PHASES`)와
# 어댑터(`signal_group_plan.MODEL_PHASES`)가 같은 튜플을 쓰므로 여기서 따로 세지 않는다.
MODEL_PHASE_COUNT = len(signal_group_plan.MODEL_PHASES)

# N4-0 목표 주기 [s] (계획서 커밋 9fa2668 · 0b6f3c3, 사용자 확정).
# `scripts/survey_signal_programs.TARGET_CYCLE_SEC` 와 같은 값이어야 한다 - 그쪽은
# `.sig` 를 재작성할 때 쓰고, 여기서는 모델 예산을 유도할 때 쓴다.
TARGET_CYCLE_SEC = 150.0

# 어댑터가 `signal` 행에 현시 녹색을 쓸 때 거는 안전 클램프.
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


def clearance_sec(vbs_path: Path | None = None) -> float:
    """전이 하나가 태우는 시간 [s] = amber + all_red."""
    amber, all_red = runner_clearance_sec(vbs_path)
    return amber + all_red


def plant_lost_time_sec(
    live_phase_count: int = MODEL_PHASE_COUNT, vbs_path: Path | None = None
) -> float:
    """플랜트가 한 주기에서 녹색이 아닌 채로 쓰는 시간 [s] = 현시 수 x (amber + all_red).

    모델의 `network.lost_time` 이 이 값과 같아야 두 주기가 같아진다. 기본값은 모델이
    선언한 현시 수(`MODEL_PHASE_COUNT`)다 — 러너는 **액션이 녹색을 준 현시 수**로 세므로
    (`LivePhaseCount`), 그 수가 모델과 다른 SC 는 `plan_live_phase_counts` 로 따로 물어야
    한다. 여기에 2 를 박아 두면 3현시 SC 에서 조용히 3 s 를 잃는다.
    """
    count = int(live_phase_count)
    if count <= 0:
        raise ValueError(f"live_phase_count must be positive, got {live_phase_count}")
    return float(count) * clearance_sec(vbs_path)


def plan_live_phase_counts(plan_table: Mapping[str, Any]) -> dict[int, int]:
    """계획이 SC 마다 SG 를 붙여 둔 현시의 수. 러너가 세는 그 N 이다.

    `vissim_stackelberg_adapter.plan_live_phases` 와 같은 규칙(현시에 SG 가 하나라도
    있으면 살아 있다)이다. 어댑터는 액션의 현시 집합이 이것과 다르면 죽으므로
    (`signal_group_action_rows`), 이 수가 곧 러너의 `LivePhaseCount` 다.
    """
    out: dict[int, int] = {}
    for key, node in (plan_table.get("controllers") or {}).items():
        groups = node.get("phase_signal_groups") or {}
        out[int(key)] = sum(
            1 for phase in signal_group_plan.MODEL_PHASES if tuple(groups.get(phase) or ())
        )
    return out


def model_effective_green_sec(
    net, live_phase_count: int = MODEL_PHASE_COUNT, vbs_path: Path | None = None
) -> float:
    """현시가 N 개인 SC 에서 모델이 나눠 줄 수 있는 녹색 예산 [s].

    `net.effective_green_total` 은 **스칼라**라 SC 마다 다른 N 을 담지 못한다. 그 간극을
    보이게 하려고 여기서 SC별 값을 따로 만든다. 두 값이 다른 SC 는 지시 녹색을 다
    실어도 플랜트 주기가 모델 주기와 어긋난다.
    """
    return float(net.cycle_length) - plant_lost_time_sec(live_phase_count, vbs_path)


def written_axis_green_sec(green_sec: float) -> float:
    """어댑터가 action CSV 에 실제로 싣는 현시 녹색 [s] (클램프 적용 후)."""
    low, high = SIGNAL_GREEN_WRITE_CLAMP_SEC
    return min(max(float(green_sec), low), high)


def plant_cycle_sec(
    phase_greens: Mapping[str, float], vbs_path: Path | None = None
) -> float:
    """모델이 현시별 녹색을 지시했을 때 러너가 재생하는 주기 [s].

    러너 `SignalCycleFromPhases` 를 그대로 옮긴 것이다 — 녹색이 0 인 현시는 세지 않고,
    남은 현시마다 clearance 를 한 번씩 문다. 어댑터가 CSV 에 싣기 전에 거는 쓰기 클램프도
    여기서 같이 적용한다(러너가 보는 것은 클램프 뒤의 값이다).
    """
    written = {
        phase: (written_axis_green_sec(value) if float(value) > 0.0 else 0.0)
        for phase, value in phase_greens.items()
    }
    live = [phase for phase, value in written.items() if value > 0.0]
    if not live:
        raise ValueError("phase_greens has no live phase")
    return sum(written[phase] for phase in live) + plant_lost_time_sec(
        len(live), vbs_path
    )


def green_box_residual_sec(net, num_phases: int = MODEL_PHASE_COUNT) -> float:
    """`green_min x (N-1) + green_max - effective_green_total` [s]. 계약이면 0 이다.

    부호가 어느 쪽 끝이 죽었는지를 말한다(모듈 docstring 의 계약 참조).

        > 0  `green_max` 가 죽은 상한 — 리더는 total - (N-1) x green_min 까지밖에 못 간다
        < 0  `green_min` 이 죽은 하한 — 리더는 그 아래로 못 내려간다
    """
    others = max(int(num_phases) - 1, 1)
    return (
        float(others) * float(net.green_min)
        + float(net.green_max)
        - float(net.effective_green_total)
    )


def leader_green_box(net, num_phases: int = MODEL_PHASE_COUNT) -> list[dict[str, float]]:
    """리더가 고를 수 있는 현시 배분 중 **극값이 잡히는 점 전부**.

    상류 `state.clamp_primary_green` 의 상자와 같은 규칙이다 — 주 현시를

        [max(green_min, total - (N-1) x green_max), min(green_max, total - (N-1) x green_min)]

    로 자르고 나머지 예산을 남은 현시가 나눈다. `plant_cycle_sec` 은 예산면 위에서
    조각별 선형이라 꺾이는 곳은 상자 끝과 **write clamp 경계** 뿐이다. 그 점들만 보면
    최댓값·최솟값이 정확히 잡힌다. 상자 끝만 보면 클램프가 상자 안쪽에서 물 때를 놓친다.
    """
    phases = list(signal_group_plan.MODEL_PHASES[: int(num_phases)])
    total = float(net.effective_green_total)
    g_min = float(net.green_min)
    g_max = float(net.green_max)
    others = max(len(phases) - 1, 1)
    low = max(g_min, total - others * g_max)
    high = min(g_max, total - others * g_min)
    if low > high:
        low = high = total / float(len(phases))

    clamp_low, clamp_high = SIGNAL_GREEN_WRITE_CLAMP_SEC
    breakpoints = (
        low, high, total / float(len(phases)),
        clamp_low, clamp_high,
        total - others * clamp_low, total - others * clamp_high,
    )
    out: list[dict[str, float]] = []
    for raw in breakpoints:
        primary = min(max(float(raw), low), high)
        rest = (total - primary) / float(others) if len(phases) > 1 else 0.0
        allocation = {phases[0]: primary}
        for phase in phases[1:]:
            allocation[phase] = rest
        out.append(allocation)
    return out


def cycle_disagreement_sec(
    net, num_phases: int = MODEL_PHASE_COUNT, vbs_path: Path | None = None
) -> float:
    """리더 행동 상자 전체에서 |플랜트 주기 - 모델 주기| 의 최댓값 [s]. 0 이어야 한다."""
    model_cycle = float(net.cycle_length)
    return max(
        abs(plant_cycle_sec(allocation, vbs_path) - model_cycle)
        for allocation in leader_green_box(net, num_phases)
    )


def green_fraction_overestimate(
    net, num_phases: int = MODEL_PHASE_COUNT, vbs_path: Path | None = None
) -> float:
    """모델이 g/C 를 얼마나 과대평가하는지의 최댓값 (비율).

    모델은 g/`cycle_length`, 플랜트는 g/`plant_cycle_sec` 이므로 같은 g 에 대해
    비는 plant_cycle / model_cycle - 1 이다.
    """
    model_cycle = float(net.cycle_length)
    return max(
        plant_cycle_sec(allocation, vbs_path) / model_cycle - 1.0
        for allocation in leader_green_box(net, num_phases)
    )
