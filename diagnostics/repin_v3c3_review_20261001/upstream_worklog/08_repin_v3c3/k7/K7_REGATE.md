# K7 오프라인 관문 재실행 (수정 선언 1 반영)

- 작성 2026-10-01 18:2x KST. 판정 대상 K7 = **`6c4c740009f7ad9c6c0c275f8715839614ec6838`**입니다. W 로컬 커밋이고, `99dc641` 위에 수정 커밋 2개(`91efffc` O-3, `6c4c740` O-7)가 있습니다. 푸시하지 않았습니다(원격 추적 브랜치·upstream 없음) [실행].
- 판정 기준
  - 사전 선언 `K7_GB_J1_PREDECLARATION.md`: sha256 `fad31d70…`, sidecar와 같음
  - 수정 선언 `K7_AMENDMENT_1.md`: sha256 `1b1d3955…`, sidecar와 같음 [실행, 시작 전과 끝난 뒤 두 번]
  - 바뀐 판정은 수정 선언 §1.4(DA-2 `unsignalized_turns`와 하류)와 §2.2(O-5 조건 4)뿐입니다. 나머지 O 기준은 사전 선언 그대로입니다.
- **관문 트리**: GWT7 `D:/VISSIM-merge/sim3-n31-v3c3-k7gate`를 `git checkout --detach 6c4c740…`로 옮겼습니다(18:05:47) [실행].
  - 옮기기 전과 후 모두 `status --porcelain --ignored`는 0줄이었습니다.
  - 바뀐 9파일은 GWT7 작업본, `git cat-file --filters HEAD:<f>`, W 작업본의 sha가 셋 다 같습니다.
- **증거**: `D:/VISSIM_runs/20261001_v3c3/reports/k7/regate/`. 아래 상대 경로는 이 폴더 기준입니다.
  - 하네스는 첫 관문(`gates/`)의 것을 복사했고, 경로와 K7 상수만 바꿨습니다. 다르게 고친 곳은 따로 적었습니다.
  - `gates/`, `fix/`, 사전 선언, 수정 선언은 고치지 않았습니다. `K7_FIX.md`(18:02) 뒤로 그 아래에서 바뀐 파일은 0개입니다 [실행].
- **실행 환경**
  - 모든 Python은 BELOW_NORMAL(`bn.py`, 되읽기 0x4000), `-B`, `PYTHONDONTWRITEBYTECODE=1`로 돌렸습니다.
  - numba 캐시는 `regate/numba_cache`와 `regate/o5/numba_cache`에 두었습니다.
  - W에서는 관문을 돌리지 않았습니다. git 읽기(`log`, `rev-parse`, `status`, `branch -r`)만 했습니다.
  - VISSIM은 시작하지도 종료하지도 않았습니다. 금지 시험 7종은 돌리지 않았습니다. 커밋·푸시·동결도 하지 않았습니다. s37/59/61/67 결과는 열지 않았습니다.
- 표기: **[실행]** 직접 돌려 확인 · **[읽음]** 파일·코드에서 확인 · **[추론]** 시험하지 않은 판단. 코드 줄 번호는 `6c4c740` 기준입니다. 사전 선언 줄은 `PREDECL:<줄>`로 적습니다.

## 0. 판정표

