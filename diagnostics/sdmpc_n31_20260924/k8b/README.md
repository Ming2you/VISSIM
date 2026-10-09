# K8b — SC1001 EB 결함 수정 묶음 (P-1·P-2·P-4′·P-4b, 키 전용)

구속: `K8_PREDECLARATION_AMENDMENT_16.md` r2(sha `e8ad8a34…cbc4`) + `K8_PREDECLARATION_AMENDMENT_17.md`(sha `5bb43134…07b4`), 사용자 결정 `K8B_USER_DECISIONS_20261007.md`(sha `5d565e35…`, D-K8b-1…4, 변형 A). 탐침 근거 `D:/VISSIM-merge/k8b_probe/`, 미니 탐침 v2 `D:/VISSIM-merge/k8b_miniprobe/MINI_V2.md`(`2b3e999d…`)·`MINI_V2_CHECK.md`(`69f10492…`). 판정 단계(보충 16 §5)는 이 폴더의 커밋들 뒤에 따로 시작합니다. 판정 상태에서 K8b 키를 켠 계산은 여기까지 0회입니다.

## 키 (config 키만; 세 키가 모두 없으면 런타임은 K8-6c와 같은 경로)

| 키 | 수정 | 코드 | 증거(값의 단일 출처) |
|---|---|---|---|
| `urban.sc1002w_saturation` | P-1: SC1002 W internal movement 3개 용량 = U4 F2(30\|p3 1,674.9 ×2차로, 30\|p4 1,706.7 ×1차로), 훅 시점 template β로 E/S 분할 | `runtime_setup.install_sc1002w_saturation`(포착 시점, `install_measured_movement_capacity` 직후) | `sc1002w_saturation_v3c3_20261007.json` (`32e48781…`) |
| `urban.wout_exit_law` | P-4′: W_out 출구 법칙을 부류×목적지 저장고로; P-4b: 10483 직결 부류(체류 = ⌈121.533 m / 60 km/h⌉ = 8 스텝 예약 하나, 만기 뒤 f = 1), 변형 A(신호 출신 부류 = 실측 분할 0.5115/0.3213/0.1672, 직결 = 100 % free) | `runtime_setup.install_wout_exit_law`(포착 시점), `urban_flow_accounting.legsplit_substep_accounted`·`_wout_*`, `lane_offramp_runtime` 직결 행 → `urban_flow_accounting.wout_direct_delay` | `wout_exit_v3c3_20261007.json` (`314b5c8e…`) |
| `urban.stopline_approach.city_arrival` | P-2: in_SC1001_W 도시 도착 운동학(창 β̂, d_g = ⌈D_g / max(ū_32, 20 km/h)⌉, 초기 W 몫 차량별 127 진입, 127 진입 = SA 이동 패킷) | `stopline_approach.city_arrival_prepare/_initialize/city_gate_step/_land_city/_skip_tiny_city_moving_share`, `split_arrival`, RS 훅 #3, UFA 게이트 루프 | `city_arrival_v3c3_20261007.json` (`ef75c8e6…`) |

- 불변식 위반은 `StoplineInvariantError`(P-2)·`WoutExitInvariantError`(P-4′/P-4b, 하네스 종류 invariant), 설정 오류는 `ValueError`/`StoplineConfigError`.
- 증거 빌더 `build_k8b_evidence.py p1|p4|p2 [--check]`: VISSIM 원자료(FZP·x2 parquet·.inpx·.sig, sha 기록)에서 다시 유도, `--check`는 커밋된 `values`와 비트 비교(다르면 `K8B_EVIDENCE_STOP`, 종료 1).
- 팔 파일(K8b-4): `../config_n31_v2_stopline_observed_full_k8b.json`(`af2a7783…`)·`../config_n31_v2_stopline_geometric_k8b.json`(`f5189611…`) = k86h SA 팔(178de6c2 / 26e3be09) + 세 키. 생성: `python -B diagnostics/sdmpc_n31_20260924/make_config_n31.py --stopline-approach diagnostics/sdmpc_n31_20260924/stopline/sc1001eb_evidence_v3c3_20261004.json --stopline-storage observed_full|geometric --k8b [--check]`. 팔 동일성: `k8_gates/sa/sa_arms.py --source repo --k8b`(BASE 319d07aa, 네 경로 밖 차이 0, 세 키를 지운 값 = k86h 팔).

## 커밋과 커밋별 관문 (보충 16 §4.1; 출력 `D:/VISSIM-merge/k8b_commit_gates/<커밋>/`, 트리 `D:/VISSIM-merge/k8_gate_trees/<커밋>` = `git archive`)

