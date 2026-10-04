# 도시 묶음 2 — 단계 3c 보고 (C6 레버 (a)(b) 적용 + G-ID (d)·G-C6 재관문)

- 작성: 2026-09-30 15:25 시작 → 20:45 완료.
- 사용자 결정(2026-09-30) 가운데 이 단계 몫: 2번 "기록·시간 정리 전부 적용" 중 C6 레버 (a) inpx의 links/signalHeads 부분만 파싱, (b) 같은 sha로 핀된 T−150 프레임 재검증 생략. 단계 3의 상수 코드화와 수정 단계의 C3 결정 기록 v2는 **그대로 유지**했습니다. 1번(C3 v2 제안)·3번(단계 8·9 보류)은 이 단계에서 건드리지 않았습니다.
- 계획: `B/BATCH2_PLAN.md` §4.2(C6), §6.1 (d), §6.9(G-C6-0~4), `B/impl/STAGE3.md` §2·§3·§7-1, `B/impl/STAGE3-7_FIX.md`.
- 대상 트리 W = `D:/VISSIM-merge/sim3-n31-urban-b2` (브랜치 `claude/urban-batch2-20260928`, HEAD `cf3ce37`). **커밋·push 없음**, 변경은 작업 트리에만 있습니다.
  - 시작 diff sha `1f33be50a082c184…` (= STAGE3-7_FIX 최종, 어댑터 `b06aa24f…`)
  - **최종 diff sha `a2dbc0e8b5dcdc013ec2eb7f2b1ce628aaf0acf23e9603e09c95837b1b6e9ea0`** (어댑터 `b06aa24f…` 그대로). 두 관문 대기열 모두 BEGIN = ALLDONE = 이 값입니다.
