# GATE_FO — FO 관문 결과: T=900 첫 제어 결정 재생 4개 + 도시 SG 쓰기 대 native 대조 (2026-10-27 21:07–21:33 KST, VISSIM 0)

- 선언: `FO/PRE_FO.md` r2 sha256 `743909fd95374568e1679f965f42e565fbe74d7486c04d4d446b26ed4691b210` §5(관문)·§9(멈춤), 리뷰 기록 `FO/PRE_FO_FIXED.md` `725c16773529897be59fe6c19dc9b3483ff0ee5ec9d105b24055b09d51ad6c02`, 비교 규칙 `FO/COMPARE_RULE_FO.md` r2 `7ef1b03da6492de3c077e349086f6125fe4ac0e2673359bf1949bc185640c5c8`, 도구 핀 `FO/PINS_FO.sha256` r2 `314d51dc5006ee65f3913940f2e7064b19f1a43d2d50e3c7df049ef7760cae66`. 넷 모두 발사 전에 `.sha256` 파일과 같았고, 핀 154줄 `sha256sum -c` 154/154 OK 였습니다 [실행 21:04 KST]. 이 넷은 고치지 않았습니다.
- 판정 낱말은 쓰지 않습니다. "조건 만족" 은 PRE_FO §5.2 에 미리 적은 조건이 사실로 맞는다는 뜻입니다.
- 표시: **[실행]** 명령으로 확인 · **[읽음]** 파일을 읽어 확인 · **[추론]** 시험하지 않은 판단 · **[계산]** 산술.
- SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`, FO = `SP/codex_handoff/fo`, FW = `FO/work`, G = `D:/VISSIM-merge/k8_gate_trees/codexhandoff/fo/gate`, FRZ_FO = `D:/VISSIM-merge/k8_gate_trees/codexhandoff/fo/frozen/sdmpc31_a49981ff_202610271954`.

## 0. 줄임말 (처음 한 번)

- **FO** = codex SDMPC(분산 모형예측제어기)가 램프 미터만 정하고, 도시 신호 17곳은 baseline(= v3c3 무제어 명령 값)을 다시 쓰기만 하는 팔(사용자 결정 D-K9-113, O2 = 작동기 범위만). **B** = 같은 codex 판이 도시 신호 + 미터를 정한 팔.
- **SC** = 신호 제어기(교차로 하나). **SG** = 신호 그룹(신호등 한 묶음). **COM** = VISSIM 을 바깥에서 움직이는 창구. **VSL** = 가변 제한속도.
- **R1·R2·R3** = B 기록 상태(v3c3-s31·s41·s43, T=900)에서 FO 설정으로 첫 결정을 다시 돌림. **R0** = R1 과 같은 상태에서 B 설정으로 다시 돌림(대조).
- **G2** = FO 재생이 쓴 도시 SG 일정(baseline)을 초 단위 GREEN 으로 펼쳐, 같은 시드 B 런 `.lsa`(VISSIM 신호 상태 기록)의 900 s 전 native 프로그램 GREEN 과 견줌.
- **A1–A8, C4·C5** = PRE_FO §5.2 의 칸 이름(요약 도구 `fog_summary.py` 가 그대로 셈).

## 1. 쉬운 답

1. [실행] **관문 요약 `FW/gate/fog_summary.json` 의 `pass` 는 true 입니다** (sha256 `d0494cfb78270f2d6b272e189e6b6606ed33c324de5262321d2195dc8adb2ce1`). PRE_FO §5.2 의 조건이 모두 맞았습니다.
2. [실행] **예외 없이 결정합니다.** R1–R3 모두 종료 0, Traceback·`DECISION_FAILED`·오류 파일 0, 명령 JSON·CSV 를 끝까지 썼습니다(`output_completed` true).
3. [실행] **도시 SG 는 baseline 계획으로만 다시 씁니다.** JSON green 68·offset 17 이 baseline 과 차 0, CSV signal 17행 차 0, signal_sg 122행이 17 SC 안에만 있고 세 시드에서 바이트 같습니다(`bd21439e…`). 결정 좌표에 신호 green·offset 은 0개입니다.
4. [실행] **미터는 SDMPC 가 정합니다.** `controller_status` ok, `sdmpc_active` true, 좌표 = meter 24개뿐(B 기록의 meter 24 와 같은 수), ramp_meter 8행.
5. [실행] **결정 벽시계 최대 170.9 s**(R1) 로 1,500 s 의 11.4 %, StallSec 3,600 s 의 4.7 % 입니다 [계산]. 같은 상태에서 B 설정(R0)은 471.3 s 였습니다.
6. [실행] **표지는 선언한 것만 다릅니다.** 정책 토큰 `7673d367…` ≠ B `848d55d3…` 이고 세 시드에서 같음, 정책은 B 정책 + `actuator_scope` 키 하나(값 = FO 설정 값), 빠지거나 바뀐 정책 키 0, `sdmpc_state` 키 집합 = B, 지역 표지 13종 0개, `head_` 아닌 최상위 메타데이터 키 차이 0.
7. [실행] **대조 R0 는 B 를 바이트까지 재현합니다.** 정책 토큰·정책 = B 기록, `action_000900.csv` 바이트 = B 기록(`fb297196…`). 그래서 solo 17파일 덮기는 키가 없을 때 B 결정을 바꾸지 않았습니다(이 한 상태에서).
8. [실행] **G2: COM 으로 다시 쓰는 baseline SG 일정 = native 프로그램 (GREEN 만).** 세 시드 모두 쓰는 SG 136개(창 있음 122 + 적색 전용 14)에서 프레임 [2, 899] 의 GREEN 차 **0 프레임**, SC 주기 17곳 모두 같음, 쓰는 SG 집합 = 계획 기대 집합, native 전용 24개(SC5 9–24·SC7 9–16)는 쓰지 않음. 그래서 FO − NC3 에 "쓰기 효과" 가 GREEN 초로는 섞이지 않습니다(GREEN 밖과 COM 쓰기 자체의 내부 효과는 보지 않음, PRE_FO §12).
9. [실행] FRZ_FO `FREEZE_VERIFIED` 재생 앞·뒤 두 번(sha `d7fa4db6…`, 파일 7,994).
10. 선언 밖 준비 1건(§5): 관문 출력 뿌리 G 가 없어서 빈 폴더만 미리 만들었습니다. 도구·명령·조건은 그대로입니다.
11. 이 단계는 FO 런을 띄우지 않았습니다. PRE_FO §13 대로 런 발사는 **사용자 발사 허락 뒤**입니다.

## 2. 한 일 (시각 KST)

| 시각 | 일 | 근거 |
|---|---|---|
| 21:04 | 고정 문서 넷 sha 대조, 핀 154/154 OK, 입력(사전 점검 provenance 4, B 기록 3시드) 있음, 공용 잠금 없음, PC VISSIM 1개(30964, 남의 것) | [실행] |
| 21:07:24 | 빈 폴더 G 만듦(§5) | [실행] LOG 21:07 항목 |
| 21:07:31 | PRE_FO §5.1 명령 그대로 WMI 발사: `fo_launch_wmi.ps1 -Script FW/gate/fog_queue.ps1 -StateName queue_fog.state.txt -ArgString "-Frz <FRZ_FO> -FrzSha d7fa4db6…"` → ReturnValue 0, 큐 PID 26896, BelowNormal | [실행 `FW/build/launch_receipts.log`] |
| 21:07:32 | 큐 시작, 디스크 C 16.2 GB·D 194.5 GB | [실행 `FW/gate/queue_fog.state.txt`] |
| 21:09:20 | FRZ_FO FREEZE.json sha 확인 + `freeze_manifest.py verify` exit 0 (`G/freeze_verify_before.txt`) | [실행] |
| 21:09:23–21:09:30 | 재생 입력 넷 만듦, 각 95파일, 위치 못 바꾼 경로 0, exit 0 | [실행 `FW/gate/build_R*.txt`, `G/pristine/*/T000900/INPUT_MANIFEST.json`] |
| 21:09:30–21:12:30 | R1 (잠금 0 s 만에 잡음, 내 토큰만 지움, 25 s 쉼) | [실행] |
| 21:12:55–21:15:55 | R2 (잠금 0 s) | [실행] |
| 21:16:20–21:19:21 | R3 (잠금 0 s) | [실행] |
| 21:19:46–21:24:16 | R0 잠금 기다림 270 s: 남의 일 `vsl_plant verify_vp/VV_A_v3c3-s31_T004050`(PID 47852)이 21:19:23 부터 잡고 있었음. 손대지 않음 | [실행] |
| 21:24:16–21:32:16 | R0 | [실행] |
| 21:32:51 | FRZ_FO verify exit 0 (`G/freeze_verify_after.txt`) | [실행] |
| 21:32:52–21:32:54 | G2 R1·R2·R3 exit 0 | [실행] |
| 21:33:07 | 요약 exit 0, 큐 `done` | [실행] |

- 잠금은 선언(PRE_FO §5.1)대로 재생마다 잡았습니다(배타 생성, 30 s 재시도, 놓은 뒤 25 s 쉼, 내 토큰만 지움). 입력 만들기·FREEZE 검사·G2·요약은 작은 파일 일이라 선언대로 잠금 밖입니다. 끝난 뒤 잠금 파일 없음, 우리 프로세스(큐·재생 래퍼·python·typeperf) 남은 것 0 [실행 21:34].
- 이 PC 의 다른 세션: VISSIM 30964 와 그 결정 python(rolling_cea, 남의 것)이 내내 돌았습니다. 세기만 했고 건드리지 않았습니다 [실행].

## 3. 재생 결과

### T1 끝남·예외·벽시계 (A1–A4)

| 재생 | 설정 | 종료 (A1) | 예외 (A2) | `[경고]` 줄 | python 벽시계 (s) | budget wall (s) | budget CPU (s) | output_completed (A3) | A4 ≤ 1,500 s | 우선순위 |
|---|---|---:|---|---:|---:|---:|---:|---|---|---|
| R1 v3c3-s31 | FO | 0 | 없음 | 3 | 170.875 | 170.180 | 43.75 | true | 만족 | BelowNormal |
| R2 v3c3-s41 | FO | 0 | 없음 | 3 | 167.408 | 166.766 | 43.81 | true | 만족 | BelowNormal |
| R3 v3c3-s43 | FO | 0 | 없음 | 3 | 161.980 | 160.228 | 49.75 | true | 만족 | BelowNormal |
| R0 v3c3-s31 | B (대조) | 0 | 없음 | 3 | 471.345 | 470.139 | 197.11 | true | (해당 없음) | BelowNormal |

- [실행] `[경고]` 세 줄은 넷 모두 바이트 같은 글(stderr sha `cdfdd13b…`)입니다: leader_hinge·np_deadband·leader_mfd_far 성분의 캘리브레이션 기하 안내. B 관문 1 의 재생에도 같은 세 줄이 있었고 예외로 세지 않습니다(GATE1 §2 [읽음]).
- [실행] `decision_budget`: "Wall limits explicitly disabled", `unlimited_time` true(시간 제한으로 끊긴 결정 없음).
- 큐 기록의 `wall=180.1`·`480.1` 은 큐가 20 s 간격으로 살핀 값이고, A4 는 요약 규칙대로 python 벽시계와 budget wall 중 큰 값을 씁니다.
- FO 결정 벽시계 최대 170.875 s [실행] → 1,500 s 의 11.4 %, StallSec 3,600 s 의 4.7 % [계산]. R0 471.3 s 는 3,600 s 의 13.1 % [계산].

### T2 결정 내용 (A5–A8)

| 재생 | CSV 행 (kind 별) | CSV sha256 앞 16 | A5 도시 = baseline (JSON green/offset 최대 차, CSV signal 차) | signal_sg 행 · sha 앞 16 | A6 좌표 (B 기록) | ramp_meter 행 | A7 VSL | A8 표지 |
|---|---|---|---|---|---|---:|---|---|
| R1 | 213 (vsl 66, signal 17, signal_sg 122, ramp_meter 8) | `df3afc2fcab6dd79` | 0.0 / 0.0, 차 0행 → 만족 | 122 · `bd21439e1d1f01f9` | meter 24 ({green 138, offset 51, meter 24}) → 만족 | 8 | 66행·JSON 모두 110 → 만족 | 만족 |
| R2 | 213 (같은 구성) | `6cb2de36f1e55cf3` | 0.0 / 0.0, 차 0행 → 만족 | 122 · `bd21439e1d1f01f9` | meter 24 (같음) → 만족 | 8 | 만족 | 만족 |
| R3 | 213 (같은 구성) | `5a9b9faa95cbcbd8` | 0.0 / 0.0, 차 0행 → 만족 | 122 · `bd21439e1d1f01f9` | meter 24 (같음) → 만족 | 8 | 만족 | 만족 |

- [실행] 선택 상태 셋 모두 `best_observed_feasible_sdmpc`. `controller_status` ok, `sdmpc_active` true, `sdmpc_state` 있음.
- A8 의 내용 [실행]: 정책 토큰(`metadata.sdmpc_state.policy_sha256`) R1·R2·R3 = `7673d3675011666d841f065c095fc1800fa07295d70ce734d1cd591f8b679773`(셋 같음), B 기록 = `848d55d3edb8b356d2901eb6f45ff2f612eaa7d075cfbecfc85b9c8d60747139` → 선언 M1 대로 다름. `joint_leader_selection.policy` 더한 키 = [`actuator_scope`] 하나(값 = FO 설정의 `adapter.sdmpc_actuator_scope`), 빠진 키 0, 바뀐 키 0 → M2. 좌표 종류 {meter} 24 → M3. 지역 표지 13종(`regional_context` 등) 찾은 수 0 → M6. `sdmpc_state` 키 집합 = B. 보고만: `head_` 아닌 최상위 메타데이터 키 대칭 차 0 / 0.
- 세 FO 재생의 정책 토큰이 서로 같음: true. signal_sg 일정이 세 시드에서 같음: true [실행].
- M5(t=1 무제어 결정 메시지 글자)는 관문 칸이 아니고 런 점검 V7 에서 봅니다(PRE_FO §3).

### T3 대조 R0 (C4·C5)

| 칸 | 값 | 조건 |
|---|---|---|
| C1–C3 | 종료 0, 예외 0, 끝남 | 만족 |
| C4 정책 토큰·정책 = B 기록 | `848d55d3…` = `848d55d3…`, 더한·빠진·바뀐 정책 키 0, 좌표 {green 138, offset 51, meter 24} = B 기록 | 만족 |
| C5 `action_000900.csv` 바이트 = B 기록 | `fb2971960188b09c54a90a710b3a0bc23fe49247a6ae50162438755ecabdf5b3` = B v3c3-s31 기록 `fb297196…` | 만족 (HOLD 아님) |

- 뜻 [추론]: FRZ_FO(solo 덮기) 위에서 키 없이 돌린 결정이 B 의 산 결정과 같은 바이트이므로, PRE_FO_FIXED §4 의 "C5 HOLD 면 덮기 탓과 재생 탓을 못 가름" 한계는 이번에 생기지 않았습니다. 한 상태·한 시드의 확인입니다.

## 4. G2 — COM 으로 다시 쓰는 baseline SG 일정 대 native 프로그램 (GREEN 만)

| 시드 | 쓰는 SG | 그중 창 있음 / 적색 전용 | GREEN 차 SG · 프레임 [2, 899] | COM 규칙 GREEN 프레임 = native GREEN 프레임 | SC 주기 17곳 같음 | 기대 밖 SG 씀 | 계획에 있으나 안 씀 | native 전용(안 씀) | 출력 sha256 |
|---|---:|---|---|---|---|---:|---:|---:|---|
| v3c3-s31 | 136 | 122 / 14 | 0 · 0 | 27,772 = 27,772 | 예 | 0 | 0 | 24 | `g2_R1.json` `5b7e1c2c5a6ed007febcba73f3b641434140fb4e87326ba8d23db66be0438aed` |
| v3c3-s41 | 136 | 122 / 14 | 0 · 0 | 27,772 = 27,772 | 예 | 0 | 0 | 24 | `g2_R2.json` `0fe04a5fa1e0c485c60690329aba9402c3132f4e5876b72b74b45e1c2723a6fb` |
| v3c3-s43 | 136 | 122 / 14 | 0 · 0 | 27,772 = 27,772 | 예 | 0 | 0 | 24 | `g2_R3.json` `dbf96cb960414e2b15aa4ec92cb2bfdb7feaec257378b2a4d43e52529a405fc9` |

- [실행] 주기: SC7 120 s, 나머지 16곳 150 s, 계획 행 주기 = native 주기(`.lsa` cycletime 되감김에서 셈). native 전용 24개 = SC5 SG 9–24(16) + SC7 SG 9–16(8) → PRE_FO §5.2 의 기대 집합(창 122 + 적색 14 = 136, native 전용 24)과 같음. 기대 집합 원본은 FRZ_FO 의 sgplan VBS `RW_SIGNAL_SG_EXPECTED`(160 SG).
- [실행] 입력: FO 재생 CSV(위 T2 sha), B 런 `.lsa` (s31 `c892a340…`, s41 `90f9cb1a…`, s43 `eedff15a…`), 쓰는 SG 집합 = 같은 시드 B 런 `signal_readback.csv` 의 도시 행(s31 `670e1d79…`, s41 `5a21a3cb…`, s43 `e6ec1ab2…`). FO 재생은 VISSIM 을 거치지 않으므로 FO 자신의 readback 은 없습니다. 런 뒤에는 V4(c)–(e) 가 FO 런의 readback·`.lsa` 로 다시 봅니다.
- 규칙: 프레임 t 가 GREEN ⇔ (t + offset) mod 주기가 창 안(VBS 시계, `OBS150_FRAME_ADVANCE` 1). 이 규칙은 FO 데이터 전에 양성 대조(codex 64cf baseline 행 → B v3c3 3시드 136 SG 0 차)와 음성 대조(B 최적 계획 → 122 SG 다름)로 시험했습니다(PRE_FO §5.3).
- 그래서 D-K9-113 의 "다르면 멈춤" 조건은 생기지 않았습니다. 보지 않은 것: 노랑·적색 초, COM 쓰기 자체가 VISSIM 안에서 내는 효과, 900 s 뒤 런 안의 실제 실현(런 점검 V4 몫).

## 5. 선언 밖 준비 1건과 밝힘

- **빈 폴더 G 를 미리 만듦** [실행 21:07:24]. 까닭: `fog_queue.ps1` 0단계가 `G/freeze_verify_before.txt` 를 Start-Process 재지정으로 쓰는데, G 가 없었습니다(PRE_FO_FIXED 20:57 확인과 같음). PS 5.1 탐침(scratchpad 의 없는 폴더로 재지정): python 은 종료 0 인데 파일이 생기지 않음 → 그대로 돌렸으면 요약의 `freeze_verify.before` 가 도구 탓으로 거짓이 되어 관문이 데이터와 무관하게 막혔을 것입니다 [실행 탐침·추론]. B 관문 1 은 사전 점검이 그 폴더를 먼저 만들어 이 일이 없었습니다 [읽음 `CW/gate1/g1_queue.ps1`]. 폴더만 만들었고 도구 바이트·명령·인자·조건·입력은 바꾸지 않았습니다. FO 데이터가 생기기 전(발사 전)에 LOG 에 적었습니다.
- **FRZ_FO 안 캐시** [실행]: 재생이 21:09 뒤 FRZ_FO 안에 `__tangentcache__` 100개, numba `__pycache__` 6개를 썼습니다. 둘 다 FREEZE 제외 폴더이고 그 밖의 새 파일은 0, 재생 뒤 `FREEZE_VERIFIED` 입니다. B 관문 1 과 같은 꼴(106개)입니다. FRZ_FO 는 FO 런의 코드 뿌리라 선언된 쓰임입니다. `D:/VISSIM-merge/frozen/*`·FRZ_B0·FRZ_B1·V-A·K92 동결 트리는 읽지도 쓰지도 않았습니다.
- 재생은 `vsl_cohorts_000900.json` 하나를 새로 만들었습니다(수집 기록 `collect.txt`, "collected 9"). 결정 입력 파생 파일이며 관문 칸이 아닙니다.

## 6. 데이터 뒤 (보고만, 무게 낮음; PRE_FO §9-8)

- [실행] T=900 미터 명령(rate_vph, green_sec)을 B 기록과 나란히 읽었습니다. 같은 상태에서 FO 는 B 와 다른 미터 값을 고른 곳이 있습니다: v3c3-s31 8개 중 2개(RM_C10646 FO 720/B 900, RM_C10639 FO 900/B 720), v3c3-s41 1개(RM_C10646 720/900), v3c3-s43 4개(RM_C10480·10639·10681·10484 FO 900/B 720). 값은 모두 {720 vph·8 s, 900 vph·10 s} 안입니다. 미터가 실제로 "정해지고" 있다는 뜻일 뿐, 효과에 대해서는 아무것도 말하지 않습니다. 런 안의 미터 결정은 900 s 뒤 상태가 갈라지므로 이와 다를 것입니다 [추론].
- [실행·계산] FO 결정의 budget CPU 는 B 설정(R0)의 0.22–0.25배(43.8–49.8 s 대 197.1 s)입니다. 결정 좌표가 213개(green 138 + offset 51 + meter 24)에서 24개로 줄어든 것과 맞는 꼴입니다 [추론]. 런 벽시계는 런 점검 V8 에서 봅니다.

## 7. 지킨 것·안 한 것

- VISSIM·COM 0, FO 런 발사 0(`D:/VISSIM_runs/20261028_codex_fo_v3c3` 없음 [실행 21:36]), kill 0(우리 큐의 7,200 s 상한도 닿지 않음), 남의 VISSIM 30964·남의 잠금 보유자 손댐 0.
- 무거운 일 = 재생 넷, 모두 공용 잠금 아래·WMI 분리 발사·BELOW_NORMAL·`PYTHONHASHSEED=0`·`python -B`·env_hsw(`OPENBLAS_CORETYPE=Haswell`, AVX-512 끔, `NUMBA_CPU_NAME=haswell`)·스레드 1, RW_* 20개는 입력 provenance 값 [실행 `replay_state.json` 의 env]. FZP 읽기 0.
- 쓰기: G(입력·작업 사본·출력), FRZ_FO 의 제외 캐시 폴더, `FW/gate/`(큐 기록·G2·요약), `FO/LOG.md`, 이 문서, 보고 사본. `D:/VISSIM-merge/frozen/*`·FRZ_B0·FRZ_B1·V-A·K92·GWT8(`D:/VISSIM-merge/sim3-n31-k8`)·codex 작업 트리 a49981ff 쓰기 0, `sealed/`·봉인 시드 37/59/61/67·codex 64cf-s59/s61/s67·v3c3-s47 값 0, 금지 시험 0, 커밋·푸시 0.
- PRE_FO·COMPARE_RULE_FO·PINS_FO·관문 도구는 바꾸지 않았습니다.

## 8. 산출 sha256

| 파일 | sha256 |
|---|---|
| `FW/gate/fog_summary.json` (관문 요약, 발사기 `-GateSha` 값) | `d0494cfb78270f2d6b272e189e6b6606ed33c324de5262321d2195dc8adb2ce1` |
| `FW/gate/g2_R1.json` / `g2_R2.json` / `g2_R3.json` | `5b7e1c2c…` / `0fe04a5f…` / `dbf96cb9…` (64자는 §4) |
| `FW/gate/queue_fog.state.txt` | `eb9fee4b01245079caa3a5043a916ce096ba3251f0459402ec53be5a96e444ad` |
| `G/freeze_verify_before.txt` = `G/freeze_verify_after.txt` | `a728ede2ef10f873242ec289ff03bb4912828e86d90739fd21338fd083fe3d56` (같은 글) |
| 입력 기록 `G/pristine/{b_s31,b_s41,b_s43,b_s31b}/T000900/INPUT_MANIFEST.json` | `4e548c88…` / `7150ddf8…` / `6a8df4a7…` / `deeb2f3a…` |
| 재생 원천 상태 `state_000900.json` (B 기록 s31 / s41 / s43) | `18cc2c45…` / `f5c75738…` / `eae4b267…` |

## 9. 다음 걸음 (사용자가 정함)

1. 관문 요약 pass true → PRE_FO §13-1 에 따라 **사용자 발사 허락이 있으면** §6 시작 명령: `powershell -NoProfile -ExecutionPolicy Bypass -File FO/fo_launcher_start.ps1 -LauncherSha e73990d0da6dac7603be9959acca063cacbc0b3f033b8cf0336d351c31ffd02b -WrapperSha b79f38ac97336ed944e431c2fb43d23a7665851ce0c4a49456b6643f2038b019 -PreSha 743909fd95374568e1679f965f42e565fbe74d7486c04d4d446b26ed4691b210 -RuleSha 7ef1b03da6492de3c077e349086f6125fe4ac0e2673359bf1949bc185640c5c8 -PinsSha 314d51dc5006ee65f3913940f2e7064b19f1a43d2d50e3c7df049ef7760cae66 -GateSha d0494cfb78270f2d6b272e189e6b6606ed33c324de5262321d2195dc8adb2ce1`. 런 하나는 이 PC 에서 B 기준 10–14 h 입니다.
2. 런 동안 할 수 있는 일: `-Plan prescan`(NC3·V-A, FO 데이터 아님).
