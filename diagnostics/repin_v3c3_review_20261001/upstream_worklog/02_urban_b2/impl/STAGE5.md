# 도시 묶음 2 — 단계 5 보고 (U5 물리 헤드 그룹당 공유 방류 자원)

- 작성: 2026-09-29 17:40 시작 → 23:05 완료. 이전 시도의 단계 5 부분 결과는 없었습니다(`B/impl`에 `stage5` 없음, 시작 시 트리 diff `9c3fc54d…` = 단계 4 끝과 같음 [실행]).
- 계획: `B/BATCH2_PLAN.md` §4.5(1~12), §5.1 U5 행과 검토 추가 행, §5.2, §5.5, §6.3 `[C-20]`, §7 단계 5 행과 멈춤 규칙(단언 초과 > 0, 단언 검사 수 = 0, 회계 substep·LOR 미설치), 부록 C-2·C-3·C-4·C-6·C-13·C-15·C-16·C-21, §C.3. 사용자 결정: C3 = U4+U5+U6(전부 아니면 전무), U5는 과대 그룹 전부 + native(Q1), Q2 = SC105·SC1 p3 증거 + SC7 정적 축소, Q3 = v3b 폐루프 없음.
- 대상 트리: `D:/VISSIM-merge/sim3-n31-urban-b2` (브랜치 `claude/urban-batch2-20260928`, HEAD `cf3ce37`). 변경은 **커밋하지 않고** 작업 트리에 남겼습니다. push·다른 브랜치/워크트리 조작, VISSIM·cscript 시작/종료는 없습니다.
- 표기: **[실행]** 이번에 직접 돌리거나 계산한 값 / **[읽음]** 파일에서 읽은 값 / **[추론]** 직접 증거 없이 끌어낸 판단.
- 약어: B = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/urban-b2`, S5 = `B/impl/stage5`, R5 = `S5/run5`(재생 연쇄), H = `B/harness`, W = b2 트리, SHG = `W/evaluation/controllers/shared_head_groups.py`(새 모듈), A = 어댑터, UFA = `urban_flow_accounting.py`, LOR = `lane_offramp_runtime.py`, RS = `runtime_setup.py`, HSC = `head_saturation_capacity.py`, T2 = `W/diagnostics/sdmpc_n31_20260924/tests/test_n31_urban_batch2.py`, N31 = `W/diagnostics/sdmpc_n31_20260924`. 줄 번호는 최종 작업 트리 기준입니다.

---

## 0. 결론

**멈춤 규칙에 걸린 것은 없습니다(stop=false).** 계획 §4.5의 1~11을 구현했고(§2), 12(완결성 전수)도 이번 재생에서 99상태 모두 확인됐습니다(§7). 판단이 필요한 것은 §2.2와 §11에 모았습니다. 가장 큰 두 가지는 native 행의 녹색 정의(헤드 SG, 행동이 실제로 바뀜)와 시간 부하(포착 예측 +6.7%)입니다.

| 항목 (계획 위치) | 결과 | 근거 |
|---|---|---|
| U5 모듈 (§4.5-1·2·8·10) | SHG 새 모듈. 계약 2단계 적재, 설치 끝 확인, 워커 확인, 스텝 할당기(water-filling), 자체 원시 단언, 장부 기록 3종, 결정 기록 | [실행] §2 |
| off-ramp 가중치 `port.ready` (§4.5-2 `[C-4]`) | `β × DelayedPort.ready`(메서드가 아니라 속성). LOR 포트 7개는 모두 `DelayedPort(interval_service=True)` | [읽음]·[실행] §2.2-2 |
| 순차 잔여 (§4.5-2 `[C-4]`) | 포트 부족분만 정규 구성원에게 되돌리고, 하류 막힘 몫은 되돌리지 않음. v3b 재생에서는 한 번도 생기지 않음(ready 가중치 때문) | [실행] 단위 시험, §5 |
| LOR 요청/실행 분리 (§4.5-4) | `requests`(순수 함수)와 `drain`. 할당이 있으면 service = min(service, x_m) | [실행] §2 |
| UFA 적용 (§4.5-3 `[C-13]`) | `_corridor_intended` 뒤·`movement_limits` 기록 전 min, 닫기는 `urban_allocator` 완료 직전 | [실행] T2:1881 |
| 정적 축소 (§4.5-11, Q2 SC7) | U4 설치에서 SC7 행 구성원 합 = n_g × s_g(1,233.33 + 2,466.67 = 3,700) | [실행] §2.2-7 |
| Q2 연결 | β 원천 `routing_v3b2q2` 등록. C3 팔의 두 movement가 p3 | [실행] §7 |
| 단위 시험 (§5.1) | T2 **74 OK**(단계 4의 54 + U5 20) | [실행] §3 |
| 스위트 | 40실행, 단계 4 대비 **회귀 0** | [실행] §4 |
| **§5.2 단언 (멈춤 규칙)** | R-obs-b **61상태 × 정확 450 s**: 원시 단언 행 1,564,650·집합 2,772,450·구성원 4,446,900회 검사, **허용오차를 넘은 검사 0**(최대 잔차 4.4e-16), 포착 기록 7,219,350건(최대 exceedance 4.4e-16), 질량 대조 4,446,900원천 최대 차 **0.0**. cohort 경로·연속 경로(tangent 워커) 3상태도 같은 계수·최대 1.6e-15 | [실행] §5 |
| **멈춤 규칙: 설치** | 회계 substep·LOR 포트는 설치 끝 단언으로 확인. 설치 99상태(R-obs-b 61, S1 19, S0e 19) 모두 통과, 스텝마다 할당기·LOR 할당 경로가 돎 | [실행] §7 |
| 10634 동일 (하네스 "U5 없는 C3" 팔) | **첫 스텝 61/61 동일.** 450 s 전체로는 T1·T150만 동일(2/61). 나머지 59상태는 LUR 입력이 먼저(+134~284 s), 10634가 그 뒤(+225~384 s) 갈라짐: 망 전파이고 U5가 10634를 직접 건드리지는 않음(판단 필요, §6) | [실행] §6 |
| G-ID 키 없음 (a)(b) | R-obs-b 61 × 기본·U1+U3: `MRS compare` **IDENTICAL 122/122**, 한 스텝 포착 15필드·설치 스냅숏이 단계 1과 같음, action 차이는 provenance·시간뿐 | [실행] §8 |
| SDMPC 키 없음 (S1 3600) | 4검사 같음(action_contract만 다름, 알려진 VSL 100/110), 녹색·offset·목적값·tangent 계수가 기록 및 단계 1과 같음 | [실행] §8 |

---

## 1. 재개 확인

- 단계 5 부분 결과가 없었습니다. 그래서 새로 시작했습니다 [실행: `B/impl`에 `stage5` 없음, 시작 시 `worktree_diff_sha256` `9c3fc54d…` = STAGE4 최종값].
- 재사용한 것: `H/_prov.py`, `H/u40_probe.py`, `H/sdmpc_replay.py`, `H/run_suites.py`, `H/compare_suites.py`(수정 없음). 비교 기준은 단계 1 키 없음 재생(`B/impl/stage1/probe/b2_{base,u1u3}`, `…/sdmpc/b2_s1_T3600`), 단계 4 최종 스위트(`B/impl/stage4/suites_final`), 단계 4 U4 스모크(`B/impl/stage4/run4/t1a/robsb_full`)입니다.

---

## 2. 바꾼 것 (작업 트리, 커밋 안 함)

| 파일 | 줄 | 내용 |
|---|---|---|
| SHG 새 모듈 (791줄, LF) | 전체 | U5: 계약 2단계 적재(configure :330), 설치 끝 확인(finalize :445), 워커 확인(:505), 스텝 할당기(`StepAllotment` :591, `_solve` :551, `_fill` :519), 원시 단언과 장부(close :710), 결정 기록(:766), 정적 축소 식(:133), 키 배제(`check_tuning` :122), 행 조립(`build_row` :309) |
| UFA | :70, :90-96, :525-539, :559-560, :573-574, :613-614, :776-779 | 할당기 생성(램프 루프 뒤·off-ramp 배수 전), 배수에 할당 전달, 순차 잔여, `_corridor_intended` 뒤 min, spatial 거부, 수락 기록, 닫기. 모두 `shared is not None`일 때만 |
| LOR | :41 `requests`, :78 `drain`, :70-71, :101-102 | 요청(순수 함수)과 실행 분리. 할당이 있으면 구성원 service를 자르고, 실행 뒤 (자기 요청량, 방출량)을 알림 |
| RS | :218-222, :275-279, :316-318 | configure(physical_ramp_branches 뒤 = 계획의 cf3ce37 RS:207-210), finalize(설치 끝, verify_final 뒤), 워커 확인(`install_worker_runtime` 끝). 모두 U4/U5 뷰가 있을 때만 |
| HSC | :17-18, :65-70, :182-185, :278-279, :296-300, :321, :397-398 | 미구현 거부를 U6만으로 좁힘, U5 키 배제, SC7 정적 축소, 회랑 turn이 정적 축소 행 구성원이면 오류 |
| A | :1662-1677, :4024-4031, :4111, :14191-14196 | native 헤드 SG 고정 계획 도우미(`_rw_native_head_green`), `routing_v3b2q2` 등록, 결정 기록 |
| `beta_source.py` | :40 | `COMPLETE_BETA_SOURCES`에 `routing_v3b2q2` |
| T2 | :57-72(설명), :1109-1118, :1223-1245, :1469-1960 | U5 시험 20개, U4 시험 두 곳 갱신 |

- 키가 없을 때 새 모듈은 import되지 않습니다. 모든 import가 함수 안에 있고 U4/U5 뷰를 거쳐야 도달합니다(T2:1942 정적 시험).
- 줄바꿈: 추적 파일은 원래 방식을 유지했습니다(UFA·어댑터·`beta_source` LF, LOR CRLF, RS 혼재는 줄마다 보존). 새 모듈은 같은 폴더의 새 파일들(HSC·C6 모듈)과 같은 LF입니다. 편집 도구 대신 줄바꿈을 보존하는 치환 스크립트(`S5/eol_edit.py`)를 썼습니다 [실행: `S5/eolcount.py`로 전후 CRLF/LF 줄 수 대조].

### 2.1 U5 모듈의 흐름 (계획 §4.5-1~10)

- **configure** (SHG:330, RS:218-222). kind·현시·커넥터·구성원을 바꿀 수 있는 설치기가 모두 끝난 자리입니다.
  - 핀: 튜닝의 `shared_head_groups` = U4 설치가 읽은 계약(같은 `{path, sha256}`), 스키마, 망 핀 = U4의 망(= 스냅숏), 분할 규칙 이름이 알려진 것, 모든 enforcement가 알려진 부류이고 대기 행 0
  - **inpx 재계산**: 핀된 inpx를 한 번 파싱해(`_network_geometry` SHG:140) 174행 모두 대조합니다. 헤드(번호·링크·차로·위치 3자리·SC/SG), 차로별 헤드 뒤 커넥터(번호·도착 링크·출발 차로), 구성원 출구 커넥터(정지선 링크에서 나가고, 구성원 차로 ⊆ 커넥터 차로, 헤드보다 뒤, 도착 링크 = 계약 destination). 계약의 300개 구성원이 모두 `source_lane_before_diverge` 규칙이라 그 규칙만 허용합니다.
  - **U1 물리 커넥터**: 구성원 출구 커넥터 ∈ 튜닝 `urban.beta` 표의 `approaches[].physical_connectors`(생성기와 같은 별칭 규칙). 표 sha가 `urban.beta.sha256`과 같아야 합니다.
  - 구성원(외래 현시 구성원 포함)의 런타임 kind·origin·수신 링크·현시·unsignalized·ramp가 계약과 같음
  - 예산 행 57개: 모든 구성원이 행의 녹색에서 서비스(현시 행은 `match`이고 런타임 현시 = 행 현시, native 행은 `native_signal`), 한 행에만 속함, ramp·무신호 아님, 소유자는 regular 또는 offramp_drain(포트는 `source_key`에서), 용량 = U4 설치값(하한이 구속했으면 하한 기록값), laminar 가족, 뿌리 = 헤드 차로 = n_g
  - 정적 축소 행(SC7): 설치값 = 식 값, 합/(n_g·s_g) = 1.0
  - 결과: `cfg.network.shared_head_groups` 압축 뷰(pickle 26,285 B, 계약 652 kB 대신 `[C-21]`)
- **finalize** (SHG:445, RS:275-279). 설치 끝, 즉 계약의 런타임 포착 지점입니다 `[C-3]`.
  - 회계 substep(`_uqm.urban_substep._control_area_events`)이 설치됨. 아니면 vendor substep이 예산을 조용히 건너뜁니다.
  - off-ramp 구성원 6개의 포트(10491, 10481)가 LOR에 있고 신호 분기(직행·local_upstream 아님)이며, 구성원이 그 off-ramp 그룹의 movement이고 `ready`를 가짐
  - native 행의 헤드 SG 도우미가 설치돼 있고 모든 native 노드에 스케줄이 있음
  - 예산 구성원 용량이 configure 뒤 바뀌지 않음(LUR·area 설치가 덮지 않음)
  - 모든 구성원의 흐름 표지(β > 1e-9)와 **완결성**: 런타임 흐름 movement ⊆ 계약 구성원 ∪ 외래 구성원 ∪ 허용 목록(65)
  - 위임 행(71|p3·p4) 증거: LUR CTM 차로당 율 대 U4 s_g
- **워커 확인** (SHG:505, RS:316-318): tangent 워커의 `install_worker_runtime` 끝에서 같은 두 조건을 봅니다. cfg에는 아무것도 쓰지 않습니다(워커의 frozen 피연산자 검사, sdmpc_tangent_worker.py:170-173).
- **스텝 할당기** `StepAllotment` (SHG:591, UFA:525-539)
  - 행마다 φ_g, 집합 용량 C_S = T_u_h × φ_g × (s_g × f_g × |S|), 가중치(정규: 도착 뒤 큐 / off-ramp: β × ready), 요청 r_m = min(w_m, T_u_h × φ_g × cap_m), water-filling
  - 모든 집합이 풀려 있으면 x = r(같은 객체). 아니면 위에서 아래로, 각 집합의 항목(하위 집합과 구성원, (최소 차로, 이름) 순서)이 가중치 비례로 나누되 자기 수요를 넘지 않습니다. 라운드는 최대 2였습니다(§5).
  - off-ramp 구성원: LOR `requests`에서 service = min(service, x_m)(LOR:70-71), 실행 뒤 알림(LOR:101-102) → `after_offramp`(UFA:539)
  - 정규 구성원: intended = min(intended, x_m)(UFA:559-560) → 수락 기록(UFA:613-614) → 닫기(UFA:776-779)
- **자체 원시 단언** (SHG:710-744) `[C-2]`: 스텝 끝에 행마다 모든 집합의 Σ 실행 ≤ C_S + 1e-7, 모든 구성원의 실행 ≤ x_m + 1e-7을 primal 값으로 확인하고, 넘으면 `ArithmeticError`입니다. 원장 포착과 무관합니다. 포착 중이면 `shared_head_group_budget`(뿌리), `shared_head_lane_set`(나머지 집합), `shared_head_member_allotment`(구성원)를 `urban_allocator` 방문 안에서 기록합니다.
- **결정 기록** `projection_diagnostics['shared_head_groups']`(A:14191-14196, SHG:766): 계약 핀, 부류, 예산 행·구성원·집합 수, native 행 수, off-ramp 구성원, 하한 비율 행, 정적 축소·위임·pre-head 증거, 완결성, 미결 과대 그룹(0), 이 프로세스의 스텝 계수. 약 2.1 kB(압축 JSON), action 안에서 약 3.2 kB입니다.

### 2.2 계획이 정하지 않았거나 계획과 다르게 한 것 (판단, 확인 부탁)

1. **native 행의 φ_g는 헤드 SG의 고정 계획입니다** [실행 `S5/u5_native_phi_probe_T2700.json`, 도구 `H/u5_native_phi_probe.py`]
   - 계약 `budget_rule.green`은 native 행에 "the native fixed schedule of the heads' SG"를 정합니다. 그런데 구성원 자신의 녹색 호출(모니터 경로)은 origin 접근로의 SG **합집합**을 적분합니다(fixed_signal_schedule.py:68-89) [읽음].
   - R-obs-b T2700 한 주기 탐침: native 예산 10행 중 **9행**에서 헤드 SG는 적색인데 구성원은 녹색인 초가 있습니다. 예: SC106 W(1210015700|nSG2)는 헤드 SG {2}, 구성원 SG {1,2,5,6}; SC102 S(1220019303|nSG8)는 헤드 {8}, 구성원 {3,8,18}. 같은 행 안에서도 구성원끼리 다른 경우가 1행(1210015700|nSG2)입니다.
   - 그래서 어댑터가 같은 모니터 스케줄을 헤드 SG로 적분하는 도우미를 녹색 함수의 속성으로 내놓게 했습니다(A:1662-1677). 키 없는 경로에서는 속성만 생기고 호출되지 않습니다. U5는 이 값을 φ_g로 씁니다.
   - **결과: native 예산 행 구성원은 헤드 SG 녹색 창 밖에서 방류하지 않습니다.** 집합이 구속하지 않아도(x = r) r에 φ_g가 들어가므로 구성원 자신의 합집합 녹색보다 좁아집니다. 계약 정의를 따른 것이지만 그룹 합 제한을 넘는 행동 변화이고, 450 s당 약 760~890대의 intended를 깎습니다(§9.1).
   - 현시 행은 모든 구성원이 같은 현시라 첫 흐름 구성원의 호출이 모든 구성원의 호출과 같습니다(SAC.phase_fraction은 현시만 봄, signal_actuation_contract.py:551-581) [읽음]. 탐침에서 현시 예산 행의 구성원 간 차이는 Q2 두 행뿐이었는데, U1+U3 권한(p4)으로 탐침했기 때문입니다. Q2 권한에서는 두 movement가 p3입니다(§7).
2. **`port.ready()`는 메서드가 아니라 `DelayedPort.ready` 속성입니다**(계획 §C.3의 미결 항목) [읽음]
   - LOR 포트 7개는 모두 `DelayedPort(interval_service=True)`입니다(lane_plant_runtime.py:363-365). `ready`는 이미 커넥터 출구에 닿은 재고이고, `release`가 구간 안에 도착하는 코호트를 사건 단위로 더합니다(metanet_calibration_v1/canonical_harness.py:101, :139-166).
   - 10643의 `CumulativeLane.ready`(physical_urban_transport.py:90-91)는 LUR 포트라 U5 구성원이 아닙니다.
   - 가중치 β × ready는 스텝 시작 값입니다. 스텝 중간에 도착하는 코호트는 그 스텝에서 서비스되지 않고 다음 스텝으로 넘어갑니다. 그래서 포트 방출이 늘 배정 이상이 되어 **순차 잔여는 v3b 재생에서 한 번도 생기지 않았습니다**(§5). 이 경로는 단위 시험(T2:1838)으로만 검증됐습니다.
3. **요청의 용량 부분은 구성원의 plant 용량(`_movement_capacity_flow`)이고, 집합 용량은 s_g × 하한 비율입니다.** 계약 식은 s_g × |lanes(m)|입니다.
   - 하한이 구속하지 않으면(단계 4의 99상태, 이번 모든 상태) 두 식은 같은 값입니다.
   - 하한이 구속하면 U4가 구성원을 같은 비율로 올리므로, 예산도 같은 비율로 올려 하한이 예산에서 사라지지 않게 했습니다 [추론].
   - 요청의 곱 순서는 UFA의 intended와 같습니다(`T_u_h × φ × cap`). 그래서 구속이 없고 φ가 같을 때 min이 원래 intended를 그대로 돌려줍니다.
4. **x = r일 때도 min(intended, x_m)을 겁니다.** 원시 단언(Σ 실행 ≤ C_S)이 늘 성립하려면 필요합니다. 구성원의 φ나 용량이 그룹 값보다 크면 구속이 없어도 깎입니다. 주로 native 행이 해당합니다(1번).
5. **그룹 닫기 위치**: 계획은 "LUR advance(UFA:1006) 뒤"였지만 `urban_substep_accounted` 끝, 즉 `urban_allocator` 완료 직전에 두었습니다. 예산 행의 실행(off-ramp 배수, 정규 방류)이 모두 그 전에 끝나고, 장부 기록이 `urban_allocator` 방문 안에 들어가기 때문입니다. 위임 행(71)은 LUR이 차로 단위 기록(`lane_urban_*`)을 이미 남기므로, U5는 설치 때 차로당 율 증거만 남깁니다.
6. **구성원 단위 원시 단언을 더했습니다**(실행 ≤ x_m + 1e-7). 할당이 어느 경로에서 빠지면 바로 드러납니다.
7. **정적 축소는 U4 설치에서 적용합니다**(HSC:296-300이 SHG의 식 SHG:133을 부름). 그래서 헤드 하한·verify_final·결정 기록이 모두 축소값을 봅니다. configure가 설치값 = 식 값인지 다시 확인합니다.
8. **Q2를 지금 연결했습니다**: β 원천 이름 `routing_v3b2q2`를 등록했습니다(A:4024-4031, beta_source.py:40). 계약 전체 대조(현시)가 Q2 권한을 요구하기 때문입니다(단계 4 §10-2). 키 없는 튜닝과 커밋된 config는 이 이름을 쓰지 않습니다(T2:1942).
9. **순차 잔여 허용오차 1e-9대**: 포트 부족분이 이 값 이하이면 되돌리지 않습니다(부동소수 잡음).
10. **1093 pre-head**는 단계 4에서 이미 `B_g − W/N 소비` 규칙입니다(native_input_prehead.py:274-280, sdmpc_aggregate.py:278-281) [읽음]. U5는 증거(행·s_g)만 기록합니다.
11. **미구현 거부**는 이제 U6만 이유로 C3 튜닝을 거부합니다(HSC:65-70). 이번 하네스는 이 함수만 메모리에서 끕니다(`H/u5_arm.py`).
12. `head_resource_contract`(10619/10629)와 `adapter.sdmpc_spatial_receiving`은 C3 설치 맨 앞(HSC:278-279)에서 거부하고, UFA의 spatial 분기에서도 한 번 더 거부합니다(UFA:573-574). HSR은 고치지 않았습니다(`[C-15]`). C3 팔에서는 HSR 뷰가 없어 10619/10629 경로가 돌지 않습니다(HSR.configure는 키가 없으면 `{}`, head_service_resources.py:27-35) [읽음].

---

## 3. 단위 시험 [실행]

`python -B -m unittest test_n31_urban_batch2`(cwd `N31/tests`, BELOW_NORMAL, 스레드 1) → **Ran 74, OK**(단계 4의 54 + U5 20). 스위트 실행(§4, codex 파이썬)에서도 74 OK입니다.

| 시험 (T2) | 계획 §5.1 항목 |
|---|---|
| `U5ConfigureTests` (:1541) | 계약 뷰(57행·162구성원·집합 101·off-ramp 포트 2·정적 축소 합 1.0·pickle < 40 kB·계수 초기화); `head_resource_contract`·spatial 공존 거부, U4 없이 거부; 망 핀·분할 규칙·미결 부류·스키마·U4가 읽은 계약과 다른 핀 거부; inpx 재계산(헤드 위치, 헤드 뒤 커넥터, 구성원 출구) 불일치 거부; 구성원 kind·수신·ramp 불일치, U1+U3 현시(Q2 아님) 거부, U1 물리 커넥터·β 표 sha 불일치 거부; laminar 아님·집합 밖 구성원 거부, 트리 모양 |
| `U5FinalizeTests` (:1666) | 정상 finalize(완결성 342 = 277 + 65, 포트 두 개, 위임 율 증거); 회계 substep 없음 / LOR 없음 / 포트 없음 / 직행 포트 / native 스케줄 없음 / 예산 구성원 용량 변경 / 흐름 표지 불일치 / 계약·허용 목록 밖 흐름 movement / LUR 출구 불일치가 각각 오류; 워커 확인은 cfg를 바꾸지 않음(pickle 동일) |
| `U5AllocatorTests` (:1740) | 여유 있으면 x = r(같은 객체); 구속 시 모든 laminar 집합·구성원 한도 만족, 뿌리 가득, 가중치 비례, 요청에서 포화; 가중치 0 → 0; 결정론(입력 순서와 무관한 항목 순서); 가중치 = 큐와 β × port.ready(stock 아님), LOR 없으면 오류; 적용(min), 하류 막힌 몫 재분배 없음, **원장 없이도 원시 단언**(구성원 초과·집합 초과 `ArithmeticError`), 미배수·이중 배수·이중 수락 오류; 포트 부족분은 정규 구성원에게 되돌아가고 하류 막힘 몫은 되돌아가지 않음; 포착 원장 기록 3종·출처 키, 원장의 초과 수락 거부 |
| `U5WiringTests` (:1879) | UFA 순서(램프 루프 → 할당기 → 배수(할당 전달) → 순차 잔여 → `_corridor_intended` → U5 min → movement_limits → 수락 → 닫기 → `urban_allocator` 완료), spatial 분기의 거부; LOR `requests`는 순수 함수이고 할당으로 service를 자름(수신 여유 예약도 그에 맞게); native 헤드 녹색 도우미 = 모니터 적분(헤드 SG, 클램프, 스케줄 없으면 오류); Q2 원천 등록, 커밋 config는 Q2 원천을 쓰지 않음, 어느 런타임 모듈도 import 시점에 U5 모듈을 부르지 않음 |
| U4 시험 갱신 두 곳 | `c3_tuning`이 `head_resource_contract`를 뺌(U5가 대체, :1109-1118), 구성원 용량 기대값에 SC7 정적 축소 반영(:1223-1245) |

- 계획 §5.1 U5 행 중 "LOR 분리 뒤 `assert_mirrors`·`release` 불변"은 재생으로 봤습니다. 키 없는 LOR은 G-ID(§8)가, U5 경로의 LOR 불변식(`assert_mirrors`, 방출 ≤ 한도·재고)은 C3 재생 전부가 매 스텝 실행했습니다(예외 0).

## 4. 스위트 [실행 `S5/suites`, 대조 `S5/suite_compare_vs_stage4.json`]

- `H/run_suites.py`(단계 3·4와 같은 40실행, codex 파이썬 + review-deps)를 최종 트리(`baabf7af…`)에서 돌렸고, 단계 4 최종 스위트와 비교했습니다: **회귀 0, 사라진 실행 0.**
  - n31 OK(skip 3), n31_batch2 74 OK, u40_extra 11 passed
  - diag11·extra_known은 이전과 같은 실패 id
  - 생성기 `--check` 15/15
- 끝난 뒤 `git status` 39줄(우리 변경만), diff sha는 그대로였습니다.

---

## 5. §5.2 단언: 그룹 합 ≤ 차로 × s × g (멈춤 규칙) [실행 `R5/stage5_results.json` `assertion`, 상태별 `R5/stage5_assertion_per_state.json`]

- **도구**
  - `H/u5_paths.py`: 단계 5 팔 튜닝 `R5/tunings/c3_u5_arm.json`(`13f4fa1d…`) = U1+U3(`f137f711`) + C3 세 키 + Q2 권한·β(`routing_v3b2q2`), U4가 대체한 키와 `head_resource_contract`는 뺌. 메모리 패치는 `c3_not_implemented` 하나뿐입니다.
  - R-obs-b 상태에서 SDMPC 결정(wu-link)을 첫 도함수 요청까지 돌리고, 그 자리에서 check_paths의 `exact`와 같은 호출(SDMPC 수평선 3 × 150 s, route-bins 집계·예측 캐시 켬, **포착 원장**)을 돌립니다.
  - T1·T150은 SDMPC 입구가 거부합니다(직전 action 없음 / 직전이 T−150이 아님, A:13094·:13102). 그래서 `H/u5_paths_nc.py`로 run 자신의 no-control 결정 안에서 같은 상태·최종 제어·3스텝 forecast로 정확 450 s를 돌렸습니다(cohort 경로).
  - 연쇄 `H/stage5_chain.py`: 한 번에 하나, BELOW_NORMAL, 스레드 1, `nbc_b2i`, codex 파이썬. 외부 재생은 기록만 했습니다(전 구간 다른 워크플로의 폐루프 VISSIM 1·cscript 1이 돌았음).

| 항목 | R-obs-b 61상태 (SDMPC 입구 59 + no-control 입구 2) |
|---|---|
| 할당기 스텝 | 27,450 (= 61 × 450) |
| 원시 단언 검사 | 행 1,564,650 · 집합 2,772,450 · 구성원 4,446,900 (상태당 25,650 · 45,450 · 72,900) |
| **허용오차(1e-7)를 넘은 검사** | **0** |
| 최대 잔차 Σ 실행 − C_S / 실행 − x_m | 4.44e-16 / 1.67e-16 (반올림 수준) |
| 포착 원장 기록 | 7,219,350건 = 그룹 1,564,650 + 집합 1,207,800 + 구성원 4,446,900 |
| 원장 exceedance 최대 | 4.44e-16 (원장의 isclose 허용 안) |
| 질량: 그룹 기록의 수락 = 같은 스텝 구성원 transfer | 4,446,900원천, 최대 차 **0.0** |
| assert_stocks 최대 | 9.94e-9 (SDMPC 입구) / 1.33e-8 (T150, no-control 입구; U5 끈 팔도 같은 값 → U5 탓 아님) |
| 구속한 행-스텝 | 112,743 (7.2%), 상태당 구속 그룹 45~46, water-filling 라운드 최대 2 |
| 순차 잔여 | 0회 (§2.2-2) |
| "U5 없는 C3" 팔 | 할당기 스텝 0, U5 기록 0 (61/61) |

- **다른 경로 (B, 2700 / 4500 / 6300)** [실행 `R5/u5_paths/paths_T*.json`]

| 경로 | 스텝 · 집합 검사 · 구성원 검사 (상태당) | U5 기록 | 최대 초과 |
|---|---|---|---|
| cohort(route-bins 끔) | 450 · 45,450 · 72,900 | 25,650 / 19,800 / 72,900 | 4.4e-16 (질량 차 0.0) |
| 연속 완화(tangent 워커, 스칼라 대리) | 워커 안(원시 단언 실패 시 워커 오류) | 25,650 / 19,800 / 72,900 (스트림 요약) | 1.1e-15 ~ 1.6e-15 |

  - 워커가 U5 모듈을 AST 변환으로 적재했습니다(`transformed_source_sha256`에 SHG). 워커의 `install_worker_runtime`이 워커 확인을 통과했습니다.
  - cohort 경로 목적값은 route-bins와 5.7e-14 이내입니다(T2700: 510.6054997452528 대 …27, 단계 0과 같은 수준).
  - 첫 B 실행은 하네스 버그로 결과를 잃었습니다(exact가 세 값을 돌려주게 바꾼 뒤 noagg 호출부를 고치지 않음; `R5/u5_paths_B_harness_bug/`). 고친 뒤 다시 돌린 값이 위 표입니다.
- **멈춤 규칙 판정**: 단언 초과 0, 검사 수 > 0(모든 상태·모든 경로), 포착 기록 > 0 → **걸리지 않음.**

## 6. 10634 동일 (하네스 "U5 없는 C3" 팔) [실행 `R5/stage5_results.json` `assertion.eq_10634`]

- 방법: 같은 프로세스·같은 상태·같은 제어에서 정확 450 s를 두 번 돌렸습니다. 한 번은 U5 켜짐, 한 번은 메모리에서 U5를 끈 팔(`cfg.network.shared_head_groups = None`, SC7 정적 축소 구성원을 s_g × |lanes|로 되돌림)입니다. 실행 순서는 상태마다 번갈아 두었습니다.
- 지문: 자원 이름에 10634가 들어간 장부 기록(LUR 출구 수신, 회랑 incoming 서비스)과 10634 풀 세 movement의 transfer. 두 팔의 전체 transfer를 스텝·경로 키 해시로도 비교했습니다.

| 항목 | 결과 |
|---|---|
| 첫 스텝의 10634 지문 | **61/61 동일** |
| 450 s 전체 동일 | 2/61 (T1, T150) |
| 차이가 있는 59상태 | 전체 transfer는 첫 스텝부터 다름(U5가 다른 교차로 흐름을 바꿈) → LUR 입력·출구가 **+134~284 s**에 처음 다름 → 10634가 **+225~384 s**에 처음 다름. **59/59에서 LUR 입력이 10634보다 먼저** 갈라짐 |
| 10634 지문 최대 차 | 0.50대 (450 s 중 한 행) |

- 해석 [추론]: U5는 10634·71 구성원을 뷰에 두지 않고(위임 행), LSS 풀·LUR 코드도 바꾸지 않습니다. 첫 스텝이 같고 차이가 LUR 입력보다 늦게 나타나므로, 10634 차이는 다른 그룹의 방류 변화가 SC1004 서측 접근로로 전파된 결과입니다. U5가 10634를 이중으로 강제하지는 않습니다.
- **판단 필요**: 계획의 "10634 동일"을 450 s 전체의 비트 동일로 읽으면 59/61에서 성립하지 않습니다. 저는 "첫 스텝 동일 + 차이가 상류 입력 뒤에만 나타남"으로 판정했습니다. 더 엄격한 확인이 필요하면, LUR 입력을 두 팔에서 고정하는 반사실(예: U5를 SC1004 서측 상류 행에만 끄기)을 단계 7에서 만들 수 있습니다.

## 7. 설치 단언·LIVE·완결성 전수 (§4.5-1·12, §5.5) [실행 `R5/u5_install/`, `R5/stage5_results.json` `full`·`install`]

- **LIVE (C: R-obs-b 1 / 150 / 2700 / 9000 no-control 전체 결정, 한 스텝 예측 150 s)**: 네 결정 모두 exit 0, controller·prediction ok

| 함수 | 결정당 호출 | 계획 기대 |
|---|---|---|
| `head_saturation_capacity.install` / `shared_head_groups.configure` / `finalize` | 1 / 1 / 1 | 1 |
| `StepAllotment` / `after_offramp` / `close`(원시 단언) | 150 / 150 / 150 | 스텝당 1 (정확 450 s에서는 450, §5) |
| UFA `urban_substep_accounted` | 150 | 스텝당 1 (vendor substep 0) |
| LOR `drain` / 할당이 있는 `requests` / 할당 없는 `requests` | 150 / 1,050 (7포트) / 0 | 각 스텝당 |

  - 원장 최대 차 6.0e-12~8.6e-9, 실패 0. 결정 기록 약 2.1 kB.
  - no-control action JSON은 단계 4(U4만) 대비 +1.9~2.4%(+6.9~7.0 kB)입니다. U5 기록 자체는 action 안에서 약 3.2 kB(0.85%)이고, 나머지는 U5로 바뀐 예측 출력 값의 자릿수 차이로 보입니다 [추론]. 58 MB급 SDMPC action에서는 0.01% 수준입니다.
- **완결성 전수 (§4.5-12 `[C-16]`)**: C3 팔로 설치한 **99상태 모두** configure·finalize 통과(R-obs-b 61은 A·C·G에서, S1 19·S0e 19는 D1·D2 설치 전용).
  - 모든 상태에서 흐름 movement 342 = 계약 277 + 허용 목록 65, 허용 목록 중 흐름 없는 것 0
  - Q2 두 movement는 p3
  - 위임 행 증거: LUR 차로당 율 1,582.5 veh/h 대 U4 s_g 1,724.3(71|p3, 0.918배)·1,754.2(71|p4, 0.902배). 계획대로 보고만 하고 고치지 않았습니다.
  - 설치 시간 중앙 약 17 s(S1·S0e, 하네스 계측 포함)
- **멈춤 규칙(회계 substep·LOR 미설치)**: 99 설치 모두 finalize 단언을 통과했고, 스텝 단위 LIVE 계수가 두 경로가 실제로 도는 것을 보여 줍니다 → **걸리지 않음.**

## 8. 키 없음 비트 동일 (§6.1 G-ID) [실행 `R5/probe/s5_{base,u1u3}`, `R5/sdmpc/s5_s1_T3600*`]

단계 5는 UFA·LOR·RS·어댑터·`beta_source`를 텍스트로 바꿨으므로, 키 없는 경로를 전부 다시 받았습니다. 비교 기준은 단계 1 b2 재생입니다.

| 관문 | 상태 | `MRS compare` | 한 스텝 포착 15필드 | 설치 스냅숏 | action JSON vs 단계 1 | 장부 |
|---|---|---|---|---|---|---|
| (a) 기본 튜닝 `d4327cbf` | R-obs-b 61 | **IDENTICAL 61/61** | 15필드 × 61 같음 | 용량 맵·urban_movements·`_LG_KINDS`·`_LTO`·`_SUS_*` 61/61, 설치 메타 비경로 차이 0 | 차이는 run_provenance와 벽시계뿐, **그 밖 0** | 최대 8.6e-9, 실패 0 |
| (b) U1+U3 `f137f711` | R-obs-b 61 | **IDENTICAL 61/61** | 같음 | 같음 | 같음 | 같음 |

| S1 3600 (U1+U3), `replay_decision_n31.ps1 -Root W` | 결과 |
|---|---|
| compare 5검사 | derived·action_csv·action_controls·objective **같음**, action_contract 다름(알려진 VSL 100/110 혼재, 단계 1~4와 같은 정의로 제외) |
| 녹색 / offset | 같음 / 같음 |
| 선택·유지 목적값 (기록 = 재생 = 단계 1) | 491.4356825691444 / 493.5432636752482 |
| tangent 2개 operations·event_counts (기록 = 재생 = 단계 1) | 12,123,157 · (7,850,416, 335,580, 630,241) / 11,962,967 · (7,778,513, 336,378, 630,972) |
| action JSON vs 단계 1 재생 | 행동이 아닌 부류만 다름: 벽시계, `request_sha256`·`frozen_context_token`·`response_token`, `transformed_source_sha256` 8개(이번까지 바뀐 LOR·`beta_source`·AGG·UFA·RS·RCC·A·NIP). 값 필드 차이 0 |

- `transformed_source_sha256`에 SHG가 없습니다. 키가 없을 때 AD 변환기가 새 모듈을 읽지 않는다는 뜻입니다.
- **판정: G-ID (a)(b) 통과, SDMPC 한 상태 통과.**

## 9. 보조 계수 (관문 아님, 단계 7 판단 자료)

### 9.1 U5가 intended를 깎은 곳과 이유 [실행 `R5/u5_cuts/cuts_T*.json`, 도구 `H/u5_cuts.py`]

같은 SDMPC 입구에서 정확 450 s(포착 없음)를 돌리며 `limit`·`offramp_service`를 primal 값으로만 세었습니다(값은 바꾸지 않음). "깎은 양"은 구성원 자신의 intended 대비 줄인 양의 합이며, 실제 방류 감소와 같지 않습니다(하류 수신이 어차피 막았을 수 있음).

| 상태 | 현시 행: 그룹 구속 | 현시 행: 요청 < 자기 intended | native 행: 그룹 구속 | native 행: 헤드 SG 녹색 < 자기 녹색 |
|---|---|---|---|---|
| 2700 | 6,421회 · 2,509대 | 0 | 465회 · 141대 | 1,099회 · 892대 |
| 4500 | 5,077회 · 1,987대 | 0 | 455회 · 125대 | 1,128회 · 845대 |
| 6300 | 4,087회 · 1,593대 | 34회 · 13.6대 | 252회 · 66대 | 912회 · 757대 |

- 가장 많이 깎은 그룹은 세 상태 모두 **127|p3**(그룹 구속, 810회, 약 480~500대)이고, 그다음은 1220008201|p3, 1220000201|p3, 1220007104|p3(Q2 SC1), 52|p3입니다.
- native 행의 "헤드 SG 녹색" 깎임이 전체 깎임의 약 25~30%입니다(§2.2-1).
- 현시 행 T6300의 34회는 off-ramp 구성원의 요청이 β × ready로 서비스보다 낮았던 경우로 보입니다(§2.2-2) [추론].
- 목적값(U5 − U5 없음, 정확 450 s): 61상태 중앙 −0.74 veh·h, 범위 −5.42 ~ +3.20, 43/61이 음수. 한 상태 예측의 목적값이라 관문 값이 아닙니다.

### 9.2 시간 [실행 `R5/stage5_results.json` `assertion.time_ratio_exact_over_nou5`, `R5/u5_profile/prof_T2700.json`]

| 측정 | 값 |
|---|---|
| 정확 450 s 포착 예측, U5 / U5 없음 (SDMPC 입구 59상태, 순서 교대) | **중앙 1.067배**(범위 0.97~1.16; U5 먼저 1.085, U5 없음 먼저 1.062). 중앙 57.0 s 대 52.6 s |
| no-control 입구 (T1 / T150, cohort 경로) | 106.3 / 98.1 s, 113.2 / 101.9 s |
| cProfile T2700 (프로파일러 부하 포함 203.6 / 182.5 s) | 도시 스텝 누적 +16.9 s 중 할당기 생성 5.1 s(φ·용량 호출 포함), 닫기 4.7 s(원시 단언 + 기록 118,350건; 기록 한 건 약 30 µs), `_movement_capacity_flow` +72,900호출 |

- 계획 §6.7의 시간 관문(결정 벽시계 중앙 ≤ 1.05, 단계 7)에 **위험 요인**입니다. SDMPC 결정 전체의 비율은 아직 재지 않았습니다.
- 줄일 레버(적용 안 함, 적용하면 G-ID와 이번 §5.2를 다시 받아야 함):
  - (a) 구성원 기록(상태당 72,900건, 전체 기록의 62%)을 구속한 행-스텝에만 남기기
  - (b) 현시 행의 φ_g와 구성원 용량을 UFA 정규 루프와 공유하기(스텝당 57 φ 호출·162 용량 호출)
  - (c) 큐·ready가 모두 0인 행은 풀이를 건너뛰기

---

## 10. provenance와 안전 [실행]

| 트리 상태 | diff sha256 | 무엇으로 확인 |
|---|---|---|
| 단계 5 시작(= 단계 4 끝) | `9c3fc54d…` | 시작 시 계산 |
| **최종** | `baabf7aff9f3774db6d929172dcc235b270998d4091815e2bd348097221f44bb` | 스위트 전후, 연쇄 세 번의 BEGIN = ALLDONE, 모든 산출 provenance |

- 최종 트리 파일 sha(앞 12자): SHG `7a3fbd969f19`, HSC `16f02e2a4683`, UFA `8eea2abf0326`, LOR `73de5297e684`, RS `1f698d458ba3`, A `f75438081cf4`, `beta_source` `fe5ab6b3ea0d`, T2 `7c78a4b61cc8`.
- 새 파일 0(`find -newer S5/marker_stage5_start`, 17:52): R-obs-b·S1·S0e 런 폴더, NC 5시드 폴더(`D:/VISSIM_runs/20260925_v3b`), `frozen/sdmpc31_cf3ce374_202609261037`, `frozen/sdmpc31_886a014a_202609260935`, OLD `D:/VISSIM-merge/sim3-n31-urban`. `frozen/` 최상위에도 marker 뒤 새 항목이 없습니다(17:40의 `sdmpc31_92fa4b8e_202609291737`은 이 단계 시작 전 다른 워크플로의 것).
- OLD: `git status` 0줄, HEAD `cf3ce37`. `sim3-n31-v3c1`: HEAD `9ed2ef0`, `claude/repin-v3c1-20260928`, `git status` 0줄. 어떤 명령도 이 둘에 쓰지 않았습니다.
- W의 `__pycache__` 없음(모든 실행 `-B`, `PYTHONDONTWRITEBYTECODE=1`). `evaluation/controllers/__tangentcache__`에 새 파일 6개가 생겼습니다(바뀐 소스의 AD 변환 캐시). .gitignore 대상이고 `freeze_manifest`가 비교에서 뺍니다(계획 §3).
- VISSIM·cscript를 시작·종료하지 않았습니다. 전 구간에 다른 워크플로의 폐루프(VISSIM 1, cscript 1)가 돌았고, 제 재생은 늘 하나였습니다. 멈춘 프로세스는 없습니다.
- 워치독·cscript·ps1 시험은 돌리지 않았습니다(`run_suites.py` 제외 목록). seed 37, RM 팔, 봉인 시드 59/61/67은 열지 않았습니다. 폐루프 런·커밋·push는 없습니다.
- 개발 중 두 번 시스템 파이썬(3.12.2, numba 없음)으로 개발 재생을 돌렸습니다(`S5/dev/`). 판정에 쓴 모든 재생·스위트는 이전 단계와 같은 codex 파이썬 3.12.14 + review-deps(numpy 2.3.5, numba 0.67.0)입니다.

---

## 11. 다음 단계로 넘기는 것 / 사용자 판단

1. **native 행의 녹색(판단 필요)**: 계약대로 헤드 SG 고정 계획을 φ_g로 썼습니다. 그 결과 native 예산 10행의 구성원이 헤드 SG 창 밖에서 방류하지 않으며, 450 s당 약 760~890대의 intended가 깎입니다(§2.2-1, §9.1). 구성원 자신의 합집합 녹색이 과대라는 뜻이기도 합니다(모니터 경로의 알려진 "union green" 성질, fixed_signal_schedule.py:112-118 주석). 이대로 둘지, native 행을 구성원 녹색으로 바꿀지 확인이 필요합니다.
2. **시간 부하(단계 7 위험)**: 포착 정확 예측이 중앙 1.067배입니다. 단계 7 시간 관문(≤ 1.05) 전에 §9.2 레버 (a)~(c)를 적용할지 판단이 필요합니다. 적용하면 G-ID와 §5.2를 다시 받아야 합니다.
3. **10634 동일의 정의(판단 필요)**: 첫 스텝 61/61 동일, 450 s 전체는 2/61. 차이는 상류 전파로 해석했습니다(§6). 더 엄격한 반사실이 필요하면 단계 7에서 만듭니다.
4. **하한 비율을 예산에 반영**(§2.2-3): 계약 문구(s_g)와 다릅니다. 하한이 구속한 적이 없어 값 차이는 아직 0입니다.
5. **U6(단계 6)**: `c3_not_implemented`(HSC:65)를 실제 U6 설치로 바꿔야 합니다. U6가 게이트 β·도착 스케줄을 바꾸면 finalize의 흐름 표지·완결성 검사가 새 값을 봅니다.
6. **후보 config(단계 9)**: C3 튜닝은 `urban.movements.physical_phase_authority` = Q2 파일, `urban.beta.source` = `routing_v3b2q2`, sha `b41d6a10…`이어야 하고, `head_resource_contract`를 빼야 합니다(U5가 대체). `make_config_n31.py`에 반영이 필요합니다.
7. **순차 잔여**: ready 가중치 때문에 v3b에서는 한 번도 생기지 않았습니다. 코드 경로는 단위 시험으로만 검증됐습니다.
8. **no-control action 크기 +1.9~2.4%**(U5 기록 0.85%): §2-9의 1% 기준을 no-control action에도 적용한다면, 기록을 줄이는 레버(부류·off-ramp 목록·정적 축소 구성원 값 생략, 약 −0.6 kB)가 있습니다.
9. **T1·T150은 SDMPC 입구가 거부**합니다(A:13094·:13102). §5.2에서는 no-control 입구(cohort 경로)로 대신 확인했습니다.
10. **T150 assert_stocks 1.33e-8**: 계획의 참고값(1e-8, 묶음 1: 9.9e-9)을 넘지만 U5 없는 팔도 같은 값이라 U5와 무관합니다(no-control 입구의 cohort 경로). 코드 허용오차는 1e-6입니다.
11. **이월(그대로)**: C6 키 1.0/8/3/3을 후보 config에(단계 9), C6 경계 경보(206.53 표지) 추이는 단계 7 보조 지표, `ControlAction.fixed`의 700 allocation(단계 4 §6), 계획 밖 1,400 사용처 둘(단계 4 §10-4), v3c1 재유도 때 생성기 상수 인자화, 동결 전 `__pycache__` 삭제(현재 없음).

## 부록: 산출 파일

- 보고서: `B/impl/STAGE5.md`
- 코드 백업(단계 4 판): `S5/backup_stage4/`. 편집 도구: `S5/eol_edit.py`, `S5/eolcount.py`, 편집 명세 `S5/edit_*.py`·`S5/spec_*.json`
- 탐침: `S5/u5_native_phi_probe_T2700.json`(도구 `H/u5_native_phi_probe.py`)
- 스위트: `S5/suites/tests/`, `S5/suite_compare_vs_stage4.json`
- 연쇄: 발사 `S5/launch_chain5.cmd`(C,D1,D2,E1,E2,F,A,B), `S5/launch_chain5_post.cmd`(G,H,I), `S5/launch_chain5_b.cmd`(B 재실행); 로그 `R5/chain.log`, `R5/logs/`; 팔 튜닝 `R5/tunings/c3_u5_arm.json`
- 결과: §5.2 `R5/u5_paths/robsb_T*.json`(59), `R5/u5_paths/robsbnc_T{1,150}.json`, 다른 경로 `R5/u5_paths/paths_T*.json`(실패본 `R5/u5_paths_B_harness_bug/`); 설치 `R5/u5_install/{robsb_full,s1,s0e}/`; G-ID `R5/probe/s5_{base,u1u3}/`; SDMPC `R5/sdmpc/`; 깎임 `R5/u5_cuts/`; 프로파일 `R5/u5_profile/`; 분석 `R5/stage5_results.json`, `R5/stage5_assertion_per_state.json`
- 하네스(새로): `H/u5_arm.py`, `H/u5_install.py`, `H/u5_paths.py`, `H/u5_paths_nc.py`(+ `H/make_u5_paths_nc.py`, `H/u5_paths_nc_template.txt`), `H/u5_cuts.py`, `H/u5_profile.py`, `H/stage5_chain.py`, `H/stage5_analyze.py`, `H/u5_native_phi_probe.py`
- 개발 실행(판정에 안 씀): `S5/dev/`
- 트리 새 파일: SHG. 수정: UFA, LOR, RS, HSC, A, `beta_source.py`, T2