| 관문 | 판정 | 핵심 근거 | 증거 |
|---|---|---|---|
| O-0 전제·트리 규칙 | **통과** (s53 보류는 계속) | 새 커밋 2개 모두 작성자·커미터가 Ming2you/alsrjsrb1915@snu.ac.kr이고, 끝 줄이 `Co-Authored-By`. 원격 브랜치 없음. v3c3 s53 런은 이제 `completed=true`(§1) | §1 |
| O-1 시험 9묶음 | **통과** | 실패 id 집합이 K6과 같음(diag 65, extra 11, 나머지 0), 첫 관문과도 같음. n31 **200 OK**(skip 3). 새 시험·고친 시험 3개 통과. T9 통과 | `o1/logs/k7gate/` |
| O-2 생성기·도구 | **통과** | 20개 명령 모두 exit 0. 후보 config `4e85cfd6`/`c60bde7c`, 무신호 회전 `43247697`(선언 §1.4 기대값). 나머지 sha는 1차와 같음 | `o2/o2.log` |
| O-3 경로 | **통과** | 98/98(A 18, M 67, R 13). 항목 집합이 1차와 같음. `99dc641..6c4c740`은 9경로 | `o3/o3_paths.json`, `o3/fix_diff_99dc641_6c4c740.txt` |
| O-3 내용 | **통과** (구속 실패 0) | DA-2 `unsignalized_turns`가 수정 기준 (a)–(g) 통과. (h)는 O-2·O-1에서 통과. 하류 기대값 통과. 나머지 행은 1차와 같이 통과. RA-1 재추출 15파일이 eo와 바이트 같음 | `o3/o3_content.json`, `o3/ra1/` |
| O-4 VSL 가족 | **통과** (다시 돌림) | (a)–(e) 통과. 결과 JSON은 1차와 경로 밖 차이 0 | `o4/o4_result.json` |
| O-5 L2 all-110 (FRZ_K6) | **통과 (수정 기준 §2.2)** | 조건 1–3, 5 통과. 조건 4의 구속 항목 1–5 통과. 항목 6(연산 수 n × d1 등식)은 보고만 하고, 편차는 1차와 같음. 결과는 1차와 벽시계·경로 밖에서 비트 동일 | `o5/out/o5_judgement.json` |
| O-6 110 미만 쓰기 | **통과** (다시 돌림) | P1–P5, N1–N6 통과. CSV 12개가 1차와 바이트 같음 | `o6/o6_result.json` |
| O-7 문서·이월 | **통과** | §5 grep 표 9행 모두 파일·줄 수와 사유가 있음. 이 단계에서 따로 잰 값과 9/9 같음 | `o7/o7_check.json` |
| O-8 트리 위생 | **통과** | W·GWT7은 0줄. GWT6은 전후 0줄이고 HEAD·status·최신 mtime이 같음. 다른 트리 5개, `frozen/*` 28개, FRZ_K6·FRZ_OLD 모두 불변 | `o8_before.json`, `o8_after.json` |

- **all_pass = true** (수정 선언 1의 기준으로).
- **단서 1, O-5 결정 주체.** O-5의 통과는 수정 선언 §2.2의 새 조건 4에 기댑니다. 수정 선언 §0은 이 사후 결정의 주체(사용자인지)를 "메인 세션이 확인해 적어야 함"으로 남겼습니다. 이 단계는 그것을 확인할 수 없습니다.
  - 옛 조건 4(`PREDECL:160-163`의 등식)로 판정하면 1차와 같은 수치로 여전히 실패합니다(§6).
  - 푸시 전에 메인 세션이 주체를 기록해야 합니다.
- **단서 2, s53 보류(O-0).** v3c3 s53 런은 끝났습니다(`run.json` completed true, exit 0, 17:38:32). 그래서 `PREDECL:65`의 사후 확인 시점이 왔습니다.
  - 이 단계는 그중 바이트 절반만 참고로 확인했습니다. v3c3 s53 재추출의 boundaries/flows/cells 3파일이 대체 입력(v3c2 s53)과 **바이트 같습니다** [실행, §1].
  - GB-1 s53 판정은 메인 세션의 일이고, 하지 않았습니다.

### 범위: O-4·O-6도 다시 돌린 이유

- 과제 지시는 O-1, O-2, O-3, O-5, O-7, O-8을 다시 돌리고, 나머지는 영향이 없음을 확인하라는 것이었습니다.
- 그런데 사전 선언 O-0(`PREDECL:56`)과 수정 선언 §5는 수정 커밋이 생기면 **O-1…O-8을 새 HEAD에서 처음부터 다시** 돌리라고 정합니다. 그리고 O-4(a)는 바뀐 후보 튜닝 두 벌을 직접 읽습니다.
- 그래서 O-4와 O-6도 다시 돌렸습니다(합쳐서 36초). "영향 없음"이라는 논증에 기대는 관문은 없습니다.
- 영향 범위 확인도 함께 남깁니다 [실행 `git diff --name-status 99dc641 6c4c740`]. 바뀐 9경로는 `K7_FIX.md` §2.1 표와 O-7 커밋의 목록과 정확히 같습니다.
  - 수정 선언이 직접 이름을 댄 것(6개)
    - `scripts/derive_unsignalized_turns.py`, `urban/unsignalized_turns_v3c3_20261001.json`, `tests/test_n31_urban_batch1.py`(§1.3)
    - 후보 config 두 벌(§1.4)
    - `REPIN_V3C3_REPORT.md`(§3)
  - §1.4의 sha 변경이 강제한 것(3개)
    - `make_config_n31.py`: `URBAN_B1_UNSIGNALIZED_SHA256` `:162`, 유도 주석 `:128-131`
    - `CONTRACT.md:723`, `PLANT_PORTING_GUIDE.md:110,:113`: 현재 sha 문구
  - 9경로 모두 98경로 합집합 안에 있습니다.
- O-6 입력(배포 튜닝 `319d07aa`, 러너 VBS `8c753c08`, lane_native `37c5021f`, mapping)과 O-5 입력(FRZ_K6, R-obs1, K7 reference FW_E)은 `99dc641`과 바이트 같습니다.

