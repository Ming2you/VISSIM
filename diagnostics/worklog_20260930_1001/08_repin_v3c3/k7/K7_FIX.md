# K7 수정 보고 (수정 선언 1 이행: O-3 · O-7 · O-8)

- 작성 2026-10-01 18:0x KST. 기준 문서는 `reports/k7/K7_AMENDMENT_1.md`입니다.
  - sha256 `1b1d39554dba1f9643f8bd20e6599c2bbb333d1c46d18c740e8c9959f58d46c9`, 15,674 B
  - 17:47:26 고정. 그때 W HEAD `99dc641`, `status --ignored` 0줄이었습니다. 코드 수정 전, 관문 재실행 전입니다.
  - 지금 다시 계산해도 sidecar와 같습니다 [실행].
- 결과 W HEAD는 **`6c4c740009f7ad9c6c0c275f8715839614ec6838`**입니다. K7 `99dc641` 위에 커밋 2개를 더했고, 푸시하지 않았습니다(`origin/claude/repin-v3c3-20261001` 없음).
- **관문(O-1…O-8)은 다시 돌리지 않았습니다.** 수정 선언 §5와 사전 선언 O-0(`PREDECL:56`)에 따라 다음 단계가 새 HEAD에서 처음부터 돌립니다.
- 증거 폴더는 `D:/VISSIM_runs/20261001_v3c3/reports/k7/fix/`(`scripts/`, `logs/`, `o8/`)입니다. 아래 상대 경로는 이 폴더 기준입니다.
- 모든 Python은 BELOW_NORMAL(`scripts/bn.py`, 0x4000 되읽기), `-B`, `PYTHONDONTWRITEBYTECODE=1`로 돌렸습니다. numba 캐시는 `fix/numba_cache`에 두었습니다(`scripts/env.sh`).
- 표기: **[실행]** 직접 돌려 확인 · **[읽음]** 파일·코드·기록에서 확인 · **[추론]** 시험하지 않은 판단. 코드 줄 번호는 `6c4c740` 기준입니다.

## 0. 요약

| 항목 | 한 일 | 결과 |
|---|---|---|
| 수정 선언 | `K7_AMENDMENT_1.md` + `.sha256`을 코드 수정 전에 고정 | O-3·O-5 변경이 결과를 본 뒤의 결정임을 적음. O-3은 사용자 결정, O-5는 결정 주체를 메인 세션이 확인해야 함. 둘 다 조건을 약하게 만들어 O-9 보충 규칙 밖임도 적음. 새 기준 §1.4·§2.2 |
| O-3 | 커밋 `91efffc` | 무신호 회전 소속 = v3c1 23개. 생성기 핀과 거부 규칙. 새 DA-2 기준 (a)–(g) 통과 [실행]. `--check` 연쇄 18/18 exit 0. n31 묶음 200 OK(skip 3) |
| O-7 | 커밋 `6c4c740` | `REPIN_V3C3_REPORT.md` §5의 9행 모두 파일·줄 수와 명령. 최종 트리에서 다시 재도 고정점 |
| O-8 | GWT6 정리 | pyc 출처 확인(외부 워크플로, `-B` 없는 import). sha·사본 남기고 삭제. `__tangentcache__` 88개는 옮김. GWT6 `status --ignored` **0줄** |
| 커밋 규칙 | 두 커밋 모두 W, 명시 경로, Ming2you/alsrjsrb1915@snu.ac.kr(작성자·커미터), `Co-Authored-By` 끝 줄, `--renormalize` 없음 | `git diff --name-status 54d821c 6c4c740`은 98경로 그대로, 새 경로 0 |

## 1. 수정 선언 [실행·읽음]

- 다음 순서로 썼습니다.
  1. 사전 선언 sha `fad31d70…` 확인
  2. 관문 보고 sha `a8b1ab6d…` 확인
  3. W·GWT7 HEAD와 status 0줄 확인
  4. 선언을 쓰고 sidecar 기록(17:47:26)
  5. 그 뒤 코드 편집
