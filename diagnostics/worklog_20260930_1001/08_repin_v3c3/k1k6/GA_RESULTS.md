# GA 관문 결과: K1–K6 (K6 = `54d821c1`)

- 작성: 2026-10-01 14:30
- 기준 문서: sha256을 실행 전과 후에 각각 다시 계산했고 기록값과 같았습니다 [실행].
  - `GA_PREDECLARATION.md` `34cc48ee…`
  - 보충 1 `607a2eb5…`
  - 보충 2 `c96b8a02…`
- 표기
  - [실행]: 직접 돌려서 확인
  - [읽음]: 파일이나 코드에서 확인
  - [추론]: 시험하지 않은 판단
- 증거 폴더: `reports/k1k6/ga/`. 아래에서 상대 경로는 모두 이 폴더 기준입니다.

## 0. 판정표

| 관문 | 판정 | 핵심 근거 | 판정 파일 |
|---|---|---|---|
| N1 (진단) | 완료. 이번 단계에서는 다시 돌리지 않음 | 옛 트리에서 4050 SDMPC를 시드 0과 2로 돌렸습니다. CSV, 목적함수, 제어 필드, 탄젠트, 4필드가 모두 같았고 JSON 차이도 0입니다 | `../n1/n1_compare.json` |
| GA-1 | **통과 61/61** | 선언 밖 차이 0. 4필드 최대 ulp는 1/1/1/2. B1 양성 확인 61/61. 정수 리프 37,551개가 같음 | `judge_ga1.json` |
| GA-2 | **통과** | 4050, 4500, 900 각각 시드 3개가 비트 단위로 같습니다. 4필드도 비트 동일 | `judge_ga2.json` |
| GA-3 | **통과 5/5** | T5-B 기록과 CSV, 목적함수 repr, 제어 7, 탄젠트, derived가 같고 선언 밖 차이는 0 | `judge_ga3.json` |
| GA-4 | **통과 (사전 선언의 대체 경로)** | 기록 증거와 함수 수준 재현으로 옛 코드의 실패를 확인했습니다. K6 전체 반사실은 **다른 이유로 거부**됐습니다(정책 토큰 불일치). 그래서 선언대로 R-4 합성 fixture 시험 4개로 대체했고 모두 통과했습니다 | `judge_ga4.json`, `ga5/logs/k6gate/new.log` |
| GA-5 | **통과** | 실패 id 집합이 묶음마다 `9ed2ef0` 기준선과 같습니다. 새 시험도 모두 통과 | `ga5/logs/k6gate/*` |
| 상시 §4 | 통과 75/75 | GA-1, GA-2, GA-3 재생 75건 모두 어댑터 exit 0, error.txt 0, DECISION_FAILED 0. GA-4 하네스 1건은 거부 그 자체라 §7에 따로 적었습니다 | 각 judge |
| B1 / B2 / B3 | 성립 | §2, §4, §6, §10 | |

- **all_pass = true**
- 단서: GA-4의 K6 쪽 실제 상태 종단 확인(실제 hybrid 상태에서 선택 녹색 ∈ {4..7})은 **관측하지 못했습니다**. 사전 선언의 대체 조항으로 통과 처리했습니다(§7).

## 1. 관문 트리 (B3)

### GWT (관문 전용 작업 트리)
- 명령: `git -C W worktree add --detach D:/VISSIM-merge/sim3-n31-v3c3-k6gate 54d821c1…`
- 결과: HEAD = K6, `status --porcelain --ignored` 0줄 [실행]

### FRZ_K6 (K6 동결본)
- 위치: `D:/VISSIM-merge/frozen/sdmpc31_54d821c1_202610011123`
- 만든 방법: 선언 §6-1 명령을 GWT에서 실행했습니다. 로그는 `freeze_preflight.out`입니다.
- 결과
  - `FREEZE_OK sha256=db59f55b… files=10314 head=K6`
  - `PREFLIGHT_ONLY done; no VISSIM started`, exit 0 [실행]
  - preflight 런 폴더: `ga/preflight/_preflight/k6gate_preflight_20261001_112636`