- 표기: **[실행]** 이번에 직접 돌리거나 계산한 값 / **[읽음]** 파일에서 읽은 값 / **[추론]** 직접 증거 없이 끌어낸 판단.
- 약어: B = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/urban-b2`, S3c = `B/impl/stage3c`, **R3d** = `S3c/run3d`(주 관문 대기열, PYTHONHASHSEED=0), **R3c** = `S3c/run3c`(같은 대기열의 첫 실행, 해시 시드 미지정 — §4), R3 = `B/impl/stage3/run3`(단계 3, 모니터 v2 참조), H = `B/harness`, SM = `W/evaluation/controllers/starvation_monitor.py`, T2 = `W/diagnostics/sdmpc_n31_20260924/tests/test_n31_urban_batch2.py`, oc = `W/evaluation/controllers/obs150_contract.py`. 줄 번호는 최종 트리 기준입니다.

---

## 0. 결론

**G-ID (d)는 통과했습니다. 멈춤 규칙에 걸린 것은 없습니다(stop=false).** 두 레버를 SM에만 넣었고(스키마 v3), 판정값(그룹·flag·카운트·스트릭·경보·경계 행)은 모든 비교 대상에서 v2와 같습니다.

| 항목 | 결과 | 절 |
|---|---|---|
| 레버 (a) links/signalHeads만 파싱 | 적용. 파일을 한 번 읽고 두 요소의 바이트 구간만 파싱합니다. 바이트가 "구간 파싱 = 전체 파싱"을 스스로 보여 주지 못하면 전체 파싱으로 돌아가고 이유를 기록합니다. 핀된 망과 세 런 망(모두 `be0075bf`)에서 구간 파싱 = 전체 파싱(그룹 105개 순서 포함, 위상 전부) | §2.1, §3 |
| 레버 (b) T−150 프레임 행 재검증 생략 | 적용. 같은 번들의 derived 문서가 같은 `frame_previous_sha256`을 적고 있을 때만 생략하고, 바이트 sha 대조는 늘 합니다. 증명이 없으면 v2와 같은 전체 검증(fail closed) | §2.2, §3 |
| 유지한 것 | 상수 코드화(단계 3), C3 결정 기록 v2(HSC·SHG·RD), 어댑터. 트리 차이가 SM·T2 두 파일뿐임을 sha로 확인 | §2.3 |
| T2 | **Ran 101, OK** (95 + 새 6, 기존 2개를 v3로 갱신) | §3 |
| 스위트 40실행 | 수정 단계(`stage7fix/run/suites`) 대비 **회귀 0**, 개선 0 (R3d·R3c 모두) | §3 |
| **G-ID (d) (a)** R-obs-b 61 | **61/61 MRS compare IDENTICAL**. 키 없는 단계 1 재생과 action JSON 차이 = C6 블록 61·provenance 610·벽시계 183, **그 밖 0**. stdout 차이는 `"starvation"` 필드뿐 | §5.1 |
| **G-ID (d) (c)** SDMPC 5 | **5/5 IDENTICAL**(5검사 모두 ok). 녹색·offset·선택/유지 목적값·tangent 계수가 기록과 같음. 키 없는 재생과 차이 "그 밖 0", csv·stderr 바이트 같음 | §5.1 |
| G-C6-1 | 블록 flag 행 vs 독립 재계산 불일치 0(R-obs-b 50행, SDMPC 27행), flag 집합 66/66 같음, 궤적 12,810행 불일치 0, `c6_dryrun` 13/13 | §5.2 |
| G-C6-1b | 격자 결과가 단계 3과 같음. 선택 tol 1.0 · M 8 (S1 첫 경보 4,650 s, S0e 0건) | §5.3 |
| G-C6-2 | 두 런 모두 메모리 = 파일 = 독립 연쇄 | §5.4 |
| **G-C6-3 크기** | 결정별 **61/61 ≤ 1 %** (평균 0.838 %, 최대 0.965 % = T1, 여유 96 B). SDMPC 블록 5.4–7.95 kB(0.01 %) | §5.5 |
| **G-C6-3 시간** | 결정별 **1 % 초과 0/61**(R3d 최대 0.80 %, R3c 최대 0.97 %), 평균 0.58 %(R3d)·0.64 %(R3c). 교대 10쌍: R3c −0.83 %, **R3d +1.33 %**(다른 워크플로의 VISSIM 4개가 돌던 부하, 쌍 표준편차 2.9 %), 20쌍 합산 +0.25 %(표준오차 0.58 %). 같은 프로세스 교대 비교에서 v3 모니터 시간 = v2의 **0.72–0.79배** | §5.5 |
| G-C6-4 | PASS. A/B의 csv 바이트·제어·목적값(483.34965062709864 / 484.0576866684797)·tangent 계수 같음, 차이는 C6·이전 action 핀 3·provenance·시간·토큰뿐, A가 스트릭을 이어 받음 | §5.6 |
| v2 → v3 블록 동일성 | R-obs-b 61/61, SDMPC 5/5, G-C6-4 A/B, 궤적 2런×61상태(모든 그룹 세부값 12,810행): flag 행·경계 행·counts·streaks·alarms·prior 같음. 상수 차이는 정확히 두 코드, 입력 차이는 `frame_previous_check` 추가뿐 | §5.7 |
| 해시 시드 | R3d는 PYTHONHASHSEED=0(환경 탐침으로 확인). R3c(시드 무작위)와 R3d의 88개 action JSON 비교 "그 밖 0", 블록 같음, csv 같음 | §4 |

**판단이 필요한 점 하나**: 교대 쌍 기준은 R3d에서 +1.33 %로 글자 그대로는 1 %를 넘습니다. 이 구간에는 다른 워크플로의 VISSIM 4개와 python 5–6개가 돌았고(CPU 평균 44–49 %), 쌍 차이 범위가 −2.35~+7.47 %라 1 % 효과를 가를 수 없는 잡음입니다. 결정별·평균 기준과 같은 프로세스 교대 비교는 모두 통과입니다. 엄밀히 닫으려면 조용한 기계에서 교대 쌍만 다시 재면 됩니다(§8-1).

---

## 1. 시작 상태와 재사용 [실행]

- 시작 트리: `_prov.tree_provenance` diff sha `1f33be50…` = STAGE3-7_FIX 최종, 어댑터 `b06aa24f…`, 더러운 항목 40, SM `de4f55f9…`(단계 3 R3 블록의 `module_sha256`과 같음 = 단계 3 이후 무변경), T2 `ace45a22…`.
- 백업: `S3c/starvation_monitor.pre_de4f55f9.py`, `S3c/test_n31_urban_batch2.pre_ace45a22.py`.
- 튜닝(단계 2 관문 튜닝, 무변경 확인): `config_n31_v2_c6.json` `419a499a`, `config_n31_v2_urban_b1_u1u3_c6.json` `fe6b0a50`. 부모 `config_n31_v2.json` `d4327cbf`, `config_n31_v2_urban_b1_u1u3.json` `f137f711`.
- 비교 기준: 키 없음 = 단계 1 재생(`B/impl/stage1/probe/b2_base` 61, `…/sdmpc/b2_*` 5)과 단계 2 같은-호출 키 없음(`B/impl/stage2/run2/sdmpc/off_s1_T3600`, `_T6300`). v1 = 단계 2 블록. **v2 = R3**(같은 상태·같은 튜닝의 단계 3 산출).
- 하네스(무수정): `c6_queue3.py`, `sdmpc_replay.py`, `u40_probe.py`, `c6_two_decision_chain.py`, `c6_chain_inputs3.py`, `c6_independent.py`, `c6_lib.py`, `run_suites.py`, `compare_suites.py`, `c6_prev_reader_audit.py`.
- 하네스(새로, 모두 읽기 전용): `H/c6_profile3c.py`(v2 사본과 v3를 같은 설치·같은 상태에서 교대 호출), `H/c6_analyze3c.py`(`S3c/make_analyze3c.py`가 `c6_analyze3.py`에 패치를 적용해 생성, v2→v3 비교 추가), `H/c6_cross_runs.py`(R3c vs R3d), `H/c6_load_steps.py`(부하 표본과 단계 대응).

## 2. 코드 변경 (SM과 T2만) [실행: 코드, 시험]

### 2.1 레버 (a): inpx에서 `<links>`와 `<signalHeads>`만 파싱

| 파일:줄 | 내용 |
|---|---|
| SM:142-146 | `NETWORK_SECTIONS = ('links', 'signalHeads')`와 구간 태그·XML 선언·인코딩·루트 시작 태그 정규식 |
| SM:240-245 `_open_elements` | 바이트 구간의 열린 요소 수 = `<` 수 − 2 × `</` 수 − `/>` 수 |
| SM:248-292 `_sectioned_root` | 조건이 모두 맞을 때만 두 요소를 각자의 바이트 구간에서 `ET.fromstring`으로 파싱해 합성 루트에 붙입니다. 조건(어긋나면 괄호 속 이유로 `(None, 이유)`): UTF-16 BOM 없음(`utf16`), 선언 인코딩 UTF-8(`encoding`), 파일 어디에도 `<!`, 선언 뒤 `<?` 없음(`markup`: 주석·CDATA·DTD·처리 명령), 루트 시작 태그가 열린 태그이고 `xmlns` 없음(`root`), 두 이름 각각 시작 태그 1개·끝 태그 1개(`tags`), 루트 시작 태그 뒤부터 첫 구간 앞과 두 구간 사이의 열린 요소 0 = 둘 다 루트의 자식이고 겹치지 않음(`depth`), 조각 파싱 오류 없음(`fragment`) |
| SM:295-302 `network_view` | 파일을 **한 번 읽고**(`read_bytes`) 위 함수를 부름. 실패하면 같은 바이트를 전체 파싱(v2와 같은 결과). 반환값에 대체 이유를 더함 |
| SM:554-557 `gather` | 대체 파싱이 일어났을 때만 `inputs.network_parse = 'full:<이유>'` 기록(정상 경로는 상수가 말함) |

- 규칙 함수 `_physical_groups_of_root`(SHO:89-111 이식)와 `_topology_of_root`는 **바꾸지 않았습니다**. 합성 루트의 `./links/link`, `./signalHeads/signalHead`가 전체 파싱과 같은 요소를 같은 순서로 봅니다.
- 한계 [추론]: `_open_elements`는 텍스트나 속성 값에 `/>`가 들어 있으면 틀리게 셉니다. 그러면 깊이 검사가 대개 실패해 전체 파싱으로 돌아가고(시험 `slash_gt_in_a_value`), 중첩을 정확히 상쇄하는 경우만 이론상 빠져나갑니다. Vissim이 쓴 inpx에는 해당이 없고, 쓰는 망은 sha로 핀되어 단위 시험이 동일성을 확인합니다.
- 핀된 v3b 망(`be0075bf…`, 3,149,139 B): `<links>` 846,893–2,460,009 B(51 %), `<signalHeads>` 2,785,237–2,922,028 B, 두 이름 모두 태그 1개, `<!` 0개, `<?` 1개(선언) [실행].
- 비용 [실행, 15:3x 조용한 기계]: v2 `network_view` 0.089–0.119 s → v3 0.070–0.087 s. v3 안에서 검사가 약 11 ms(`<!` 1.4, `<?` 1.7, 태그 정규식 4.9, 깊이 계수 2.8 ms)이고, links 조각 파싱 46 ms가 대부분입니다.

### 2.2 레버 (b): 같은 sha로 핀된 T−150 프레임의 행 재검증 생략

| 파일:줄 | 내용 |
|---|---|
| SM:367-377 `_derived_document` | 결정의 obs150 derived 문서를 **한 번** 읽음(v2도 flag 결정에서 헤드 창 때문에 읽던 파일). 헤드 창과 핀 증명이 같은 읽기를 씀 |
| SM:380-395 `_pin_unproven` | 증명 조건: 문서가 있고 dict(`no_derived`), `inputs.frame_previous_sha256`이 있음(`pin_missing`), 같은 번들 = `sim_sec`·`run_id` 같고 `inputs.raw_sha256` = `oc.canonical_sha256(state.obs150)`(`other_bundle`), 그 sha = 상태의 `frames.previous.sha256`(`pin_differs`) |
| SM:398-412 `_load_pinned_frame` | 증명이 있으면 바이트를 읽어 **sha256을 핀과 대조**하고(다르면 `oc.load_frame`이 계약의 핀 오류를 냄), `oc._read_text`(oc:1109-1113)와 같은 디코딩 뒤 `json.loads`만 함 → `check = 'pin'`. 증명이 없으면 v2와 똑같이 `oc.load_frame`(sha 대조 + `validate_frame`) → `check = 'rows:<이유>'` |
| SM:415-431 `_previous_frame` | 프레임을 읽은 결정에서 `inputs.frame_previous_check` 기록 |
| SM:434-446 `_head_window` | 읽어 둔 문서에서 헤드 창을 꺼냄(`files_read`·`inputs.head_window` 값은 v2와 같음) |
| SM:593-595 `gather` | flag 그룹이 있을 때 derived 문서 → 프레임 → 헤드 창 순서 |

- **왜 안전한가** [읽음 + 추론]
  - `obs150_observation.derive`(obs150_observation.py:681-727)는 `oc.load_bundle(raw)`(:697; oc:1200-1216)로 `frames.previous`를 sha 대조 + `validate_frame`한 뒤, derived 문서 `inputs`에 `raw_sha256 = canonical_sha256(obs)`(:711)와 `frame_previous_sha256`(:716)을 적습니다.
  - 어댑터에서는 `runtime_setup.py:100`이 결정마다 `lane_plant_runtime.observe_state`(lane_plant_runtime.py:130)를 부르고, 그 안에서 `derive`(:148) → `oc.write_derived`(:149)입니다. `write_derived`(oc:1523-1536)는 파일이 이미 있으면 **바이트가 같을 때만** 통과합니다.
  - 그러므로 같은 번들의 derived 문서가 같은 sha를 적고 있고 지금 읽은 바이트가 그 sha이면, 그 바이트는 같은 `time_s`(`sim_sec`에서 정해짐)로 이미 `validate_frame`(oc:1091-1106, 바이트와 `time_s`의 순수 함수)을 통과했습니다.
- **fail closed**: 생략은 긍정 증명이 있을 때만입니다. 증명이 없으면 v2와 같은 전체 검증이 돌고, 행이 계약을 어기면 오류 블록이 됩니다. **sha 대조는 두 경로 모두에서 합니다**(생략하는 것은 행 단위 `validate_frame`뿐).
- 신뢰 가정(한계) [추론]: derived 문서를 누가 손으로 위조하면 행 검증이 빠집니다. 모니터는 v2부터 같은 문서의 헤드 창을 그대로 믿어 왔고, 어댑터 경로에서는 그 문서가 이번 결정의 `derive` 결과와 바이트가 같음이 `write_derived`로 보장됩니다. 시험이 이 의미를 고정합니다(§3).
- 비용 [실행]: R-obs-b T2700 프레임(5,057행, 1.43 MB)에서 읽기 2 ms, sha 4 ms, `json.loads` 13 ms, `validate_frame` 13–31 ms. 생략되는 것은 마지막 항목이고 `canonical_sha256(obs)` 0.6 ms가 더해집니다.

### 2.3 스키마 v3·상수·유지한 것

- SM:75 `SCHEMA = 'urban-starvation-monitor/v3'`(SM 규약: 상수가 바뀌면 스키마가 바뀜). 규칙·네 키·스트릭·경보·표 형식은 v2와 같습니다. 이전 결정의 v2 블록은 `schema_mismatch`로 이어 받지 않습니다.
- 상수(SM:97-116): 단계 3의 짧은 코드 방식을 그대로 두고 `network_parse` 값 `'once'` → `'sections'`, 새 코드 `frame_rows: 'pin'`만 더했습니다. 설명은 `CONSTANT_CODES`(SM:130-137), 모듈 문서의 v3 문단은 SM:36-48입니다.
- 블록 크기 변화 [실행]: v3 − v2 = 결정당 +33~+83 B(평균 +63 B). flag 0 결정은 상수만(+33~43 B, 벽시계 자릿수 차 포함), 프레임을 읽은 결정은 `frame_previous_check` +40 B가 더해집니다.
- **바꾸지 않은 것**: 어댑터(`b06aa24f`), C3 결정 기록 v2(HSC·SHG·RD), 단계 3 상수 코드화, 규칙 함수(`group_flag`·`evaluate`·`watch_windows`·`boundary_rows`·`read_prior`·`scrub`·`stdout_summary`). 키가 없으면 SM은 import되지 않습니다(T2 AST 시험 2개 통과).
- **트리 차이가 SM·T2뿐** [실행]: 현재 트리의 diff 계산에서 SM과 T2만 시작 사본으로 바꿔 넣으면 sha가 정확히 시작값 `1f33be50…`입니다. 새 SM `0696ec95…`, 새 T2 `49130a73…`.
- 줄바꿈: 두 파일 모두 LF(편집 뒤 CR 0 확인). SM은 `S3c/eol_edit.py`(단계 6 도구 복사) + 명세 `S3c/edit_sm.py`로 바꾸고, 줄 길이 정리 세 곳과 T2는 편집 도구로 고친 뒤 CR 수를 다시 셌습니다.

## 3. 시험·스위트 [실행]

`python -B -m unittest test_n31_urban_batch2`(N31/tests, 스레드 1, codex 파이썬 3.12 + review-deps) → **Ran 101, OK**. 스위트 안의 n31_batch2도 101 OK(R3c·R3d).

| 시험 (T2) | 내용 |
|---|---|
| 수정 `test_one_inpx_parse_per_decision` (:932) | inpx를 한 번 읽고 `ET.parse`는 부르지 않으며, 파싱되는 조각은 `<links>`·`<signalHeads>` 두 개, `network_parse` 입력 없음 |
| 수정 스키마 단언 (:998) | `urban-starvation-monitor/v3` |
| 새 `c6_network_variants` (:1025) | 픽스처 망 11가지: 정상 2(`plain`, BOM + UTF-8 선언), 대체 9(주석 속 `<links>`, 처리 명령, 두 번째 `<links>`, 자기 닫힘 `<signalHeads/>`, 중첩 `<links>`, 속성 값 속 `/>`, 루트 xmlns, ISO-8859-1 선언, UTF-16) |
| 새 `test_sectioned_parse_is_the_full_parse` (:1072) | 핀된 v3b 망(실제 계획 + 계획 없음), 가장자리 픽스처, 정상 변형 2개: 구간 루트의 자식이 `links`·`signalHeads`, 그룹(순서 포함)·위상이 전체 파싱과 같고 SHO.physical_groups와도 같음, `network_view` 대체 없음, v3b 105그룹 |
| 새 `test_sectioned_parse_falls_back_when_the_bytes_do_not_prove_it` (:1098) | 대체 9가지 모두 기대 이유, `network_view` = 전체 파싱, 블록 `inputs.network_parse = 'full:<이유>'`, 같은 망인 변형 6개는 정상 블록과 groups·counts·streaks가 같음. 중첩 `<links>`는 전체 파싱이 커넥터를 하나도 못 보므로 검사가 필요함을 보임 |
| 새 `test_rows_are_not_validated_again_when_the_derived_document_proves_the_pin` (:1166) | 증명이 있으면 `validate_frame` 호출 0, `stopped_prev` 3(기대값), `frame_previous_check = 'pin'`, 읽은 파일 3 |
| 새 `test_every_unproven_pin_validates_the_rows` (:1179) | `no_derived`·`pin_missing`·`other_bundle`(run_id, sim_sec, raw_sha256)·`pin_differs` 각각 `validate_frame` 1회, `rows:<이유>`, 같은 `stopped_prev` |
| 새 `test_bytes_that_differ_from_the_pin_fail_in_both_paths` (:1201) | 핀과 다른 바이트는 두 경로 모두 `ObsContractError`(Frame bytes differ from their pin). 폭 6 행 프레임: 증명이 없으면 거부, 있으면 통과(신뢰 가정을 고정) |
| 새 `test_pin_path_decodes_as_the_contract` (:1222) | UTF-8·UTF-8-sig·UTF-16 바이트에서 생략 경로의 결과 = `oc.load_frame` 결과 |

- 스위트 40실행(`H/run_suites.py`, 무수정)을 `H/compare_suites.py`로 수정 단계(`B/impl/stage7fix/run/suites`, 40실행)와 비교: R3d **공통 40, 회귀 0, 개선 0, 사라진 실행 0**(`R3d/suite_compare_vs_fix.json`). R3c도 같고(`R3c/suite_compare_vs_fix.json`), R3c vs R3d도 회귀 0입니다.
- 이전 action 독자 정적 감사(`c6_prev_reader_audit.py`): 독자 17, 접두사 충돌 0, 정확 키 충돌 0, 단계 3과 같은 구성(`R3d/prev_reader_audit.json`).

## 4. 실행 조건 — 대기열 두 번 [실행]

| | R3c | R3d (주) |
|---|---|---|
| 시간 | 15:46 → 17:54 | 17:56 → 20:16 |
| 단계 | 94(단계 3의 93 + 같은 프로세스 v2/v3 교대 프로파일 1) | 96(R3c의 94 + 환경 탐침 2) |
| diff sha BEGIN = ALLDONE | `a2dbc0e8…` | `a2dbc0e8…` |
| PYTHONHASHSEED | **미지정**(무작위) | **0**. 발사 cmd에서 설정했고, 탐침 두 단계가 대기열 자식(`HASHSEED_ENV 0 hash_randomization 0`)과 PowerShell `Start-Process`로 띄운 python(`HASHSEED_PS 0 0`, 재생 ps1 경로)에서 확인 |
| 모든 단계 rc | 0 | 0 |

- **R3c 경위**: 지시의 실행 조건 PYTHONHASHSEED=0을 첫 대기열에 넣지 않았습니다(제 누락). 그래서 같은 대기열을 조건에 맞춘 R3d로 다시 돌렸고, **관문 판정은 R3d로 합니다.** R3c는 보조 반복으로 보고합니다.
- **두 실행 비교**(`H/c6_cross_runs.py`, `S3c/cross_run3c_run3d.json`): R-obs-b 61 + 교대 20 + SDMPC 5 + G-C6-4 2 = 88개 action JSON에서 차이는 C6 벽시계 537, provenance 176, 시간 476, 토큰 126, 이전 핀 5, **그 밖 0**. 모니터 블록은 벽시계 밖에서 88/88 같고, SDMPC·G-C6-4 csv 바이트 7/7 같습니다. 해시 시드는 관측된 어떤 값도 바꾸지 않았습니다.
- 공통: 재생은 한 번에 하나, BELOW_NORMAL, 스레드 1, `NUMBA_CACHE_DIR=C:/Users/TRLAB/AppData/Local/Temp/nbc_b2i`, `PYTHONDONTWRITEBYTECODE=1`, WMI 분리 발사(`S3c/launch_queue3c.cmd`, `S3c/launch_queue3d.cmd`), `H/c6_queue3.py`(단계마다 트리 sha 확인).
- **기계 부하**(15 s 표본 `S3c/load_log.txt`·`S3c/load_log_run3d.txt`, 단계 대응 `R3c/load_steps.json`·`R3d/load_steps.json`): "조용한 기계"는 확보하지 못했습니다. 다른 워크플로(`scratchpad/termcost`, `v_fzp.py`, 다른 곳의 VISSIM 폐루프)는 제가 시작하거나 멈추지 않았습니다.

| 구간 | R3c | R3d |
|---|---|---|
| SDMPC 7 | 조용함(단계 시작 python 1, VISSIM 0) | CPU 평균 45 %, VISSIM 0 → 4 |
| R-obs-b 61 | 17:02 이후 외부 python 1–3(표본은 17:31부터, CPU 약 20 %) | **VISSIM 4·cscript 4 상시**, 외부 python 6, CPU 평균 48.5 % |
| 교대 20 | 외부 python 2–5, CPU 약 15 % | VISSIM 0–4, CPU 평균 44 % |

## 5. 관문 (판정은 R3d, 괄호는 R3c) [실행 `R3d/stage3c_results.json`, `R3c/stage3c_results.json`, 분석 `H/c6_analyze3c.py`]

### 5.1 G-ID (d) = G-C6-0

**(a) R-obs-b 61상태, 기본 튜닝 + C6 키(`419a499a`)** — `R3d/probe/c6_base`

| 검사 | 결과 |
|---|---|
| 종료 / `MRS compare` | 61/61 종료 0, **IDENTICAL 61/61** (R3c 61/61) |
| 키 없는 단계 1 재생과 action JSON 전체 | C6 61, provenance 610, 벽시계 183, 토큰·이전 핀·경로 0, **그 밖 0** (R3c 같음) |
| adapter stdout | 61/61에서 `"starvation"` 필드만 다름(필드 71 B ≤ 512 B, 줄 최대 605 B) |
| 블록 | 오류 0, prior `no_previous_action` 1·`no_monitor_block` 60, flag 합 50, 경보 0, `network_parse` 대체 0, `frame_previous_check` = `pin` 37(프레임을 읽은 결정 전부), 기록 없음 24(flag 0 결정) |

**(c) SDMPC 결정 재생 5개, C6 키** — `R3d/sdmpc/c6_*`

| 상태 | compare | 녹색/offset | 선택 / 유지 목적값 (기록 = 재생) | tangent | 단계 1 키 없음과 차이 | 같은-호출 키 없음(단계 2 `off`)과 차이 | csv·stderr |
|---|---|---|---|---|---|---|---|
| S1 1800 | 5/5 ok | 같음 | 460.9685165323024 / 462.7372813177537 | 같음 | C6 1, prov 10, 시간 36, 토큰 28, **그 밖 0** | – | 바이트 같음 |
| S1 3600 | 5/5 ok | 같음 | 491.4356825691444 / 493.5432636752482 | 같음 | 그 밖 0 | C6 1, prov 10, 시간 37, 토큰 28, **그 밖 0** | 같음 |
| S1 6300 | 5/5 ok | 같음 | 357.44510216515835 / 359.3969080380441 | 같음 | 그 밖 0 | 그 밖 0 | 같음 |
| S0e 1800 | 5/5 ok | 같음 | 468.49466951165346 / 470.22280722558446 | 같음 | 그 밖 0 | – | 같음 |
| S0e 3600 | 5/5 ok | 같음 | 490.13138414502527 / 491.4703575883558 | 같음 | 그 밖 0 | – | 같음 |

- 목적값은 단계 3과 소수 끝자리까지 같습니다(R3c도 같음). 토큰 28(단계 3은 14)은 단계 4~7에서 바뀐 모듈의 `transformed_source_sha256`이 요청·문맥 토큰에 들어간 몫입니다(수정 단계 §4와 같은 부류).
- stdout은 단계 1·`off`와 `"starvation"`·벽시계 밖에서 같습니다.

**판정: G-ID (d) 통과.**

### 5.2 G-C6-1 입력 대조

| 대조 | 범위 | 결과 |
|---|---|---|
| 블록 flag 행 vs 독립 재계산(`H/c6_independent.py`, 모니터·SHO import 안 함) | R-obs-b 61블록 50행 + SDMPC 5블록 27행 | **불일치 0** |
| flag 집합 | 66블록 | 66/66 같음, `counts.groups_flagged` = 행 수 |
| 모듈 `gather(details='all')` vs 독립, 기록 궤적 | S1·S0e 각 61상태 × 105그룹 = 12,810 | **불일치 0** |
| 궤적 설치 cfg vs 어댑터 블록 | SDMPC 5상태 | 그룹 행 불일치 0, `bound_veh` 불일치 0 |
| `B/c6_dryrun.json` | 13 | 13/13 |

- 궤적은 모든 그룹의 세부값을 계산하므로 **122상태 모두에서 T−150 프레임이 생략 경로(`pin`)로 읽혔고**, 그 `stopped_prev`가 v2(전체 검증) 값과 12,810행 모두 같습니다(§5.7).

### 5.3 G-C6-1b

- 격자(M ∈ {8,6,4} × tol ∈ {1,2,4})가 단계 3과 같습니다. M8 tol1: S1 SC109_p3_L173 첫 경보 **4,650 s**, 경보 결정 14, 위상 경보 결정 159. S0e는 SC109 경보 0, 위상 경보 결정 108. 선택 **tol 1.0, M 8**. 하한은 두 튜닝 105그룹 모두 61상태에서 변동 0.

### 5.4 G-C6-2

- S1·S0e 모두 메모리 연쇄 = 파일 연쇄(`read_prior`) = 독립 연쇄, 모든 결정에서 streaks·bound_streaks 같음. 파일 연쇄 prior: `valid` 59, `no_previous_action` 1, `time_mismatch` 1(T=150).

### 5.5 G-C6-3 크기·시간

**크기** (R-obs-b 61, 원 action 바이트, 단계 1 키 없음 대비)

| 지표 | R3d | R3c | 1 % 한도 |
|---|---|---|---|
| 평균 / 최대 증가 | +2,946 B (+0.838 %) / +3,489 B (T3450, 0.961 %) | +2,945 B (0.837 %) / 0.964 % | – |
| 비율 최대 | **0.965 % (T1, +2,684 B / 278,010 B, 여유 96 B)** | 0.964 % (T1) | 61/61 통과 |
| 1 % 초과 | **0/61** | 0/61 | 통과 |
| 교대 쌍(같은 트리 키 없음 대비) | 평균 0.832 %, 최대 0.927 % | 평균 0.832 %, 최대 0.926 % | 통과 |
| stdout 필드 / 줄 | 71 B / ≤ 605 B | 같음 | ≤ 512 B 통과 |
| SDMPC | 블록 5,412–7,950 B(action 57.4–57.8 MB의 0.01 %), stdout 590–592 B | 같음 | 통과 |

- v3가 v2보다 결정당 +33~+83 B 늘어서 T1 여유는 단계 3의 136 B에서 96 B로 줄었습니다.

**시간** (모니터 `elapsed_sec` / 같은 결정의 `decision_wall_sec`)

| 지표 | R3d (부하 큼) | R3c | 판정 |
|---|---|---|---|
| 모니터 시간 평균 / 중앙 / 최대 | 0.174 / 0.176 / 0.234 s | 0.174 / 0.175 / 0.276 s | – |
| 결정 대비 평균 / 최대 | **0.578 % / 0.801 %** | 0.638 % / 0.974 % | 평균 통과 |
| **결정별 1 % 초과** | **0/61** | 0/61 | 통과 |
| flag 0 결정 / flag ≥ 1 결정 평균 | 0.498 % (24개) / 0.630 % (37개) | – | – |
| 시간 분해 평균 (s) | inpx 0.119, 세부 0.031, 이전 action 0.009, 그룹 0.008, 레코드 0.006 | inpx 0.108, 세부 0.043 | – |
| 교대 10쌍 (키 없음/있음, 900–9000 s) | **평균 +1.33 %, 중앙 +1.05 %, 표준편차 2.95 %, 범위 −2.35~+7.47 %** | 평균 −0.83 %, 중앙 −1.12 %, 표준편차 1.65 % | R3c 통과, R3d 글자 그대로 초과(잡음) |
| 20쌍 합산 | 평균 +0.25 %, 중앙 +0.07 %, 표준오차 0.58 % | | 통과 |
| SDMPC 5 | 0.17–0.28 %(모니터 1.0–1.9 s, 대부분 58 MB 이전 action 읽기 0.79–1.62 s) | 0.20–0.29 % | 통과 |

- **같은 프로세스 교대 비교**(`H/c6_profile3c.py`: 한 번 설치한 cfg에서 R-obs-b 12상태마다 v2 사본과 v3를 6회씩 번갈아, 순서도 교대): v3/v2 모니터 시간 = **0.787**(15:43 조용한 기계, `S3c/profile3c_dev`), 0.721(R3c), 0.769(R3d, 상태별 0.67–0.89). 블록은 12/12에서 무시 필드 밖이 같고, 입력 차이는 `frame_previous_check`뿐입니다. 조용한 기계에서 v3는 0.090–0.149 s이고, 원 런 결정 벽시계(17–24 s)의 최대 0.69 %입니다. 부분별로 inpx 0.111 → 0.085 s, flag 결정의 세부 0.040 → 0.028 s입니다.
- **분모에 대한 주의**: 이번 결정 벽시계는 부하 때문에 길었습니다(평균 R3d 30.1 s, R3c 27.1 s, 단계 3 23.3 s). 이번 모니터 시간을 단계 3의 결정 벽시계로 나누면 평균 0.75 %, 1 % 초과가 R3d 3개(최대 1.07 %)·R3c 8개(최대 1.19 %)입니다. 다만 분자는 이번 부하에서 쟀으므로(inpx 0.119 s, 조용할 때 0.085 s) 조건이 섞인 값입니다. 조건을 맞춘 비교는 같은 프로세스 교대(v3 = v2의 0.72–0.79배)입니다 [실행 값, 해석은 추론].
- **판정**: 크기는 결정별 통과. 시간은 결정별·평균 통과, 교대 쌍은 R3c·합산 통과이고 R3d는 부하 잡음 속에서 +1.33 %입니다(쌍 표준편차가 효과 크기의 약 3배). 교대 쌍만의 엄밀한 확인에는 조용한 기계가 필요합니다(§8-1).

### 5.6 G-C6-4 두 결정 연쇄 [실행 `R3d/g_c6_4`]

| 검사 | 결과 |
|---|---|
| A(이전 = C6 켠 3600 재생 산출)·B(이전 = 기록) 각각 vs 기록 3750 | 둘 다 IDENTICAL, `prev_chain/` 파일 불변 |
| A vs B | csv 바이트·제어 7필드·녹색·offset·목적값(483.34965062709864 / 484.0576866684797)·tangent 계수·stderr 같음 |
| A vs B JSON 차이 | C6 63, provenance 2, 시간 31, 토큰 33, **이전 action 핀 3**(`sdmpc_state/previous_application/receipt_sha256`, `joint_leader_selection/price_state/previous_application/receipt_sha256`, `n31_binding/vsl_cohort_initialization/sha256`), **그 밖 0** |
| A 블록 | prior `valid`(3600), 스트릭 = 3600 스트릭 + 1(SC1002_p1_L427, SC1004_p1_L66, SC1004_p2_L66, SC6_p2_L1210018302 = 2) |
| B 블록 | prior `no_monitor_block`, 스트릭 모두 1 |
| stdout | 두 팔의 `"starvation"`이 같고, 그 밖 필드도 같음 |

**판정: 통과**(R3c도 같음). A의 이전 action은 이번 트리(v3)의 3600 산출이라 스키마가 맞아 이어 받습니다.

### 5.7 v2 → v3 블록 동일성 [실행 `c6_analyze3c`의 `v2_v3`, `chains_v2_v3`]

- 비교 규칙(`v2_v3_compare`): config·sim_sec·run_id·interval·prior·prior_valid·정지 기준·counts·boundary_status·streaks·bound_streaks·alarms·bound_alarms·groups(flag 행)·boundary(경계 행)가 **같음**. 상수 차이 = 정확히 `{network_parse: once → sections, frame_rows: 없음 → pin}`. 입력 차이 ⊆ {`frame_previous_check` 추가}이고 프레임을 읽은 결정에만 있음. 스키마 v2 → v3. 그 밖 최상위 차이 없음.

| 대상 | 결과 |
|---|---|
| R-obs-b 61 (R3 v2 블록 대비) | **61/61 같음**. action JSON 전체 차이 C6 698 · provenance 366 · 시간 183 · **그 밖 0** |
| SDMPC 5 | **5/5 같음**, 모두 `pin`. action 전체 차이 C6 11–12 · prov 6 · 시간 32–37 · 토큰 28 · **그 밖 0**, csv·stderr 바이트 같음 |
| G-C6-4 A·B | 2/2 같음 |
| 궤적(모든 그룹 세부값) S1·S0e | 각 61상태 6,405행: **그룹 행(stopped_prev·floor_status·hw_* 포함)·경계 행·skipped·독립 재계산이 모두 같음**, 입력 차이는 `frame_previous_check` 61/61(`pin`) |
| v1(단계 2) → v3 | R-obs-b 61/61, SDMPC 5/5: v3 행 = v1의 flag 1 행, counts·streaks·alarms·prior 같음 |

### 5.8 상태 불변

- `R3d/chain/S1.json` `state_check`: 실제 설치 cfg(S1 3600)와 실제 멤버 탐침으로 `sm.run`, 14개 대상 해시 변화 0, stdout·stderr 0 B, 이전 action sha 불변, 오류 없음, `frame_previous_check = pin`, stdout 요약 71 B.

## 6. provenance와 안전 [실행]

| 항목 | 결과 |
|---|---|
| 트리 | 최종 diff `a2dbc0e8…`, 어댑터 `b06aa24f…`, HEAD `cf3ce37`, 브랜치 그대로, `git status` 40줄(시작과 같음). 변경은 SM·T2(§2.3의 대입 검증) |
| W 부산물 | `__pycache__` 0개. 개발 중 제가 `-B` 없이 한 번 만든 `evaluation/controllers/__pycache__/obs150_contract.cpython-312.pyc`(15:30, git 무시)는 대기열 전에 지웠습니다. `__tangentcache__`에 새 `.mcode` 1개(15:46, 816 kB): 수정 단계가 주석만 고친 어댑터 `b06aa24f`로 SDMPC를 처음 돌려 생긴 변환본이고, git 무시·동결 비교 제외 대상입니다. `diagnostics/head_service_resources_canonical_validation.json`은 스위트의 기존 시험이 다시 쓰고 `run_suites.py`가 HEAD로 되돌린 추적 파일입니다(HEAD 대비 차이 0, diff sha 불변). `.review-fixtures/`(git 무시)는 스위트 픽스처 |
| 금지 대상 새 파일(단계 시작 표지 15:35 이후) | R-obs-b·S1·S0e 런 폴더 0, `sim3-n31-urban` 0, `sim3-n31-v3c1` 0, `D:/VISSIM-merge/frozen` 최상위 새 항목 0 |
| OLD | `sim3-n31-urban` HEAD `cf3ce37`, `git status` 0줄(`--no-optional-locks`로 읽기만) |
| 하지 않은 것 | VISSIM·cscript 시작/종료, 워치독·cscript·ps1 시험(`run_suites.py` 제외 목록 그대로), seed 37·봉인 시드 59/61/67 열기, 단계 8·9, C3 코드 수정, 커밋·push·`--renormalize`, 다른 워크트리·브랜치 조작, 다운로드 |
| 제 프로세스 | 대기열 둘(각자 WMI 분리 발사, 정상 종료), 부하 표본기 둘(`S3c/load_sampler.ps1`·`S3c/load_sampler_run3d.ps1`, 읽기 전용, ALLDONE에서 스스로 종료). 멈추거나 죽인 프로세스 없음 |

## 7. 알려진 비결정성 (`vendor/NumSim-mine/src/models/state.py:1306` 집합 반복 합) — 보고만, 고치지 않음

- 이번 단계의 어떤 action JSON 비교에서도 "그 밖" 차이가 없었습니다: R3d·R3c vs 단계 1 키 없음(61 + SDMPC 5), vs 단계 3 v2(61 + 5), R3c vs R3d(88개, 해시 시드 무작위 vs 0).
- 수정 단계가 본 마지막 자리 차이(`prediction_summary.off_ramp_storage_veh`, T5700)는 u40 포착 필드였고, 이번에는 그 포착을 돌리지 않았습니다. 그래서 "없어졌다"가 아니라 "이번 비교 범위(action JSON)에 드러나지 않았다"입니다 [실행 값, 범위 해석은 추론]. 코드는 건드리지 않았습니다.

## 8. 판단 필요 / 다음으로 넘기는 것

1. **교대 쌍 시간(판단 필요)**: R3d +1.33 %는 VISSIM 4개 부하 속 잡음(쌍 표준편차 2.95 %)이고, R3c −0.83 %, 합산 +0.25 %입니다. 결정별(0/61)·평균(0.58 %)·같은 프로세스 교대(v3 = v2의 0.72–0.79배)는 통과입니다. 엄밀히 닫으려면 조용한 시간에 교대 쌍만 다시 재면 됩니다(20단계 약 11분, `R3d/queue.json`의 `alt_*` 단계 그대로, 트리 무변경).
2. **크기 여유**: 가장 작은 곳은 T1 0.965 %(여유 96 B)입니다. 앞으로 C6 블록에 무엇을 더하면 T1이 먼저 넘습니다. 폐루프 no-control 결정은 워밍업 6개뿐입니다 [읽음 STAGE2 §5.5].
3. **대체 경로는 시험으로만 검증**: 실제 데이터(망 3개, 재생 결정 68개, 궤적 122상태)에서는 `network_parse` 대체 0, `frame_previous_check`는 프레임을 읽은 곳 전부 `pin`이었습니다. `rows:`·`full:` 경로는 T2의 픽스처로만 확인했습니다.
4. **PYTHONHASHSEED 누락(과정 편차)**: 첫 대기열 R3c에 지시된 PYTHONHASHSEED=0을 넣지 않았습니다. 판정은 조건을 맞춘 R3d로 했고, 두 실행의 산출은 벽시계·토큰 밖에서 같습니다(§4). 기존 하네스는 고치지 않았으므로, 다음 단계의 발사 cmd에도 `set PYTHONHASHSEED=0`이 필요합니다(`S3c/launch_queue3d.cmd` 참고).
5. **이월(그대로)**: C6 키 1.0/8/3/3을 후보 config에(단계 9), 동결 전 `__pycache__` 삭제(현재 0), `__tangentcache__` 새 항목 1개(동결 비교 제외 대상). 단계 8(C2 증분)과 9는 사용자 결정대로 C3 v2 뒤로 보류입니다.

## 부록: 산출 파일

- 보고서: `B/impl/STAGE3c_C6_LEVERS.md`(이 문서)
- 코드 백업·편집 도구: `S3c/starvation_monitor.pre_de4f55f9.py`, `S3c/test_n31_urban_batch2.pre_ace45a22.py`, `S3c/eol_edit.py`, `S3c/edit_sm.py`, `S3c/spec_sm.json`
- 시험 로그: `S3c/unittest_b2_dev.txt`(개발 중 T2 101 OK), 스위트 `R3d/suites/tests/*.txt`, `R3c/suites/tests/*.txt`
- 주 대기열 R3d: `R3d/queue.json`, `R3d/queue_done.jsonl`, `R3d/chain.log`, `R3d/logs/`, 발사 `S3c/launch_queue3d.cmd`, 환경 탐침 `S3c/env_probe.ps1`·`S3c/add_env_probe.py`, 결과 `R3d/stage3c_results.json`, 분석 로그 `R3d/analyze3c.log`, 스위트 대조 `R3d/suite_compare_vs_fix.json`·`R3d/suite_compare_vs_run3c.json`, 감사 `R3d/prev_reader_audit.json`, 프로파일 `R3d/profile3c/profile3c.json`, 부하 `S3c/load_log_run3d.txt`·`R3d/load_steps.json`
- 보조 대기열 R3c: 같은 구성(`R3c/…`, `S3c/launch_queue3c.cmd`, `S3c/load_log.txt`, `R3c/load_steps.json`, `R3c/suite_compare_vs_fix.json`)
- 두 실행 비교: `S3c/cross_run3c_run3d.json`
- 조용한 기계 프로파일(개발, 15:43, 해시 시드 미지정의 읽기 전용 측정): `S3c/profile3c_dev/profile3c.json`
- 새 하네스: `H/c6_profile3c.py`, `H/c6_analyze3c.py`(+ 생성 `S3c/make_analyze3c.py`), `H/c6_cross_runs.py`, `H/c6_load_steps.py`, 부하 표본기 `S3c/load_sampler.ps1`·`S3c/load_sampler_run3d.ps1`
- 트리 변경: `W/evaluation/controllers/starvation_monitor.py`(`0696ec95…`), `W/diagnostics/sdmpc_n31_20260924/tests/test_n31_urban_batch2.py`(`49130a73…`)
