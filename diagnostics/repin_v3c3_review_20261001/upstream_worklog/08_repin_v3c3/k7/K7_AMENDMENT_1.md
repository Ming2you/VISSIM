# K7 오프라인 관문 수정 선언 1 (사후 결정, 재실행 전 고정)

- 작성 2026-10-01 17:4x KST. **관문 재실행 전, K7 수정 커밋 전**에 고정합니다. 고정 수단: 같은 폴더의 `K7_AMENDMENT_1.md.sha256`.
- 고정 시점 상태 [실행]
  - W `D:/VISSIM-merge/sim3-n31-v3c3` HEAD `99dc641809fb939515c6d6f1e2f655c21deef289`, `status --porcelain --ignored` 0줄
  - GWT7 HEAD `99dc641…`, `status --porcelain --ignored` 0줄
  - 사전 선언 `K7_GB_J1_PREDECLARATION.md` sha256 `fad31d7024e8c277a0e4eb40dbf28a5b1dac0db7708a3d9dfa828ec7e6c31d11` = sidecar(바뀌지 않음)
  - 관문 결과 `K7_OFFLINE_GATES.md` sha256 `a8b1ab6d8f59cf26cf7b5f6c652a0909985843581f81fd86d984efcf6a1cf2ea`(17:31, all_pass = false, O-9로 멈춤)
- 표기: **[실행]** 직접 돌려 확인 · **[읽음]** 파일·코드·기록에서 확인 · **[추론]** 시험하지 않은 판단. 줄 번호는 따로 적지 않으면 W @ `99dc641` 기준입니다. 사전 선언 줄 번호는 `PREDECL:<줄>`로 적습니다.

## 0. 이 수정의 성격 (먼저 공개)

- **O-3(DA-2)과 O-5(조건 4)의 변경은 결과를 본 뒤의 결정입니다.** 두 관문의 실패는 `K7_OFFLINE_GATES.md`(17:31)에 이미 적혀 있었고, 이 문서는 그 뒤에 씁니다.
- 사전 선언 O-9(`PREDECL:228`)는 "보충은 열거만 더할 수 있고, 조건을 약하게 바꾸는 보충은 무효"라고 정했습니다. 아래 두 변경은 **조건을 바꾸고 약하게 만듭니다.** 그래서 O-9의 보충 규칙으로 정당화되지 않습니다. 근거는 그 규칙이 아니라 아래 결정입니다.
  - **O-3**: 사용자 결정(2026-10-01 17:3x). 지시 원문은 "USER CHOSE TO KEEP THE OLD v3c1 LIST (23 entries)"입니다.
  - **O-5**: 같은 지시 묶음(17:3x, "Offline-gate failures and the USER DECISION")으로 전달된 사후 결정입니다. 지시 원문은 O-3에만 "사용자가 골랐다"를 명시합니다. 그래서 이 문서는 O-5 결정의 주체를 따로 확인하지 않았습니다. 메인 세션이 주체를 확인해 적어야 합니다.
- O-7과 O-8은 **기준을 바꾸지 않습니다.** 문서 보완과 트리 정리일 뿐입니다.
- 그 밖의 모든 관문 정의, 허용 오차, 허용 목록, GB·J1 절은 그대로입니다.

## 1. O-3 DA-2: `unsignalized_turns` 소속을 v3c1 23개로 고정 (사용자 결정)

### 1.1 실패 사실 [실행, `gates/o3/o3_content.json`]

- `urban/unsignalized_turns_v3c3_20261001.json`의 `/movements`가 23개 → 22개가 됐습니다.
- `SC103_S_SC6_to_E`(커넥터 10096)가 `/not_included_fzp_validation`으로 옮겨졌습니다.
- 원인: v3c3 fit FZP로 다시 계산한 정지 비율이 0.0472(n 5611, v3c1) → 0.0544(n 5602, v3c3)로 올라 규칙 문턱 0.05(`scripts/derive_unsignalized_turns.py:42`, 출력 `:151`)를 넘었습니다.
- 생성기 규칙은 바뀌지 않았습니다. 바뀐 것은 입력 검증표입니다.
- 선언 DA-2 행(`PREDECL:110`)의 예외는 "검증 수치"뿐입니다. 소속 변화는 그 예외 밖이라 구속 실패입니다.

