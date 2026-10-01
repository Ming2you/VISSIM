# K1–K6 독립 검증 (VERIFY)

- 작성 2026-10-01 15:20. 검증 단계는 **읽기 전용**이었습니다. 제 코드와 출력은 모두 `reports/k1k6/verify/`에 있습니다.
- 대상: K6 = `54d821c1e7140d23635f295283849d5a1197624c` (W와 GWT 모두 이 HEAD)
- 입력 문서
  - `K1K6_IMPLEMENT.md`
  - `GA_RESULTS.md`
  - `GA_PREDECLARATION.md` `34cc48ee…`, 보충 1 `607a2eb5…`, 보충 2 `c96b8a02…` (sha 다시 계산해서 일치 [실행])
  - 계획 `REPIN_V3C2_PLAN.md` `d4b70c02…` [실행], 검토 `REPIN_V3C2_PLAN_REVIEW.md`
- 표기: [실행] 직접 돌려 확인 · [읽음] 코드·파일에서 확인 · [추론] 시험하지 않은 판단
- 제 재생은 한 번에 하나씩, BELOW_NORMAL로 돌렸습니다. 순서: GA-1 2회 → GA-4 2회. VISSIM은 쓰지 않았습니다.

## 0. 결론

| 항목 | 판정 | 근거 |
|---|---|---|
| K1–K6 diff 검토 | **통과**. 막는 결함은 없음. 비차단 주의 3건(P2, P3, P7) | §2 |
| GA-1 재실행(4050, Root = GWT / FRZ_K6) | **통과** | §3 |
| GA-1 61개 독립 재판정 | **61/61**. 분류 합계가 GA와 완전히 같음 | §3 |
| GA-2 / GA-3 파일 재판정 | **통과**. 선언 밖 차이 0 | §4 |
| GA-4 선언 경로 재실행 | GA와 **같은 거부**를 재현. 원인이 10490과 무관하다는 것도 확인 → 대체 조항 적용 요건 성립 | §5.1 |
| GA-4 종단 관측(탐색, **사전 선언 아님**) | exit 0. `dropped`가 기록됐고, 블록 0 허용집합 [4,5,6,7], 선택 녹색 6 | §5.2 |
| GA-5 새 시험 재실행 | 통과 (29 + 8 + 41) | §6 |
| provenance가 K6를 가리키는가 (B1/B2) | **예**. 예외 1건: 데이터 경로 하나가 원본 그대로 남아 있음(P4, 보충 1이 허용) | §3, §4 |
| B3 (GA를 두 번째 작업 트리에서 실행) | 성립. GA 재생 76건의 Root는 FRZ_K6 67건, GWT 9건이고, W에서 돈 것은 0건 | §1 |
| 판정이 사전 선언을 따랐는가 | **따랐음**. 다만 GA-4는 선언된 대체 조항으로 통과했고, 기계 판정 파일과 보고서 표현이 어긋남(P1) | §7 |

**종합**: GA_RESULTS의 all_pass는 재현됩니다. K7로 넘어가는 것을 막을 문제는 찾지 못했습니다.

---

## 1. 트리와 커밋 상태 [실행]

- 트리 검사 `verify/v_tree.py`(자체 해시 코드)를 제 재생 전(`tree_before.json`)과 후(`tree_after.json`)에 돌렸습니다.
  - GWT HEAD = K6. `git status --porcelain --ignored` 0줄
  - GWT 바이트 대 FRZ_K6 `FREEZE.json` 표: 0/0/0
  - FRZ_K6 실제 바이트 대 자기 표: 0/0/0
  - FRZ_K6 `git.head` = K6
  - FRZ_OLD 표 대 FRZ_K6 표의 차이 54개 = `git diff --name-only 5323faa 9ed2ef0`(35) ∪ `9ed2ef0..K6`(19). **정확히 같습니다**(선언 §2.3 마지막 항목).
- W HEAD = K6입니다. 아직 K7 편집이 없습니다.
- 푸시: 브랜치에 upstream이 없고, `git branch -r --contains 54d821c`는 0줄입니다 → 푸시하지 않았습니다.
- 커밋 6개(`2d70e4a`, `779037b`, `de5ff5f`, `8959efa`, `07a2f7a`, `54d821c`)
  - 작성자와 커미터: 모두 `Ming2you <alsrjsrb1915@snu.ac.kr>`
  - 메시지 끝: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
