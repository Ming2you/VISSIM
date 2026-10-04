# 도시 묶음 2 구현 계획: C3(U4+U5+U6) · C2(U2) · C6 (망 v3b, cf3ce37 기준)

- 작성 2026-09-28. 대상 코드: `D:/VISSIM-merge/sim3-n31-urban` @ `cf3ce37` (브랜치 `claude/urban-fix-v3b-20260925`). 구현은 새 워크트리에서 합니다(§3).
- 기준(base): 묶음 1의 U1+U3 = `config_n31_v2_urban_b1_u1u3.json` (sha `f88d05f1`, S1 튜닝). 묶음 2의 모든 판정은 "U1+U3 대비"입니다.
- 이 문서는 네 병렬 작업 결과(U4 표, U5 계약 초안, U6 진단, 코드 지도)와 설계 문서 셋(URBAN_FIX_PROPOSAL, SC109_DIAG, XREPLAY_RESULT)을 하나의 실행 계획으로 묶은 것입니다. 새 측정은 하지 않았습니다.
- 표기
  - **[실행]**: 이번에 제가 직접 돌려서 얻은 값입니다. JSON 구조·등급 집계, 결정 파일 grep, 코드 줄 재확인이 여기에 해당합니다.
  - **[읽음]**: 파일에서 읽은 값입니다. 병렬 보고서 수치는 출처(예: `u6 §5.5`)를 함께 적습니다.
  - **[추론]**: 직접 증거 없이 설계상 끌어낸 판단입니다.