## 1. O-0 전제와 트리 규칙 [실행·읽음]

- 새 커밋 두 개는 모두 작성자·커미터가 `Ming2you <alsrjsrb1915@snu.ac.kr>`이고, 메시지 끝 줄이 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`입니다.
  - `91efffcf…`: O-3 수정
  - `6c4c7400…`: O-7 수정
  - `--renormalize` 사용 여부는 사후에 직접 확인할 수 없습니다(1차와 같음).
  - 바뀐 9파일의 작업본이 filtered blob과 같아 줄끝 이상은 없습니다.
- 푸시: `refs/remotes/origin/claude/repin-v3c3*` 없음, upstream 없음 → 푸시 전입니다.
- **s53 상태**
  - `D:/VISSIM_runs/20261001_v3c3/s53_v3c3nc/run/run.json`: completed true, exit_code 0, 16:19:58 → 17:38:32
  - O-0의 대체(v3c2 s53)는 영수증·QUALIFICATION·보고서 기록과 함께 그대로입니다(O-3 RA-1 행이 `substitute` 문구를 다시 확인함).
  - **참고 (판정 아님)**: `s53_ref/`
    - 끝난 v3c3 s53 런을 RA-1 영수증 인자(phase 0.1, geometry_profile, branch_guard)로 GWT7에서 추출했습니다(18:23–18:24). 출력은 GWT7 밖 `tmp/s53_v3c3_reextract`로 옮겼습니다.
    - `boundaries_30s.csv` `ce59ac19…`, `flows_30s.csv` `8cf2a917…`, `cells_30s.csv` `19a04652…`가 v3c2 eo s53, 그리고 이번 RA-1 재추출 s53과 바이트 같습니다(`s53_ref/s53_byte_check.json`).
    - checks는 18538입니다.
    - **GB-1 s53 PASS 판정은 하지 않았습니다.** `gb1_identity.py judge`는 메인 세션의 일입니다.

## 2. O-1 시험 묶음 [실행] (`o1/run_tests_gwt7.sh`, 18:07:26–18:12:22)

- 1차 러너에서 env와 로그 경로만 regate로 바꿨습니다. 실패 id는 `o1/ids2.py`로 뽑았고, extra는 `--headers`(K6 `extra.outcome`과 같은 방식)로 뽑았습니다.
- 기준은 `reports/k1k6/ga/ga5/logs/k6gate/*.ids`, `extra.outcome`입니다.

| 묶음 | 결과 | K6 대비 | 1차(99dc641) 대비 |
|---|---|---|---|
| n31 | 200 OK (skip 3) | 같음 (0) | id 같음. 시험 수 198 → 200 |
| t9 | 9 OK | 같음 (0) | 같음 |
| tools | 60 OK | 같음 (0) | 같음 |
| obs | 143 OK | 같음 (0) | 같음 |
| pyt | 73 passed | 같음 (0) | 같음 |
| extra | 7 failed / 4 errors / 13 passed | 11 id 같음 | 같음 |
| diag | 28 failed / 37 errors / 228 passed / 3 skipped | 65 id 같음 | 같음 |
| dprof | 16 passed, 2 skipped | 같음 (0) | 같음 |
| new | 1 OK, 8 OK, 41 passed | 같음 (0) | 같음 |

- **조건 1**: K7 실패 ⊆ K6 실패. 새 실패 0, 개명은 1차와 같은 5건입니다.
- **조건 2**: K6 실패 → K7 통과로 바뀐 것 0입니다.
- **조건 3**
  - 1차의 새 시험 10개(N8 열거, C-10, V-11 `VslFamilyTests` 3개, V-10 `test_reference_law_is_l2`, N11)가 모두 통과입니다.
  - 수정 시험도 통과입니다(`test_n31_urban_batch1.UnsignalizedTurnTests`)
    - `test_strict_rule_excludes_downstream_heads_and_unvalidated`(23개와 초과 1건 고정)
    - `test_membership_is_pinned_to_the_v3c1_list`
    - `test_derivation_refuses_another_membership`
  - skip 3개는 1차와 같습니다: `test_missing_owner_inputs_are_listed`, `PortProfileTests.test_regenerates_bytes`, `test_g1_frame`.
  - N11 생성일 `'2026-10-01'`은 수정 커밋의 import 추가로 줄이 밀려, 지금 `test_n31_urban_batch1.py:62`에 있습니다(1차 :60, 선언 :59). 내용은 같습니다 [실행].
- **조건 4 (T9)**: `test_vsl_below_max_equals_central_fd`가 통과합니다. h 0.0625, 상대 1e-4 그대로입니다(1차의 h 단서도 그대로 유효).

## 3. O-2 생성기·도구 [실행] (`o2/run_o2.sh`, 18:07:34–18:15:09)

- 20개 명령 모두 exit 0이고, Traceback은 0입니다.

| 점검 | 결과 |
|---|---|
| reference / plant / config | `add58bc4` / `b119d6d9` / `319d07aa` (1차와 같음) |
| 후보 `--urban-batch1` / `--components U1,U3` | **`4e85cfd6` / `c60bde7c`**. 선언 §1.4가 바뀐다고 예고한 값이고, `K7_FIX.md` §6-2의 기대값과 같음 |
| `derive_ramp_forecast_n31 --check` | `RAMP_FORECAST_OK`(drain 17.4/43.0/31.1/88.4/38.6/154.3/33.1/44.6, 1차와 같음) |
| port profile / obs150 | `PORT_PROFILE_OK` / `108debbb` 294행 |
| `derive_unsignalized_validation --check` ×2 | 두 번 모두 `d8718b9d` |
| C-9 생성기 다섯 개 | phase authority `9ba47f3b`, area `fdc21f06`(provenance `f912429d`), route queue `181a452a`, routing β `4290d180`, **무신호 회전 `43247697`** |
| `preflight_tuning_paths` ×3 | PASS |
| `repin verify` | `REPIN_VERIFY_OK files=70 pins=122 net=identical` |
| `configure-check --sec 1/150/900` | `REPIN_CONFIGURE_OK … family=single_value:written=81,91,101,110 t=1:keys=312,enabled=38 t=150:keys=328 t=900:keys=376` |

- configure-check가 `freeway.lane_plant`를 빼고 돈다는 1차의 단서(`runtime_setup.py:246-251` 줄 자체는 실행되지 않음)는 그대로입니다 [읽음, 1차 §3].

## 4. O-3 허용 diff와 파생 기대값

### 경로 [실행] (`o3/o3_paths.py` → `o3_paths.json`)

- `git diff --name-status -M 54d821c 6c4c740`: 98항목(A 18, M 67, R 13)이고, 98/98이 합집합 안에 있습니다.
- (상태, 경로) 집합이 1차(`99dc641`)의 98항목과 정확히 같습니다.

### 내용 (`o3/o3_content.py` → `o3_content.json`, 구속 실패 0)

- 하네스는 1차 `o3_content.py`의 사본입니다. 바꾼 것은 DA-2 덩어리(`o3/da2_amended_block.py`를 끼움)와 머리 docstring뿐입니다. 나머지 행의 코드는 같습니다.

| 행 | 판정 | 근거 |
|---|---|---|
| RA-1 영수증 + boundaries | 통과 | 5시드 checks 18538, 프레임 8995.1. 망 sha 31 `3de889f0`, 41 `726af589`, 43 `51478c39`, 47 `1895ca30`, 53 `c2dd1a48`(대체, `substitute` 문구 확인). 추출기 `5fa27047`, 인자는 eo와 같음 |
| RA-1 재추출(boundaries/flows/cells) | 통과 | GWT7에서 5시드를 다시 추출했습니다(18:15–18:22, 하나씩; 출력은 `tmp/ra1_reextract`로 옮김). 15파일이 v3c2 eo와 바이트 같고, sha가 1차 재추출과도 같음. boundaries는 커밋본과 같음. manifest·geometry 차이는 경로, 벽시계, 그 경로를 담은 geometry의 sha뿐(1차와 같은 키 6종) |
| RA-2 s31 geometry | 통과 | v3c2 eo `b705f472`와 provenance 키 8개만 다름 |
| RA-3 / RA-4 | 보고 | 1차와 같음(수치 리프 30개, 최대 \|Δ\| 10; RAMP_FORECAST 위 표) |
| DA-1 β | 통과 | 키 `routing_v3c3{,_2}`, 값 포인터 차이 0, complete-β 망 `3de889f0` |
| **DA-2 (i)** 나머지 표 다섯 + area provenance | 통과 | 핀만 바뀜. area 계약은 바이트 같음 |
| **DA-2 (ii)** `unsignalized_turns` (선언 §1.4) | **통과** | 아래 표 |
| **DA-2/DA-6 하류** (선언 §1.4) | **통과** | 아래 |
| DA-3, DA-4, DA-5, DA-6 reference, DA-6 튜닝 ×3, V-6, N-4, C-7, 바꾸지 않는 것 | 통과 | 1차와 같은 값. 튜닝 세 벌 모두 단일값 사상 M, vsl_set, max_vsl_step 40, ignore_wall_time_limits true |

**DA-2 (ii): 수정 선언 §1.4 (a)–(h)** [실행]

- v3c1 표는 K6 `54d821c` blob `c2558392fed0…`, sha256 `95ea2732…`, 34,022 B로, 선언 §1.2와 같습니다.
- v3c3 표의 sha256은 `43247697899a…`입니다.

| # | 판정 | 값 |
|---|---|---|
| a | 통과 | `/movements` 이름 집합 = v3c1 23개. 순서도 같음(보고) |
| b | 통과 | 23행(`SC103_S_SC6_to_E` 포함) 모두 `validation` 밖이 v3c1 행과 같음. 키 순서까지 같음 |
| c | 통과 | `/not_included_fzp_validation` = [(`SC107_N_SC1_to_W_SC1005`, [10610])]. 수치만 다름(crossings 553 → 552, red_bin c150 0.13 → 0.07) |
| d | 통과 | `schema`, `definition`, `not_included_shared_lane`, `already_unsignalized_by_phase_authority`, `screened_signalized_movements`, `downstream_head_not_included`, `validation_rule`이 같음 |
| e | 통과 | 그 밖에 다른 키는 `generated`, `network`, `inputs`뿐이고, 다른 리프는 날짜와 `/path`·`/sha256`뿐 |
| f | 통과 | 더한 키는 `membership_pin` 하나이고 맨 끝. 다른 키 순서는 v3c1과 같음. `movements` 23개. `source` = 경로·commit `54d821c1…`·blob·sha256이 K6 객체와 같음. `known_validation_exceedances`는 1건: `SC103_S_SC6_to_E` [10096]. v3c3 수치(0.0544, n 5602)가 그 행의 `validation`과 같고, v3c1 수치(0.0472, n 5611)가 v3c1 행과 같음 |
| g | 통과 | 나머지 22행 모두 n ≥ 100, 비율 ≤ 0.05. `SC103_S_SC6_to_E`는 실제로 문턱을 넘음(초과 기록이 실재함) |
| h | 통과 | O-2 `--check` `43247697` exit 0. 거부 시험 `test_derivation_refuses_another_membership`이 O-1 n31에서 ok |

- 보고 [실행]
  - 23행과 미검증 1행의 `validation`이 검증표 `d8718b9d`의 커넥터 값과 모두 같습니다(불일치 0).
  - v3c1 대비 `movements` 안의 검증 수치 변화는 51개입니다.
  - 교차 확인: fix 단계의 `check_da2.py`를 W 대신 GWT7을 읽게 한 사본(`o3/check_da2_gwt7.py`)도 `DA2_AMENDED OK`였습니다.
- **알려진 초과 (선언 §1.2, 공개)**: `SC103_S_SC6_to_E`는 v3c3에서 0.0544(n 5602) > 0.05, v3c1에서 0.0472(n 5611)입니다. U3 후보 튜닝만 이 표를 읽습니다. 배포 경로(R-obs3·J1)는 읽지 않습니다 [읽음, 선언 §1.2].

**하류 기대값 (선언 §1.4, 구속)** [실행]

- `config_n31_v2_urban_b1.json`(`7c43f881` → `4e85cfd6`)과 `config_n31_v2_urban_b1_u1u3.json`(`371c6b75` → `c60bde7c`)은 `99dc641` 대비 포인터 차이가 정확히 1개입니다.
  - 그 포인터는 `/urban/movements/unsignalized_evidence/sha256`이고, `83326aca…` → `43247697…`(새 표 sha)입니다.
  - evidence 경로는 새 표입니다.
- `99dc641`과 바이트가 같은 것
  - `config_n31_v2.json` `319d07aa`, `plant_n31_v2.json` `b119d6d9`, `reference_config_n31_v2.json` `add58bc4`, `scenario/lane_native_b110.vbs` `37c5021f`
  - 검증표 `d8718b9d`
  - DA-2 나머지 표 다섯(`9ba47f3b`, `fdc21f06`, `181a452a`, `04fce57c`, `c2ef5b0f`)과 area provenance `f912429d`

## 5. O-4 VSL 가족 · O-6 110 미만 쓰기 (다시 돌림) [실행] (`run_o4_o6.sh`, 18:10:54–18:11:30)

- **O-4** (`o4/o4_run.py` 사본, 1차와 같은 코드): (a)–(e)가 모두 True입니다.
  - (a) 튜닝 세 벌(후보 두 벌은 새 sha) 모두 `{'family':'single_value','commands':[80,90,100,110],'written':[81,91,101,110],'speed_scale_roads':['FW_E']}`
  - (b) K7 망 사본은 [81,91,101,110]을 받고, v3c2 s31 원본은 `[81, 91, 101]` 부재로 거부
  - (c) L1 가족 두 벌이 결정적이고, `configure-check` OK
  - (d) d1/d2는 `REPIN_ERROR VSL family:`, d3는 `plant runner_config differs from its pin`
  - (e) 발사기 함수 단위 통과
  - `o4_result.json`은 1차와 비교해 `gates` → `regate` 경로 밖의 차이가 0입니다.
- **O-6** (`o6/o6_run.py` 사본): P1–P5는 ACCEPT이고 기대한 쓰기 값입니다. N1–N6은 모두 True입니다.
  - CSV 12개는 1차와 바이트 같습니다.
  - VBS 11개는 1차와 비교해 CSV 경로 한 줄(`gates` → `regate`)만 다릅니다.
  - `o6_result.json`은 경로 밖의 차이가 0입니다.

## 6. O-5 L2 all-110 plant 동일성 (FRZ_K6, R-obs1, 읽기 전용) [실행] (`o5/run_o5.sh`, 18:08:06–18:15:55)

- **입력**
  - v3c1 R-obs 상태 4개(900, 3600, 4800, 6300)를 그대로 다시 썼습니다. `RUN = D:/VISSIM_runs/20260928_sdmpc31_v3c1/sdmpc31_v3c1_nc_s31`, `FRZ = frozen/sdmpc31_54d821c1_202610011123`입니다.
  - P10 `l0l1_*.py` 사본 3개는 P10 원본과 sha가 같습니다(`b03ddc4b`, `45362146`, `db136b2d`).
  - reference 세 벌 `ref_{L2,KA,L1}.json`은 1차와 바이트 같습니다(L1 = `6c597e25…`).
  - tcache와 numba 캐시는 새로 만들었습니다.
- **전제**
  - 핵심 5모듈은 blob이 K6 = K7입니다.
  - 하네스가 import한 FRZ 파일은 71개이고, K6 ≠ K7은 `beta_source.py`, `vissim_stackelberg_adapter.py` 둘뿐입니다(1차와 같음). 수정 커밋 9경로는 import 목록에 없습니다.
  - FRZ_K6 파일 목록은 전후 같습니다.
- **판정기**: `o5/o5_compare.py`(1차 사본)입니다. 바꾼 것은 다음뿐입니다.
  - K7 상수
  - 상태 판정에서 `ops_rule`/`entries_rule`을 빼고 `*_REPORT_ONLY`로 내림(선언 §2.2 항목 6)
  - 항목별 판정(`amended_items`), 상쇄 진단, 1차 비교 보고 필드를 더함

| 조건 | 판정 | 내용 |
|---|---|---|
| 1 | 통과 | `speed_scale_ratio(…,110) == 1.0`. 4상태 × FW_E 31셀이 hex 동일 |
| 2 스칼라 all-110 | 통과 | 4상태 × 2도로에서 L2 = KA = L1, 입력 6종 동일 |
| 3 fwe100 | 통과 | FW_E는 L2 ≠ KA(예: 4800 ttt 148.051644 대 147.852611), FW_W는 같음 |
| 4 (§2.2) | **통과** | 4상태 모두 항목 1–5 통과(아래) |
| 5 digest | 보고 | all-110 digest 8개가 P10 기록과 모두 같음 |

- **새 조건 4의 구속 항목** (4상태 모두)
  1. primal: ttt·blocks·vehicles·speeds hex가 L2 = KA = L1
  2. FW_W: 세 벌 모두 도함수 열 0, Trace `result()`는 L2 = KA(= L1), 법칙 호출 0
  3. FW_E: `event_counts`, `max_tangent_entries`, `exact_tie_axes`, `discrete_dependent_axes`가 L2 = KA. n_L2 = n_KA = 27,809
  4. κ = 1.1924542785990433 비례: 리프 148개 위반 0. 최대 상대 편차는 1.8e-14 / 8.5e-15 / 5.5e-14 / **2.3e-13**(900/3600/4800/6300)
  5. 0이 아닌 FW_E 도함수 148개, L2 ≠ L1
- **항목 6 (보고만, 등식은 더 이상 구속 아님)**
  - d1은 세 프로세스 모두 연산 38, 항목 38입니다(단일 호출 연산 L2 47, KA 9). n × d1 = 1,056,742입니다.

| T | ΔOps (L2 − KA) | 편차 | ΔEntries | 편차 | 버린 0 항목 L2 / KA (차) | 접힘 L2 / KA (차) |
|---|---|---|---|---|---|---|
| 900 | 1,056,746 | +4 | 1,056,609 | −133 | 283,042 / 282,988 (+54) | 18,979 / 18,975 (+4) |
| 3600 | 1,056,730 | −12 | 1,056,406 | −336 | 289,464 / 289,335 (+129) | 18,958 / 18,950 (+8) |
| 4800 | 1,056,732 | −10 | 1,056,475 | −267 | 290,283 / 290,224 (+59) | 18,925 / 18,937 (−12) |
| 6300 | 1,056,722 | −20 | 1,056,531 | −211 | 285,384 / 285,259 (+125) | 18,833 / 18,817 (+16) |

  - 첫 실행 값(수정 선언 §2.1 표)과 연산 수·항목 수가 4상태 모두 정확히 같습니다.
  - 상쇄 진단(`o5_diag_collapse.py`)은 이번에 4상태 모두 돌렸습니다(1차는 900·6300만). 진단 프로세스의 연산 수는 관문 런과 같습니다.
  - 900·6300 진단 값은 1차와 같습니다.
  - [추론] 설명은 선언 §2.1과 같습니다. κ배된 접선에서 정확한 0 상쇄가 한쪽에서만 일어나, 법칙 밖 하류 연산 수가 달라집니다.
- **1차와의 동일성** (`o5/out/first_run_identity.json`)
  - `cond1.json`: JSON 동일
  - scalar pickle ×3: 다른 곳은 `/reference`(경로), `/setup_sec`, `/states/*/sec`뿐
  - tangent JSON ×3: 다른 곳은 위 경로·벽시계와 `/tangent_cache`, `/total_sec`뿐
  - 즉 O-5 결과는 K7 이동과 무관하게 비트 재현됩니다.
- **옛 기준과의 관계 (공개)**: `PREDECL:160-163`의 정확한 등식으로 판정하면 위 편차 때문에 4상태 모두 실패입니다. O-5 통과는 수정 선언 §2.2에만 근거합니다. 결정 주체 확인은 §0 단서 1을 보십시오.

## 7. O-7 문서·주석·이월 [실행·읽음]

- **grep 기록(N17)** [실행]: `o7/o7_check.py`가 fix 단계의 `o7_counts.py`와 독립적으로 셉니다.
  - 기준은 `REPIN_V3C3_REPORT.md` §5(`:70-88`)의 명령 그대로입니다: `git grep -l/-h -F … 6c4c740 -- . ':!vendor'`, 코드 행은 `'*.py' '*.ps1' '*.vbs'`.
  - GWT7에서 잰 값과 커밋된 보고 표를 파싱한 값을 비교했습니다.

| 패턴 | 보고 파일/줄 | 측정 파일/줄 |
|---|---|---|
| `2577209b` | 29 / 57 | 29 / 57 |
| `226baa37` / `b8e7cf1f` | 6 / 6, 6 / 6 | 6 / 6, 6 / 6 |
| `ec0cd81d` / `385f40da` | 5 / 5, 5 / 5 | 5 / 5, 5 / 5 |
| 코드 `v3c1` | 21 / 123 | 21 / 123 |
| 코드 `0.94` | 12 / 14 | 12 / 14 |
| 코드 `1.44` | 13 / 20 | 13 / 20 |
| `RW_ALLOWED_VSL_SPEEDS = ` | 35 / 44 | 35 / 44 |

  - 9행 모두 건수와 사유가 있고, 범위 문구(`vendor/` 제외, 보고 자신 포함, 명령)가 있습니다. 바이너리 일치는 0입니다.
  - 단어 일치(`-w`)로 재면 `0.94` 9파일, `1.44` 12파일이고, `99dc641`에서도 같습니다. 1차 관문 값은 `-w`로 잰 것으로 보는 fix 보고의 추론과 맞습니다 [실행].
  - **하네스 공개**: 첫 실행은 "사유 10자 이상" 휴리스틱 때문에 `b8e7cf1f` 행("위와 같은 구성")을 사유 없음으로 보아 FAIL을 냈습니다. 그래서 참조형 사유를 실제로 검사하도록 고쳤습니다. 그 행의 파일 범주(v3c1 추출 2, worklog 3, 이 보고 1)가 위 행과 같은지 봅니다. `385f40da` 행("위(s47)와 같은 구성")도 같은 방식으로 일치를 확인했습니다. 고친 하네스로 다시 돌린 결과가 `o7_check.json`이고, `O7_GREP_RECORD OK`입니다.
- **나머지 O-7 항목** [실행·읽음]
  - 수정 커밋이 바꾼 문서 줄은 `CONTRACT.md:723`, `PLANT_PORTING_GUIDE.md:110,:113`(현재 sha, 소속 고정 문구)뿐입니다(diff 3줄). 1차가 확인한 CONTRACT v3c3 항목(R3, N11–N13, N16, V-9, L2·M)은 그대로입니다.
  - 이월 사전값 표의 sha 5개(`6b40550a`, `8e4f6047`, `54704bee`, `a3390254`, `4091d6e1`)가 `REPIN_V3C3_REPORT.md`에 남아 있습니다.
  - QUALIFICATION(`plant_n31_v2.json`)은 바이트 불변입니다.
  - 주석(`physical_movement_routes.py`, `area_dynamic_routes.py`)은 diff 밖입니다.
  - N31 문서에서 "무신호 22개"로 남은 낡은 문구는 없습니다. `REPIN_V3C3_REPORT.md:30`은 "규칙대로면 22개지만 소속을 v3c1 23개로 고정"입니다.

## 8. O-8 트리 위생 [실행] (`o8_snapshot.py` 사본, `o8_before.json` 18:06:18, `o8_after.json` 18:25:00)

- **W**: HEAD `6c4c740`, `status --ignored` 0줄(전후).
- **GWT7**
  - HEAD `6c4c740`. 관문 뒤 `__tangentcache__` 60개(3,255,670 B, 18:08:23–18:08:27)를 `moved_tangentcache/`로 옮겼습니다. 목록은 `moved_tangentcache_list.csv`(sha256 `f7f15b55…`)이고, 옮긴 뒤 sha 불일치는 0입니다.
  - RA-1 재추출 폴더와 s53 참고 추출 폴더(`_k7regate_*`)는 GWT7 밖 `tmp/`로 옮겼습니다.
  - 그 뒤 `status --ignored` **0줄**입니다. pyc는 0개입니다.
- **GWT6** `sim3-n31-v3c3-k6gate`
  - 전후 모두 HEAD `54d821c`, `status --ignored` **0줄**이고, status sha·파일 수·바이트·최신 mtime(11:17:41)이 같습니다. 관문 중 외부 쓰기는 없었습니다.
  - **수정 선언 §4 처리 확인** [실행]
    - 떠도는 pyc의 sha256 `6a7cdabd…`, 60,292 B, mtime 17:04:51, 머리(magic `cb0d0d0a`, 원본 mtime 11:17:30, 47,236 B)가 `fix/o8/o8_gwt6.json`에 기록되어 있습니다.
    - 사본 `fix/o8/evidence/k6gate_control_area_objective.cpython-312.pyc`의 sha가 같습니다.
    - 출처 기록(외부 워크플로 `wf_f7f340b8-6ad`, 에이전트 `a960e462f93b6b664`, `-B` 없는 import)은 [읽음]입니다.
    - 원본은 GWT6에서 지워졌고 `__pycache__`도 없습니다.
    - 옮긴 `__tangentcache__` 88개(4,678,034 B)는 목록 csv(`c6a21427…`)와 크기·sha가 모두 같습니다.
- **다른 트리 5개** (`sim3-n31-v3c1`, `-urban-b2`, `-f10f11`, `-termcost`, `-hybrid`): HEAD·status 줄 수·status sha·파일 수·바이트·최신 mtime이 전후 모두 같습니다.
  - urban-b2는 status 42줄이고, termcost 9줄, hybrid 5줄입니다. 관문 전부터 그대로이고, 다른 작업의 상태입니다.
  - 같은 세션의 다른 워크플로가 urban-b2를 읽는 Python 프로세스를 돌리고 있었지만(18:05 확인), 전후 변화는 없었습니다.
- **`frozen/*`** 28개 항목: 파일 수·바이트·최신 mtime이 같고, 새 폴더는 없습니다.
  - FRZ_K6(`54d821c1`)과 FRZ_OLD(`5323faa4`)는 FREEZE 표가 무결하고, 다시 해시해도 0/0/0입니다. 캐시 파일 수 0 / 119가 전후 같습니다.

## 9. 다음 (메인 세션)

1. **O-5 결정 주체 기록**(수정 선언 §0): 사용자 결정인지 확인해 선언 기록에 적습니다. 그 전에는 O-5 통과의 근거가 비어 있습니다.
2. **s53 사후 확인**(O-0, `PREDECL:65`): 런이 끝났으니 GB-1 s53을 판정합니다. 바이트 절반은 이 단계에서 참고로 같음을 확인했습니다(`s53_ref/s53_byte_check.json`). 하나라도 어긋나면 STOP입니다.
3. 위 두 가지가 정리되고 이 결과(all_pass = true)를 받아들이면, 수정된 관문은 모두 통과한 것입니다. 그다음에야 `git -C D:/VISSIM-merge/sim3-n31-v3c3 push -u origin claude/repin-v3c3-20261001`을 합니다. **이 단계는 푸시하지 않았습니다.**
4. GWT6은 0줄 상태입니다. GB 단계 동안에도 다른 워크플로가 `-B` 없이 import하지 않게 막아야 합니다 [추론].
5. GWT7은 `6c4c740`에 detached로 남겨 두었고, 0줄입니다.