- K diff는 19파일입니다. EOL 피해는 없습니다(`runtime_setup.py`는 base와 K6 모두 전 줄 CRLF).
- GA 재생 Root 집계(`verify/v_roots.py`, `replay_run.json` 76개)
  - A 61, H 6 → FRZ_K6
  - B 8, G4 1 → GWT
  - W(편집 트리)에서 돈 재생은 0건 → B3 성립
- 제 SDMPC 탐색 실행이 GWT에 만든 `__tangentcache__` 88개는 `verify/moved_tangentcache/`로 옮겼습니다(목록과 sha: `verify/moved_tangentcache_list.csv`). 옮긴 뒤 GWT `status --ignored`는 0줄입니다.

## 2. 커밋별 diff 검토 [읽음]

| K | 확인한 것 | 결과 |
|---|---|---|
| K1 | 정렬 범위 | `state.py:1308` 한 줄만 `sorted(set(...), key=str)`입니다. 바로 위 urban 합(`off_ramp_storage_links = set(...)`)은 소속 검사에만 쓰므로 순서 무관입니다. H-2(다른 set 순회)는 손대지 않았습니다(계획대로) |
| K2 | `action_contract` 의미 | `make_replay_state_v2.py:240`, `:254`: 소속은 `set(speeds) <= set(written)`, 그리고 written == runner. 새 검사는 키워드 전용 `vsl_contract`이고, `compare(out_dir, vsl_expected)`·`action_contract(csv, vsl_expected)` 위치 인자 의미는 그대로입니다(N14). 의미 변화: 예전 `--tuning`은 "전부 110"을 요구했지만, 지금은 소속만 봅니다. 의도된 P-1입니다 |
| K3 | 가장 낮은 허용 녹색 규칙 | `physical_ramp_branches.py:36-86`. 서비스 값이 정확히 같은 것끼리 묶습니다(디코드 `:424`의 `value==rate`와 같은 기준). 허용 = 0 또는 ≥ min, `min(..., key=int)`. 순서를 보존하는 필터, `str` 키, 유일한 표는 같은 객체. 최대 서비스 녹색이 탈락하면 거부합니다(`:75`) |
| K3 | 적용 위치 | configure 수송표(`:140`)와 결정마다 도는 lane plant 설치 경로(`lane_plant_runtime.py:512`), 두 곳입니다. 설치 경로의 거부(N3)는 같은 helper가 맡습니다. 측정표 식은 `n*3600/10`로 원문과 같은 연산 순서입니다 |
| K4 | 키 없음 비트 동일 | `freeway_fd.py:141-149`: 키가 없으면 `b = command / maximum` 원문 그대로입니다. 더해진 것은 dict 소속 검사뿐이고 Dual 연산·비교는 없습니다. `physical_lane_groups`는 키가 없으면 `(100, 120)` 호출 그대로입니다. 3차식 단조 검사(도함수 2차식의 양 끝과 꼭짓점)는 식이 맞습니다 |
| K5 | 쓰기 사상 | `vissim_stackelberg_adapter.py:12656`: 키가 없으면 `parse`가 바로 None을 내고, nearest + 120 경로 그대로입니다. 사상이 있으면 1e-9 엄격, 120 확장 없음(N5). 가족 검사는 생성기·launch_plan·런타임(`runtime_setup.py:250`, v2만) 세 곳에 있습니다 |
| K6 | 설치 검사 | `lane_plant_runtime.py:78-89`, 호출 `:124`(성분 생성 직후). 양쪽 부재 = 같음. `physical_cell_fd`·`state_response`는 거부합니다. metadata 키는 `initialize`가 반환합니다 |

- 비차단 주의 3건(자세한 내용은 §8): **P2** K3의 선언되지 않은 거부 1종, **P3** 시간 정규식의 과포괄, **P7** `state_response` 거부 근거 불일치

## 3. GA-1 재실행과 61개 재판정 [실행]

