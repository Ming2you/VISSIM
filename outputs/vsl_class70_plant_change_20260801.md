# 플랜트 변경 고지 — 택시(클래스 70) VSL 편입 및 S0 진입 클리어런스 (2026-08-01)

이 문서는 성능 보고가 아니라 **비교 기준선이 끊어졌다는 고지**다.
이 날짜 이후 재생성된 `network/real_world_gaepo_modi/modi_eval_rw_control.inpx` 로 돌린 런은
그 이전 런과 **직접 비교할 수 없다**. 아래에 무엇이 바뀌었고 어느 수치가 무효가 되는지 적는다.

선행 근거는 `outputs/vsl_channel_live_execution_20260801.md` 의 실측(§4, §6)이다.

---

## 1. 무엇을 바꿨나

### 변경 A — 택시(차량 클래스 70)를 VSL 대상에 편입 (플랜트 거동 변경)

| 항목 | 이전 | 이후 |
|---|---|---|
| RW DSD 64개의 대상 클래스 | 10, 20, 30 | 10, 20, 30, **70** |
| 레거시 DSD 36~42 (런타임 주입) | 10, 20, 30 | 10, 20, 30, **70** |
| 본선에서 택시의 희망속도 | 유입 구성 분포 40(40~45 km/h)을 전 구간 유지 | 지시 VSL 분포(무제어 기본 120) |
| 매니페스트 `veh_classes` 열 | `10;20;30` | `10;20;30;70` |

택시는 차종 150, 클래스 70이고 본선 유입 구성(vehComp 1)의 10%, 실측 본선 표본의 **14.45%** 다.
이전에는 본선 체인 위 71개 DSD 어느 것도 클래스 70에 분포를 지정하지 않아 택시가
**본선 전 구간에서 40~45 km/h를 희망하는 이동 장애물**로 굴러갔다.

**분포 선택 — 다른 클래스와 동일한 VSL 분포를 쓴다.** 근거는 셋이다.

1. 사용자 결정이 "클래스 70을 VSL 대상에 편입한다"이므로 지시값이 택시에도 그대로 닿아야 한다.
2. 대안인 "택시는 min(VSL, 40)으로 캡"은 VSL 메뉴 하한이 50 km/h라 어떤 지시값에서도
   40을 밑돌지 않는다. 즉 편입하지 않은 것과 수학적으로 같아져 결정과 모순된다.
3. 편입하지 않으면 VSL의 이론적 최대 적용률이 채널이 아무리 건강해도 약 85%로 묶인다.
   제어 권한(authority) 분석이 성립하려면 대상 집합이 본선 차량 전체여야 한다.

**대가를 분명히 적는다.** 이것은 원 네트워크의 모델링 의도를 바꾼다. 원저작자는 택시를
본선에서 저속으로 달리는 차량으로 모델링했고, 그 14.45%가 사실상 상시 병목 요소였다.
이제 택시도 120 km/h를 희망하므로 **본선의 자유류 속도와 용량이 올라간다.**
그래서 이 변경 전후는 비교 불가다.

### 변경 B — 세그먼트 0 진입 클리어런스 (구조 결함 수정, 운영 배선에서는 거동 중립)

`install_real_world_freeway_controls.vbs` 의 `If i = 0 Then dsdPos = ClampPos(1.0, link)` 예외를
제거했다. S0 DSD가 진입점 + `DSD_EDGE_CLEARANCE_M`(40 m)로 이동한다.

| 채널 | 이전 위치 | 이후 위치 | 같은 링크의 레거시 DSD |
|---|---|---|---|
| RW_FW_E_S0 (link 74, 차로 1~4) | pos 1.000 | **pos 40.000** | no 39/38/37/36 @ 11.528~11.869 (분포 100) |
| RW_FW_W_S0 (link 26, 차로 1~4) | pos 1.000 | **pos 40.000** | no 41/42/40 @ 1.605~2.616 (분포 100) |

