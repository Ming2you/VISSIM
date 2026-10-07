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
| K8b-4 팔 파일 | 이 커밋 | `k8b4/gate_G1.json` | `k8b4/gate_G2.json` | — | — | — |

- G1 기준값: `anchor_k84v3/`(트리 `r84v3` = `git archive ec063ffa`, r84g와 파일·바이트 같음). full 2700 BASE objective 496.8425457870215 / held 506.0624474786317 / CSV `28d36ba1…` = k8_gates_out_v2 k84g와 같음. 도구의 G1 단위 로그는 `test_stopline_approach.py`만이라, SA 단위 세 파일 전부(배선 시험은 K8 작업트리 git 객체, `K8_SA_BASE_REV=ec063ffa`)로 G-EB-1을 다시 계산한 `gate_G1_full_units.json`을 함께 둡니다(모두 PASS).
- K8b-1 G4: 도구(`k8b_commit_gates.g4 --part p1`)가 문자열 잎 `/tuning/sha256` 하나(키 튜닝 `0247c8aa…` vs 탐침의 SAF 팔 `178de6c2…`)까지 같음을 요구해 FAIL을 냈습니다. 선언은 "숫자 필드, 원천 해시·플래그 기록 필드 제외, 메타 이름 대응표 고정"이므로 같은 산출을 선언 규칙으로 다시 판정한 `k8b1/gate_G4_p1_declared.json`이 PASS입니다(틀 숫자 40,552 / 41,432 차 0, capture 숫자 265 / 325 차 0, 메타 대응 5/5). 다시 돌린 계산은 없습니다.
- 개발 점검(커밋 전, 작업트리 전 키 상태, 탐침 표본만): `dev/gate_G4_all.json` = 미니 탐침 A7′ H3 4상태·L2 H27 비트 동일, `dev/dev_adfull.json` s31 3300 p4 / p2 / 전 키 모두 완전 일치.

## 판정 단계로 넘길 것

- 판정 팔: BASE = `config_n31_v2.json`(319d07aa), SAF-K8b / SAG-K8b = 위 팔 파일. 하네스 출력 `D:/VISSIM-merge/k8_gates_out_v3`, `--gates-stage k8bt --declaration-sha e8ad8a34…` 로만 판정 상태에서 키를 켤 수 있음(K8b-0 가드).
- 순서·문턱·표본은 보충 16 §5·§6·§7 그대로입니다.
