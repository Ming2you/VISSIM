#!/usr/bin/env python3
# v3 사전등록 상수 한 곳 — FD 미분 스텝과 레버 진폭을 분리해 고정한다
"""Pre-registered constants, with the two look-alike amplitudes kept apart.

계획에 진폭이 두 벌 있고 **서로 다른 양**이다. 문서만 읽으면 헷갈린다.

    전진폭 (N8-1)   FD 미분 스텝. 기울기 추정용.
                    녹색 6 s · VSL 10 km/h · offset C/8 · 램프미터 max(300, 0.20·capacity)

    진폭   (N9-2)   짝지은 검증 레버 low/base/high.
                    녹색 ±10 s · VSL ±10 km/h · 램프미터 ±150 veh/h · offset ±10 s

둘 다 사전등록이라 런 후 수정이 금지된다. 그런데 계획의 "사전 등록" 절에는 FD 스텝만 적혀
있어, 거기만 읽은 사람은 N9 레버 진폭을 못 찾거나 FD 스텝을 레버 진폭으로 오해한다.

같은 부류의 사고가 이미 한 번 있었다 — N9 행렬의 holdout 시드를 임의로 정했다가 N5 부모 런과
어긋났고, 두 명세가 서로 다른 절에 있어 사람이 놓쳤다. 그래서 여기서 **교차 정합을 코드로
건다**: 시드·H 축·잡음 바닥·레버 진폭이 N5/N9 산출물과 같은지 테스트가 확인한다.
"""

from __future__ import annotations

from typing import Mapping


SCHEMA_VERSION = "preregistration-v3"

# ── N8-1 FD 미분 스텝 ────────────────────────────────────────────────────────
# 기울기 추정용 전진 섭동이다. 레버 진폭이 아니다.
# 두 추정기 모두 요청 폭이 아니라 **경계된 실현 변위**로 나눈다.
FD_STEP: Mapping[str, float] = {
    "green_sec": 6.0,
    "vsl_kph": 10.0,
    "offset_cycle_fraction": 1.0 / 8.0,      # C/8 — 주기에 비례한다
    "ramp_meter_floor_veh_h": 300.0,          # max(300, 0.20·capacity) 의 바닥
    "ramp_meter_capacity_fraction": 0.20,     # 같은 max 의 비율 항
}


def ramp_fd_step(capacity_veh_h: float) -> float:
    """max(300 veh/h, 0.20·capacity). 둘 중 **큰 쪽**을 쓴다."""
    return max(
        FD_STEP["ramp_meter_floor_veh_h"],
        FD_STEP["ramp_meter_capacity_fraction"] * float(capacity_veh_h),
    )


def offset_fd_step(cycle_sec: float) -> float:
    """C/8. 실망 주기가 100~170 s 이므로 SC 마다 스텝이 다르다."""
    return FD_STEP["offset_cycle_fraction"] * float(cycle_sec)


# ── N9-2 레버 진폭 ───────────────────────────────────────────────────────────
# 짝지은 검증의 (low, base, high). FD 스텝과 혼동하지 마라.
# build_experiment_matrix_v3.LEVER_AMPLITUDES 와 같아야 하며 테스트가 확인한다.
LEVER_AMPLITUDE: Mapping[str, tuple[float, float, float]] = {
    "green": (-10.0, 0.0, 10.0),
    "vsl": (-10.0, 0.0, 10.0),
    "ramp_meter": (-150.0, 0.0, 150.0),
    "offset": (-10.0, 0.0, 10.0),
}

# ── 시드 ─────────────────────────────────────────────────────────────────────
TRAINING_SEEDS = (13, 29)
HOLDOUT_SEEDS = (47,)
# holdout 은 N6 적합과 N8/N9 임계선택에 쓰지 않는다. 승격 판정 전용이다.
HOLDOUT_USAGE = "promotion_only"

# ── H 축 ─────────────────────────────────────────────────────────────────────
HORIZONS = (1, 3, 5, 10, 15)
H1_INDEPENDENT_GATE = True   # H=1 은 다른 H 로 구제하지 않는다

# ── 잡음 바닥 ────────────────────────────────────────────────────────────────
# 두 값을 절대 섞지 마라. 합치면 eps_g 가 과대해져 지지 요건이 무너진다.
EPS_J_VISSIM_FLOOR_VEH_H = 1.0e-6      # VISSIM 런간 분산 (N5, N9 의 ΔJ 재료성 전용)
EPS_J_ENDPOINT_FLOOR_VEH_H = 1.0e-9    # 플랜트 endpoint 재현성 (N8-1 이 자체 측정)