이전에는 S0 DSD가 레거시 진입부 DSD보다 **상류**라 10 m 뒤에서 덮여 사라졌다
(실측 자기지문 FW_E S0 1.3%, FW_W S0 21.8% — 차로 4만 생존).
이제 S0가 하류이므로 우리 VSL이 이긴다.

**거동 영향은 제한적이다.** 운영 배선에서는 어댑터가 레거시 DSD 36~42에도
(`segments[*].extra_dsd_controls`) 같은 VSL을 실어 보내고 있었으므로,
클래스 10/20/30 의 실효 개시점은 이전에도 이후에도 레거시 DSD 위치(11.5 / 2.6 m)다.
바뀐 것은 **채널의 생사가 더 이상 레거시 DSD 수집 로직에 의존하지 않는다는 것**이다.

예외 한 가지. 컨트롤러가 액션 CSV를 한 번도 적용하지 않은 상태로 .inpx 를 그대로 읽는 경우
(VISSIM GUI 직접 열기 등), 세그먼트 0의 정적 희망속도 분포가 100에서 120으로 바뀐다.
러너(`run_real_world_stackelberg_controller.vbs`)는 no-control 변형에서도 VSL 행을 120으로
매 결정마다 집행하므로 러너 경유 런에는 해당하지 않는다.

### 남는 근사

체인 [0, 40 m) 구간에는 VSL이 적용되지 않는다. 상류 세그먼트가 없으므로 그 구간의 차량은
네트워크 자신의 유입 분포를 유지한다. 세그먼트 길이 약 1347 m 대비 3.0%다.
측정 격자(`segment_bounds_m`)는 손대지 않았다 — 움직인 것은 물리 DSD 위치뿐이고,
크기는 `control_mapping.json` 의 `segments[*].dsd_snap_offset_m = 40.0` 에 적혀 있다.

두 근사 모두 `evaluation/real_world_modi_control/control_mapping.json` 의
`known_approximations` 에 `vsl_segment0_entry_clearance`, `vsl_taxi_class70_included`
두 항목으로 기록돼 있다.

---

## 2. 비교 불가 범위 — 무효가 되는 헤드라인 수치

플랜트가 바뀌었으므로 **`modi_eval_rw_control.inpx`(및 그 파생 수요 변형 네트워크)로 측정한
모든 VISSIM 수치**가 재측정 대상이다. baseline과 candidate가 같은 옛 플랜트에서 나왔다면
그 둘 사이의 **상대 비교(delta %)는 내부적으로는 여전히 유효**하지만,
새 플랜트에서 나온 값과는 절대치도 델타도 섞을 수 없다.

### 2.1 절대치와 델타가 모두 무효

| 산출물 | 무효가 되는 대표 수치 |
|---|---|
| `outputs/real_world_peakhold_recovery_d115_7200_comparison_20260731.md` | Total TTT 7130.582 → 7006.048 (−1.746%), 평균 본선속도 63.928 → 64.270 kph |
| `outputs/real_world_peakhold_recovery_7200_comparison_20260729.md` | 동 계열 TTT/속도/정지시간 전부 |
| `outputs/real_world_demand100_8100_comparison_20260729.md` | 동 |
| `outputs/real_world_demand115_pstack_4500_20260727.md` | 동 |
| `outputs/real_world_congestion_modes_comparison_20260727.md` | 동 |
| `outputs/real_world_congestion_ladder_*_20260724.{md,csv,json}` | 수요 사다리 전 구간 |
| `outputs/real_world_d115_demand_bottleneck_control_overlap_20260731.md` | 병목/제어 중첩 판정 |

### 2.2 플랜트 특성치이므로 재적합 필요

