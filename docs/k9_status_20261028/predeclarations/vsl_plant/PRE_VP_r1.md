# PRE_VP — 우리 plant(V-A 줄기) VSL 탐침 A·B 와 P1 편향 추적: 실행 전 고정 (2026-10-27 KST)

- 근거: 사용자 결정 D-K9-101~103 (`SP/K9_1_J1_NOTES_20261013.md`, sha256 `b33fe5e79c60fa499cce17a41bc18d24b1de33773226d8e80600a7c9bc8f5f89`, 337–344 줄). 이 문서는 Q-V3(탐침 A·B)와 Q-V4(P1 원인 추적)만 다룹니다. Q-V5(φ 사잇값)는 하지 않습니다. Q-V6(C1 보고 VSL 줄)은 C1 쪽 일입니다.
- 이 문서는 탐침 자료가 하나도 나오기 전에 고정합니다. 고정 sha256 은 `VP/PRE_VP.md.sha256` 과 `VP/LOG.md` 에 적습니다. 고정 뒤에는 고치지 않습니다. 결함이 보이면 멈추고 보고합니다(사용자가 정함). 자료를 본 뒤에 하는 분석은 "데이터 뒤" 라고 붙입니다.
- 판정 낱말은 쓰지 않습니다. 숫자·부호·띠·규칙 충족 여부만 적습니다. 시드는 망 이름을 붙여 적습니다(v3c3-s31 등). 신호 녹색은 GREEN 만 셉니다(이 문서에는 신호 녹색 지표가 없습니다).
- 표시: **[실행]** 이번에 돌려서 확인 · **[읽음]** 파일·코드를 읽어 확인 · **[추론]** 시험하지 않은 판단 · **[계산]** 산술.
- 경로 줄임: SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`, VP = `SP/vsl_plant`, GT = `D:/VISSIM-merge/k8_gate_trees/vsl_plant`(스크래치), FRZ_K92 = V-A 동결 트리 `D:/VISSIM-merge/frozen/sdmpc31_c20aff1d_202610230833`(읽기만), RVP = 보고 사본 `D:/VISSIM_runs/20261001_v3c3/reports/k8/vsl_plant`. 코드 줄 번호는 FRZ_K92 기준입니다(EC = `evaluation/controllers`).

## 0. 줄임말 (처음 한 번)

- VSL = 가변 제한속도. DSD = VISSIM 희망속도 결정점(표지). plant = SDMPC(순차 분해 모형예측제어기) 안의 교통 예측 모형. V-A = 우리 줄기 폐루프 VISSIM 런 3개(`D:/VISSIM_runs/20261023_sdmpc31_k92`). NC3 = 같은 시드 무제어 런. VSL 단독 = DSD 63–66 에 91 을 고정한 native 런(`D:/VISSIM_runs/20261027_vsl_v3c3`). B = codex 제어기를 v3c3 로 옮긴 폐루프(VSL 110 고정, `D:/VISSIM_runs/20261026_codex_b_v3c3`). FZP = VISSIM 차량 궤적 기록(5 s 프레임).
- J = plant 의 모형 목적값 `objective_veh_h`(Ω635 영역, 450 s = 150 s 블록 3개, veh·h). ΔJ = 두 팔의 J 차.
- 팔 = 같은 결정 상태에서 바꿔 굴리는 계획 하나. REC = 기록된 선택 계획. EXEC = VISSIM 이 그 450 s 동안 실제로 돌린 블록들. ARM v = REC 에서 VSL 구역 머리 10 만 v 로 바꾼 계획.
- AD 경로 = 미분을 함께 내는 작업자 굴림(기록된 선택 계획의 J 가 이 길에서 나왔음). 스칼라 경로 = 값만 내는 작업자 굴림. 작업자 = 결정이 plant 를 굴릴 때 띄우는 별도 python 프로세스(`EC/sdmpc_tangent_worker.py`). 둘 다 배포 결정과 같은 작업자 경로입니다(§1.2).
- 셀 = FW_E 본선 31셀(체인 0–10,784 m, 경계 = `vsl_cell_scan.py` 의 CELL_B). 구역(PRE_O1O2 와 같은 이름·범위): U 0–7 · B1 8–13 · M1 14–15 · VSa 16–18 · VSb 19–25 · D 26–30. 덧붙인 셀 맞춤 구역: Mu′ 16–17 (6,315–6,666 m) · VS0′ 18 (6,666–6,842 m, 차로 감소 바로 앞 셀) · B2′ 19–24 (6,842–7,827 m). 프라임(′)은 VSL_REPORT 의 체인 구역(Mu 6,300–6,700 · VS0 6,700–6,800 · B2 6,800–8,100 m)을 셀 경계로 맞춘 근사라는 뜻입니다.
- φ_lane = 차로 감소항 계수(`freeway.lane_drop_phi`). φ_cd = 용량 감소 방류 계수(`capacity_drop_discharge_phi`). ν_cong 전환 = 혼잡 때 예견항 계수를 바꾸는 용량 감소 표현(`capacity_drop_anticipation`). δ = 합류 감속항 계수(`metanet_delta_merge`). ρ_c = 셀 임계 밀도. v_free = 셀 자유 속도. a = FD(기본도) 모양 지수. Carlson 법칙 = plant 의 VSL 준수 법칙(m_v = 측정 속도 척도). 코호트 = 표지를 지난 차가 지닌 명령 값 꼬리표(`VSLExposure`).
- R = 줄임 비율(§5.4). 띠 A·B·C = R 중앙값 구간(§5.4). S-* = 멈춤 규칙(§7).

## 1. 대상 plant 와 경로 (데이터 전 사실)

### 1.1 우리 plant 의 FW_E

- [실행 smoke v1·v2 훅 스냅샷, §1.3] V-A plant 의 FW_E 는 차로군 plant 가 없습니다. `LaneFreewayRuntime.advance` 가 길마다 `self.lanes.get(road)` 를 보고(EC/lane_freeway_runtime.py:107), 없으면 31셀 집계 METANET `area_freeway_accounting._freeway_substep_events` 를 1 s 마다 부릅니다(같은 파일 :123; EC/lane_coupling.py:97). plant 구성 `plant_n31_v2.json:59` 도 `"lane_groups": false` 입니다 [읽음].
- [실행 smoke 스냅샷] 셀은 31개이고 경계가 CELL_B 와 같습니다(셀 12 길이 0.18424 km = 4,894.4–5,078.6 m). 차로는 셀 0–18 이 4, 셀 19–30 이 3 입니다. 그래서 차로 감소항은 셀 18(VS0′)에만 걸립니다(EC/vissim_stackelberg_adapter.py:9597-9602).
- [읽음] VSL 명령 공간은 부모 21구간 키(`FW_E__seg0…seg20`)이고, 구역 머리는 FW_E [0, 5, 10, 15], 자유 구역은 0·1·2 입니다(`diagnostics/sdmpc_n31_20260924/config_n31_v2.json`:8058-8077). 31셀은 자기 구역 머리 키의 값을 받습니다(어댑터 `_zoned_segment_vsl`, :9126-9134).
- [읽음] V-A 가 110 밖을 쓴 결정은 모두 구역 머리 10(`FW_E__seg10…14`)의 100 이고, VISSIM 에는 분포 101 로 써졌습니다(`SP/k92/va/analysis/VA_REPORT.md`(b57022e6…):573; `plant_n31_v2.json` qualification "commands 80/90/100/110 are written as the distributions 81/91/101/110").
- [읽음] 한 걸음의 항(EC/area_freeway_accounting.py = AFA): 목표 속도 V = 셀별 v_free·exp(−(ρ/ρ_c)^a / a)(메타넷 `desired_speed_kmh`, `vendor/NumSim-mine/src/models/metanet.py`:15; 셀 값은 어댑터 훅 :9548) → 명령 < 109.5 일 때만 Carlson 법칙(AFA:382-384, EC/freeway_fd.py:115-152) → 코호트 혼합(AFA:385-387, freeway_fd.py:283-) → 이완·대류·예견 갱신(AFA:392, metanet.py:99-122; ν 는 :125-137 에서 ν_cong 전환) → 차로 감소항(어댑터 :9597-9602) → 합류 감속항 δ(AFA:162, :393-396) → 출구 막힘 속도 상한(AFA:354) → 흐름 q = ρ·v·차로, φ_cd 방류 상한(AFA:133, :213-216).
- [실행 smoke v2 훅 스냅샷, 작업자가 본 FW_E 구성 값] φ_lane 3.0, δ 1.0(튜닝 `config_overrides.network.metanet_delta_merge` 는 0.3 이지만 FW_E 걸음은 구성 사본의 1.0 을 읽음, 방향별 값 없음), φ_cd 1.0, ν_cong 전환 꺼짐(ν 38.7, ν_cong 250 은 쓰이지 않음), α_vsl 0, 링크 ρ_c 37.8, 셀 길이 가변(합 10.784 km, 31셀), 셀 행 키 v_free·rho_crit·metanet_a_m·metanet_tau_h·metanet_nu_km2_h·metanet_kappa_veh_km_lane·segment_length_km. 준수 법칙 Carlson A 1.33 · E 0.87 · m_v(80/90/100) 0.7225/0.8120/0.9007. 코호트 표지 셀 [0, 3, 5, 8, 14, 18, 26, 28]. 구역 머리 10 이 다스리는 셀 = 14–24(M1 14–15, VSa 16–18, VSb 19–24). FW_E 출구 셀: 10643 → 9, 10682 → 11, 10481 → 18, 10483 → 20. FW_E 합류 램프: RM_C10639·10681·10490·10484. Hadi 수용 모형 없음.

### 1.2 배포 결정의 plant 경로

- [읽음] V-A 정책은 `surrogate_reuse` 가 켜져 있어 결정의 모든 plant 굴림이 연속 대리 모형 `sdmpc_tangent_surrogate.Query` 를 거칩니다(EC/sdmpc.py:587-593). `Query.evaluate`(EC/sdmpc_tangent_surrogate.py:202-256)는 계획 하나마다 `sdmpc_tangent._evaluate_single`(EC/sdmpc_tangent.py:48-71)로 작업자 프로세스 하나를 띄웁니다. 이것이 작업자 경로입니다.
- [읽음] 기록된 선택 계획의 J(`metadata.joint_leader_selection.selected_objective`)는 AD 굴림에서 나왔습니다(V-A 행동 JSON 의 `surrogate_query.rows` 에서 그 계획 토큰의 행이 `derivatives: true`).

### 1.3 배관 시험 (목록 밖 상태 v3c3-s31 T=2,400, 결과로 쓰지 않음) [실행]

- smoke v1 (16:16–16:23): REC 의 AD 경로 J 가 기록 selected_objective 와 **비트까지 같았습니다**(차 0.0). 스칼라 경로 J − AD 경로 J = 0.0. 재포장(REPACK) J 도 비트 같음. 소유자별 비용 20개 가운데 3개(FW_E·SC1001·SC1005)가 기록과 1.4e-14 이하로 달랐습니다 → R1 규칙의 비용 허용 1e-9 를 이 사실로 정했습니다(§3.4). 기록 JSON 을 그대로 읽은 계획(`control_from_json`)도 J 가 같았습니다. 이 판에서 FW_E 에 차로군 plant 가 없다는 것을 알아(훅 오류 "no lane plant", 절제 KeyError) 훅·절제·셀 번호를 31셀 집계 걸음에 맞게 고쳤습니다.
- smoke v2 (16:27–16:34, 고친 훅·절제): 종료 0, R1 목적값 비트 같음, 비용 최대 차 1.42e-14, R2 − R1 = 0.0, R3·null 비트 같음, 훅 14개 모두 450 걸음·오류 0. C5 절제 요청은 null 과 바이트까지 같았습니다(φ_cd 1.0·ν_cong 전환 꺼짐 = 구조상 0). 여기서 도구 결함 두 개를 찾아 고쳤습니다: 절제 굴림이 모두 같은 계획이라 훅을 행동 토큰만으로 가를 수 없던 것(→ 묶음 이름별 실행기), 훅이 없을 때 도달 점검이 예외를 낸 것.
- smoke v3 (16:35–16:45): 위 고침 뒤 `vp_jobcheck.py` 걸림 0(훅 14개, 도달 점검 8개 모두 참), 표 도구가 실제 꼴의 출력에서 멈춤 0(`vp_tablesmoke.py`, VISSIM 쪽은 합성 프레임). 절제 굴림이 기준(EXEC)과 다른지만 보면(값은 보지 않음): C1·C2·C3·C4·C7 은 다르고, C5·C6 은 블록 값까지 같았습니다(VSL 끔 상태의 구조상 0 이 §5.4 예상과 같음). 이 판 뒤에 follower 셀 행이 부모 21구간일 수 있다고 보고, follower 행은 행 수가 같을 때만 맞추는 가드를 더했습니다(smoke v4 에서 follower 도 31행이라 실제로는 같이 맞춤).
- smoke v4 (16:45–16:51, 최종 `vp_probe.py`·훅·분석 도구): 종료 0, R1 목적값 비트 같음(차 0.0), 비용 최대 차 1.42e-14, R2 − R1 = 0.0, R3·null 비트 같음, `vp_jobcheck.py` 걸림 0(훅 14개, 도달 점검 8개 참), 표 도구 멈춤 0. 기준과 다른 절제 = C1·C2·C3·C4·C7, 블록 값까지 같은 절제 = C5·C6. 벽시계 400 s(준비 50 s, AD 약 130 s, 스칼라 묶음 약 68 s, 절제 두 차례 약 145 s). 그 뒤 `vp_common.lock_acquire` 의 쉼 규칙만 고쳤습니다(잠금 함수, plant 굴림과 무관; 자체 시험 49/49).
- 배관 시험에서 화면에 나온 팔별·절제별 J 차는 smoke 상태의 값이라 결과로 쓰지 않고, 이 문서의 규칙·문턱을 정하는 데 쓰지 않았습니다 [LOG 16:30 항목].

## 2. 상태 (고정 목록)

- 규칙과 목록 파일: `VP/decl/VP_STATES.json`(도구 `vp_states.py`, sha 는 §9). 시드는 run provenance 의 `seed` 입니다(폴더 이름 아님). 결정 기록 폴더는 읽기만 합니다.
- 탐침 A·B 상태(12): 시드마다 T_low = 행동 CSV 의 FW_E VSL 행에 110 미만이 있는 결정 시각. A1 = min(T_low) − 150 (110 결정), A2 = min(T_low) (101), A3 = T_low 의 아래 중앙값 (101), A4 = max(T_low) + 150 (110). 이 문서에서 결정·블록의 "101" 은 VISSIM 에 쓴 값이고, 그 결정의 plant 명령은 100 입니다(§1.1).

| 시드 | A1 (110) | A2 (101) | A3 (101) | A4 (110) | T_low 수 |
|---|---:|---:|---:|---:|---:|
| v3c3-s31 | 3,300 | 3,450 | 4,050 | 4,800 | 9 |
| v3c3-s41 | 2,400 | 2,550 | 3,300 | 4,200 | 10 |
| v3c3-s43 | 2,700 | 2,850 | 3,750 | 5,100 | 14 |

- P1 상태(9, VSL 끔): 시드마다 T0 ∈ {1,800, 5,400, 7,200}. 결정 T, T+150, T+300 의 FW_E 행이 모두 110 이어야 합니다(아니면 T+150, +300, +450 순서로 대신). [실행] 9개 모두 T0 그대로 조건을 채웠습니다.
- 실행된 블록의 VSL(탐침 B 묶음용, 행동 CSV 에서 읽음): s31 A1 = 110·101·101, A2 = 101·101·101, A3 = 101·101·101, A4 = 110·110·110; s41 A1 = 110·101·110, A2 = 101·110·101, A3 = 101·101·101, A4 = 110·110·110; s43 A1 = 110·101·101, A2 = 101·101·101, A3 = 101·101·101, A4 = 110·110·110 [실행 VP_STATES.json `written_fwe_T/T150/T300`].
- 배관 시험 상태 v3c3-s31 T=2,400 은 어느 목록에도 없습니다(도구가 확인).

## 3. 탐침 A — plant ΔJ (Q-V3)

### 3.1 무엇을 묻나

- 우리 plant 가 V-A 결정 상태에서 VSL 110·101·100·90 을 어떻게 값매기는가. V-A 가 VSL 을 쓴 상태(plant 100 → VISSIM 101; A2·A3)와 그 앞뒤 110 상태(A1·A4)에서 봅니다.

### 3.2 계획과 팔을 거는 방법

- 도구 `vp_probe.py`(sha §9)가 어댑터를 VBS 명령줄처럼 `__main__` 으로 돌리고(`sys.path` 도 `python -B adapter.py` 와 같게), `sdmpc.solve` 하나만 탐침 함수로 바꿉니다. 탐침 함수는 `sdmpc.solve` 의 앞부분(EC/sdmpc.py:538-593)을 그대로 되풀이합니다: 직전 명령 영수증·가격 점검(`load_prices`, 정책 토큰이 기록과 같아야 통과), held 기준, 런타임 콜백, 결정 공유 질의, 3블록 좌표, `prepare_request(follower, state, forecast, reference, reference, coord, worker_bootstrap)`. 그 뒤 모든 굴림은 같은 요청 틀로 만든 `Query` 의 `evaluate` 로 합니다(작업자 경로). 탐침은 작업자 실행기를 감싸 어느 요청(sha256)이 어느 팔인지만 적습니다. 행동 파일은 쓰지 않습니다.
- 재생 묶음: `SP/j1/fix/gates/gprep.py`(sha `0482a538…`)가 결정 상태를 복사만 해서 만듭니다(상태 JSON, obs150 창과 이력, 직전 명령과 영수증). 코드 뿌리는 FRZ_K92 의 바이트 사본 GT/code_va(16:16 에 FREEZE.json 10,569 파일 sha 대조 끝, 실행 전 §8 H0 에서 다시 대조). 환경은 `k92_replay.py`(FRZ_K92 `diagnostics/sdmpc_n31_20260924/k8_gates/sa/k92_replay.py`) 꼴: provenance 의 RW_*, PYTHONPATH = 훅 폴더;deps\sdmpc;deps\sdmpc-numba, BLAS 스레드 1, PYTHONHASHSEED 0, NUMBA_NUM_THREADS 지움(D-K9-99), cwd = 코드 뿌리, python -B. 튜닝은 V-A 튜닝 그대로(sha `c8e3ee2c…`, 정책 토큰 `428e650d…`).
- REC = held(action_T) 를 블록 0 으로, action_T 에 기록된 미래 두 블록(`diagnostics.sdmpc_prediction_sequence`)을 블록 1·2 로 `sequence.pack`. held(x) = `control_from_json` → `physical_ramp_branches.held_actual_reference` → `expand_shared_vsl_action`(어댑터가 쓴 segment_vsl 함수) → `sequence.first_action` → `area_meter_finalization.prepare_held_actual_reference`. 다음 결정이 직전 명령을 읽는 길과 같습니다(EC/vissim_stackelberg_adapter.py:13158-13180, EC/sdmpc.py:556-568).
- ARM v (v ∈ {110, 101, 100, 90}) = REC 의 세 블록 모두에서 구역 머리 10 의 키 `FW_E__seg10…seg14` 를 v 로, 길 키 `FW_E` 를 FW_E 구간 키의 최솟값으로 바꾼 계획. 다른 구역(머리 0·5·15), FW_W, 미터, 신호, 오프셋, N_P*·N_UF* 는 REC 그대로입니다. V-A 가 쓴 구역이 머리 10 하나뿐이라 머리 10 에만 겁니다. plant 안에서는 셀 14–24 가 이 값을 받습니다(§1.1, 표지 셀 14·18 에서 코호트 꼬리표가 바뀜).
- 101 팔의 뜻 [읽음 EC/freeway_fd.py:90-103, :147]: plant 명령 100 이 VISSIM 분포 101 로 써지는 값이고(§1.1), plant 안의 101 은 같은 3차 m_v 곡선을 101 에서 읽은 명령입니다(knot 80·90·100·110 사이 보간). 그래서 101 팔은 "VISSIM 101" 이 아니라 100 옆의 plant 기울기를 보는 점입니다. 100 팔이 V-A 가 실제로 쓴 plant 명령입니다.
- 굴림: REC 는 AD 경로 한 번(R1), REC·REPACK·ARM 넷·EXEC 는 스칼라 경로 한 배치(동시 작업자 최대 8, 배포와 같은 `Query.evaluate` 묶음).

### 3.3 지표

- J(450 s, veh·h)와 ΔJ_v = J(ARM v) − J(ARM 110). 부호: |ΔJ| < 0.01 이면 0. ΔJ(101 − 100)도 적습니다. J(ARM v) − J(REC 스칼라)도 적습니다.
- 소유자별 비용 차(`sdmpc_omega_partition.costs`): FW_E 와 나머지 합.
- 훅(§3.6)에서: FW_E 입구 대기 veh·h(origin queue 의 시간 적분), 구역별 속도·재고 차(블록 0·1·2, w300 = 블록 0–1, w450 = 블록 0–2), 셀 8–25 속도 차(w450), 구역 veh·h 차(재고 차 × 시간).

### 3.4 점검 (어긋나면 멈춤)

- R1: REC 의 AD 경로 J 가 기록 `selected_objective` 와 비트까지 같고, 소유자별 비용 20개가 기록 `omega_partition.costs` 와 키가 같고 차가 모두 1e-9 veh·h 이하. 아니면 S-R1.
- R2: REC 스칼라 J − AD J 를 적습니다(배관 시험 0.0). 0 이 아니면 모든 ΔJ 를 "스칼라 경로" 로 표시하고 그 차를 함께 적습니다(멈추지 않음).
- R3: REPACK(identity 재포장) 스칼라 J 와 비용이 REC 스칼라와 비트 같음. 아니면 S-R3.
- R0: REC 토큰이 기록 `plan_action_token` 과 같은지 적습니다(보고만; 배관 시험에서 다름, 진단 키 구성 차이).
- 훅: 스칼라 굴림마다 걸음 450, t = T … T+449, 블록마다 150 걸음, 셀 31, 훅 오류 0. 아니면 S-HOOK. 셀 경계: 훅이 본 셀 길이 누적이 CELL_B 와 1 m 안. 아니면 S-MAP.

### 3.5 표 (`vp_analyze.py tables`)

- A1: 상태별 R1·R3, ΔJ 101·100·90, ΔJ(101−100), 100 팔의 FW_E 비용 차·다른 소유자 차·입구 대기 차.
- A2: 결정 묶음(101 상태 = A2·A3, 110 상태 = A1·A4)별 ΔJ 부호 수와 범위.
- A3: 상태 × 팔(101·100·90)의 구역 속도 차(w450).
- JSON 에 블록별 값, 셀 8–25 속도 차, 구역 veh·h 차를 모두 둡니다.

### 3.6 훅 (작업자 안, 수동)

- `vp_hooks/sitecustomize.py`(sha §9). PYTHONPATH 로만 실리고 `VP_HOOK_DIR` 이 있을 때만 켜집니다. `sys.monitoring` 으로 `LaneFreewayRuntime.advance` 하나의 시작·끝만 보고, 지역 변수 `self`·`state` 와 구성의 속성을 읽기만 합니다(모형 메서드 호출 0, 쓰기 0). 작업자의 소스 변환 finder 앞에 자기 finder 를 다시 두는 방법은 K8 SA 훅(FRZ_K92 `k8_gates/sa/sa_hooks/sitecustomize.py`)과 같습니다.
- 걸음마다 셀 재고 = 밀도 × 셀 길이 × 차로, 속도, 흐름(`state.freeway_flow`), 입구 대기를 150 s 블록으로 쌓습니다. 첫 걸음 시작에 작업자가 본 FW_E 매개변수와 시작 상태를 적습니다(§5.3 도달 점검).
- 훅이 계산을 바꾸지 않는다는 근거: 훅이 켜진 채로 R1 이 비트 같아야 합니다(배관 시험에서 같았음).

## 4. 탐침 B — plant 충실도 (Q-V3)

### 4.1 상태와 계획

- 탐침 A 와 같은 12상태. plant 쪽 주 계획 = EXEC = pack([held(action_T), held(action_{T+150}), held(action_{T+300})]) — VISSIM 이 [T, T+450) 에 실제로 돌린 블록 0 셋입니다. 보조 = REC(결정이 그린 계획). 스칼라 작업자 경로.
- 묶음은 블록 단위입니다: 블록 b 의 VSL = 결정 T+150b 의 FW_E 행(§2 의 실행된 블록 VSL). 켬 = 101, 끔 = 110.

### 4.2 VISSIM 쪽

- V-A FZP 3개를 `o2_fzp_cells.py`(sha `cff42e34…`, PRE_O1O2 도구 그대로)로 5 s 프레임 × 31셀 N·SV 로 셈. 창 [1,700, 7,700] s. 출력 `GT/out/fzp_frames/VA_v3c3-s<S>.json`.
- 블록 b = 프레임 T+150b ≤ t < T+150(b+1) (보통 30개). 150 s 당 프레임이 25개 미만이면 그 칸은 "못 냄".

### 4.3 지표와 편향

- 셀: 재고 = N/프레임 수(veh), 속도 = SV/N(km/h, Edie 공간평균), 흐름 = SV/(L·프레임 수)(veh/h, 모든 차로). plant 는 재고 = 걸음 평균, 속도 = 재고 가중 평균, 흐름 = 걸음 평균.
- 구역: 재고 = 합, 속도 = 재고 가중(plant)·SV/N(VISSIM), 흐름 = 길이 가중 평균.
- 편향 e = plant − VISSIM. 창: b0, b1, b2, w300, w450. 구역 9개(U·B1·M1·VSa·Mu′·VS0′·VSb·B2′·D), 셀 8–25.
- 시작 편향: plant 첫 걸음 전 상태 대 FZP 프레임 T−4.9·T+0.1 (셀·구역 재고·속도).
- 요약(B3): 36블록(12상태 × 3)을 블록의 실행 VSL(켬·끔)로 나눠 구역·양마다 n, 평균 e, 평균 |e|, 켬 − 끔. §2 의 행동 CSV 로 세면 켬 22블록, 끔 14블록입니다 [계산]. 한 상태의 블록끼리는 독립이 아니라서 n 은 블록 수일 뿐입니다. 검정은 하지 않습니다.

### 4.4 표

- B1 구역 속도 편향(b0/b1/b2/w450), B2 재고·흐름 편향(w450), B3 블록 묶음 요약, B4 셀 8–25 속도 편향(w450). JSON 에 REC 계획 편향, VISSIM 셀 속도(창별), 시작 편향을 둡니다.

### 4.5 읽는 법 단서 (데이터 전 고정)

- plant 의 수요는 결정 T 의 예보이고 VISSIM 은 실제 도착입니다. 이 차도 편향에 들어갑니다(P1 의 "목록 밖 항", §5.5).
- 시드마다 V-A 런 하나라서 흔들림은 모릅니다.
- 탐침 B 의 켬 − 끔 은 VSL 몫이 아닙니다. 켬 블록과 끔 블록은 시각·교통 상태가 다릅니다.

## 5. P1 — VSL 과 무관한 편향 추적 (Q-V4)

### 5.1 무엇을 찾나

- codex 판 plant 에서 VSL 끔 상태에도 VSa·VSb·M1 이 VISSIM 보다 느렸습니다(VSL_RESULTS r2 §1.6, `SP/vsl_v3c3/VSL_RESULTS.md` sha `9bbf83a3…`). 여기서는 **우리 plant** 에서 같은 자리(셀 18 = VS0′, M1, VSb 재고)를 VSL 끔 상태로 재고, 어떤 항이 그 편향을 만드는지 항을 하나씩 빼서 봅니다.

### 5.2 FZP 쪽 (VISSIM 이 보인 것)

- 원천 12개 = NC3 · VSL 단독 · V-A · B × v3c3-s31·s41·s43 (`VP/decl/VP_FZP_SOURCES.json`, 선언 폴더만 열고 디렉터리 훑기 없음). 스캐너 `vsl_cell_scan.py`(sha `fa5aeafd…`, VSL 워크플로 도구 그대로): 31셀 × 60 s 창 × 차로 1–4 의 N·SV. NC3·VSL 출력은 기존 것을 sha 로 재사용, B·V-A 6개는 새로 셈(`GT/out/fzp_cell/`).
- 창 조건: 900 ≤ t0, t0 + 60 ≤ 9,000, 프레임 12. 저밀도 = k = (N/12)/(L·차로) ≤ 12 veh/km/차로.
- P1-F 지표(셀 8–25, 원천마다): 저밀도 창의 속도 중앙·k 중앙·창 수, 차로당 최대 60 s 흐름과 그때 k, 속도 < 60 km/h 창 비율, 저밀도 차로별 속도 중앙, 셀 18 에서 (셀 18 속도 − 셀 16–17 속도)의 저밀도 중앙. V-A 는 VSL 이 걸린 기간([min T_low, max T_low + 600) s)을 뺀 판도 적습니다.

### 5.3 plant 쪽

- P1 9상태에서 EXEC(세 블록 모두 110)를 스칼라 작업자 경로로 굴려 V-A FZP 와 대조합니다(정의는 §4.3). 이 상태들에서도 R1·R3 를 같은 규칙으로 점검합니다.
- 기준 편향 지표: m1 VSa 속도, m2 M1 속도, m3 VSb 재고, m4 VSb 속도, m5 VS0′(셀 18) 속도. 창 w450(C7 만 b0).
- 절제 = 요청 틀을 unpickle 한 사본(`t['owned']` 의 state·follower)에서 구성 값만 바꾸고, 그 사본으로 만든 `Query` 로 EXEC 를 굴림. 코드 객체는 바꾸지 않습니다. 바꾸는 곳은 FW_E 구성 사본 `state.lane_freeway_runtime.configs['FW_E'].network`(plant 걸음이 실제로 쓰는 구성)입니다. follower 구성의 셀 행은 같은 셀(행 수 31)을 나타낼 때만 같이 맞춥니다. V-A follower 의 FW_E 셀 행도 31행이라 같이 맞춥니다 [실행 smoke v4, 절제 기록 `component_rows_n` = `follower_rows_n` = 31, `follower_rows_patched` 참].
- null 절제(아무것도 안 바꾼 사본)의 J·비용이 EXEC 와 비트 같아야 합니다(아니면 S-NULL).
- 도달 점검: 각 절제 굴림의 훅 스냅샷(작업자가 본 값)이 바꾼 값과 같아야 합니다(아니면 S-REACH).

### 5.4 후보 원인 목록 (고정, 7개)과 시험

| # | 후보(plant 항) | 코드 자리 | 절제(바꾸는 값) | 그 항을 가리키는 결과 |
|---|---|---|---|---|
| C1 | 셀 자유 속도 v_free | 어댑터 :9548-9560 (행 `v_free`) | 셀 8–25 의 v_free 를 VISSIM 저밀도 점에 맞춘 값으로: v_free′ = s_med / exp(−(k_med/ρ_c)^a / a), (k_med, s_med) = NC3 세 시드를 모은 저밀도 창의 중앙(창 20개 미만인 셀은 바꾸지 않음), ρ_c·a 는 그 셀 plant 값 | 가리킴 규칙(아래) 충족. 함께 P1-P 의 "plant FD 속도(같은 k) − VISSIM 속도" 를 적음 |
| C2 | FD 혼잡 갈래(ρ_c) | 어댑터 :9548-9560 (행 `rho_crit`) | 셀 8–25 의 ρ_c × 1.2 (φ_cd 문턱인 링크 스칼라 ρ_c 는 그대로) | 가리킴 규칙 충족. 함께 VISSIM 차로당 최대 흐름 때 k 와 plant ρ_c 를 적음 |
| C3 | 합류 감속 δ | AFA :162, :393-396 | FW_E δ = 0 (구성 스칼라와 방향별 값) | 가리킴 규칙 충족 |
| C4 | 차로 감소항 φ_lane (셀 18) | 어댑터 :9597-9602 | FW_E φ_lane = 0 | 가리킴 규칙 충족. 함께 P1-F 의 셀 18 − 셀 16–17 저밀도 속도 차를 적음 |
| C5 | 용량 감소(φ_cd 방류 상한 + ν_cong 전환) | AFA :133, :213-216; metanet.py:125-137 | φ_cd = 1.0, ν_cong 전환 끔 | 가리킴 규칙 충족. 두 값이 이미 꺼져 있으면 기준과 비트 같음 = "구조상 0" 으로 적음 |
| C6 | 준수 법칙(Carlson + m_v)과 코호트 | AFA :200-209, :382-387; freeway_fd.py:115-152, :283- | FW_E 의 `freeway_vsl_fd_response`·`component_vsl_transport`·`component_vsl_initial_commands`·코호트 상태를 뺌 | 가리킴 규칙 충족. VSL 끔 상태(초기 꼬리표 모두 110, 명령 모두 110)에서는 비트 같음이 예상 = "구조상 0" |
| C7 | 초기 상태 투영 | 관측 → plant 시작 상태 | 셀 8–25 의 시작 속도(`state.freeway_speed`)를 V-A FZP 프레임 T−4.9·T+0.1 의 셀 Edie 속도로(그 셀에 차가 없으면 그대로; 시작 밀도·재고는 그대로) | 창 b0 에서 가리킴 규칙 충족. 함께 시작 편향(§4.3)과 b0 편향의 비를 적음 |

- 줄임 비율 R_c,m = 1 − |e_c,m| / |e_0,m| (e_0 = 같은 상태 EXEC 의 기준 편향, e_c = 절제 굴림의 편향, 같은 VISSIM). |e_0| < 1 km/h(속도) 또는 < 1 veh(재고)이면 R 은 정의하지 않습니다.
- 가리킴 규칙(후보 c, 지표 m): 정의된 상태 수 n ≥ 6, R ≥ 0.5 인 상태가 ⌈2n/3⌉ 이상, 중앙 R ≥ 0.5. 충족하면 "c 가 m 편향을 가리킴" 으로 적습니다. 중앙 R ≤ −0.2 이면 "c 를 빼면 m 편향이 커짐" 으로 적습니다. 띠: 중앙 R ≥ 0.5 = A, 0.2 ≤ 중앙 R < 0.5 = B, 그 밖 = C.
- 여러 후보가 같은 지표를 가리킬 수 있습니다. 항끼리의 겹침은 이번에 가르지 않습니다(한 번에 하나만 뺌).

### 5.5 목록 밖 항 (이번에 빼지 않음)

- 출구 막힘 속도 상한(AFA :354; FW_E 출구가 셀 9·11·18·20 에 있어 셀 18 에도 걸릴 수 있음), 이완·예견 τ·ν·κ, 입구 원천 용량과 수요 예보, 끝 경계, 차로 프로파일의 출구 역류 감소, 신호·도시 쪽에서 오는 합류 램프 방출(미터 굴림은 REC·EXEC 그대로). Hadi 수용 상한은 V-A FW_E 에 없습니다(§1.1). 일곱 후보가 모두 가리키지 않으면 "목록 밖 항에 남음" 으로 적고, 다음 단계는 사용자가 정합니다.

### 5.6 표

- P1-F(원천 12 × 셀 8–25 저밀도 속도 중앙, 셀 18 − 셀 16–17), P1-P(작업자가 본 매개변수, VISSIM 저밀도 점, plant FD 속도, C1 값), P1-B(상태별 기준 편향 m1–m5, 시작 편향), P1-R(후보 × 지표의 n, R ≥ 0.5 수, R ≤ −0.2 수, 중앙 R, 띠, 규칙 충족, 기준과 비트 같은 상태 수). 도달 점검·비트 같음은 JSON 에 상태별로 둡니다.

## 6. 산출물

- 결정 상태·원천: `VP/decl/VP_STATES.json`, `VP/decl/VP_FZP_SOURCES.json`, `VP/decl/jobs_fzp.json`, `VP/decl/specs/spec_A_*.json`·`jobs_A.json`.
- plant 일: `GT/out/plant_A/<시드>_T<T>/`, `GT/out/plant_P/<시드>_T<T>/` 마다 `probe.json`, `hooks/vphook_*.json`, `job_summary.json`, `bundle/`(재생 사본), 로그.
- FZP: `GT/out/fzp_cell/<원천>.json`, `GT/out/fzp_frames/VA_v3c3-s<S>.json`.
- P1 입력·명세(데이터 뒤 기계적 생성, 규칙은 §5.4): `GT/out/p1_specs/p1_inputs.json`, `spec_P_*.json`, `jobs_P.json`.
- 표: `GT/out/tables/vp_tables.json`, `vp_tables.md`. 보고: `VP/VP_RESULTS.md`(다음 단계), 사본 RVP.
- 로그: `VP/LOG.md`(KST 덧붙임), `VP/logs/<일 묶음>/queue.log`, plant 일마다 `jobcheck.json`(멈춤 규칙 점검).

## 7. 멈춤 규칙 (걸리면 남은 무거운 일을 하지 않고 보고, 사용자가 정함)

- S-R1: R1 이 어긋남(§3.4). 그 일에서 탐침이 스스로 멈추고(종료 코드 5), 큐가 `VP/STOP_VP` 를 씀.
- S-R3: REPACK 이 REC 와 비트 다름. S-NULL: null 절제가 EXEC 와 비트 다름. S-REACH: 절제 값이 작업자에 닿지 않음. S-HOOK: 훅 걸음·블록·셀 수가 어긋나거나 훅 오류. S-MAP: 셀 경계가 CELL_B 와 1 m 넘게 다름.
- S-ERR: 탐침 예외, 재생 묶음 실패, 핀 sha 다름, 디스크 < 8 GB.
- S-BLIND: 봉인 시드(37·59·61·67)·v3c3-s47·`sealed` 이름이 걸림(도구가 거부).
- 각 plant 일(H2·H3)이 끝나면 큐가 `vp_jobcheck.py` 로 S-R1·S-R3·S-NULL·S-HOOK·S-MAP·S-REACH·S-ERR 를 바로 보고, 하나라도 걸리면 `VP/STOP_VP` 를 쓰고 남은 일을 하지 않습니다(그 일의 `jobcheck.json` 에 이유).
- 표 도구도 걸린 규칙을 "멈춤 규칙 걸림" 칸에 모두 적습니다. 걸림이 있으면 그 상태의 표 칸은 쓰지 않고 보고에 이유를 적습니다.
- 워치독: plant 일 하나가 45 분 동안 출력·진행 파일을 바꾸지 않으면 그 일의 자기 프로세스 트리만 끝냅니다(다른 세션의 VISSIM·python 은 건드리지 않음).

## 8. 순서와 비용 (가벼운 것 먼저)

| 단계 | 일 | 잠금 | 어림 시간 |
|---|---|---|---|
| L0 | 핀 대조(VP 에서 `sha256sum -c SHA256SUMS_VP.txt` 와 `sha256sum -c SHA256SUMS_VP_EXT.txt`; 하나라도 다르면 S-ERR), 자체 시험 다시(`vp_selftest.py`, 모두 참이어야 함) | 없음 | 1 분 |
| H0 | 코드 사본 다시 대조(`vp_tree.py verify`, FREEZE.json 10,569 파일; 어긋나면 S-ERR) | 잡음 | 3–5 분 |
| L1 | `vp_analyze.py p1-fzp` — 이미 있는 NC3·VSL 스캔으로 P1-F 일부 | 없음 | 1 분 |
| H1 | FZP 스캔 9개(`decl/jobs_fzp.json`: B·V-A 셀 스캔 6, V-A 프레임 3; FZP 하나 약 1.1 GB 읽기) | 일마다 | 30–60 분 |
| L2 | `vp_analyze.py p1-inputs GT/out/p1_specs` — C1·C7 값, P1 명세 9개 | 없음 | 1 분 |
| H2 | 탐침 A·B 12상태(`decl/specs/jobs_A.json`) | 일마다 | 상태당 약 4.5–7 분(준비 약 50 s + AD 약 150–235 s + 스칼라 묶음 약 70 s; smoke 세 번 실측, 다른 작업이 돌면 느려짐), 합 약 1–1.4 시간 |
| H3 | P1 9상태(`GT/out/p1_specs/jobs_P.json`) | 일마다 | 상태당 약 6.5–9 분(위 + 절제 8개를 동시 4개씩 두 차례, 한 차례 약 66 s), 합 약 1–1.4 시간 |
| L3 | `vp_analyze.py tables GT/out/tables/vp_tables.json …md` | 없음 | 1 분 |

- 무거운 일은 `vp_launch.ps1` → `vp_queue.py`(WMI 분리, BELOW_NORMAL, PYTHONHASHSEED=0, python -B, NUMBA_NUM_THREADS 지움). 공유 잠금 `D:/VISSIM-merge/k8_gate_trees/heavy.lock` 을 일마다 배타 생성으로 잡고, 자기 것만 지우며, 풀고 나서 20 s 이상 쉰 뒤 다시 잡습니다(C1 guard design·C1 워크플로와 차례). 폴링은 9 분 이하.
- 끊기면 다시 띄웁니다. 끝난 일(`.done`)은 건너뛰고, 중간에 끊긴 일의 출력은 `*_interrupted_*` 로 옮긴 뒤 다시 합니다.
- 탐침 B 와 P1 은 H2·H3 의 같은 굴림에서 나옵니다(굴림을 따로 하지 않음).

## 9. 도구 핀 (이 문서와 함께 고정)

- 핀 목록 파일 `VP/SHA256SUMS_VP.txt`(VP 기준 상대 경로, `sha256sum -c` 로 대조)와 `VP/SHA256SUMS_VP_EXT.txt`(재사용 도구·재사용 스캔 출력·FREEZE.json·코드 사본 기록·smoke v4 기록, 절대 경로). 주요 sha:
  - `tools/vp_probe.py` `c38fc1a98ae21f8e0b2fa845ec1e0ff37ef78526280e7a946b66270fa5478386`
  - `tools/vp_hooks/sitecustomize.py` `1c212040b781eca8d39ed8d98c13cb141abf00ba41c3af626a3dc8ae481f6fd7`
  - `tools/vp_job.py` `2164f97ed16bcbd3e2c095ea23435f9524ab0695c6a9a1533016dbe297d94baf`
  - `tools/vp_queue.py` `53efbad49aece715e05bf1c28ac473daac9f8a3ec8bcdf5da5790c5639c94e3d`
  - `tools/vp_jobcheck.py` `a922ab6d6bb7b8e06ad1b0d00123844a6931d7c9071787cca3cde980a54c0ae7`
  - `tools/vp_common.py` `a8cdeff508c72ceb320a4dd98a555820016678e6b9d1c98d132a50ae2eed6691`
  - `tools/vp_analyze.py` `faff15d49d2d7a2b82b2487a16b90298fe9a97969608d17b4509d560c839f326`
  - `tools/vp_selftest.py` `2834d8292fe37d1d085d76f316cd408dd91c24f92c35b0db55a0a9e1cae5b343`
  - `tools/vp_states.py` `1ff348f5f96971118f68f626389b4547cb02093b824211d64598b77ff06d1dfe`
  - `tools/vp_fzp.py` `e93103526b2bfe5c1904b16ebf87e344d75944ac780558093f119c50e5a9b469`
  - `tools/vp_tree.py` `c84d53b07ca3f6b63a665bd51835f765160ff13d0d835546c4045a3cebe69cca`
  - `tools/vp_pinned.py` `eedaf1b73f8c4d46ec8471c2a3ec3205092e64333937f5a8a60002ee2e690b29`
  - `tools/vp_launch.ps1` `efbc4ebfb536f602fdf8e2438432016964b3b9aae91e676c59db85c8d3221247`
  - `decl/VP_STATES.json` `8f09c649522e43fffa87ee9ce2042ea1b8e1c08175a3c6238bf1839410f44fc8`
  - `decl/VP_FZP_SOURCES.json` `2bdf0e7d75c14b78b4c0124861e4ec85bd08b84441fe9165318be84e8aaa5a14`
  - `decl/jobs_fzp.json` `3b4f96a4abe7d1a90dc41a7e46b7d9ad0f8164ae8be3cc1445d2d4d065165638`
  - `decl/specs/jobs_A.json` `b68e18f2860f9735ce93b9336f7a2f8e1bbc9750c1bbe6dca139e3d2e9587c3f`
  - `selftest/selftest_final.json` `6f45abbe3bce39df223ffcd862bb1a3c34db5a094047a9d71c2371323cc977d7`
  - 핀 목록 `SHA256SUMS_VP.txt` (33줄) `5c36cffa81b680eb06605e9085e59269f664de27e1bf797d2798f388c30a4410`, 바깥 핀 `SHA256SUMS_VP_EXT.txt` `7ce3016bf9214f3eae4068f36daef6d25e5482d2d26ad0ec0664e08158921cb1`
- 재사용(남의 도구, 바이트 그대로 sha 로 실행): `SP/vsl_v3c3/tools/vsl_cell_scan.py` `fa5aeafd01c99297652f8f5fce6d5f760cdbb223640b3258d2020cd03229a078`, `SP/vsl_v3c3/o1o2/tools/o2_fzp_cells.py` `cff42e34d518bb5d1864fcd5d9c503b329037007f73947564088362c3a412013`, `SP/j1/fix/gates/gprep.py` `0482a53868fd3ee644724dab2dcb6af2c56d749708ccec5242f6b3549ae26f22`(그 안에서 FRZ_K8′ 의 `make_replay_state_v2.py` 를 부름, sha 는 EXT 목록).
- 코드 뿌리 GT/code_va = FRZ_K92 사본, FREEZE.json sha `011f5be253fd31a5fb8342859b2b571375e49b4bbbbb42ea8f3ca93657b68476`, 대조 기록 `GT/code_va.tree.json`(10,569/10,569).

## 10. 하지 않는 것

- VISSIM·COM·러너 실행 0, 동결 0, 커밋·푸시 0, GWT8 손대지 않음(c20aff1d 그대로), FRZ_K92·런 폴더 쓰기 0.
- 금지 시험 0: test_b1a_watchdog_attempt_launch.py, run_plant_fidelity_matrix, test_runner_ps1_obs150.py, test_native_vbs_clock.py, test_tools_launch.py, test_tools_replay.py, real_watchdog.
- 봉인 시드 37·59·61·67 열기 0, codex 64cf-s59/s61/s67 숫자 0, v3c3-s47 값 0.
- φ 사잇값(Q-V5) 0. 새 VSL VISSIM 런(D-K9-102) 0.
- 바뀐 정책 토큰으로 결정 전체를 다시 푸는 재생 0(가격 적재에서 멈춤; 대신 기록 상태에서 한 결정짜리 plant 굴림만 함).
