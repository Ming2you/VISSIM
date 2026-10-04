# L0/L1 all-110 런 상태 점검 (P10, 2026-09-28)

> 서브에이전트 Write 가 막혀 메인 세션이 워크플로 결과(wf_be1afaf0-164, l0l1)를 그대로 저장함.

## 판정
통과했습니다. R-obs 상태 네 개(900·3600·4800·6300 s)에서 모든 VSL 명령을 110으로 두고 plant 롤아웃을 돌렸고, L1 reference와 L0 변형 두 개(L0a: 법칙만 A0.5/E4로 바꿈, L0b: cf3ce37 reference 원본)의 예측 값이 비트 단위로 같습니다. 비교 범위는 두 도로, 450 스텝, 매 스텝의 cost·진단·밀도·속도·흐름·차로·원점 큐와 VSL cohort입니다. 도로·케이스당 float 101,250개를 Python == 와 float.hex sha256 두 방식으로 대조했습니다. FW_E VSL 축(zone head 0/5/10/15) 도함수는 16쌍(축 4 × 상태 4) 모두 L0와 L1에서 다릅니다. 비교한 양은 110 한쪽 dTTT·dN_end와 100 dTTT·dN_end입니다. FW_W 열은 세 reference 모두 0입니다. [실행]

# L0/L1 all-110 런 상태 점검 (REPIN_PLAN §5.5-1, 런 상태 부분)

※ L0L1_REPORT.md는 쓰지 못했습니다. 서브에이전트 Write 도구가 보고서 파일 쓰기를 막았습니다("Subagents should return findings as text"). 아래 본문이 그 보고서 내용입니다. 표의 숫자는 render_tables.py 출력에서 그대로 옮겼습니다.

## 1. 판정 [실행]
- **all-110 예측 값: IDENTICAL.**
  - 대조: L1(`reference_config_n31_v2.json` 6c597e25) 대 L0a(1d13d78c, L1에서 `freeway.vsl_fd_response.FW_E`의 A 0.94→0.5, E 1.44→4.0만 바꿈)와 L0b(2c4857f4, `git show cf3ce37:<reference>` 그대로. vsl_set 50..110, 주석 두 개도 다름).
  - 범위: 상태 4개 × 도로 2개 × 450 스텝 전부. 매 스텝의 (cost, diag, density, speed, flow, lanes, origin queue), 최종 VSL cohort·tangent·residual, TTT·블록 3개·종단 차량 수가 Python == 로 같습니다. float.hex 정규화 sha256도 같습니다. NaN은 없고, 입력(forcing, binding, cohort 초기값, 셀 계수, 관측 source, VSL 맵)도 같습니다.
  - all110 digest(L1 = L0a = L0b, FW_E / FW_W):

    | T | FW_E | FW_W |
    |---|---|---|
    | 900 | 8710ad711846c7ff | 6ec1d1b8462d91cc |
    | 3600 | 6b59526ff764112b | 3ff0455e79654790 |
    | 4800 | 38f39f0f92ddd512 | 87cff04bf4a8d0a4 |
    | 6300 | 60887abb269b57a0 | 0ef2b2b113b31030 |
- **FW_E VSL 축 도함수: 다름.**
  - 16쌍 모두에서 네 가지 양(d_ttt110, d_veh110, d_ttt100, d_veh100)이 L0 ≠ L1입니다.
  - 순방향 AD의 primal@110(hex)은 세 reference에서 같습니다. 같은 프로세스 안의 plain 110 롤아웃도 세 reference에서 같습니다.
  - L0b 도함수는 L0a와 비트 단위로 같습니다. vsl_set이 달라도 max가 110으로 같기 때문입니다.
- **FW_W 축 열은 0입니다.** 세 reference, 네 상태 모두입니다. FW_W에는 법칙이 없습니다.
- **비공허 대조(fwe100: FW_E zone head 네 개를 100, FW_W는 110).**
  - FW_E는 스텝 1부터 L0와 L1이 갈립니다. 450 s TTT 차이(L0−L1)는 −2.2460 / −3.0296 / −3.1052 / −2.8753입니다.
  - FW_W는 IDENTICAL입니다.
  - 즉 법칙이 살아 있고, 110에서만 값이 같습니다.