| 산출물 | 무효가 되는 항목 |
|---|---|
| `outputs/no_control_fd_mfd_20260724_*` | freeway FD, urban MFD 점군과 binned 곡선 전부 |
| `outputs/no_control_mixed_critical_fd_mfd_20260724_*` | 동 |
| `evaluation/calibration/real_world_modi_control_v0_20260719.json` | `operational.network` 의 `v_free_kph` 100.0, `rho_crit_veh_km_lane` 24.0, `freeway_capacity_veh_h` 7600.0 — 14.45%의 저속 차량이 사라졌으므로 셋 다 위로 이동한다 |
| `outputs/real_world_prediction_accuracy_*_2026072*` | 예측 오차 분해는 플랜트 FD 위에서만 의미가 있다 |
| `outputs/vsl_sensitivity_20260801.md` | "내부 FD가 실측 대비 +35 km/h" 라는 편향 진단. 실측 쪽이 올라가므로 편향 크기가 줄어든다. 플랜트/NumSim 내부 비교(§1~§5)는 VISSIM과 무관하므로 유효 |

### 2.3 채널 커버리지 재측정 필요

`outputs/vsl_channel_live_execution_20260801.md` 의 §3 표와 코리도 집계는
"클래스 70은 대상이 아니다"를 전제로 계산됐다. 다음 값들이 정의부터 달라진다.

- 자기 세그먼트 VSL을 받은 본선 표본 82.37%(실행 B) — 분모에 택시가 들어오므로 재계산 필요
- 대상 클래스만 볼 때 96.28% — 대상 클래스 정의가 4개로 바뀜
- 클래스 70 표본 14.45% — 이제 누수가 아니라 대상
- §4의 FW_E S0 1.3% / FW_W S0 21.8%(실행 A) — 변경 B가 직접 겨냥한 값이므로 폐기
- `scripts/analyze_vsl_channel_liveness.py` 의 클래스 70 예외 처리(line 16, 153)도 함께 갱신해야
  재측정이 성립한다

### 2.4 영향 없음

- 가상 네트워크(hypothetical / 8seg) 계열 산출물 전부 — 다른 .inpx 를 쓴다
  (`outputs/*_220w_600s_20260716.*`, `outputs/*_20260715.*`, `outputs/pstack_nonimprovement_audit_20260718.*`)
- `plant/` 커널 테스트와 NumSim 내부 정합 검증 — VISSIM 측정을 입력으로 쓰지 않는 부분
- 신호/도시 팔로워 매핑 산출물 — DSD 클래스와 무관
  (`outputs/urban_follower_sc_mapping_fix_20260801.md`, `outputs/real_world_distributed_urban_followers_*`)

---

## 3. 기준선 재수립 절차

1. `no-control` 런으로 FD/MFD를 다시 뽑는다 (`scripts/extract_no_control_fd_mfd.py`).
2. `evaluation/calibration/real_world_modi_control_v0_20260719.json` 의
   `v_free_kph` / `rho_crit_veh_km_lane` / `freeway_capacity_veh_h` 를 재적합한다.
3. 그 다음에야 pstack vs fixed 비교를 다시 돌린다. 2번을 건너뛰면 예측 오차가
   플랜트 변경 때문인지 컨트롤러 때문인지 분리되지 않는다.
4. VSL 채널 생존 재측정은 `scripts/analyze_vsl_channel_liveness.py` 의 클래스 70 취급을
   "대상"으로 고친 뒤에 한다.

---

## 4. 변경 파일

| 경로 | 변경 |
|---|---|
| `scripts/install_real_world_freeway_controls.vbs` | 세그먼트 0 예외 제거, `ENTRY_HOLD=` echo 추가, `SetClassSpeed dsd, 70`, 매니페스트 `veh_classes` |
| `scripts/run_real_world_stackelberg_controller.vbs` | `ApplyActionCsv` 에 `SetClassSpeed dsd, 70, speed`, readback에 `DesSpeedDistr(70)` 병기 |
| `scripts/generate_real_world_control_mapping.py` | `known_approximations` 2항목 추가 |
| `network/real_world_gaepo_modi/modi_eval_rw_control.inpx` (+ `.layx`) | 재생성 |
| `evaluation/real_world_modi_control/*` | 매니페스트/매핑/플레이어 재생성 |
| `evaluation/real_world_modi_control_distributed_20260728/*` | 재생성 (primary19, core15) |
| `evaluation/generated/real_world_modi_control_config*.vbs` | 재생성 |
| `outputs/vsl_class70_plant_change_20260801.md` | 이 문서 |