### 재실행
- 스크립트: `verify/v_ga1.py`
  - 도구와 Root를 같은 K6 트리에서 가져옵니다.
  - 순서: prepare → `replay_decision_n31.ps1 -Root` → ps1의 `compare --tuning` → `--tuning` 없는 compare
- 대상: R-obs 4050. 4필드 ulp가 가장 큰 결정입니다.

| Root | ps1 | `--tuning` 판정 | 비-tuning 판정 | 선언 밖 | 4필드 ulp |
|---|---|---|---|---|---|
| GWT | exit 0, `ROOT_NOT_FROZEN`, `REBASE FRZ_OLD -> GWT` | IDENTICAL | IDENTICAL | 0 | 1/1/1/2 |
| FRZ_K6 | exit 0, `FREEZE_VERIFIED … head=54d821c1…`, `REBASE FRZ_OLD -> FRZ_K6` | IDENTICAL | IDENTICAL | 0 | 1/1/1/2 |

### 판정기
- `verify/v_judge_ga1.py`. GA 판정기와 코드를 공유하지 않습니다. 리프 단위로 비교하고 하위 트리를 지우지 않습니다.
- 분류(4050, Root = GWT)
  - V 7, B1 104, 보충 1 2, 새 키 3(값이 정확히 같음), 4필드 4, **선언 밖 0**
  - Root = FRZ_K6일 때 B1은 102입니다. `workspace_git_commit`이 ''로 그대로이기 때문입니다.
- B1/B2 양성 확인(직접 다시 계산)
  - `workspace_root` = 그 Root
  - `numsim_repo_root` = `<Root>\vendor\NumSim-mine`
  - `numsim_src_sha256` = 다시 계산한 값 `f394c83b…`, 원본 `05a58a33…`과 다름
  - `imported_modules`: 30키가 같고, 경로는 모두 Root 아래입니다. 각 sha = 디스크 파일 sha이고, 바뀐 것은 `src.models.state` 하나 = `git cat-file --filters K6:` sha `7c1f577a…`(K1 판)
  - `inputs`: FRZ_OLD 아래 15개가 그대로 옮겨졌습니다. `adapter_py` = `028cf0cd…`(K5 판). 나머지 sha와 `exists`는 같습니다.
  - `execution_fingerprint_sha256`: 재생 자신의 증거로 다시 계산한 값과 같고, 원본과는 다릅니다.
  - `workspace_git_commit`: GWT에서는 K6, FRZ_K6에서는 ''(보충 1의 정정과 같음)
  - top-level 사본 = metadata 사본
- K1 결정성: 4필드 값 `78.69970870217519 / 179.79145106598816 / 1894.2689210945364`가 GA의 재생, GA-2의 세 시드와 **비트 단위로 같습니다**.
- 같은 FRZ_K6 Root끼리 비교: 제 재생과 GA 재생의 차이는 V 7개뿐입니다.

### 61개 재판정
- `verify/v_judge_all_ga1.py`(같은 판정기)를 `ga/A`의 61개에 돌렸습니다 → **61/61 통과**
- 분류 합계 V 427 / B1 6,222 / 보충 1 122 / 새 키 183 / 4필드 13 / 선언 밖 0. GA `judge_ga1.json`과 **숫자가 모두 같습니다**.
- 4필드 최대 ulp 1/1/1/2

## 4. GA-2, GA-3 파일 재판정 [실행] (`verify/v_files.py`, `files_ga2_ga3.json`)

### GA-2
- 4050, 4500(FRZ_K6), 900(GWT) 각각 시드 {미설정, 0, 2}를 비교했습니다.
- 휘발이 아닌 리프 차이 0, CSV 같음, 4필드 비트 동일. 900은 목적함수 repr `348.3666786204171 / 351.261489741853`도 같습니다.

### GA-3
- 5건(900 r1/r2, 2700, 4950 r1/r2)을 T5-B 기록과 비교했습니다.
- 같은 것: CSV 바이트, 목적함수 repr
- 선언 밖 0. B1의 Root는 GWT, `workspace_git_commit`은 K6, imported는 모두 GWT 아래
- 보충 2(`transformed_source_sha256`)
  - 상대 경로 집합이 같습니다.
  - sha가 바뀐 파일은 정확히 5개 = K6 blob sha: `freeway_fd`, `physical_ramp_branches`, `runtime_setup`, adapter, `state.py`