- 기존 FRZ는 고치지 않았습니다.

### 트리 확인 3회
- 시점: 동결 전, 동결 후, GA 후(`tree_check_{before_freeze,after_freeze,after_ga}.json`) [실행]
- GWT와 W: changed/missing/extra 모두 0
- GWT와 FRZ_K6 표: 0/0/0. FRZ_K6를 다시 해시해도 표와 0/0/0
- FRZ_K6 대 FRZ_OLD 표의 차이 54개 = worklog 35개 ∪ `git diff --name-only 9ed2ef0 K6` 19개. **정확히 같습니다**(§2.3 마지막 항목).
- FRZ_OLD: 다시 해시해도 표와 0/0/0. `__pycache__` 119개는 원래 있던 것이고 개수 변화가 없습니다.
- R-obs 폴더 618개와 hybrid 폴더 598개 파일은 크기와 mtime이 GA 전후로 같습니다. 재생은 런 폴더에 쓰지 않았습니다.

### 실행 위치
- GA 재생은 FRZ_K6(무제어)와 GWT(SDMPC)에서만 돌렸습니다.
- W는 GA 내내 HEAD `54d821c1`, `status --ignored` 0줄이었고, 바이트가 GWT와 같았습니다(after_ga).

## 2. 하네스 재조준 (B2)

### 공통 모듈
- `ga_common.py`는 `make_ga_common.py`가 P10 `t5_common.py`(`e0d81423…`, 바뀌지 않음)에서 상수 3개만 바꿔 만듭니다.
  - `FRZ` → FRZ_K6 (`ga_common.py:11`)
  - `WT` → GWT (`:12`)
  - `NUMBA` → `ga/numba_cache` (`:19`)
  - `TOOLS`는 FRZ를 따라갑니다.
- 끝에 GA 블록을 덧붙였습니다.
  - `aim_guard`(`:184`): 체인 머리에서 시작 거부 조건을 검사합니다.
  - `provenance_record`(`:212`)
- P10 원본 4개는 고치지 않았습니다. 차이 전문은 `harness_diff_vs_t5.txt`에 있습니다.

### 체인에 더한 것 (상수 밖 변경, 선언 GA-1 문구 그대로)
- 무제어 체인은 `-Root FRZ_K6`를 명시합니다(`ga_chain_a.py:70`, `ga_chain_h.py:71`). T5-A는 `-Root` 없이 런 자체의 Root(FRZ_OLD)로 재생했습니다.
- SDMPC 체인: `WT_PS1` = FRZ_K6 사본(`ga_chain_b.py:35`), `-Root GWT`(`:141`)
- 체인 공통 추가
  - 해시 시드 지정. `unset`이면 환경에서 지웁니다.
  - 재생마다 provenance 기록
  - 상시 관문 증거 수집

### 시작 거부 검사 (6회 모두 ok)
- 체인 머리마다 한 번씩: A, H×2, B×2, G4. 각 결과는 `*/aim_guard_*.json`에 있습니다 [실행].
- 검사 내용
  - FRZ_K6 `git.head` = K6
  - GWT HEAD = K6
  - GWT status: 캐시 폴더를 빼고 0줄
  - GWT 대 FRZ_K6 표: 0/0/0

### 재생별 B2 기록 (75/75)
- `replay_run.json root` = `workspace_root` = 그 재생의 Root(FRZ_K6 또는 GWT)
- `imported_modules['src.models.state'].sha256` = `7c1f577a…`. `git cat-file --filters K6:…`와 같은 K1 판입니다.
- `inputs.adapter_py.sha256` = `028cf0cd…`(K5 판)
- FRZ_OLD나 `sim3-n31-v3c1`을 가리키는 값은 0개입니다 [실행].

## 3. N1: 옛 트리 해시 시드 A/B (진단)