## 2. 무엇을 돌렸나 [읽음 + 실행]
- **plant 경로.** v2 plant의 freeway 부분을 LaneFreewayRuntime이 lane group 없는 도로를 밟는 방식 그대로 돌렸습니다(`lane_freeway_runtime.py:116-126`, `_freeway_substep_events` 1 s × 450, update_ramp_queues·include_ramp_queue_ttt·complete_allocator_scope False). 단위 시험 `test_n31_vsl_model.py`의 rollout과 T9 `tests/n31_ad_smoke.py`와 같은 구성입니다.
  - 도로별 config: 시험 대상 reference로 만든 CanonicalFreewayModel의 `_config`입니다. 여기에 `_bind_refined`(`lane_plant_runtime.py:555-610`, parent 공간 VSL zone 표, 빈 셀 v_free)와 `_initialize_vsl_cohorts`(`:639-664`, 직전 action)를 겁니다. 이어 LPR과 같이 FW_E zero-gradient terminal, physical_vehicle_counts, occupancy_lane_loss를 설정합니다(`:437-449`).
- **초기 상태.** R-obs `sdmpc31_v3c1_nc_s31`의 `state_<T>.json`을 사용합니다.
  - obs150 `derive → merge_into_state → lane_observation` 순서로 처리하고, 망 sha와 v2 계약을 검증합니다.
  - 현재 프레임을 31 refined 셀로 binning합니다(`lane_plant_runtime.py:419-429`와 같은 식).
  - 직전 action은 `action_<T−150>.json`입니다. 네 상태 모두 cohort 초기값이 {110}입니다.
- **경계 입력.** T 이후 데이터는 읽지 않고, T 시점 상태만으로 정합니다.
  - source: A1 `source_boundary.forecast`의 150 s 블록 평균.
  - 램프: 마지막 150 s 도착 수 × 24를 유지.
  - off-ramp: 관측 split을 유지하고 용량 1800 veh/h(T9 closure).
  - 10643 차로 분율: 관측값 유지.
- **tangent.** `sdmpc_tangent_runtime.install(FRZ,'forward')`를 모델 import 전에 부르고 marshal 캐시를 scratch `tcache/`로 돌렸습니다. 이것은 T9 방식입니다. 명세는 다음과 같습니다.
  - ad110: 8축 Dual(110). 축 하나는 그 zone head의 parent 셀 전부이고, owner key는 ad.minimum입니다. 두 도로 모두 돌립니다.
  - ad100: FW_E 4축 Dual(100).
  - FD: 110에서 왼쪽 차분 h=1, 2와 Richardson, 100에서 중앙차분 h=0.25.
- **실행 조건.** 한 번에 한 프로세스, BELOW_NORMAL(lowrun.py), NUMBA_CACHE_DIR=`C:/Users/TRLAB/AppData/Local/Temp/nbc_p10`, 스레드 1. 소요는 reference당 약 265–281 s였습니다. 체인 L1 19:16:39 → L0a 19:21:05 → L0b 19:25:34 → 19:30:16, 모두 rc=0.

## 3. 재사용한 것과 확인 방법 (재개)
- **재사용(scalar 3벌, 17:48–17:49 생성): `out/scalar_{L1,L0a,L0b}.pickle`, `out/compare_scalar_only.json`.** 확인 항목은 다음과 같습니다.
  - (a) 각 pickle의 reference sha가 현재 파일 sha와 같습니다. L1은 FRZ와 worktree의 reference(6c597e25)와도 같습니다.
  - (b) manifest sha aaf49170이 현재 FRZ `plant_n31_v2.json`과 같습니다.
  - (c) frz·run 경로가 맞고, component에 설치된 법칙과 vsl_set이 기대값과 같습니다. L0a/L0b의 provenance는 `<scratch>/…`입니다.
  - (d) 상태 4개 × 케이스 2개 × 도로 2개가 모두 450행입니다.
  - (e) 생성 스크립트의 mtime(l0l1_common 17:48:18, l0l1_scalar 17:48:28)이 산출물보다 앞서고, 이후 수정되지 않았습니다.
  - (f) 로그에 오류가 없습니다(SCALAR_DONE).
  - (g) refs 차이를 다시 계산했습니다. L0a는 A·E 두 값만, L0b는 A·E·vsl_set·주석 두 개만 L1과 다릅니다.
  - (h) 교차 프로세스 재현: 이번 tangent 프로세스 안의 plain 110 롤아웃 TTT와 종단 차량 수(hex)가 재사용한 scalar 값과 네 상태 모두 같습니다(`L1_plain_in_tangent_vs_scalar` True).
