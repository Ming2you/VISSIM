# 도시 묶음 2 — 단계 2 보고 (C6 굶김 감시)

- 작성: 2026-09-29 00:17 재개 → 03:55 완료. 전날 밤 22:55에 시작한 분이 세션 한도로 23:06에 끊겼고, 그 부분 결과를 검사한 뒤 이어서 했습니다(§1).
- 계획: `B/BATCH2_PLAN.md` §4.2, §5.1 C6 행, §6.1 (d), §6.9 G-C6-0~4, §10-10, §2 공통 규칙, 부록 C-10·C-11.
- 대상 트리: `D:/VISSIM-merge/sim3-n31-urban-b2` (브랜치 `claude/urban-batch2-20260928`, HEAD `cf3ce37`). 변경은 **커밋하지 않고** 작업 트리에 남겼습니다. push·rebase·다른 브랜치/워크트리 조작은 없습니다.
- 표기: **[실행]** 이번에 직접 돌리거나 계산한 값 / **[읽음]** 파일에서 읽은 값 / **[추론]** 직접 증거 없이 끌어낸 판단.
- 약어: B = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/urban-b2`, S2 = `B/impl/stage2`, R2 = `S2/run2`(이번 판정의 모든 산출물), H = `B/harness`, W = b2 트리, A = `W/evaluation/controllers/vissim_stackelberg_adapter.py`, SM = `W/evaluation/controllers/starvation_monitor.py`, T2 = `W/diagnostics/sdmpc_n31_20260924/tests/test_n31_urban_batch2.py`, S1D = `B/impl/stage1`. 줄 번호는 모두 최종 작업 트리 기준입니다.

---

## 0. 결론

**G-C6-0·1·1b·2·4와 S1 확인은 통과했습니다. 기존 스위트의 새 실패는 0입니다. G-C6-3은 SDMPC 결정에서 통과했지만, no-control(워밍업) 결정에서는 상대 기준 1%를 넘습니다(시간 약 2%, 절대 0.5 s / JSON 크기 +6.8%, 절대 24 kB).** 이 한 가지는 §5.5에 따로 적었습니다. 진단 전용 키라 행동과 무관하므로 멈춤 사유로 보지 않았습니다(stop=false). 사용자 판단이 필요한 항목으로 남깁니다.

| 확인 항목 (계획 위치) | 결과 | 근거 |
|---|---|---|
| 재개 검토 (과업 지시) | 모듈·배선·시험 블록은 검토 뒤 재사용. 결함 둘(공급 창 덮어쓰기, 이전 프레임 부재 시 전체 오류)과 부족 둘(비유한 수, 시간 분해)을 고침. 이전 감사·스모크·탐색 결과는 트리가 달라 판정에 안 씀 | [실행] §1 |
| 모듈·키·배선 (§4.2) | SM 582줄(새 파일), A +25/−2줄. 키 `urban.diagnostics.starvation_monitor` 네 필드 필수·모르는 키 거부. 키가 없으면 import 안 함 | [실행] §2 |
| 초기값 (§10-10) | `floor_tol_s` 1.0, `min_stopped_per_lane` 8, `n_consecutive` 3, `boundary_capacity_bound_k` 3. G-C6-1b가 1.0 / 8을 그대로 고름 | [실행] §2.3, §5.3 |
| 단위 시험 (§5.1 C6 행) | T2 28개 OK (U4-0 14 + C6 14) | [실행] §3 |
| 이전 action 독자 정적 감사 (§4.2 통로 2) | 독자 17곳(모니터 자신 포함). 모두 이름·접두사로만 읽고, `starvation_monitor`와 겹치는 접두사 0, 정확한 이름 충돌 0. 파일 전체를 쓰는 곳은 sha 핀뿐 | [실행] §4 |
| **G-C6-0 = G-ID (d)** (a) R-obs-b 61상태 | 61/61 `MRS compare` IDENTICAL. 키 없는 단계 1 재생과의 JSON 차이는 C6 블록·run_provenance·벽시계뿐. stdout 차이는 `"starvation"` 필드뿐 | [실행] §5.1 |
| **G-C6-0 = G-ID (d)** (c) SDMPC 5결정 | 5/5 IDENTICAL(derived·action_csv·controls·objective·contract), 녹색·offset·목적값·tangent 계수가 기록과 같음. 키 없는 재생과의 차이는 C6 블록·provenance·시간·토큰뿐 | [실행] §5.1 |
| **G-C6-1** 입력 대조 | 어댑터가 낸 블록 66개(SDMPC 5 + R-obs-b 61) × 105그룹과 독립 재계산 불일치 0. 기록 궤적 2런 × 61상태 × 105그룹 불일치 0. `c6_dryrun.json` 13행 전부 일치 | [실행] §5.2 |
| **G-C6-1b** `floor_tol_s` 보정 | {1, 2, 4} 중 최솟값 1.0이 두 조건을 만족: S1 SC109 p3 첫 경보 **4,650 s**(원형과 같음), S0e 0건. M은 8 유지 | [실행] §5.3 |
| **G-C6-2** 스트릭 | 기록 궤적 연쇄를 세 방법(메모리 연쇄, 합성 이전 JSON 파일을 `read_prior`로 읽는 연쇄, 독립 재계산 연쇄)으로 계산해 두 런 모두 모든 결정에서 같음 | [실행] §5.4 |
| **G-C6-3** 시간·크기 | SDMPC: 모니터 1.0–1.9 s = 결정의 0.23–0.34 %, JSON +30.8–31.9 kB(0.053–0.056 %), stdout 필드 71 B. no-control: 0.50 s = 2.25 %(교대 10쌍 평균 +1.7 %), JSON +24 kB(+6.8 %) | [실행] §5.5 |
| **G-C6-4** 두 결정 연쇄 | S1 3600(C6 켬) → 3750. 이전 action을 C6 산출물로 바꾼 팔 A와 기록 팔 B의 action_csv 바이트·제어·목적값·tangent 계수가 같음. 차이는 C6 블록·이전 action sha 핀·시간·토큰뿐. A는 스트릭을 이어 받음(prior valid, 4그룹 스트릭 2) | [실행] §5.6 |
| **S1 확인** (과업 지시) | S1 6300 결정 재생에서 SC109_p3_L173 flag=1(녹색 20.211 s, 정지 15+144 ≥ 24), 행동은 기록과 비트 동일. 기록 궤적 연쇄에서 4,650–5,550 s와 6,450–7,350 s에 경보(스트릭 3–9) | [실행] §6 |
| 상태 불변 (§4.2 통로 3) | 실제 설치 cfg(S1 3600)에서 실제 멤버 판정 함수로 모니터를 돌림. cfg·cfg.network·TrafficState·어댑터·SHO·SAC 등 14개 대상의 정규화 해시 변화 0, stdout·stderr 0바이트 | [실행] §5.7 |
| 기존 스위트 (§5.1 끝) | 단계 1 대비 70개 실행 회귀 0, 단계 0 대비 68개 실행 회귀 0. 생성기 `--check` 15개 모두 0 | [실행] §7 |
| provenance | 판정 산출물 전부가 한 트리 상태: `worktree_diff_sha256` `36ac3916…`, 어댑터 `da469e21…`, 대기열 BEGIN과 ALLDONE이 같음 | [실행] §8 |
| 금지 대상 무변경 | 런 폴더 3곳 새 파일 0, OLD 트리 `git status` 0줄. VISSIM·cscript 시작/종료 없음 | [실행] §8 |

---

## 1. 재개: 남아 있던 것과 처리

전날 밤(22:55–23:06) 결과는 "검사 전에는 믿지 않는 스크래치"로 다뤘습니다.

| 남아 있던 것 | 확인 방법 | 처리 |
|---|---|---|
| SM (untracked, 22:57, 551줄) | 계획 §4.2·code_map §8.2–8.4와 줄 단위 대조, 어댑터 호출 함수(`physical_groups`, `phase_bounds`, `complete_records`, `load_frame`, `_movement_capacity_flow`, `_distribute_lane_group_capacity_to_movements`)의 부작용을 읽음 [읽음] | **재사용 + 수정 4건**(§2.1) |
| A의 C6 배선(작업 트리 diff) | 삽입 위치가 `post_guard_safety_metadata`(A:14089)와 감사 보정 뒤, `decision_wall_sec`(A:14109) 앞인지, 키 없는 stdout dict 순서가 원래와 같은지 확인 | 그대로 재사용 |
| `S2/c6_tests_block.py` → T2 병합본 | 두 파일 차이가 머리말·꼬리뿐임을 `diff`로 확인 | 재사용 + 시험 2개 추가·1개 확장(§3) |
| `H/c6_lib.py`, `H/c6_independent.py`, `H/c6_prev_reader_audit.py` | 코드 검토 | c6_lib·감사 도구 재사용. c6_independent는 공급 창 의미를 규칙 문장대로 고침(§5.2) |
| `S2/prev_reader_audit.json` | provenance가 트리 diff `79fa064c…`(최종 아님) | **판정에 안 씀.** 최종 트리에서 다시 돌림(`R2/prev_reader_audit.json`) |
| `S2/smoke/`(R-obs-b 2700, IDENTICAL), `S2/explore_s1_3600/` | 트리 diff `79fa064c…`, 튜닝이 `extends` 방식 | 참고만. 판정에 안 씀 |
| `S2/tunings/*.json`(`extends` + 메모 키) | 부모와의 차이가 키 하나가 아님 | 쓰지 않고 **부모 바이트 복사 + 키 하나**로 새로 만듦(`S2/tunings_full/`, §2.3) |
| `S2/s1/tests/n31.txt`(중단된 스위트), `S2/suites_stdout.txt`(빈 파일) | 불완전 | 버림. 스위트는 새로 돌림 |

- 첫 대기열 `S2/run`(00:30 시작, diff `524ce8d7…`)은 S1 3600 재생, G-C6-4 두 팔, 궤적 입력까지 돌았습니다. 여기서 G-C6-1이 공급 창 결함(§2.1-1)을 찾았고, 01:04에 제 대기열 프로세스 트리(PID 12084와 자식들)를 멈춘 뒤 고쳤습니다. `S2/run`의 결과는 **판정에 쓰지 않았고** 대조용으로만 남깁니다(`S2/run/chain.log` 마지막 NOTE).
- 판정은 모두 두 번째 대기열 `R2`(01:06–03:31, diff `36ac3916…`)에서 나왔습니다.

---

## 2. 바꾼 것 (작업 트리, 커밋 안 함) [실행: `git status`, `git diff --stat`]

| 파일 | 내용 |
|---|---|
| SM (새 파일, 582줄) | C6 모듈 전체 |
| A | +25/−2줄(단계 1 diff 위에): 설정 검증과 조건부 import(A:13639-13647), 결정 끝 호출(A:14099-14108), stdout 필드(A:14168-14177). 키가 없을 때 코드 경로는 그대로입니다 |
| T2 | C6 시험 14개(§3). U4-0 시험 14개는 단계 1 그대로 |

- `git status` 17줄 = 단계 1의 16줄 + SM. 최종 `worktree_diff_sha256` = `36ac3916007632db503762321002cdec413e56884dd6a15a705644bd715e96d8`, 어댑터 `da469e21…`, SM `4ddb5404…`.

### 2.1 재개 뒤 SM에 고친 것

1. **공급 창 덮어쓰기(결함)** SM:154-194. 한 상류 차로가 시작점이 몇 m 다른 커넥터 둘로 같은 그룹을 먹일 때, 옛 코드는 창 dict를 **덮어써서** 먼저 쓴 구간을 잃었습니다. 결과가 헤드 순서에 따라 달랐습니다.
   - 실제 사례 [실행]: link 387 차로 1 → 10614·10615, link 1220008502 차로 4 → 10544·10545, link 126 차로 1 → 10641·10700. 잃은 구간은 최대 0.53 m였고, 기록 122상태에서 정지 수가 달라진 곳은 없었습니다.
   - 고친 것: 차로별로 구간 목록을 모아 **합집합**을 만들고, 차량은 한 번만 셉니다(`_union`, `watch_windows`, `_count`). 망 v3b의 113그룹 모두에서 독립 구현의 창과 같습니다 [실행].
2. **이전 프레임이 없으면 블록 전체가 오류(결함)** SM:216-231. `frames.previous`가 없으면 `KeyError`로 블록 전체가 `error`가 됐습니다. 이제 `frame_previous: "absent"`, `stopped_prev: null`로 둡니다.
3. **비유한 수** SM:512-525. `scrub`이 비유한 float를 `null`로 바꿉니다. 그래야 action JSON에 `NaN`/`Infinity`가 들어가지 않습니다.
4. **시간 분해** SM:323-406, :555-582. `elapsed_parts_sec`(records / inpx / frame_and_window / groups / boundary / prior)를 기록합니다. G-C6-3 보고용이고 벽시계 값입니다.

### 2.2 모듈 동작 (계획 §4.2 대조) [읽음 SM]

- **설정** `settings()` SM:103-121: 네 키 필수, 모르는 키 거부, `floor_tol_s` ≥ 0 유한수, `min_stopped_per_lane` > 0 유한수, 두 정수 ≥ 1(`bool`·`float` 거부). A:13645-13647이 **결정 계산 전에** 검증하므로, 설정 오류는 다른 키처럼 결정을 실패시킵니다.
- **현시 규칙** `evaluate()` SM:452-509: 녹색 ≤ 하한 + tol **이고** (헤드 차로 + 공급 차로 정지차) ≥ M × 헤드 차로 수이면 스트릭 +1, 아니면 0. 스트릭 ≥ N이면 경보입니다.
  - 정지 = 원 상태 `vehicle_records`의 러너 플래그 `stopped`(기준 `stopped_threshold_kph` 1.0 km/h, 읽기만).
  - 헤드 창 = 헤드 위치 + 0.5 m까지. 공급 창 = 커넥터 한 단계(커넥터 전체) + 상류 링크 300 m.
  - 하한 = `SAC.phase_bounds(net, SC)[p][0]`.
- **경계 규칙** `boundary_rows()` SM:282-320: β > 0인 `boundary_in`/`boundary_out` movement마다 `served / Σ_블록(cap × 녹색 × 150/주기)/3600`을 구합니다. 비율 ≥ 0.95가 k결정 연속이면 경보입니다.
  - served는 `joint_response.final_score.quantities.served_by_movement_veh`입니다. 최종 응답이 없는 결정(no-control)은 `boundary_status: no_final_response`로 둡니다.
- **이전 스트릭** `read_prior()` SM:409-443: 같은 `run_id`(최상위와 블록 모두), `sim_sec = T − 150`(블록과 metadata 모두), 같은 스키마·설정, 이전 블록에 오류 없음일 때만 이어 받습니다. 그 밖에는 사유(`run_id_mismatch`, `time_mismatch`, `config_mismatch`, `previous_error`, `schema_mismatch`, `no_monitor_block`, `unreadable`, `no_previous_action`)를 남기고 1부터 다시 셉니다.
- **출력**: `metadata['starvation_monitor']`에 schema·config·constants·sim_sec·prior·prior_valid·streaks·bound_streaks·alarms·bound_alarms·counts·groups 표·boundary 표·inputs·module_sha256·elapsed를 둡니다. stdout에는 `"starvation": {alarms, bound_alarms, flagged, keys≤10, bound≤10}`를 512바이트 상한으로 넣습니다(SM:532-548).
- **예외를 올리지 않음** SM:555-582. 내부 오류는 `{'error': {type, message≤300}}`로 돌려주고 stdout에는 ASCII 오류 문자열을 넣습니다. 러너 필드 이름(`controller_status`, `decision_wall_sec`)은 대소문자와 관계없이 `runner-field`로 바꿉니다.
- **통로 넷**(C-10) 대응: stdout 상한 512 B, stderr 무출력, 상태 불변(§5.7), 이름 검색 충돌 방지(대소문자 무시). 다음 결정 통로는 §4·§5.6입니다.
- **계획과 다른 점** (보고):
  1. 블록에 계획 목록 밖의 `groups`·`boundary` 표(그룹당 10필드)를 둡니다. G-C6-1이 "어댑터가 낸 정지 수·하한 유무·녹색·경계 비율"을 대조하려면 필요하기 때문입니다. SDMPC 결정에서는 +27 kB(0.05 %)입니다. no-control에서는 §5.5의 크기 초과 원인입니다.
  2. 경보 조건에는 하한 유무를 넣지 않았습니다. 하한 유무는 `floor_status`(applied / resource / no_members / short / waiting / none)로 기록만 합니다. 계획 §4.2 규칙 문장과 code_map §8.3("기록만 하는 항목")을 따랐습니다. SC109_DIAG의 제안 문구("헤드 하한이 없다")와는 다릅니다.
- tangent 워커는 SM을 import하지 않습니다. SM을 이름으로 부르는 런타임 모듈은 A 하나입니다(T2의 정적 시험).

### 2.3 설정 키와 초기값

- 키 `urban.diagnostics.starvation_monitor = {floor_tol_s: 1.0, min_stopped_per_lane: 8, n_consecutive: 3, boundary_capacity_bound_k: 3}` (§10-10).
- 이 단계의 관문 튜닝은 `S2/tunings_full/`에 있습니다 [실행 `H/c6_make_tunings.py`, `S2/tunings_full/tunings_full.json`].
  - `config_n31_v2_c6.json`(`419a499a…`)은 부모 `config_n31_v2.json`(`d4327cbf…`)을 복사하고 이 키 하나만 넣었습니다.
  - `config_n31_v2_urban_b1_u1u3_c6.json`(`fe6b0a50…`)은 부모 `f137f711…`에서 같은 방식으로 만들었습니다.
  - 생성기가 "키를 빼면 부모와 같다"를 단언합니다.
- 추적 config(`config_n31_v2_urban_b2_c6.json` 등)는 계획 §4.8 순서대로 후보 config 단계에서 `make_config_n31.py`로 만듭니다. 이번에는 추적 파일을 늘리지 않았습니다.

---

## 3. 단위 시험 (계획 §5.1 C6 행) [실행]

`python -B -m unittest test_n31_urban_batch2` (cwd `W/diagnostics/sdmpc_n31_20260924/tests`, 스레드 1) → **Ran 28, OK**. 스위트 `n31_batch2`에서도 28 OK입니다(§7).

| 시험 (T2) | 계획 항목 |
|---|---|
| `test_four_keys_required_typed_and_nothing_else` (:500) | 설정 검증(네 키 필수, 타입, 모르는 키 거부, NaN/inf/bool/문자열 거부) |
| `test_imported_only_under_the_key` (:548) | 키 없으면 import 안 함(AST: import가 하나이고 키 조건 안에 있음). SM을 이름으로 부르는 런타임 모듈은 A뿐 |
| `test_outputs_written_only_under_the_settings` (:564) | 두 출력이 `starvation_settings is not None` 안에서만 쓰임, 키 없는 stdout 네 필드 순서 그대로, 호출이 가드 뒤·`decision_wall_sec` 앞 |
| `test_counts_windows_floor_and_boundary_bound` (:599) | 헤드/공급 창 경계값, 이동차 제외, 멤버 판정 함수가 새 빈 dict만 받음, 경계 비율(3블록 녹색), internal 제외 |
| `test_one_upstream_lane_feeding_two_connectors_is_one_union_window` (:619, 재개 추가) | 합집합 창, 헤드 순서 무관, 한 번만 셈 |
| `test_each_condition_alone_resets` (:637) | 녹색 조건·정지 조건 각각이 스트릭을 끊음 |
| `test_valid_prior_continues_the_streaks_to_alarms` (:647) | 합성 이전 JSON(유효) → 스트릭 3, 경보, stdout 키 |
| `test_invalid_priors_restart_at_one` (:659) | `run_id` 다름(문서/블록 각각), `sim_sec` 어긋남(각각), 설정 다름, 이전 오류, 스키마 다름, 블록 없음, 읽기 실패, 파일 없음 |
| `test_boundary_without_a_final_response` (:687) | 최종 응답 없음·served 없음, 계열 없는 제어(0블록 유지), allocation 상한 |
| `test_absent_inputs_degrade_and_the_block_stays_strict_json` (:699, 재개 추가) | 이전 프레임·derived 없음 → 오류 아님, inf → null, `allow_nan=False` 직렬화 |
| `test_runtime_failure_is_returned_not_raised` (:714) | 내부 예외(KeyError, AttributeError)를 돌려줌, 설정 오류는 올림 |
| `test_runner_field_names_never_appear_in_any_case` (:727) | 이름 충돌(대소문자 무시) 없음, 오류 메시지 안의 이름도 바꿈 |
| `test_stdout_summary_is_capped` (:742) | 300경보 × 긴 이름에서도 ≤ 512 B, 앞 키 순서 유지, 긴 한글 오류도 ≤ 512 B이고 ASCII |
| `test_prints_nothing_and_mutates_nothing` (:759) | stdout·stderr 0 B, cfg·state JSON·control·metadata·plan·joint·모듈 데이터의 pickle 동일(재개: 모듈 데이터 추가), 이전 파일 바이트 불변 |

---

## 4. 이전 action 독자 정적 감사 (계획 §4.2 통로 2, G-C6-4 정적 부분) [실행 `R2/prev_reader_audit.json`, 도구 `H/c6_prev_reader_audit.py`]

- 방법: 런타임 소스 173개(`evaluation/**`, `vendor/NumSim-mine/src/**`, 시험 제외)를 AST로 훑습니다.
  - 시작점은 A `main()`의 `args.previous_action_json`·`previous_path`입니다.
  - 인자 전파로 오염된 함수를 따라가 파일을 읽는 곳을 찾고(간선 27), 각 독자가 문서에 접근하는 방식을 모읍니다: 접두사, 정확한 키, 순회, `**` 펼침, 전체 해시.
  - 콜백 하나(HSR `observe(original, …)` = SHO `install`)는 손으로 이었습니다.
- 결과: **독자 17곳, `starvation_monitor`와 겹치는 접두사 0, 정확한 이름 충돌 0**(모니터 자신 제외). 계획이 grep으로 센 14곳은 모두 포함됩니다. 줄 번호는 이번 트리 기준입니다.
- 사람이 판정한 표 [읽음]:

| 독자 (읽는 줄) | 이전 action에서 읽는 것 | 판정 |
|---|---|---|
| SHO `install` :114 (:126) | `{**diagnostics, **metadata}`에서 접두사 `head_discharge_floor_`·`head_candidate_`(:130), 정확한 키(:136-137, :203, :244-247), `head_candidate_end_` 접두사 순회(:140). :192 해시는 헤드·맥락만 대상 | 이름·접두사만 |
| SHO `_install_head_free_service` :361 (:378) | 접두사 `head_free_candidate_end_`(:385), 정확한 키(:396, :415-416). :391 해시는 맥락·계약·커넥터 | 이름·접두사만 |
| HSR `observe` :95 (:118) | 정확한 키(맥락·스냅숏·`head_resource_observed_floor_*`·후보 키), 접두사 `head_candidate_end_`(:133). :122/:143/:151 순회는 **이번** 결정의 metadata. :137 해시는 맥락·계약·커넥터 | 이름·접두사만 |
| `sdmpc.load_prices` :500 (:502, :509, :520) | `metadata.sdmpc_state`, `.applied` 영수증, 영수증 sha | 이름만 + 영수증 핀 |
| `sdmpc.solve` :523 (:550) | `metadata.sdmpc_state.next_central_duals_scaled` | 이름만 |
| `lane_plant_runtime.applied_vsl_from_previous` :613 (:629) | 최상위 `vsl`, `metadata.sim_sec`. 파일 전체 sha(:634)는 provenance 핀 | 이름만 + sha 핀 |
| `area_meter_finalization.configure` :32 (:50) | `diagnostics` 중 접두사 `rw_meter_demand_`·`rw_meter_green_` | metadata 안 읽음 |
| `physical_ramp_branches.read_recorded_control` :281 (:287) | 형제 **CSV**와 그 sha(:302) | metadata 안 읽음 |
| A `control_from_json` :10450 (:10453) | 최상위 제어 필드 + `diagnostics` 통째 | metadata 안 읽음 |
| A `prediction_error_from_previous` :11061 (:11065) | 최상위 `prediction` | metadata 안 읽음 |
| A `load_joint_historical_reference` :13020 (:13026, :13047) | `run_id`(최상위·metadata), `metadata.sim_sec`, 제어 필드, `diagnostics.no_control_*`, JSON·CSV sha 핀(:13025) | 이름만 + sha 핀 |
| A `main` 규칙 분기 :13229 (:13840) | `diagnostics.diagnostic_rule_next_history`(진단 규칙 제어기만) | metadata 안 읽음 |
| A `install_observed_backpressure_price` :1970 (:2036) | 형제 **state** 파일(n31은 모드 꺼짐) | action 문서 안 읽음 |
| A `install_measured_movement_capacity` :4314 (:4377) | 접두사 `sat_est_`(헤드 관측이 꺼진 옛 경로만) | 접두사만 |
| A `_measured_green_sec_by_link` :4721 (:4726) | 옛 경로만(단계 1: n31에서 호출 0) | — |
| A `install_measured_far_reservoir_rates` :8562 (:8646) | 접두사 `far_rate_est_` | 접두사만 |
| SM `read_prior` :409 (:418) | `metadata.starvation_monitor`, `metadata.sim_sec`, `run_provenance.run_id` | 자기 블록 |

- 런타임 호출자가 없는 `network_pressure.compute`(:398)도 확인했습니다. 최상위 `green_times`·`ramp_metering`만 읽습니다 [읽음].
- 결정 안에서 C6 **뒤에** metadata를 읽는 곳도 봤습니다 [읽음]. `_action_csv_metadata`(A:12675)는 `controller_status`·`offset_writer`·`physical_projection_provenance` 등 이름만 읽고, CSV 행 생성 `iter_action_csv_rows`(A:12715, 읽는 줄 :12751-12772)도 `controller_variant`·`suppress_signal_rows` 이름만 읽습니다. `control_to_json_dict`(A:10524)는 `_json_evidence`로 직렬화만 합니다.
- **계획에 없던 통로 하나(기록)**: `decision_budget.check('final_action_validation', final=True)`(A:14116)에서 C6 시간이 마감 검사에 들어갑니다. n31 세 config는 `ignore_wall_time_limits: true`라 이 통로가 닫혀 있습니다 [읽음 config :7697]. 시간 제한을 켠 config에서는 C6의 1–2 s가 마감 여유에서 빠집니다 [추론].

---

## 5. 관문 (계획 §6.9)

모든 관문 산출물은 대기열 `R2` 한 번에서 나왔습니다(96단계, 2.31 h, 한 번에 하나, BELOW_NORMAL, 스레드 1, `NUMBA_CACHE_DIR=…/nbc_b2i`). 분석은 `H/c6_analyze.py` → `R2/stage2_results.json`입니다.

### 5.1 G-C6-0 = G-ID (d) [실행]

**(a) R-obs-b 61상태, 기본 튜닝 + C6 키(`419a499a`)** — `R2/probe/c6_base/`, 대조 `S1D/probe/b2_base/`(단계 1, 키 없음)

| 검사 | 결과 |
|---|---|
| 종료 / `MRS compare`(derived, action_csv, action_controls, objective, action_contract) | 61/61 종료 0, **IDENTICAL 61/61** |
| 키 없는 단계 1 재생과 action JSON 전체 차이(트리·출력 경로 정규화) | C6 키 유무 61, run_provenance 610(어댑터·튜닝·state sha, 튜닝 경로, 실행 지문), 벽시계 183(`decision_wall_sec`, `prediction_wall_sec`, `prediction/wall_sec`). **그 밖 0** |
| adapter stdout | 61/61에서 `"starvation"`을 빼고 경로를 정규화하면 같음(`decision_wall_sec` 제외). 필드 최대 71 B, 줄 최대 601 B |
| 블록 | 오류 0. prior 상태: `no_previous_action` 1(T=1), `no_monitor_block` 60(기록 이전 action에는 블록이 없음). 한 상태 재생이라 스트릭 ≤ 1, 경보 0, flag 합 50 |

**(c) SDMPC 결정 재생 5개, C6 키 켬** — `R2/sdmpc/c6_*`

| 상태 (튜닝) | compare 5검사 | 녹색 / offset | 선택·유지 목적값 (기록 = 재생) | tangent 계수 | 키 없는 재생과 차이 (단계 1 / 같은 호출 `off`) | csv·stderr |
|---|---|---|---|---|---|---|
| S1 1800 (U1+U3 + C6) | 모두 ok | 같음 | 460.9685165323024 / 462.7372813177537 | 같음 | C6 키 1, provenance 10, 시간 36, 토큰 14, **그 밖 0** / – | 단계 1과 바이트 같음 |
| S1 3600 | 모두 ok | 같음 | 491.4356825691444 / 493.5432636752482 | 같음 | 그 밖 0 / C6 1, provenance 8, 시간 37, 토큰 12, **그 밖 0** | 같음 / 같음 |
| S1 6300 | 모두 ok | 같음 | 357.44510216515835 / 359.3969080380441 | 같음 | 그 밖 0 / 그 밖 0 | 같음 / 같음 |
| S0e 1800 (기본 + C6) | 모두 ok | 같음 | 468.49466951165346 / 470.22280722558446 | 같음 | 그 밖 0 / – | 같음 |
| S0e 3600 | 모두 ok | 같음 | 490.13138414502527 / 491.4703575883558 | 같음 | 그 밖 0 / – | 같음 |

- "토큰"은 cfg·응답을 pickle한 바이트의 sha입니다(`request_sha256`, `*_token`, 어댑터 `transformed_source_sha256`). 단계 1 §5.3의 판정대로 트리·튜닝 바이트에 따라 바뀌며 행동이 아닙니다. 이번에는 어댑터 소스가 C6 배선만큼 바뀌어 `transformed_source_sha256`도 달라졌습니다.
- `off`는 같은 호출(`H/alt_replay.ps1`)에 키만 뺀 부모 config로 돌린 재생입니다(`R2/sdmpc/off_s1_T3600`, `_T6300`). 두 팔의 차이에서 호출 방식 차이까지 빠집니다.
- 이번 재생은 모두 `action_contract`도 ok였습니다. 단계 1의 `replay_decision_n31.ps1` 경로에서는 "다름"이었습니다. 이 차이는 비교 호출 경로에서 오는 것입니다. 같은 경로의 키 없는 `off`도 ok이므로 C6와 무관합니다 [실행].
- stdout 줄은 키 없음 484–487 B → 키 있음 584–588 B입니다(필드 71 B).

### 5.2 G-C6-1 입력 대조 [실행]

- **독립 재계산** `H/c6_independent.py`는 모니터·SHO를 import하지 않습니다. 계획 규칙 문장과 `c6_dryrun.py` 방식으로 헤드 그룹 자격(SHO 규칙 재코딩), 헤드·공급 창, 정지 수(T와 T−150 프레임), 녹색, 헤드 하한 키 유무를 다시 셉니다.
  - 재개 때 공급 창 의미를 규칙 문장에 맞췄습니다. 한 차로의 여러 구간은 합집합으로 두고, 차량은 한 번만 세고, 헤드 차로는 공급에서 뺍니다. 옛 사본은 `c6_independent.py.bak_0106`입니다.

| 대조 | 범위 | 결과 |
|---|---|---|
| 어댑터가 실제로 낸 블록 vs 독립 재계산 | SDMPC 재생 5 + R-obs-b 61 = 66블록 × 105그룹 | **불일치 0** (헤드/공급 차로 수, 정지 헤드/공급/T−150, 녹색, 하한 유무) |
| 모듈 `gather`(설치 cfg) vs 독립 재계산, 기록 궤적 | S1·S0e 각 61상태(1–9000 s) × 105그룹 = 12,810 | **불일치 0** (계획 대상 S1 2700–8100, S0e 3600·7650 포함) |
| `B/c6_dryrun.json`(계획의 기준 방식, SC109) vs 궤적 값 | S1 9상태 + S0e 4상태 | **13/13 일치** (p3 녹색, 헤드 정지, 공급 포함 정지, 173 p3 하한 유무, W→E 경계 비율) |
| 궤적 입력(한 번 설치한 cfg) vs 어댑터 블록 | 재생 5상태 | 그룹 행 불일치 0, `bound_veh` 불일치 0 |

- 궤적 입력은 런마다 3600 s 설치 한 번의 cfg를 씁니다(`H/c6_chain_inputs.py`). 현시 하한·멤버 판정·경계 용량은 튜닝으로 정해지기 때문입니다. 마지막 행이 이 가정을 어댑터 블록 5개에서 확인합니다.
- 기록에는 최종 응답(served)이 없어서 궤적의 경계 규칙은 마지막 도함수의 surrogate served를 대리값으로 씁니다(55/61상태, 6상태는 없음). 재생 5상태에서 실제값과의 차이는 최대 0.0–7.9대, 평균 0.0–0.55대입니다 [실행 `chain_vs_adapter`].

### 5.3 G-C6-1b `floor_tol_s` 보정 (C-11) [실행 `R2/stage2_results.json` `chain.grid`]

- 궤적 연쇄(T=1–9000, 61결정)를 격자 M ∈ {8, 6, 4} × tol ∈ {1, 2, 4}로 다시 계산했습니다. 대상은 SC109_p3_L173(원형의 SC109 SG2)입니다.

| 셀 | S1 첫 경보 | S1 경보 결정 수 | S0e 경보 결정 수 | 전 현시 경보 합 (S1 / S0e) |
|---|---|---|---|---|
| **M8 tol1** | **4,650 s** | 14 | **0** | 159 / 108 |
| M8 tol2 | 4,500 s | 20 | 0 | 210 / 152 |
| M8 tol4 | 3,900 s | 32 | 1 (6,750 s) | 263 / 208 |
| M6 tol1 / M4 tol1 | 4,650 s | 14 | 0 | 168·189 / 116·139 |

- 규칙("{1, 2, 4} 중 두 조건을 만족하는 최솟값")에 따라 **tol 1.0, M 8**입니다. §10-10 초기값과 같습니다. C-11이 걱정한 불만족은 생기지 않았습니다. 러너 기준 1.0 km/h와 T 시점 기록으로도 원형(5 km/h, 결정 직후 프레임)과 같은 **4,650 s**가 나왔습니다.
- SC109의 다른 p3 그룹(L1220000704, 동측)은 모든 셀에서 두 런 모두 0입니다.
- 그 밖의 현시 경보(tol 1, M 8)는 원형의 "두 런 공통" 목록과 같은 곳에서 납니다. SC1004_p2_L66(S1 44 / S0e 41), SC1004_p1_L66(17/19), SC16_p3_L1220011200(43/17), SC6_p2_L1210018302(15/14), SC1001_p2_L40(8/8), SC11_p4(11/5)입니다. SC109_p3_L173(14/0)만 S1 전용입니다.

### 5.4 G-C6-2 스트릭 [실행]

- 두 런 각각 기록 궤적 61결정을 세 방법으로 연쇄했습니다.
  1. 메모리 연쇄: `evaluate`에 이전 블록을 prior로 넘김
  2. **파일 연쇄**: 각 블록을 합성 이전 action JSON으로 쓰고 다음 결정이 `read_prior`로 읽음. 어댑터와 같은 경로입니다
  3. 독립 연쇄: 독립 정지 수로 flag를 만들고 단순 누적
- 결과: 두 런 모두 **모든 결정에서 streaks·bound_streaks가 세 방법 모두 같습니다.** 파일 연쇄의 prior 상태는 `no_previous_action` 1, `time_mismatch` 1, `valid` 59입니다.
  - `time_mismatch` 1건은 T=150입니다. 직전 결정이 T=1이라 `T−150`이 아닙니다. 첫 두 결정 사이의 알려진 끊김이고 경보에는 영향이 없습니다.
- 단위 시험(§3)의 합성 prior 사례들과 G-C6-4 팔 A(§5.6)가 이 규칙을 실제 어댑터 경로에서도 보여 줍니다.

### 5.5 G-C6-3 시간·크기 [실행]

- **결정론 계수 먼저**: 결정마다 읽는 파일 5개(inpx 2회 파싱, T−150 프레임, `derived_<T>.json`, 이전 action JSON). 레코드 3,485–5,417대(SDMPC 재생), R-obs-b 약 5천 대입니다.

| 결정 종류 | 모니터 시간 (자기 측정) | 결정 대비 | 교대 벽시계 | action JSON 증가 | stdout 필드 |
|---|---|---|---|---|---|
| SDMPC (재생 5) | 1.02–1.88 s. 이전 JSON(약 58 MB) 읽기 0.53–1.27 s가 대부분, inpx 0.19–0.23 s, 그룹 0.15–0.38 s | **0.23–0.34 %** | 같은 호출 쌍: 6300 +1.2 %(인접), 3600 +4.3 %(비인접). 잡음이 커서 1 %를 가르지 못함(아래) | +30.8–31.9 kB = **0.053–0.056 %** | 71 B |
| no-control (R-obs-b 61) | 평균 0.50 s(0.41–0.69) | **평균 2.25 %, 최대 3.1 %** | 키 끔/켬 교대 10쌍(900–9000 s): **평균 +1.68 %**, 중앙 +1.68 %, 범위 −1.2 ~ +6.4 % | +24.0 kB = **+6.8 %**(기준 약 350 kB) | 71 B |

- 판정
  - **SDMPC 결정: 통과.** 계획 §8.5가 이 관문의 작업량으로 적은 것(58 MB 이전 JSON, 5,391 레코드)이 SDMPC 결정입니다. 자기 측정 0.34 % 이하, 크기 0.056 % 이하, stdout 필드 ≤ 512 B입니다.
  - SDMPC 벽시계 쌍은 1 %를 가를 수 없습니다. 같은 키 없는 결정(S1 3600)이 단계 1에서 577.1 s, 이번 `off`에서 540.4 s로 이미 6.4 % 다릅니다. 그래서 모니터의 자기 측정을 근거로 삼았습니다.
  - **no-control 결정: 상대 기준 1 % 초과.** 시간 +0.5 s(교대 +1.7 %)와 JSON +24 kB(+6.8 %)입니다. 원인은 결정 자체가 짧고(약 22 s) 작기(약 350 kB) 때문입니다. 절대량은 SDMPC 결정보다 작습니다.
  - 폐루프 런에서는 워밍업 6결정(T < 900)이 여기에 해당합니다. 사용자 판단 항목으로 남깁니다(§9-1).

### 5.6 G-C6-4 두 결정 연쇄 [실행 `R2/g_c6_4/`, 도구 `H/c6_two_decision_chain.py` + `H/c6_alt_replay_prev.ps1`]

- 방법
  - `MRS.prepare`로 S1 3750 상태를 복사합니다. 복사본 안에 `prev_chain/`을 만들고 이전 action(3600)을 둡니다.
    - 팔 A는 C6 켠 3600 재생 산출물(`R2/sdmpc/c6_s1_T3600/replay/action_003600.json`, `7d565e21…`)입니다.
    - 팔 B는 기록 3600(`ca02051c…`)입니다.
  - 형제 파일(csv·decision_budget·joint·joint.progress·joint_written·sdmpc_pending)은 두 팔 모두 **기록본**입니다.
  - `.applied` 영수증은 csv 경로 줄 하나만 복사본 csv로 바꿨습니다(UTF-16 BOM 유지). `sdmpc.load_prices`(sdmpc.py:506-515)가 영수증 csv = `previous_path.with_suffix('.csv')`를 요구하기 때문입니다. csv 자체는 기록 파일 그대로입니다. C6 재생 csv와 기록 csv는 바이트가 같습니다.
  - 두 팔은 이전 action JSON 바이트만 다릅니다. 둘 다 C6 켠 U1+U3 튜닝으로 3750을 재생했습니다. 결정 뒤 `prev_chain/`의 모든 파일 sha는 그대로였습니다.

| 검사 | 결과 |
|---|---|
| 두 팔 각각 vs 기록 3750 (`MRS compare` 5검사) | A·B 모두 IDENTICAL |
| A vs B: action_csv 바이트 | 같음 |
| A vs B: 제어 7필드(N_P*, N_UF*, 미터, VSL, 녹색, offset, 배분) | 같음 |
| A vs B: 선택·유지 목적값 | 483.34965062709864 / 484.0576866684797 양쪽 같음 |
| A vs B: tangent 계수(operations, event_counts) | 같음 |
| A vs B: stderr | 같음(406 B, 기존 보정 경고 3줄) |
| A vs B: action JSON 전체 차이 132잎 | C6 블록 63, provenance 2(복사 state sha), 시간 31, 토큰 33, **이전 action 핀 3**(`sdmpc_state/previous_application/receipt_sha256`, `joint_leader_selection/price_state/previous_application/receipt_sha256`, `n31_binding/vsl_cohort_initialization/sha256`), **그 밖 0** |
| A의 C6 블록 | prior `valid`(sim_sec 3600), 스트릭이 3600의 스트릭 + 1로 이어짐(SC1002_p1_L427, SC1004_p1_L66, SC1004_p2_L66, SC6_p2_L1210018302 = 2) |
| B의 C6 블록 | prior `no_monitor_block`, 스트릭 모두 1 |

- 판정: **통과.** C6가 쓴 metadata는 다음 결정의 행동을 바꾸지 않습니다. 차이는 계획이 허용한 이전 action sha 핀·C6 필드와, 단계 1에서 행동이 아님을 보인 시간·토큰뿐입니다. 정적 감사(§4)와 같은 결론입니다.

### 5.7 상태 불변 (§4.2 통로 3, 실제 설치 cfg) [실행 `R2/chain/S1.json` `state_check`]

- S1 3600을 U1+U3 튜닝으로 설치했습니다(`configure_runtime` 직후 정지). 기록 3600 action의 제어·metadata와 기록 3450 이전 action으로 `starvation_monitor.run`을 **어댑터의 실제 멤버 판정 함수**와 함께 돌렸습니다.
- 전후로 14개 대상의 정규화 해시(순환·numpy 처리, 객체는 `vars`)를 비교했습니다. 대상은 `cfg`, `cfg.network`, TrafficState, state JSON, control, metadata, joint, plan, 어댑터 모듈 데이터 전역, 모니터·SHO·SAC·projection_support·obs150_contract 모듈 데이터입니다. **바뀐 것 0**입니다.
- 가로챈 stdout·stderr는 0 B입니다. 이전 action 파일 sha는 그대로였습니다.
- SAC `_native_plan` lru 캐시는 적중만 17 → 34로 늘었고 항목 수는 17로 그대로입니다(순수 메모이제이션).

---

## 6. S1 확인: SC109 p3 잠김 구간 [실행]

- **결정 재생(행동 비트 동일 + flag)**: S1 6300 C6 재생(`R2/sdmpc/c6_s1_T6300`)은 compare 5검사 ok, 녹색·offset·목적값·tangent 계수가 기록과 같습니다. 블록의 `SC109_p3_L173` 행은 다음과 같습니다.
  - 녹색 20.211 s, 하한 20.0, 헤드 3차로, 공급 6차로, 정지 헤드 15 + 공급 144 = 159 ≥ 8 × 3
  - T−150 정지 141, `floor_status` no_members, **flag 1**
  - 한 상태 재생이라 기록 이전 action에 블록이 없어 streak은 1입니다.
- 비교: S1 3600은 녹색 21.914(> 21)라 flag 0이고, S1 1800·S0e 1800·3600은 정지 0–45대, 녹색 40–64 s라 flag 0입니다.
- **기록 궤적 연쇄(tol 1, M 8)의 SC109_p3_L173** — (T, 녹색, 헤드/공급 정지, streak)

| 구간 | 내용 |
|---|---|
| 2,700–4,200 s | 녹색 38 → 21.3 s로 내려감, 공급 정지 44 → 138대, flag 없음 (4,200은 21.345 > 21) |
| 4,350–5,550 s | 녹색 20.006–20.505 s, 정지(헤드+공급) 101–110대, streak 1 → 9, **경보 4,650–5,550 s (7결정)** |
| 5,700 / 6,000 s | 녹색 21.13 / 21.125 s로 끊김(5,850에서 1) |
| 6,150–7,350 s | 녹색 20.0–20.562 s, 정지 91–159대, streak 1 → 9, **경보 6,450–7,350 s (7결정)** |
| 7,500–8,100 s | 녹색 22.9–24.4 s(7,950만 20.0 s, streak 1), 정지 130–159대 |

- S0e는 같은 링크에서(2,700–8,100 s) 녹색 21.3–50.4 s, 공급 정지 0–62대이고, flag가 한 번도 서지 않았습니다(streak 0).
- SC109_DIAG의 "잠김은 3,600~4,500 s에 생겼다"와 맞습니다. 감시는 4,350 s에 조건을 처음 잡고 4,650 s에 경보합니다.
- **경계 규칙 참고**: tol·M과 무관하게 경계 경보가 상시 켜집니다. 최종 응답이 있는 결정 53/55에서 경보가 났고, movement는 S1 35개, S0e 38개입니다. SC109 W→E 비율도 0.99–1.05입니다.
  - code_map §8.6이 예고한 206.53 척도 결함의 표지입니다. C3(U4) 뒤 이 수가 줄어드는지를 보조 지표로 씁니다.
  - stdout `bound` 목록은 이 상태에서 늘 10개로 차며, 필드는 최대 439 B입니다(512 이하) [실행 궤적 재계산].

---

## 7. 기존 스위트 (단계 0·1 대비) [실행 `R2/suites/tests/`, `R2/suites/fixtures/`, 대조 `R2/suite_compare_vs_stage1.json`, `R2/suite_compare_vs_stage0.json`]

- 대기열 안에서 재생이 끝난 뒤 돌렸습니다(`H/run_suites.py`, `H/fixture_suites.py`, 한 번에 하나, 금지 시험 제외). 시작과 끝의 diff sha는 `36ac3916…`로 같습니다.
- **판정: 새 실패·새 오류 0, 통과 수 감소 0.** 단계 1(`S1D/s3`) 대비 공통 70개 실행, 단계 0 대비 공통 68개 실행에서 회귀 0, 개선 0, 사라진 실행 0입니다.

| 스위트 | 단계 1 | 단계 2 |
|---|---|---|
| n31 (12 파일) | 167 OK | 167 OK |
| **n31_batch2** | 14 OK | **28 OK** |
| n31_observe_pipeline / t6_runner / parity / ad_smoke | 4 / 6 / 5 / 8 OK | 같음 |
| tools / obs / obs_head / pyt | 60 / 29 / 31 / 61 | 같음 |
| u40_extra | 11 passed, 3 skipped | 같음 |
| diag11 (한 번에) | 32 failed, 69 passed, 4 skipped, 15 errors | 같음(같은 id) |
| diag11 파일별, extra_known(7 failed, 13 passed, 4 errors) | – | 같음(같은 id) |
| fixture 30실행 | – | 같음 |
| 생성기 `--check` 15개 | 모두 0 | 모두 0 |

- **하네스 사고 하나**: 첫 fixture 실행(`suites_fixtures`)이 추적 파일 diff를 쓰다 MAX_PATH를 넘겨 멈췄습니다. 이 때문에 시험이 다시 쓴 `diagnostics/head_service_resources_canonical_validation.json`(알려진 재작성 파일)이 되돌려지지 않은 채 남았습니다.
  - 대기열이 다음 단계 전에 diff sha 변화를 잡고 멈췄습니다(`TREE_CHANGED`, `R2/chain.log`).
  - 그 diff를 `R2/suites/fx_restore/hsr_canonical_validation.diff`로 남긴 뒤 `git checkout --`으로 되돌렸습니다. diff sha가 `36ac3916…`로 돌아온 것을 확인했습니다.
  - `H/fixture_suites.py`를 "되돌린 뒤 짧은 이름으로 기록"하도록 고치고 fixture를 다시 돌렸습니다(`suites_fixtures2`). 첫 시도 산출물은 `R2/suites/fixtures_attempt1_maxpath/`에 있습니다.
  - 단계 1의 `run_suites.py`에서 고친 것과 같은 종류의 문제입니다.

---

## 8. provenance와 안전 [실행]

- `R2/chain.log`
  - 01:06:19 BEGIN `diff_sha256=36ac3916…` 어댑터 `da469e21`
  - 03:19:28 TREE_CHANGED(§7의 fixture 사고) → 되돌림 → 03:22:11 BEGIN `36ac3916…`
  - 03:31:01 ALLDONE `36ac3916…` (same at BEGIN)
- 대기열 96단계의 기록(`R2/queue_done.jsonl`)은 모두 `36ac3916`입니다. rc≠0은 `suites_fixtures`(하네스 사고) 하나입니다.
- 재생 산출물(SDMPC 요약·G-C6-4 요약·R-obs-b 기록·궤적 입력)의 provenance도 모두 같은 diff sha입니다(`R2/stage2_results.json`).
- 새 파일 0(`find -newer S2/marker_stage2_start`, 22:55 이후, 03:35–03:51 확인):
  - 런 폴더 `sdmpc31_v3b_nc_s31b`(R-obs-b), `sdmpc31_v3b_b1u13_s31`(S1), `sdmpc31_v3b_s31e`(S0e)
  - `frozen/sdmpc31_cf3ce374_202609261037`, `frozen/sdmpc31_886a014a_202609260935`, `frozen/` 최상위
  - OLD `D:/VISSIM-merge/sim3-n31-urban`: `git status` 0줄, HEAD `cf3ce37`
  - `sim3-n31`, `sim3-n31-v3c1`은 전체 `find`가 느려 끝내지 않고 멈췄습니다. 이 두 곳은 어떤 명령에서도 쓰기 대상이 아니었습니다(모든 도구가 `--tree W` 또는 스크래치만 씀) [추론]. 다른 워크플로가 쓰는 트리일 수 있어 새 파일 수로는 판정하지 않았습니다.
- VISSIM·cscript는 시작하지도 죽이지도 않았습니다. 제가 멈춘 프로세스는 제 첫 대기열 트리(PID 12084: 대기열 python, `sdmpc_replay.py`, powershell, 어댑터 python, tangent 워커 3) 하나입니다(01:04, VISSIM·cscript 없음). 워치독·cscript·ps1 시험은 돌리지 않았습니다(`H/run_suites.py` 제외 목록).
- 재생은 한 번에 하나였습니다. 분석(`c6_analyze.py`, 읽기 전용)은 재생 중에 몇 번 돌렸지만, 교대 벽시계 구간(02:59–03:07)과는 겹치지 않았습니다.
- seed 37, RM 팔(v3b/v3c1), 봉인 시드 59/61/67은 열지 않았습니다. 폐루프 런도, 커밋·push도 없습니다.


---

## 9. 다음에 넘기는 것 / 사용자 판단

1. **G-C6-3 no-control 초과(판단 필요).** 워밍업 결정에서 C6는 +0.5 s(약 2 %)와 +24 kB(+6.8 %)입니다. 싸게 줄이는 방법은 둘입니다. 어느 쪽이든 트리 변경이라 G-ID (d)를 다시 받아야 합니다.
   - (a) inpx를 한 번만 파싱하기(모니터 쪽 기하 재사용)
   - (b) `groups`·`boundary` 표를 경보·flag 행으로 줄이기. 이렇게 하면 G-C6-1 대조가 flag 행으로 좁아집니다.
2. **후보 config**(§4.8): `make_config_n31.py`의 batch-2 생성에 C6 키를 §10-10 값(1.0 / 8 / 3 / 3, G-C6-1b 확정)으로 넣습니다. 이번 관문 튜닝(`S2/tunings_full/`)과 같은 내용이어야 합니다.
3. **경계 규칙은 지금 상시 경보입니다**(§6). U4 뒤 경보 수·SC109 W→E 비율이 떨어지는지를 C3 보조 지표로 봅니다(계획 §6.10).
4. **시간 제한 config에서의 마감 통로**(§4 끝). 시간 제한을 켜는 config가 생기면 C6 시간이 마감 검사에 들어갑니다.
5. 한 상태 재생 도구는 여전히 이전 action을 런 폴더에서 읽습니다. 그래서 스트릭 검증은 `H/c6_two_decision_chain.py`(영수증 경로만 바꾼 복사 폴더) 방식으로 합니다.
6. **하네스**: `H/fixture_suites.py`를 고쳤습니다(되돌리기 먼저, 짧은 diff 이름). 새 도구는 `H/c6_queue.py`(대기열, 단계마다 diff sha 검사), `H/c6_two_decision_chain.py`, `H/c6_alt_replay_prev.ps1`, `H/c6_chain_inputs.py`, `H/c6_analyze.py`, `H/c6_make_tunings.py`입니다.

## 부록: 산출 파일

- 보고서: `B/impl/STAGE2.md`
- 판정 대기열: `R2/queue.json`, `R2/queue_done.jsonl`, `R2/chain.log`, `R2/logs/*.txt`, 발사 `S2/launch_queue2.cmd`(WMI로 세션과 분리)
- 결과 모음: `R2/stage2_results.json`(`H/c6_analyze.py`)
- SDMPC 재생: `R2/sdmpc/c6_{s1,s0e}_T*`(+`.summary.json`), 키 없는 같은 호출 `R2/sdmpc/off_s1_T{3600,6300}`
- G-C6-4: `R2/g_c6_4/{A,B}_T3750/`(+`prev_chain/`, `.summary.json`)
- R-obs-b: `R2/probe/c6_base/`(61), 교대 쌍 `R2/probe/alt_off/`, `alt_on/`(각 10)
- 궤적 입력·상태 검사: `R2/chain/S1.json`, `R2/chain/S0e.json`
- 정적 감사: `R2/prev_reader_audit.json`
- 스위트: `R2/suites/tests/`, `R2/suites/fixtures/`, 대조 `R2/suite_compare_vs_stage1.json`, `_vs_stage0.json`, 복구 기록 `R2/suites/fx_restore/`
- 관문 튜닝: `S2/tunings_full/`
- 대체된 첫 대기열(판정에 안 씀): `S2/run/`