- **이번 단계에서는 다시 돌리지 않았습니다.**
  - 이유: 선언상 N1은 K1 편집 전 W(`9ed2ef0`)에서만 돌립니다. 지금 W는 K6입니다. 옛 코드는 FRZ_OLD(쓰기 금지, 탄젠트 캐시를 쓸 수 없음)와 다른 작업 트리(쓰기 금지)에만 있습니다.
  - 앞 단계 실행분의 증거를 확인했습니다 [읽음].
- 실행 시각과 위치
  - 10:14–10:38, Root = W @ `9ed2ef0`
  - 앞뒤 트리 확인: FRZ_OLD 표 대비 changed 0, missing 0, extra = worklog 35
  - K1 커밋 시각은 10:40:53으로, N1 이후입니다(`git log`) [실행].
- 결과 `../n1/n1_compare.json`(`7e9e7eb0…`): 4050 wu-link 반사실에서 시드 0과 2가 아래 항목 모두 같았습니다.
  - CSV `4e1cc3ff…`
  - 목적함수 497.36952262710264 / 498.47908727527283
  - 제어 필드, 탄젠트 트레이스, 4필드
  - JSON 차이 0(시간 키, 토큰, state_json 제외)
- 해석
  - 옛 코드에서도 이 상태의 SDMPC 출력에는 해시 순서가 닿지 않았습니다.
  - 반면 T5-H(옛 코드, 무제어 4050)에서는 시드 2가 4필드를 바꿨습니다. 그래서 이 결론은 이 상태 하나에 한정됩니다 [추론].

## 4. GA-1: R-obs 61개 재생 (Root = FRZ_K6, 무제어) [실행]

### 판정
- ps1 자체 판정(`--tuning`, K2 소속 검사): 61/61 IDENTICAL, exit 0
  - 예 4050 `action_contract`: written = runner = [80,90,100,110], 쓰인 값 [110]
- 비-tuning compare: 61/61 IDENTICAL
- 로그
  - `FREEZE_VERIFIED … head=54d821c1…`: 61/61
  - `REBASE provenance root FRZ_OLD -> FRZ_K6`: 61/61
- CSV 바이트 61/61 같음. 원본의 정수 리프 37,551개가 재생에서 모두 같은 값입니다.

### 차이 분류 합계

| 분류 | 건수 | 결정당 |
|---|---|---|
| V | 427 | 7 |
| B1 provenance | 6,222 | 102 |
| 보충 1 Root 경로 | 122 | 2 |
| 새 metadata 키 | 183 | 3. 값이 선언 §2.2와 정확히 같음 |
| 4필드 | 13 | |
| **선언 밖** | **0** | |

### 4필드
- 차이가 난 결정: 2250, 3300, 3450, 4050, 4500
- 최대 ulp
  - `state_summary.off_ramp_storage_veh` 1
  - `calibrated_state_summary.off_ramp_storage_veh` 1
  - `terminal_features.ramp_vehicles` 1
  - `terminal_features.stopped_vehicles` 2(4050)
- 모두 ≤ 2입니다.
- 원본은 무작위 해시 순서로 계산됐습니다. K1의 정렬 순서와 원본 순서가 다른 상태에서만 차이가 납니다 [추론].

### B1 양성 확인 (61/61 모두 성립)
- `workspace_root` = FRZ_K6
- `numsim_repo_root` = `FRZ_K6\vendor\NumSim-mine`
- `numsim_src_sha256` = `f394c83b…`
  - `_source_tree_sha256` 방식으로 따로 다시 계산한 값과 같습니다.
  - `05a58a33…`과는 다릅니다.
- `imported_modules`
  - 키 30개가 같습니다. 경로는 모두 FRZ_K6 아래, 같은 상대 경로입니다.
  - sha는 `src.models.state` 하나만 바뀌었고, 그 값이 K1 판입니다.
- `inputs`
  - FRZ_OLD 아래에 있던 것은 정확히 선언된 15개입니다. 모두 같은 상대 경로로 옮겨졌습니다.
  - sha는 `adapter_py`만 K5 판으로 바뀌었습니다.
  - 나머지와 `exists`는 같습니다.