### 1.2 결정

- 소속(`/movements`의 이름 집합)은 v3c1 목록 23개로 고정합니다.
  - 출처: K6 `54d821c`의 `diagnostics/sdmpc_n31_20260924/urban/unsignalized_turns_v3c1_20260928.json`
  - blob id `c2558392fed0d22f5bf53cac380d906c065b3465`, 바이트 sha256 `95ea27326d99cab1dee8557df1a8044287958082b6918c12e7e34354619867e2`(34,022 B; `REPIN_V3C1_REPORT.md:86`의 `95ea2732`와 같음) [실행]
- 검증 수치는 v3c3 입력(`unsignalized_validation_v3c3nc_20261001.json`, `d8718b9d…`)으로 다시 계산해 그대로 적습니다.
- `SC103_S_SC6_to_E`는 **알려진 초과**로 기록합니다: v3c3 0.0544(n 5602) > 0.05, v3c1 0.0472(n 5611).
- 영향 범위 [읽음]
  - 이 표를 읽는 곳은 U3 후보 튜닝 두 벌(`config_n31_v2_urban_b1.json`, `config_n31_v2_urban_b1_u1u3.json`, `/urban/movements/unsignalized_evidence`)뿐입니다.
  - 설치기는 `vissim_stackelberg_adapter.py:7165-7204`입니다. `schema`, `network.sha256`, `/movements`의 `expected_spec`만 읽습니다.
  - 배포 튜닝 `config_n31_v2.json`, plant, reference, 러너는 이 표를 읽지 않습니다.

### 1.3 구현 방식 (수정 커밋에서 할 일; 여기서는 방식만 고정)

- `scripts/derive_unsignalized_turns.py`에 소속 핀 상수를 둡니다. 상수에는 위 출처(경로, blob id, sha256), 23개 이름, 알려진 초과 집합 {`SC103_S_SC6_to_E`}(v3c1 수치 포함)을 담습니다.
- 생성 규칙
  - 구조 선별(헤드 없음, 배타 차로, 하류 헤드)과 FZP 규칙(≤ 0.05, ≥ 100)은 그대로입니다.
  - 핀에 있는 movement가 FZP 규칙**만** 어기면, 알려진 초과 집합에 있을 때에 한해 포함하고 초과로 기록합니다.
  - 생성기는 다음 경우 멈춥니다(SystemExit). 소속을 바꾸려면 새 결정이 필요하다는 뜻입니다.
    1. 도출한 소속이 핀 23개와 다름
    2. 핀 movement 중 실제 초과 집합이 선언한 초과 집합과 다름
    3. 핀 movement가 구조 선별에서 빠짐
- 출력에는 최상위 키 `membership_pin` 하나를 맨 끝에 더합니다. 나머지 키의 이름과 순서는 그대로입니다.
- 소속을 고정하는 시험과, K6 blob과 소속을 대조하는 시험을 둡니다. 22를 고정하던 시험(`tests/test_n31_urban_batch1.py:659-667`)은 고칩니다.

### 1.4 새 DA-2 기준 (`unsignalized_turns`에만 적용; DA-2 행의 다른 표·area 계약 조건은 그대로)

v3c3 표(K7 새 HEAD)를 v3c1 표(K6 `54d821c` blob)와 핀 사상 뒤 비교합니다. 모두 구속입니다.