- 내용
  - §0: 사후 결정 공개
  - §1: O-3 결정, 구현 방식, 새 DA-2 기준 (a)–(h)와 하류 기대값
  - §2: O-5 새 조건 4. n × d1 등식만 보고로 내리고, 나머지는 그대로. GB-8에도 적용
  - §3: O-7, 기준 그대로
  - §4: O-8, 기준 그대로, GWT6 처리
  - §5: 재실행 규칙
- 지시 원문이 O-3에만 "USER CHOSE"를 쓰고 있어, O-5 결정 주체는 선언에 "메인 세션이 확인해 적어야 함"으로 남겼습니다.

## 2. O-3 수정 (커밋 `91efffcf8b56474c9be8670d2f5df077e1199389`)

### 2.1 바꾼 것 [실행 diff]

| 파일 | 변경 |
|---|---|
| `scripts/derive_unsignalized_turns.py` | 아래 생성기 변경 참고 |
| `N31D/urban/unsignalized_turns_v3c3_20261001.json` | 다시 유도. sha256 `83326aca…` → **`43247697899a156ad6d078349cf32a3fa2180f0cef922e876fbeaf428ebafa16`**. `membership_pin`은 `:1521` |
| `N31D/make_config_n31.py` | `URBAN_B1_UNSIGNALIZED_SHA256`(`:162`), 유도 주석(`:128-131`) |
| `N31D/config_n31_v2_urban_b1.json` | `make_config_n31.py --urban-batch1`로 다시 씀. `7c43f881` → **`4e85cfd6…`** |
| `N31D/config_n31_v2_urban_b1_u1u3.json` | `--components U1,U3`로 다시 씀. `371c6b75` → **`c60bde7c…`** |
| `N31D/tests/test_n31_urban_batch1.py` | `import subprocess`(`:38`). `test_strict_rule_excludes_downstream_heads_and_unvalidated`(`:655`, 이름 그대로)이 23개와 초과 1건을 고정. 새 시험 둘(아래) |
| `N31D/CONTRACT.md:723`, `PLANT_PORTING_GUIDE.md:110,:113` | 후보 sha, 소속 고정 문구 |
| `N31D/REPIN_V3C3_REPORT.md` | `:12`, `:30`, §4(b) 문구 |

- **생성기 변경** (`scripts/derive_unsignalized_turns.py`)
  - docstring 단락(`:21-26`)
  - `MEMBERSHIP_PIN`(`:54`): 출처는 K6 blob `c2558392…`, sha256 `95ea2732…`. 이름 23개와 알려진 초과 {`SC103_S_SC6_to_E`: 10096, v3c1 0.0472/5611}를 담음
  - 검증 단계(`:161-167`): 핀의 초과 회전이 비율 문턱**만** 넘을 때 포함하고 기록(n ≥ 100, 비율 있음 필요)
  - 거부(`:172-181`): 소속 ≠ 핀이거나, 초과 집합 ≠ 선언이면 SystemExit
  - 출력 마지막 키 `membership_pin`(`:196`)
- **새 시험**
  - `test_membership_is_pinned_to_the_v3c1_list`(`:681`): K6 blob과 이름·행·순서를 대조하고, 출처 sha를 확인합니다.
  - `test_derivation_refuses_another_membership`(`:709`): 네 경우 거부를 확인합니다. 핀을 되돌리면 sha 핀이 재현됩니다.
- 하류가 실제로 바뀐 범위 [실행 `git diff`]
  - 후보 config 두 벌은 `/urban/movements/unsignalized_evidence/sha256` 한 줄씩만 바뀌었습니다.
  - `config_n31_v2.json`(`319d07aa`), `plant_n31_v2.json`(`b119d6d9`), `reference_config_n31_v2.json`(`add58bc4`), `scenario/lane_native_b110.vbs`, `urban/unsignalized_validation_v3c3nc_20261001.json`(`d8718b9d`)은 `99dc641` 대비 diff 0입니다.
- 줄끝
  - N31D 파일(`-text`)은 i/lf·w/lf 그대로입니다.
  - `scripts/derive_unsignalized_turns.py`는 작업본이 CRLF 그대로이고, 커밋 blob은 LF(CRLF 0/236)입니다.
  - 바뀐 9개 모두 작업본 = `git cat-file --filters HEAD:<f>` [실행].

