# 도시 묶음 2 — 단계 3 보고 (증거 파일 확정 + C6 비용 축소)

- 작성: 2026-09-29 10:15 시작 → 14:30 완료. 이전 시도의 단계 3 부분 결과는 없었습니다(`B/impl/stage3` 없음, 트리 diff `36ac3916…` = 단계 2 끝 그대로). 재사용한 것은 §1에 적었습니다.
- 계획: `B/BATCH2_PLAN.md` §4.3, §4.2(C6), §5.1, §6.1 (d), §6.9, §7 단계 3 행, §9, §10, §11 Q1·Q2, 부록 C. 사용자 결정: C3 = U4+U5+U6(전부 아니면 전무), U5는 과대 그룹 전부 + native(Q1), Q2 = SC105·SC1 공유 좌회전 차로 현시 권한을 p3로(증거 파일) + SC7 직렬 헤드 그룹 정적 축소, Q3 = v3b 폐루프 없음, 2026-09-29 = C6 no-control 비용 축소 후 재확인.
- 대상 트리: `D:/VISSIM-merge/sim3-n31-urban-b2` (브랜치 `claude/urban-batch2-20260928`, HEAD `cf3ce37`). 변경은 **커밋하지 않고** 작업 트리에 남겼습니다. push·rebase·다른 브랜치/워크트리 조작, VISSIM·cscript 시작/종료는 없습니다.
- 표기: **[실행]** 이번에 직접 돌리거나 계산한 값 / **[읽음]** 파일에서 읽은 값 / **[추론]** 직접 증거 없이 끌어낸 판단.
- 약어: B = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/urban-b2`, S3 = `B/impl/stage3`, R3 = `S3/run3`(C6 관문 대기열), R3b = `S3/run3b`(최종 트리 다리 확인), EV = `S3/evidence`(증거 생성·검사), H = `B/harness`, W = b2 트리, SM = `W/evaluation/controllers/starvation_monitor.py`, T2 = `W/diagnostics/sdmpc_n31_20260924/tests/test_n31_urban_batch2.py`, N31 = `W/diagnostics/sdmpc_n31_20260924`, U = `N31/urban`. 줄 번호는 최종 작업 트리 기준입니다.

---

## 0. 결론

**멈춤 규칙에 걸린 것은 없습니다(stop=false).** 증거 파일 다섯 개(+ Q2 β 표, 런타임 포착)가 각자의 생성기와 `--check`(바이트 재현)를 갖고, 교차 일관성 검사 7개가 모두 통과했습니다. C6는 사용자가 지정한 두 방법(inpx 한 번 파싱, flag 행만 표에 남김)에 상수 축약 하나를 더해 no-control 비용을 줄였고, G-ID (d)·G-C6-0~4를 다시 받아 모두 통과했습니다. **1% 한도 판정: JSON 크기는 61/61 결정에서 1% 이하(최대 0.95%)로 통과, 시간은 평균 0.79%·교대 쌍 평균 +0.07%로 통과이지만 결정별로는 61개 중 8개가 1.01~1.25%입니다**(§3.5; 대부분의 측정 구간에 다른 워크플로의 SDMPC 재생이 동시에 돌았습니다). 남은 초과분을 없앨 레버 두 개를 §7-1에 적었고, 적용 여부는 사용자 판단으로 남깁니다.

| 항목 (계획 위치) | 결과 | 근거 |
|---|---|---|
| C6 비용 축소 (사용자 결정 09-29) | 스키마 v2. inpx 1회 파싱(SHO 규칙을 그 파싱에 적용, 동일성 단위 시험), 표는 flag 행만, 기록용 세부값(T−150 프레임·헤드 창·멤버 탐침)은 flag 그룹만, 상수는 짧은 코드. 규칙·스트릭·경보는 v1과 같음 | [실행] §2 |
| G-ID (d) (a) R-obs-b 61 | 61/61 `MRS compare` IDENTICAL, 키 없는 단계 1 재생과 JSON 차이는 C6 블록·provenance·벽시계뿐(그 밖 0), stdout 차이는 `"starvation"` 필드뿐 | [실행] §3.1 |
| G-ID (d) (c) SDMPC 5 | 5/5 IDENTICAL, 녹색·offset·목적값·tangent 계수가 기록과 같음, 키 없는 재생과 차이 "그 밖 0", csv·stderr 바이트 같음 | [실행] §3.1 |
| G-C6-1 | 어댑터 블록의 flag 행 27개(SDMPC)+50개(R-obs-b) 독립 재계산과 불일치 0, flag 집합이 66블록 모두 독립 flag 집합과 같음, 궤적 2런×61상태×105그룹(12,810) 불일치 0, `c6_dryrun` 13/13 | [실행] §3.2 |
| G-C6-1b | 격자 결과가 단계 2와 같음: tol 1.0·M 8 선택(S1 첫 경보 4,650 s, S0e 0건) | [실행] §3.3 |
| G-C6-2 | 두 런 모두 메모리·파일·독립 세 연쇄의 스트릭이 모든 결정에서 같음 | [실행] §3.4 |
| G-C6-3 (no-control) | 모니터 자체 시간 0.502 → **0.184 s**(평균), 결정 대비 2.25% → **0.79%**(최대 1.25%, >1%: 8/61), 교대 10쌍 평균 **+0.07%**(중앙 +0.49%), JSON **+6.8% → +0.82%**(최대 0.95%, >1%: 0/61) | [실행] §3.5 |
| G-C6-3 (SDMPC) | 0.20–0.30%, 블록 26.8–27.4 kB → 5.3–7.9 kB, stdout 필드 71 B | [실행] §3.5 |
| G-C6-4 | PASS: A/B의 csv 바이트·제어·목적값·tangent 계수 같음, 차이는 C6 블록·이전 action 핀 3·provenance·시간·토큰뿐, A가 스트릭을 이어 받음 | [실행] §3.6 |
| v1 → v2 블록 동일성 | 66블록 전부: v2 행 = v1의 flag 1 행, counts·streaks·alarms·prior 같음 | [실행] §3.7 |
| 상태 불변·스위트·정적 감사 | 14개 대상 해시 변화 0, stdout/stderr 0 B; 스위트 40실행 회귀 0(단계 2 대비); 이전 action 독자 감사 재실행 | [실행] §3.8 |
| **Q2 증거** (SC105/SC1 → p3) | `U/physical_phase_authority_v3b_q2_20260929.json` = 묶음 1 권한 + 2행. FZP 5시드: SC105 1,250건 중 SG6 녹색 1,249·황색 1·적색 0, SC1 1,135건 중 녹색 1,128·황색 7·적색 0. R-obs-b 정확 통과시각: 250/235건, 선언 현시(p4) 녹색 중 통과 0/1건. 실제 설치 체인에서 두 현시만 바뀜 | [실행] §4.2 |
| Q2 β 표 | `N31/beta/movement_beta_routing_v3b2q2_20260929.json`: β·사유·접근로·무흐름 현시가 묶음 1 표와 같고 `inputs.phase_authority`·`runtime_phases`만 다름 | [실행] §4.2 |
| 런타임 포착 | `U/urban_movement_runtime_v3b_20260929.json`: R-obs-b T2700, U1+U3, `configure_runtime` 직후 정지, movement 356 | [실행] §4.3 |
| **U5 계약 v1** | 174행, 대기 행 0. budget 46 · 10629 대체 1 · LUR 위임 2 · 정적 축소(SC7) 1 · 직렬 첫 헤드 1 · native_budget 10 · 구속 안 됨 54 · native 구속 안 됨 53 · 흐름 없음 6. 제어 108그룹 중 과대 50개 전부 처리 | [실행] §4.4 |
| **U4 표 v1** | 174그룹 344헤드: 실측 110(관측 65·다중헤드 3·native 42), 기본값 63(1,850), 직렬 규칙 1. 초안 105행을 이식이 재현(float32 저장이면 105행 측정값 전부 일치) | [실행] §4.5 |
| **U6 분기 증거** | `U/ramp_diverge_v3b_20260929.json`: 1136/1137/1135 경로·분할, W_out 734.24/351.35 m, 10483 → 꼬리, 10639 퇴역, 분기 용량 1,800 선언. FZP 5시드 검증이 inpx 값과 맞음 | [실행] §4.6 |
| 교차 일관성 | 7개 검사 모두 OK (`scripts/check_urban_batch2_evidence.py`) | [실행] §4.7 |
| `--check` | 생성기 6개 + 포착 도구 + 기존 β 표: 모두 바이트 재현 | [실행] §4.8 |
| 단위 시험 | T2 **38 OK** (단계 2의 28 + C6 v2 5 + 증거 5) | [실행] §5 |
| 최종 트리 다리 | 최종 diff `0f56bd42…`에서 R-obs-b 4상태 IDENTICAL, C6 블록이 관문 대기열 블록과 같음(벽시계 제외), 스위트 40실행 회귀 0 | [실행] §6 |

---

## 1. 재개 확인과 재사용

- 단계 3의 부분 결과는 없었습니다 [실행: `B/impl`에 `stage3` 없음, 트리 diff `36ac3916007632db…` = 단계 2 끝]. 새로 시작했습니다.
- 재사용(검사 후):
  - 단계 2 관문 튜닝 `B/impl/stage2/tunings_full/config_n31_v2_c6.json`(`419a499a…`), `config_n31_v2_urban_b1_u1u3_c6.json`(`fe6b0a50…`). 부모 `config_n31_v2.json`(`d4327cbf…`)·`config_n31_v2_urban_b1_u1u3.json`(`f137f711…`)가 그대로임을 확인했습니다 [실행 sha256].
  - 단계 2 하네스(`sdmpc_replay.py`, `u40_probe.py`, `c6_two_decision_chain.py`, `c6_independent.py`, `c6_lib.py`, `run_suites.py`, `c6_prev_reader_audit.py`)를 수정 없이 썼습니다. 모니터 v2 때문에 바뀐 둘은 사본을 만들었습니다: `H/c6_chain_inputs3.py`(`gather(..., details='all')`), `H/c6_analyze3.py`(flag 행 비교·flag 집합·v1 대조 추가; `S3/make_analyze3.py`가 원본에서 패치로 생성).
  - 키 없음 비교 기준: 단계 1 재생(`B/impl/stage1/probe/b2_base`, `…/sdmpc/b2_*`)과 단계 2의 같은-호출 키 없음 재생(`B/impl/stage2/run2/sdmpc/off_s1_T3600`, `_T6300`). 키 없는 코드 경로는 단계 2 이후 바뀌지 않았습니다(어댑터 `da469e21…` 그대로, SM은 키가 있을 때만 import) [실행 sha256, 읽음 A:13644-13647 (import :13646, 설정 검증 :13647)].
  - 증거 초안: `B/u4/*`(U4), `B/u5_derive.py`·`u5_build_contract.py`(U5), `B/u6/*`·`u6_diagnosis.md` §7.1(U6)의 방법을 저장소 생성기로 이식했습니다(§4). 초안 파일 자체는 값으로 쓰지 않았고, 이식이 초안을 재현하는지만 대조했습니다.

---

## 2. C6 비용 축소 (사용자 결정 2026-09-29) [실행: 코드, 시험]

### 2.1 바꾼 것 (SM만; 어댑터는 바꾸지 않음)

| 무엇 | 위치 | 내용 |
|---|---|---|
| 스키마 | SM:62 | `urban-starvation-monitor/v1` → **v2**. 규칙·스트릭 의미는 같고, 계산·기록 범위만 바뀝니다. 모듈 규약(SM 문서 끝 "상수를 바꾸면 SCHEMA가 바뀐다")에 따라 올렸습니다. 이전 v1 블록은 `schema_mismatch`로 이어 받지 않습니다 |
| **inpx 1회 파싱** | SM:165-218 `_physical_groups_of_root`, `_topology_of_root`, `network_view` | v1은 `SHO.physical_groups`와 `network_topology`가 각각 파싱(결정당 2회, 0.18 s). v2는 한 번 파싱한 root에서 둘 다 만듭니다. 그룹 규칙은 SHO:89-111을 줄 단위로 옮긴 것이고, T2:830이 규칙의 모든 제외 사례 픽스처와 v3b 망 실제 계획에서 `SHO.physical_groups`와 **같은 dict·같은 순서**임을 확인합니다. SHO 자체는 건드리지 않았습니다(키 없는 경로 무변경) |
| **flag 행만 표에** | SM:545-600 `evaluate` | `groups`·`boundary` 표는 flag 1 행만 담습니다. `counts`는 모든 행을 세고, `streaks`는 v1도 0이 아닌 것만 담았으므로 그대로입니다 |
| **세부값은 flag 그룹만** | SM:399-499 `gather` (:457 `wanted`) | `stopped_prev`(T−150 프레임), `floor_status`(멤버 탐침·헤드 창), `hw_*`를 flag 그룹에만 계산합니다. flag 그룹이 없으면 T−150 프레임·derived 헤드 창을 **읽지 않고** 탐침도 부르지 않습니다(`inputs.frame_previous = 'not_read_no_flagged_group'`, SM:491). `details='all'`은 오프라인 검사용으로 모든 그룹의 세부값을 계산합니다(G-C6-1 궤적 대조) |
| 상수 축약 (추가) | SM:83-121 | v1 값은 모두 유지하되 긴 규칙 문장은 짧은 코드로(설명은 모듈 안 `CONSTANT_CODES`, 블록에 모듈 sha 기록), 이름 목록 3개는 쉼표 문자열로(`LIST_CONSTANTS`). 들여쓰기된 action JSON에서 상수 블록이 ~1.9 kB → ~0.8 kB. **사용자가 지정한 두 방법 밖의 변경입니다.** 두 방법만으로는 모의 계산에서 JSON 증가가 평균 0.94%·최대 1.12%(61개 중 7개 >1%)여서 더했습니다 [실행 `S3` 모의 계산]. 되돌리기 쉬운 독립 변경입니다 |
| 벽시계 반올림 | SM:672-673 | `elapsed_sec`·`elapsed_parts_sec`를 `decision_wall_sec`처럼 1 µs로 반올림 |

- 계획 §4.2 "고정 상수는 metadata `constants`로 기록"은 지켰습니다(값은 전부 기록, 문장만 코드화). 
- 키가 없으면 SM은 import되지 않고 어댑터는 그대로입니다(T2의 AST 시험 2개, §5).

### 2.2 프로파일 (조용한 기계, R-obs-b 설치 후 `sm.run` 반복) [실행 `S3/profile`, `S3/profile_v2`, 도구 `H/c6_profile.py`]

| 상태 | v1 (단계 2 모듈) | v2 |
|---|---|---|
| T2700 (flag 2) | 0.42–0.56 s; 멤버 탐침 105회 0.26 s(cProfile), inpx 2회 0.18 s, T−150 프레임 0.11 s | 0.16–0.19 s; inpx 1회 0.11 s, 프레임 0.09 s(flag가 있어 읽음) |
| T450 (flag 0) | – | 0.11–0.12 s (inpx 0.11 s가 거의 전부) |

---

## 3. C6 관문 재실행 (계획 §6.9, §6.1 (d)) [실행 `R3/stage3_results.json`, 분석 `H/c6_analyze3.py`]

대기열 `R3`: 93단계(SDMPC 5 + G-C6-4 2 + 궤적 2 + R-obs-b 61 + 교대 20 + 스위트 + 감사), BELOW_NORMAL, 스레드 1, `NUMBA_CACHE_DIR=…/nbc_b2i`, 10:28 BEGIN → 13:23 ALLDONE, **BEGIN과 ALLDONE의 diff가 같음** `66e22abe…`(SM v2 + T2 C6 시험), 어댑터 `da469e21`.
- 대기열 사건: 11:19–12:43 다른 워크플로(`scratchpad/hybrid`, `D:/VISSIM-merge/sim3-n31-hybrid`)의 SDMPC 재생이 연달아 돌아, "외부 재생 중에는 기다린다"는 단계 2 대기열 규칙 때문에 45분간 멈췄습니다. 제 대기열 프로세스(자식 없음을 확인)를 멈추고, 기다리지 않고 **외부 재생을 단계마다 기록하는** 사본 `H/c6_queue3.py`로 같은 산출 폴더에서 이어 돌렸습니다(`R3/chain.log` 12:43:30 BEGIN, `CONCURRENT` 줄). 그 뒤 R-obs-b 43단계 중 24단계, 교대 20단계 중 19단계가 외부 SDMPC 재생 1개와 동시에 돌았습니다. 제 재생은 끝까지 한 번에 하나였습니다.

### 3.1 G-ID (d) = G-C6-0

**(a) R-obs-b 61상태, 기본 튜닝 + C6 키(`419a499a`)** — `R3/probe/c6_base`, 대조 `B/impl/stage1/probe/b2_base`

| 검사 | 결과 |
|---|---|
| 종료 / `MRS compare` 5검사 | 61/61 종료 0, **IDENTICAL 61/61** |
| 키 없는 단계 1 재생과 action JSON 전체 차이 | C6 키 61, provenance 610, 벽시계 183, **그 밖 0** (토큰·이전 핀·경로 0) |
| adapter stdout | 61/61에서 `"starvation"`만 다름(필드 최대 71 B, 줄 최대 601 B) |
| 블록 | 오류 0, prior `no_previous_action` 1·`no_monitor_block` 60, flag 합 50(단계 2와 같음), 경보 0 |

**(c) SDMPC 결정 재생 5개, C6 키** — `R3/sdmpc/c6_*`

| 상태 | compare | 녹색/offset | 선택/유지 목적값 (기록 = 재생) | tangent | 단계 1 키 없음과 차이 | 같은-호출 키 없음(단계 2 `off`)과 차이 | csv·stderr |
|---|---|---|---|---|---|---|---|
| S1 1800 | 5/5 ok | 같음 | 460.9685165323024 / 462.7372813177537 | 같음 | C6 1, prov 10, 시간 36, 토큰 14, **그 밖 0** | – | 바이트 같음 |
| S1 3600 | 5/5 ok | 같음 | 491.4356825691444 / 493.5432636752482 | 같음 | 그 밖 0 | C6 1, prov 8, 시간 37, 토큰 12, **그 밖 0** | 같음 |
| S1 6300 | 5/5 ok | 같음 | 357.44510216515835 / 359.3969080380441 | 같음 | 그 밖 0 | 그 밖 0 | 같음 |
| S0e 1800 | 5/5 ok | 같음 | 468.49466951165346 / 470.22280722558446 | 같음 | 그 밖 0 | – | 같음 |
| S0e 3600 | 5/5 ok | 같음 | 490.13138414502527 / 491.4703575883558 | 같음 | 그 밖 0 | – | 같음 |

- 목적값은 단계 2와 소수 끝자리까지 같습니다. "토큰"은 단계 1·2에서 행동이 아님을 보인 pickle sha 류입니다.

### 3.2 G-C6-1 입력 대조

| 대조 | 범위 | 결과 |
|---|---|---|
| 어댑터 블록의 flag 행 vs 독립 재계산(`H/c6_independent.py`, 모니터·SHO import 안 함) | SDMPC 5블록 27행 + R-obs-b 61블록 50행 | **불일치 0** (헤드/공급 차로, 정지 수 T·T−150, 녹색, 하한 유무) |
| **flag 집합** (v2에서 새로 필요) | 66블록 | 블록의 행 집합 = 독립 정지 수 + 기록 녹색 + 같은 튜닝의 궤적 설치 하한으로 판정한 flag 집합, 66/66 같음. `counts.groups_flagged` = 행 수 |
| 모듈 `gather(details='all')` vs 독립 재계산, 기록 궤적 | S1·S0e 각 61상태 × 105그룹 = 12,810 | **불일치 0** |
| 궤적 설치 cfg vs 어댑터 블록 | 5상태 | 그룹 행 불일치 0, `bound_veh` 불일치 0 |
| `B/c6_dryrun.json` | S1 9 + S0e 4 | 13/13 일치 |

- 하한(`floor_s`)은 튜닝 정적이라 궤적 설치 한 번의 값을 썼고, 61상태 모두에서 그룹별 하한이 변하지 않음을 확인했습니다(`floors_from_chain`, 두 튜닝 각 105그룹, 변동 0).

### 3.3 G-C6-1b

- 궤적 격자(M ∈ {8,6,4} × tol ∈ {1,2,4})가 단계 2와 같습니다: M8 tol1 → S1 SC109_p3_L173 첫 경보 **4,650 s**, 경보 결정 14; S0e 0건. 선택 **tol 1.0, M 8** (§10-10 초기값 그대로).

### 3.4 G-C6-2

- 두 런 모두 메모리 연쇄 = 파일 연쇄(`read_prior`로 합성 이전 JSON 읽기) = 독립 연쇄, 모든 결정에서 streaks·bound_streaks가 같습니다. 파일 연쇄 prior: `valid` 59, `no_previous_action` 1, `time_mismatch` 1(T=150; 직전 결정이 T=1).

### 3.5 G-C6-3 시간·크기 — **no-control 1% 한도 판정**

**R-obs-b 61 (no-control, 결정 약 22–28 s, 약 350 kB)**

| 지표 | 단계 2 (v1) | 단계 3 (v2) | 1% 한도 |
|---|---|---|---|
| 모니터 자체 시간 평균 | 0.502 s | **0.184 s** (−63%) | – |
| 결정 대비 평균 / 최대 | 2.25% / 3.1% | **0.79% / 1.25%** | 평균 통과, **결정별 8/61 초과** |
| 1% 초과 결정 | 대부분 | T1050 1.01, T1500 1.22, T3000 1.25, T3150 1.02, T3600 1.08, T4650 1.18, T5250 1.17, T7350 1.10 (%) | – |
| 교대 10쌍 (키 없음/있음, 900–9000 s) | 평균 +1.68% | **평균 +0.07%, 중앙 +0.49%** (범위 −8.6~+4.5%) | 통과(잡음 큼) |
| action JSON 증가 (61상태, 단계 1 키 없음 대비 원본 바이트) | +24.0 kB, +6.8% | **평균 +2,883 B (+0.82%), 최대 +3,410 B (+0.95%)** | **61/61 통과** |
| 교대 쌍 JSON 증가 | – | 평균 0.82%, 최대 0.91% | 통과 |
| stdout 필드 / 줄 | 71 B / ≤601 B | 71 B / ≤601 B | ≤512 B 통과 |

- 시간 분해(평균/최대 s): inpx 0.123/0.189, 세부값 0.040/0.108, 이전 action 0.009/0.018, 그룹 0.006/0.049, 레코드 0.004/0.013 [실행 `R3/stage3_results.json` `gid_d_a.monitor_parts`]. flag 0개 결정 평균 0.62%, flag ≥1 결정 평균 0.90%.
- 부하: 이 구간의 결정 벽시계 평균은 23.27 s로 단계 2(22.35 s)보다 길었고, inpx 파싱도 조용한 기계(0.09 s)보다 느렸습니다. R-obs-b 43단계 중 24단계가 외부 SDMPC 재생과 겹쳤습니다(§3 머리). 조용한 기계 프로파일(§2.2)은 flag 2개 결정에서 0.16–0.19 s(22.7 s의 0.7–0.85%)였습니다 [실행]. 단계 3 모니터 시간을 단계 2 결정 벽시계로 나누면 평균 0.82%, 최대 1.31%입니다 [실행].
- **판정 요약**: 크기는 결정별로 통과, 시간은 평균·교대 쌍 기준으로 통과, 결정별 최대 기준으로는 8/61이 1% 약간 초과. 폐루프에서 no-control 결정은 워밍업 6개(T<900)뿐입니다 [읽음 STAGE2 §5.5]. 남은 레버는 §7-1.

**SDMPC 5결정**: 모니터 1.00–1.84 s = **0.20–0.30%**(단계 2 0.23–0.34%), 블록 **5.3–7.9 kB**(v1 26.8–27.4 kB), action JSON 약 57.4–57.8 MB의 0.01%, stdout 필드 71 B. 대부분이 이전 action(58 MB) 읽기 0.72–1.40 s입니다.

### 3.6 G-C6-4 두 결정 연쇄 [실행 `R3/g_c6_4`]

| 검사 | 결과 |
|---|---|
| A(이전 = C6 켠 3600 재생 산출물)·B(이전 = 기록) 각각 vs 기록 3750 | 둘 다 IDENTICAL, `prev_chain/` 파일 불변 |
| A vs B | csv 바이트·제어 7필드·녹색·offset·목적값(483.34965062709864 / 484.0576866684797)·tangent 계수·stderr 같음 |
| A vs B JSON 차이 | C6 63, provenance 2, 시간 31, 토큰 33, **이전 action 핀 3**(`sdmpc_state/previous_application/receipt_sha256`, `joint_leader_selection/price_state/previous_application/receipt_sha256`, `n31_binding/vsl_cohort_initialization/sha256`), **그 밖 0** |
| A의 블록 | prior `valid`(3600), 스트릭이 3600의 스트릭 + 1로 이어짐(SC1002_p1_L427, SC1004_p1_L66, SC1004_p2_L66, SC6_p2_L1210018302 = 2) |
| B의 블록 | prior `no_monitor_block`, 스트릭 모두 1 |

**판정: 통과.**

### 3.7 v1 → v2 블록 동일성 [실행 `c6_analyze3` `v1_v2`]

- 같은 상태의 단계 2(v1) 블록과 비교했습니다: R-obs-b 61/61, SDMPC 5/5에서 **v2 표 = v1의 flag 1 행(10필드 모두), 경계 표 = v1의 비율 ≥ 0.95 행, counts·streaks·bound_streaks·alarms·bound_alarms·prior·boundary_status 같음**. 계산 범위를 줄였지만 판정값은 바뀌지 않았습니다.

### 3.8 상태 불변·스위트·감사

- 상태 불변(`R3/chain/S1.json` `state_check`): 실제 설치 cfg(S1 3600)에서 실제 멤버 탐침으로 `sm.run`, 14개 대상 해시 변화 0, stdout·stderr 0 B, 이전 action sha 불변 [실행].
- 스위트(`R3/suites`, `H/run_suites.py`): 단계 2 대비 공통 40실행 **회귀 0, 개선 0**(`R3/suite_compare_vs_stage2.json`). n31 167 OK(skip 3), n31_batch2 33 OK. fixture 스위트(30실행)는 돌리지 않았습니다: SM은 키가 있을 때만 import되고 fixture들은 C6 키를 쓰지 않으며, 단계 2에서 MAX_PATH 사고를 낸 도구라 [추론] 생략했습니다.
- 이전 action 독자 정적 감사 재실행(`R3/prev_reader_audit.json`): `read_prior`는 바뀌지 않았고 독자 목록도 단계 2와 같은 구성입니다.

---

## 4. 증거 파일 확정 (계획 §4.3, §9)

### 4.1 공통

- 새 파일(모두 W 안, untracked):
  - `scripts/urban_b2_evidence.py` 363줄: 공통 판독기(한 번 파싱한 `Network`와 서명, `.sig` 녹색/황색 창, `.lsa` 대조, `stream_fzp`(파일 sha256을 같은 통과에서 계산), `.mer` 헤드 검지기, relFlow 규칙). 런타임 import 없음.
  - 생성기 5개: `scripts/derive_phase_authority_shared_lane_v3b.py`, `scripts/derive_shared_head_groups.py`, `scripts/derive_head_saturation.py`, `scripts/derive_ramp_diverge.py`, `scripts/check_urban_batch2_evidence.py`(교차 검사).
  - 포착 도구: `N31/tools/capture_urban_runtime.py` 191줄.
  - 산출: `U/physical_phase_authority_v3b_q2_20260929.json`, `U/urban_movement_runtime_v3b_20260929.json`, `U/shared_head_groups_v3b_20260929.json`, `U/head_saturation_v3b_20260929.json`, `U/ramp_diverge_v3b_20260929.json`, `N31/beta/movement_beta_routing_v3b2q2_20260929.json`.
- 모든 산출이 망 `N31/network/baseline_s31_v3bnc.inpx`(`be0075bf…`)를 `{path, sha256}`으로 핀합니다. 외부 입력(NC 5시드 FZP, R-obs-b FZP/.mer/.lsa)은 경로·sha256·크기로 핀합니다(FZP 5개 각 약 1.15 GB).
- 어떤 런타임 모듈이나 config도 새 파일을 참조하지 않습니다 [실행: `evaluation`, `vendor`, `N31/*.json` grep 0건]. 설치는 단계 4~6입니다.
- 생성 순서(`S3/evidence_run.sh`, 한 번에 하나, BELOW_NORMAL, 결정류 프로세스 전에는 외부 재생 대기 `H/wait_no_replay.py`): Q2 → Q2 β → 런타임 포착 → U5 → U4 → U6 → 교차 검사 → 모든 `--check` → Q2 설치 확인 [실행 `EV/run.log`].

### 4.2 Q2: SC105·SC1 공유 좌회전 차로 현시 권한 → p3 (U1 SC7 정정과 같은 방식)

- 생성기: `scripts/derive_phase_authority_shared_lane_v3b.py`. 대상은 `MOVEMENTS`(:52) 둘: `SC105_E_to_S_SC1005`, `SC1_W_to_N_SC101`. U1 SC7 정정 생성기(`scripts/derive_phase_authority_v3b.py`)와 같은 행 구조를 만들고, `physical_movement_routes.configure_phase_authority`(physical_movement_routes.py:131-351)가 설치 때 다시 확인하는 조건을 생성 때 모두 검사합니다: 커넥터 경로, 신호 자기 헤드가 커넥터 앞에서 출발 링크의 모든 차로를 덮음, 정적 경로가 헤드 앞에서 진입, 헤드 SG의 유일한 계획 현시에 native 녹색이 있음, 선언 현시가 그 SG를 갖지 않음.
- 산출 `U/physical_phase_authority_v3b_q2_20260929.json` (`0a061172…`, 35,755 B) = 묶음 1 권한 `U/physical_phase_authority_v3b_20260926.json`(`e729cdc4…`, U1+U3 튜닝이 쓰는 것)을 그대로 복사 + 2행 + `shared_lane_corrections` 기록.

| movement | 경로 | 헤드 | 선언/런타임 → 새 현시 | 쌍둥이(같은 커넥터, 다른 origin) |
|---|---|---|---|---|
| SC105_E_to_S_SC1005 (boundary_in, in_SC105_E) | 1220007001 → **10669** → 1220006403 (경로 1042:1) | 1050601·1050602, 둘 다 SC105 SG 6 | SC105_p4 (SG 1·5) → **SC105_p3** (SG 2·6) | SC105_E_SC1_to_S_SC1005: 2026-08-28 현시 보정으로 이미 p3 (SG 6, signalhead_confirmed) |
| SC1_W_to_N_SC101 (boundary_in, in_SC1_W) | 1220007104 → **10562** → 1220008501 (경로 11:1) | 10202·10201, 둘 다 SC1 SG 2 | SC1_p4 (SG 1·5) → **SC1_p3** (SG 2·6) | SC1_W_SC105_to_N_SC101: 이미 p3 (SG 2) |

- **원인** [읽음 `outputs/movement_phase_correction_20260828.json`]: 08-28 보정은 내부 별칭만 이름으로 고쳤고 경계 별칭은 빠졌습니다. 그래서 한 물리 좌회전이 origin에 따라 p3과 p4로 따로 서비스되었습니다(U5 초안의 `pure_phase_mismatch`).
- **신호 증거** [실행]: 계획 SG 집합(SC105·SC1 모두 p3 = {2, 6}, p4 = {1, 5}); native `.sig` 프로그램(SC105 `개포동 test-bed105_n4dr150.sig` 주기 150 s, SG 6 녹색 35 s, SG 1·5 34 s; SC1 `…test-bed1_n4dr150.sig` SG 2 32 s, SG 1·5 31 s); `.sig` 창과 R-obs-b `.lsa`의 불일치 SG 0.
- **FZP 증거 (NC 5시드, 5 s 프레임)** [실행]: 커넥터로 나간 차량이 자기 차로 헤드를 지난 5 s 구간의 헤드 SG 상태.

| movement | 통과 | SG 녹색 | 황색 | 적색 | 선언 현시만 녹색인 구간 |
|---|---|---|---|---|---|
| SC105_E_to_S_SC1005 | 1,250 (시드별 238–268) | 1,249 | 1 | **0** | **0** |
| SC1_W_to_N_SC101 | 1,135 (214–246) | 1,128 | 7 | **0** | **0** |

- **정확 통과시각 증거 (R-obs-b = seed 31 궤적, obs150 헤드 검지기 .mer)** [실행]: SC105 250건 중 SG 6 녹색 249·황색 1·적색 0, 선언 현시(p4) 녹색 중 통과 0; SC1 235건 중 녹색 230·황색 4·적색 1, p4 녹색 중 1(적색 전환 경계에서 진입한 1대). 5 s 분류와 정확 분류의 교차표도 파일에 둡니다.
- 도구 결함 하나를 개발 중에 고쳤습니다 [실행]: 첫 판의 통과 구간 판정이 "헤드 앞 마지막 관측"만 봐서, 출발 링크에서 차로를 바꾼 차량 5대를 적색으로 잘못 셌습니다(정확 시각과 대조해 발견). 지금은 "헤드를 처음 지난 관측과 그 직전 관측이 한 프레임 차이"로 판정합니다(`fzp_crossings`, :93-125). 또 경로 11:1이 착지 링크(출구 2개)에서 끝나 SC7 생성기의 "유일 출구" 규칙으로는 기록용 `crossed_heads_after_source`를 못 만들어, 경로 종점 `destPos`까지를 착지 구간으로 봤습니다(두 경로 모두 해당 헤드 0개).
- **실제 설치 체인 확인** [실행 `EV/q2_install/q2_install_check.json`, 하네스 `H/q2_install_check.py`]: U1+U3 튜닝의 권한을 Q2 파일로, `urban.beta.sha256`을 Q2 β 표로 바꾼 임시 튜닝으로 R-obs-b T2700을 `configure_runtime`까지 설치했습니다. `routing_v3b2`의 표 경로 등록(`BETA_EVIDENCE_JSON`, A:3998-4003)은 **메모리에서만** Q2 표로 바꿨습니다. 결과: `configure_phase_authority`(교정 7건)·`check_complete_beta_runtime`·그 밖 설치기가 모두 통과했고, 묶음 1 포착과 비교해 **바뀐 것은 두 movement의 현시뿐**(SC105_p4→p3, SC1_p4→p3), 용량 맵 동일.
- **Q2 β 표** `N31/beta/movement_beta_routing_v3b2q2_20260929.json` (`b41d6a10…`): 기존 생성기 `scripts/derive_routing_beta_physical.py --phase-authority <Q2>`로 만들었습니다. 묶음 1 표(`41b3113f…`)와 β·사유·접근로·무흐름 현시(`SC109_p1`)·굶김 가드·선언이 모두 같고, `inputs.phase_authority`·`generated`·`runtime_phases`만 다릅니다(런타임 현시 변경 +3: SC105_E_to_S_SC1005, SC1_W_to_N_SC101, 그 병합 가족 SC1_W_to_N). **이 표를 config가 쓰려면 어댑터의 β 원천 등록(A:3998-4003)과 `beta_source.COMPLETE_BETA_SOURCES`(beta_source.py:40)에 이름 하나가 필요합니다**(§7-2).

### 4.3 런타임 포착 (U5의 입력)

- 도구 `N31/tools/capture_urban_runtime.py`: `make_replay_state_v2.prepare`(복사만), 어댑터 `__main__`을 `replay_decision_n31.ps1`과 같은 인자·환경으로 실행하고 `runtime_setup.configure_runtime` 반환 직후 멈춥니다(투영·예측·결정·출력 없음). `--check`는 다시 포착해 바이트를 비교합니다.
- 산출 `U/urban_movement_runtime_v3b_20260929.json` (`e45b3eb4…`): R-obs-b T2700(state `ca6a29ab…`), 튜닝 U1+U3(`f137f711…`), 망 sha `be0075bf…`, movement 356개(필드 13개), 용량 맵. 설치 메타: 물리 현시 권한 교정 5, 무신호 권한 4, 완결 β 492.
- U5 초안이 쓴 옛 트리(cf3ce37) 포착과 비교: kind·origin·phase·수신 링크·β·용량이 모두 같고, 다른 것은 옛 포착에 없던 필드(destination·intersection·turn)뿐입니다 [실행].

### 4.4 U5 계약 v1 `U/shared_head_groups_v3b_20260929.json` (`164016f9…`, 652,355 B)

- 생성기 `scripts/derive_shared_head_groups.py`. 초안(`B/u5_derive.py` + `u5_build_contract.py`)의 멤버십 규칙(제어 헤드 = 같은 제어기의 분기 직전 마지막 헤드, 없으면 착지 차로 첫 헤드)을 그대로 옮겼습니다. 입력은 런타임 포착(§4.3), Q2 권한(포착한 튜닝의 권한에 없는 행을 `configure_phase_authority`와 같은 방식으로 적용, :150-162), U1 β 표(출구 커넥터), 튜닝이 이름 붙인 U3 증거·헤드 자원 계약·회랑 증거 4개, 1093 pre-head 증거, 차로 파일 둘(기록용).
- **과대 판정은 U4 기준으로 바꿨습니다**: 구성원의 차로 = 그 그룹 헤드 뒤에서 그 구성원 커넥터가 떠나는 물리 차로. 라미나 집합 중 하나라도 구성원 차로 합 > 집합 차로 수면 과대입니다(`overcounted_lane_sets`). U4 용량이 `s_g × |lanes(m)|`이기 때문입니다. 초안은 현 plant의 차로 파일 단위(`plant_lane_units`)로 셌고, 이 값도 기록합니다.
- 행 필드: 헤드, `physical_lanes`(n_g), 차로별 사후 커넥터·흐름 구성원, 구성원(커넥터·차로·도착지·kind·origin·수신 링크·런타임 현시·β·흐름·**소유자**·`source_key`·현시 관계), 외래 현시 구성원(다중 현시 커넥터 15), 라미나 집합, `saturation_ref`(= U4 키), `green`(현시 또는 native 고정 계획), `discharge_owner`, `enforcement`.
- `split_rule.name = "queue_proportional_fifo_v1"`, 예산·정적 축소 식은 문서 머리 `budget_rule`에 있습니다. 완결성 허용 목록 `non_members_with_flow` 65개(U3 23, 현시권한·B5 8, 헤드 없음 18, 비도시·미드블록 3, 하류 외래 정지선 3, native 헤드 없음 10) — 초안과 같습니다.

| enforcement | 수 | 비고 |
|---|---|---|
| budget | 46 | 초안 budget 45 중 44 + Q2로 풀린 SC105 1220007001\|p3·SC1 1220007104\|p3 |
| budget_supersedes_head_resource_10629 | 1 | 52\|p3 |
| delegated_lane_urban_runtime | 2 | 71\|p3, 71\|p4 (LUR CTM) |
| static_reduction_serial_head | 1 | **1220008601\|p1 (SC7)**: 차로 2에 SG 7(p2, 33.13 m)과 SG 4(p1, 33.26 m) 직렬, 구성원 SC7_N_SC11_to_E_SC16가 p2에서 서비스. 사용자 결정 Q2 |
| serial_first_head_prehead_1093 | 1 | 1220012001\|p3 (소유자 prehead_1093) |
| native_budget | 10 | 사용자 결정 Q1 |
| not_binding / native_not_binding / no_flow_member | 54 / 53 / 6 | 구성원 상한이 이미 그룹을 묶음 / 포착 시점 흐름 없음 |

- **"과대 그룹 전부"의 대응**: 제어 108그룹 중 과대는 50개이고 **전부** budget 46·10629 1·LUR 2·정적 축소 1로 처리됩니다. 계획의 "53"(초안, plant 단위)과의 차이 3개는 U4의 물리 차로 기준으로 과대가 아닌 그룹입니다: 1220018401\|p3(구성원 하나, 차로 파일은 4차로인데 커넥터는 3차로 → U4에서 `s × 3 = n_g × s`), 초안의 "파생 기준으로만 과대" 2개. native는 과대 10개(초안 12: 4개는 물리 차로로 과대 아님, 1220001501\|nSG4·1220022604\|nSG2는 새로 과대) [실행].
- 대기 행 0, 순수 현시 불일치는 SC7 한 행(정적 축소)만, 라미나 아님 0, 모듈을 가로지르는 그룹 127\|p3·127\|p4(offramp_drain+regular)와 71\|p3·p4(LUR). 초안과 구성원 집합 차이 0 [실행].

### 4.5 U4 표 v1 `U/head_saturation_v3b_20260929.json` (`09462676…`, 436,154 B)

- 생성기 `scripts/derive_head_saturation.py`: 초안 `B/u4/{trees,analyze_run,build_table}.py`를 한 파일로 옮겼습니다(방법·상수 동일). 그룹은 U5 계약 v1의 174행에서 읽고(계약 sha 핀), 관측 그룹이 `SHO.physical_groups`와 같은지(여러 헤드 차로의 제어 헤드 추가만 허용) 확인합니다. 녹색 창은 핀된 망의 `.sig`(NC는 고정시간)이고, 각 NC 시드의 `.sig`와 바이트가 같은지, R-obs-b `.lsa`와 창이 같은지(불일치 SG 0) 확인합니다. NC 5시드의 망 서명(헤드·커넥터·제어기·정적 경로)이 핀된 망과 같습니다.
- **이식 검증** [실행]: 초안의 105그룹만 넣으면 초안 표를 재현합니다. 위치·속도를 초안처럼 float32로 저장한 변형은 105행의 측정 블록·flag가 **전부** 같고, v1(float64)은 1220012001\|p3 한 행만 1569.2 → 1568.6로 다릅니다(초안의 float32 반올림). native·다중헤드 헤드를 더해도 관측 105행은 하나도 바뀌지 않습니다.
- 값 규칙: 실측(bins ≥ 24, cycles ≥ 8, 시드 ≥ 3) = 비방해 주값, 기본값 1,850, **직렬 첫 헤드 규칙**: 1210012001\|p3(헤드 30601, SC11 SG 6, 표본 0)은 같은 SG의 첫 헤드 그룹 1220012001\|p3(30603·30604, 1093 pre-head 쌍)의 값 1,568.6을 받습니다(§4.3-1 값 규칙; `SERIAL_DOWNSTREAM` :79, 생성 때 1093 증거·SG·커넥터로 관계를 확인). 30602(p4, 12 bins)는 규칙 밖이라 기본값입니다.

| 부류 | 그룹 | 실측 | 기본값 | 직렬 | 실측 중앙 (veh/h/차로) |
|---|---|---|---|---|---|
| 관측 105 | 105 | 65 | 39 | 1 | 1,859.7 |
| 다중헤드 3 | 3 | 3 | 0 | 0 | 1,747.1 (1220011001\|p1 1,747.1·68 bins, 1220013600\|p3 1,892.8·229, \|p4 1,576.2·37) |
| native 66 | 66 | 42 | 24 | 0 | 1,896.8 (1,460.6–2,065.0) |

- native_budget 10행은 모두 실측입니다. SC7 1220008601\|p1은 차로 2 헤드 140402가 더해졌지만 표본 2 bins라 기본값 1,850입니다(정적 축소가 이 값을 씀). 측정 실측 110개 분위: 최소 1,246.7, 중앙 1,872.0, 최대 2,065.0; flag 29그룹(기록용).
- 초안에 있던 plant·collector·폐루프 열은 저장소 입력으로 재현할 수 없어 싣지 않았습니다(초안 파일은 참고로 남음).

### 4.6 U6 분기 증거 `U/ramp_diverge_v3b_20260929.json` (`0aacabf1…`, 11,264 B)

- 생성기 `scripts/derive_ramp_diverge.py`. 값은 핀된 inpx에서만(정적 경로결정·커넥터 기하), NC 5시드 FZP는 검증에만 씁니다(u6 §7.1 원칙).

| 항목 | 값 (inpx) | 검증 (NC 5시드, 900–9000 s) |
|---|---|---|
| gate_onramps | SC1001_W_to_onW: 10482(2차로), 분기 32@1,028.62 m, 1136:1 relFlow 6/9; SC1001_W_to_onE: 10490(1차로), 129@299.99 m, 1136:3 2/9; 결정점→분기 1,010.6/1,311.7 m | 1136 경로 실현 몫 0.668 / 0.108 / 0.223 |
| stopline_route·gate_storages | 1136:2 (1/9): 32 → 129 → 127 | – |
| diverge_lane_capacity_veh_h | 1,800 (선언) | 150 s 창 최대 진입 1,176–1,260 veh/h/차로, 그 창에서 분기 150 m 안 정지 0 |
| w_out SC1001_W_out | 31 + 124 = **734.24 m**, 1137: RM_C10484 0.5 / RM_C10480 1/3 / free 1/6 | 진입 5,323대: 0.508 / 0.311 / 0.167 (기타 0.3%, 복수 1.1%) |
| w_out SC1004_W_out | 68 + 121 = **351.35 m**, 1135: RM_C10681 0.6 / RM_C10646 0.2 / free 0.2 | 18,062대: 0.598 / 0.194 / 0.202 |
| direct_landings 10483 | 124@201.15 m 착지, 유일 경로 1131:3이 10775 → 125로 나감 → SC1001_W_tail | 11,839대 중 꼬리 11,821, 미확인 18 |
| gate_onramps_retired SC1004_W_to_onE | 10639를 지나는 정적 경로는 1134:3(69 → 10637 → 70 → 10639)뿐 → 공유 줄기 소유 | 10639 진입 4,152대 전부 10637 경유(10638 경유 0) |

- 분할은 relFlow 정확 분수로 둡니다(0.5, 0.3333…, 0.1666…).

### 4.7 교차 일관성 (`scripts/check_urban_batch2_evidence.py`) [실행 `EV/logs/cross.txt`, T2:964]

| 검사 | 결과 |
|---|---|
| network: U4·U5·U6·Q2·Q2 β가 같은 inpx path+sha, 디스크 파일과 같음 | OK |
| u4_u5: U4 그룹 = U5 행 174 (헤드 집합 같음), U4가 이 계약 sha를 핀, 예산·정적 축소·직렬 행 모두 U4 값 있음 | OK |
| u6_u5: 게이트 on-ramp 3개(onW·onE·퇴역 onE)는 어느 U5 행의 구성원도 아니고 허용 목록(`unsignalized_phase_authority_or_B5_peeloff`)에 있음 | OK |
| q2_u5: U5가 Q2 파일을 핀, 두 movement가 새 현시·`match`·흐름·budget 그룹의 구성원 | OK |
| q2_beta: Q2 β 표가 Q2를 이름, 묶음 1 표와 β 등이 같고 차이는 inputs.phase_authority·generated·runtime_phases(+3)뿐 | OK |
| no_pending: 모든 enforcement가 알려진 부류, 대기 행 0 | OK |
| static_rows: 정적 축소는 SC7 직렬 헤드 행 하나, native_budget은 native 행만 | OK |

### 4.8 `--check` (바이트 재현) [실행 `EV/run.log`]

| 생성기 | 산출 sha256 | 시간 |
|---|---|---|
| derive_phase_authority_shared_lane_v3b.py | `0a061172…` | 101 s |
| derive_routing_beta_physical.py (Q2) | `b41d6a10…` | 1 s |
| derive_routing_beta_physical.py (묶음 1 표, 기존) | `41b3113f…` | 1 s |
| capture_urban_runtime.py | `e45b3eb4…` | 14 s |
| derive_shared_head_groups.py | `164016f9…` | 1 s |
| derive_head_saturation.py | `09462676…` | 297 s |
| derive_ramp_diverge.py | `0aacabf1…` | 111 s |

- 생성과 검사 사이 트리 diff가 같았습니다(`0c1b11c4…`). 개발 중 스크래치 산출과도 같은 sha(Q2·U6)입니다.

---

## 5. 단위 시험 [실행]

`python -B -m unittest test_n31_urban_batch2` (cwd `N31/tests`, 스레드 1) → **Ran 38, OK** (단계 2 28 + 아래 10).

| 시험 (T2) | 내용 |
|---|---|
| `StarvationMonitorCostTests` (:820) | SHO 규칙 동일(:830: 제외 사례 픽스처 + v3b 망·실제 계획 + 계획 없음), 결정당 inpx 파싱 1회(:854), flag 없으면 표 비고 프레임·헤드 창·탐침 안 읽음(:868), flag 행 세부값과 `details='all'`(:887), 상수 값 보존·코드 설명(:910) |
| 기존 C6 시험 1개 수정 (`test_each_condition_alone_resets`) | flag 0이면 표에 행이 없고 counts만 셈 |
| `UrbanBatch2EvidenceTests` (:958) | U5 계약 = 자기 유도(:959), 교차 일관성(:964), U5 행이 사용자 결정을 따름(:969), U4 값 규칙(:994), 망 핀(:1012) |

- FZP를 읽는 세 생성기(U4·U6·Q2)의 `--check`는 수 분이 걸려 단위 시험에 넣지 않고 §4.8로 받았습니다.

---

## 6. provenance와 안전 [실행]

| 트리 상태 | diff sha256 | 무엇으로 확인 |
|---|---|---|
| C6 관문 (SM v2 + T2 C6 시험) | `66e22abe…` | R3 BEGIN = ALLDONE, 산출 provenance 전부 이 값 |
| 증거 생성 후 | `0c1b11c4…` | EV GENERATED = 모든 `--check` 후 |
| **최종** (+ T2 증거 시험) | `0f56bd42a8e84af5bb9dcbe4cd5e6733bce094f8564b4d42d6ecc1cbd94569c6` | R3b BEGIN = ALLDONE |

- **최종 트리 다리**(R3b): R-obs-b T1·2700·4500·6300을 C6 켜고 재생 → 4/4 IDENTICAL, C6 블록이 R3 블록과 같음(벽시계 필드 제외), action JSON 차이는 벽시계·복사 state 경로/sha뿐. 스위트 40실행이 R3 대비 회귀 0, n31_batch2 38 OK. 관문 이후 바뀐 것은 런타임이 참조하지 않는 스크립트·도구·JSON·시험뿐입니다.
- 새 파일 0: 런 폴더 R-obs-b·S1·S0e와 NC 5시드 폴더, `frozen/sdmpc31_cf3ce374_202609261037`, `frozen/sdmpc31_886a014a_202609260935`(단계 3 시작 marker 이후 `find -newer`). `frozen/` 최상위에는 다른 워크플로의 동결 폴더 둘(`sdmpc31_43150c8e_202609291223`, `sdmpc31_d34fd1aa_202609291357`)과 robocopy 로그가 새로 생겼습니다. 이 단계의 어떤 명령도 `frozen/`에 쓰지 않았습니다 [추론: 모든 도구가 W 또는 스크래치만 씀, 폴더 이름의 커밋 접두사가 이 트리 것이 아님].
- OLD `D:/VISSIM-merge/sim3-n31-urban`: `git status` 0줄, HEAD `cf3ce37`. `sim3-n31-v3c1`은 건드리지 않았습니다(어떤 명령의 쓰기 대상도 아님).
- W의 `evaluation/controllers/__pycache__`: 개발 중 `-B` 없이 한 번 생겼던 것을 대기열 전에 지웠고, 지금 없습니다. `scripts/__pycache__`·`tools/__pycache__`도 없습니다.
- VISSIM·cscript 시작/종료 없음. 멈춘 프로세스는 제 대기열(PID 21780, 자식 없음, 12:43) 하나입니다. 워치독·cscript·ps1 시험은 돌리지 않았습니다(`run_suites.py` 제외 목록). seed 37, RM 팔, 봉인 시드 59/61/67은 열지 않았습니다. 폐루프 런·커밋·push 없음.
- 재생은 한 번에 하나였습니다. FZP 스트리밍도 한 번에 하나였습니다(일부는 제 재생 대기열과 동시에 돌았습니다: 스트리밍 1개 + 재생 1개).

---

## 7. 다음 단계로 넘기는 것 / 사용자 판단

1. **C6 no-control 시간 (판단 필요).** 크기는 결정별 통과(최대 0.95%), 시간은 평균 0.79%·교대 쌍 +0.07%로 통과이지만 결정별 8/61이 1.01–1.25%입니다(외부 재생 동시 부하 구간 포함). 싸게 더 줄이는 레버 둘(미적용, 적용 시 G-ID (d)·G-C6 재확인 필요):
   - (a) inpx에서 `<links>`와 `<signalHeads>` 구간만 파싱(프로파일 기준 약 −0.05~−0.06 s). 단위 시험으로 전체 파싱과 동일성을 확인해야 합니다.
   - (b) T−150 프레임의 행 단위 재검증 생략: 같은 sha 핀 바이트를 같은 결정의 `obs150_contract.load_bundle`(obs150_contract.py:1200-1216)이 이미 검증합니다(flag 결정에서 약 −0.03~−0.07 s).
   또 결정당 상수 블록을 줄인 것(§2.1)은 두 지정 방법 밖의 변경이므로 확인을 부탁드립니다.
2. **Q2 β 표 등록 (단계 4 또는 9).** 후보 config가 Q2 권한을 쓰려면 어댑터 `BETA_EVIDENCE_JSON`(A:3998-4003)과 `beta_source.COMPLETE_BETA_SOURCES`(beta_source.py:40)에 새 원천 이름(예: `routing_v3b2q2`)을 더하고, config에 `urban.movements.physical_phase_authority` = Q2 파일, `urban.beta.source`·`sha256` = Q2 표를 넣어야 합니다. 키가 없으면 비트 동일인 변경입니다. 이번에는 하네스에서 메모리로만 등록해 설치 체인을 확인했습니다(§4.2).
3. **U5 설치(단계 5)**: native 그룹의 `green.source = native_fixed_schedule`은 plant가 native 신호 구성원에 쓰는 고정 계획 함수(A:1578-1628, `build_patched_phase_green_fraction`; [읽음] U5 초안 정의)와 같은 호출이어야 합니다. 정적 축소(SC7)의 식은 `budget_rule.static_reduction`입니다. 계약은 T2700 한 상태의 흐름 구성원이라, §4.5-12의 61+S1·S0e 전수 확인이 남아 있습니다.
4. **U4 설치(단계 4)**: 그룹 밖 movement는 기본값 × 기존 차로 파일(표의 `default_veh_h_per_lane`), 게이트 peel-off·LUR 출구는 소유자가 덮음. 헤드 하한 차로 비율 콜백과 `install_lane_group_membership` 확장(단계 2 이월 메모)은 그대로 남아 있습니다.
5. **C6 경계 경보(206.53 표지)**: 이번 SDMPC 결정에서 결정당 경계 flag 16–33개였습니다. U4 뒤 줄어드는지를 C3 보조 지표로 단계 7에서 봅니다(이월).
6. **v3c1 재유도(§9)**: 생성기의 망·런 경로는 `scripts/urban_b2_evidence.py` 상수(`NETWORK`, `NC_ROOT`, `ROBS`)와 각 생성기 DEFAULTS에 있습니다. v3c1에서는 이 상수와 시드·결정 번호(1134–1137)를 인자로 바꿔 다시 만들고, 망 sha 핀이 어긋나면 설치가 실패합니다.
7. **대기열 규칙**: 외부 워크플로 재생을 기다리는 규칙이 45분 정체를 만들어, 이번 대기열 후반은 기다리지 않고 기록만 했습니다(`H/c6_queue3.py`). 시간 관문을 다시 잴 때는 조용한 구간에서 교대 쌍을 받는 편이 좋습니다.
8. 이월 메모(그대로): C6 키 1.0/8/3/3을 후보 config에(단계 9), 동결 전 `__pycache__` 삭제(현재 없음).

## 부록: 산출 파일

- 보고서: `B/impl/STAGE3.md`
- C6 관문: 대기열 `R3/queue.json`, `R3/queue_done.jsonl`, `R3/chain.log`, `R3/logs/`, 발사 `S3/launch_queue3.cmd`(WMI 분리), 결과 `R3/stage3_results.json`, 분석 로그 `R3/analyze3.log`, 스위트 대조 `R3/suite_compare_vs_stage2.json`, 정적 감사 `R3/prev_reader_audit.json`
- C6 프로파일: `S3/profile/profile_T2700.json`(v1), `S3/profile_v2/profile_T{2700,450}.json`(v2), 스모크 `S3/smoke/`
- 최종 트리 다리: `R3b/` (`chain.log`, `probe/c6_base/`, `suites/`, `suite_compare_vs_run3.json`)
- 증거 생성: `S3/evidence_run.sh`, `EV/run.log`, `EV/logs/*.txt`, Q2 설치 확인 `EV/q2_install/q2_install_check.json`
- 개발 산출(판정에 안 씀): `S3/evtree/`(스크립트 개발본, `out/dev_*`, float32 대조 `devf32/`, 로그)
- 하네스(새로): `H/c6_profile.py`, `H/c6_chain_inputs3.py`, `H/c6_analyze3.py`(+ 생성 스크립트 `S3/make_analyze3.py`), `H/c6_queue3.py`, `H/q2_install_check.py`, `H/wait_no_replay.py`
- 백업: `S3/starvation_monitor.stage2_4ddb5404.py`, `S3/test_n31_urban_batch2.stage2.py`
- 트리 새 파일: `W/scripts/{urban_b2_evidence,derive_phase_authority_shared_lane_v3b,derive_shared_head_groups,derive_head_saturation,derive_ramp_diverge,check_urban_batch2_evidence}.py`, `N31/tools/capture_urban_runtime.py`, `U/{physical_phase_authority_v3b_q2,urban_movement_runtime_v3b,shared_head_groups_v3b,head_saturation_v3b,ramp_diverge_v3b}_20260929.json`, `N31/beta/movement_beta_routing_v3b2q2_20260929.json`; 수정 `SM`, `T2`