- `execution_fingerprint_sha256`: 재생 JSON 자신의 증거로 다시 계산한 값과 같고, 원본과는 다릅니다.
- 변하지 않은 것
  - `workspace_git_commit` = `numsim_git_commit` = ''
  - schema_version, run_id, numsim_snapshot_commit, signal_program_sha256
  - top-level 사본과 `metadata.run_provenance` 사본이 같습니다.

### 그 밖
- 재생 JSON 안의 FRZ_OLD 문자열은 결정마다 1개입니다.
  - 위치: `metadata.shared_approach.demand_profile.path`
  - 원본 그대로이고 보충 1이 허용합니다. 차이 위치도 아닙니다.
- 어댑터 wall 중앙값 31.3 s

## 5. GA-2: 해시 시드 A/B (K6) [실행]

### 무제어 4050, 4500 (Root = FRZ_K6)
- 시드 {미설정, 0, 2} 사이에서 다음이 모두 같았습니다.
  - action JSON 차이 0(V7 제외)
  - CSV
  - 4필드: **비트 동일**
  - ps1 IDENTICAL
- 4050 값: 78.69970870217519 / 179.79145106598816 / 1894.2689210945364
- 옛 코드(T5-H)에서는 시드 3이 `…517` / `…813` / `…536`을 냈습니다. K1이 이 상태의 시드 의존을 없앴습니다.

### SDMPC 900 (Root = GWT)
- 세 시드 모두 다음이 같았습니다.
  - 목적함수 `348.3666786204171` / `351.261489741853`
  - CSV `25f420d2…`
  - 제어 7, 탄젠트 트레이스
  - JSON 차이 0(SDMPC V 제외)
- raw 차이는 시드마다 50개였습니다. 46개는 시간 키나 토큰 리프이고, 4개는 state_json입니다. 하위 트리 제거 규칙 때문에만 숨겨진 차이는 0입니다(`ga2_sdmpc_raw_leaf_check.json`).
- 900_h2 앞에서 외부 재생 때문에 325 s를 기다렸습니다. 판정에는 영향이 없습니다.

## 6. GA-3: T5-B 반사실 5개 재현 (Root = GWT) [실행]

| 재생 | 목적함수 / held (기록과 repr 같음) | 탄젠트 리프 |
|---|---|---|
| 900 r1, r2 | 348.3666786204171 / 351.261489741853 | 872 |
| 2700 r1 | 504.54515375135594 / 507.3203269038361 | 880 |
| 4950 r1, r2 | 432.34345770706574 / 434.5783681328314 | 876 |

### 5/5 모두 성립
- 같은 것
  - CSV 바이트
  - 제어 7
  - 탄젠트 트레이스(시간 키 제외)
  - derived: T5-B 기록 파일과 같음(`inputs.raw_sha256` 제외), R-obs 원본 대비 compare도 ok
- 차이 분류(결정당)

| 분류 | 건수 |
|---|---|
| V | 4 |
| B1 | 104 |
| 보충 1 | 2 |
| 보충 2 | 384 |
| 새 키 | 3 |
| 4필드 이름 리프 | 0 |
| **선언 밖** | **0** |

- B1
  - `workspace_git_commit`: 기록 `5323faa4…` → 재생 K6(기대값 K6)
  - `numsim_git_commit` ''
  - imported는 state.py만 바뀌었습니다.
- 보충 2: 탄젠트 호출 2회 × 97키
  - 상대 경로 집합이 같고, 키는 모두 GWT 아래입니다.
  - sha가 바뀐 파일은 정확히 5개이고 모두 K diff 안에 있습니다: `freeway_fd.py`, `physical_ramp_branches.py`, `runtime_setup.py`, `vissim_stackelberg_adapter.py`, `state.py`.
  - 그 5개의 sha는 K6 파일 sha와 같습니다. K 코드가 실제로 계측·실행됐다는 양성 증거입니다.