- RM_C10490 축(블록 0/1/2) = [8,9,10] / [6..10] / [4..10]. 옛 기록과 같고, 3은 없습니다.
- VSL 블록 0 = [80,90,100,110]

## 5. GA-4 재실행

### 5.1 선언 경로 재실행 [실행] (`verify/v_ga4.py declared`)
- 설정
  - Root = GWT, wu-link
  - 상태: hybrid `state_003000`(GWT prepare)
  - 직전 행동: hybrid 런 폴더의 `action_002850`
  - 튜닝: GWT 배포판 `config_n31_v2.json` `33027258…`
- 결과: **exit 1**, 40.7 s
  - 메시지 `SDMPC prior price/application context mismatch`
  - 위치 `sdmpc.py:545` → `load_prices`
  - GA와 같습니다.
- 원인을 따로 확인했습니다 [실행·읽음].
  - `.applied` 3줄: `2850` / csv 경로 / `28333` = 실제 csv 크기
  - `schema` = `sdmpc-proxlinear/v1` = `sdmpc.SCHEMA`
  - `sim_sec` 2850 = 3000 − 150
  - 즉 `sdmpc.py:514`의 조건 가운데 `policy_sha256`만 다릅니다: hybrid `46f86bf8…` ≠ 배포 `428e650d…`
  - 이 거부는 10490 디코드보다 앞에서 일어납니다 → 선언의 대체 조항("다른 이유로 거부") 요건이 성립합니다.
- [추론] 같은 `load_prices`는 K2 트리에도 있습니다. 그래서 계획 GA-4의 "K2 트리 재현"을 배포 튜닝으로 돌렸다면, 10490 오류가 아니라 같은 정책 토큰 오류로 죽었을 것입니다. 즉 선언된 전체 반사실은 **양쪽 모두** 10490 경로에 닿을 수 없는 설계였습니다(P1).

### 5.2 종단 관측 — 탐색 실행, 사전 선언 아님, 관문 판정에 쓰지 않음 [실행] (`verify/v_ga4.py stripped`)
- 5.1과 같은 설정입니다. 다른 점은 직전 행동 사본 하나뿐입니다.
  - `metadata.sdmpc_state`를 지웠습니다 → `load_prices`가 `first_sdmpc_decision`으로 시작하고, 사전 가격은 0입니다.
  - csv와 `state_0024..2850`은 바이트 사본입니다.
  - 적용 녹색 RM_C10490 = 5는 그대로입니다.
- 결과: **exit 0**, 767 s(벽시계 제한 꺼짐), error.txt 없음, DECISION_FAILED 없음

| 항목 | 값 | 선언 GA-4(K6 쪽) 기대 |
|---|---|---|
| `lane_ramp_head_service_normalisation.dropped` | `{'RM_C10490': {'3': '2'}}` | 같음 ✔ |
| 미터 축 `allowed`, RM_C10490, 블록 0 | [4, 5, 6, 7] | [4, 5, 6, 7] ✔ |
| 블록 1 / 블록 2 | [2,4,…,9] / [0,2,4,…,10] (3 없음) | — |
| 선택 녹색 RM_C10490 (CSV, diagnostics) | 6.0 (842.4 veh/h) | ∈ {4..7} ✔ |
| `physical_ramp_service_normalisation` / `lane_plant_install_check` | 선언값과 같음 | ✔ |
| provenance | Root GWT, git K6, `state.py` `7c1f577a…`, adapter `028cf0cd…`, imported 모두 GWT 아래 | ✔ |

- 덧붙여 이 결정은 **처음으로 110 미만 VSL을 실제로 썼습니다**(FW_E seg10–14 = 100).
  - K2 소속 계약: ok (100 ∈ {80,90,100,110}, 쓰는 집합 = 러너)
  - K2 이전 의미(`vsl_expected = 110`): ok = false
  - 파일: `verify/g4_stripped_k2_contract.json`
  - K2가 고치려던 결함(P-1)을 실제 SDMPC 결정에서 확인한 셈입니다.
