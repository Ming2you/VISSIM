# 도시 묶음 2 — 단계 4 보고 (U4 용량 척도 교체)

- 작성: 2026-09-29 14:40 시작 → 17:35 완료. 이전 시도의 단계 4 부분 결과는 없었습니다(`B/impl`에 `stage4` 없음, 시작 시 트리 diff `0f56bd42…` = 단계 3 끝과 같음 [실행]).
- 계획: `B/BATCH2_PLAN.md` §4.4(1, 1b, 2~8), §4.1-1 `[검토 C-8]`(차로 파일 핀), §2-2 `[검토 C-7]`, §5.1 U4 행과 검토 추가 행, §6.3 T1a `[검토 C-20]`, §6.1 G-ID, §7 단계 4 행과 멈춤 규칙(경계 allocation 구속 > 0), 부록 C-1·C-7·C-8·C-14·C-20. 사용자 결정: C3 = U4+U5+U6(전부 아니면 전무, U4 단독 금지), U5는 과대 그룹 전부 + native(Q1), Q2 = SC105·SC1 p3 증거 + SC7 정적 축소, Q3 = v3b 폐루프 없음.
- 대상 트리: `D:/VISSIM-merge/sim3-n31-urban-b2` (브랜치 `claude/urban-batch2-20260928`, HEAD `cf3ce37`). 변경은 **커밋하지 않고** 작업 트리에 남겼습니다. push·rebase·다른 브랜치/워크트리 조작, VISSIM·cscript 시작/종료는 없습니다.
- 표기: **[실행]** 이번에 직접 돌리거나 계산한 값 / **[읽음]** 파일에서 읽은 값 / **[추론]** 직접 증거 없이 끌어낸 판단.
- 약어: B = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/urban-b2`, S4 = `B/impl/stage4`, R4 = `S4/run4`(재생 체인), H = `B/harness`, W = b2 트리, A = `W/evaluation/controllers/vissim_stackelberg_adapter.py`, HSC = `W/evaluation/controllers/head_saturation_capacity.py`(새 모듈), RS = `runtime_setup.py`, RCC = `route_choice_corridor.py`, NIP = `native_input_prehead.py`, AGG = `sdmpc_aggregate.py`, LOR = `lane_offramp_runtime.py`, SHO = `signal_head_observation.py`, T2 = `W/diagnostics/sdmpc_n31_20260924/tests/test_n31_urban_batch2.py`, N31 = `W/diagnostics/sdmpc_n31_20260924`, U = `N31/urban`. 줄 번호는 최종 작업 트리 기준입니다.

---

## 0. 결론

**멈춤 규칙에 걸린 것은 없습니다(stop=false).** 경계 allocation 구속은 실제로 평가된 제어에서 0이고, 계획 §4.4의 1·1b·2~8을 모두 구현했습니다. 다만 첫 결정(T=1)의 "기준 제어"에 관한 발견 하나가 있습니다. 판단이 필요할 수 있어 §6에 따로 적었습니다.

| 항목 (계획 위치) | 결과 | 근거 |
|---|---|---|
| U4 설치 함수 (§4.4-1) | HSC 새 모듈 + A `install_movement_capacity_by_saturation`. RS:128 자리에서 C3 키가 하나라도 있을 때만 부르고, 없으면 옛 함수를 그대로 부릅니다 | [실행] §2.1 |
| C3 결합 (§2-2) | 셋 다 있거나 셋 다 없어야 합니다. 셋이 다 있어도 **U5·U6 코드가 생길 때까지(단계 5·6) 설치를 거부**합니다. U4 단독 배포를 막기 위해서입니다 | [실행] §2.2 |
| 계약 2단계 적재 1단계 (§4.4-1 `[C-1]`) | 표·계약·차로 파일 sha, 스키마, 스냅숏 망, 표↔계약 교차 일관성을 확인하고 구성원·차로·소유자만 읽습니다. 2단계(RS:207 뒤 전체 대조)는 단계 5 몫입니다 | [실행] §2.3 |
| 차로 파일 핀 (§4.1-1 `[C-8]`) | U4 표에 `lane_files`를 더해 재생성했습니다. 값은 바뀌지 않았고 키 하나만 늘었습니다. `--check` 바이트 재현, 교차 검사 OK | [실행] §2.4 |
| 헤드 하한 차로 비율 콜백 (§4.4-1b `[C-1]`) | `distribute_by_u4_ratio`: 하한이 구속하지 않으면 **아무것도 쓰지 않습니다**. 구속하면 비율 하나로 올립니다. 99상태 모두에서 구속 0 | [실행] §2.5, §5 |
| 소유자 제외 (§4.4-2) | 게이트 peel-off는 U4 뒤에 게이트 설치가 값을 기록합니다(순서 증명). LUR 출구와 10634 풀은 lane plant 값인지 설치 끝에서 확인합니다 | [실행] §2.6 |
| `lane_group_kinds` (§4.4-3, 단계 2 이월) | C3 세 키가 모두 있을 때만 넓힐 수 있고, 그때는 네 kind 전부여야 합니다. `on_ramp`은 오류입니다 | [실행] §2.7 |
| 회랑·1093·LOR (§4.4-4~6) | 회랑 turn은 조회 함수, 무신호 연결로·분기는 표 기본값입니다. 1093 pre-head 예산은 첫 헤드 그룹의 s_g입니다(NIP·AGG 같은 식). LOR direct는 표 기본값입니다 | [실행] §2.8~2.10 |
| 계측 (§4.4-7·8) | `projection_diagnostics['u4_saturation']` 약 1.8~2.0 kB(키가 있을 때만) | [실행] §2.11 |
| 단위 시험 (§5.1) | T2 **54 OK**(단계 3의 38 + 16) | [실행] §3 |
| 스위트 | 40실행 단계 3(R3b) 대비 **회귀 0**(표 재생성 뒤 diff와 최종 diff에서 각각) | [실행] §4 |
| **T1a (하네스 패치)** | R-obs-b 61 + S1 19 + S0e 19 = 99상태: 누락 0, 설명 안 되는 최종값 0, 그룹 밖 무소유 변경 0, 헤드 하한 구속 0 | [실행] §5 |
| **멈춤 규칙: 경계 allocation** | 99상태의 이전 action allocation은 전부 `{}`. 스모크 결정의 평가 제어에서 경계 구속은 0/25,650 호출(no-control 4결정), SDMPC S1 3600 부모 프로세스 0/25,887, 결정 기록의 allocation 필드 9개 모두 `{}` | [실행] §6 |
| G-ID 키 없음 (a)(b) | R-obs-b 61 × 기본·U1+U3: `MRS compare` **IDENTICAL 122/122**. 한 스텝 포착 15필드·설치 스냅숏·설치 메타가 단계 1 기록과 122/122 같음, action JSON 차이는 run_provenance 해시와 벽시계뿐 | [실행] §7 |
| SDMPC 키 없음 (S1 3600) | derived·action_csv·action_controls·objective 같음(action_contract만 다름, 알려진 VSL 100/110), 녹색·offset·선택/유지 목적값·tangent 계수가 기록 및 단계 1 재생과 같음 | [실행] §7 |
| U4 스모크 | no-control 4결정(T1·150·2700·9000) 모두 ok, 장부 최대 8.6e-9. SDMPC S1 3600: 결정 완료(controller ok, prediction ok, 장부 4.7e-9, 548.6 s, 외부 재생 1개와 동시) | [실행] §8 |

---

## 1. 재개 확인

- 단계 4 부분 결과가 없었습니다. 그래서 새로 시작했습니다 [실행: `B/impl`에 `stage4` 없음, 시작 시 `worktree_diff_sha256` `0f56bd42…` = STAGE3 최종값].
- 재사용한 것
  - 하네스: `H/_prov.py`, `H/u40_probe.py`(G-ID 재생), `H/sdmpc_replay.py`, `H/run_suites.py`, `H/compare_suites.py`. 모두 수정 없이 썼습니다.
  - 비교 기준: 단계 1 키 없음 재생(`B/impl/stage1/probe/b2_base`, `b2_u1u3`, `…/sdmpc/b2_s1_T3600`), 단계 3 최종 트리 스위트(`B/impl/stage3/run3b/suites`).
  - 키 없는 코드 경로는 단계 1 이후 C6(키 게이트)만 바뀌었습니다 [읽음 STAGE2·STAGE3].
- 중단 한 번 [실행]
  - 첫 체인(`S4/run4_aborted_1`, 15:14 BEGIN, diff `06b20091…`)은 R-obs-b 12상태를 돈 뒤 제가 멈췄습니다(PID 8872·1860, 자식 없음 확인).
  - 이유: 결정 기록의 "기준 제어" allocation 계수가 첫 결정에서 합성 `fixed` 제어를 세고 있었습니다(§6). 이를 고치고, 평가된 제어의 allocation 계측을 하네스에 더했습니다.
  - 그 12상태는 판정에 쓰지 않았습니다. 체인은 새 diff(`9c3fc54d…`)에서 처음부터 다시 돌렸습니다.

---

## 2. 바꾼 것 (작업 트리, 커밋 안 함)

| 파일 | 줄 | 내용 |
|---|---|---|
| HSC (새, 522줄) | 전체 | U4 모듈: 로더, 설치, 헤드 하한 콜백, 소유자 조회·확인, 결정 기록 |
| A | :4268 `c3_keys_present`, :4281 `install_movement_capacity_by_saturation`, :4291 `_head_lane_group_distribute` | C3 키 존재 판정(순수), U4 설치 진입점, 헤드 하한·C6 멤버 탐침의 배분 함수 선택 |
| A | :4336-4342 `install_lane_group_membership` | C3 세 키가 있을 때만 확장하고, 그때는 네 kind |
| A | :4409-4414 헤드 관측 `if` 안 | U4면 차로 비율 콜백 + 구성원 무변경 사전 확인 |
| A | :3380 `install_gate_onramp_queue`(기록 :3414-3418) | U4 뷰가 있으면 게이트 값을 소유자 기록으로 남김 |
| A | :13840-13846, :14164, :14167-14170 `main` | 결정 기록(`projection_diagnostics['u4_saturation']`), C6 멤버 탐침 함수, 최종 제어 allocation 계수 |
| RS | :128-133, :179-185, :265-269 | C3 스위치, 회랑에 조회 함수 전달, 설치 끝 소유자 확인 |
| RCC | :58-85, :305, :406-416, :450-455, :554 | `saturation` 인자(스칼라와 공존 금지), turn 서비스 조회, 거부 두 가지, 출처 표지 |
| NIP / AGG | NIP:103-116, :274-277 / AGG:278-281 | 1093 pre-head 예산의 척도(같은 평가 순서) |
| LOR | :13-17, :58, :63 | direct·local_upstream 차로당 서비스 |
| `scripts/derive_head_saturation.py` | :29-30, :59-63, :798-801 | 표에 `lane_files` 핀 |
| `scripts/check_urban_batch2_evidence.py` | :11-13, :71-82 | 표의 차로 파일 핀 = 계약의 차로 입력 = 디스크 |
| U4 표 `U/head_saturation_v3b_20260929.json` | – | 재생성 `09462676… → 67176609…` (`lane_files` 키만 추가) |
| T2 | :44-55(설명), :208, :297-299, :1062-1439 | 확장 시험 1개, 읽은 키 집합 갱신, U4 시험 15개 |

- 키가 없을 때 새 모듈은 import되지 않습니다. 모든 import가 함수 안에 있고, C3 키나 설치된 뷰를 거쳐야 도달합니다(T2:1426 정적 시험).
- **줄바꿈 사고와 복구** [실행]
  - 편집 도구가 T2(LF)를 전부 CRLF로, `runtime_setup.py`(CRLF·LF 혼재, `-text`)도 전부 CRLF로 바꿨습니다.
  - 제 첫 복구 스크립트는 git blob을 기준으로 삼아, `core.autocrlf=true`(시스템 gitconfig)로 CRLF 체크아웃된 `sdmpc_aggregate.py`·`lane_offramp_runtime.py`를 LF로 잘못 바꿨습니다. `git ls-files --eol`(`i/lf w/crlf`)로 확인하고 곧바로 CRLF로 되돌렸습니다.
  - 최종 `S4/fix_eol.py` 규칙: `-text` 파일은 blob의 줄별 줄바꿈, autocrlf 파일은 CRLF, 추적 안 된 파일은 단계 3 사본의 방식. 내용 동일은 단언으로 확인했습니다.
  - 복구 뒤 diff는 실제 변경 줄만 남습니다(RS `+14/-2`). 모든 스위트·체인은 복구 뒤 트리에서 돌았습니다.

### 2.1 U4 설치 (계획 §4.4-1) — HSC:266 `install`

- **값**
  - 계약 구성원: `cap_m = s_g × |lanes(m)|`입니다. 두 행에 걸친 구성원은 행별 합이고, v3b에서는 `SC103_S_SC6_to_W_SC102`(native nSG3 1차로 + nSG8 1차로) 하나뿐입니다.
  - 외래 현시 구성원(15)의 외래 차로는 버립니다(계획 §10-4 v1). 외래로만 나오는 movement는 0개입니다 [실행].
  - 그 밖의 movement: 표 기본값 1,850 × `install_movement_capacity_by_lanes`와 **같은 차로 수**입니다. 내부/경계 차로 파일, turn 종류 중앙값, 경계 전체 중앙값 규칙이 같습니다(HSC:230 `_lane_counts`, perimeter "all" + boundary_out 포함과 같음).
  - 옛 함수의 차로 수와 같음은 T2:1199가 모든 그룹 밖 movement에서 비트 단위로 확인합니다(`per_lane × lanes` = 옛 값).
  - 맵은 통째로 교체합니다(옛 함수와 같음).
- **R-obs-b T2700 설치 결과** [실행]
  - 그룹 174, 구성원 movement 284, 기본값 87(그중 중앙값 차로 40), 두 그룹 구성원 1
  - 옛 척도(단계 3 포착, 206.53 정규화) 대비 비율 중앙값 8.96 = 1,850/206.53. 범위 0.91(1210012001|p3 직렬 헤드 1,568.6 대 1,729.2)~91(옛 β 배분 하한 몫 20.3 → 1,850)
  - 회랑 4개의 `per_lane_capacity_veh_h` 1,850, 1093 pre-head `s_g` 1,568.6
- **거부하는 것**(HSC:120 `load`)
  - 대체된 키 `per_lane`·`equivalent_uniform_veh_h`·`perimeter`·`perimeter_include_boundary_out`. 남으면 죽은 키가 되기 때문입니다.
  - `measured`가 켜졌는데 헤드 관측이 꺼진 경우. 옛 measured 경로가 U4 값을 β로 다시 나누기 때문입니다.
  - `lane_group_kinds`가 네 kind가 아닐 때, 계약 구성원 kind가 선언 밖일 때, 소유자 이름을 모를 때
  - 계약 구성원이 설치 시점에 런타임 movement가 아닐 때, 게이트 peel-off가 구성원일 때
- **설치 시간** [실행]: U4 설치 자체 22–57 ms(99상태). 설치 전체는 R-obs-b 평균 10.1 s, S1·S0e 약 17 s입니다(하네스 계측 포함).

### 2.2 C3 결합과 "아직 구현 안 됨" 거부 (계획 §2-2, `[C-7]`)

- RS:128이 `a.c3_keys_present(tuning)`로 판정합니다. 순수 함수이고, 키가 없으면 `()`입니다. 그러면 옛 `install_movement_capacity_by_lanes`를 그대로 부릅니다. 스텁 어댑터를 쓰는 기존 시험도 거짓 값을 받아 옛 경로로 갑니다.
- 키가 하나라도 있으면 HSC `install`이 **셋 다**인지 확인합니다(`all or nothing` 오류).
- 셋이 다 있어도 `c3_not_implemented`(HSC:62)가 거부합니다. 단계 4에는 U5·U6 코드가 없어서, 세 키를 가진 튜닝이 실제로는 U4만 돌리기 때문입니다.
  - 단계 5·6이 이 함수를 실제 설치로 바꿔야 합니다(§10-1).
  - 계획 §6.3 `[C-20]`대로 단계 4의 T1a는 **하네스 메모리 패치**(이 함수만 no-op)로 받았습니다. 어떤 config 키로도 이 거부를 끌 수 없습니다.
- 어느 시점의 트리에서도 C3 전부 아니면 전무가 성립합니다. 키 하나·둘은 결합 오류이고, 셋은 미구현 오류입니다(T2:1136).

### 2.3 계약 2단계 적재 중 1단계 (계획 §4.4-1 `[C-1]`) — HSC:120

- 확인하는 것
  - config 값이 정확히 `{path, sha256}`이고 파일 sha가 같음(표·계약)
  - 스키마 `u4-saturation-table/v1`, `shared-head-discharge-contract/v1`
  - 표의 망 sha = `snapshot_network_sha256(state)`(`check_complete_beta_runtime`과 같은 방식) = 계약의 망 핀
  - 표의 `groups_source` = config의 `shared_head_groups` 핀(같은 계약에서 유도됨)
  - 표 그룹 = 계약 행, 행마다 헤드·차로 수·`saturation_ref` 일치
  - 차로 파일 두 개 sha, `prehead_1093` 행, `lane_urban_exits`
- 읽는 것: 구성원·차로·소유자, 관측 행의 헤드 하한 구성원(흐름 구성원이면서 `phase_relation == match`이고 LUR 소유가 아닌 것), prehead 행.
- **2단계(RS:207 뒤 kind·origin·현시·β·완결성 전체 대조)는 구현하지 않았습니다.** 계획상 U5(단계 5)의 `configure_shared_head_groups` 몫입니다. T1a 하네스가 그 대조를 미리 봤습니다(§5, `contract_vs_final`).

### 2.4 차로 파일 핀 (계획 §4.1-1 `[C-8]`)

- 단계 3의 U4 표에는 차로 파일 핀이 없었습니다(계약의 `inputs`에 기록으로만 있었음). 계획은 "U4 경로는 이 두 파일을 **표에** 핀"입니다.
- 생성기에 `lane_files {internal, perimeter, use}`를 더하고 표를 다시 만들었습니다 [실행 `S4/evidence/run.log`].
  - 한 번에 하나, BELOW_NORMAL, NC 5시드 FZP 스트리밍 311 s
  - 교차 검사 `URBAN_BATCH2_EVIDENCE_CONSISTENT`, `--check` 311 s 바이트 재현
  - 새 sha `6717660981127e32…`(옛 `09462676…` 사본은 `S4/evidence/`)
- 옛 표와 비교하면 새 키는 `lane_files` 하나이고, 공통 키의 값 차이는 0입니다 [실행].
- 교차 검사기에 "표의 차로 파일 핀 = 계약의 `inputs.lanes_*` = 디스크"를 더했습니다(u4_u5 검사).
- 설치기는 핀이 없거나 sha가 다르면 실패합니다(T2:1170).

### 2.5 헤드 하한 차로 비율 콜백 (계획 §4.4-1b `[C-1]`) — HSC:341

- A:4411이 U4 뷰가 있으면 `distribute_by_u4_ratio`를, 없으면 옛 `_distribute_lane_group_capacity_to_movements`를 넘깁니다. SHO 옵션은 바꾸지 않았습니다(SHO:63).
- 구성원: 계약 관측 행의 흐름 구성원 중 그룹 현시와 같은 것(`match`)이고 LUR 소유가 아닌 것.
  - 21|p3은 `SC108_W_to_E_SC109`를 얻습니다(옛 `{internal}`에서는 구성원 0).
  - 71|p3·p4는 LUR 소유라 구성원이 없습니다(하한 없음).
  - SC7 1220008601|p1의 p2 구성원 `SC7_N_SC11_to_E_SC16`은 빠집니다.
- 배분
  - `total == S`(S = 구성원 U4 값의 계약 순서 합 = SHO:202의 base)이면 **아무것도 쓰지 않습니다.**
  - 아니면 `caps[m] = U[m] × total / S`입니다. 비율이 1보다 크면(하한 구속) 뷰에 그룹·비율을 기록합니다.
  - 멤버 탐침(total 1.0, 빈 dict; SHO·HSR·C6)은 키만 씁니다.
- 사전 확인 `check_floor_members_unchanged`(HSC:330): RS:128과 RS:145 사이 설치기가 구성원 값을 바꿨으면 실패합니다. AST 증명 시험(`test_signal_observation_window_patch`)이 이 함수 본문에 새 최상위 문장을 허용하지 않아, 헤드 관측 `if` 안에만 넣었습니다.
- LIVE [실행, 99상태 전부 같은 모양]: `install_movement_capacity_by_saturation` 1, 옛 `install_movement_capacity_by_lanes` 0, `distribute_by_u4_ratio` 106(탐침 105 + 최종 1), 옛 β 배분 0.
- 결과 [실행]: 99상태 모두 하한이 한 번도 구속하지 않았습니다(`head_floor` 0, 헤드 하한 단계에서 바뀐 값 0).
  - 이월·갱신된 하한 키는 있습니다. R-obs-b 합 updated 2,422·carried 2,520, S1 693·988, S0e 683·1,002.
  - 모두 U4 합보다 작아 `max(base, …) = base`였습니다. 계획 §C.3의 "v3b 표 값이 옛 하한보다 대부분 클 것" [추론]이 실측으로 확인됐습니다.

### 2.6 소유자 (계획 §4.4-2) — HSC:408 `record_owner_values`, :415 `verify_final`

- **게이트 peel-off**(`SC1001_W_to_onW`, `SC1001_W_to_onE`, `SC1004_W_to_onE`)
  - U4는 기본값을 씁니다(구성원이 아님, 1,850 × 차로). 곧이어 RS:134 `install_gate_onramp_queue`가 1,800으로 덮고, U4 뷰가 있으면 그 값을 소유자 기록으로 남깁니다(A:3414-3418).
  - 설치 끝에서 기록이 없거나 최종값이 기록과 다르면 실패합니다. 게이트 설치가 U4보다 먼저 돌면 기록이 생기지 않아 실패하므로 **순서가 증명**됩니다(T2:1250).
- **LUR**: 출구 10634/10635/10642의 movement와 10634 풀 구성원은 `lane_plant_service_ownership.rates_veh_h`와 같아야 합니다(T2:1269).
  - LUR 라벨 중 10635 쪽 둘(`SC1004_offE/offW_to_N_SC1003`)은 lane plant가 덮지 않아 U4 값을 유지합니다. 기록만 합니다.
- **분류** [실행, T2700]: installed 343, 게이트 3, LUR 5, 회랑 turn 5, 하한 0, **그 밖 0**. 설치 뒤 다른 설치기(회랑 병합, 경로 정리, 1083 권한)가 지운 그룹 밖 movement 15개는 따로 적었습니다(`SC108_W_to_N_SC7`·`SC108_W_to_S`는 1083 권한, 나머지 13은 SC1004·SC107 쪽).

### 2.7 `lane_group_kinds` 확장 (계획 §4.4-3, 단계 2 이월)

- A:4336-4342: C3 세 키가 모두 있으면 네 런타임 kind 전부(순서 무관)여야 합니다(HSC:111 `check_lane_group_kinds`). 없으면 예전처럼 `["internal"]`만 됩니다. 오류 문구에 지금 있는 C3 키를 적습니다.
- 시험: T2:181(옛 시험 그대로 통과), T2:208(새로: 키 하나·둘 → 거부, 셋 → 네 kind만 허용, `_LG_KINDS` 네 개).
- U4 켜짐에서 `_LG_KINDS`는 옛 β 배분 함수만 읽는데, 그 함수는 헤드·C6 경로에서 불리지 않습니다(LIVE 0). 네 kind 검사는 U4 로더가 계약 구성원 kind에 대해 다시 합니다.

### 2.8 route-choice 회랑 (계획 §4.4-4)

- RS:179-185가 `saturation=cfg.network.u4_saturation`을 넘깁니다. 키가 없으면 `None`이고, `_configure_one` 호출 모양도 옛 것과 같습니다. 5인자 함수로 패치하는 기존 fixture 시험이 있어서 이렇게 했습니다.
- 둘 다 오면 오류입니다(RCC:70, T2:1371).
- U4일 때
  - 신호 제어 incoming turn: 그 movement의 유일한 헤드 그룹 `lanes × s_g`(`turn_service_veh_h` HSC:378; 계약 차로 수 ≠ 커넥터 차로 수면 오류). 설치값과 같습니다(T2:1355).
  - 무신호 turn, 로컬 자유 출구, 분기 서비스: `lanes × 1,850`(spec의 `per_lane_capacity_veh_h` = 표 기본값)
  - 거부 두 가지(n31 회랑 4개에는 없음 [실행: 설치 99회 통과]): 상속 척도 보정 핀(`service_resource_calibration`, 옛 스칼라 척도로만 검토됨), 보정 방류가 없는 native 고정 서비스(RCC:909가 스칼라를 쓰게 됨; 분기 서비스는 RCC:896)
- 10634 풀 불변식 `service == cap`(LSS:58)은 같은 조회라 유지되고, 99설치가 통과했습니다.

### 2.9 pre-head 1093 (계획 §4.4-5)

- NIP `configure_input`(NIP:103-116)이 U4일 때 `first_head_saturation_veh_h_per_lane`을 prehead spec에 넣습니다. 첫 헤드 `30603·30604`, 2차로, `SC11_p3`가 U4 직렬 첫 헤드 행과 같아야 합니다(HSC:396).
- 예산식은 NIP:274-277과 AGG:278-281에서 같습니다: `φ × T × first_head_lanes × (s_g 또는 옛 기준 movement 용량)`.
  - 평가 순서를 옛 식과 똑같이 두었습니다. 키가 없으면 곱의 피연산자와 순서가 같고, `_phase_green_fraction`이 `_movement_capacity_flow`보다 먼저 불립니다.
  - 두 파일의 예산 대입문은 AST로 같습니다(T2:1379).
- 값 1,568.6(표 1220012001|p3 실측)이고, 옛 기준(좌회전 1차로 용량 × 2)을 대체합니다. W/N 소비 차감은 기존 규칙 그대로입니다(U5 §4.5-7은 단계 5).

### 2.10 LOR direct·local_upstream (계획 §4.4-6)

- LOR:13 `_connector_per_lane_veh_h`: U4 뷰가 없으면 `movement_capacity_veh_h`(1,400, 같은 float 객체), 있으면 표 기본값 1,850입니다. 식 `rate × lanes / 3600.`의 순서는 같습니다.
- 계획 밖이라 바꾸지 않은 1,400 사용처가 둘 있습니다: `sc2001_corridor.py:285`, `shared_approach.py:297`(§10-4).

### 2.11 결정 기록 (계획 §4.4-7·8) — HSC:494 `decision_diagnostics`, :476 `allocation_binding`

- `projection_diagnostics['u4_saturation']`(키가 있을 때만): 표·계약·차로 파일 핀, 그룹 수, 구성원·기본값 movement 수, 두 그룹 구성원, 소유자 제외 목록, 헤드 하한 비율 그룹, 설치 끝 분류, 경계 allocation 구속 수(기준 제어 + 최종 제어)
- 크기 1,756–2,008 B(결정 JSON 29–38만 B의 0.6%) [실행 B 스모크]
- 기준 제어에는 `source`를 붙입니다: `previous_action` 또는 `fixed_fallback`(§6).
- runtime 설치 메타(평면 키) `u4_saturation_*` 8개도 metadata에 남습니다. 키가 없으면 없습니다.

---

## 3. 단위 시험 [실행]

`python -B -m unittest test_n31_urban_batch2`(cwd `N31/tests`, BELOW_NORMAL, 스레드 1) → **Ran 54, OK**(단계 3의 38 + 16).

| 시험 (T2) | 계획 §5.1 항목 |
|---|---|
| `LaneGroupMembershipTests.test_kinds_widen_only_with_all_three_c3_keys` (:208) | `lane_group_kinds` ≠ internal + C3 없음 → 오류, 셋이면 네 kind, `on_ramp` 오류 |
| `…test_head_path_reads_no_legacy_key…` (:275, 갱신) | 헤드 경로가 읽는 키 = 옛 셋 + C3 존재 검사 둘(값은 안 읽음), 키 없으면 옛 배분 함수 |
| `U4InstallTests` (:1134) | C3 결합(하나·둘 → 오류, 셋 → 미구현 거부), 커밋 config 셋은 C3 키 없음; 대체 키·옛 measured 경로·kind 거부; 표 sha·`{path, sha256}` 형식·스냅숏 망·다른 계약·스키마·차로 파일 핀 없음/변조·행 누락·차로 수 불일치 실패; `cap_m = s_g × |lanes(m)|`(두 그룹 합 포함), 그룹 밖 = 1,850 × 옛 함수 차로 수(비트), 21\|p3 구성원; 구성원 부재·게이트가 구성원이면 실패 |
| `U4OwnerAndFloorTests` (:1248) | 게이트 최종 = A1 값이고 U4 값이 아님, 게이트가 U4보다 먼저면 거부(순서); LUR 출구·풀 = lane plant 값, 하나라도 U4 값이면 거부, 그 밖 변경은 기록, NaN 거부; 차로 비율: `total == base`면 쓰지 않음(같은 float 객체), 초과면 비율 하나·비례 유지·기록, 모르는 그룹 오류; 헤드 경로가 U4에서 콜백 선택, 구성원 변경 시 실패 |
| `U4LookupTests` (:1353) | 회랑 조회 = 맵 값 / 기본값, 차로 불일치·무신호 구성원·신호 비구성원 오류, 스칼라와 공존 오류; 1093 = 첫 헤드 그룹 s, 불일치 오류, NIP·AGG 같은 식; LOR = 1,400 / 1,850; 결정 기록 크기 < 8 kB, 기준 제어 source, fixed 대체 계수; 새 모듈은 함수 안에서만 import |

- 계획 §5.1 U4 행 중 "RCC 조회 값이 맵 값과 같다"는 조회 함수 수준에서 봤습니다. 실제 회랑 설치(증거·스냅숏 필요)는 T1a 99설치의 분류(`route_turn` 5, 그 밖 0)로 봤습니다.

## 4. 스위트 [실행 `S4/suites`, 대조 `S4/suite_compare_vs_run3b.json`]

- `H/run_suites.py`(단계 3과 같은 40실행)를 diff `06b20091…`에서 돌렸고, `H/compare_suites.py`로 단계 3 최종 트리(R3b)와 비교했습니다: **회귀 0, 개선 0, 사라진 실행 0.**
  - n31 167 OK(skip 3), n31_batch2 54 OK, u40_extra 11 passed(AST 증명 포함), diag11·extra_known은 이전과 같은 실패 id
  - 생성기 `--check` 15개 0
- 시험이 다시 쓴 추적 파일(`head_service_resources_canonical_validation.json` 등)은 하네스가 diff를 남기고 되돌렸습니다.
- 그 뒤 바뀐 것은 HSC의 `decision_diagnostics` 인자 하나(U4 키 경로 전용)와 T2 시험 한 개입니다(§1 중단 사유). T2 54 OK를 최종 diff `9c3fc54d…`에서 다시 받았고, **같은 40실행 스위트도 최종 diff에서 다시 돌렸습니다**(`S4/suites_final`, 17:18–17:27): R3b 대비 회귀 0·개선 0·사라진 실행 0(`S4/suite_compare_final_vs_run3b.json`), 생성기 `--check` 15/15, 끝난 뒤 `git status` 36줄(우리 변경만), 보고 직전 diff sha도 `9c3fc54d…` 그대로입니다.

---

## 5. T1a — 하네스 패치 (계획 §6.3 `[C-20]`) [실행 `R4/t1a/{robsb,s1,s0e}`, 분석 `R4/stage4_results.json`]

- 도구: `H/u4_t1a.py`
  - C3 팔 튜닝 `R4/tunings/c3_u4_arm.json`(`20387771…`): U1+U3(`f137f711`) + C3 세 키, 네 kind. U4 대체 키와 `head_resource_contract`(U5가 대체)는 뺐습니다. U6 키는 그대로입니다(코드 없음).
  - 메모리 패치는 `c3_not_implemented` 하나뿐입니다.
  - `MRS.prepare` 사본으로 어댑터 `__main__`을 돌리고, `configure_runtime` 끝(RS:185 LSS 뒤, RS:246 lane plant 뒤)에서 멈춥니다.
- 체인 `H/stage4_chain.py`: 한 번에 하나, BELOW_NORMAL, 스레드 1, `nbc_b2i`, 외부 재생은 기다리지 않고 기록만 합니다.

| 상태 집합 | 상태 | 종료 | T1a 누락 | 행 분류 (상태당) | 경계 allocation 구속 | 설명 안 되는 최종값 | 그룹 밖 무소유 변경 | 하한 구속 | 설치 시간 |
|---|---|---|---|---|---|---|---|---|---|
| R-obs-b (1, 150…9000) | 61 | 61 설치 후 정지 | **0** | ≤ n_g·s_g 114, 초과(예산 부류) 60 | **0** | 0 | 0 | 0 | 평균 10.1 s |
| S1 결정 상태 900…9000/450 | 19 | 19 | **0** | 114 / 60 | **0** | 0 | 0 | 0 | 17.0 s |
| S0e 결정 상태 | 19 | 19 | **0** | 114 / 60 | **0** | 0 | 0 | 0 | 16.8 s |

- **행 분류**
  - n_g × s_g를 넘는 60행은 모두 예산 부류입니다: budget 46, native_budget 10, 10629 대체 1, LUR 위임 2, SC7 정적 축소 1.
  - 넘는 정도는 최대 6.0배(1210009700\|p3, 1차로에 구성원 차로 6). 127\|p3 4.5, SC105·SC1(Q2) 4.0, SC7 1.5, 52\|p3 2.0입니다.
  - 넘지 않는 114행의 흐름 구성원 합은 전부 정확히 n_g × s_g입니다(비율 1.000). not_binding 54, native_not_binding 53, 흐름 없음 6, 직렬 첫 헤드 1.
  - **단계 4에서는 예산이 없으므로 이 60행은 그룹 단위로 과대 방류합니다.** 강제는 U5(단계 5)와 LUR(위임)의 몫이고, SC7 정적 축소도 단계 5입니다(계획 §7). 설치 경로의 T1a 판정은 단계 7입니다(`[C-20]`).
- **최종값 분류**(상태당): installed 343, 게이트 3, LUR 5, 회랑 turn 5, 하한 0, 그 밖 0. 설치 직후 맵 = 뷰 기록(99/99), 하한 직전 구성원 값 = 설치값(99/99).
- **계약 대 최종 설치**(단계 5 완결성 전수의 미리보기, 판정 아님)
  - 구성원 소멸 0, kind 차이 0
  - 흐름 표지와 최종 β(> 0)의 불일치 0(흐름인데 β 0, 비흐름인데 β > 0 모두 0)
  - **현시 차이 2**: `SC105_E_to_S_SC1005`, `SC1_W_to_N_SC101`. 계약은 Q2 권한(p3)으로 만들어졌고, 팔 튜닝은 U1+U3 권한(p4)입니다. Q2 β 표는 어댑터 β 원천 등록이 없어 config로 쓸 수 없습니다(STAGE3 §7-2). 후보 config에서 Q2를 연결해야 합니다(§10-2).
- 뷰 크기: pickle 41,314 B(워커로 가는 `follower.cfg`에 포함). 계약 전체 652 kB 대신 압축 형태입니다(`[C-21]`).

---

## 6. 멈춤 규칙: 경계 allocation 구속 (계획 §4.4-7, §7) — **걸리지 않음**

- 경계 kind의 방류 상한은 `min(allocation, ceiling)`입니다(UQM:752-767 [읽음]). allocation이 U4 값보다 작으면 경계에서 U4가 무력해집니다.
- **확인한 것** [실행]
  1. 기록 action 183개(R-obs-b·S1·S0e 각 61)의 `inflow_outflow_allocation`은 전부 `{}`입니다.
  2. T1a 99상태에서 이전 action(후보가 출발하는 기준 제어)의 경계 구속은 0입니다.
  3. 정적 확인 [읽음]: `evaluation/controllers`에서 allocation에 값을 쓰는 곳은 `{}` 대입(`link_predictor.py:753`, `signal_actuation_contract.py:637`)과 JSON 읽기(A:10512)뿐입니다. SDMPC 후보는 기준 제어의 녹색만 바꾼 사본입니다(`sdmpc.py:357-403`).
  4. **평가된 제어 계측**: no-control 4결정(T1·150·2700·9000)에서 `_movement_capacity_flow` 호출마다 경계 movement가 allocation에 묶였는지 셌습니다. 결정당 52,200 호출(경계 25,650) 중 **0**, allocation을 가진 제어 0입니다. SDMPC S1 3600: 부모 프로세스 52,791 호출(경계 25,887) 중 **0**. tangent 워커는 별도 프로세스라 계측하지 못했습니다. 대신 키 없는 같은 상태의 SDMPC 결정 JSON(D1)에 기록된 allocation 필드 9개(최종 제어, 후보·시퀀스)가 모두 `{}`임을 확인했습니다.
- **발견 (판단 필요할 수 있음)**
  - 이전 action 파일이 없는 첫 결정(T=1)에서 어댑터는 `previous = ControlAction.fixed(cfg)`를 만듭니다(A:10503). 이 제어의 allocation은 모든 경계 movement에 `movement_capacity_veh_h × 0.5 = 700`입니다(`vendor/.../state.py:1706-1709`).
  - U4 척도에서는 700 < 1,850 × 차로이므로, 이 제어가 평가되면 경계 movement 179개가 700에 묶입니다(옛 206.53 척도에서는 대부분 묶이지 않았습니다 [추론]).
  - 실측으로는 T=1 결정에서 이 제어가 한 번도 평가되지 않았습니다(위 4의 T1: 평가 제어의 allocation 0). no-control 결정은 `uncontrolled`(allocation `{}`)를 쓰고, SDMPC 결정은 이전 action이 있는 상태에서만 돕니다.
  - 그래서 멈춤으로 보지 않았습니다. 대신 결정 기록의 기준 제어에 `source: "fixed_fallback"`을 붙여, 이 계수가 합성 대체값임을 디스크가 말하게 했습니다(HSC:494).
  - `fixed()`를 쓰는 다른 곳: 예외 대체 A:14102(control_area에서는 예외를 다시 올림), 진단 제어기 A:12306, vendor 제어기들(n31 SDMPC 경로 밖). U4 뒤 이들이 쓰이면 경계가 700에 묶입니다(§10-3).

---

## 7. 키 없음 비트 동일 (계획 §6.1 G-ID)

- 도구: `H/u40_probe.py`(단계 1과 같은 도구, 같은 한 스텝 포착 16필드)와 `H/sdmpc_replay.py`. 체인 `R4` C1·C2·D1, 최종 diff `9c3fc54d…`, 어댑터 `411f1ead`. 비교 기준은 단계 1 b2 재생입니다(`B/impl/stage1/probe/b2_{base,u1u3}`, `…/sdmpc/b2_s1_T3600`). 단계 1 뒤 키 없는 경로를 바꾼 단계는 없습니다(C6은 키 게이트).
- 튜닝은 단계 1과 같습니다: 기본 `d4327cbf`, U1+U3 `f137f711`.

| 관문 | 상태 | `MRS compare` | 한 스텝 포착 15필드 vs 단계 1 | 설치 스냅숏 vs 단계 1 | action JSON vs 단계 1 | 장부 |
|---|---|---|---|---|---|---|
| (a) 기본 튜닝 | R-obs-b 61 | **IDENTICAL 61/61** | 15필드 × 61 모두 같음(`route_attr`는 양쪽 없음) | 용량 맵·urban_movements·`_LG_KINDS`·`_LTO`·`_SUS_*` 61/61, 설치 메타 비경로 차이 0 | 61/61에서 차이는 run_provenance(어댑터·state 사본 sha, 실행 지문)와 벽시계 3종뿐, **그 밖 0** | 최대 8.6e-9, 실패 0 |
| (b) U1+U3 튜닝 | R-obs-b 61 | **IDENTICAL 61/61** | 같음 | 같음 | 같음(그 밖 0) | 같음 |

- 계획 §6.1 (b)의 "OLD(cf3ce37) 대 b2"는 단계 1에서 받았고(비경로 차이 0/61), 이번에는 그 b2 재생과 비교했습니다(추이 관계).
- (c) SDMPC는 계획상 U4-0 뒤와 최종에만 받습니다. 이번 변경이 SDMPC 예측 경로의 코드(RCC:896 분기 서비스, NIP/AGG 예산식, LOR 배수)를 텍스트로 건드렸기 때문에 S1 3600 한 상태를 더 받았습니다.

| S1 3600 (U1+U3) | 결과 |
|---|---|
| compare 5검사 | derived·action_csv·action_controls·objective **같음**, action_contract 다름(알려진 VSL 100/110 혼재, 기록도 같은 성질, 단계 1·2·3과 같은 정의로 제외) |
| 녹색 / offset | 같음 / 같음 |
| 선택·유지 목적값 (기록 = 재생 = 단계 1) | 491.4356825691444 / 493.5432636752482 |
| tangent 2개 operations·event_counts (기록 = 재생 = 단계 1) | 12,123,157 · (7,850,416, 335,580, 630,241) / 11,962,967 · (7,778,513, 336,378, 630,972) |
| action JSON vs 단계 1 재생 | run_provenance 6, 벽시계 류, 그리고 행동이 아닌 세 부류: `frozen_context_token`·`response_token`·`request_sha256`(cfg pickle sha), **`transformed_source_sha256` 6개**(이번에 고친 A·RS·RCC·NIP·AGG·LOR의 AD 변환 소스 해시). 값 필드 차이 0 |
| adapter stdout / stderr | 499 B / 406 B |

- `transformed_source_sha256`에 HSC가 없습니다. 키가 없을 때 AD 변환기가 새 모듈을 읽지 않는다는 뜻입니다 [실행].
- **판정: G-ID (a)(b) 통과, SDMPC 한 상태 통과.** 키 없음 경로의 행동·예측·tangent 결정론 계수가 바뀌지 않았습니다.

---

## 8. U4 스모크 (전체 결정)

도구 `H/u4_t1a.py --full`(C3 팔, 같은 메모리 패치), 체인 B·D2. 목적은 U4 설치 뒤 결정 전체(투영·예측·SDMPC·출력)가 도는지와 결정 기록 확인이며, **판정 관문이 아닙니다**(C3 판정은 단계 7).

| 결정 | 제어기 | 종료 / 상태 | 예측 | 장부 최대 | U4 기록 | 기준 제어 allocation (source) | 최종 제어 | 평가 제어 경계 구속 | 결정 시간 |
|---|---|---|---|---|---|---|---|---|---|
| R-obs-b T1 | no-control | 0 / ok | ok | 6.0e-12 | 2,008 B | 179 (`fixed_fallback`) | 0 | 0 / 25,650 | 20.7 s |
| R-obs-b T150 | no-control | 0 / ok | ok | 8.6e-9 | 1,756 B | 0 (`previous_action`) | 0 | 0 / 25,650 | 21.8 s |
| R-obs-b T2700 | no-control | 0 / ok | ok | 1.8e-9 | 1,756 B | 0 | 0 | 0 / 25,650 | 25.2 s |
| R-obs-b T9000 | no-control | 0 / ok | ok | 1.8e-9 | 1,756 B | 0 | 0 | 0 / 25,650 | 21.6 s |
| S1 T3600 | SDMPC (wu-link) | 0 / ok | ok | 4.7e-9 | 1,756 B | 0 | 0 | 0 / 25,887 (부모) | 548.6 s |

- 다섯 결정 모두 설치 결과는 T1a와 같습니다(누락 0, 그 밖 0, 하한 구속 0, LIVE 1/0/106/0).
- SDMPC 결정 시간 548.6 s는 외부 재생 1개(`sim3-n31-hybrid`)와 동시였고, 하네스 계측(`_movement_capacity_flow` 감싸기)이 포함된 값입니다. 시간 관문은 단계 7 몫입니다.
- 결정 JSON 크기: no-control 29–38만 B, SDMPC 57.8 MB(키 없는 D1 57.6 MB와 같은 규모).

---

## 9. provenance와 안전 [실행]

| 트리 상태 | diff sha256 | 무엇으로 확인 |
|---|---|---|
| 단계 4 시작(= 단계 3 끝) | `0f56bd42…` | 시작 시 계산 |
| 표 재생성·첫 스위트 | `06b20091…` | 증거 ALLDONE, 스위트 provenance |
| **최종** | `9c3fc54dcde576677266c9948d72e5fbcfe3fe8a990e76510822d60e698af8c7` | 체인 R4 BEGIN = ALLDONE, 모든 T1a·스모크·G-ID·SDMPC 산출 provenance, 최종 스위트 |

- 최종 트리 파일 sha(앞 12자): HSC `2c38f9f6ecd4`, A `411f1eadf3b0`, RS `b6cec1db2934`, RCC `87c88c77695d`, NIP `43bb0c81311e`, AGG `62e9f4f0c7ea`, LOR `a4544a39326c`, U4 표 `671766098112`.
- 새 파일 0(`find -newer S4/marker_stage4_start`, 14:51): R-obs-b·S1·S0e 런 폴더, NC 5시드 폴더(`D:/VISSIM_runs/20260925_v3b`), `frozen/sdmpc31_cf3ce374_202609261037`, `frozen/sdmpc31_886a014a_202609260935`, OLD `D:/VISSIM-merge/sim3-n31-urban`. `frozen/` 최상위에도 단계 4 뒤 새 항목이 없습니다.
- OLD: `git status` 0줄, HEAD `cf3ce37`. `sim3-n31-v3c1`: HEAD `9ed2ef0`, `claude/repin-v3c1-20260928`, `git status` 0줄. 어떤 명령도 이 둘에 쓰지 않았습니다.
- W의 `__pycache__`: 없음(모든 실행 `-B`, `PYTHONDONTWRITEBYTECODE=1`). 재생 사본 폴더는 도구가 지웠고, SDMPC 재생 폴더(`R4/sdmpc/s4_s1_T3600`)는 스크래치에 남겼습니다.
- VISSIM·cscript를 시작하거나 종료하지 않았습니다. 체인 시작 때 다른 워크플로의 폐루프(VISSIM 1, cscript 1)가 돌았고, 16:39 단계 기록부터 0개였습니다(census 기록: 15:19 VISSIM 1·cscript 1 → 16:39 둘 다 0). 제가 멈춘 프로세스는 제 첫 체인 두 개(PID 8872·1860)뿐입니다.
- 재생은 한 번에 하나였습니다. 외부 재생은 기다리지 않고 기록했습니다(`CONCURRENT`: D2 한 단계). FZP 스트리밍(표 재생성·`--check`)도 한 번에 하나였습니다.
- 워치독·cscript·ps1 시험은 돌리지 않았습니다(`run_suites.py` 제외 목록). seed 37, RM 팔, 봉인 시드 59/61/67은 열지 않았습니다. 폐루프 런·커밋·push는 없습니다.

---

## 10. 다음 단계로 넘기는 것 / 사용자 판단

1. **C3 미구현 거부 해제(단계 5·6)**: HSC:62 `c3_not_implemented`는 단계 5(U5)·6(U6) 설치로 대체해야 합니다. 그 전에는 C3 세 키를 가진 어떤 config도 설치에서 멈춥니다(의도). 계약 2단계 적재의 2단계(RS:207 뒤 전체 대조)도 단계 5입니다.
2. **Q2 연결(단계 5 또는 9)**: 계약은 Q2 권한(SC105·SC1 공유 좌회전 p3)으로 만들어졌습니다. 후보 config는 `urban.movements.physical_phase_authority` = Q2 파일, `urban.beta` = Q2 표를 써야 하고, 그러려면 어댑터 `BETA_EVIDENCE_JSON`(A:4005)과 `beta_source.COMPLETE_BETA_SOURCES`(beta_source.py:40)에 원천 이름이 필요합니다. 연결하지 않으면 단계 5 전체 대조가 두 movement의 현시 차이로 실패합니다(§5). U4 값 자체는 현시와 무관합니다.
3. **`ControlAction.fixed`의 700 allocation**(§6): U4 뒤에는 `fixed` 제어를 평가하는 경로가 경계를 700에 묶습니다. n31 SDMPC·no-control 경로에서는 평가되지 않음을 확인했습니다. C3 폐루프(v3c1) 전에 `fixed` 대체 경로를 막을지(예: U4일 때 allocation 비움), 계측으로 지켜볼지는 판단이 필요합니다. 단계 7 LIVE에서 `evaluated_allocation` 계측을 SDMPC 결정 여러 개로 다시 보는 것을 권합니다.
4. **계획 밖 1,400 사용처**: `sc2001_corridor.py:285`(`sat = movement_capacity_veh_h`), `shared_approach.py:297`(분기 서비스 `movement_capacity_veh_h × lanes`). 계획 §4.4는 LOR만 바꾸라고 했으므로 두지 않았습니다. U4 척도와 맞출지 단계 7 관문 전에 정하는 편이 좋습니다.
5. **예산 없는 과대 60행**: 단계 4 상태(하네스 팔)에서는 60행이 n_g × s_g를 넘습니다(최대 6배). U5가 강제하기 전에는 C3 판정을 하지 않습니다(계획대로).
6. **헤드 하한**: v3b 99상태에서 구속 0입니다. 콜백은 동작하지만(LIVE 106/상태) 값이 바뀐 적은 없습니다. 구속이 생기는 경우는 단위 시험으로만 확인됐습니다.
7. **이월(그대로)**: C6 키 1.0/8/3/3을 후보 config에(단계 9), C6 경계 경보(206.53 표지)가 U4 뒤 줄어드는지는 단계 7 보조 지표, v3c1 재유도 시 생성기 상수 인자화(차로 파일 포함), 동결 전 `__pycache__` 삭제(현재 없음).

## 부록: 산출 파일

- 보고서: `B/impl/STAGE4.md`
- 증거 재생성: `S4/evidence_run.sh`, `S4/evidence/run.log`, `S4/evidence/logs/`, 옛 표 사본 `S4/evidence/head_saturation_v3b_20260929.stage3_09462676.json`
- 줄바꿈 복구: `S4/fix_eol.py`
- 스위트: `S4/suites/tests/`, `S4/suite_compare_vs_run3b.json`
- 체인: `S4/launch_chain4.cmd`(WMI 분리 발사), `R4/chain.log`, `R4/logs/`, T1a `R4/t1a/{robsb,s1,s0e,robsb_full,s1_full}/`, 팔 튜닝 `R4/tunings/c3_u4_arm.json`, G-ID `R4/probe/{s4_base,s4_u1u3}/`, SDMPC `R4/sdmpc/`, 분석 `R4/stage4_results.json`
- 중단된 첫 체인: `S4/run4_aborted_1/`(판정에 안 씀), 개발 실행 `S4/dev/`
- 하네스(새로): `H/u4_t1a.py`, `H/stage4_chain.py`, `H/stage4_analyze.py`
- 트리 새 파일: HSC. 수정: A, RS, RCC, NIP, AGG, LOR, T2, `scripts/derive_head_saturation.py`, `scripts/check_urban_batch2_evidence.py`, U4 표