### 2.2 새 DA-2 기준 판정 (수정 선언 §1.4) [실행 `scripts/check_da2.py 6c4c740` → `logs/check_da2_6c4c740.json`, `DA2_AMENDED OK`]

| # | 판정 | 값 |
|---|---|---|
| a | 통과 | `/movements` 이름 = v3c1 23개. 순서도 같음 |
| b | 통과 | 23행 모두 `validation` 밖은 v3c1 행과 같음(`SC103_S_SC6_to_E` 포함) |
| c | 통과 | `/not_included_fzp_validation` = [(`SC107_N_SC1_to_W_SC1005`, [10610])]. v3c1과 같고 수치만 다름 |
| d | 통과 | `schema`·`definition`·`not_included_shared_lane`·`already_unsignalized_by_phase_authority`·`screened_signalized_movements`·`downstream_head_not_included`·`validation_rule`이 v3c1과 같음 |
| e | 통과 | 그 밖에 다른 키는 `generated`·`network`·`inputs`뿐 |
| f | 통과 | 더한 키는 `membership_pin` 하나이고 맨 끝. `movements` 23개, `source` blob·sha가 K6 객체와 같음. `known_validation_exceedances` 1건 = `SC103_S_SC6_to_E` [10096], v3c3 0.0544/5602(그 행의 `validation`과 같음), v3c1 0.0472/5611 |
| g | 통과 | 나머지 22행은 모두 n ≥ 100, 비율 ≤ 0.05 |
| h | 통과 | `--check` 두 번 모두 `43247697`. 거부 네 경우의 메시지는 `logs/refusal_messages.log` |

- 거부 네 경우와 메시지
  - 회전 하나 뺌 → "extra ['SC1_S_to_E_SC11']"
  - 검증 안 된 회전 더함 → "missing ['SC107_N_SC1_to_W_SC1005']"
  - 초과 선언 없음 → "missing ['SC103_S_SC6_to_E']"
  - 초과가 아닌 회전을 초과로 선언 → "exceedances … differ"
- `movements` 안의 검증 수치 변화는 51개입니다(v3c1 대비).

### 2.3 W에서 돌린 점검 [실행]

- 생성기 `--check` 연쇄(`scripts/run_checks_fix.sh` → `logs/checks_fix.log`): 18개 모두 exit 0입니다. 구현 단계의 `run_checks_k7_fast.sh` 목록과 같고, unsignalized turns만 두 번 돌렸습니다.
  - `REPIN_VERIFY_OK files=70 pins=122 net=identical`
  - phase authority `9ba47f3b`, routing β `4290d180`, unsignalized turns `43247697`(×2), route queue `181a452a`, area `fdc21f06`
  - obs150 `108debbb` 294행, reference `add58bc4`, plant `b119d6d9`, `RAMP_FORECAST_OK`
  - config `319d07aa` / `4e85cfd6` / `c60bde7c`, `PORT_PROFILE_OK`, preflight ×3 PASS
- 시험 n31 묶음(O-1 n31과 같은 16모듈, `logs/n31.log`): **200 OK, skip 3**입니다.
  - 관문 때 198개에 새 시험 2개가 더해졌습니다.
  - skip 3개는 같은 이유입니다: `test_missing_owner_inputs_are_listed`, `PortProfileTests.test_regenerates_bytes`, `test_g1_frame`.
  - 집중 실행 `logs/unsig_tests.log`: 13 OK.
- 실행 뒤 W `status --porcelain --ignored`는 0줄입니다(옮길 캐시 없음).
- **돌리지 않은 것**
  - `derive_unsignalized_validation.py --check`: 5.9 GB FZP를 읽습니다. 그 생성기와 표는 바뀌지 않았습니다(diff 0).
  - `configure-check`
  - O-1의 나머지 묶음(t9·tools·obs·pyt·extra·diag·dprof·new)
  - 이것들은 재실행 단계에서 돕니다.

## 3. O-7 수정 (커밋 `6c4c740009f7ad9c6c0c275f8715839614ec6838`)

