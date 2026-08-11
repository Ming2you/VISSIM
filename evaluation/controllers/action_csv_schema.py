# action CSV 열 계약의 단일 출처 - 축 2값(v3)을 현시 4값(v4)으로 바꾼 스키마
"""어댑터가 쓰고 러너(VBS)가 읽는 action CSV 의 열 이름과 그 해석.

## v3 -> v4 로 바뀐 것

v3 는 축 2값이었다.

    kind,id,dsd_no,sc_no,link,lane,speed_kph,major_green,minor_green,offset,rate_vph,green_sec,metadata

`major_green`/`minor_green` 은 **축** 녹색이고, 어댑터가 `major_maps_to` 로 모델 현시를
축에 대응시켜 실었다. 4현시가 되면 축이라는 중간 이름이 더는 성립하지 않는다 -
한 축 안에 직진 현시와 좌회전 현시가 따로 있고 둘 사이에도 clearance 가 든다.

v4 는 모델 현시 이름을 그대로 쓴다.

    kind,id,dsd_no,sc_no,link,lane,speed_kph,p1_green,p2_green,p3_green,p4_green,offset,rate_vph,green_sec,metadata

열 이름은 `signal_group_plan.MODEL_PHASES` 에서 유도한다. 여기에 문자열을 베껴 두면
모델 현시 수가 바뀌었을 때 조용히 어긋난다.

## 어느 쪽이 정본인가 - `signal` 행이다

`signal_sg` 행도 SG별 녹색창을 싣지만 그것은 **파생**이다.

    signal 행     현시 4값 = 모델의 결정. 정본.
    signal_sg 행  그 4값을 SG 녹색창으로 편 것. 어댑터가 `signal_group_plan` 으로 유도한다.

러너는 파생을 다시 만들지 않는다 - 만들 수 없다. 창 분수는 실 `.sig` 를 파싱해 나오고
그 파서는 파이썬에 있다. 러너가 하는 일은 **대조** 다.

    Sum(현시 녹색) + (녹색 있는 현시 수) x clearance  ==  모든 signal_sg 행의 green_sec

어긋나면 그 CSV 를 통째로 거부한다. 즉 정본과 파생이 갈라진 순간 부분 적용이 아니라
전량 거부가 일어난다.

VISSIM 에 실제로 실리는 값은 `signal_sg` 창이다(러너 `ApplyRuntimeSignalControllerFromPlan`).
정본이 `signal` 행인 것과 모순되지 않는다 - 파생이 정본에서 유도됐음을 위 항등식이
매 결정마다 증명하기 때문이다.

## `signal_sg` 행의 열 재사용

`signal_sg` 는 v3 때부터 열을 재사용한다. v4 에서도 자리만 옮겨 같은 규칙이다.

    dsd_no    -> sg 번호
    link      -> 녹색창 인덱스
    p1_green  -> 녹색창 시작[s] (플랜 주기 좌표)
    p2_green  -> 녹색창 끝[s]
    p3_green  -> 빈 칸 (반드시 비어 있어야 한다)
    p4_green  -> 빈 칸 (반드시 비어 있어야 한다)
    offset    -> 그 SC 의 offset (같은 SC 의 `signal` 행과 같아야 한다)
    green_sec -> 플랜 주기[s]

p3/p4 를 비워 두는 것이 `signal` 행과 `signal_sg` 행을 가르는 판별자다. 러너가 이것을
검사하므로 두 종류가 섞이면 거부된다.

## 옛 파일 - 다시 쓰지 않는다

저장소에 이미 있는 action CSV 8천여 개는 전부 v3 이고 **그대로 둔다**. 판별은 헤더로
한다(`major_green` 이 있으면 v3, `p1_green` 이 있으면 v4). 옛 런을 읽는 도구는
`phase_green_sum_sec` / `window_bounds_sec` 을 쓰면 두 세대를 같은 코드로 읽는다.
"""

from __future__ import annotations

from typing import Any, Mapping

from evaluation.controllers.signal_group_plan import (
    MODEL_PHASES,
    live_phases,
    plan_cycle_sec,
)


ACTION_CSV_SCHEMA_VERSION = 4

# 현시 녹색 열. 모델 현시 이름에서 유도한다.
PHASE_GREEN_FIELDS: tuple[str, ...] = tuple(f"{phase}_green" for phase in MODEL_PHASES)

ACTION_CSV_FIELDS: tuple[str, ...] = (
    "kind",
    "id",
    "dsd_no",
    "sc_no",
    "link",
    "lane",
    "speed_kph",
    *PHASE_GREEN_FIELDS,
    "offset",
    "rate_vph",
    "green_sec",
    "metadata",
)