- 줄 번호는 모두 cf3ce37 기준입니다. 약어는 `code_map.md`와 같습니다.
  - A = `evaluation/controllers/vissim_stackelberg_adapter.py`, RS = `runtime_setup.py`, UFA = `urban_flow_accounting.py`, UQM = `vendor/NumSim-mine/src/models/urban_queue_model.py`
  - SHO = `signal_head_observation.py`, HSR = `head_service_resources.py`, LSS = `local_signal_service.py`, LOR = `lane_offramp_runtime.py`
  - RCC = `route_choice_corridor.py`, NIP = `native_input_prehead.py`, AGG = `sdmpc_aggregate.py`, CONT = `sdmpc_continuous.py`
  - CAO = `control_area_objective.py`, LUR = `lane_urban_runtime.py`, P = `evaluation/parameters.json`
  - CFG = `diagnostics/sdmpc_n31_20260924/config_n31_v2_urban_b1_u1u3.json`
  - MRS = `diagnostics/sdmpc_n31_20260924/tools/make_replay_state_v2.py`
  - B = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/urban-b2`

### 이 문서를 쓰며 한 일 (안전)

- 코드·config·git은 건드리지 않았습니다. VISSIM, cscript, ps1, 재생도 돌리지 않았습니다. 새로 쓴 파일은 이 문서 하나입니다.
- 읽기 전용 확인 세 가지를 했습니다. 모두 수 초짜리 작업입니다.
  - python으로 JSON 읽기 3회: U4 표·U5 계약의 구조와 등급, 원형 굶김 감시 결과
  - `sed`로 코드 12곳 줄 번호 재확인(부록 A)
  - R-obs-b 결정 파일 하나(`action_002700.json`)를 grep
- v3c1·N1 폴더와 그 프로세스, s37, RM 팔, 봉인 시드는 쓰지 않았습니다.

### 적대적 검토 뒤 고친 판 (2026-09-28 오후)

- 검토에서 찾은 문제 22건과 해결을 **부록 C**에 모았습니다. 본문은 그 해결에 맞춰 고쳤고, 고친 곳에는 `[검토 C-n]` 표시를 달았습니다.
- 검토 때 한 일도 모두 읽기 전용입니다. 코드·config·git·VISSIM·재생은 건드리지 않았고, 이 문서 외에 쓴 파일은 없습니다.
  - `sed`로 인용 줄 30여 곳을 cf3ce37에서 다시 읽었습니다(부록 C.1).
  - python으로 JSON 읽기 5회: U4 표, U5 계약 계수, 굶김 원형 결과, S1 T3600·R-obs-b T2700 결정 JSON(런 폴더에서 **읽기만**)
- 가장 큰 발견 네 가지
  - 헤드 하한(SHO)이 U4 뒤에 돌면서 구성원 용량을 **β 비율로 다시 나눕니다.** 그래서 "cap_m = s_g × 차로"가 그대로 남지 않습니다(C-1).
  - 장부 예외(CAO)는 응답을 포착하는 평가에서만 발동합니다. 따라서 "모든 예측에서 단언"이라는 서술은 틀렸습니다(C-2).
  - v3b 표에서 127|p4 실측은 2,058.3입니다. 옛 관문 범위 1,725~2,025를 **구조적으로 넘습니다**(C-5).
  - 현시 불일치 그룹을 "예산 없이 남기는" 선택지는 그 그룹에서 U4 단독 배포와 같습니다(C-6).

---

## 0. 한눈에

1. **묶음 2는 세 조각을 한 후보로 냅니다.**
   - C3 = U4 + U5 + U6: 용량 척도, 헤드 그룹 공유 자원, W측 램프 분기입니다. 코드 수준에서 **셋 다 있거나 셋 다 없어야** 설치됩니다.
   - C2 = U2: 기존 코드에 켜는 키를 넣고, 가시성 결함 하나를 고칩니다.
   - C6: 굶김 감시입니다. 진단 전용이라 행동은 비트 동일합니다.
   - U1+U3는 그대로 기준으로 둡니다.
2. **U4**
   - 206.53 veh/h-녹색/차로 정규화(A:3832-3836)를 **헤드 그룹 실측 포화 방류율 핀 표**로 대체합니다. 실측 65그룹, 기본값 40그룹(1,850)입니다 [읽음 `u4_saturation_table.json`].
   - `lane_group_kinds`는 네 kind를 명시합니다: `internal`, `boundary_out`, `boundary_in`, `off_ramp`. 런타임에 `on_ramp` kind는 없습니다 [읽음 code_map §3.3].
   - 구성원은 **U5 계약에서 읽습니다.** kind 필터로 구성원을 넓히면 게이트 peel-off(1800)와 10634 풀 구성원이 헤드 그룹에 들어오고, `21|p3`는 detector 매핑 오류로 구성원이 0이 되기 때문입니다 [읽음 code_map §3.3, U4 결과 §7].
   - **U4를 켜면 헤드 하한 배분 함수도 바꿉니다** `[검토 C-1]`.
     - 헤드 하한(RS:145 `install_measured_movement_capacity` → SHO:202, :252-255 → A:4598-4602)은 RS:128보다 **뒤에** 돌고, 그룹 총량을 β 비율로 구성원에게 다시 나눕니다.
     - 그래서 U4가 켜지면 A:4435가 넘기는 `distribute`를 **차로 비율 보존** 함수로 바꿉니다. 하한이 구속하지 않으면 U4 값이 비트 그대로 남습니다.
3. **U5**
   - 과대 그룹 전부에 그룹 예산 `B_g = s_g × n_g × T × φ_g`를 겁니다. 몫은 큐 비례(유체 FIFO)로 나눕니다.
   - 몫 계산 위치는 **UFA:516과 :521 사이**, 즉 도착 반영 뒤·off-ramp 배수 전입니다. 적용 위치는 UFA:540(회랑 재기록 뒤)~:542와 LOR:59-71입니다 `[검토 C-13]`.
   - off-ramp 가중치는 `β × port.ready()`이고, 포트 물리로 못 쓴 몫은 같은 스텝의 정규 구성원에게 되돌립니다. 127 몫은 새 관문 G-U5-127로 FZP와 대조합니다 `[검토 C-4]`.
   - 할당기는 원장 포착과 무관한 **자체 원시 단언**을 가집니다. CAO 예외는 포착하는 평가에서만 발동하기 때문입니다 `[검토 C-2]`.
   - v3b 계약 등급 [실행 `u5_contract_draft.json`]
     - budget 45, 10629 대체 1, LUR 위임 2, 직렬 첫 헤드 1
     - 현시 불일치 차단 3, 흐름 없음 3, 구속 안 됨 53
     - native 66 (그중 과대 12)
   - **"58/105, 81차로"는 v2(V5b) 수치입니다** `[검토 C-6]` [실행 `counts`]
     - v3b에서 다시 세면 관측 105그룹 중 과대는 50개이고, 관측 밖 제어 그룹 3개를 더하면 108그룹 중 53개입니다.
     - 53개는 등급으로 이렇게 나뉩니다: budget 45, 10629 대체 1, LUR 위임 2, 현시 불일치 3, 파생 기준으로만 과대 2(흐름 없음 1, 구속 안 됨 1). 마지막 둘은 v1 구성원(§10-4) 기준으로는 과대가 아니라서 예산이 필요 없습니다.
     - 공유 정지선 차로는 movement 기준 80(108그룹)·76(105그룹)입니다. 실제로 둘 이상의 출구가 나눠 쓰는 차로는 44·40이고, 나머지 36은 한 출구 커넥터를 여러 origin 별칭이 중복으로 가리킨 것입니다.
     - 사용자 결정 "과대 그룹 전부"는 v3b에서 **이 53개 + (Q1에 따라) native 12**로 읽습니다.
   - **미결 행은 U4 단독이 되지 않게 합니다** `[검토 C-6]`. 현시 불일치 3행과 native 12행은 결정 전까지 "정적 축소"를 받습니다. 구성원 용량 합이 n_g × s_g가 되도록 차로 비율로 줄이는 방식입니다(§4.5-11).
4. **U6**
   - `urban.ramp.admission_policy: "physical_diverge_v1"` 하나로 A1–A4, B1–B3, C를 **한꺼번에** 켭니다.
   - 진입 여유 식은 건드리지 않습니다. 구속한 시간이 0초였기 때문입니다 [읽음 u6 §0].
5. **C2**: 코드는 이미 있습니다. 구현할 것은 `projection_diagnostics` 가시성 수정 하나이고, 판정은 **"C3 위 U2" 증분**으로 합니다.
6. **C6**: A:13981과 :13991 사이에 읽기 전용 모듈을 넣습니다. 출력은 `metadata['starvation_monitor']`와 stdout `"starvation"`이고, 러너 VBS는 바꾸지 않습니다.
   - `[검토 C-10]` 결정 밖에서 행동에 닿는 통로 넷을 막습니다: stdout 512바이트 상한(러너가 종료 뒤 파이프를 읽음), 다음 결정이 읽는 이전 action(새 관문 G-C6-4), 상태 불변, 대소문자 무시 필드 검색.
7. **발견 하나 [실행]**
   - R-obs-b 결정은 `controller_variant: "no-control"`(T2700 `decision_wall_sec` 22.8)입니다.
   - 그래서 "기본 튜닝 61/61 IDENTICAL"은 plant·투영·한 스텝 예측·목적값을 덮지만 **SDMPC 최적화 경로(tangent·후보 평가)는 덮지 않습니다.**
   - 비트 동일 관문에 S1·S0e 상태의 SDMPC 결정 재생을 더합니다(§6.1 (c)).
8. **순서**: 준비 → 비트 동일 정리(U4-0) → C6 → 증거 파일 확정 → U4 → U5 → U6 → C3 묶음 관문 → C2 증분 → 후보 config. 약 19~26 작업일에 재생 벽시계 11~17 h가 따로 듭니다(§7, 검토 뒤 +2~3일·+1~2 h `[검토 C-1·C-4·C-10·C-12·C-16]`).
9. **여쭐 것은 세 가지입니다**(§11): native 과대 12그룹, 현시 불일치 3그룹, v3c1 전에 v3b 단일 시드 폐루프를 할지.

---

## 1. 요약 표

| 항목 | 변경 | 파일:줄 (cf3ce37) | config 키 | 시험 | 오프라인 관문 | 노력 | 의존 |
|---|---|---|---|---|---|---|---|
| P 준비 | 워크트리, 하네스 경로 매개화, 기준선 재현 | 하네스 `urban-b1d/{b1_capture,t3_arms,check_paths}.py`, `sc109-diag/cfw/cf_driver.py`, `B/u6/u6_capture.py`, `B/livecheck.py` | – | 기존 스위트 전부 통과 | 기준선 = 묶음 1 수치 재현(§6.2) | 0.5–1일 | – |
| U4-0 비트 동일 정리 | 코드 기본값 4개를 config로 올림(`lane_group_kinds ["internal"]`, `gate_onramp_queue_capacity_veh_h 1800`, `perimeter_include_boundary_out true` `[검토 C-8]`, `equivalent_uniform_veh_h` 코드 기본 600 → 필수). `_LG_KINDS`/`_LTO`/`_SUS_SIGS` 설정을 별도 설치 함수로 분리(`_SUS_SIGS`는 대체 계수 뒤 결정). 죽은 분기 격리, 죽은 키 제거. b2 브랜치 안 평탄화 + diff 검사 `[검토 C-9]` | A:3391, A:3832, A:3874, A:4570-4572, A:4296-4409(:4350-4358), A:4437-4545, A:4606/:4622/:4650, CFG:7821-7839 | 기존 키를 명시 | 필수 키 누락·알 수 없는 키 거부, 평탄화 diff | G-ID(§6.1) | 1–1.5일 | P |
| C6 굶김 감시 | 새 모듈, 결정 끝에 읽기 전용 계산 | 새 `evaluation/controllers/starvation_monitor.py`, 삽입 A:13981–13991, stdout A:14050-14055 (VBS:1236-1240 무변경) | `urban.diagnostics.starvation_monitor {floor_tol_s, min_stopped_per_lane, n_consecutive, boundary_capacity_bound_k}` | 설정 검증, 합성 prior 스트릭, 오류 포착, 이름 충돌, stdout 상한, 상태 불변 | G-C6-0~4 (§6.9) | 1.5–2일 | P |
| 증거 파일 확정 | U4 표 v1(망 sha, +3 다중헤드 그룹, +native 66), U5 계약 v1(구성원·소유자·U4 키 연결), U6 분기 증거 | 새 `scripts/derive_head_saturation.py`, `derive_shared_head_groups.py`, `derive_ramp_diverge.py`, 새 `diagnostics/sdmpc_n31_20260924/urban/*_v3b_*.json` | – | `--check` 바이트 재현, 스키마 | 핀·교차 일관성 | 2일 | P |
| U4 용량 척도 | 표 기반 설치 함수. 구성원은 계약에서(2단계 적재). **헤드 하한 차로 비율 보존 콜백** `[검토 C-1]`. RCC 조회 함수. pre-head 1093. LOR direct | A:3772-3922(대체 자리 :3909), A:4435 → SHO:202-255 → A:4598-4602, RS:128(서명에 `state_json`), RS:174-182 → RCC:397/:431-437/:531/:871/:884, A:4561-4603, NIP:99-102/:266-268, AGG:276-278, LOR:51/:56 | `urban.capacity.saturation_veh_h_per_lane {path, sha256}`, `urban.capacity.lane_group_kinds` (4종) | 로더·결합 오류, 소유자 제외, 21\|p3, allocation 점검 | T1, G-ID | 2–3일 | 증거, U4-0 |
| U5 공유 자원 | 계약 로더(새 모듈), 스텝 할당기(자체 원시 단언), LOR 요청/실행 분리(`port.ready()`), 장부. **HSR은 고치지 않음** `[검토 C-15]` | UFA:219-220/:516-521/:540-542/:586-599/:1000-1006, UFA:978-997(설치 단언), LOR:27-32/:47/:59-71/:73/:84, `physical_urban_transport.py:91`, LSS:88-120, NIP:254-294, AGG:268-292, RS:207-210/:245-247/:261-294, CAO:329-357 | `urban.capacity.shared_head_groups {path, sha256}` (`head_resource_contract` 대체) | 할당기 단위, 매 스텝 단언, 10634 동일, spatial 거부 | G-U5-0~6, T1 | 4–6일 | U4 |
| U6 램프 분기 | A1 분기 용량, A2 경로 적격·운동학 도착, A3 신규 유입 지연, A4 SC1004 중복 제거, B1 τ·이중 지연, B2 10483 착지, B3 분할표, C 계측 | A:3380-3416(:3391), A:10022-10097, `area_runtime.py:61-87`, UFA:378-381/:386-393/:607, LOR:95, A:2876-2900, A:3190-3193, A:8408-8457, A:2785-2789, A:3419-3476, P:84-88 | `urban.ramp.admission_policy`, `urban.ramp.diverge_evidence {path, sha256}` | 증거 로더, 적격·도착·보존, 공존 금지 | G6-0~10 (§6.5) | 3–4일 | P (판정은 U4·U5와 함께) |
| C3 묶음 관문 | – | – | – | 세 경로, 캐시, AD 대 FD, 시간 계수 | G-ID, T1, G0, G-SC109, G6, G-v3b, 시간 | 2–3일 | U4·U5·U6 |
| C2 = U2 | `queue_attribution_route` 요약을 `projection_diagnostics`로 | A:6784-6793 → A:13607-13614 | 기존 `urban.queue.attribution: "route"`, `urban.queue.route_evidence` | 가시성(키 없으면 필드 없음) | G0·G-SC109 증분, 173/174 몫 | 1일 | C3 |
| 후보 config | `make_config_n31.py --urban-batch2 --components …` | `make_config_n31.py:249` 옆 새 함수 | 위 키 전부 명시 | `--check` | – | 0.5일 | 전부 |

---

## 2. 공통 규칙 (이번 묶음 전체)

1. **스위치는 config 키 하나입니다.**
   - env, `getattr` 기본값, `section.get(k, 기본)`으로 켜지는 게이트는 만들지 않습니다.
   - 지금 코드 기본값으로 살아 있는 값은 U4-0에서 config로 올리고, 코드는 필수 키로 바꿉니다.
   - 확인한 예 [실행, 부록 A]: A:3391 `section.get("gate_onramp_queue_capacity_veh_h")` 기본 1800, A:3832 `equivalent_uniform_veh_h` 기본 600, A:4351 `lane_group_kinds` 기본 `["internal"]`
2. **키 결합은 설치 단계에서 강제합니다.**
   - C3 세 키(`saturation_veh_h_per_lane`, `shared_head_groups`, `admission_policy`)는 셋 다 있거나 셋 다 없어야 합니다. 하나라도 빠지면 `ValueError`입니다.
   - `[검토 C-7]` **`lane_group_kinds`도 결합에 넣습니다.** `["internal"]`이 아닌 값은 C3 세 키가 모두 있을 때만 허용합니다.
     - U4-0 뒤에는 `install_lane_group_membership`이 이 키를 U4와 상관없이 읽습니다.
     - 그래서 이 키만 네 kind로 바꾼 config는 게이트 peel-off를 127|p3에 넣습니다(code_map §3.3). 이것은 U4 단독의 한 형태입니다.
   - 근거는 사용자 결정 "U4 단독 금지"와 증거 둘입니다: U4/U5 대리만 넣으면 W 정지선 큐가 −28 → −67, U6만 넣으면 +34였습니다 [읽음 u6 §5.5].
   - 귀속 분석용 부분 팔은 코드 키가 아니라 **하네스의 메모리 패치**로 만듭니다(u6 진단과 같은 방식).
   - 대체 관계인 옛 키와는 함께 쓸 수 없습니다: `equivalent_uniform_veh_h`·`per_lane`·`perimeter` ↔ U4, `head_resource_contract` ↔ U5, `gate_onramp_queue_capacity_veh_h`·`urban.boundary_out.ramp_split_json` ↔ U6.
3. **새 표·계약은 `cfg.network`에 둡니다.** 워커는 설치를 다시 하지 않고 `follower.cfg`를 받기 때문입니다(RS:261-294, code_map §2). 모듈 전역에 기대지 않습니다.
4. **"켰다"와 "돌았다"를 디스크가 말하게 합니다.**
   - 결정 JSON은 `projection_diagnostics` 하위만 나릅니다(A:13607-13614). 그래서 U4·U5·U6·U2 진단은 모두 그 안에 넣습니다.
   - 계측은 **해당 키가 있을 때만** 씁니다. 그래야 키 없음 비트 동일이 유지됩니다.
5. **옛 경로는 승격 때 격리합니다.** 묶음 2는 후보 config만 만들고 기본 config는 바꾸지 않습니다. 따라서 키가 없을 때의 옛 경로는 남아 있습니다.
   - 승격(v3c1 폐루프 판정 뒤)할 때 `_superseded_<날짜>/`로 옮기고, sha와 그것을 쓴 런 목록을 매니페스트로 남깁니다.
   - U4-0의 죽은 분기는 예외입니다. 지금 격리합니다(§4.1 조건 충족 시).
6. **SHO 옵션에 키를 더하지 않습니다.** SHO:63이 런 provenance와 옵션이 **정확히** 같기를 요구하므로, 더하면 기록된 상태의 재생이 전부 실패합니다(code_map §3.5-6).
7. **AD 수칙.** 새 코드는 이항 `+`·`−`·`×`·`÷`와 `min`만 씁니다 `[검토 C-13]`.
   - U5는 `B_g − 소비`와 요청 합이 필요하므로 덧셈·뺄셈이 빠질 수 없습니다. 여러 항의 합은 순서를 고정한 이항 합으로 씁니다.
   - 정수화, 반올림, 교통량을 dict 키로 쓰는 것, 새 n항 연산 노드는 금지입니다(TRT:35-66, DUAL:176-185, `sdmpc_tangent_reverse.py:44-67`, code_map §7.2).
   - 장부 기록은 도함수에 들어가지 않습니다(CAO:341-346).
8. **새 코드는 stdout·stderr에 아무것도 쓰지 않습니다** `[검토 C-10]`.
   - 러너는 결정 프로세스가 끝난 **뒤에** 파이프를 읽습니다(VBS:5139-5143, A:14058-14059 주석). 출력이 파이프 버퍼를 넘으면 결정이 멈춥니다.
   - 예외는 결정 끝의 stdout JSON 한 줄뿐입니다. numpy 경고도 막습니다.
9. **action JSON 크기** `[검토 C-22]`: 이미 결정당 약 58 MB입니다(VBS:5008-5010 주석). 새 진단은 요약 계수만 넣고, 초 단위 배열은 넣지 않습니다. 크기 증가를 시간 관문에서 함께 재고, 1% 이하여야 합니다.

---

## 3. 작업 트리·브랜치 계획

- **새 워크트리:** `D:/VISSIM-merge/sim3-n31-urban-b2` [실행: 아직 없음]
  - 새 브랜치 `claude/urban-b2-20260928`을 `cf3ce37`에서 만듭니다.
  - 명령(구현 시작 때 한 번): `git -C D:/VISSIM-merge/repo worktree add -b claude/urban-b2-20260928 D:/VISSIM-merge/sim3-n31-urban-b2 cf3ce37`
- **기존 워크트리는 건드리지 않습니다.** `D:/VISSIM-merge/sim3-n31-urban`은 S1 provenance와 frozen `sdmpc31_cf3ce374_202609261037`의 원본입니다. 기준선 대조 재생(§6.1 (b))의 "옛 트리" 쪽으로 읽기만 합니다.
- **커밋:** 단계마다 로컬 커밋 하나씩 만들고, 메시지 끝에 attribution 줄을 붙입니다. **push, main 병합, 기본 config 변경은 사용자 결정 없이 하지 않습니다.**
  - `[검토 C-9]` U4-0은 b2 브랜치 안에서 `config_n31_v2.json`을 평탄화합니다. 앞 문장과 충돌하므로 범위를 이렇게 정합니다.
    - 평탄화는 **의미가 같은 변경만** 허용합니다. 옛 코드 기본값을 명시하고, 부록 C의 죽은 키 목록만 지웁니다.
    - 기계적 diff 검사로 확인합니다: 더한 키는 옛 기본값과 같아야 하고, 지운 키는 죽은 키 목록에 있어야 합니다.
    - 로컬 커밋까지만 합니다. main의 기본 config로 올리는 것은 사용자 결정입니다.
  - 결과: 옛 런 provenance와 frozen 트리에 기록된 튜닝은 새 코드에서 필수 키가 없어 적재되지 않습니다. b2 트리의 모든 재생은 평탄화한 config를 씁니다.
- **캐시**
  - `__tangentcache__`는 b2 워크트리에서만 새 파일이 생깁니다(TRT:76-116). `freeze_manifest.py:35-37`이 비교에서 뺍니다.
  - `NUMBA_CACHE_DIR=C:/Users/TRLAB/AppData/Local/Temp/nbc_b2`
- **하네스 함정**
  - `urban-b1d/t3_arms.py`는 워크트리 경로를 `W = Path(r'D:/VISSIM-merge/sim3-n31-urban')`로 하드코딩합니다 [읽음]. `b1_capture.py`·`check_paths.py`·`cf_driver.py`·`u6_capture.py`·`livecheck.py`도 같은 식일 가능성이 큽니다 [추론].
  - 그대로 쓰면 **옛 트리를 재는 조용한 오측정**이 됩니다. `B/harness/`로 복사하고 워크트리 경로를 필수 인자로 바꿉니다. 모든 산출 JSON에 `worktree_head`와 어댑터 sha를 기록합니다.
- **재생 규칙**
  - 한 번에 하나, BELOW_NORMAL, 스레드 1로 돌립니다. 시작 전에 다른 재생 python이 없는지 확인합니다(`run_livecheck.sh`의 `busy()` 재사용).
  - 재생 상태는 `MRS.prepare`로 **복사해서** 씁니다. 런 폴더에는 쓰지 않습니다. 재생 뒤에는 원 런 폴더·frozen 트리에 `find -newer`로 새 파일이 0개인지 확인합니다.
  - `[검토 C-19]` 옛 트리(cf3ce37)로 재생할 때는 `PYTHONDONTWRITEBYTECODE=1`을 둡니다. `__pycache__`가 옛 트리에 새로 생기지 않게 하기 위해서입니다. 옛 트리의 `find -newer` 0개 확인도 합니다.
- **폐루프 런은 이 계획에 없습니다.** 필요하면 `-Freeze`, WMI 분리 발사, `-NoGlobalKill`로 하고, 별도 승인을 받습니다(§11 Q3).

---

## 4. 항목별 구현 단계

### 4.0 준비 (P)

1. 워크트리를 만들고 하네스를 이식합니다(§3).
2. 기존 스위트를 b2 트리에서 돌려 통과를 확인합니다.
   - `diagnostics/test_*.py` 11개 [실행: 존재 확인]: head_service_resources, head_free_service, sc1004_resource_service, shared_service_pool, route_choice_corridor, native_input_prehead, sdmpc_aggregate, urban_flow_accounting, sdmpc_spatial, legsplit_receiving, shared_approach
   - `diagnostics/sdmpc_n31_20260924/tests/test_n31_*.py`
   - `diagnostics/obs150_20260924/tests/test_head_*.py`
3. **기준선 재현.** b2 트리(키 변경 없음)에서 R-obs-b 61상태를 U1+U3로 재생하고, 묶음 1 값을 다시 얻습니다 [읽음 PLANT_PORTING_GUIDE, SC7 정정 뒤].
   - T3: A1 6.361, A2 8.892, A3 11.587, B1 7.191, B2 10.041, B3 12.884, C 11.011
   - 세 경로(T2700): 캐시·반복 0, no_agg ≤ 1.6e-13, AD 대 스칼라 ≤ 3.6e-15, 연속 대 정확 도시 owner ≤ 0.013
   - FD: SC1001 3.003/2.975, SC1002 0.913/0.916, SC7 p1 −0.238/−0.209(꺾임점)
   - 이 값이 안 나오면 멈추고 하네스부터 봅니다.
4. **206.53 가정 fixture 목록을 먼저 뽑습니다**(code_map §3.6). U4 뒤 깨질 시험과 진짜 회귀를 가르기 위해서입니다.
5. **시간 기준선**을 잽니다.
   - livecheck 호출 수(정확 450 s 예측): `urban_substep_accounted` 450, `LaneOfframpRuntime.drain` 450, `regular_batch` 44,550, `receiving_space` 6,750
   - `tangent_derivatives[i].trace`의 `operations`·`event_counts`

### 4.1 U4-0 숨은 기본값·죽은 키 정리 (비트 동일)

1. **config로 올리기**(기본 `config_n31_v2.json`, `_b1.json`, `_b1_u1u3.json` 모두. b2 브랜치 안에서만, §3 `[검토 C-9]`)
   - `urban.capacity.lane_group_kinds: ["internal"]`
   - `urban.ramp.gate_onramp_queue_capacity_veh_h: 1800`
   - `[검토 C-8]` `urban.capacity.perimeter_include_boundary_out: true`: A:3874의 네 번째 살아 있는 코드 기본값입니다(`section.get(..., True)`). 처음 판은 셋만 셌습니다.
   - 코드 쪽: A:3391·A:4351·A:3874를 필수 키 읽기로 바꿉니다. A:3832의 기본 600도 필수로 바꿉니다(config 값은 330).
   - `[검토 C-8]` 옛 경로가 하드코딩한 차로 파일 두 개(A:3808 `movement_lanes_core17legs4b_20260821.json`, A:3868 `movement_lanes_perimeter_20260824.json`)는 파일이 없으면 조용히 `source_missing` 메타만 남깁니다. 키 없음 경로는 비트 동일을 위해 그대로 둡니다. **U4 경로는 이 두 파일을 표에 {path, sha256}으로 핀하고, 없으면 실패합니다.**
2. **`_LG_KINDS`·`_LTO`·`_SUS_SIGS` 설정 분리** `[검토 C-8]`
   - 지금은 죽은 `seed: "sustained"` 분기 안(A:4350-4365)에서 부작용으로만 설정됩니다.
   - 처음 판은 둘만 옮겼습니다. 그런데 같은 분기가 `sustained_json`(CFG:7834)에서 `_SUS_SIGS`(링크 → 신호, S1 3600에서 68개)도 채우고, 이것을 **살아 있는** 배분 함수가 씁니다(A:4570-4572, `groups`에 없는 링크의 신호 대체).
   - code_map은 이것을 "효과 DEAD"로 봤지만 [추론]입니다. 그래서 다음 순서로 합니다.
     - (i) 계수를 먼저 붙입니다. A:4570-4572 대체가 구성원이 있는 `est_lg` 항목에 쓰인 횟수를 R-obs-b 61상태, S1·S0e 결정 상태에서 셉니다.
     - (ii) 0이면 `_SUS_SIGS`와 `sustained_json`을 함께 격리합니다.
     - (iii) 0이 아니면 새 설치 함수가 명시 키(`urban.capacity.lane_group_signal_fallback_json {path, sha256}`)로 `_SUS_SIGS`를 채웁니다.
   - 이를 `install_lane_group_membership(cfg, tuning)`로 떼어 A:4430-4435 조기 반환 **전에** 명시 호출합니다. 입력은 `lane_group_kinds`, `detector_mapping_json`(그리고 (iii)이면 대체 파일)입니다.
   - 전역 이름은 바꾸지 않습니다. tangent 요청은 어댑터 모듈 전역 중 `_`+대문자 dict/list/set을 깊은 복사로 나릅니다(`sdmpc_tangent.py:25-26`). 이름이 바뀌면 요청 바이트가 달라집니다.
   - 옛 코드는 `_LTO` 적재 오류를 삼킵니다(A:4357 `except … pass`). 새 함수는 삼키지 않습니다. 파일이 있는 설정에서는 비트 동일이고, 파일이 없으면 이제 실패합니다.
3. **죽은 분기 격리 (조건부)**
   - 대상: A:4437-4545(온라인 갱신·fallback), `observed`·`sustained` 씨앗 값 경로, 도우미 A:4606·:4622·:4650. 옮길 곳은 `_superseded_20260928/`입니다.
   - **조건:** 저장소의 **모든** config JSON(SDMPC 외 21셀·wu-link 계열 포함)을 grep해 이 분기를 켜는 설정이 없어야 합니다. livecheck 호출 수 0(code_map §1.2)은 SDMPC 두 튜닝만 본 것입니다. 하나라도 있으면 격리하지 않고 표로 남깁니다.
   - 해석기 두 개(`whose_code.py`·`resolve_live_controller.py`)는 이 판정에 쓰지 않습니다(메모리 `vissim-sdmpc31-live-check-tools-blind`).
4. **죽은 키 제거**: CFG:7822-7839(code_map §3.4 표의 DEAD 행)를 세 config에서 뺍니다. 기본 config 바이트가 바뀝니다.
   - `[검토 C-8]` `sustained_json`(7834)은 2-(ii)일 때만 뺍니다. `decay`(7833)는 A:4269에서 반환 전에 읽히므로, 읽기만 하고 쓰이지 않는다는 것을 계수로 확인한 뒤에 뺍니다.
5. **판정**: G-ID(§6.1) (a)(b)(c)를 **평탄화한 새 config**로 받습니다. 그 뒤로는 이 config가 "키 없음" 기준입니다.
   - 평탄화 diff 검사(§3 `[검토 C-9]`)를 G-ID보다 먼저 통과해야 합니다.
   - 재생 도구가 기록 튜닝 sha를 대조해 실패하면, 비교를 action_csv·action_controls·objective 세 검사로 합니다(SC109_DIAG §4 도구 주의와 같은 정의).

### 4.2 C6 굶김 감시 (진단 전용)

- **새 모듈** `evaluation/controllers/starvation_monitor.py`
  - 호출 위치: A:13981(`post_guard_safety_metadata`) 뒤, A:13991(`decision_wall_sec`) 앞 [읽음, 이번에 재확인]
  - 키가 없으면 import하지 않습니다.
  - tangent 워커는 이 모듈을 부르지 않으므로 AST 계측과 무관합니다 [추론].
- **키** `urban.diagnostics.starvation_monitor`
  - 필드: `floor_tol_s`(≥ 0), `min_stopped_per_lane`(> 0), `n_consecutive`(≥ 1 정수), `boundary_capacity_bound_k`(≥ 1 정수)
  - 넷 다 필수이고, 모르는 키는 거부합니다(SHO.settings SHO:32-53 방식).
  - 고정 상수는 스키마 `urban-starvation-monitor/v1`에 묶어 metadata `constants`로 기록합니다: 정지 기준은 원 상태 `vehicle_records.stopped_threshold_kph`를 읽기만 함(러너 1.0 km/h), 공급 차로는 커넥터 한 단계·300 m, 경계 구속 비율은 0.95입니다.
- **입력** (code_map §8.2)
  - 원 상태 `vehicle_records`(T), obs150 `frames.previous`(T−150)
  - `obs150/derived_<T>.json` 헤드 창: **읽기만** 합니다. MRS 비교 대상이기 때문입니다.
  - `SHO.physical_groups`, inpx 헤드·커넥터, `SAC.phase_bounds`
  - 최종 `control.green_times`, 헤드 하한 메타 키
  - `joint_response.final_score.quantities.served_by_movement_veh`
  - 이전 결정의 `metadata.starvation_monitor.streaks`: 같은 `run_id`이고 `sim_sec = T−150`일 때만 씁니다.
- **규칙**
  - 현시 굶김: 녹색 ≤ 하한 + `floor_tol_s` **이고** (헤드 차로 + 상류 공급 차로 정지차) ≥ M × 헤드 차로 수이면 스트릭 +1입니다. 스트릭 ≥ N이면 경보입니다.
  - 경계 구속: `served / (cap × G/3600) ≥ 0.95`가 k결정 연속이면 경보입니다.
- **출력**
  - `metadata['starvation_monitor']`: schema, config, constants, sim_sec, prior_valid, streaks, bound_streaks, alarms
  - stdout JSON에 `"starvation": {"alarms": n, "keys": […], "bound": […]}`를 더합니다. 러너가 이 stdout을 `CONTROLLER_DECISION … stdout=` 줄에 그대로 남기므로 VBS 변경 없이 runlog 요약이 됩니다(VBS:1236-1240) [읽음 code_map §8.4].
  - 러너는 `controller_status`·`decision_wall_sec`를 첫 출현 텍스트 검색으로 읽습니다(VBS:5011-5020). 그래서 새 필드 안에 이 두 이름을 쓰지 않습니다.
- **예외는 올리지 않습니다.** `starvation_monitor.error`와 stdout `"starvation": {"error": …}`로 남깁니다. 진단 오류로 결정이 실패하면 행동이 바뀌기 때문입니다. 런로그에 드러나므로 조용한 실패는 아닙니다.
- **행동에 닿는 통로 넷을 막습니다** `[검토 C-10]`. action은 C6 전에 확정되지만, 다음 넷은 여전히 행동을 바꿀 수 있습니다.
  1. **파이프 교착.** 러너는 프로세스가 끝난 뒤에 stdout·stderr를 읽습니다(VBS:5139-5143, A:14058-14059 주석).
     - stdout `"starvation"`은 크기를 고정합니다: 계수 3개와 앞 10개 키, 최대 512바이트입니다. 자세한 내용은 metadata에만 둡니다.
     - stderr에는 쓰지 않습니다.
  2. **다음 결정이 읽는 이전 action.** 이전 action JSON을 읽는 곳이 14곳(grep, 읽기 호출 기준)입니다(HSR:118, SHO:126·:378, sdmpc.py:502·:550, A:2036·:4275·:4627·:8547·:10966·:12927·:13732, `area_meter_finalization.py:50`, `network_pressure.py:398`).
     - A:12927-12929는 이전 action 파일의 sha를 핀합니다. 따라서 C6가 있으면 다음 결정의 입력 바이트가 달라집니다.
     - 판정: 정적 감사로 이 독자들이 metadata를 **이름이나 접두사로만** 읽는지 확인합니다(현재 접두사 독자는 `head_candidate_end_`·`head_free_candidate_end_`뿐). 여기에 G-C6-4 두 결정 연쇄 재생을 더합니다(§6.9).
  3. **상태 변형.** C6는 `cfg`·`state`·SHO 캐시를 바꾸지 않습니다. 단위 시험에서 C6 전후 `cfg.network`·`state`의 pickle 해시가 같아야 합니다.
  4. **러너 필드 검색.** 러너는 `JsonFieldText`를 `vbTextCompare`, 즉 **대소문자 무시**로 찾습니다(VBS:5038-5048). 새 필드 이름은 대소문자와 관계없이 `controller_status`·`decision_wall_sec`와 겹치면 안 됩니다.
- **초기값**: `floor_tol_s` 1.0, M 8, N 3, k 3 (원형 `net-v3c/s12_starvation_watch.py`와 같음). `floor_tol_s`는 G-C6-1b 규칙으로 {1, 2, 4} 중에서 정합니다(§6.9).
- **참고 [실행 `net-v3c/starve_s1.json`·`starve_s0e.json`]**
  - 원형(정지 5 km/h, tol 1)은 S1·S0e에서 각각 경보 22건을 냈습니다. SC109 SG2(p3) 경보는 S1에서만 났고(첫 경보 4,650 s, 6,450 s), SC1004 SG3/SG8·SC16 SG6·SC6 SG3은 두 런 모두에서 났습니다.
  - 어댑터는 러너 정지 기준 1.0 km/h를 읽으므로 경보 수가 달라집니다. G-C6-1은 같은 상수로 다시 계산한 값과 대조합니다.

### 4.3 증거 파일 확정 (U4 표 v1 · U5 계약 v1 · U6 분기 증거)

1. **U4 표 v1** (`B/u4/*` → 저장소 `scripts/derive_head_saturation.py`로 옮김)
   - 스키마 `u4-saturation-table/v1`에 `network: {path, sha256}`을 넣습니다. 지금은 설명 문자열입니다 [실행]. 망은 `baseline_s31_v3bnc.inpx` `be0075bf…`입니다.
   - **행 추가**
     - U5 계약의 다중 헤드 차로 그룹 3개(1220011001|p1, 1220013600|p3, 1220013600|p4): 셋 다 계약 등급이 budget이고 obs150 헤드 창이 없습니다 [실행]. 같은 FZP 방법으로 헤드 위치를 지정해 잽니다.
     - native 66그룹: `.sig` 고정 계획으로 녹색 창을 만듭니다. §11 Q1 결정에 따라 적용 여부가 정해지지만, 측정 비용이 작아 미리 해 둡니다.
   - **값 규칙 (제가 정한 것, §10)**
     - 실측 그룹은 비방해 주값을 씁니다. plant에 수신 공간 제약(UFA:567-574)이 있어 하류 역류를 따로 표현하기 때문입니다 [추론].
     - 방해 포함값과 s31 정확값은 기록 칸에 남깁니다.
     - 기본값은 1,850입니다.
     - SC11 이중 정지선 하류 헤드 30601(표본 0)은 직렬 첫 헤드 규칙(1093)을 따릅니다.
   - 키는 U5 계약 `group_id`와 같은 `"<stopline_link>|<phase>"` 형식으로 맞춥니다.
   - 127|p3 `plant` 블록의 게이트 on-ramp 두 movement(각 1800)는 기록용일 뿐이고 구성원이 아닙니다 [읽음 u6 §9-3].
2. **U5 계약 v1** (`B/u5_*.py` → `scripts/derive_shared_head_groups.py`)
   - 상태를 DRAFT에서 핀 가능으로 바꿉니다. 행마다 `saturation_ref`(U4 키)와 구성원 **소유자**(UFA 정규 / LOR / LUR 위임 / prehead)를 둡니다.
   - `split_rule.name = "queue_proportional_fifo_v1"`로 둡니다. 규칙 이름이 핀된 계약 안에 있고, 모르는 이름은 설치 오류입니다.
   - **구성원 완결성 목록**: `non_members_with_flow` 65개를 사유와 함께 허용 목록으로 둡니다(U3 무신호 23, 현시권한·B5 8, 헤드 없음 18, 하류 정지선 3 등) [읽음 U5 결과 §2]. 이 목록 밖에서 헤드 차로를 떠나는 흐름 movement가 있으면 설치가 실패합니다.
   - 사용자 결정 대기 행(현시 불일치 3, native 12)은 행은 두되 `enforcement`를 결정 전 상태로 둡니다. 설치기는 이 행들을 예산에 넣지 않고 메타에 "미결 과대 그룹"으로 셉니다(§11).
3. **U6 분기 증거** (`B/u6/geo_probe.py` → `scripts/derive_ramp_diverge.py`)
   - 스키마 `ramp-diverge/v1`. 내용은 u6 §7.1 초안 그대로입니다: 1136·1137·1135 경로·분할, W_out 물리 길이 734.24 / 351.35 m, 10483 착지, SC1004_W_to_onE 퇴역, 검증 FZP.
   - 값의 출처는 pinned inpx이고, NC FZP는 검증에만 씁니다.
4. **교차 일관성 검사**(설치 때도 같은 검사를 합니다)
   - 세 파일의 망 sha가 같아야 합니다.
   - U5 계약의 모든 budget 행에 U4 키가 있어야 합니다.
   - U6 게이트 peel-off movement는 어떤 U5 행의 구성원도 아니어야 합니다.

### 4.4 U4 용량 척도 교체

1. **새 설치 함수** `install_movement_capacity_by_saturation(cfg, tuning, state_json)`
   - RS:128 자리에서, 키가 있을 때만 부릅니다. 키가 없으면 기존 `install_movement_capacity_by_lanes`(A:3772-3922)를 그대로 부릅니다.
   - 로더: 스키마, 망 sha가 스냅숏과 같은지(A:4140-4143과 같은 방식), 대체 관계 키와 공존하지 않는지, C3 결합.
   - **용량** `cap_m = s_g × |lanes(m)|`: 그룹과 구성원 차로는 U5 계약에서 읽습니다.
   - **그룹 밖 movement**는 표 기본값 × 기존 차로 JSON 차로수입니다(A:3808-3811, :3868-3873, 없으면 turn 종류 중앙값 :3817-3828). U3 무신호 23개가 여기에 들어갑니다.
   - 결과는 A:3909처럼 `movement_capacity_by_movement_veh_h`를 **통째로** 교체합니다.
   - `[검토 C-1]` **계약은 두 단계로 읽습니다.** 구성원은 RS:128(U4)과 RS:145(헤드 하한)에서 이미 필요합니다. 그런데 계약의 런타임 검증(§4.5-1)은 RS:207 뒤에야 할 수 있습니다.
     - RS:128: 두 파일의 스키마·망 sha·교차 일관성을 확인하고, 구성원·차로·소유자만 읽습니다.
     - RS:207 뒤: 전체 런타임 대조를 합니다.
     - RS:128과 RS:207 사이에는 kind·현시·β를 바꿀 수 있는 설치기가 있습니다(off-ramp 라우팅, 착지, native 구조, 위상 복구, 동적 경로, 회랑, native 입력). 불일치가 있으면 RS:207 뒤 검증에서 실패합니다.
1b. **헤드 하한과의 결합** `[검토 C-1]` (처음 판에 없던 단계)
   - 사실 [읽음]
     - RS:145-146 `install_measured_movement_capacity`는 RS:128보다 뒤입니다.
     - 헤드 관측이 켜져 있으면 A:4430-4435 → `HSR.observe` → `SHO.install`로 갑니다. 그곳의 `base = Σ 구성원 현재 용량`(SHO:202), `estimate = max(base, carried, supported)`(SHO:205, :249)를 거쳐 `distribute(cfg, groups, estimates, changed)`(SHO:252-255)가 호출됩니다.
     - 이 호출이 그룹 총량을 **β 비율**로 구성원에게 다시 씁니다(A:4598-4602 `caps[m] = total × β_m/Σβ`).
     - S1 3600에서 carried 54, updated 45였습니다(code_map §3.1). 재생 상태에서도 이전 action의 하한 키가 유효하면 이월되므로 재생에서도 일어납니다.
   - 결과: 처음 판의 "`cap_m = s_g × |lanes(m)|`"은 이 그룹들에서 최종값이 아닙니다. 공유 차로가 있으면 `base`가 중복 계상된 합이라서, β 비율 재배분이 좌회전 1차로 같은 구성원을 과소·과대로 만듭니다.
   - 수정
     - U4가 켜지면 A:4435가 넘기는 `distribute`를 `_distribute_lane_group_capacity_by_u4_ratio`로 바꿉니다.
       - 구성원은 계약의 흐름 구성원에서 소유자 제외(아래 2)를 뺀 것입니다.
       - 배분은 `caps[m] = U4cap_m × estimate / Σ U4cap`입니다. 단 `estimate == base`이면 **아무것도 쓰지 않습니다.** `x × S / S`는 반올림 때문에 x와 비트가 다를 수 있기 때문입니다.
     - `estimate ≥ base`이므로 비율은 1 이상입니다. 하한이 구속하지 않으면(`estimate == base`) U4 값이 **비트 그대로** 남습니다.
     - SHO 옵션은 바꾸지 않습니다(SHO:63). 바뀌는 것은 어댑터가 넘기는 콜백뿐입니다.
   - 계측: `u4_saturation.head_floor_scaled_groups`(비율 > 1인 그룹 수·최대 비율)
   - 시험: T1a는 RS:128 직후가 아니라 **RS:185(LSS configure) 뒤의 최종 맵**에서 잽니다.
2. **소유자 제외**(code_map §3.3)
   - 게이트 peel-off 3개: RS:129 `install_gate_onramp_queue`가 U6 A1 값으로 덮습니다. 그 순서를 **단언**으로 고정합니다.
   - LUR CTM 출구 10634/10635/10642: LUR:100-127이 덮습니다.
   - 둘 다 U4가 쓴 값이 최종값으로 남지 않았는지 설치 끝에서 확인합니다.
3. **`lane_group_kinds`**
   - `["internal", "boundary_out", "boundary_in", "off_ramp"]`을 명시합니다. 목록이 이 넷과 다르거나 런타임에 없는 kind(`on_ramp`)가 있으면 오류입니다.
   - U4가 켜져 있으면 헤드 하한 멤버 함수(A:4561-4603)는 **계약 구성원**을 읽습니다. `lane_group_kinds`는 "계약 구성원의 kind ⊆ 선언" 검사에 씁니다.
   - 이 방식으로 `21|p3`(`link_to_origins['21'] = ['SC108_to_SC109']` 오매핑으로 구성원 0)도 해결됩니다 [읽음 U4 결과 §7-2].
   - SHO 옵션은 바꾸지 않습니다(§2-6).
4. **route-choice 회랑**
   - RS:174-182가 넘기는 스칼라 `per_lane`을 **그룹 조회 함수**로 바꿉니다(RCC:58, :296, :397, :431, :520, :531, :871, :884).
   - U4가 켜져 있는데 스칼라가 넘어오면 오류입니다. 키가 없으면 옛 스칼라를 그대로 넘기므로 비트 동일입니다.
   - 10634 풀의 불변식 `service == cap`(LSS:58)은 두 값이 같은 조회에서 나오므로 유지됩니다.
5. **pre-head 1093**
   - NIP:266-268과 AGG:276-278의 예산 참조를 "기준 movement 용량 × 첫 헤드 차로(2)"에서 첫 헤드 그룹(1220012001|p3)의 `B_g`로 바꿉니다.
   - 두 파일을 **같이** 바꿉니다. 입력 번호는 1083이 아니라 1093입니다(code_map §3.2). 설치 검사 NIP:99-102도 맞춥니다.
6. **LOR direct·local_upstream**(LOR:51, :56 [읽음, 이번에 재확인]): 키가 있을 때만 `movement_capacity_veh_h`(1400) × 차로를 표 기본값 × 차로로 바꿉니다.
7. **경계 movement allocation 점검**
   - 경계 kind의 방류 상한은 `min(allocation, ceiling)`입니다(UQM:752-767) [읽음, 이번에 재확인].
   - `[검토 C-14]` 최종 action의 `inflow_outflow_allocation`은 S1 T3600과 R-obs-b T2700 모두 `{}`입니다 [실행: 결정 JSON 읽기]. 따라서 최종 action에서는 ceiling이 곧 U4 값입니다.
   - SDMPC **후보** 제어가 이 필드를 채우는지는 아직 모릅니다(`signal_actuation_contract.py:637`은 탐침에서 `{}`로 둠) [추론].
   - 설치 메타에 "allocation < 표 값인 경계 movement 수"를 결정마다 기록하고, T1에서 0인지 봅니다. 0이 아니면 U4가 경계에서 무력하다는 뜻이므로 멈추고 보고합니다.
8. **메타**: `projection_diagnostics['u4_saturation']`에 표 sha, 적용 그룹 수, 기본값 적용 movement 수, 소유자 제외 목록, allocation 구속 수를 넣습니다.

### 4.5 U5 물리 헤드 그룹당 공유 방류 자원

1. **계약 로더** `configure_shared_head_groups(cfg, tuning, state_json)`: 새 모듈 `evaluation/controllers/shared_head_groups.py`에 둡니다(처음 판은 HSR, `[검토 C-15]`로 바꿈).
   - 설치 위치는 RS:207-210 뒤입니다. 병합, 현시 권한, U3, 회랑, 풀, native 입력 설치가 모두 끝난 시점입니다.
   - finalize는 RS:245-247 뒤입니다. 71 위임 행 때문에 `lane_urban_runtime`이 있어야 합니다.
   - 검증 항목
     - 망 sha(HSR:44-51 방식)와 inpx 재계산 행이 바이트 단위로 일치
     - 구성원의 kind·origin·수신·현시가 기록과 같고 `ramp` 필드가 없음
     - 구성원 출구 커넥터 = U1 물리 커넥터
     - laminar 집합, 구성원 완결성(§4.3-2)
     - `head_resource_contract`와 공존하지 않음, C3 결합
     - `[검토 C-3]` **U5가 실제로 돌 경로가 설치됐는지** 확인합니다.
       - 회계 substep(UFA)은 `control_area_enabled`·`sc2001_corridor`·`route_choice_corridor`·`native_internal_inputs` 중 하나가 있을 때만 설치되고 호출됩니다(UFA:978-985, :993-997). 없으면 vendor 원본 substep이 돌고, U5 할당기는 **조용히** 빠집니다.
       - 그래서 `_uqm.urban_substep._control_area_events`가 참인지 단언합니다.
       - off-ramp 구성원이 있는 그룹(127|p3·p4)은 `state.lane_offramp_runtime`이 있어야 합니다. 없으면 옛 배수(UFA:88-155)가 예산을 우회하므로, 첫 스텝에서 `ValueError`를 냅니다.
   - 결과는 `cfg.network.shared_head_groups`에 둡니다.
     - `[검토 C-21]` 계약 문서 전체(약 770 KB)가 아니라 **압축된 런타임 형태**로 둡니다: 그룹 → (구성원, 차로 집합, s_g, laminar 집합, 소유자). `follower.cfg`가 tangent 요청마다 워커로 넘어가기 때문입니다.
2. **스텝 할당기** `group_allotments(state, control, cfg, step)`
   - 위치: UFA:516(램프 루프 끝)과 :521(off-ramp 배수 호출) 사이 [읽음, 이번에 재확인]
   - 가중치
     - 정규 구성원: 도착 반영 뒤의 큐
     - off-ramp 배수 구성원(SC1001 offW/offE): **β × `port.ready()`**(`physical_urban_transport.py:91`)입니다. 조회는 상태를 바꾸지 않습니다.
       - `[검토 C-4]` `port.stock`이 아닙니다. 지금 LOR:47·:69는 `stock`으로 요청을 만듭니다. 그런데 LOR 모듈 설명대로 커넥터를 **주행 중인** 차량도 stock에 들어 있습니다("Connector travel is part of its existing stock", LOR:3).
       - stock을 가중치로 쓰면 아직 정지선에 없는 off-ramp 차량이 127 예산을 가져가고, 정규 구성원이 과소 서비스됩니다.
     - `[검토 C-4]` **순차 잔여.** 같은 스텝 안에서 LOR 실행(:521)이 정규 방류(:538)보다 먼저입니다.
       - 포트 물리(`port.release` < 배정)로 쓰지 못한 off-ramp 몫은 같은 스텝의 정규 구성원 배정에 되돌립니다. 순서가 고정이라 순환이 없습니다.
       - 하류 수신 공간 때문에 막힌 몫은 §10-5대로 되돌리지 않습니다.
     - 기본 귀속(C2 없음)에서는 127 정지 차량 일부가 off_ramp kind movement 큐에 들어가 영영 서비스되지 않습니다(UFA:533-534). 이 큐는 가중치에도 서비스에도 들어가지 않습니다. 이중 계상은 아니지만, 127 행의 C3 판정은 C2와 함께 봐야 합니다(§6.4).
   - 요청: `r_m = min(a_m, s_g × |lanes(m)| × T × φ_g)`
   - 모든 laminar 제약이 풀려 있으면 `x = r`(U5 무작동)입니다. 넘으면 위에서 아래로 water-filling합니다. 한 그룹 구성원은 최대 6개입니다.
   - 하류가 막힌 몫은 같은 스텝 안에서 재분배하지 않습니다.
   - `φ_g`는 구성원과 **같은** `_uqm._phase_green_fraction` 호출입니다. 그래서 정확·연속 경로가 저절로 맞고 캐시도 공유됩니다.
   - 결과는 스텝 문맥에 둡니다(cfg가 아님).
3. **UFA 적용**
   - `[검토 C-13]` 정확한 자리는 `_corridor_intended`(UFA:539-540) **뒤**입니다. 회랑 함수가 `intended`를 다시 쓰기 때문에, :538 바로 뒤에 걸면 덮일 수 있습니다.
   - UFA:540 뒤, :541-542 `movement_limits` 기록 **전에** `intended = min(intended, x_m)`를 겁니다. 그래야 `urban_movement_intended_limit`(:584)이 강제된 한도를 기록하고, spatial(:552-559)·일반(:561-574) 두 수신 분기가 모두 덮입니다.
   - 수락은 :590 옆에서 `budget.accepted`로 기록합니다.
4. **LOR 요청/실행 분리**
   - LOR:59-71을 두 함수로 나눕니다: 요청만 내는 함수(상태 불변)와 배정 `x_m`을 받아 실행하는 함수입니다. 실행은 `service = min(service, x_m)`입니다.
   - `assert_mirrors`(LOR:27-32)와 `port.release`(LOR:73) 불변식을 지킵니다. 기록은 :84에서 합니다.
   - 모듈을 가로지르는 그룹은 127|p3, 127|p4 둘뿐입니다 [읽음 U5 결과 §3].
5. **HSR은 고치지 않습니다** `[검토 C-15]` (처음 판의 "HSR 일반화"를 바꿈)
   - U5 키와 `head_resource_contract`는 함께 쓸 수 없습니다. 그래서 U5가 켜지면 `HSR.view(cfg)`가 None이고, HSR의 10619/10629 경로는 돌지 않습니다(HSR:96-98).
   - HSR:42·:225-226을 계약 기반으로 바꾸면 **키 없음 경로의 코드만** 바뀝니다. 비트 동일 위험만 늘고 얻는 것이 없습니다.
   - 그래서 U5는 새 모듈(`evaluation/controllers/shared_head_groups.py`)에 두고, HSR은 승격 때 통째로 격리합니다.
   - 대체되는 값 [실행 S1 T3600 metadata]
     - 10619 관측 하한 970.8 → U4 183|p3 기본값 1,850 × 4 = 7,400(구성원 하나라 예산은 무작동)
     - 10629 3,060 → 52|p3 예산 1,859.7 × 3 = 5,579.1
6. **LSS 10634 풀은 그대로 둡니다.** 71|p3·p4는 LUR CTM이 차로 단위로 강제하므로 위임하고 증거만 기록합니다.
7. **pre-head 1093**: §4.4-5의 `B_g`에서 W/N 소비를 뺍니다. 기존 prehead 우선 규칙은 유지합니다(§10).
8. **장부**
   - 그룹마다 스텝마다 닫을 때 `record_resource_allocation('shared_head_group_budget', 'head:<g>', B_g, 수락_by_source)`를 기록합니다. 위치는 UFA:1000-1011이고, 원장이 포착 중이면 초과 시 CAO:353-356이 예외를 냅니다(아래 `[검토 C-2]`).
   - 중간 laminar 집합은 `shared_head_lane_set`, 구성원은 `shared_head_member_allotment`(UFA:576-599, LOR:79-106)으로 기록합니다.
   - **scope는 기존 `urban_allocator` 안에서 씁니다.** CAO:397-400 허용 집합, `lane_coupling.py:61-69`, `area_freeway_accounting.py:544-552`를 고치지 않습니다. 한 곳이라도 빠지면 SDMPC 후보가 전부 infeasible이 되는 위험(sdmpc.py:605-609)을 피하기 위해서입니다.
   - 완결성은 U5 자체 계수(할당기 호출 수 = 도시 스텝 수)로 봅니다(§10).
   - 위치 주의: UFA:1000-1006은 `legsplit_substep_accounted` 반환과 LUR `advance` 사이입니다. 그룹 닫기는 LUR advance(:1006) **뒤**에 둡니다. 71 위임 증거가 그 뒤에 나오기 때문입니다.
   - `[검토 C-2]` **장부 예외는 항상 켜져 있지 않습니다.**
     - `record_resource_allocation`은 원장이 응답을 포착할 때만 검사합니다(CAO:335-336 `if not self.captures_response: return`).
     - 포착을 켜는 곳은 `area_follower_objective.py:506·:510`과 `sdmpc_tangent_worker.py:249`뿐입니다. 한 스텝 투영, 포착 없는 예측, 캐시 경로에서는 초과가 있어도 예외가 나지 않습니다.
     - 그래서 할당기는 **자체 원시 단언**을 가집니다. LOR:74-75처럼, 원장과 관계없이 매 스텝 `Σ 실행 ≤ B_g + 1e-7`(모든 laminar 집합 포함)을 확인하고 넘으면 `ArithmeticError`를 냅니다. 비교는 primal 값으로 합니다.
     - 장부 기록은 그 위의 추가 증거입니다.
9. **거부**: U5 키와 `sdmpc_spatial_receiving`이 함께 있으면 `ValueError`입니다. 기각된 고속경로라 커널(SPAT:106-149)을 고치지 않습니다.
10. **메타**: `projection_diagnostics['shared_head_groups']`에 계약 sha, 구속 그룹 수, 구속 스텝 수, 최대 초과, 미결 과대 그룹 목록을 넣습니다.
11. **미결 행의 정적 축소** `[검토 C-6]`
    - 대상: 사용자 결정 전의 과대 행(현시 불일치 3, native 12)
    - 이 행들에 예산을 걸지 않고 U4 값을 그대로 두면, 그 그룹에서는 U4 단독이 됩니다. 1,850/차로 척도에서 ×4(SC105·SC1)까지 과대 방류합니다.
    - 그래서 결정 전까지 구성원 용량을 `cap_m = s_g × |lanes(m)| × n_g / Σ_k |lanes(k)|`로 줄입니다. 구성원 합이 정확히 n_g × s_g가 됩니다.
      - 동적 예산이 아니므로 현시(φ)를 맞출 필요가 없습니다. 현시 불일치 행에도 걸 수 있습니다.
      - 한 구성원만 수요가 있을 때 과소 서비스라는 대가가 있습니다. 그래서 과소량을 T1에서 따로 보고합니다.
    - 결정이 나면 그 행을 budget 등급으로 바꾸거나, 사용자 선택대로 처리합니다.
12. **완결성 검사를 폐루프 전에 전수 확인합니다** `[검토 C-16]`
    - 계약 설치의 완결성 검사는 fail-closed입니다. 폐루프에서 이 검사가 걸리면 그 결정이 실패하고, 150 s 동안 제어가 없습니다.
    - 그래서 C3 후보 튜닝으로 R-obs-b 61상태, S1·S0e 결정 상태 전부에서 "흐름 구성원 집합 = 계약 집합"을 오프라인으로 확인합니다. U1 β는 정적 증거라 같아야 하지만, `apply_dead_phase_beta_zero` 같은 설치기가 상태에 따라 β를 0으로 만드는지 이 확인으로 봅니다.

### 4.6 U6 W측 램프 분기 (`physical_diverge_v1`)

u6 §7.2 표를 그대로 구현합니다. 부분 조합 값은 만들지 않습니다(A1만 넣은 vA는 10482 유입 +54.5, 재고 +32로 나빠짐 [읽음 u6 §5.4]).

| # | 위치 | 구현 |
|---|---|---|
| A1 | `install_gate_onramp_queue` A:3380-3416 | `capmap[m] = lanes × diverge_lane_capacity_veh_h`(증거 1800/차로). 정책이 켜져 있는데 `gate_onramp_queue_capacity_veh_h`가 있으면 오류 |
| A2 | `seed_urban_arrival_buffer` A:10022-10097 다음 새 단계, `area_runtime.pair_initial_arrival_releases`(:61-87) 확장, 소비 UFA:378-381 | 링크 32·129 위 차량 가운데 결정 1136 경로 1 → onW, 3 → onE, 2 → 정지선. 경로 없는 차량만 β(129는 β_onE/(1−β_onW)), 127 위 차량은 램프 몫 0. 분기 도착 시각 = 거리 ÷ max(차량 속도, 같은 링크 평균 속도, 20 km/h). 정지선 몫의 +15/+105 s는 유지(U7 대상) |
| A3 | UFA:386-393 착지 | 신규 유입의 램프 몫은 `transit:gate:*` 재고에 두고 (분기거리 ÷ v − `_inflow_delay_steps`)만큼 늦게 착지. 장부·TTT 적분은 그대로 |
| A4 | A:2785-2789 등록, A:3419-3476 게이트 β | `SC1004_W_to_onE`는 β 0으로 고정하고 형제를 재정규화(A:3471-3475), 계측에는 남김. 10639는 공유 줄기가 소유 |
| B1 | `_legsplit_wout_rate` A:2876-2900, UFA:607, LOR:95 | L = 증거의 W_out 물리 길이. W_out 진입은 방출 예약 1 s와 v/L 확산만(이중 지연 제거). P:84-88 옛 길이는 정책 경로에서 읽지 않음 |
| B2 | B4b 규칙 A:3190-3193 | 10483 착지 → SC1001_W_tail. SC1004 10682는 현행 유지 |
| B3 | `install_boundary_out_ramp_split` A:8408-8457 | 증거 `split`(1137: 0.5/0.333/0.167, 1135: 0.6/0.2/0.2). `ramp_split_json`과 함께 있으면 오류 |
| C | `projection_diagnostics['ramp_admission']` (정책이 켜져 있을 때만) | 램프별 용량·진입 여유·재고 구속 초, 최소 진입 여유, 적격/비적격 저류 대수, 지연 착지 대수, τ 길이, 분할 출처 |

- **재사용 구성요소**(u6 §7.2): `vehicle_routes.complete_vehicle_routes`, `shared_approach.configure`(:110-152), `route_choice_corridor._validate_path`(:117), 스텝별 due 사전(:230-236), 보존 단언(`advance` :279-281, :356-358). 증거 검증은 `known-wout-routes/v1`(RCC:945-966) 방식을 따릅니다.
- **건드리지 않는 것**
  - `PhysicalRampBoundary.capacity_veh`와 진입 여유 식(PRB:352-357)
  - 공용 `ramp_capacity_veh_h`
  - 미터 헤드·합류
  - 09-03 정본(주입·관측·β 결합), 게이트 β 식과 합 클램프 0.85
- **새 상태 필드**(A2·A3 스케줄·표지)는 `TrafficState.copy()` 깊은 복사에 들어가고, 예측·응답 캐시 상태 키에도 들어가야 합니다(u6 §7.5).

### 4.7 C2 = U2 (경로·차로 기준 큐 귀속)

1. **구현은 이미 있습니다**(A:5105-5120, :5133-5181, :5225-5376, :6444-6506). 증거는 `route_queue_attribution_v3b_20260925.json`(`ec8697a4…`, CFGB1:7882-7886)입니다.
2. **가시성 수정** (하나뿐)
   - `queue_attribution_route`의 `totals`(A:6789-6792)와 증거 sha를 `projection_diagnostics['queue_attribution_route']`로 옮깁니다.
   - 키가 `"route"`일 때만 씁니다. 키가 없으면 필드가 없어 비트 동일입니다.
   - `derived_<T>.json`은 건드리지 않습니다. MRS 비교 대상이기 때문입니다(MRS:257-271).
3. **정의 정합 확인**
   - U2는 off-ramp 출신 127 정지차를 "같은 출구의 served movement"로 보냅니다(A:5275).
   - U5의 127 예산은 정규 큐(링크 127 위 차량)와 LOR 포트 재고(10491·10481 위 차량)를 나누므로 **같은 차량이 두 번 세이지 않습니다** [추론].
   - U6 A2와 U2는 같은 경로 관측(`vehicle_routes`)을 읽습니다. 127 접근로 합(큐 + 저류)은 한 스텝 표에서 함께 봅니다.
4. **포함 규칙**: C2는 §6.8 증분 관문을 통과할 때만 최종 후보에 넣습니다. 실패하면 뺀 이유를 보고하고, 조용히 빼지 않습니다.

### 4.8 후보 config 생성

- `make_config_n31.py`에 `apply_urban_batch2(doc, components)`와 `--urban-batch2 --components C3[,C2][,C6]`을 더합니다(:249 `apply_urban_batch1` 옆). 기준은 U1+U3 `f88d05f1` 내용이고, 모든 키를 명시합니다.
- 산출 파일(`diagnostics/sdmpc_n31_20260924/`)

| 파일 | 내용 | 쓰임 |
|---|---|---|
| `config_n31_v2_urban_b2_c3.json` | U1+U3 + C3 | 묶음 판정 |
| `config_n31_v2_urban_b2_c3c2.json` | + U2 | C2 증분 |
| `config_n31_v2_urban_b2_c3c2c6.json` | + C6 | 최종 후보 (C2 탈락 시 `_c3c6`) |
| `config_n31_v2_urban_b2_c6.json` | U1+U3 + C6 | G-C6-0 비트 동일 |

- 생성기는 C3 세 키가 모두 있는지, 증거 세 파일의 sha가 일치하는지 확인합니다. `--check`는 바이트 재현을 확인합니다.
- 기본 config(`config_n31_v2.json`)는 U4-0 명시 외에는 바꾸지 않습니다.

---

## 5. 시험 목록

### 5.1 단위 시험 (새 파일 `diagnostics/sdmpc_n31_20260924/tests/test_n31_urban_batch2.py` + 기존 파일 확장)

| 묶음 | 시험 |
|---|---|
| U4-0 | 올린 키 누락 → 오류, 알 수 없는 kind → 오류, `install_lane_group_membership`이 옛 부작용(`_LG_KINDS`·`_LTO`)과 같은 값을 만든다 |
| U4 | 표 스키마·망 sha 불일치 실패. `equivalent_uniform_veh_h`·`per_lane`·`perimeter`와 공존하면 오류. C3 결합 오류(하나·둘만 있을 때). `cap_m = s_g × \|lanes(m)\|`. 그룹 밖 movement는 기본값 × 차로. 게이트 peel-off 최종 용량 = A1 값, LUR 출구 최종 = LUR 값. `21\|p3`에 `SC108_W_to_E_SC109`가 구성원으로 들어간다. RCC에 스칼라가 오면 오류, 조회 값이 맵 값과 같다. NIP·AGG 예산 동일. LOR direct가 기본값 × 차로. `on_ramp` kind 선언은 오류 |
| U5 | 계약 로더(망 sha, inpx 재계산 불일치, 구성원 kind·현시·ramp, laminar, 완결성 허용 목록 밖 흐름 movement는 실패, `head_resource_contract` 공존 오류). 할당기: 여유 있으면 `x = r`, 초과 시 water-filling 결과 Σ ≤ B, 모든 laminar 집합 만족, 가중 0 처리, 막힌 구성원 몫 재분배 없음, 결정론(순서 = 최소 차로, 이름). LOR 분리 뒤 `assert_mirrors`·`release` 불변. 초과 수락은 `record_resource_allocation` 예외. spatial + U5는 오류 |
| U6 | 정책 값 검증(없음 / `""` / `physical_diverge_v1` / 그 밖 오류). 증거 로더(망 sha, 1136·1137·1135 inpx 대조). A1 용량. A2 적격(경로 1/2/3/없음, 127 위 0)과 도착 속도 규칙. A3 지연 착지 질량 보존(transit 재고). B1 τ = L/v, 이중 지연 없음. B2 착지 대상. B3 분할. A4 β 0과 형제 재정규화. 공존 금지 두 키 |
| C2 | 키 `"route"`면 `projection_diagnostics.queue_attribution_route` 있음, 키 없으면 필드 없음(JSON 바이트 동일) |
| C6 | 설정 검증(네 키 필수, 타입, 모르는 키 거부). 키 없으면 import 안 함. 합성 이전 JSON으로 스트릭(유효 prior / `run_id` 다름 / `sim_sec` 어긋남). 경계 비율. 내부 예외가 결정을 실패시키지 않음. 새 필드에 `controller_status`·`decision_wall_sec` 문자열 없음(대소문자 무시) |
| 검토 추가 `[검토 C-1~C-16]` | (U4) 차로 비율 보존 `distribute`: `estimate == base`이면 U4 값 비트 동일, `estimate > base`이면 비율 배율. 계약 2단계 적재(RS:128 부분, RS:207 뒤 전체). 차로 파일 핀 누락 시 실패. `lane_group_kinds` ≠ `["internal"]` + C3 키 없음 → 오류. (U4-0) `_SUS_SIGS`를 옛 부작용과 비교, A:4570 대체 계수. `perimeter_include_boundary_out` 누락 → 오류. (U5) 회계 substep 미설치 → 오류, LOR 없음 + off-ramp 구성원 → 오류. 가중치가 `port.ready()`(stock 아님). 포트 물리 부족분의 순차 잔여 반환, 하류 막힘 몫은 반환 없음. 자체 원시 단언이 포착 없는 원장에서도 예외. 정적 축소 합 = n_g × s_g. 적용 자리가 `_corridor_intended` 뒤. (C6) stdout 512바이트 상한, stderr 0바이트, C6 전후 `cfg.network`·`state` pickle 해시 동일 |

- 기존 스위트(§4.0-2)는 전부 통과해야 합니다. 206.53 가정 fixture는 §4.0-4 목록으로 "U4 키 있음/없음" 두 벌로 나눕니다.

### 5.2 단언: 그룹 합 ≤ 차로 × s × g (매 스텝)

- **런타임 단언** `[검토 C-2]`: 할당기의 **자체 원시 단언**(§4.5-8)이 모든 경로·모든 스텝에서 `Σ 실행 ≤ B_g + 1e-7`을 확인합니다. laminar 집합도 같습니다. 원장 포착과 관계없습니다.
  - 처음 판의 "CAO 예외가 모든 예측에서 검사된다"는 틀렸습니다. CAO:335-336은 포착하지 않는 원장에서 바로 반환합니다.
  - CAO 기록(상대 1e-9·절대 1e-7)은 포착하는 평가에서만 생기는 추가 증거입니다.
- **오프라인 전수**: R-obs-b 61상태 × 정확 450 s × 모든 그룹에서 초과 0을 확인합니다. 연속 경로(tangent 워커)와 route-bins 경로에서도 같은 계수를 모읍니다.
  - `[검토 C-2]` **공허 통과 금지.** 판정 전에 "검사 수 = 그룹 수 × 스텝 수 > 0"을 먼저 확인합니다. 자체 단언 계수와 (포착하는 하네스라면) `shared_head_group_budget` 기록 수를 봅니다.
  - 하네스는 포착을 켠 원장으로 돌립니다. 기록이 0개인데 `max_exceedance == 0`이면 실패로 칩니다.
- **질량**: 같은 스텝에서 `shared_head_group_budget`의 Σ수락_by_source가 해당 구성원의 방출 transfer 합과 같아야 합니다. `assert_stocks` 최대 |추적 − 모형| ≤ 1e-8입니다(묶음 1: 9.9e-9).

### 5.3 세 예측 경로 · 캐시 · AD 대 FD (`harness/check_paths.py`, T2700 + S1 3600 상태)

| 비교 | 기준 |
|---|---|
| 정확 대 반복, 캐시 on/off | 차이 0 |
| route-bins(`no_agg`) | ≤ 1.6e-13 |
| 연속 완화 대 정확 | 도시 owner 최대 차이 ≤ 0.013 (묶음 1 대역). 71 그룹(CONT:136-139 LUR GREEN 치환)은 따로 표시 |
| AD 대 스칼라 | ≤ 3.6e-15 수준 |
| tangent 대 FD (h = 0.01, 중앙차분) | \|AD − FD\| ≤ max(0.05·\|FD\|, 0.03). 꺾임점에서는 AD가 [min(FD−, FD+), max(FD−, FD+)] 안에 있어야 함. 꺾임점은 목록으로 보고 |
| U6 초 단위 W측 지표 (W_to_onW, 램프 유입·재고, W_out) | 세 경로 동일, 연속 경로는 미터 보간 차이만 허용 |

### 5.4 키 없음 비트 동일

§6.1 G-ID(a)~(d)입니다. 단위 시험이 아니라 재생 관문입니다.

### 5.5 LIVE 판정 (새 코드가 실제로 도는가)

- `harness/livecheck.py`를 C3 후보로 한 번 돌립니다(S1 3600 복사 상태, 첫 도함수 요청에서 멈춤). 기대 호출 수는 아래와 같습니다.

| 함수 | 기대 호출 |
|---|---|
| `group_allotments` | 450 / 예측 |
| `install_movement_capacity_by_saturation` | 1 |
| 옛 `install_movement_capacity_by_lanes` | 0 |
| U6 A2 설치 | 1 |
| A3 지연 착지 경로 | > 0 |
| `LaneOfframpRuntime` 요청·실행 | 각 450 |
| `starvation_monitor` | 1 / 결정 (C6 키가 있을 때) |
| `[검토 C-1]` `_distribute_lane_group_capacity_by_u4_ratio` / 옛 `_distribute_lane_group_capacity_to_movements` | > 0 / 0 (U4 켜짐, 설치 단계) |
| `[검토 C-2]` U5 자체 원시 단언 | 450 / 예측, 원장 포착 여부와 무관 |
| `[검토 C-3]` UFA `urban_substep_accounted` | 450 / 예측 (vendor 원본 substep 0) |
| `[검토 C-15]` HSR `regular_batch`의 구성원 있는 호출 | 0 (U5 켜짐, 10629 풀은 계약 행이 대체) |

- 해석기 두 개는 SDMPC-31을 판정하지 못하므로 쓰지 않습니다.

---

## 6. 오프라인 관문

모든 관문의 비교 대상은 **U1+U3(b2 트리, 키 없음)**입니다. 상태는 v3b에 핀돼 있습니다.

### 6.1 G-ID: 키 없음 = 비트 동일

- (a) **R-obs-b 61상태, 평탄화한 기본 튜닝**: `MRS compare` IDENTICAL 61/61 (derived, action_csv, CONTROL_FIELDS, objective, action_contract)
  - 한계 [실행]: R-obs-b는 `controller_variant: "no-control"`이라 SDMPC 최적화 경로를 덮지 않습니다.
- (b) **같은 61상태, U1+U3 튜닝**
  - cf3ce37 트리 재생과 b2 트리 재생의 action JSON 비경로 차이가 0이어야 합니다.
  - `b1_capture` 한 스텝 포착(β·큐·재고·방류·녹색)이 바이트 동일해야 합니다.
- (c) **SDMPC 경로**: 결정 재생 5회가 기록과 녹색·offset이 비트 동일해야 합니다.
  - S1 상태 1800 / 3600 / 6300 (U1+U3), S0e 상태 1800 / 3600 (기본)
  - 비교는 action_csv·action_controls·objective 세 검사로 합니다. 두 런에 VSL 100이 섞여 `action_contract`는 제외합니다(SC109_DIAG §4).
  - `[검토 C-12]` 처음 판의 "xreplay가 이 재현을 이미 확인했다"는 과장이었습니다. 확인된 것은 셋뿐입니다.
    - S0e × 기본 1800·3600: XREPLAY_RESULT:10, :17
    - S1·S0e 3600: SC109_DIAG:292-293 `r3600`, `action_contract`만 DIFFERENT
    - **S1 × U1+U3 1800·6300은 자기 설정 재현이 아직 확인되지 않았습니다.** 단계 0(§4.0-3)에서 cf3ce37 트리로 먼저 재현합니다. 재현되지 않으면 그 상태를 재현되는 S1 상태(예: 2700·4500)로 바꾸고 이유를 기록합니다.
- (d) **C6 키 있음**(`_c6.json`): (a)·(c)에서 action_csv가 동일해야 합니다. 결정 JSON 차이는 `metadata.starvation_monitor`뿐, stdout 차이는 `"starvation"` 필드뿐이어야 합니다.
- U4-0 뒤와 각 단계 커밋 뒤에 (a)·(b)를 다시 받습니다. (c)는 U4-0 뒤와 최종에 받습니다.

### 6.2 기준선 재현 (관문 전제)

§4.0-3의 T3·세 경로·FD 값이 b2 트리에서 그대로 나와야 합니다.

### 6.3 T1: 그룹 용량이 실측의 0.8~1.2배

- **T1a 설치값**: 계약의 모든 행에서 유효 그룹 상한이 n_g × s_g여야 합니다. 구성원 상한 합이 그룹 상한을 넘는 그룹은 전부 예산 등급이어야 하고, 누락은 0이어야 합니다(미결 행은 정적 축소로 합 = n_g × s_g, 별도 계수).
  - `[검토 C-1]` 잴 곳은 RS:185 뒤의 **최종** 맵입니다. 헤드 하한(RS:145), 회랑(RS:176), LUR, 게이트 peel-off가 모두 덮은 뒤입니다. `head_floor_scaled_groups`도 함께 봅니다.
  - `[검토 C-20]` 단계 4·5에서는 C3 결합 때문에 config로 U4만 설치할 수 없습니다. 그래서 그때의 T1a는 하네스 메모리 패치나 단위 시험으로 보고, 설치 경로의 T1a는 단계 7에서 받습니다.
- `[검토 C-20]` T1b의 성격: 포화 녹색초에는 예산이 곧 n_g × s_g × φ라서, T1b는 모형 충실도가 아니라 **구현 검사**에 가깝습니다. 충실도 판정은 G0(T3 대 FZP)이 맡습니다.
- **T1b 행동**
  - R-obs-b 61상태의 정확 150 s 예측에서 "포화 녹색초"를 봅니다. 녹색이고 구성원 요청 합이 남은 예산보다 큰 초입니다.
  - 그 초들의 그룹 방류율이 U4 표 실측값의 **0.8~1.2배**여야 합니다.
  - 대상: 실측 그룹 65개와 다중헤드 3개 가운데 포화 녹색초가 60초 이상인 그룹
  - 다른 제약(수신·회랑·prehead·LUR)이 구속한 초는 따로 분류해 보고합니다.
- **G-U5-2** `[검토 C-5]` (처음 판: "127|p3 3,600~3,935, 127|p4 1,725~2,025")
  - 옛 범위는 v2 보고서 값입니다(URBAN_FIX_PROPOSAL :190, :238). v3b U4 표에서 127|p4는 **2,058.3 veh/h/차로 × 1차로**입니다 [실행]. 예산이 이 값을 쓰면 포화 녹색초 방류가 2,058이 되어 옛 상한 2,025를 **구조적으로** 넘습니다. 127|p3는 1,899.7 × 2 = 3,799.4로 범위 안입니다.
  - 새 기준(v3b): 포화 녹색초의 그룹 방류가 n_g × s_g(U4 표 v1)의 ±5% 안이어야 합니다.
  - 교차 확인: 같은 표의 주기별 방류율 p25–p75 안이어야 합니다(127|p4 1,920–2,160, 127|p3는 표 값으로 계산).
  - 옛 v2 범위는 참고로만 적습니다.
- **G-U5-127 (새 관문, 모듈 경계)** `[검토 C-4]`
  - 배경: 127 차로군은 UFA 정규 방류와 LOR off-ramp 배수가 나눠 씁니다. 옛 B3 실패(메모리 `vissim-offramp-drain-share-semantics`: 무신호 출구가 저장고를 비움 → SC1001 꼭짓점 → 링크 32 잠김 → off-ramp 본선 역류 +1002)는 이 몫이 틀릴 때의 폐루프 비용을 보여 줍니다.
  - (a) 127|p3·p4 포화 녹색초 방류 중 off-ramp 출신 비율: FZP 같은 창의 비율 ±0.10. FZP에서는 10491·10481을 거쳐 127 헤드를 지난 차량으로 셉니다.
  - (b) off-ramp 저장고 10491·10481 재고의 한 스텝 편향: U1+U3보다 나쁘지 않을 것(짝 CI 하한 > 0이면 실패)
  - (c) 저장고 만차 초: 늘지 않을 것
  - (d) 순차 잔여로 되돌린 양과 하류 막힘 몫을 따로 보고
  - C3 단독과 C3+C2를 모두 잽니다. 판정은 C3+C2로 합니다(§6.4).
- **위임 그룹** 71|p3·p4: LUR 차로 `capacity_rate`를 실측(71|p3 1,724, 방해 포함 1,569)과 비교해 보고만 합니다. 벗어나도 묶음 2에서 고치지 않고 따로 보고합니다.
- **경계 allocation 구속 수 = 0**(§4.4-7)

### 6.4 G0: R-obs-b 61상태(54전이), T3 한 스텝 지표가 U1+U3보다 나쁘지 않을 것

- **지표**: A1–A3(접근로 재고, 150/300/450 s), B1–B3(물리 그룹), C(한 스텝 방류 대 FZP). 정의는 `urban-b1d/t3_arms.py`와 같습니다.
- **판정**: (C3 − U1+U3) 짝 증분의 95% bootstrap CI(2,000회 재표본)를 봅니다. **하한이 0보다 크면 실패**입니다(유의하게 나빠짐).
  - 전이는 계열 상관이 있고 seed 31 하나라는 한계를 같이 적습니다.
  - `[검토 C-18]` iid 재표본은 상관 있는 54전이에서 CI를 좁게 잡습니다. 그래서 이동 블록 bootstrap(블록 5)도 함께 계산해 두 값을 보고합니다. 판정은 **둘 다** 하한 ≤ 0이어야 통과입니다.
- **접근로별 표**: SC1001 W(127), S(40), SC1004 W(71)를 따로 봅니다. G-v3b (a) 기준은 |편향| ≤ 50, MAE ≤ persistence입니다.
  - `[검토 C-4]` **127 행은 C3+C2로 판정합니다.** C2가 없으면 기본 귀속이 127 정지 차량 일부를 off_ramp kind movement 큐에 넣고, 그 큐는 서비스되지 않습니다(UFA:533-534). 그래서 C3 단독의 127 값에는 알려진 결함이 섞입니다. C3 단독의 127 행은 보고만 합니다.
- `[검토 C-17]` 제안서 G-v3b의 (b)·(c)는 여기서 판정하지 않습니다.
  - (b) V5b 상태 회귀는 v2 망 상태라 v3b에 핀한 표·계약이 설치에서 실패합니다. 적용할 수 없습니다.
  - (c) U10 비율 기준은 묶음 2 범위 밖입니다.
  - 둘 다 뺀 이유를 최종 보고에 적습니다.
- **U3 회전**: 10377, 10686 한 스텝 방류 대 FZP를 봅니다(10686은 묶음 1에서 8.3 대 33.1로 U4 대상이었습니다).
- G0에는 세 경로(§5.3)와 시간(§6.7)도 포함됩니다.

### 6.5 U6 관문 (R-obs-b 54상태, 모형 한 스텝 대 같은 창 FZP) [기준값 읽음 u6 §8]

| 관문 | 기준 | 참고: base | 참고: vFULLrK(9상태 대리) |
|---|---|---|---|
| G6-1 분기 대기 | W_to_onW·W_to_onE 큐 T+150 p90 ≤ 2대 | p90 163 | 0 |
| G6-2 10482 유입 | \|평균 편향\| ≤ FZP 평균의 10%, r ≥ 0.8 | −1.0, r 없음 | −3.2, 0.98 |
| G6-3 RM_C10482 재고 | MAE ≤ 5, r ≥ 0.5 | 6.7 | 5.1, 0.79 (경계, 54상태로 재측정) |
| G6-4 10490 | 유입 \|b\| ≤ 5, 재고 \|b\| ≤ 3 | +27.4 / +9.6 | −0.3 / −0.8 |
| G6-5 SC1004 W_out | \|b\| ≤ 5 | +60.4 | +0.7 |
| G6-6 (묶음) SC1001 W_out 출구분, 10484/10480 | W_out \|b\| ≤ 5, 램프 유입 \|b\| ≤ FZP 평균의 20% | +30.9 / −4% / −9% | −4.2 / −3% / +11% |
| G6-7 (묶음) W 정지선 큐 ~ 127 정지 | \|b\| ≤ 20, r ≥ 0.5 | −30.4, −0.08 | −16.9, 0.95 |
| G6-8 계측 | 진입 여유 구속 초가 메타에 기록되고, 미터 개방에서 0 | – | – |
| G6-9 SC1004 10639 유입 | \|b\| ≤ 2대/150 s, r ≥ 0.9 | +1.2, 0.96 | 공유 줄기만 −0.8, 0.96 (산술 대리) |
| G6-10 | G-v3b §6.6 | – | – |

- W_out 비교는 FZP의 SC1001 출구 차량분(`wout_sc1001`)으로 합니다.
- vFULLrK는 **대리**였습니다. 이번에는 실제 U4·U5 코드로 다시 잽니다.
- 폐루프 서술: S0e·S1 상태에서 G6-1~G6-4의 방향이 같아야 합니다(u6 §6.2 방식).

### 6.6 G-SC109 (S1 3600/4500/6300/7650, S0e 3600/6300, C3 후보 튜닝)

| 관문 | 기준 | 도구 | 참고 (현 결함 상태) |
|---|---|---|---|
| (a) | "p3 +20 / p4 −20" ΔJ < 0 (6300은 SC109_DIAG와 같은 ±25) | `harness/cf_driver.py`: 기록 action 고정 plant 반사실 | 현 +0.759 / +1.250. 서측 직진 2,541 대리 −1.72 / −1.53, 서+동 −2.38 |
| (b) | plant 150 s W→E 방류가 같은 녹색의 VISSIM 통과의 0.8~1.2배 (20~24 s 녹색에서 33~42대) | 같은 반사실의 served | 현 용량 619.6 = 녹색초당 0.172대 → 20~24 s 녹색에서 약 3.4~4.1대 [추론, 산술]. U4 1,900 × 3차로면 22 s에 약 34.8대 |
| (c) | C3 후보로 결정 재생해 고른 p3가 NC 수요에 필요한 녹색 이상(3,600~4,500 s 약 38 s, 이후 25~31 s)이거나 적어도 하한 20 s가 아님 | 결정 재생(MRS prepare + 어댑터, 또는 `xreplay/alt_replay.ps1`) | 기록 S1 21.9~23.8 s |
| (d) | plant 북측 방류가 용량에 묶이지 않음: p2 ≥ 60 s에서 served < 0.9 × 용량 × 녹색 | 반사실 served | 900~2,700 s 두 런 모두 ±5%로 묶임 |

- 한 상태 재생이라 헤드 하한 이력은 원 런의 것을 씁니다. C3의 용량은 정적 핀 표라 한 상태에서도 효과가 보입니다(SC109_DIAG C3).
- G-SC109는 plant가 "왜 그렇게 골랐나"에 대한 관문입니다. VISSIM TTT 개선의 증거가 아닙니다.
- 교차 재생(XREPLAY)이 경로 의존을 보였으므로, 폐루프 판정은 v3c1 다시드 짝으로 합니다.

### 6.7 G-v3b 나머지와 시간

- **(d)** 동측 본선(①)·국소(②)·미터·VSL 한 스텝 오차가 54전이 짝에서 나빠지지 않아야 합니다(CI 하한 > 0이면 실패).
  - U6가 10482 유입을 상수 1,620 veh/h에서 수요 추종으로 바꾸고, 10490 합류 과대(+28대/150 s)를 없앱니다. 그래서 FW 쪽을 반드시 봅니다 [읽음 u6 §9-7].
- **(e) 시간** (P0_REPORT Q17 규약)
  1. **결정론 계수 먼저**: `tangent_derivatives[i].trace`의 `operations`와 `event_counts{primal_comparisons, exact_primal_ties, discrete_comparisons}`
     - `discrete_comparisons`는 **늘면 안 됩니다.** U5 water-filling의 비교는 primal로만 들어가야 합니다.
     - livecheck 보조 계수: 할당기 1회/스텝, water-filling 라운드 ≤ 6/그룹, `receiving_space` 15/스텝 불변, `regular_batch` 증감 설명
  2. **교대 벽시계**: 같은 세션에서 기준과 C3 후보를 결정 3개 × 교대 2회로 재생합니다. 중앙 비 ≤ 1.05이면 통과입니다.
     - 시작할 때 python·VISSIM 프로세스 수를 기록합니다. VISSIM 4개가 도는 동안의 값이면 그렇다고 표기합니다.
     - 예측 1회는 약 45~50 s를 유지해야 합니다.

### 6.8 C2 증분 관문 (C3+C2 − C3)

- G0 지표 증분 CI 하한 > 0이 하나도 없어야 합니다. 묶음 1에서 U2 단독은 A1 +0.12~+0.21, B1 +0.16~+0.19로 실패했습니다. C3 위에서 이 증분이 사라지는지가 핵심입니다.
- S1 4050~8100 상태에서 173/174 서측 직진/좌회전 큐 몫이 FZP 스냅숏 ±0.15 안이어야 합니다(SC109_DIAG C2). 참고로 livecheck S1 3600에서 174는 0.5/0.5 → 0.928/0.072로 바뀌었습니다 [읽음 code_map §6.1].
- G-SC109 (a)~(d)가 C3 대비 유지되어야 합니다.
- `projection_diagnostics.queue_attribution_route`가 결정 JSON에 남아야 합니다.

### 6.9 C6 관문

- **G-C6-0**: G-ID (d)
- **G-C6-1 입력 대조**: 어댑터가 낸 정지 수·하한 유무·녹색·경계 비율이 `B/c6_dryrun.py` 방식의 오프라인 재계산(같은 상수)과 같아야 합니다. 대상 상태는 S1 2700~8100, S0e 3600·7650입니다.
- **G-C6-1b `floor_tol_s` 보정**: {1, 2, 4} 가운데 두 조건을 만족하는 최솟값을 고릅니다.
  - S1 SC109 p3 첫 경보가 4,650 s 이하(원형과 같거나 빠름)
  - S0e SC109 p3 경보 0
  - 기록 궤적 연쇄를 오프라인으로 다시 계산해 판정합니다.
  - `[검토 C-11]` **만족하는 값이 없을 수 있습니다.** 원형 4,650 s는 정지 기준 5 km/h와 "결정 직후 FZP 프레임"으로 나온 값입니다(`s12_starvation_watch.py:30`, :87). 어댑터는 T 시점 차량 기록과 1.0 km/h를 씁니다. 정지 차량이 적게 잡히므로 {1, 2, 4} 어느 값에서도 4,650 s 안에 경보가 안 날 수 있습니다.
    - 그때는 둘째 축으로 M ∈ {8, 6, 4}를 씁니다. S0e SC109 = 0 조건은 그대로 둡니다.
    - 그래도 없으면 1.0 / 8을 유지하고 "원형과 불일치"로 보고합니다. C6는 진단이라 이것이 묶음을 막지는 않습니다.
- **G-C6-2 스트릭**: 합성 prior 단위 시험(§5.1)과 기록 궤적 연쇄 재계산이 같아야 합니다. 재생 도구가 이전 action을 런 폴더에서만 읽으므로 한 상태 재생으로는 스트릭이 0에서 시작합니다.
- **G-C6-3 시간**: 읽은 파일 수와 레코드 수를 먼저 보고, 교대 벽시계로 결정 시간 증가 < 1%를 확인합니다. action JSON 크기 증가와 stdout 바이트 수(≤ 512)도 같이 봅니다.
- **G-C6-4 두 결정 연쇄** `[검토 C-10]` (새 관문)
  - 목적: C6가 쓴 metadata가 **다음** 결정의 행동을 바꾸지 않는지 봅니다. 한 상태 재생(G-ID (d))으로는 이것을 볼 수 없습니다.
  - 방법: S1 3600을 C6 켜고 재생합니다. `MRS.prepare`로 복사한 3750 상태 폴더에서 이전 action을 그 산출물로 바꿔 넣고 3750을 재생합니다. 이것을 기록된 이전 action으로 재생한 3750과 비교합니다.
  - 기준: action_csv·action_controls·objective 동일, 차이는 이전 action sha 핀(A:12927-12929)과 C6 필드뿐
  - 도구 확장이 필요합니다(SC109_DIAG Q4와 같은 종류). 복사본 안에서만 바꾸고, `.applied` 영수증이 가리키는 csv는 그대로 둡니다.
  - 정적 감사(§4.2 통로 2)와 함께 판정합니다.

### 6.10 보조 점검 (관문 아님, 반드시 보고)

- **가격·듀얼**: S1·S0e 결정 재생(§6.1 (c) 5상태 + G-SC109 6상태)의 metadata에서 가격·λ가 0이 아닌 개수와 크기를 전후 비교합니다. 과거 램프 cap 수정이 듀얼로 증폭된 사례(+1432)가 있어서 봅니다.
- **꼭짓점 래칫**: 같은 결정 재생에서 녹색이 하한·상한에 붙은 현시 비율, 국소 기울기 크기 분포를 전후 비교합니다. xreplay 1800~3600 s 상태(각 13개)를 재사용하면 표본이 26개가 됩니다.
- **C6 경보 수**: 같은 재생에서 C3 전후를 비교합니다. 경계 구속 비율(SC109 W→E 약 1.0)이 C3 뒤 떨어지는지를 C3 보조 지표로 씁니다(code_map §8.6).

---

## 7. 작업 순서와 일정

| 단계 | 내용 | 산출·판정 | 작업일 | 재생 벽시계 |
|---|---|---|---|---|
| 0 | 준비: 워크트리, 하네스 매개화, 스위트, 기준선 재현, fixture 목록, 시간 기준선, **S1 1800·6300 자기 설정 재현** `[검토 C-12]` | §6.2 | 0.5–1 | 약 1.8 h (61 포착 + 61 결정 + livecheck + SDMPC 2회) |
| 1 | U4-0 비트 동일 정리(+ `_SUS_SIGS` 대체 계수, 평탄화 diff 검사) `[검토 C-8·C-9]` | G-ID (a)(b)(c) | 1–1.5 | 약 2.5 h |
| 2 | C6 (+ 이전 action 독자 정적 감사, 두 결정 연쇄 도구) `[검토 C-10]` | G-C6-0~4 | 1.5–2 | 약 2 h |
| 3 | 증거 파일 확정 (U4 표 v1 + 다중헤드·native FZP 측정, U5 계약 v1, U6 증거) | `--check`, 교차 일관성 | 2 | FZP 스트리밍(5시드) 수 시간, BELOW_NORMAL |
| 4 | U4 코드(+ 헤드 하한 차로 비율 콜백, 계약 2단계 적재, 차로 파일 핀) `[검토 C-1·C-8]` | 단위 시험, T1a(하네스 패치) | 2.5–3.5 | – |
| 5 | U5 코드(+ 자체 원시 단언, `port.ready()` 가중치, 순차 잔여, 정적 축소, 설치 단언) `[검토 C-2~C-6]` | 단위 시험, §5.2 단언, 10634 동일(하네스 패치로 "U5 없는 C3" 팔) | 4.5–7 | 약 1 h |
| 6 | U6 코드 | 단위 시험, G6 부분(9상태 예비) | 3–4 | 약 1 h |
| 7 | C3 묶음 관문 | G-ID, T1, G0, **G-U5-127**, G6, G-SC109, G-v3b, 시간, 보조 점검, 완결성 전수 `[검토 C-16]`, 귀속 팔(하네스 패치 vK·vU6, 9상태) | 2.5–3.5 | 약 5–7 h |
| 8 | C2 증분 | §6.8 | 1 | 약 1.5 h |
| 9 | 후보 config·보고서 | `--check`, 최종 G-ID | 0.5 | 약 1 h |
| 합계 | | | **약 19–26** (검토 전 17–23) | **약 11–17 h** (순차, 검토 전 10–15 h) |

- **벽시계 근거** [읽음]
  - R-obs-b 한 스텝 포착 재생 21~37 s/상태(u6 §1)
  - R-obs-b 결정 재생 약 23 s(no-control) [실행]
  - SDMPC 상태 결정 재생 5~10분/회(SC109_DIAG Q1)
- **동시성**: 모든 재생은 순차입니다. VISSIM 4개가 도는 동안에는 결정론 계수 관문만 먼저 판정하고, 교대 벽시계는 부하가 안정된 때 잽니다.
- **멈춤 규칙**
  - 기준선 재현 실패(단계 0)
  - G-ID 실패(어느 단계든)
  - 경계 allocation 구속 > 0(단계 4)
  - 단언 초과 > 0(단계 5)
  - `[검토 C-2·C-3]` 단언 검사 수 = 0(공허), 또는 회계 substep·LOR 미설치(단계 5)
  - `[검토 C-12]` S1 1800·6300 자기 설정 재현 실패 시 대체 상태를 못 찾음(단계 0)
  - 위 가운데 하나라도 나오면 다음 단계로 가지 않고 보고합니다.
- **보고**: 단계 7 뒤에 C3 판정 요약을, 단계 9 뒤에 최종 후보와 모든 관문 표를 보고합니다. push와 폐루프 런은 그 뒤 사용자 결정입니다.

---

## 8. 위험

1. **꼭짓점 래칫**
   - U4 뒤 비포화 접근로의 한계값은 0으로, 포화 접근로는 약 9배로 커집니다. 목적함수가 다시 꼭짓점을 고를 수 있습니다(메모리 `vissim-flat-local-cost-vertex`, `vissim-model-flat-where-plant-steep`).
   - 대응: §6.10 하한·상한 비율과 C6 경보 수를 봅니다. 비율이 U1+U3보다 10%p 넘게 늘면 폐루프 제안 전에 원인을 분해합니다.
2. **가격·듀얼 증폭**
   - 356개 movement 용량이 전부 바뀌고, U6가 램프 유입을 바꿉니다. V5b에서는 가격·듀얼이 0이었지만 과거 램프 cap +1432 사례가 있습니다.
   - 대응: §6.10. 공용 `ramp_capacity_veh_h`는 건드리지 않습니다.
3. **예측 시간**
   - 할당기는 108그룹 × 450스텝 × 후보 평가만큼 돕니다. U6은 스케줄 항목을 늘립니다.
   - 대응: §6.7 계수를 먼저 봅니다. water-filling 라운드 상한은 6이고, 구속이 없는 그룹은 `x = r` 빠른 경로로 넘깁니다.
4. **키 없음 비트 동일 깨짐**
   - 원인 후보: U4-0 평탄화로 기본 config 바이트가 바뀜, SHO:63 provenance 대조, 재생 도구의 튜닝 sha 대조
   - 대응: §4.1-5의 세 검사 정의. SHO 옵션은 절대 바꾸지 않습니다.
5. **R-obs-b 동일성의 한계**: no-control이라 SDMPC 경로를 덮지 않습니다 [실행]. 대응은 §6.1 (c)입니다.
6. **소유자 경계 오류**
   - 게이트 peel-off가 127|p3에 들어가면 게이트 분기 용량이 헤드 하한에 끌려갑니다(code_map §3.3).
   - 대응: 구성원은 계약에서만 읽고, 설치 순서를 단언하고, 교차 일관성을 검사합니다(§4.3-4).
7. **U6 부분 조합은 해롭습니다**(vA +54.5). 대응: 코드 수준 all-or-nothing(§2-2)입니다.
8. **경계 allocation**: `min(allocation, ceiling)` 때문에 U4가 경계에서 무력할 수 있습니다. `[검토 C-14]` 최종 action에서는 `{}`임을 확인했습니다 [실행: S1 T3600, R-obs-b T2700]. 후보 제어는 미확인이라 §4.4-7 계수를 유지합니다.
9. **하네스 경로 하드코딩**: 옛 트리를 재는 조용한 오측정이 될 수 있습니다. 대응은 §3입니다.
10. **단일 시드와 경로 의존**
    - 오프라인 관문은 모두 seed 31(R-obs-b, S1, S0e)입니다. XREPLAY는 SC109 잠김이 설정보다 상태를 따른다는 것을 보였습니다.
    - 그래서 오프라인 통과는 **필요조건**일 뿐입니다. 폐루프 가치는 v3c1 다시드 짝(3시드 이상)으로 판정합니다.
11. **FW 결합**: U6가 FW_W·FW_E 합류 부하를 바꿉니다. S0e의 FW_E +314(VSL 중 B1 큐 연장)와 섞어 읽지 않도록 지표 네 가지를 따로 보고합니다.
12. **미결 과대 그룹**(현시 불일치 3, native 12)이 남으면 해당 교차로의 과대 방류가 남습니다. 메타 계수로 드러냅니다(§4.5-10).
13. **계약·표는 T2700 한 상태의 β에서 나온 구성원입니다.** 튜닝이 달라 β가 0이던 movement가 흐름을 얻으면 완결성 검사가 설치를 멈춥니다(의도된 fail-closed). `[검토 C-16]` 폐루프에서는 이것이 결정 실패(150 s 무제어)이므로 §4.5-12 전수 확인을 먼저 합니다.
14. `[검토 C-1]` **헤드 하한 재배분.** U4 값이 헤드 하한의 β 재배분으로 덮이는 위험입니다. 대응은 §4.4-1b 차로 비율 콜백과 최종 맵 T1a입니다.
15. `[검토 C-3]` **U5가 조용히 빠지는 경로**(회계 substep 미설치, LOR 없음). 대응은 설치 단언입니다.
16. `[검토 C-10]` **진단 출력이 결정을 멈추는 경로**(파이프 교착, 이전 action 독자). 대응은 §2-8, §4.2 통로 넷, G-C6-4입니다.
17. `[검토 C-4]` **127 모듈 경계 몫.** off-ramp 가중치가 커넥터 주행 차량까지 세면 정규 127 방류가 과소가 됩니다. 옛 B3처럼 SC1001 꼭짓점과 링크 32 잠김으로 번질 수 있습니다. 대응은 `port.ready()`, 순차 잔여, G-U5-127입니다.

---

## 9. 새 망(v3c1)에서 다시 만드는 것

망 sha가 바뀌면 아래 증거는 설치에서 **실패**합니다(fail-closed). v3c1 NC 5시드 판정이 끝난 뒤 한 번에 다시 만듭니다. v3c1 런은 이번 계획에서 쓰지 않았습니다.

| 순서 | 대상 | 방법 | 비고 |
|---|---|---|---|
| 1 | 망 sha 상수 5곳 재핀, ramp forecast 입력 시드 | 별도 승인(메모리 v3c Q12) | 코드 변경 |
| 2 | U1 β 표 | `derive_routing_beta_physical.py` | 새 결정 1160, 1162–1168이 β를 바꿈 |
| 3 | U3 무신호 증거 | `derive_unsignalized_validation.py` | – |
| 4 | U2 경로 증거 | `derive_route_queue_attribution.py`, `make_config_n31.py:94-99` 명령 | – |
| 5 | v3c1 R-obs(obs150 수집, 무제어) | VISSIM 런, 표준안에 포함, 승인 필요 | T3 관문과 U5 런타임 구성원의 입력 |
| 6 | U5 계약 | `derive_shared_head_groups.py` (inpx + R-obs 한 상태 런타임 포착) | 헤드 그룹 105/108/174 재계수, 과대 그룹 재판정 |
| 7 | U4 표 | `derive_head_saturation.py` (v3c1 NC 5시드 FZP, 같은 판정 기준) | 헤드·커넥터·제어기가 5시드에서 같은지 다시 확인 |
| 8 | U6 분기 증거 | `derive_ramp_diverge.py` (1134–1137, W_out 길이·분할) + FZP 검증 | v3c1 새 결정은 W측 밖이지만(V1·V3–V7) 증거는 망 sha에 묶이므로 재생성 |
| 9 | 오프라인 관문 재실행 | v3c1 R-obs로 G-ID, T1, G0, G6 | G-SC109는 v3b 폐루프 상태 전용이라 v3c1에서는 재실행 불가. v3b 라벨 증거로만 남김 |

- **C6은 망 핀이 없습니다.** inpx를 결정 때 상태의 `network_path`에서 읽으므로 다시 만들 것이 없습니다. `floor_tol_s`만 v3c1 폐루프에서 다시 봅니다.
- **U4-0 정리와 코드는 망과 무관합니다.**
- 망을 넘는 비교(v3b 값 대 v3c1 값)는 하지 않습니다(메모리 `vissim-network-v3c-20260927`).

---

## 10. 이 계획에서 제가 정한 것 (이의가 있으시면 말씀해 주십시오)

1. **U4 기본값은 1,850 veh/h/차로 하나**입니다. 직진·좌회전 분리(1,850/1,800)나 1,900도 차이 1~3%라 가능합니다 [읽음 U4 결과 §6].
2. **방해 플래그 13그룹은 비방해 주값**을 씁니다. plant의 수신 공간 제약이 하류 역류를 따로 표현하기 때문입니다. 방해 포함값은 기록만 합니다.
3. **다중 헤드 차로 그룹 3개는 포함**합니다(계약 등급 budget [실행]). U4 값은 FZP로 따로 잽니다.
4. **다현시 커넥터 7그룹·15 movement는 v1**을 씁니다. 외래 현시 차로 용량은 버립니다. 차로별 서비스 채널은 plant 변경이라 묶음 2 밖이고, T1에서 과소 정도를 보고합니다.
5. **분할 규칙은 `queue_proportional_fifo_v1`**입니다. 하류 수신 공간 때문에 막힌 몫은 재분배하지 않고, 직렬 첫 헤드(1093)는 기존 prehead W/N 우선 규칙을 유지합니다. `[검토 C-4]` 예외가 하나 있습니다. 127의 off-ramp 몫 가운데 **포트 물리**(`port.release` < 배정)로 못 쓴 양은 같은 스텝의 정규 구성원에게 되돌립니다(순차 잔여). off-ramp 가중치는 `port.ready()`입니다.
6. **route-choice 회랑 turn도 U4 척도로 바꿉니다.** 같은 206.53 스칼라이기 때문입니다(RS:174-182). 10634·10619 불변식은 같은 조회로 유지합니다.
7. **헤드 없이 plant만 막는 movement 18+3개**(예: `SC1004_N_SC1003_to_W` β 0.75, `SC1002_N_SC2004_to_S_SC105` β 0.71)는 U5가 아니라 U3 확장 후보로 기록하고 묶음 2에 넣지 않습니다.
8. **U6 A4는 등록 해제 대신 β 0**을 씁니다. 되접기(A:2806-2814)의 in_ 게이트 처리를 건드리지 않기 위해서입니다.
9. **U5 장부는 새 scope가 아니라 새 kind**로 기록합니다(`urban_allocator` 안). 완결성은 U5 자체 계수로 봅니다.
10. **C6 초기값** `floor_tol_s` 1.0, M 8, N 3, k 3. `floor_tol_s`는 G-C6-1b 규칙으로 확정합니다. 행동과 무관한 진단 키라 나중에 바꿔도 비용이 없습니다.
11. **C3 세 키는 코드 수준에서 all-or-nothing**입니다. 귀속 분석용 부분 팔은 하네스 패치로만 만듭니다.
12. **U4-0 죽은 분기는 지금 격리**합니다. 단, 저장소의 모든 config를 grep해서 쓰는 곳이 없을 때만입니다(§4.1-3).
13. `[검토 C-6]` **미결 과대 행은 정적 축소**합니다(§4.5-11). U4 값을 그대로 두는 선택지는 없습니다.
14. `[검토 C-15]` **HSR은 고치지 않습니다.** U5는 새 모듈이고, HSR은 승격 때 격리합니다.
15. `[검토 C-1]` **U4가 켜지면 헤드 하한은 차로 비율로 배분**합니다. 하한은 "달성 방류의 하한"이라서, U4 값보다 클 때만 그룹 전체를 같은 비율로 올립니다.

---

## 11. 사용자께 여쭐 것 (실제 결정만)

**Q1. native 신호 그룹(66개, 그중 과대 12개)을 U4·U5에 넣을까요?**
- 사실 [실행]: U4가 206.53을 대체하면 native 신호의 movement도 새 척도(실측 또는 1,850)를 받습니다. 과대 12그룹(예: SC106 1210015700|nSG2 ×4, SC103 1210021904|nSG3 ×2)은 예산이 없으면 과대 방류가 커집니다.
- 선택지
  - (가) U4와 U5 예산을 모두 적용합니다. φ는 native 고정 계획을 씁니다.
  - (나) native movement는 U4에서 빼고 지금 용량을 유지합니다.
- **권장은 (가)입니다.** "과대 그룹 전부" 결정의 취지와 맞고, (나)는 206.53을 일부 남깁니다.
- `[검토 C-6]` 범위: 사용자 결정의 "105개 중 58개"는 관측 그룹(제어 신호) 기준이라, native 66그룹은 그 수에 들어 있지 않았습니다. 그래서 이것은 실제로 새로 여쭙는 질문입니다.
- 결정 전 기본값은 **정적 축소**(§4.5-11)입니다. U4 값을 그대로 두는 것(U4 단독)은 선택지에 없습니다.

**Q2. 현시 불일치 3그룹을 어떻게 할까요?**
- 대상과 과대 배수 [실행]
  - SC105 1220007001|p3 ×4, SC1 1220007104|p3 ×4: 직진 헤드가 서비스하는 공유 좌회전 차로입니다. 런타임 현시는 p4, 헤드 현시는 p3입니다.
  - SC7 1220008601|p1 ×1.5: SG7(p2)과 SG4(p1)가 0.13 m 간격으로 연속한 직렬 헤드입니다.
- 선택지 `[검토 C-6]`으로 (가)를 고쳤습니다.
  - (가) 묶음 2에서는 동적 예산 없이 **정적 축소**(§4.5-11, 구성원 합 = n_g × s_g)를 걸고 메타에 드러냅니다.
    - 처음 판의 (가)는 "예산 없이 남긴다"였습니다. 그러면 그 세 그룹에서 U4가 단독으로 적용되어, 1,850/차로 척도로 ×4(SC105·SC1)·×1.5(SC7) 과대 방류합니다.
    - 이것은 "U4 단독 금지"와 "과대 그룹 전부" 두 결정에 모두 어긋납니다. 세 그룹은 사용자 결정 범위(관측·제어 그룹) 안에 있습니다.
  - (나) SC105·SC1 두 movement의 현시 권한을 헤드 현시(p3)로 고치는 증거 파일(U1 SC7 정정과 같은 방식)을 먼저 만들고 동적 예산에 넣습니다. SC7 직렬 헤드는 (가) 정적 축소입니다.
- **권장은 (나)입니다.** 다만 (나)는 plant 현시 게이팅을 바꾸는 U1 성격의 변경이라 따로 여쭙니다. 결정 전까지는 (가) 정적 축소로 구현하고 시험합니다.

**Q3. v3c1 전에 v3b에서 C3 후보로 단일 시드 폐루프(S2, 약 8~9 h, VISSIM 슬롯 1개)를 띄울까요?**
- **권장은 띄우지 않는 것입니다.** 이미 결정하신 대로 다시드 폐루프는 v3c1에서만 하고, 교차 재생이 단일 쌍의 경로 의존을 보였으며, 지금 VISSIM 4개가 돌고 있기 때문입니다.
- 오프라인 관문 결과가 애매할 때만 다시 여쭙겠습니다.

---

## 부록 A. 이번에 다시 확인한 줄 (cf3ce37, `sed` 읽기) [읽음]

| 위치 | 내용 |
|---|---|
| A:3389-3393 | `conn_cap = _as_float(section.get("gate_onramp_queue_capacity_veh_h"), 1800.0)` |
| A:3832-3836 | `equiv = _as_float(section.get("equivalent_uniform_veh_h"), 600.0)`, `per_lane = total_target / total_share` |
| A:4349-4352 | `_LG_KINDS.update(… section.get("lane_group_kinds") or ["internal"])` |
| UFA:514-523 | 램프 루프 끝(:516) → 주석 → `_drain_offramp_storage_accounted`(:521) |
| UFA:535-542 | `intended = min(available, sim.T_u_h * green_fraction * cap_flow)`(:538) → `_corridor_intended` → `movement_limits` |
| HSR:42, :225-226 | 자원 집합 `{'10619', '10629'}`, `movement['kind'] != 'boundary_out' or movement.get('ramp')` 거부 |
| LOR:50-70 | direct·local_upstream `movement_capacity_veh_h * lanes`, 신호 분기 `min(beta*stock, service, room)` |
| RS:126-130 | `install_movement_capacity_by_lanes`(:128) → `install_gate_onramp_queue`(:129) |
| A:13979-13992 | `post_guard_safety_metadata` 반영(:13981) … `decision_wall_sec`(:13991) |
| NIP:266-268, AGG:276-278 | 같은 pre-head 예산식(`physical_head_lanes × _movement_capacity_flow(reference)`) |
| CAO:395-401 | scope 허용 집합 |
| UQM:730-767 | 경계 kind는 `min(allocation, ceiling)` |

- 존재 확인 [실행]
  - 테스트 파일 11개(§4.0-2)
  - `diagnostics/sdmpc_n31_20260924/make_config_n31.py`(:249 `apply_urban_batch1`, 456행)
  - 워크트리 `D:/VISSIM-merge/sim3-n31-urban-b2`는 아직 없음
  - R-obs-b `decisions_sdmpc31_v3b_nc_s31b/action_002700.json`: `controller_variant "no-control"`, `decision_wall_sec 22.78`

## 부록 B. 근거 파일

- 병렬 결과(B 아래)
  - `u4_saturation_table.json`, `u4/*`
  - `u5_contract_draft.json`, `u5_groups_v3b.json`, `u5_derive.py`, `u5_build_contract.py`
  - `u6_diagnosis.md`, `u6/*`
  - `code_map.md`, `livecheck.py`, `live/*.json`, `c6_dryrun.py`, `c6_dryrun.json`
- 설계
  - `…/scratchpad/urban-fix-v3b/URBAN_FIX_PROPOSAL.md` (U2 :139-166, U4 :186-217, U5 :219-242, U6 :244-260, §4 :336-350)
  - `…/scratchpad/sc109-diag/SC109_DIAG.md` (§3 기구, §4 C1–C6·G0·G-SC109)
  - `…/scratchpad/xreplay/XREPLAY_RESULT.md`
  - `…/scratchpad/net-v3c/s12_starvation_watch.py`, `starve_s1.json`, `starve_s0e.json`
  - `…/scratchpad/fwe-struct/p0/P0_REPORT.md` (Q17, :48, :248)
- 기준 수치: `D:/VISSIM-merge/sim3-n31-urban/diagnostics/sdmpc_n31_20260924/PLANT_PORTING_GUIDE.md` (묶음 1 관문, SC7 정정 뒤 재측정)
- 하네스 원본
  - `…/scratchpad/urban-b1d/{b1_capture.py, t3_arms.py, check_paths.py}`
  - `…/scratchpad/sc109-diag/cfw/cf_driver.py`
  - `…/scratchpad/xreplay/alt_replay.ps1`
- 메모리 노트: `vissim-boundary-movement-capacity-206`, `vissim-queue-projection-fixed-fraction`, `vissim-measured-capacity-online`, `vissim-supersede-dont-flag`, `vissim-gate-outside-config-is-dead`, `vissim-sdmpc31-live-check-tools-blind`, `vissim-urban-batch1-and-rmcal-20260926`, `vissim-network-v3c-20260927`

---

## 부록 C. 적대적 검토: 문제와 해결 (2026-09-28)

- 범위: 수치·file:line 재확인, 키가 없을 때 조용히 거동이 바뀌는 곳, 모듈 경계 예산(link 127의 도시 방류 + off-ramp 배수), 시험할 수 없는 관문, U4 단독 배포 경로, C6가 행동에 닿는 통로
- 방법: cf3ce37 코드를 `sed`/`grep`으로 읽었습니다. JSON(U4 표, U5 계약, 굶김 원형 결과, S1 T3600·R-obs-b T2700 결정)은 python으로 읽기만 했습니다. 코드·config·git·VISSIM·재생은 건드리지 않았습니다.
- 등급
  - **치명**: 그대로 구현하면 관문이 틀린 판정을 냅니다.
  - **높음**: 행동이나 판정이 조용히 바뀝니다.
  - **중간**: 구현 중에 막히거나 비트 동일이 깨집니다.
  - **낮음**: 문구나 보고 품질 문제입니다.

### C.0 문제와 해결 표

| # | 등급 | 문제 | 근거 | 해결(본문 위치) |
|---|---|---|---|---|
| C-1 | 치명 | **헤드 하한이 U4 구성원 용량을 β 비율로 다시 씁니다.** 처음 판은 U4 설치(RS:128)가 최종값이라고 봤습니다. 그런데 RS:145-146 `install_measured_movement_capacity`가 그 뒤에 돕니다. 여기서 `base = Σ 구성원 용량`(SHO:202), `estimate = max(base, carried[, supported])`(SHO:205, :249)를 만든 뒤 `distribute`(SHO:254)가 `caps[m] = total × β_m/Σβ`(A:4601)로 씁니다. 공유 차로 그룹에서는 base가 중복 합이라 재배분이 구성원 용량을 뒤틉니다. U5 요청 `r_m`은 차로 기준이고 UFA `intended`는 맵 기준이라, 더 작은 쪽이 구속합니다. | [읽음] RS:145-146, SHO:198-255, A:4561-4603. S1 3600 carried 54 / updated 45 [읽음 code_map §3.1]. PLANT_PORTING_GUIDE:66도 "멤버 용량 합에서 출발해 β로 다시 나눈다"고 적었습니다. | U4가 켜지면 A:4435가 차로 비율 보존 콜백을 넘깁니다. 하한이 구속하지 않으면 U4 값이 비트 그대로 남습니다. 계약은 2단계로 적재합니다. T1a는 RS:185 뒤 최종 맵에서 잽니다. 계수 `head_floor_scaled_groups`를 둡니다(§4.4-1, -1b, §6.3, §5.5) |
| C-2 | 치명 | **"매 스텝 단언이 모든 예측에서 검사된다"는 틀렸습니다.** `record_resource_allocation`은 원장이 응답을 포착하지 않으면 바로 반환합니다. 포착은 세 곳에서만 켜집니다. 따라서 §5.2의 `max_exceedance == 0`은 기록이 0개여도 통과할 수 있습니다(공허 통과). | [읽음] CAO:335-336, :294-295 `captures_response = hasattr(self, '_response')`, AFO:506·:510, `sdmpc_tangent_worker.py:249` | 할당기에 자체 원시 단언을 둡니다(LOR:74-75 방식, 원장과 무관). 오프라인 전수는 "검사 수 > 0"을 먼저 확인합니다(§4.5-8, §5.2) |
| C-3 | 높음 | **U5가 조용히 빠지는 경로가 둘 있습니다.** (a) 회계 substep은 `control_area_enabled`·`sc2001_corridor`·`route_choice_corridor`·`native_internal_inputs` 중 하나가 있어야 설치·호출됩니다. 없으면 vendor 원본이 돕니다. (b) `state.lane_offramp_runtime`이 없으면 옛 배수(UFA:88-155)가 127 예산을 우회합니다. | [읽음] UFA:978-985, :993-997, :87-89 | 설치 단언 두 개(§4.5-1), LIVE 계수(§5.5) |
| C-4 | 높음 | **link 127 모듈 경계 몫이 불완전합니다.** (a) off-ramp 가중치 "포트 준비량"이 실제 코드로는 `port.stock`입니다. stock에는 커넥터를 주행 중인 차량도 들어 있어, off-ramp 몫이 커지고 정규 127이 과소 서비스됩니다. (b) LOR 실행이 정규 방류보다 먼저인데, 포트 물리로 못 쓴 몫이 버려집니다. (c) 127 몫 자체를 FZP와 대조하는 관문이 없었습니다. (d) C2가 없으면 127 정지 차량 일부가 서비스되지 않는 off_ramp kind 큐에 갇힙니다. 그래서 C3 단독 127 판정이 오염됩니다. | [읽음] LOR:3, :47, :69, :73; `physical_urban_transport.py:91` `ready()`; UFA:521 → :530-538; UFA:533-534; A:5270-5275. 메모리 B3 실패(+1002) | 가중치 `β × port.ready()`, 순차 잔여 반환(하류 막힘 몫은 반환 안 함), 새 관문 G-U5-127(off-ramp 출신 비율 ±0.10, 10491·10481 재고, 만차 초), 127 행은 C3+C2로 판정(§4.5-2, §6.3, §6.4, §10-5) |
| C-5 | 높음 | **G-U5-2 범위가 v3b 표와 구조적으로 충돌합니다.** 옛 범위(p4 1,725~2,025)는 v2 보고서 값입니다. v3b U4 표의 127\|p4는 2,058.3/차로 × 1차로입니다. 포화 녹색초 방류가 2,058이 되어 무조건 실패합니다. 127\|p3는 3,799.4로 범위 안입니다. | [실행] `u4_saturation_table.json` 127\|p4 `saturation_veh_h_per_lane 2058.3`, 주기별 p25/p50/p75 1,920/2,160/2,160; 127\|p3 1,899.7. [읽음] URBAN_FIX_PROPOSAL:190, :238 | v3b 기준으로 다시 정합니다: n_g × s_g ± 5% + 표 주기별 p25–p75 교차 확인. 옛 범위는 참고로만 둡니다(§6.3) |
| C-6 | 높음 | **"과대 그룹 전부"의 범위와 미결 행.** (a) 사용자 결정의 58/105·81차로는 v2 수치입니다. 계획은 v3b 재계수(108그룹 중 53, 공유 차로 80/44)와의 대응을 적지 않았습니다. (b) Q2 (가) "예산 없이 남긴다"는 그 세 그룹에서 U4 단독(×4·×1.5 과대)이 됩니다. 두 사용자 결정 모두에 어긋납니다. native 12도 결정 전에는 같은 상태입니다. | [실행] `u5_contract_draft.json` `counts.reproduction`, `controlled_all_108`, 등급별 과대 교차표(budget 45 + 10629 1 + LUR 2 + 현시 불일치 3 + 파생만 2 = 53) | §0-3에 대응표를 적습니다. 미결 행에는 **정적 축소**(구성원 합 = n_g × s_g)를 기본으로 겁니다. Q2 (가)를 이에 맞게 고쳤고, Q1에는 범위 설명을 더했습니다(§4.5-11, §11) |
| C-7 | 중간 | **`lane_group_kinds`가 U4 단독 경로가 됩니다.** U4-0 뒤에는 이 키가 U4와 무관하게 멤버십을 정합니다. 네 kind만 넣은 config는 게이트 peel-off를 127\|p3·71\|p3에 넣습니다. | [읽음] A:4351, :4584-4595; code_map §3.3 [실행 livecheck] | 결합 집합에 넣습니다: `["internal"]` 밖의 값은 C3 세 키가 있어야 합니다(§2-2) |
| C-8 | 중간 | **U4-0이 살아 있는 부작용·기본값을 빠뜨렸습니다.** (a) `sustained` 분기는 `_SUS_SIGS`(68)도 채우고, 이것을 살아 있는 배분 함수가 씁니다. code_map의 "효과 DEAD"는 [추론]입니다. (b) A:3874 `perimeter_include_boundary_out` 기본 True는 살아 있는 네 번째 코드 기본값입니다. (c) A:3808·:3868의 하드코딩 차로 파일은 없으면 조용히 `source_missing`만 남깁니다. | [읽음] A:4350-4365, :4570-4572, :3874, :3808, :3868-3870; CFG:7834 | 대체 계수를 붙인 뒤 격리하거나 명시 키로 둡니다. 네 번째 기본값을 올립니다. U4 경로는 차로 파일을 핀합니다(§4.1-1, -2, -4) |
| C-9 | 중간 | **기본 config 변경의 모순과 옛 튜닝 적재.** §3은 "기본 config 변경은 사용자 결정 없이 안 한다"인데, U4-0은 `config_n31_v2.json`을 고칩니다. 또 필수 키로 바꾸면 옛 런 provenance·frozen 튜닝은 새 코드에서 적재되지 않습니다. | [읽음] 계획 §3, §4.1 | b2 브랜치 안의 의미 보존 평탄화로 한정하고, 기계적 diff 검사를 둡니다. main 승격은 사용자 결정입니다. 재생은 평탄화 config로 합니다(§3, §4.1-5) |
| C-10 | 높음 | **C6가 행동에 닿는 통로 넷.** (a) 러너는 프로세스가 끝난 뒤 파이프를 읽습니다. stdout이 커지면 결정이 교착됩니다. (b) 이전 action JSON을 다음 결정의 14곳(grep, 읽기 호출 기준)이 읽고, A:12927은 그 sha를 핀합니다. G-ID (d)의 한 상태 재생으로는 볼 수 없습니다. (c) C6가 cfg·state·캐시를 바꿀 가능성. (d) 러너 필드 검색이 대소문자를 무시합니다. | [읽음] VBS:5125-5145(`Do While exec.Status = 0` 뒤 `ReadAll`), A:14058-14059 주석, VBS:5038-5048 `vbTextCompare`, 이전 action 독자 목록(§4.2) | stdout 512바이트 상한, stderr 0, 상태 해시 불변 시험, 정적 감사 + 새 관문 G-C6-4(두 결정 연쇄), 이름 충돌 검사는 대소문자 무시(§2-8, §4.2, §6.9) |
| C-11 | 중간 | **G-C6-1b가 만족될 수 없을 수 있습니다.** 원형의 4,650 s는 5 km/h와 "결정 직후 프레임"으로 나온 값입니다. 어댑터는 1.0 km/h와 T 시점을 씁니다. | [읽음] `s12_starvation_watch.py:28-30`, :87-113; [실행] `starve_s1.json` rule `stop_kph 5.0`, SC109 SG2 p3 4650·6450, 22건/22건 | M ∈ {8, 6, 4} 둘째 축, 그래도 없으면 1.0/8 유지 + 불일치 보고(§6.9) |
| C-12 | 중간 | **G-ID (c) 재현 주장이 과장됐습니다.** 확인된 것은 S0e×기본 1800·3600(XREPLAY)과 S1·S0e 3600(SC109_DIAG r3600)뿐입니다. S1×U1+U3 1800·6300은 미확인입니다. | [읽음] XREPLAY_RESULT:10, :17; SC109_DIAG:292-293 | 단계 0에서 먼저 재현하고, 안 되면 상태를 바꿉니다(§6.1 (c), §7) |
| C-13 | 낮음~중간 | (a) AD 수칙 "min·곱셈·나눗셈만"은 U5에 필요한 덧셈·뺄셈을 빠뜨렸습니다. (b) U5 적용 자리 "UFA:538 뒤"는 `_corridor_intended`(:539-540)가 `intended`를 다시 쓰기 전입니다. | [읽음] UFA:538-542; `sdmpc_tangent_reverse.py:44-67`(이항 노드) | 이항 +,−,×,÷,min으로 고칩니다. 적용은 :540 뒤, :541 전입니다(§2-7, §4.5-3) |
| C-14 | 정보 | 경계 allocation 위험은 최종 action에서는 해소됐습니다. S1 T3600·R-obs-b T2700 모두 `inflow_outflow_allocation: {}`입니다. 후보 제어는 미확인입니다. | [실행] 결정 JSON 두 개 | 계수는 유지하고 서술을 고쳤습니다(§4.4-7, §8-8) |
| C-15 | 중간 | **HSR 일반화는 불필요하고 위험합니다.** U5와 `head_resource_contract`는 공존하지 않으므로, U5가 켜지면 HSR은 `view(cfg) is None`으로 옛 경로를 돌지 않습니다. HSR:42·:225-226을 고치면 키 없음 경로만 바뀝니다. | [읽음] HSR:96-98, :42, :216-230; [실행] S1 T3600 `head_resource_final_rate_10619 970.79`, `_10629 3060.0` | U5는 새 모듈에 두고 HSR은 그대로 둔 뒤 승격 때 격리합니다. 대체 값을 기록합니다(§4.5-5) |
| C-16 | 중간 | **완결성 fail-closed는 폐루프에서 결정 실패(150 s 무제어)가 됩니다.** | [추론] 계획 §8-13 | C3 튜닝으로 R-obs-b 61 + S1·S0e 결정 상태 전부에서 흐름 구성원 집합이 계약과 같은지 오프라인 전수 확인(§4.5-12) |
| C-17 | 낮음 | 제안서 G-v3b (b) V5b 회귀와 (c) U10 비율이 계획에서 말없이 빠졌습니다. (b)는 v2 망이라 핀에서 실패하므로 적용할 수 없습니다. | [읽음] URBAN_FIX_PROPOSAL:341-346 ((b) :343, (c) :344) | 뺀 이유를 명시합니다(§6.4) |
| C-18 | 낮음 | G0 bootstrap이 iid 재표본이라, 상관 있는 54전이에서 CI가 좁습니다. | [추론] | 이동 블록 bootstrap(블록 5)을 병기하고, 둘 다 통과해야 합니다(§6.4) |
| C-19 | 낮음 | 옛 트리 재생이 `__pycache__`를 쓸 수 있습니다. | [추론] | `PYTHONDONTWRITEBYTECODE=1`과 옛 트리 `find -newer` 0개 확인(§3) |
| C-20 | 낮음 | 단계 4의 T1a는 C3 결합 때문에 config로 설치할 수 없습니다. T1b는 구조상 거의 항등이라 충실도 관문이 아닙니다. | [추론] 계획 §2-2, §7 | 단계 4·5는 하네스 패치로 보고, 설치 T1a는 단계 7에서 받습니다. 충실도는 G0이 맡는다고 명시합니다(§6.3) |
| C-21 | 낮음 | 계약 전체(약 770 KB)를 `cfg.network`에 두면 tangent 요청마다 워커로 넘어갑니다. | [읽음] `sdmpc_tangent.py:21-36`; [실행] 파일 크기 772,979 B | 압축된 런타임 형태만 둡니다(§4.5-1) |
| C-22 | 낮음 | action JSON이 이미 결정당 약 58 MB입니다. 새 진단이 초 단위 배열을 넣으면 러너 읽기 시간과 디스크가 커집니다. | [읽음] VBS:5008-5010 주석 | 요약 계수만 넣고, 크기 증가 ≤ 1%를 시간 관문에서 봅니다(§2-9) |

### C.1 다시 확인한 수치·인용 (cf3ce37)

| 대상 | 계획의 값 | 확인 결과 |
|---|---|---|
| A:3391 게이트 분기 기본값 | 1800 | 맞음 [읽음] `_as_float(section.get("gate_onramp_queue_capacity_veh_h"), 1800.0)` |
| A:3832-3836 정규화 | 기본 600, config 330, 206.53 | 맞음 [읽음]. 330 × 184 / 294 = 206.53 [산술] |
| A:4351 `lane_group_kinds` 기본 | `["internal"]` | 맞음. 다만 같은 분기에 `_SUS_SIGS`(A:4362)가 있음 → C-8 |
| UFA:516 / :521 / :538 / :541-542 | 램프 루프 끝 / off-ramp 배수 / intended / limits | 맞음. :539-540 회랑 재기록 → C-13 |
| RS:128 / :129 / :145-146 / :174-182 / :207-210 / :245-247 | 설치 순서 | 맞음. :145-146 헤드 하한이 U4 뒤 → C-1 |
| HSR:42 | `{'10619','10629'}` | 맞음 |
| NIP:266-268, AGG:276-278 | 같은 pre-head 예산식 | 맞음(AGG는 :268 `def prehead_finish`, :276 spec, :278 budget) |
| CAO:329-357, :395-401 | 장부 검사·scope 허용 집합 | 맞음. 다만 :335-336 조기 반환 → C-2 |
| UQM:730-767 | `min(allocation, ceiling)` | 맞음(함수는 :728부터) |
| A:13981 / :13991 | C6 삽입 자리 | 맞음 |
| VBS:1236-1240, :5011-5020 | stdout 기록, 첫 필드 검색 | 맞음. :5042 `vbTextCompare`, :5139-5143 종료 뒤 읽기 → C-10 |
| LOR:51 / :56 / :59-71 / :73 / :84 | direct·local_upstream·신호 분기·release·기록 | 맞음. :47·:69가 `stock` 사용 → C-4 |
| U4 표 | 실측 65, 기본 40, 1,850 | 맞음 [실행] |
| U5 등급 | 45/1/2/1/3/3/53, native 66(12) | 맞음 [실행] |
| R-obs-b T2700 | no-control, 22.78 s | 맞음 [실행] |
| u6 수치 | −28 → −67, +34, vA +54.5 | 맞음 [읽음 u6_diagnosis.md:30-36, :281] |
| SC109 | ΔJ +0.759/+1.250, 619.6 | 맞음 [읽음 SC109_DIAG:32-35, :186] |
| 묶음 1 T3 | A1 6.361 … C 11.011, 세 경로·FD 값 | 맞음 [읽음 PLANT_PORTING_GUIDE:75] |
| 굶김 원형 | 22/22건, SC109 SG2 4,650·6,450(S1만) | 맞음 [실행] |
| 테스트 파일 11개 | 존재 | 맞음 [실행] |
| G-U5-2 127\|p4 | 1,725~2,025 | **틀림**: v3b 표 2,058.3 → C-5 |
| "xreplay가 5회 재현 확인" | – | **과장**: 3개 상태만 → C-12 |
| URBAN_FIX_PROPOSAL 옛 범위 인용 줄 | (없음) | :190, :238 [실행 grep] |

### C.2 요청된 점검 항목별 결론

- **키가 없을 때 조용히 바뀌는 것**
  - U4-0의 필수 키 전환: 새 코드에서는 옛 튜닝이 적재되지 않습니다. 이것은 조용하지 않고 실패하므로, 평탄화 diff 검사로 관리합니다(C-9).
  - `_SUS_SIGS` 제거: 조용히 바뀔 수 있습니다. 계수를 먼저 봅니다(C-8).
  - `_LTO` 오류 삼킴 제거: 파일이 있는 설정에서는 비트 동일이고, 파일이 없으면 이제 실패합니다(C-8).
  - C2 가시성, C6 import, U6 정책: 모두 키가 있을 때만 작동합니다. 문제 없음 [읽음].
- **모듈 경계 예산(127)**: C-3, C-4로 보강했습니다. 71은 LUR 위임, 52는 10629 대체입니다. 계약상 모듈을 가로지르는 그룹은 127\|p3·127\|p4 둘뿐입니다 [실행 `cross_module_groups`].
- **시험할 수 없거나 공허한 관문**
  - §5.2 공허 통과(C-2), G-U5-2 구조적 실패(C-5), G-C6-1b 만족 불가 가능성(C-11), G-v3b (b) 적용 불가(C-17), 단계 4 T1a 설치 불가(C-20)
  - 모두 고쳤습니다.
- **U4 단독 배포 경로** 여섯 가지를 봤습니다.
  1. config 결합: 막혀 있습니다.
  2. `lane_group_kinds` 단독: C-7로 막았습니다.
  3. 미결 과대 행: C-6 정적 축소로 막았습니다.
  4. 하네스 메모리 패치: 분석 전용이라 허용합니다.
  5. `make_config_n31.py --components`: C3을 한 단위로만 받습니다.
  6. v3c1 재유도: 망 sha 핀이 어긋나면 설치가 실패합니다.
- **C6가 행동에 닿는 통로**: 결정 안에서는 action이 C6 전에 확정되므로 닿지 않습니다. 결정 밖의 통로 넷(파이프, 다음 결정, 상태, 러너 검색)은 C-10으로 막았습니다.

### C.3 남은 불확실성 (검토로 풀지 못한 것)

- SDMPC 후보 제어의 `inflow_outflow_allocation`이 비어 있는지 모릅니다(C-14). 계수로 봅니다.
- `_SUS_SIGS` 대체가 실제로 쓰이는지 모릅니다(C-8). 계수로 봅니다.
- 차로 비율 콜백 뒤에도 헤드 하한이 구속하는 그룹이 얼마나 되는지 모릅니다(C-1). v3b 표 값이 옛 하한보다 대부분 클 것으로 봅니다 [추론]. 계수로 확인합니다.
- `port.ready()`가 LOR 신호 분기 포트 모두에서 같은 의미인지(CumulativeLane 대 CoupledPort) 아직 읽지 않았습니다. 단계 5 첫 작업으로 확인합니다.