- 한계 [추론]
  - 사전 가격이 0이라 hybrid 런의 실제 3000 s 결정과 같은 결정은 아닙니다.
  - 옛 코드 쪽 같은 입력 재현은 돌리지 않았습니다. 탄젠트 캐시를 Root 아래에 써야 하는데, 옛 코드는 쓰기 금지 트리(FRZ_OLD, sim3-n31-v3c1)에만 있기 때문입니다.
  - 옛 코드 쪽은 기록 증거(runlog `:1825-1827` [읽음])와 함수 수준 시험(§6)으로 남습니다.

## 6. GA-5와 새 시험 [실행]

- `verify/v_tests.sh`(GWT, BELOW_NORMAL, 바이트코드·캐시 쓰기 없음)로 다시 돌렸습니다. 모두 통과했고, 실행 뒤 GWT는 깨끗합니다.
  - `test_n31_hash_order` + `test_n31_plant_load`(K6 시험 포함): 29 OK
  - `test_tools_replay_contract`: 8 OK
  - pytest(`test_vsl_command_distribution`, `ServiceNormalisationTests`, `test_literature_vsl_fd`): 41 passed
- GA-5 로그: `ga5/logs/k6gate/*.ids`와 `*.base.ids`의 실패 id 집합이 묶음마다 같습니다.
  - diag 65 = 65
  - extra는 outcome 파일 기준으로 같음
  - diag와 extra의 base는 구현 단계 scratchpad 기준선 파일과도 같습니다.

## 7. 판정이 사전 선언을 따랐는가

| 관문 | 선언 조건 | 판정 |
|---|---|---|
| GA-1 | 61/61 IDENTICAL(두 compare), 선언 밖 0, 4필드 ≤ 2 ulp, CSV·정수 리프, B1 양성, 상시 관문 | 따름(§3, 독립 재판정 61/61) |
| GA-2 | 세 시드의 JSON(V 제외)·CSV·목적함수·탄젠트·4필드 비트 동일 | 따름(§4) |
| GA-3 | T5-B와 CSV·repr·제어 7·탄젠트·derived 같음, 허용 diff 목록만, VSL 검사, root = GWT | 따름(§4). 시간 정규식 주의 P3 |
| GA-4 | K6 전체 반사실 → 다른 이유로 거부되면 R-4 fixture로 대체하고 기록 | 대체 조항 적용 요건이 성립하고, 기록도 있음. 다만 `judge_ga4.json`은 `"pass": false`이고, "대체 통과"는 GA_RESULTS 문장에만 있음(P1). 대체 시험의 축 시험은 `sdmpc.py:325-331`을 다시 구현한 것. §5.2 탐색 실행이 종단 공백을 메움(관문 아님) |
| GA-5 | 실패 id 집합 = 기준선, 새 시험 통과 | 따름(§6) |
| N1 | K1 전 W에서 시드 0 대 2 | 따름. N1 after-check 10:39:09 < K1 커밋 10:40:53. 결과는 완전히 같음 |
| 보충 1·2 | GA 전에 고정 | 시각상 GA 전입니다(보충 2 11:09 < FRZ_K6 11:26 < GA-1 11:31). 다만 K6 코드 smoke를 **본 뒤** 쓴 것이라 코드 기준으로는 사후입니다(P5). 판정 필드는 넓히지 않았고, 경로형 필드에 양성 조건을 둔 것뿐입니다 |

## 8. 문제와 주의 (중요도 순, 막는 것 없음)

- **P1. GA-4는 사전 선언 설계상 양성 대조가 불가능했습니다.**
  - 배포 튜닝에서는 `load_prices`의 정책 토큰 검사(`sdmpc.py:514`)가 디코드보다 먼저 거부합니다. 이것은 K2·K6 트리 모두 같습니다 [실행·추론].
  - 그래서 판정은 대체 조항(단위 시험)에 기대고, `judge_ga4.json`은 `"pass": false`인 채 남아 있습니다.
  - 권고: GA_RESULTS의 "대체 통과"를 기계 판정 파일에도 남기기. 종단 증거로 §5.2를 인용하기(관문이 아니라 증거).
  - 이후 비슷한 양성 대조는 직전 `sdmpc_state`의 정책 토큰과 배포 튜닝을 맞추는 것을 사전 선언에 넣어야 합니다.