# 러너가 남기는 누적 action 로그는 앞뒤로 한 열씩 더 붙는다.
ACTION_LOG_FIELDS: tuple[str, ...] = ("sim_sec", *ACTION_CSV_FIELDS, "readback")

# v3. 저장소에 있는 옛 파일을 읽을 때만 쓴다. 새로 쓰지 않는다.
LEGACY_AXIS_GREEN_FIELDS: tuple[str, ...] = ("major_green", "minor_green")
LEGACY_ACTION_CSV_FIELDS: tuple[str, ...] = (
    "kind",
    "id",
    "dsd_no",
    "sc_no",
    "link",
    "lane",
    "speed_kph",
    *LEGACY_AXIS_GREEN_FIELDS,
    "offset",
    "rate_vph",
    "green_sec",
    "metadata",
)

# `signal_sg` 행이 녹색창 시작/끝으로 재사용하는 두 열.
WINDOW_START_FIELD = PHASE_GREEN_FIELDS[0]
WINDOW_END_FIELD = PHASE_GREEN_FIELDS[1]
# 그 행에서 반드시 비어 있어야 하는 열. `signal` 행과의 판별자다.
WINDOW_BLANK_FIELDS: tuple[str, ...] = PHASE_GREEN_FIELDS[2:]


class ActionCsvSchemaError(RuntimeError):
    """action CSV 가 계약을 어겼다. 조용한 폴백 대신 예외로 올린다."""


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        text = str(value).strip()
    except Exception:  # pragma: no cover - str() 이 죽는 값은 오지 않는다
        return default
    if not text:
        return default
    try:
        return float(text)
    except (TypeError, ValueError):
        return default


def row_is_v4(row: Mapping[str, Any]) -> bool:
    """이 행이 v4 스키마인가. 헤더로 판별한다."""
    return PHASE_GREEN_FIELDS[0] in row


def phase_greens(row: Mapping[str, Any]) -> dict[str, float]:
    """v4 `signal` 행의 현시 녹색. v3 행에는 현시 귀속이 없어 거부한다.

    v3 의 `major_green`/`minor_green` 은 축 이름이고 어느 현시였는지는 행에 없다
    (`major_maps_to` 는 매핑 JSON 에만 있다). 그래서 v3 행을 현시로 되돌리는 것은
    행만 보고는 불가능하다 - 합만 필요한 곳은 `phase_green_sum_sec` 을 써라.
    """
    if not row_is_v4(row):
        raise ActionCsvSchemaError(
            "v3 action row has axis greens, not phase greens - use phase_green_sum_sec()"
        )
    return {
        phase: _as_float(row.get(field))
        for phase, field in zip(MODEL_PHASES, PHASE_GREEN_FIELDS)
    }


def phase_green_sum_sec(row: Mapping[str, Any]) -> float:
    """`signal` 행이 지시한 녹색의 총합[s]. v3/v4 둘 다 읽는다."""
    fields = PHASE_GREEN_FIELDS if row_is_v4(row) else LEGACY_AXIS_GREEN_FIELDS
    return sum(_as_float(row.get(field)) for field in fields)


def window_bounds_sec(row: Mapping[str, Any]) -> tuple[float, float]:
    """`signal_sg` 행의 녹색창 (시작, 끝)[s]. v3/v4 둘 다 읽는다."""
    if row_is_v4(row):
        return (_as_float(row.get(WINDOW_START_FIELD)), _as_float(row.get(WINDOW_END_FIELD)))
    return (
        _as_float(row.get(LEGACY_AXIS_GREEN_FIELDS[0])),
        _as_float(row.get(LEGACY_AXIS_GREEN_FIELDS[1])),
    )


def action_cycle_sec(
    phase_green_map: Mapping[str, float], amber_sec: float, all_red_sec: float
) -> float:
    """현시 녹색이 만드는 플랜트 주기[s]. `signal_group_plan` 의 식이 단일 출처다."""
    return plan_cycle_sec(phase_green_map, amber_sec, all_red_sec)


__all__ = [
    "ACTION_CSV_FIELDS",
    "ACTION_CSV_SCHEMA_VERSION",
    "ACTION_LOG_FIELDS",
    "ActionCsvSchemaError",
    "LEGACY_ACTION_CSV_FIELDS",
    "LEGACY_AXIS_GREEN_FIELDS",
    "PHASE_GREEN_FIELDS",
    "WINDOW_BLANK_FIELDS",
    "WINDOW_END_FIELD",
    "WINDOW_START_FIELD",
    "action_cycle_sec",
    "live_phases",
    "phase_green_sum_sec",
    "phase_greens",
    "row_is_v4",
    "window_bounds_sec",
]