- **다시 돌림: tangent 3벌 전부.** 17:5x의 L1 tangent는 900·3600까지만 로그가 남았고 JSON은 없었습니다(세션 한도로 중단). 옛 로그는 `logs/tangent_L1.aborted_1755.log`로 보존했습니다. 새 실행의 900·3600 값은 옛 로그와 자릿수까지 같습니다.
- **tcache 재사용.** 캐시 키가 소스 digest, 런타임 파일 digest, 인터프리터, 파일명의 sha256이라(`sdmpc_tangent_runtime.py:90-116`) 소스가 바뀌면 자동으로 무효가 됩니다. 항목은 69개입니다.
- **정리.** 남아 있던 내 로그 감시 `tail`(PID 14732)을 종료했습니다. 다른 작업(t5, u1t1)의 tail은 건드리지 않았습니다.

## 4. 결과
### 4.1 scalar all110 / fwe100 [실행]
| T | 변형 | 입력 동일 | all110 FW_E | all110 FW_W | 비교 float 수(도로당) | fwe100 FW_E ΔTTT (변형−L1) | 첫 차이 스텝 | fwe100 FW_W |
|---|---|---|---|---|---|---|---|---|
| 900 | L0a | True | IDENTICAL | IDENTICAL | 101250 | -2.2460 | 1 | IDENTICAL |
| 900 | L0b | True | IDENTICAL | IDENTICAL | 101250 | -2.2460 | 1 | IDENTICAL |
| 3600 | L0a | True | IDENTICAL | IDENTICAL | 101250 | -3.0296 | 1 | IDENTICAL |
| 3600 | L0b | True | IDENTICAL | IDENTICAL | 101250 | -3.0296 | 1 | IDENTICAL |
| 4800 | L0a | True | IDENTICAL | IDENTICAL | 101250 | -3.1052 | 1 | IDENTICAL |
| 4800 | L0b | True | IDENTICAL | IDENTICAL | 101250 | -3.1052 | 1 | IDENTICAL |
| 6300 | L0a | True | IDENTICAL | IDENTICAL | 101250 | -2.8753 | 1 | IDENTICAL |
| 6300 | L0b | True | IDENTICAL | IDENTICAL | 101250 | -2.8753 | 1 | IDENTICAL |

all110 FW_E TTT(세 reference 공통)는 92.016173 / 143.152247 / 146.629202 / 116.716046이고, cohort 최대 residual은 1.1e-13 이하입니다. fwe100에서 all110 대비 FW_E TTT 변화는 다음과 같습니다(값은 로그에서 계산).
- L1: +2.734 / +1.226 / +1.069 / +2.131
- L0: +0.488 / −1.803 / −2.036 / −0.745

### 4.2 FW_E 축 도함수 (c = 해당 zone 명령, L0 = L0a = L0b) [실행]
| T | 축 | dTTT/dc @110 L1 | L0 | L0/L1 | dN_end/dc @110 L1 | L0 | dTTT/dc @100 L1 | L0 | L0/L1 |
|---|---|---|---|---|---|---|---|---|---|
| 900 | FW_E@0 | -0.027966 | 0.000798 | -0.029 | -0.5798 | 0.0119 | -0.034836 | -0.028643 | 0.822 |
| 900 | FW_E@5 | -0.047547 | -0.002737 | 0.058 | -0.8403 | -0.0715 | -0.060645 | -0.050423 | 0.831 |
| 900 | FW_E@10 | -0.072134 | 0.062030 | -0.860 | -1.2226 | 1.2119 | -0.097803 | -0.057376 | 0.587 |
| 900 | FW_E@15 | -0.086768 | 0.077586 | -0.894 | -1.0097 | 1.2354 | -0.116333 | -0.057394 | 0.493 |
| 3600 | FW_E@0 | -0.016163 | 0.012228 | -0.757 | -0.2742 | 0.1612 | -0.023282 | -0.013253 | 0.569 |
| 3600 | FW_E@5 | -0.020828 | 0.015895 | -0.763 | -0.2373 | 0.0923 | -0.031810 | -0.016681 | 0.524 |
| 3600 | FW_E@10 | 0.040145 | 0.119691 | 2.981 | 0.9556 | 2.8435 | 0.006084 | 0.039540 | 6.499 |
| 3600 | FW_E@15 | -0.070469 | 0.243437 | -3.455 | -0.7882 | 4.3068 | -0.128111 | -0.001068 | 0.008 |
| 4800 | FW_E@0 | -0.010330 | 0.007846 | -0.760 | -0.2403 | 0.1600 | -0.017730 | -0.010082 | 0.569 |
| 4800 | FW_E@5 | 0.001373 | 0.045090 | 32.851 | -0.2166 | 0.1917 | -0.019503 | -0.003418 | 0.175 |
| 4800 | FW_E@10 | 0.049040 | 0.183621 | 3.744 | 1.2270 | 3.9595 | -0.005076 | 0.051576 | -10.160 |
| 4800 | FW_E@15 | -0.079567 | 0.193153 | -2.428 | -0.9310 | 3.3311 | -0.129337 | -0.018843 | 0.146 |
| 6300 | FW_E@0 | -0.017952 | 0.010178 | -0.567 | -0.3619 | 0.1514 | -0.026546 | -0.015455 | 0.582 |
| 6300 | FW_E@5 | -0.020876 | 0.012009 | -0.575 | -0.3596 | 0.0723 | -0.035062 | -0.017472 | 0.498 |
| 6300 | FW_E@10 | -0.033450 | 0.144071 | -4.307 | -0.3511 | 3.1862 | -0.078852 | -0.008298 | 0.105 |
| 6300 | FW_E@15 | -0.087336 | 0.109161 | -1.250 | -1.0104 | 2.0443 | -0.123621 | -0.046559 | 0.377 |