- **P2. K3에 선언되지 않은 거부가 하나 있습니다.**
  - `normalise_service_table`은 `min_green_sec ≤ 0`이면 **유일한 표에서도** 거부합니다(`physical_ramp_branches.py:57`).
  - 예전 configure는 이 값을 받았습니다.
  - 이 트리에서 `urban.physical_ramp_branches`를 켠 튜닝 66개는 모두 2.0이라 지금은 효과가 없습니다 [실행]. 0.0인 `tuning_ver2*.json`은 물리 램프를 켜지 않습니다.
  - 선언 §1 K3의 거부 목록에 없는 동작입니다. 문서화하거나, 유일한 표에서는 검사를 건너뛰기를 권합니다.
- **P3. 선언 §2.1의 SDMPC 시간 정규식이 너무 넓습니다.**
  - `time_s`가 `transformed_source_sha256`의 파일 경로 키 `runtime_setup.py`에 걸립니다.
  - 하위 트리 제거 방식이면 이 키 4개가 V로 숨습니다.
  - GA는 보충 2 검사를 따로 해서 잡았고, 제 리프 판정에서도 `runtime_setup.py` sha = K6 판이 확인됐습니다. 그래서 결과에는 영향이 없습니다.
  - K7 선언(GB-7·GB-9)에서는 V를 리프 키 이름으로만 적용하거나 경로 키를 제외하기를 권합니다.
- **P4. 데이터 경로 하나가 FRZ_OLD를 가리킵니다.**
  - 모든 K6 재생에서 `metadata.shared_approach.demand_profile.path`가 FRZ_OLD의 `profile.csv`를 가리킵니다(보충 1이 허용).
  - 내용 sha `7b23853c…`는 K6 트리 파일과 같습니다 [실행].
  - "provenance가 모두 K6"에 대한 유일한 예외이고, 데이터 파일입니다.
- **P5. 보충 1·2는 K6 smoke 결과를 본 뒤 쓴 것입니다.** 경로형 필드만 더했고 양성 조건이 붙어 있어 위험은 낮습니다.
- **P6. K2·K4·K5의 활성 경로는 GA 재생 어디에서도 실행되지 않았습니다.**
  - GA 재생은 모두 키가 없고 VSL이 전부 110입니다.
  - K2만 §5.2에서 실제 결정으로 확인했습니다.
  - K4(`speed_scale`)와 K5(단일값 사상, 가족 검사의 거부 쪽)는 단위 시험뿐입니다. GB-8·GB-9·GB-10에서 확인해야 합니다.
- **P7. `state_response` 거부의 근거 문장이 사실과 다릅니다.**
  - 계획의 근거 "설치기 없음"은 `state_response`에서는 틀립니다(`freeway_fd.py:393 configure_state_response`).
  - 거부 결정 자체는 계획대로입니다. 구현자도 이미 보고했습니다.
- **P8. `test_n31_hash_order.py`만 CRLF로 커밋됐습니다**(`-text`). 기능에는 영향이 없습니다.

## 9. 파일 (`reports/k1k6/verify/`)

| 구분 | 파일 |
|---|---|
| 공용 / 트리 | `v_common.py`, `v_tree.py` → `tree_before.json`, `tree_after.json`; `v_roots.py` |
| GA-1 | `v_ga1.py` → `ga1_gwt/`, `ga1_frz/`; `v_judge_ga1.py` → `judge_ga1_{gwt,frz}_T004050.json`; `v_judge_all_ga1.py` → `judge_ga1_all61.json`, `gaA_judged/` |
| GA-2·3 | `v_files.py` → `files_ga2_ga3.json` |
| GA-4 | `v_ga4.py` → `g4_declared/`, `g4_stripped/`, `g4_stripped_summary.json`, `g4_stripped_k2_contract.json` |
| 시험 | `v_tests.sh` → `tests/*.log` |
| 캐시 | `moved_tangentcache/`, `moved_tangentcache_list.csv` |