| # | 대상 | 기준 |
|---|---|---|
| a | `/movements` 이름 집합 | v3c1 23개와 정확히 같음 |
| b | `/movements/<m>` 행(23개 모두, `SC103_S_SC6_to_E` 포함) | 키 `validation` 밖은 v3c1 행과 JSON 같음 |
| c | `/not_included_fzp_validation` | (movement, connectors) 목록이 v3c1과 같음(= `SC107_N_SC1_to_W_SC1005`, [10610]). `validation` 수치만 다를 수 있음 |
| d | `schema`, `definition`, `not_included_shared_lane`, `already_unsignalized_by_phase_authority`, `screened_signalized_movements`, `downstream_head_not_included`, `validation_rule` | v3c1과 JSON 같음 |
| e | `generated`, `network`, `inputs` | 날짜·핀만 다름(종전과 같음) |
| f | 새 최상위 키 | 정확히 하나, `membership_pin`. `movements` = (a)의 23개. `source` = 위 blob id·sha256·경로. `known_validation_exceedances` = `SC103_S_SC6_to_E` 한 건(커넥터 10096). 그 v3c3 수치 = `/movements/SC103_S_SC6_to_E/validation`(0.0544, n 5602), v3c1 수치 0.0472(n 5611) |
| g | `SC103_S_SC6_to_E` 밖의 22개 행 | 모두 규칙 충족(정지 비율 ≤ 0.05, n ≥ 100) |
| h | 생성기 | `--check` 통과(O-2 C-9). 소속·초과 집합이 바뀌면 거부함(시험) |

- **하류 기대값** (구속, O-3 DA-6 "튜닝 세 벌" 행에 더함)
  - `config_n31_v2_urban_b1.json`, `config_n31_v2_urban_b1_u1u3.json`은 `99dc641`과 `/urban/movements/unsignalized_evidence/sha256` 한 곳만 다릅니다. 새 값 = 새 표의 sha256입니다.
  - 그래서 O-2의 후보 sha(`7c43f881`, `371c6b75`)는 바뀝니다. 이것은 실패가 아닙니다.
  - 배포 튜닝 `config_n31_v2.json`(`319d07aa`), plant(`b119d6d9`), reference(`add58bc4`), 러너(`37c5021f`), DA-2의 다른 표 다섯 개, 검증표(`d8718b9d`)는 `99dc641`과 바이트 같습니다.
- **경로**: 수정 커밋이 바꾸는 경로는 모두 이미 98경로 합집합 안에 있습니다. O-3 경로 기준은 그대로입니다.
- **약해진 점(공개)**: 소속이 더 이상 규칙에서 나오지 않습니다. v3c3 FZP에서 5.44 %가 커넥터 전에 정지한 회전을 U3 후보는 무신호로 다룹니다. U3 후보를 v3c3에서 쓰는 결과에는 이 사실을 함께 적어야 합니다. 배포 경로(R-obs3·J1)는 이 표를 읽지 않습니다 [읽음].

## 2. O-5 조건 4: 연산 수 정확 등식을 값 수준 기준으로 바꿈 (사후 결정)

### 2.1 실패 사실 [실행, `gates/o5/out/o5_judgement.json`, `out/diag_collapse_{L2,KA}.json`]

- 옛 기준(`PREDECL:160-163`): FW_E에서 `operations`와 `tangent_entries` 각각 **L2 − KA = n × d1**. n = 27,809(L2 = KA, 4상태), d1 = 38(같은 프로세스에서 다시 잼), n × d1 = 1,056,742입니다.

| T | operations L2 − KA | 편차 | tangent_entries L2 − KA | 편차 |
|---|---|---|---|---|
| 900 | 1,056,746 | +4 | 1,056,609 | −133 |
| 3600 | 1,056,730 | −12 | 1,056,406 | −336 |
| 4800 | 1,056,732 | −10 | 1,056,475 | −267 |
| 6300 | 1,056,722 | −20 | 1,056,531 | −211 |

- 진단 [실행]: `Trace.scalar`를 감싸 두 가지를 셌습니다.
  - 값이 정확히 0.0이라 버린 tangent 항목(`sdmpc_dual.py:41`)
  - 항목이 모두 사라져 float로 접힌 결과(`:51`)
  - 900: 버린 항목 283,042 대 282,988(+54), 접힘 18,979 대 18,975(+4)
  - 6300: 버린 항목 285,384 대 285,259(+125), 접힘 18,833 대 18,817(+16)
- 설명 [추론]: 두 법칙의 접선은 κ배 차이입니다. κ배된 부동소수 값에서는 정확한 상쇄(0.0)가 한쪽에서만 일어날 수 있습니다. 그래서 법칙 밖 하류 연산의 수가 L2와 KA에서 조금 다릅니다. 도함수 값 자체는 비례합니다(최대 상대 편차 1.8e-14 / 8.5e-15 / 5.5e-14 / 2.3e-13).