- `N31D/REPIN_V3C3_REPORT.md` §5(`:70-89`)를 표 형식(패턴 | 파일 | 줄 | 남은 곳과 사유)으로 바꿨습니다.
  - 범위: 최종 K7 트리, `vendor/` 제외, 보고 자신 포함
  - 정확한 `git grep -F` 명령을 함께 적었습니다.
  - 측정 스크립트는 `scripts/o7_counts.py`, 기록 스크립트는 `scripts/e_o7_report.py`입니다.

| 패턴 | 파일 | 줄 |
|---|---|---|
| `2577209b` | 29 | 57 |
| `226baa37` / `b8e7cf1f` / `ec0cd81d` / `385f40da` | 6 / 6 / 5 / 5 | 6 / 6 / 5 / 5 |
| 코드 `v3c1` | 21 | 123 |
| 코드 `0.94` | 12 | 14 |
| 코드 `1.44` | 13 | 20 |
| `RW_ALLOWED_VSL_SPEEDS = ` | 35 | 44 |

- 같은 값을 세 번 쟀습니다: `91efffc`, 작업본, `6c4c740`(`logs/o7_counts_{91efffc,worktree,6c4c740}.json`). 보고 자신을 넣어도 값이 같습니다(고정점) [실행].
- 관문 값과 다른 곳
  - 코드 `v3c1`은 20 → 21입니다. O-3의 `MEMBERSHIP_PIN` 때문이고, 보고에 적었습니다.
  - 코드 `0.94`·`1.44`는 관문이 적은 9·12와 다릅니다. 관문은 측정 방식을 남기지 않았습니다. 단어 일치(`git grep -w -F`, 같은 세 확장자)로 재면 `99dc641`에서 9·12로 관문 값과 같습니다 [실행]. 그래서 관문은 `-w`를 쓴 것으로 봅니다 [추론].
  - 보고에는 고정 문자열 값과 그 안의 다른 숫자 일치(5파일씩)를 따로 적었습니다.
- 행마다 사유를 파일 단위로 다시 확인했습니다 [실행 목록]. 예: `2577209b` 29 = 추출 3 + 문서 11 + 생성기·도구 7 + plant 1 + 영수증 2 + 시험 5.
  - `2577209b`의 코드 줄 20개는 모두 이력 주석, `PREVIOUS_RUNTIME_NETWORK`, 시험 상수입니다. 살아 있는 핀은 0개입니다 [읽음].

## 4. O-8 처리 (GWT6) [실행 `scripts/o8_gwt6_clean.py` → `o8/o8_gwt6.json`]

- 처리 전 GWT6: HEAD `54d821c`, `status --porcelain --ignored` 2줄
  - `!! evaluation/controllers/__pycache__/`
  - `!! evaluation/controllers/__tangentcache__/`
- 스크립트는 HEAD와 이 두 줄이 정확히 맞을 때만 진행하도록 짰습니다.
- **떠도는 pyc**
  - 파일: `evaluation/controllers/__pycache__/control_area_objective.cpython-312.pyc`, 60,292 B, mtime 17:04:51.29
  - sha256 **`6a7cdabddf0b174ca90897b085fae52a114a8c54904c2d5ac6d39f23a63f0d01`**
  - 머리: magic `cb0d0d0a`(3.12), flags 0, 원본 mtime 11:17:30, 원본 47,236 B
  - 이 머리는 GWT6 자신의 `control_area_objective.py`(mtime 11:17:30.98, 47,236 B, sha `0781f329…`)와 맞습니다(`header_matches_gwt6_source: true`).
  - `evaluation/`에는 `__init__.py`가 없어 이 모듈 하나만 컴파일된 것과 맞습니다.
- **출처 (가능성 높음)** [읽음: 이 세션 워크플로 기록]
  - 워크플로 `wf_f7f340b8-6ad`(SC1001-EB opt1 설계·검토), 에이전트 `a960e462f93b6b664`
  - 17:04:49.78에 `cd …-k6gate && python - <<EOF … sys.path.insert(0,'.') … from evaluation.controllers.control_area_objective import physical_membership_from_ledger`를 `-B` 없이 실행했습니다.
  - 이 워크플로의 마지막 기록은 17:20:58이고, 지금 GWT6 경로를 쓰는 프로세스는 0개입니다(17:4x 프로세스 목록) [실행].