| 커밋 | sha | G1 키 없음 = ec063ff | G2 키 끈 SAF = k86h | G3 키 켬 예상 차이 | G4 탐침 재현 | 빌더 `--check` |
|---|---|---|---|---|---|---|
| K8b-0 하네스 | `315b7cc4` | PASS | PASS | — | — | — |
| K8b-1 P-1 | `264d1565` | PASS | PASS | PASS (첫 스텝 용량 오차 0 ×3, 다른 movement 0) | 선언 규칙 PASS (도구 판정 FAIL, 아래) | p1 OK |
| K8b-2 P-4′+P-4b | `c242071b` | PASS | PASS | PASS (shrink 0, X[direct] 유입 > 0, adfull 3.6e-12) | — | p4 OK |
| K8b-3 P-2 | `a6e4d414` | PASS | PASS | PASS (도시 도착 계수 있음, room fallback 0, 대기 = 시드 차감, adfull 9.1e-13) | PASS (A7′ H3 4상태·L2 H27 숫자 잎 차 0) | p2 OK (같은 빌더로 p1·p4 재확인 OK) |
| K8b-4 팔 파일 | `9b0ea891` | `k8b4/gate_G1.json` | `k8b4/gate_G2.json` | — | — | — |
| K8b-5a 관문 도구(진단 전용) | `85d441be` | — (런타임·하네스 실행 파일 불변) | — | — | K8b-1 G4 재실행 `k8b1_g4r/gate_G4_p1.json` PASS(아래) | — |
| K8b-5b 계수기·잠복 패리티 | 이 커밋 | `k8b5/gate_G1.json` | `k8b5/gate_G2.json` | G5 `k8b5/gate_G5.json`, G6 `k8b5/gate_G6.json`(보충 18 §3.3) | — | `k8b5/` 기록 |

- G1 기준값: `anchor_k84v3/`(트리 `r84v3` = `git archive ec063ffa`, r84g와 파일·바이트 같음). full 2700 BASE objective 496.8425457870215 / held 506.0624474786317 / CSV `28d36ba1…` = k8_gates_out_v2 k84g와 같음. 도구의 G1 단위 로그는 `test_stopline_approach.py`만이라, SA 단위 세 파일 전부(배선 시험은 K8 작업트리 git 객체, `K8_SA_BASE_REV=ec063ffa`)로 G-EB-1을 다시 계산한 `gate_G1_full_units.json`을 함께 둡니다(모두 PASS).
- K8b-1 G4: 도구(`k8b_commit_gates.g4 --part p1`)가 문자열 잎 `/tuning/sha256` 하나(키 튜닝 `0247c8aa…` vs 탐침의 SAF 팔 `178de6c2…`)까지 같음을 요구해 FAIL을 냈습니다. 선언은 "숫자 필드, 원천 해시·플래그 기록 필드 제외, 메타 이름 대응표 고정"이므로 같은 산출을 선언 규칙으로 다시 판정한 `k8b1/gate_G4_p1_declared.json`이 PASS입니다(틀 숫자 40,552 / 41,432 차 0, capture 숫자 265 / 325 차 0, 메타 대응 5/5). 다시 돌린 계산은 없습니다.
- K8b-1 G4 재실행(보충 18 §3.2, D-K8b-6): K8b-5a 도구(g4 p1 = 숫자 잎만 판정)로 코드 루트 `k8b1`(264d1565, 블롭 대조)에서 포착 2개를 새로 계산해 `k8b1_g4r/gate_G4_p1.json` **PASS**(틀 숫자 40,552 / 41,432 차 0, capture 숫자 265 / 325 차 0, 메타 대응 5/5). 목록만: 문자열 잎 `/tuning/sha256` 하나 = **튜닝 파일 해시**(키 파일 `0247c8aa…` 대 탐침 k86h SAF `178de6c2…`; 숫자 규칙상 비교 밖, 런타임 원천 해시가 아님), 한쪽 잎 12 / 0(`metadata/k8b_p1/*`, 탐침은 같은 값을 `net.k8b_probe_capture.P1`에 두어 메타 대응표로 비교). 10-07의 스크래치 재판정(`gate_G4_p1_declared.json`)은 이 재실행으로 대체됩니다.
- 개발 점검(커밋 전, 작업트리 전 키 상태, 탐침 표본만): `dev/gate_G4_all.json` = 미니 탐침 A7′ H3 4상태·L2 H27 비트 동일, `dev/dev_adfull.json` s31 3300 p4 / p2 / 전 키 모두 완전 일치.