### 2.2 새 조건 4 (구속; 줄마다 옛 조건 4와의 관계를 적음)

1. primal: 4상태 × 2도로에서 ttt·blocks·vehicles·speeds 모든 리프의 hex가 L2 = KA = L1입니다. (그대로)
2. FW_W: 세 벌 모두 도함수 열 0이고, FW_W Trace `result()` 키 전부가 L2 = KA입니다. (그대로)
3. FW_E 사건 수: `event_counts`, `max_tangent_entries`, `exact_tie_axes`, `discrete_dependent_axes`가 L2 = KA이고, 법칙의 탄젠트 평가 횟수 n이 n_L2 = n_KA입니다. (그대로)
4. FW_E 도함수 비례: 모든 도함수 리프에서 \|t_L2 − κ·t_KA\| ≤ 1e-9·max(\|t_L2\|, \|κ·t_KA\|) + 1e-12입니다. κ = 1.1924542785990433, 즉 상대 1e-9입니다. (그대로)
5. 상태마다 0이 아닌 FW_E 도함수가 1개 이상이고, L2 ≠ L1입니다. (그대로)
6. **삭제**: `operations`·`tangent_entries`의 L2 − KA = n × d1 등식은 더 이상 구속이 아닙니다. 대신 상태마다 다음을 **보고**합니다.
   - ΔOps, ΔEntries, n × d1, 편차
   - 같은 프로세스의 d1(옛 기준대로, 38이 아니면 적음)
   - 상쇄 진단(버린 0 항목 수, 접힘 수; 최소 900·6300)
   - 첫 실행 값(위 표, 편차 ≤ 20 연산 / ≤ 336 항목)도 함께 적습니다.

- **약해진 점(공개)**
  - 법칙 호출 횟수는 3번(n 동일)이 계속 잡습니다. 값의 비례는 4번이 1e-9로 잡습니다.
  - 잃는 것은 법칙 밖 하류 산술의 **연산 수**가 정확히 같은지에 대한 장부 검사입니다.
- **적용 범위**: GB-8(`PREDECL:296-299`)은 "통과 조건 = O-5의 1–4 그대로"라고 참조합니다. 그래서 이 새 조건 4는 GB-8에도 적용됩니다. GB-8 실행 전에 고정하는 것입니다.

## 3. O-7: 기준 그대로, 문서만 보완

- 기준(`PREDECL:215`, "범위·건수·남은 곳의 사유")은 바꾸지 않습니다.
- `diagnostics/sdmpc_n31_20260924/REPIN_V3C3_REPORT.md` §5의 모든 행에 건수(파일 수·줄 수)를 채웁니다.
- 건수는 최종 K7 트리(보고서 자신 포함)에서 `git grep`으로 잽니다(`vendor` 제외). 정확한 명령도 함께 적습니다.

## 4. O-8: 기준 그대로, GWT6 정리

- 기준(`PREDECL:217-222`; GWT6은 HEAD·status·최신 mtime이 관문 전후 불변)은 바꾸지 않습니다.
- **떠도는 파일** [실행·읽음]
  - `D:/VISSIM-merge/sim3-n31-v3c3-k6gate/evaluation/controllers/__pycache__/control_area_objective.cpython-312.pyc`
  - 60,292 B, mtime 17:04:51, sha256 `6a7cdabddf0b174ca90897b085fae52a114a8c54904c2d5ac6d39f23a63f0d01`
  - 머리: magic `cb0d0d0a`(Python 3.12), flags 0, 원본 mtime 2026-10-01 11:17:30, 원본 크기 47,236 B. 이것은 **GWT6 자신의** `control_area_objective.py`(mtime 11:17:30.98, 47,236 B)와 같고, GWT7 사본(mtime 16:50:14)과는 다릅니다.
  - `evaluation`·`evaluation/controllers`에는 `__init__.py`가 없습니다(namespace 패키지). 그래서 이 모듈 하나만 컴파일된 것과 맞습니다.
