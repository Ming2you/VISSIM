# 도시 묶음 2 — 단계 3~7 수정 보고 (검증자 차단 1건: 시간 관문의 크기 조건)

- 작성: 2026-09-30 12:15 시작 → 15:25 완료.
- 계획: `B/BATCH2_PLAN.md` §2-9(action JSON 크기 1 % 이하), §6.7 (e)(시간 관문), §6.1(G-ID), §6.9 G-C6-3(같은 종류의 no-control 크기 초과를 사용자가 줄이게 한 선례), §7 멈춤 규칙.
- 대상 트리: `D:/VISSIM-merge/sim3-n31-urban-b2` (브랜치 `claude/urban-batch2-20260928`, HEAD `cf3ce37`, 커밋하지 않음).
  - 시작 diff sha `1dd86f3d…`(= STAGE7 최종)
  - 재측정 대기열 diff sha `a2cd02b0f487f5ae…`(어댑터 `5aef72a7…`)
  - 최종 diff sha `1f33be50a082c184…`(어댑터 `b06aa24f…`). 최종 트리는 재측정 트리와 어댑터 주석 두 곳만 다르며, 다리 확인을 따로 했습니다(§6).
- 표기: **[실행]** 이번에 직접 돌리거나 계산한 값 / **[읽음]** 파일에서 읽은 값 / **[추론]** 직접 증거 없이 끌어낸 판단.
- 약어
  - B = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/urban-b2`, F = `B/impl/stage7fix`, H = `B/harness`, W = b2 트리
  - A = `W/evaluation/controllers/vissim_stackelberg_adapter.py`, HSC = `…/head_saturation_capacity.py`, SHG = `…/shared_head_groups.py`, RD = `…/ramp_diverge.py`, T2 = `W/diagnostics/sdmpc_n31_20260924/tests/test_n31_urban_batch2.py`
  - 줄 번호는 최종 트리 기준입니다.
- 팔: **C3** = `c3_c6`(`a335596e`, 단계 7 C3 팔), **U1+U3** = `u13_c6`(`fe6b0a50`, 단계 7 기준 팔). 두 팔 모두 C6 키가 있습니다. 키 없음 G-ID는 `config_n31_v2_urban_b1_u1u3.json`(`f137f711`)과 `config_n31_v2.json`(`d4327cbf`)을 썼습니다.

---

## 0. 결론

**검증자 지적은 실재합니다. 코드를 고치고 다시 쟀습니다. 멈춤 규칙에 걸린 것은 없습니다(stop=false).**

| 항목 | 결과 | 절 |
|---|---|---|
| 지적 확인 [실행] | 단계 7 트리의 C3 결정 기록 세 개(U4 `u4_saturation`, U5 `shared_head_groups`, U6 `ramp_admission`)가 no-control action JSON에 **두 벌** 들어갔습니다: `metadata.projection_diagnostics`와 최상위 `projection_diagnostics`(A:10653의 복사). 들여쓰기·CRLF까지 합쳐 결정당 20.6~21.2 kB(5.5~7.3 %)입니다. 61/61 결정이 1 %를 넘습니다(C3 − U1+U3 전체 차 +5.69~7.40 %). STAGE7 §9.2의 "기록 6.8 kB = 1.9 %, 나머지는 예측 값 자릿수"는 틀린 귀속입니다. | §1 |
| 수정 | 결정 기록 스키마 v2 (1) 결정마다 바뀌는 계수는 `name=value` 한 줄 문자열로 압축, (2) 런 안에서 바뀌지 않는 설치 사실은 `install_sha256_16`(설치 요약의 sha256 앞 16자리)으로 대체, (3) 행·목록은 비어 있지 않을 때만 기록, (4) 최상위 복사본에서 세 기록 제외. 새 config 키는 없고, C3 키가 없으면 출력이 비트 동일합니다. | §2 |
| **크기 재측정 (R-obs-b 61, no-control)** | C3 − U1+U3 전체 차 **평균 +0.739 %, 최대 +0.931 %(T1), 1 % 초과 0/61**. 기록 자체는 평균 2,133 B(0.589 %), 최대 2,511 B(0.869 %, T1). 기록 밖 차이(Q2 권한 기록·헤드 하한 키 등 내용 차이)는 0.06~0.25 %입니다. | §3 |
| 크기 재측정 (SDMPC S1 3600) | 기록 21,182 → 2,157 B. C3 action 58,100,440 → 58,081,398 B. C3 − U1+U3 전체 차는 +0.804 %(내용 차이이며, 기록은 0.004 %) | §3 |
| C3 행동 불변 [실행] | 61상태 포착 필드(β·큐·재고·방류·녹색·예측 요약)가 단계 7 C3 포착과 같습니다(60/61 비트 동일, T5700 예측 요약 한 값만 마지막 자리 8e-15 차이, §4). MRS compare 61/61 IDENTICAL. 수정 전 8상태와 action 전체를 비교하면 차이는 세 기록·provenance·시간뿐("other" 0). SDMPC S1 3600은 녹색·offset·미터·VSL·allocation·N_P*·N_UF*·csv 바이트·tangent 연산/이산 계수가 단계 7과 같습니다("other" 0). | §4 |
| G-ID 재확인 [실행] | (a) 기본 8상태, (b) U1+U3 61상태: 포착 필드 0 차이, IDENTICAL, action 전체 "other" 0. (d) U1+U3+C6 61상태: 필드·C6 블록 동일. (c)+(d) SDMPC S1 3600 U1+U3+C6: 5검사 IDENTICAL, 기록과 녹색·offset 같음, "other" 0. | §5 |
| 단위 시험·스위트 [실행] | T2 **95 OK**(단계 6의 94 + 새 시험 1, 기존 3개 v2로 갱신). 스위트 40실행이 단계 6 대비 회귀 0. | §5 |
| **시간 관문 판정** | 단계 7 트리 기준 **실패(크기)**로 정정합니다(STAGE7.md §0 행·§9.2·§13-11 고침). 수정 트리에서 재측정한 결과는 **통과**입니다. 교대 벽시계(중앙 0.899)와 이산 비교 판정은 그대로입니다. | §7 |
| **C3 묶음 판정** | **불합격 그대로**입니다(전부 아니면 전무). 실패 관문은 G-U5-127, G0 A1, G-v3b (a), G6, 세 경로 다섯 개입니다. 단계 7 트리 기준으로는 시간까지 여섯 개였습니다. | §7 |
| 거부한 항목 | 없음. 검증자 수치와 제 수치의 절대 바이트 차이(371,663 대 374,824 B)는 기준 팔 차이(C6 없음 대 있음)로 설명됩니다. | §8 |

---

## 1. 지적 확인과 원인 [실행]

- 재개 확인: 이 수정의 이전 시도 산출물은 없었습니다(`B/impl`에 `stage7fix` 없음). 시작 트리 diff sha는 `1dd86f3d…`로 STAGE7 최종값과 같았습니다 [실행 `_prov.worktree_diff_sha256`].
- 수정 전 코드로 R-obs-b 8상태(1, 150, 1050, 2700, 4500, 6300, 7650, 9000)의 C3 결정을, T2700의 U1+U3 결정을 재생해 원 action 바이트를 받았습니다(`F/pre/probe/{c3pre,basepre}`, 도구 `H/u40_probe.py` 수정 없음).
- 크기 측정 방법: 어댑터의 쓰기(`json.dumps(..., ensure_ascii=False, indent=2)` + Windows 텍스트 모드 CRLF)를 그대로 재직렬화하면 원 바이트와 **정확히 같습니다**(3개 파일로 확인). 그래서 "기록 바이트"는 파일에서 세 기록을 뺀 재직렬화와의 차로 정확히 셉니다(도구 `H/c7fix_analyze.py` `record_bytes`).

| T2700 (수정 전 v1) | 바이트 |
|---|---|
| U1+U3 + C6 action | 374,824 |
| C3 + C6 action | 396,169 (+5.70 %) |
| 세 기록(두 벌, 들여쓰기·CRLF 포함) | 20,620 = U4 5,162 + U5 6,274 + U6 9,184 |
| 기록 밖 차이 | +725 B (0.19 %) |

- 8상태 v1 기록: 평균 20,839 B(5.50~7.34 %) [실행].
- 단계 7 포착(`R7/capture/{base,c3}`)의 61상태 전체 차는 +5.69~7.40 %(평균 5.93 %)이고, **61/61이 1 %를 넘습니다** [실행].
- 검증자의 371,663 → 393,122 B는 C6 없는 U1+U3 기준으로 보입니다. 키 없는 U1+U3 T2700이 371,727 B입니다(`F/bridge/probe/u1u3post`). 백분율(+5.8 %)과 결론은 같습니다 [실행, 기준 팔 해석은 추론].
- 틀린 귀속의 원인 [실행]: 단계 4~7은 기록 한 벌의 압축 JSON 크기(약 6.6~6.8 kB)만 셌습니다(STAGE4 §2.11, STAGE5:196, STAGE6:183, STAGE7 §9.2).
  - 실제 파일은 A:10653(수정 전 `payload["projection_diagnostics"] = dict(projection_diagnostics)`)이 `metadata.projection_diagnostics`를 최상위로 한 번 더 복사합니다.
  - 들여쓰기(깊이 2~4)와 줄마다 CR도 붙습니다.
  - "예측 값 자릿수"라는 나머지 설명은 틀렸습니다. 기록 밖 차이는 0.06~0.25 %뿐입니다.

## 2. 수정 내용 [실행: 코드, 시험]

### 2.1 코드

| 파일:줄 | 변경 |
|---|---|
| HSC:52-55 | `DIAGNOSTICS_SCHEMA` v1 → **`u4-saturation-diagnostics/v2`** |
| HSC:484-494 | 크기 규칙 주석(검증자 지적, §2-9, 네 가지 규칙) |
| HSC:495-537 | `pack_record` / `unpack_record`: `name=value` 공백 구분 한 줄, float는 repr, None은 `none`, numpy 스칼라는 파이썬 수로 변환. 이름·값에 공백이나 `=`가 있으면 `ValueError` |
| HSC:539-543 | `install_digest`: 정렬 키·압축 구분자의 정규 JSON sha256 앞 16자리 |
| HSC:563 | `install_summary(cfg)`: v1에 있던 설치 사실(표·계약·차로 파일 핀, 기본값, 그룹·구성원 수, 다중 그룹 구성원, 소유자 제외 목록, U4 값을 유지하는 LUR 표지) |
| HSC:583 | `decision_diagnostics` v2: `install_sha256_16`, `final_install`(최종 맵 부류 5개 + other_changed + head_floor_scaled_groups, 압축), `allocation_binding`(reference_binding/entries/source, 압축). 헤드 하한 배율 그룹·다른 최종값 행·구속 movement 이름은 있을 때만 기록 |
| HSC:621 | `record_final_allocation`: 최종 제어의 final_binding/entries를 붙이고, 구속이 있으면 이름을 붙임 |
| SHG:62 | 스키마 **`u5-shared-head-groups-diagnostics/v2`** |
| SHG:766, :786, :791 | `install_summary`(계약·U1 표 핀, 분할 규칙, 부류, 행 모양, off-ramp 구성원, 정적 축소, pre-head, 미결 그룹), `RECORD_COUNTERS`(13개, 순서 고정), `decision_diagnostics` v2: `completeness`, `process_counters`(자체 단언 검사 수·최대 초과·라운드·순차 잔여 등), `delegated`(비율 6자리, 있을 때만), `head_floor_scaled_rows`(있을 때만) |
| RD:37-39, :59 | 모듈 문서 C 항목, 스키마 **`u6-ramp-admission-diagnostics/v2`** |
| RD:672, :690, :709 | `install_summary`(정책·증거 핀·용량·퇴역 movement·W_out 길이/τ/분할/출처·진입 방출·직행 착지·속도 하한), `_initial_items`(저장고와 부류, 링크 합산 경로 부류 계수, 게이트 속도·추가 착지 스텝, 유입 지연, 예약 길이), `decision_diagnostics` v2: `retired_share`, `initial`, `process`, 램프별 `ramps`(압축), `links_outside_route`(있을 때만) |
| A:10653-10660 | `control_to_json_dict`: 최상위 `projection_diagnostics` 복사본에서 세 키를 뺍니다. 셋이 없으면 `dict(...)`와 키·순서·값이 같습니다 |
| A:14239-14241 | 최종 allocation 기록을 `head_saturation_capacity.record_final_allocation` 호출로 바꿈(v1의 중첩 dict 대입 대체) |
| A:14243-14244, :14249-14250 | 주석만 v2 내용으로 고침(최종 트리, §6 다리 확인) |

- **새 스위치 없음.** 세 기록은 이전처럼 C3 뷰가 있을 때만 생깁니다. 키가 없으면 A:10653-10660은 이전 출력과 같습니다. T2 새 시험과 G-ID (a)(b)(c)(d), §5에서 확인했습니다.
- **옛 형식은 그 자리에서 대체했습니다(스키마 v2).** 플래그로 남기지 않았고, 키 없음 경로와 무관한 C3 전용 코드입니다.
- env·`getattr` 게이트도, stdout·stderr 출력도 추가하지 않았습니다. tangent 요청이 실어 나르는 어댑터 전역(`_`+대문자 dict/list/set)도 새로 만들지 않았습니다. 제외 목록은 함수 안 튜플 리터럴입니다.
- AD 규칙: 새 코드는 결정 끝 부모 프로세스에서 primal 계수만 다룹니다(`_primal` 뒤 값, RD:598-617 [읽음]). 추적 경로 밖입니다.

### 2.2 v1에서 v2로: 남긴 것 / 해시로 옮긴 것 / 뺀 것

| 기록 | 결정마다 남김(v2) | 설치 요약 해시로 옮김(재계산 가능) | 뺌 |
|---|---|---|---|
| U4 | 최종 부류 5종, other_changed, 헤드 하한 배율 그룹 수(행은 있을 때), 기준·최종 allocation 구속 수·항목 수·출처(이름은 있을 때) | 표·계약·차로 파일 핀, 기본값 1,850, 그룹 174·구성원 284·기본 87·중앙값 40, 다중 그룹 구성원, 소유자 제외, LUR 표지 | – |
| U5 | 완결성(341 = 277 + 64), 스텝 계수 13종, 위임 비율, 헤드 하한 배율 행(있을 때) | 계약·U1 표 핀, 분할 규칙, 부류 수, 예산 행·구성원·집합·native 행 수, off-ramp 구성원, 정적 축소 구성원 값, pre-head | 결속 그룹 상위 10(관문 아님) |
| U6 | 퇴역 몫, 초기 저장고·부류(램프 몫·정지선·경로 부류 합), 게이트 속도·추가 스텝·유입 지연·예약 길이, 과정 계수, 램프별 요청·용량·재고·진입 여유 구속 초와 최소 진입 여유(G6-8 입력) | 정책, 증거 핀, 용량, W_out 길이·τ·분할·출처, 진입 방출 1 스텝, 직행 착지, 속도 하한 | 링크별 행, 링크 평균 속도, time_sec, 씨앗 덩이 수, 예약 첫/끝 스텝 |

- 뺀 값은 모두 결정 상태에서 결정론적으로 다시 계산됩니다. 포착 하네스(`H/c7_capture.py` 방식)로 재생하면 얻을 수 있습니다 [추론].
- 해시가 정말 런 안에서 일정한지 [실행]: 61결정 모두 같은 세 값 `0d6552d9bf984679 / deb9483f334ac21c / deec9f91b0e8570f`입니다(T2가 `install_digest(install_summary(cfg))`와 같은지도 확인).

### 2.3 시험 (T2) [실행 `F/unittest_b2_final.txt`]

- `test_decision_record_counts_boundary_allocations_and_stays_small`(T2:1449)를 v2로 바꿨습니다. 확인하는 것: 키 집합, 해시 = 재계산, 압축 값, `record_final_allocation`, fixed_fallback 구속 이름, 들여쓴 크기 < 500 B.
- 새 시험 `test_decision_records_are_packed_and_written_once`(T2:1484): 압축 왕복, numpy 스칼라, 거부 6종, 최상위 복사본에서 세 키 제외, 키 없는 입력의 들여쓴 JSON이 `dict(...)`와 바이트 같음.
- `test_finalize_checks_the_runtime_and_records_the_evidence`(T2:1719)에 U5 v2 기록 검사를 더했습니다: 해시, 완결성, 계수 순서, 위임 비율, 크기 < 700 B.
- `test_c_gate_ramp_counters_and_decision_record`(T2:2472)를 U6 v2로 바꿨습니다: 해시, τ, 퇴역 몫, 램프 계수 왕복, A2 없는 결정, 링크 합산, 밖 링크 목록, 크기 < 1,100 B.
- `python -B -m unittest test_n31_urban_batch2` → **Ran 95, OK** (codex 파이썬 3.12 + review-deps, BELOW_NORMAL, 스레드 1).

## 3. 크기 재측정 (계획 §2-9, §6.7 (e)) [실행 `F/an/fix.json` `size`, 도구 `H/c7fix_analyze.py`]

R-obs-b 61 no-control 결정. 두 팔을 같은 수정 트리(`a2cd02b0…`)에서 재생했습니다(`F/run/probe/{c3post,basepost}`). 원 바이트를 셌습니다.

| 지표 (61결정) | 평균 | 최소 | 최대 | > 1 % |
|---|---|---|---|---|
| v1: C3 − U1+U3 전체 차 (단계 7 포착) | +5.93 % | +5.69 % | +7.40 % | 61/61 |
| **v2: C3 − U1+U3 전체 차** | **+0.739 %** | +0.673 % | **+0.931 % (T1)** | **0/61** |
| v2: 세 기록 자체 | 2,133 B (0.589 %) | 2,076 B (0.556 %) | 2,511 B (0.869 %, T1) | 0/61 |
| v2: 기록 밖 차이(내용) | 0.150 % | 0.063 % | 0.245 % | – |

- 큰 쪽 다섯 상태(전체 차 / 기록): T1 0.931 / 0.869 %, T150 0.891 / 0.656 %, T300 0.854 / 0.608 %, T450 0.813 / 0.610 %, T6450 0.794 / 0.591 %.
  - T1은 런의 첫 결정입니다. 이전 action이 없어 `ControlAction.fixed` 대체 allocation(0.5 × 용량)이 기준 제어가 되고, U4 기준 구속 179/259와 이름 10개가 기록에 붙습니다(STAGE4 이후 알려진 합성 대체, 최종 제어 구속은 0).
- 기록 구성(T2700, 한 벌): U4 428 B, U5 580 B, U6 1,077 B. T1은 U4 894 B입니다(구속 이름 목록).
- 최상위 복사본에 남은 기록: 0/61.
- **SDMPC (S1 3600, 58 MB급)**:
  - C3 action 58,100,440 → 58,081,398 B, 기록 21,182 → 2,157 B.
  - 같은 트리의 U1+U3 57,618,197 B 대비 C3 전체 차는 +0.804 %입니다(단계 7 +0.84 %). 이 차이는 후보·응답 기록 같은 내용 차이이고, 기록은 0.004 %입니다.
  - stdout: C3 588 B, U1+U3 587 B(`starvation` 필드 512 B 상한 그대로).
- 판정: 크기 조건(§2-9 1 %)을 no-control 61/61과 SDMPC에서 모두 만족합니다. 기준을 "C3 − U1+U3 전체 파일 차"라는 엄격한 쪽으로 잡아도 통과입니다.
  - 여유가 가장 작은 곳은 T1(0.931 %)입니다. 폐루프에서 no-control 결정은 워밍업 6개뿐입니다 [읽음 STAGE2 §5.5].
- 시간(보조, 판정 아님)
  - no-control 결정 시간 비 C3/U1+U3 중앙 0.952(0.829~1.017) [실행]. 교대가 아니라 C3 61개 → U1+U3 61개 순서로 잰 값입니다.
  - SDMPC S1 3600 한 쌍 553.2 s / 595.3 s = 0.929 ≤ 1.05 [실행].
  - 이번 C3 SDMPC는 단계 7 같은 상태(526.6·533.0 s)보다 약 5 % 느렸습니다. 늘어난 시간은 tangent·PFO 워커 계산에 있습니다(도함수 1의 `tangent_sec` 94.1 → 103.0 s). 그런데 연산 수·이산 비교 수는 같고, 컴파일/적재는 1.55~1.59 s로 같습니다. 그래서 기계 부하 변동으로 봅니다 [실행 값, 해석은 추론].
  - 기록 축소는 결정 끝 직렬화만 줄이므로 계산 경로를 바꾸지 않습니다. 단계 7의 교대 벽시계(중앙 0.899)는 다시 재지 않았습니다.

## 4. C3 행동 불변 [실행 `F/an/fix.json` `c3_same`, `records`, `sdmpc`]

- **61상태 포착 필드**(`u40_probe`, β·movement 메타·q0/o0/inv0·배정·q1/o1/inv1·방류·경로 방류·녹색·예측 요약·off-ramp 직행 몫·링크 큐·경로 귀속)를 단계 7 C3 포착(`R7/capture/c3`, 같은 튜닝 `a335596e`)과 비교했습니다: **60/61 비트 동일.**
  - T5700 한 곳은 `prediction_summary.off_ramp_storage_veh`가 81.96304302572392 대 81.9630430257239입니다(상대 8e-15). 같은 상태의 q1·o1·inv1·방류·녹색은 같습니다.
  - 원인 [읽음]: `vendor/NumSim-mine/src/models/state.py:1306`이 `set(net.off_ramp_storage_link.values())`를 돌며 합합니다. 집합 반복 순서는 프로세스마다 다른 문자열 해시 시드를 따르므로, 요약 합의 마지막 자리가 프로세스마다 달라질 수 있습니다. 이번 수정과 무관하고, 예측 상태가 아니라 보고용 요약입니다 [추론].
- MRS compare 61/61 IDENTICAL, exit 0, 예측 ok 61/61.
- **수정 전 8상태와 action 전체 비교**(경로 정규화 뒤): 차이는 세 기록 52~53경로, provenance 6, 시간·경로 9~10뿐입니다. **"other" 0.**
- **SDMPC S1 3600 C3**(`F/run/sdmpc/c_s1_T3600` 대 `R7/sdmpc/c_s1_T3600`)
  - 녹색·offset·미터·VSL·allocation·N_P*·N_UF*가 같고, csv 바이트가 같습니다.
  - tangent 도함수 2개의 `operations`·`event_counts`가 같습니다.
  - 기록 대비 5검사 패턴도 같습니다(C3 튜닝은 기록된 U1+U3 결정과 다르므로 action_csv·controls·objective DIFFERENT는 단계 7과 같음).
  - action 전체 차이 분류: 세 기록 53, C6 경과 시간 7, provenance 8, 시간 32, 토큰 18(바뀐 모듈의 `transformed_source_sha256`과 그것을 담는 요청·문맥 토큰). **"other" 0.**
- **v2 기록 내용(61결정)**: 세 스키마 모두 v2 61개.
  - U4: 최종 제어 구속 0/61. 기준 구속은 T1의 fixed_fallback 179/259만 있습니다. other_changed 0, 헤드 하한 배율 0.
  - U5: steps 150 61/61, 검사 수 > 0 61/61, 자체 단언 최대 초과 4.44e-16, 순차 잔여 0, 최대 라운드 2.
  - U6: 세 램프 계수 61/61, 진입 여유 구속 초 합 0(G6-8의 "미터 개방에서 0"과 같은 방향), 미해결 0. `links_outside_route`는 34결정에 있습니다.

## 5. G-ID·시험·스위트 재확인 [실행]

| 관문 | 비교 | 결과 |
|---|---|---|
| G-ID (a) 기본 튜닝 `d4327cbf` | R-obs-b 8상태(1…9000) 대 단계 6 `R6/probe/s6_base`(수정 전 트리) | 포착 필드 차이 0, IDENTICAL 8/8, action 전체 "other" 0(provenance 48, 시간·경로 24) |
| G-ID (b) U1+U3 `f137f711` | 61상태 대 단계 6 `s6_u1u3` | 포착 필드 차이 0, IDENTICAL 61/61, action 전체 "other" 0(provenance 366, 시간·경로 183) |
| G-ID (d) U1+U3+C6 `fe6b0a50` | 61상태 대 단계 7 기준 포착 `R7/capture/base` | 필드 차이 0, IDENTICAL 61/61, C6 블록(스키마·계수·flag 행·경계 상태·prior·오류) 61/61 같음. T2700 action 전체를 수정 전과 비교해도 "other" 0 |
| G-ID (c)+(d) SDMPC S1 3600, U1+U3+C6 | 기록과 단계 7 `R7/sdmpc/b_s1_T3600` | 5검사 모두 ok(IDENTICAL), 녹색·offset이 기록과 같음, 단계 7 재생과 제어·csv 바이트·tangent 계수 같음, action 전체 "other" 0(C6 경과 시간 7, provenance 8, 시간 37, 토큰 14 = 어댑터 소스 sha) |
| T2 | – | Ran 95, OK |
| 스위트 40실행 (`H/run_suites.py`, 수정 없음) | 단계 6 스위트(`B/impl/stage6/suites`)와 `H/compare_suites.py` | 공통 40, **회귀 0**, 개선 0, 사라진 실행 0 [`F/an/suite_compare_vs_stage6.json`] |

- 선별 스위트 밖에서 `control_to_json_dict`를 쓰는 시험 3파일도 돌렸습니다(`diagnostics/test_joint_final_output_budget.py`, `test_joint_written_action.py`, `test_native_runtime_reference.py`): 22 실패, 5 통과 [실행 `F/joint_tests.txt`]. 이 실패는 이번 수정과 무관합니다.
  - 다른 PC 경로의 픽스처(`C:\Users\alsrj\…\개포동 test-bed1_n4dr150.sig`, `action_row_iterator_preparation_v1/fixtures/manifest.json`)가 없습니다.
  - 출력 블록을 따로 exec하는 시험에서 `_json_evidence`가 이름공간에 없습니다. 이 참조는 cf3ce37에도 있습니다(`git show cf3ce37:…adapter.py` :14036) [읽음].
  - 이 시험들은 `control_to_json_dict`를 가짜 함수로 바꿔 쓰므로 이번 변경을 지나지 않습니다 [읽음 `test_joint_final_output_budget.py:62`].

## 6. provenance와 안전 [실행]

| 항목 | 결과 |
|---|---|
| 재측정 대기열 | `F/run`(WMI가 아니라 백그라운드 셸, `H/c7_queue.py` 수정 없음): 195단계 모두 rc 0. BEGIN과 ALLDONE의 diff sha가 `a2cd02b0…`로 같음. 다른 워크플로 재생 0, VISSIM 0, cscript 0(단계마다 census) |
| 버린 실행 | 첫 대기열(12:45)은 제가 대기열을 띄운 뒤 `pack_record`의 numpy 방어를 더해 12:49 `TREE_CHANGED`로 멈췄습니다. 그 7상태(`F/run_aborted_1249`)는 쓰지 않았고, 새 폴더에서 처음부터 다시 돌렸습니다 |
| 최종 트리 다리 | 재측정 뒤 어댑터 주석 두 곳(A:14243-14244, :14249-14250)만 고쳤습니다(diff `1f33be50…`, 어댑터 `b06aa24f…`). 다리 확인 [`F/an/bridge.json`]: C3 T1·T2700, U1+U3+C6 T2700, 키 없는 U1+U3 T2700 네 재생이 재측정 트리 결과와 "other" 0, 세 기록 같음, 포착 필드 같음, IDENTICAL(바이트 차 4~6 B는 경로 문자열 `run`↔`bridge`와 시간 자릿수). T2 95 OK |
| 금지 대상 새 파일(12:10 이후) | R-obs-b·S1 런 폴더, `D:/VISSIM-merge/frozen`, `sim3-n31-urban`, `sim3-n31-v3c1`, `sim3-n31`: 모두 0 (15:05, 다리 확인 뒤 15:25 두 번 확인) |
| OLD / v3c1 / W | OLD `sim3-n31-urban` HEAD `cf3ce37`, `git status` 0줄. `sim3-n31-v3c1` HEAD `9ed2ef0`, 브랜치 `claude/repin-v3c1-20260928`, `git status` 0줄(`--no-optional-locks`로 읽기만). W `git status` 40줄(단계 7과 같은 수), `__pycache__` 0 |
| W 부산물 | `__pycache__` 없음. `__tangentcache__`에 새 `.mcode` 3개(바뀐 세 모듈의 변환 소스; 계획 §3대로 b2 트리에만 생기고 동결 비교에서 빠짐). `.review-fixtures/head_44eff729`(스위트 픽스처, git 무시). 둘 다 diff sha에 들어가지 않음(BEGIN = ALLDONE) |
| 원본 보존 | 수정 전 파일 사본 `F/pre/{head_saturation_capacity,shared_head_groups,ramp_diverge,vissim_stackelberg_adapter,test_n31_urban_batch2}.py`, STAGE7 수정 전 `F/STAGE7.md.before_fix` |
| 실행 조건 | 재생은 한 번에 하나, BELOW_NORMAL, 스레드 1, `NUMBA_CACHE_DIR=…/nbc_b2i`, `PYTHONDONTWRITEBYTECODE=1`. 파일 줄 끝은 LF를 유지했습니다(중간에 CRLF로 바뀐 두 파일을 되돌리고 확인) |
| 하지 않은 것 | VISSIM·cscript 시작/종료, 워치독·cscript·ps1 시험, seed 37·RM 팔·봉인 시드 열기, 폐루프 런, 커밋·push, v3c1 브랜치/워크트리 조작 |

## 7. 판정 갱신

| 관문 | 단계 7 보고 | 정정(단계 7 트리) | 수정 트리 재측정 |
|---|---|---|---|
| 시간 (§6.7 (e)) | 통과 | **실패**: 크기 +5.69~7.40 %, 61/61 > 1 % | **통과**: 크기 +0.67~0.93 %, 0/61 > 1 %. 교대 벽시계 0.899와 이산 비교 판정은 그대로 |
| C3 묶음 | 불합격(14개 중 5개 실패) | 불합격(6개 실패) | **불합격(5개 실패: G-U5-127, G0 A1, G-v3b (a), G6, 세 경로)** |

- STAGE7.md는 제자리에서 고쳤습니다: §0 결론 문장, §0 표의 시간 행, §9.2 크기 항목, §13-11.
- 단계 7의 다른 관문 수치는 이번 수정으로 바뀌지 않습니다. 행동이 같기 때문입니다(§4, §5).
- 다만 단계 7 산출물(`R7/capture`의 `pdg_*`, `R7/sdmpc/*` 결정 기록)은 v1 형식입니다. 앞으로 하네스가 v2 기록을 읽으려면 `head_saturation_capacity.unpack_record`로 풀어야 합니다(§9-2).

## 8. 거부·미채택 항목 설명

- 검증자 지적 1건을 그대로 받아들였습니다. 거부한 것은 없습니다.
- 검증자가 제시한 두 길("실패/판단 필요로 기록" 또는 "블록을 줄임") 가운데 **둘 다** 했습니다: 단계 7 트리의 판정은 실패로 정정했고, 사용자의 C6 선례(no-control 초과를 줄이게 함)를 따라 블록을 줄였습니다.
- 판단이 들어간 곳(사용자 확인 권장)
  1. **최상위 복사본 제외(A:10653-10660).** 압축만으로는 T2700에서 +1.23 %라서 부족했습니다 [실행 모의 계산]. 그래서 세 기록을 `metadata.projection_diagnostics` 한 곳에만 두었습니다.
     - 키 없음 경로는 바이트 동일합니다.
     - 최상위 `projection_diagnostics`를 읽는 곳(`scripts/audit_plant_fidelity.py:1599-1609`)은 수치 스칼라만 모읍니다. 세 기록은 dict·문자열이라 원래 대상이 아니었습니다 [읽음].
  2. **판정 기준.** "C3 − U1+U3 전체 파일 차"(내용 차이 포함, 엄격)와 "세 기록 자체" 두 기준을 모두 보고했고, 둘 다 1 % 이하입니다.
  3. **정보 손실.** 설치 사실은 해시로 남아 재계산으로 검증할 수 있습니다. 결속 그룹 상위 10, U6 링크별 행·평균 속도·예약 첫/끝 스텝은 결정 기록에서 뺐습니다(관문 입력 아님, 포착 재생으로 재현 가능).

## 9. 다음 단계로 넘기는 것

1. **단계 8(C2)**: `queue_attribution_route` 요약을 `projection_diagnostics`에 넣을 때도 같은 규칙을 따라야 합니다(압축 합계, 한 벌).
   - 지금 A:10660 제외 목록에는 C3 세 키만 있으므로, 넣으면 최상위에 두 벌로 쓰입니다.
   - C3+C2 후보의 크기는 단계 8에서 61상태로 다시 재야 합니다. T1 여유가 0.069 %p뿐입니다.
2. 하네스: v1 필드를 읽는 도구(`c7_capture.py` `pdg_*`, `c7_sdmpc_an.py` `u4_allocation`/`u5_counters`, `u6_g6.py` `ramps`/`initial`/`process`, `c7_t1.py` `delegated`, `stage4/5_analyze.py`)는 v2 기록에 쓰기 전에 `unpack_record`로 바꿔야 합니다. 단계 7 판정은 v1 산출물로 이미 끝났습니다.
3. 단계 9 후보 config 전 이월 사항(그대로): C6 키 1.0/8/3/3, 동결 전 `__pycache__` 삭제(현재 없음), `__tangentcache__` 새 항목 3개(동결 비교 제외 대상).
4. 선별 스위트 밖의 기존 실패 3파일(§5)은 이번 범위 밖입니다.

## 부록: 산출 파일

- 보고서: `B/impl/STAGE3-7_FIX.md`(이 문서), 정정한 `B/impl/STAGE7.md`(원본 `F/STAGE7.md.before_fix`)
- 수정 전 재생: `F/pre/probe/{c3pre,basepre}/T*.{json,action.json.gz}`, `F/pre/chain.log`
- 재측정 대기열: `F/run/{queue.json,chain.log,queue_done.jsonl,logs/}`, 산출 `F/run/probe/{c3post,basepost,u1u3post,defpost}/`, `F/run/sdmpc/{c_s1_T3600,b_s1_T3600}{,.summary.json}`, `F/run/suites/`
- 다리 확인: `F/bridge/`, `F/an/bridge.json`
- 분석: `F/an/fix.json`, `F/an/fix_stdout.txt`, `F/an/suite_compare_vs_stage6.json`, 시험 로그 `F/unittest_b2_final.txt`, `F/joint_tests.txt`
- 새 도구(모두 스크래치): `H/c7fix_analyze.py`, `F/sizediff.py`, `F/bn_run.py`, `F/patch_u4.py`(HSC 1회 패치 스크립트)
- 쓰지 않은 실행: `F/run_aborted_1249/`(중간 트리), `F/smoke/`(개발 스모크)