## K8b-5 (보충 18 `ad20a934…`, 결정 D-K8b-5·D-K8b-6, 결정 파일 `58696db7…`; 판정 뒤 런타임 수정)

판정(k8bt) STOP 뒤 진단 D-c가 찾은 계수기 패리티 결함(`TL3_2700_SAF_A1_H3_ADREF_ad_full` idx 3019: 스칼라 Δ = 0.0, 탄젠트 Δ = −2⁻⁵¹ → `shrink_tiny_events` 28 대 29, adfull 오차 1.0)과 같은 원칙의 잠복 자리를 고칩니다. 원칙(§2.3.1): 비교 상태에 저장되는 구조(dict 키, 방문 계수기)는 정수 술어나 구조적 값에서 1e-9 떨어진 띠 술어로만 정하고, 정확 산술이 경계에 정확히 놓는 값(새 도착 없는 Δ = 0, 빈 포트·만차 저장의 0)의 부호로 정하지 않습니다. 값 산술은 그대로입니다.

| 자리 | 수정 | 계수기 이름 |
|---|---|---|
| UFA `_wout_store_update` 근-균형 | 갈래와 무관하게 원시 \|Δ\| ≤ 1e-9 방문을 셈(산술 줄·`shrink_events`·`shrink_veh` 불변) | `shrink_tiny_events` → `near_balance_events` |
| A-1 LOR 직결 행(`n<=0`, 빈 포트·W_out 여유 0) | `n<=0`이어도 새 `urban_flow_accounting.wout_direct_touch`가 같은 pending 키(step + d)와 계수 행을 만듦(값 더하기 없음); 방출·만기 계수는 원시값 > 1e-9 띠 | `direct_release_events` → `direct_release_band_events`, `direct_matured_events` → `direct_matured_band_events` |
| A-2 SA `_land_city` 차로 몫 예약(in_SC1001_W 만차 → 몫 0.0 대 O(1e-16)) | K8b 전용 도우미 `_schedule_city_share`: due 키는 몫 부호와 무관, 양수 몫은 `uqm._schedule`과 같은 산술, 아니면 0.0 키(UQM 불변) | — |

- 고치지 않은 자리: SA rest 술어(`p2_room_fallback_events`, frac = 1이면 두 런 모두 rest = 0.0 정확) — 합성 시험에서 K8b-4도 패리티 성립, 시험만 남김. K8b 전 잠복(LOR:89 아래 UQM `_schedule` 예약 키, UFA `arrived <= 0.0`)은 보고만.
- 시험: `tests/test_k8b_p4.py` `WoutCounterParityTests`(선언 다섯 경우, 기대 1/1/1/0/0)·`DirectRowParityTests`, `tests/test_k8b_p2.py` `CityLandingParityTests`; A-1·A-2는 새 탐침 `tests/k8b5_parity_probe.py`(탄젠트 Finder를 설치한 새 하위 프로세스, forward·reverse-v1, 스칼라 0.0 대 Dual +2⁻⁵¹, `sdmpc_tangent_worker.state_error`)를 씀. K8b-4 런타임에서는 셋 다 실패, 이 커밋에서는 통과.
- 파급: K8b-0 기록기 잎 `k8b0.wout_counters.<이름>`이 새 이름으로 바뀜. R6 경보 규칙(`shrink_veh`)은 그대로이고, R6 보고 행(`shrink`로 시작하는 키)에는 `near_balance_events`가 나오지 않음.
- 관문(보충 18 §3.3, 출력 `D:/VISSIM-merge/k8b_commit_gates/k8b5/`): U5 단위·B 빌더 `--check` → G2 → G5(탐침 26상태 키 켬 OBS, K8b-4 대 K8b-5 비트 동일, 이름 바뀐 계수기 쌍만 한쪽 잎) → G6(탐침 8상태 ADREF + s31 3300 ADM2ALL adfull ≤ 1e-8) → R-ctl(K8b-4 트리 대조, 보고) → G1. 판정 상태에서 K8b-5 키 켬 계산은 0회입니다(보충 18 §4).

## 판정 단계로 넘길 것

- 판정 팔: BASE = `config_n31_v2.json`(319d07aa), SAF-K8b / SAG-K8b = 위 팔 파일. 하네스 출력 `D:/VISSIM-merge/k8_gates_out_v3`, `--gates-stage k8bt --declaration-sha e8ad8a34…` 로만 판정 상태에서 키를 켤 수 있음(K8b-0 가드).
- 순서·문턱·표본은 보충 16 §5·§6·§7 그대로입니다.