- **출처 (가능성 높음)** [읽음: 이 세션의 워크플로 기록]
  - 워크플로 `wf_f7f340b8-6ad`(SC1001-EB opt1 설계·검토, GWT6을 읽기용으로 씀), 에이전트 `a960e462f93b6b664`
  - 17:04:49 KST에 `cd D:/VISSIM-merge/sim3-n31-v3c3-k6gate && python - <<EOF … sys.path.insert(0,'.') … from evaluation.controllers.control_area_objective import physical_membership_from_ledger …`를 **`-B` 없이** 실행했습니다.
  - 2초 뒤 파일이 생겼습니다. 관문 프로세스가 아닙니다.
- **처리**: sha와 머리를 기록하고, 사본 하나를 `reports/k7/fix/o8/`에 증거로 남긴 뒤 GWT6에서 지웁니다.
- **같은 출처의 다른 무시 항목**
  - `evaluation/controllers/__tangentcache__/` 88개(16:28:57–16:29:03)는 관문 전(16:48 `o8_before`)부터 있었습니다.
  - 같은 워크플로의 에이전트 `ac30b914ef55da5cb`가 16:28:54에 GWT6 아래에서 `f2_run.py` 작업을 돌렸습니다.
  - 이것이 남으면 GWT6 `status --ignored`가 1줄입니다. 그래서 지우지 않고 `reports/k7/fix/o8/moved_k6gate_tangentcache/`로 **옮기고** 목록(경로·크기·sha256)을 남깁니다.
  - 목표는 GWT6 `status --porcelain --ignored` **0줄**입니다.
- **재실행 때 기준**: O-8 GWT6 판정은 재실행의 새 전 스냅샷(0줄 예상)과 후 스냅샷을 비교합니다. 재실행 중 다른 워크플로가 GWT6에서 `-B` 없이 import하면 같은 실패가 다시 납니다. 메인 세션이 그동안 GWT6 사용을 막거나 `-B`와 바깥 캐시를 쓰게 해야 합니다 [추론].

## 5. 재실행 규칙 (그대로 적용)

- 수정 커밋이 생기므로 `PREDECL:56`(O-0)에 따라 **O-1…O-8을 새 HEAD에서 처음부터 다시** 돌립니다. 새 HEAD가 K7입니다(`PREDECL` §0 정의).
- 커밋 규칙(O-0)은 그대로입니다: W에서만, 명시 경로, Ming2you 신원, `Co-Authored-By` 줄, `--renormalize` 금지. 수정 커밋은 O-3 수정과 O-7 보고 보완을 따로 합니다.
- 재실행에서 바뀌는 판정은 이 문서 §1.4(DA-2 `unsignalized_turns`와 하류 기대값)와 §2.2(O-5 조건 4)뿐입니다. 나머지 O 기준은 그대로입니다.
- O-0의 s53 보류(v3c3 s53 완료 뒤 GB-1 s53 PASS와 재추출 바이트 동일)는 그대로입니다.
- 모든 O가 (수정된 기준으로) 통과한 뒤에만 `git -C W push -u origin claude/repin-v3c3-20261001`을 합니다. 그 전에는 푸시·동결·발사를 하지 않습니다(O-9).

## 6. 이 문서를 쓰며 한 일 (공개)

- **[실행]**
  - W·GWT7 HEAD와 `status --ignored` 줄 수
  - 사전 선언과 관문 보고 sha256
  - K6 v3c1 표 blob id·sha256·크기
  - v3c1 대 K7 표 키별 비교: 22개 공통 행은 `validation` 밖에서 같음, 그 밖 차이는 `generated`·`network`·`inputs`·`not_included_fzp_validation`뿐
  - GWT6 pyc sha·머리 해독, 원본 3벌 mtime·크기
  - GWT6 `status --ignored`(2줄), 실행 중 프로세스 중 GWT6 명령줄 0개
- **[읽음]**: 사전 선언 전체, `K7_OFFLINE_GATES.md`, `gates/o3/o3_content.json`, `gates/o5/out/*`, `gates/o8_{before,after}.json`, 생성기·설치기 코드, 이 세션 워크플로 기록(`wf_f7f340b8-6ad`의 GWT6 명령)
- **하지 않은 것**: 코드·표·git 쓰기(이 문서 고정 전), 관문 재실행, VISSIM 시작·종료, 금지 시험, s37/59/61/67 열람