- VSL
  - 쓰인 값 {110} ⊂ {80..110}
  - 블록 0 허용 [80,90,100,110]
  - RM_C10490 미터 축 [8,9,10]
- `replay_run.json root` = GWT

## 7. GA-4: RM_C10490 양성 대조

### (a) 옛 코드 쪽 기록 증거 [읽음]
- `runlog_sdmpc31_v3c1_hybrid_s31.txt:1825-1827`(`e834a4cb…`)
  - `DECISION_FAILED … no unique physical green: RM_C10490`
  - `ERROR=EXPERIMENT_DECISION_FAILED`
- `action_003000.error.txt`(`66f86486…`): `physical_ramp_branches.py:360 candidate_from_services`
- 직전 2850의 적용 녹색은 5.0입니다(`action_002850.csv:213`).

### (b) 함수 수준 재현 [실행]
- GWT에서 `test_old_table_reproduces_the_hybrid_3000s_failure_and_the_new_one_decodes`(`diagnostics/test_physical_ramp_branches.py:475-494`) PASSED
  - 옛 표 + 녹색 5 → 같은 ValueError
  - 새 표 → 디코드 {4,5,6,7}

### K6 전체 반사실 (`ga_chain_g4.py`, Root = GWT, 튜닝 = GWT 배포 config `33027258…`)
- 결과: **어댑터 exit 1**, 41.6 s
  - 메시지: `SDMPC prior price/application context mismatch`
  - 위치: `sdmpc.py:515`, `:545`의 `load_prices`에서 발생 [실행]
- 원인 [실행]
  - hybrid 2850의 `sdmpc_state.policy_sha256`은 `46f86bf8…`입니다.
  - 배포 튜닝 정책은 `428e650d…`입니다(GA-3 2700 재생과 T5-B 기록이 같은 값).
  - `sdmpc.py:511-514`의 나머지 조건(receipt 3줄, 2850 = 3000−150, csv 경로와 크기, schema, sim_sec)은 모두 성립합니다.
  - 즉 hybrid 튜닝으로 만든 직전 상태를 배포 튜닝이 받지 않은 것이고, 10490과는 무관한 거부입니다.
- 이 거부는 후보 디코드(`sdmpc.py:642/660`)보다 앞에서 일어납니다. 그래서 전체 반사실은 10490 경로에 **닿지 못했습니다**.
- 선언의 대체 조항("다른 이유로 거부하면 R-4 합성 fixture 단위 시험으로 대체")을 따랐습니다. GWT의 `ServiceNormalisationTests`에서 다음 4개가 PASSED입니다(`ga5/logs/k6gate/new.log`).
  - 위 (b)
  - `test_sdmpc_meter_axis_allowed_sets`(:529-538): 녹색 5 → [4,5,6,7], 10 → [8,9,10]
  - `test_every_anchor_decodes_every_seed_after_normalisation`(:496-512)
  - `test_recorded_green_3_is_refused_and_alinea_cannot_pick_it`(:540-): 3을 거부, ALINEA 3 → 4
- 대체 경로가 덮는 범위와 못 덮는 범위
  - `dropped = {'RM_C10490': {'3': '2'}}`는 실제 상태에서도 확인했습니다. GA-1 61건, GA-2 9건, GA-3 5건 모두 metadata 값이 정확했습니다 [실행].
  - 미터 축 시험은 `sdmpc.py:325-331`의 열거를 시험 안에서 다시 구현한 것이고, sdmpc 코드를 직접 부르지는 않습니다 [읽음].
  - **실제 hybrid 상태에서 SDMPC가 {4..7} 중 하나를 고르는 종단 관측은 없습니다.**
- 하네스 결과는 `G4/T003000/replay/`에 두었습니다(error.txt, replay_run.json 포함).
- 다른 직전 행동(예: first_sdmpc_decision)으로 다시 돌리지 않았습니다. 그렇게 하면 선언한 하네스가 바뀌기 때문입니다.

## 8. GA-5: 시험 묶음 (GWT, BELOW_NORMAL, 금지 7종 제외) [실행]