- **처리**
  - 사본 `o8/evidence/k6gate_control_area_objective.cpython-312.pyc`를 남겼습니다(sha 같음).
  - GWT6에서 파일과 빈 `__pycache__`를 지웠습니다.
- **`__tangentcache__`**
  - 88개, 4,678,034 B, mtime 16:28:56–16:29:03입니다. 관문 전부터 있었습니다.
  - 같은 워크플로의 에이전트 `ac30b914ef55da5cb`가 16:28:54에 GWT6 아래에서 `f2_run.py`를 돌린 것입니다 [읽음].
  - 지우지 않고 `o8/moved_k6gate_tangentcache/`로 옮겼습니다. 옮긴 뒤 88개 모두 sha가 같습니다. 목록은 `o8/moved_k6gate_tangentcache_list.csv`(sha256 `c6a21427…`)입니다.
- **처리 후**: GWT6 HEAD `54d821c`, `status --porcelain --ignored` **0줄** [실행].

## 5. 건드리지 않은 것 [실행·읽음]

- GWT7: HEAD `99dc641`, `status --ignored` 0줄 그대로입니다. 재실행 전에 새 K7로 옮겨야 합니다(§6).
- FRZ_K6, FRZ_OLD, `D:/VISSIM-merge/frozen/*`: 쓰지 않았습니다.
- `sim3-n31-v3c1`, `-urban-b2`, `-f10f11`, `-termcost`, `-hybrid`: 쓰지 않았습니다.
- 사전 선언, `K7_IMPLEMENT.md`, `K7_OFFLINE_GATES.md`, `gates/` 증거: 고치지 않았습니다. 사전 선언 sha는 sidecar와 같습니다.
- VISSIM은 시작·종료하지 않았습니다. 금지 시험 7종은 돌리지 않았습니다. 푸시·동결은 하지 않았습니다. s37/59/61/67은 열지 않았습니다.

## 6. 다음 단계(재실행)를 위한 사항

1. **K7 = `6c4c740`.** GWT7을 이 커밋으로 옮기거나(`checkout --detach 6c4c740`) 새로 만든 뒤 `status --ignored` 0줄을 확인하고, O-1…O-8을 처음부터 돌립니다(O-0).
2. **O-2**: 후보 config sha는 `4e85cfd6` / `c60bde7c`, 무신호 회전 표는 `43247697`이 기대값입니다(선언 §1.4 하류). 나머지 sha는 관문 1차와 같아야 합니다.
3. **O-3 DA-2**: 선언 §1.4로 판정합니다. `fix/scripts/check_da2.py <rev>`가 (a)–(g)를 기계적으로 봅니다. 관문은 자체 하네스를 써도 됩니다.
   - 다른 DA-2 표와 area 계약 조건은 그대로입니다. 경로 98개는 1차와 같은 집합입니다.
4. **O-5**: FRZ_K6은 그대로라 결과 수치는 1차와 같을 것으로 봅니다 [추론]. 판정은 선언 §2.2입니다. ΔOps·ΔEntries·n × d1·상쇄 진단은 보고로만 남깁니다.
5. **O-7**: `fix/scripts/o7_counts.py <K7>`가 §5 표와 같은 값을 내야 합니다.
6. **O-8**: GWT6 기준선은 이제 0줄입니다. 재실행 동안 다른 워크플로(특히 `wf_f7f340b8-6ad` 계열)가 GWT6에서 `-B` 없이 import하거나 탄젠트 캐시를 쓰면 다시 실패합니다. 메인 세션이 그동안 막아야 합니다 [추론].
7. **보류(O-0)**: v3c3 s53이 완료되면 GB-1 s53 PASS와 재추출 바이트 동일을 확인해야 합니다.
8. 모든 O가 수정 기준으로 통과한 뒤에만 `git -C W push -u origin claude/repin-v3c3-20261001`을 합니다.
9. **사람이 정할 것**: O-5 사후 변경의 결정 주체(사용자인지)를 메인 세션이 선언 기록에 확인해 적어야 합니다.