- **AD 정확도(참고, 판정 조건 아님).** 모든 경우에 h1이 h2보다 AD에 가깝습니다.
  - L1은 110 Richardson 상대오차가 최대 3.8e-2(6300), 100 중앙차분은 최대 9.4e-3입니다.
  - L0는 110에서 최대 2.1e-1인데, 900 FW_E@0처럼 값이 0.0008로 작은 경우입니다. 절대차는 1e-4입니다. 100에서는 6300 FW_E@5(AD −0.0175 대 FD −0.0308)가 튑니다. [추론] 450 s 실제 상태 롤아웃의 min/max 꺾임 때문으로 봅니다.
- **reach(참고).** 1스텝 뒤에는 900의 빈 셀 8만 FW_E@5에 반응합니다(빈 셀 v_free 경로). 3스텝 뒤에는 각 zone의 sign 셀 하류(0,1,3,4 / 5,6,(7),8,9 / 14,15,18,19 / 26–29)가 반응합니다. 110 앵커에서는 sign 셀에서 재태깅된 차량만 반응한다는 설계(`freeway_fd.py:209-231`)와 맞습니다.
- **계측 프로세스 대 scalar 프로세스(참고).** L1 Dual 롤아웃의 primal은 속도가 전부 같습니다. 종단 차량 수는 3600/4800/6300에서 1 ULP(≤2.3e-13), TTT는 900에서 1.4e-14 다릅니다. 이는 Dual 산술 순서에 따른 계측 효과이고 L0/L1 차이가 아닙니다. 같은 프로세스 안의 L0와 L1 primal은 hex까지 같습니다.

## 5. 해석 [추론, 근거는 읽음]
- **동일성은 구조적입니다.** plain float에서 명령 = max(=110)이면 코드가 법칙을 아예 평가하지 않습니다.
  - `area_freeway_accounting.py:375`에서 `vsl_active_i = vsl_i < vsl_max-0.5`가 False입니다.
  - 그러면 `:379-381 literature_desired_speed`가 `freeway_fd.py:121-123`에서 target을 그대로 돌려줍니다.
  - 모든 cohort가 110이면 `VSLExposure.target`도 `freeway_fd.py:215-216`에서 legacy를 돌려줍니다.
  - A·E가 들어가는 곳은 `literature_vsl_parameters`(`freeway_fd.py:39-46`)뿐입니다. 이 함수는 active일 때와 tangent 경로(`:124-126`, `:217-231`)에서만 불립니다.
  - v2 plant 경로에서 `freeway_vsl_fd_response`를 읽는 곳은 AFA:380과 freeway_fd:219 두 곳뿐입니다. physical_lane_groups는 v2에서 꺼져 있고, full-follower는 `runtime_setup.py:45-48`에서 거부합니다.
  - 그래서 이번 점검이 확인한 것은, 실제 v3c1 상태·경계·cohort 초기화에서도 법칙 계수가 110 값 경로로 새어 들어가는 곳이 없다는 사실입니다.