- 러너: `ga5/run_tests_gwt.sh`. 구현 단계 `run_tests.sh`에서 경로만 GWT로 바꾸고 `new` 묶음을 더했습니다.
- 기준선: `scratchpad/v3c3-k1k6/logs/base`(`9ed2ef0`)

| 묶음 | GWT (K6) | 9ed2ef0 | 실패 id |
|---|---|---|---|
| N31 unittest 16 | 194 OK (skip 3) | 190 OK | 같음(+4는 K6 시험) |
| T9 ad_smoke | 9 OK | 9 OK | 같음 |
| tools 4 | OK | OK | 같음 |
| obs150 13 | 143 OK | 143 OK | 같음 |
| repin/prepare pytest | 67 passed | 67 passed | 같음 |
| extra 3 | 7 F / 4 E / 13 passed | 같음 | 11개 id 같음 |
| diag 20 | 28 F / 37 E / 228 passed | 28 / 37 / 211 | 65개 id 같음(diff 0), +17 신규 |
| dprof | 16 passed, 2 skip | 같음 | 같음 |
| 새 시험 | hash_order 1 OK, replay_contract 8 OK, pytest 41 passed | — | 모두 통과 |

- 시험 뒤 GWT `status --ignored`는 0줄이었습니다.

## 9. 상시 관문 (§4)

- 재생 75건 모두 성립했습니다(GA-1 61, GA-2 9, GA-3 5): 어댑터 exit 0, `*.error.txt` 없음, stdout·stderr·ps1 출력에 DECISION_FAILED 없음.
  - SDMPC 재생의 ps1 exit 2는 기록이 무제어라 생기는 구성상 DIFFERENT입니다. T5-B와 같습니다.
- 이 단계에는 폐루프 런이 없습니다. 그래서 런로그 기준(`DECISIONS_FAILED`, `ERROR=`, `SKIPS`)은 해당이 없습니다.

## 10. 정리, 선언과 다른 점, 남은 것

### 정리 (B3)
- GA가 GWT에 만든 `__tangentcache__` 92개를 `ga/moved_tangentcache/`로 옮겼습니다. 목록과 sha는 `moved_tangentcache_list.csv`에 있습니다.
- 옮긴 뒤 GWT `status --ignored`는 0줄입니다.
- FRZ_K6 캐시 0. W는 손대지 않았습니다.
- 커밋과 푸시는 하지 않았습니다.

### 선언과 다른 점
1. 결과 파일 위치: 선언 §6-4는 `ga/GA_REPORT.md`였습니다. 과제 지시대로 `reports/k1k6/GA_RESULTS.md`(이 파일)에 썼습니다.
2. 판정기 `ga_judge.py`의 버그 1건을 GA-3 판정 전에 고쳤습니다.
   - 내용: 보충 2 검사에서 상대 경로를 소문자로 바꿔 K diff와 대조하던 버그
   - 영향: 재생 출력에는 영향이 없습니다. 수정 뒤 GA-2 900 결과로 미리 확인했습니다.
3. SDMPC V 규칙은 T5-B의 `strip_timing`(하위 트리 제거)을 그대로 썼습니다. 그와 별도로 리프 기준으로만 숨는 차이가 0인지도 확인했습니다(GA-2, GA-3).

### 남은 것
- GA-4 종단 확인을 원하면 새 사전 선언이 필요합니다. 예: 배포 튜닝 정책과 맞는 직전 상태, 또는 직전 sdmpc_state 없이 시작
- K7(v3c3 망 sha가 생긴 뒤)
- 푸시는 K7 관문 뒤

### 주요 파일 (`reports/k1k6/ga/`)
- 판정: `judge_ga{1,2,3,4}.json`
- 트리 확인: `tree_check_*.json`
- 체인 출력: `A/`, `H/`, `B/`, `G4/`, `ga5/`
- 동결과 preflight: `FRZ_K6.txt`, `freeze_preflight.out`
- 하네스: `ga_*.py`, `make_ga_common.py`, `harness_diff_vs_t5.txt`
