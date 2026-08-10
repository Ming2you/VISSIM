#!/usr/bin/env python3
# 짝지은 검증 관측을 60초로 집계하고 ΔJ 를 같은 prefix 에서 계산한다 (v3 N9-3)
"""Aggregate 1-second VISSIM observations into 60-second bins and form paired deltas.

계획(N9-3)의 세 문장이 각각 함정을 하나씩 막는다.

**"같은 prefix 에서"** — base 와 action 은 anchor 까지 동일한 궤적이어야 한다. 다른 prefix 의
`J` 를 빼면 그 차이가 레버 효과로 둔갑한다. `delta_j` 가 prefix 신원과 anchor 를 요구한다.

**"반복은 잡음만 추정하고 표본 수를 늘리지 않는다"** — replicate 를 독립 표본으로 세면
유의성이 부풀려진다. `collapse_replicates` 는 값을 하나로 접고 분산은 잡음 추정에만 쓴다.
반복이 하나면 잡음을 **0 이 아니라 미상(None)** 으로 둔다 — 0 으로 두면 모든 효과가 유의해 보인다.

**채널 분리** — 총량 지표가 접속부 오차를 흡수하지 못하게 한다. 램프미터 레버 효과가
발생하는 곳이 정확히 거기다. 미배정 항목은 버리지 않고 `unassigned` 로 남긴다.

집계에서 조용히 사라지는 것이 없도록 두 가지를 더 지킨다 — 빈 bin 을 실체화해 base 와
action 의 인덱스가 어긋나지 않게 하고, 잘린 마지막 bin 은 `partial` 로 표시해 표본 수가
줄어든 것을 드러낸다.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence


SCHEMA_VERSION = "paired-validation-aggregate-v3"

DEFAULT_BIN_SEC = 60.0

CHANNELS = ("controlled", "monitor", "midblock", "boundary", "ramp", "freeway")

# 계획이 명시한 채널 크기. 실측이 다르면 매핑이 어긋난 것이다.
EXPECTED_CHANNEL_SIZES = {"controlled": 15, "monitor": 26, "midblock": 9}


class AggregateError(ValueError):
    """Raised when aggregation would silently lose or fabricate a sample."""


@dataclass(frozen=True)
class Bin:
    start_sec: float
    end_sec: float
    count: int
    mean: float | None
    partial: bool


@dataclass(frozen=True)
class RunObjective:
    """한 런의 목적함수 값. prefix 신원이 없으면 짝을 지을 수 없다."""

    prefix_id: str
    anchor_sec: int
    value: float


@dataclass(frozen=True)
class ReplicateSummary:
    value: float
    noise: float | None
    replicate_count: int
    sample_count: int


def aggregate_to_bins(
    samples: Sequence[tuple[float, float]], bin_sec: float = DEFAULT_BIN_SEC
) -> list[Bin]:
    """(time_sec, value) 표본을 반개구간 [start, start+bin) 으로 묶는다.

    닫힌 구간이면 경계 표본이 두 bin 에 들어간다. 빈 bin 도 만들어 둔다 — 건너뛰면 인덱스가
    밀려 base 와 action 의 같은 시각이 서로 다른 bin 으로 간다.
    """
    if bin_sec <= 0:
        raise AggregateError("bin_sec must be positive")
    if not samples:
        return []
    times = [float(t) for t, _ in samples]
    if any(b < a for a, b in zip(times, times[1:])):
        raise AggregateError("samples must be sorted by time")

    buckets: dict[int, list[float]] = {}
    for time_sec, value in samples:
        index = int(float(time_sec) // bin_sec)
        buckets.setdefault(index, []).append(float(value))

    last_time = times[-1]
    highest = max(buckets)
    out: list[Bin] = []
    for index in range(0, highest + 1):
        values = buckets.get(index, [])
        start = index * bin_sec
        end = start + bin_sec
        # 마지막 bin 이 관측 끝을 넘어서면 잘린 것이다. 조용히 버리지 않고 표시한다.
        partial = index == highest and last_time + 1.0 < end
        out.append(
            Bin(
                start_sec=start,
                end_sec=end,
                count=len(values),
                mean=(sum(values) / len(values)) if values else None,
                partial=partial,
            )
        )
    return out


def delta_j(action: RunObjective, base: RunObjective) -> float:
    """ΔJ = J(action) − J(base). 같은 prefix·같은 anchor 가 아니면 거부한다."""
    if action.prefix_id != base.prefix_id:
        raise AggregateError(
            f"prefix mismatch: action={action.prefix_id!r} base={base.prefix_id!r}"
        )
    if action.anchor_sec != base.anchor_sec:
        raise AggregateError(
            f"anchor mismatch: action={action.anchor_sec} base={base.anchor_sec}"
        )
    return float(action.value) - float(base.value)


def collapse_replicates(values: Sequence[float]) -> ReplicateSummary:
    """반복을 표본 하나로 접는다. 분산은 잡음 추정에만 쓴다.

    반복이 하나면 잡음은 0 이 아니라 미상이다 — 0 으로 두면 모든 효과가 유의해 보인다.
    """
    items = [float(v) for v in values]
    if not items:
        raise AggregateError("no replicates to collapse")
    if len(items) == 1:
        noise = None
    elif len(items) == 2:
        # 두 번이면 표준편차 대신 두 값의 차이를 잡음 폭으로 쓴다. 표본 2 의 stdev 는
        # 같은 정보를 1/sqrt(2) 배로 줄여 보여 줄 뿐이라 읽는 사람을 오도한다.
        noise = abs(items[0] - items[1])
    else:
        noise = statistics.stdev(items)
    return ReplicateSummary(
        value=sum(items) / len(items),
        noise=noise,
        replicate_count=len(items),
        sample_count=1,
    )


def split_by_channel(
    items: Iterable[str], assignment: Mapping[str, str]
) -> dict[str, list[str]]:
    """항목을 채널로 가른다. 미배정은 버리지 않고 `unassigned` 로 남긴다.

    버리면 총량 지표가 접속부 오차를 흡수한다 — 계획이 막으려는 바로 그것이다.
    """
    out: dict[str, list[str]] = {channel: [] for channel in CHANNELS}
    out["unassigned"] = []
    for item in items:
        channel = assignment.get(item)
        if channel is None:
            out["unassigned"].append(item)
            continue
        if channel not in out:
            raise AggregateError(f"unknown channel {channel!r} for item {item!r}")
        out[channel].append(item)
    return out