- **도함수 부호가 대체로 반대입니다.** SDMPC는 110에서 명령을 내리는 쪽만 허용합니다. 왼쪽 도함수 d>0이면 명령을 내릴 때 TTT가 줄어듭니다.
  - L1: d<0이 16쌍 중 13쌍입니다. 110에서 내리면 plant TTT가 늘어난다는 뜻입니다. 예외는 3600·4800의 @10과 4800의 @5입니다.
  - L0: d>0이 16쌍 중 15쌍입니다.
  - 따라서 재핀이 110 근처에서 plant의 1차 VSL 유인을 대부분 뒤집었습니다. 폐루프 효과는 이 점검 범위 밖이고 J1(3시드 이상 짝)로 봅니다.

## 6. 범위와 위생
- **plant 범위.** freeway 도로별 커널만 돌렸습니다. 도시·램프 큐 결합은 유지 closure로 대신했습니다. 이 점검은 같은 입력에서 L0와 L1의 동일성을 보는 것이므로 closure는 두 쪽에 똑같이 적용됩니다. SDMPC 결정 전체의 재생(ps1)은 쓰지 않았습니다.
- **데이터.** v3c1 NC s31 R-obs의 state/action 파일만 읽었습니다(허용 시드). seed 37, RM 팔, 봉인 시드는 열지 않았습니다. VISSIM·cscript를 시작하거나 종료하지 않았고, 금지된 시험도 돌리지 않았습니다.
- **FRZ.** 읽기 전용으로 다뤘습니다. 생성물 목록(__pycache__, pyc, mcode, __tangentcache__ 등)이 시작 전 목록과 같고(FRZ_GENERATED_SAME), 시작 마커(17:41)보다 새 파일은 0개입니다.
- **worktree.** `D:/VISSIM-merge/sim3-n31-v3c1`(claude/repin-v3c1-20260928, HEAD 5323faa4)의 `git status --porcelain`이 시작과 끝 모두 비어 있습니다. 다만 ignored 폴더 `evaluation/controllers/__tangentcache__/`(60개)가 있습니다. 생성 시각이 2026-09-28 12:22:57–12:23:02로 이 작업(17:37 시작)과 커밋보다 앞서므로, P8 T9 실행의 산물로 보입니다. 이 작업이 만든 것이 아니라서 지우지 않았습니다.

## 열린 문제
1. L0L1_REPORT.md를 쓰지 못했습니다. 서브에이전트 Write 도구가 보고서 파일 쓰기를 거부했습니다. details_ko 본문을 그 경로(…/v3c1-p10/l0l1/L0L1_REPORT.md)에 그대로 저장하면 됩니다.
2. worktree에 ignored 폴더 D:/VISSIM-merge/sim3-n31-v3c1/evaluation/controllers/__tangentcache__/ 가 남아 있습니다(60개, 09-28 12:23 생성, 이 작업보다 먼저). git status는 비어 있지만 "tangent 캐시를 남기지 않는다" 조건에 걸리므로 지울지 정해야 합니다. 이 작업이 만든 것이 아니라서 건드리지 않았습니다.
3. 이 점검의 plant는 freeway 도로별 커널(LFR 집계 경로)에 경계 입력을 유지 closure로 넣은 것입니다. 도시·램프 결합과 SDMPC 결정 전체는 포함하지 않습니다. 결정 수준 재현은 §5.5-4 T5 재생(ps1)이 담당합니다.
4. 계측 프로세스 안의 primal은 L1 scalar와 1 ULP 차이가 납니다(종단 차량 수, 900 TTT). L0/L1 대조와는 무관합니다.
5. AD와 FD의 차이가 T9 1% 기준을 넘는 곳이 있습니다. L1 6300은 110 Richardson 3.8%, L0 6300 FW_E@5는 100 중앙차분이 크게 어긋납니다. [추론] 실제 상태 롤아웃의 꺾임 때문으로 보며, 이번 판정 조건은 아닙니다.
6. 해석상 짚을 점이 하나 있습니다. 110 한쪽 dTTT/dc의 부호가 L1에서는 16쌍 중 13쌍이 음수(명령을 내리면 plant TTT 증가), L0에서는 15쌍이 양수입니다. 재핀이 plant의 1차 VSL 유인을 대부분 뒤집었다는 뜻입니다. 폐루프 효과는 J1에서 확인해야 합니다.
