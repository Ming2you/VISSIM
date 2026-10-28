# PRE_FO — FO 사전 선언: 설정 차이·동결·사전 점검·T=900 관문·발사기·런 점검·비교 규칙·멈춤 규칙 (2026-10-27 KST, FO 데이터 전 고정)

- 이 문서는 **FO 데이터가 하나도 없을 때** 씁니다(FO 결정 재생 0, FO VISSIM 런 0). sha256 을 `SP/codex_handoff/fo/LOG.md` 에 적어 고정하고, 고정 뒤에는 고치지 않습니다. 쓰인 대로 할 수 없거나 관문·점검이 FAIL/HOLD 이면 **멈추고 보고**하며, 다음 걸음은 사용자가 정합니다.
- 판정 낱말은 쓰지 않습니다. Ω701 은 늘 ④·Ω 밖과 함께, ④b 는 첫 관측 차분이 주 값, 도시도로는 codex 분할만, FW_E 가 주 목표·FW_W 는 감시, 신호·미터 녹색은 GREEN 초만 셉니다. 시드는 v3c3-s31·s41·s43 (provenance 의 시드).
- 표시: **[실행]** 명령으로 확인 · **[읽음]** 파일을 읽어 확인 · **[추론]** 시험하지 않은 판단 · **[계산]** 산술.
- SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`, FO = `SP/codex_handoff/fo`, FW = `FO/work`, CW = `SP/codex_handoff/work`. 증거는 이름 + sha256 으로 적습니다.

## 0. 쉬운 요약

1. [실행] **FRZ_FO 를 만들었습니다**: FRZ_B1 의 원천 + codex solo 판 17파일(바이트 그대로) + FO 설정 1개. FREEZE.json `d7fa4db6…`, 파일 7,994개(FRZ_B1 + 5), FREEZE_VERIFIED 두 번.
2. [실행] **FO 설정은 B 설정에 키 하나만 더한 것**입니다: `adapter.sdmpc_actuator_scope = {mode: freeway_only, baseline: v3c3 무제어 명령 값}`. `sdmpc_information_scope` 는 넣지 않았고, 고속 경로·목적함수·예측기·VSL 110 고정은 B 그대로입니다. 설정 sha `80e0abef…`.
3. [실행] **러너 사전 점검 4개 통과**(s31·s41·s43 FO 설정, s31b B 설정 = 관문 대조용). B1 사전 점검과 다른 잎은 선언한 것뿐입니다.
4. **T=900 관문**(다음 걸음에서 돌림): B 기록 상태 3시드에서 FO 설정 첫 결정 재생 R1–R3 + B 설정 대조 재생 R0, 그리고 도시 SG 쓰기 대 native 프로그램 대조 G2. 하나라도 통과 못 하면 런을 띄우지 않고 멈춥니다.
5. [실행] **발사기**는 B 발사기를 이름만 바꾼 사본 + 선언한 덧붙임(PRE_FO·규칙·핀·관문 sha 를 고정 목록에 넣고, 관문 pass 가 아니면 띄우지 않음)입니다. 모의 실행 17/17, 멈춤 도구 모의 실행 7/7 통과. VISSIM 발사 0.
6. 비교 규칙은 `COMPARE_RULE_FO.md`(`d5a47e8d…`): 짝 FO − NC3·B − FO·FO − V-A, 줄은 B 와 같고, FW_E 분해 칸 RF1–RF11·DA1–DA4 를 FW_E 도구 그대로 냅니다(자기 시험 102/102).

## 1. 근거 결정

- D-K9-112 (`SP/K9_1_J1_NOTES_20261013.md` :380): codex SDMPC 고속도로만 팔 FO, s31·s41·s43, B 와 다른 것은 도시 제어 끔 하나, VSL 110 고정, B − FO = 도시 제어 몫, FO − NC3 = 고속도로 제어 몫.
- D-K9-113 (같은 파일 :382-387): **O2 = 작동기만 고속도로.** FRZ_FO = FRZ_B1 + solo 17파일, `sdmpc_actuator_scope` 만 켬, information_scope 끔, 고속 경로 B 와 같게, VSL 110. codex 실행 기록 0회 조합이라 T=900 관문 먼저, COM 재기록 baseline 대 native 활성 프로그램(GREEN 만) 대조, 다르면 멈춤.
- [실행] 노트 sha: D-K9-113 이 적힌 직후 `1bb1b1ef3b6897fd49ce7ca8c283cfec3e7f6555c9c5ee15488448638068d69b`(이 단계 첫 읽기). 19:31 에 다른 줄기가 D-K9-114(C1 가드, FO 와 무관)를 덧붙여 지금은 `bfd3fc2bc8f9feab76806245171b948467444fa20fe4f261ed58d7c7549e6419` 입니다. D-K9-113 줄은 바뀌지 않았습니다.
- 사실 단계: `FO/FACTS_FO.md` `8f379cc73be25509cdd2241a3c8edb6c46e888867b94cd4b4c8c7a49daf72447`.

## 2. FO 설정 차이 (FRZ_B1 의 B 설정 대비, 정확한 키·값)

| 항목 | B (`diagnostics/b0_v3c3/config_b0_v3c3.json`, `729640af…`) | FO (`diagnostics/b0_v3c3/config_fo_v3c3.json`, `80e0abefdb25526374c97d8f7a6b45b9ad434db1f3499cec208985038ac249f3`) |
|---|---|---|
| `/adapter/sdmpc_actuator_scope` | 없음 | `{"mode": "freeway_only", "baseline": {"green_times": {SC1_p1 54.0, … 68개}, "offsets": {SC1 19.0, … 17개}}}` (codex freeway_only 설정 `cd193948…` 의 같은 값을 깊은 복사) |
| 그 밖의 모든 잎 | — | B 와 같음 [실행 잎 대조: 다른 잎 = 위 키 아래 86잎뿐, 빠진 잎 0, 바뀐 잎 0] |
| `/adapter/sdmpc_information_scope` | 없음 | **없음** (D-K9-113) |
| `/adapter/sdmpc_fixed_vsl` | `{start_sec 0, base_kmh 110, zone_kmh {}}` | 같음 → **VSL 110 고정, B 와 같음** |
| 고속 경로 키 18개(`sdmpc_fast_primitives` 등) | B 값 | 같음 (codex FO 는 18칸을 껐음; FO 는 끄지 않음) |
| `/name`, `/description` | `native348_FW5_U10_optimized_b0v3c3` | 같음 |

- [실행] baseline = B 3시드(provenance 시드 31·41·43)의 무제어 명령 t=1·t=750 의 green_times·offsets 와 **차 0**(6개 모두).
- [실행] 직렬화: B 설정 바이트를 그대로 재현하는 방식(json indent 2, ensure_ascii False, CRLF, 끝 CRLF)으로 키 하나를 adapter 끝에 더함. 새 경로 글자 0.
- codex freeway_only 팔과 다른 점(밝힘): codex 는 information_scope 도 켰고(목적 소유자 FW_W·FW_E, 실험 지역 예측기, NP 끔, 고속 경로 18칸 끔), VSL 을 최적화했습니다(100·90 선택). FO 는 둘 다 하지 않습니다.

## 3. 코드: FRZ_FO = FRZ_B1 + solo 17파일 [실행]

- 원천 `D:/VISSIM-merge/k8_gate_trees/codexhandoff/fo/source` = 새 git 저장소에 `b1/source` HEAD(a49981ff) fetch·detached + robocopy. 덮기 전 파일표 = FRZ_B1 FREEZE 와 0 차이(7,989).
- 덮은 파일(모두 `evaluation/controllers/`, 인계 사본 `HO/original_code_dependencies/solo` 바이트, solo FREEZE `f55ecec3…` 의 sha 와 같음; 고친 13개는 덮기 전 = joint FREEZE `f980fcce…` = FRZ_B1): `area_follower_objective, joint_owner_neighbors, runtime_setup, sdmpc, sdmpc_budget, sdmpc_central, sdmpc_pfo, sdmpc_sequence, sdmpc_tangent, sdmpc_tangent_constraints, sdmpc_tangent_surrogate, sdmpc_tangent_worker, vissim_stackelberg_adapter` + 새 `sdmpc_actuator_scope, sdmpc_regional_context, sdmpc_regional_contracts, sdmpc_regional_prototype`. 기록 `FW/build/overlay_record.json` `7de8f540…`, 차분 `FW/build/frzb1_to_fo_13files.diff` `643115b3…`(Facts 차분과 같은 줄).
- 덮지 않은 것: B0/B1 고침 7파일(F1·F2·F3·H1·H2·H3·러너 N1+B1)은 FRZ_B1 그대로. 러너 `6ff68b38…`(StallSec 3,600, 4자리 상한) 그대로.
- [읽음 solo 코드] 키가 없으면 새 갈래는 모두 막혀 B 와 같은 길입니다(`regional`·`actuator_scope` 로 막힘). 키가 있고 information_scope 가 없으면(O2): 좌표에서 신호 green·offset 축과 VSL 축을 빼고(`sdmpc.py:418-462`), 미터 축만 남음; 목적 소유자는 Ω701 19개 그대로(:343 은 regional 일 때만 바뀜); 축 없는 소유자는 QP 를 건너뜀(:1210); 결정·3블록 계획의 green·offset 이 baseline 과 1e-9 안에서 같지 않으면 `ValueError('Inactive urban actuator changed')`(`sdmpc_actuator_scope.check`, `sdmpc.py:557`·`:931`, `sdmpc_sequence.py:195`); 예측기·NP·고속 경로는 B 그대로.
- **B 와 달라질 것으로 선언하는 표지(관문 A8·런 점검 V7 이 대조)**:
  - M1 `metadata.sdmpc_state.policy_sha256` ≠ B 기록 값(`848d55d3…`): 정책 옵션에 `actuator_scope` 가 들어감(`sdmpc.py:807-814` `policy_token`). 세 시드에서 같은 값.
  - M2 `joint_leader_selection.policy` = B 기록 정책 + 키 `actuator_scope` 하나(값 = FO 설정 값), 그 밖의 정책 값 같음.
  - M3 `joint_leader_selection.coordinates` 의 종류 = {meter} 뿐, 개수 = B 기록의 meter 좌표 수(24 = 미터 8 × 3블록), green·offset 0개.
  - M4 명령 CSV 의 signal 17행·JSON green_times/offsets = baseline 그대로; VSL 66행 = 110.
  - M5 t=1 무제어 결정의 `metadata.prediction_runtime_unavailable_reason` 글자 = solo `runtime_setup.py:333` 글자(모드와 무관하게 바뀜). 런 점검 V7 에서 보고.
  - M6 지역 표지 없음: `regional_context, regional_prediction_blocks, regional_boundary, regional_mode, active_cost_owners, input_isolation_qualified, input_context_schema, regional_startup_baseline, active_resources, active_resource, region, regional_prediction_prototype, regional_context_required` 가 명령 JSON 어디에도 없음.
  - 그 밖의 메타데이터 키 차이(예: 상태에 따라 이름이 바뀌는 `head_*` 키)는 보고만 합니다(같은 B 설정끼리도 상태가 다르면 수백 개가 달랐음 [실행: 관문 1 재생 대 B 기록]).
  - 정책 토큰과 표지가 다르므로, FO 결정이 B 의 가격 문맥을 이어 받는 일은 없습니다(FO 런은 처음부터 FO 정책).

## 4. 동결 FRZ_FO·사전 점검·짝 점검 [실행]

| 항목 | 값 |
|---|---|
| 경로 | `D:/VISSIM-merge/k8_gate_trees/codexhandoff/fo/frozen/sdmpc31_a49981ff_202610271954` |
| FREEZE.json sha256 | `d7fa4db6c3ca854a3c6c7dfd352f97626d6f9ca9d0e5ea6f18e36fc779d37373` |
| 파일 / 바이트 / tree sha | 7,994 / 495,975,719 / `8994da3eecb8ad21909e2440e62564b0c4c023dcad27a7a381626ab2c3f997fd` |
| git head · status 줄 | a49981ff · 3,671 (`11dab851…`) |
| FRZ_B1 대비 | 바뀜 13 + 더함 5(새 모듈 4 + FO 설정), 빠짐 0 (`FW/build/diff_frzfo_vs_frzb1.json` `68d10950…`) |
| 동결 도구 | codex `tools/sdmpc31/freeze_worktree.ps1`(FRZ_B1 의 것과 같은 바이트 `2f8ff1ea…`) → FREEZE_OK, 113.9 s |
| 검증 | FREEZE_VERIFIED 사전 점검 앞·뒤 |
| 손대지 않음 | `D:/VISSIM-merge/frozen/*`, FRZ_B0·FRZ_B1·V-A·K92 동결 트리, GWT8 `D:/VISSIM-merge/sim3-n31-k8`, codex 작업 트리 a49981ff |

러너 사전 점검(`-PreflightOnly`, VISSIM 0, codex pwsh 7, env_hsw + PYTHONHASHSEED=0 + RW_* 지움; 도구 `FW/build/fo_preflight_wrapper.ps1`):

| 라벨 | 설정 | 종료 · 벽시계 | provenance sha256 | 검사 19개 |
|---|---|---|---|---|
| s31 | FO | 0 · 14.7 s | `dea0ba5e3eb52a942e6c5e558b0afe370e421079a214f222951e1553c4de3d28` | 모두 참 |
| s41 | FO | 0 · 14.1 s | `51766b3be0c0bec7d2ba571d8ef84b21d9d090e7a832bdd5b58f8c72e5d9a394` | 모두 참 |
| s43 | FO | 0 · 14.9 s | `c640c095f17eebffff82c7f6146ab0aa08eb874e9285c2edca5caad9f7dc210a` | 모두 참 |
| s31b | B (R0 입력 전용) | 0 · 14.5 s | `d5a724f8b82a8efff9015fd995c19e3493b0afe6bea2cc393a39a6b0739d1c82` | 모두 참 |

- 검사: 종료 0, FREEZE_VERIFIED(FRZ_FO sha), 망 `3de889f0…`(러너가 만든 준비 폴더의 망 사본 `<결과 뿌리>/sdmpc/network/sdmpc31_sdmpc9000_s<s>.inpx` 의 sha), 유지 env(hold_previous_on_exception·1·0), 설정 sha·RW_SIGNAL_OBSERVATION_CONFIG_SHA256 = 그 설정, freeze 핀 = FRZ_FO, plant manifest `11842498…`, 검지표 `108debbb…`·294행, wu-link, 시드, 9,000 s, 작업 뿌리 FRZ_FO, 빈 RW 값은 RW_OBS150_GT 뿐, StallSec 3600(워치독 명령줄·러너 상태 인자), preflight_complete, **B1 사전 점검과 잎 대조**: 다른 잎 = created_at, run_id, freeze sha, (FO 설정만) 설정 경로·sha 7잎(RW 설정 sha, files/tuning 경로·sha, 두 config_chain 의 경로·sha), files/adapter/sha256; controller_sources 는 solo 17파일만 다름.
- 짝 점검(시드는 provenance·run.json 에서 읽음, 폴더 이름에서 읽지 않음): NC3 prepared/run 시드 일치·완주, NC3 망 sha = 기록된 원천 sha(s31 `3de889f0…`, s41 `726af589…`, s43 `51478c39…`), B·V-A 시드·망 `3de889f0…`, B 완주, `.sig` 42개가 FRZ_FO·NC3·B·V-A 9곳에서 바이트 같음, FO 결과 뿌리 없음.
- 요약 `FW/build/fo_summary.json` `0c6b3d00767a29ac4c7871489a2962cc96911c11d8cfb154d00377a9047d40df` (FO_BUILD_PASS true), 사슬 기록 `FW/build/chain_fo.state.txt`.

## 5. T=900 관문 (GATE1_RULE 꼴; 다음 걸음에서 돌림, 결과 전 고정)

### 5.1 재생 넷

| ID | 입력 상태 | 설정 | provenance |
|---|---|---|---|
| R1 | B v3c3-s31 기록 `state_000900.json` + 직전 `action_000750.json`(무제어, sdmpc_state 없음, `.applied` 없음) | FO | 사전 점검 s31 |
| R2 | B v3c3-s41 같은 꼴 | FO | s41 |
| R3 | B v3c3-s43 같은 꼴 | FO | s43 |
| R0 (대조) | B v3c3-s31 (R1 과 같은 상태) | B | s31b |

- 왜 B 기록 상태인가 [추론]: FO 는 900 s 전까지 B 와 같은 러너·같은 무제어 결정(같은 바이트 명령)을 하므로, FO 의 T=900 상태는 B 의 것과 같을 것입니다(런 점검 V6·V7 이 사후 확인).
- 도구: 입력 `FW/gate/fog_build_inputs.py`(관문 1 의 `g1_build_inputs.py` 에서 원천을 B 런으로, 위치 바꾸기를 B 런 폴더·FRZ_B1 → 관문 폴더·FRZ_FO 로), 재생 `FW/gate/fog_replay.ps1`(관문 1 의 `g1_replay.ps1` 에서 코드 뿌리 FRZ_FO, 우선순위 BELOW_NORMAL, 수집 출력 UTF-8), 큐 `FW/gate/fog_queue.ps1`, 요약 `FW/gate/fog_summary.py`, SG 대조 `FW/gate/fog_sg_native.py`, 발사 `FW/build/fo_launch_wmi.ps1`(WMI, BELOW_NORMAL, 한 번만). 어댑터 인자는 관문 1·B 와 같음.
- 차례: FRZ_FO FREEZE sha·verify → 입력 넷 → 재생 R1·R2·R3·R0(하나씩, 재생마다 공용 잠금 `heavy.lock` 배타 생성·30 s 재시도·60 분 못 잡으면 멈춤·내 토큰만 지움·놓은 뒤 25 s 쉼; 7,200 s 상한 넘으면 내 프로세스 나무만 멈추고 stopped_cap) → FRZ_FO verify → G2(R1–R3) → 요약.
- 환경: env_hsw, PYTHONHASHSEED=0, `python -B`, 스레드 1, RW_* = 입력 provenance 의 비지 않은 값(설정 sha 일치 검사).
- 다음 걸음의 시작 명령(이 문서에 고정): `powershell -NoProfile -ExecutionPolicy Bypass -File FW/build/fo_launch_wmi.ps1 -Script FW/gate/fog_queue.ps1 -StateName queue_fog.state.txt -ArgString "-Frz D:\VISSIM-merge\k8_gate_trees\codexhandoff\fo\frozen\sdmpc31_a49981ff_202610271954 -FrzSha d7fa4db6c3ca854a3c6c7dfd352f97626d6f9ca9d0e5ea6f18e36fc779d37373"`.

### 5.2 통과 조건 (`fog_summary.py`; 하나라도 거짓이면 관문 FAIL → 런을 띄우지 않고 멈춤·보고)

- R1–R3 각각: A1 종료 0 · A2 예외 0(`Traceback`·`DECISION_FAILED`·`action_000900*.error*` 없음) · A3 결정 끝남(json·csv, `output_completed` true) · **A4 결정 벽시계 ≤ 1,500 s**(래퍼 스톱워치와 budget wall_sec 중 큰 값) · **A5 도시 신호는 baseline 만**(JSON green 68·offset 17 차 0, CSV signal 17행 차 ≤ 1e-9, signal_sg 의 SC 는 17곳 안) · **A6 미터를 SDMPC 가 정함**(controller_status ok, sdmpc_active, sdmpc_state 있음, ramp_meter 8행, 좌표 = meter 뿐·개수 B 와 같음) · A7 VSL 66행·JSON 모두 110 · **A8 표지가 선언대로만 다름**(§3 M1·M2·M6, sdmpc_state 키 집합 = B).
- 세 FO 재생의 policy_sha256 이 서로 같음.
- R0: 종료 0·예외 0·끝남, **C4 policy_sha256 과 정책 = B 기록**, **C5 action_000900.csv 바이트 = B 기록**(다르면 HOLD: solo 덮기 또는 재생 경로가 B 를 그대로 재현하지 못함 → B − FO 해석에 섞임이 생길 수 있어 멈춤).
- FRZ_FO FREEZE_VERIFIED 재생 앞·뒤.
- **G2 (도시 SG 쓰기 대 native, GREEN 만)**: R1–R3 의 signal_sg 행을 VBS 규칙(SG 상태 = (t + offset) mod 주기가 창 안이면 GREEN, 창 없는 SG 는 적색; 관측 프레임 t 는 명령 시계 t−1, `OBS150_FRAME_ADVANCE` 1)으로 펼친 GREEN 프레임이, 같은 시드 B 런 `.lsa` 의 900 s 전 native 프로그램 GREEN 프레임(프레임 2–899)과 **쓰는 SG 136개 모두에서 0 프레임 차**, SC 주기 17곳 모두 같음, 쓰는 SG 집합 = 계획 기대 집합(창 있음 122 + 적색 전용 14; native 전용 24 = SC5 9–24·SC7 9–16 은 쓰지 않음). **다르면 멈추고 보고**(D-K9-113).
- 결정 벽시계 최대는 StallSec 3,600 s 여유로 따로 적습니다(B 런은 이 PC 중앙 448–469 s).

### 5.3 이 관문을 믿는 근거 (자기 시험, 모두 FO 데이터 아님) [실행]

- G2 도구 양성 대조(codex 64cf-s29 freeway_only 런, 인계 사본): 명령 규칙 대 LDP(1,050–8,099 s) 136 SG 0 프레임 차, `.lsa` 대 LDP(2–899 s) 0, 64cf 판 G2(baseline 행 대 native `.lsa`) 0, readback 규칙(V4c) 대 native(901–8,100 s) 0. 음성 대조(B T=900 최적 계획 대 native): 3시드 모두 122 SG 다름(16,968 / 30,935 / 38,079 프레임). 결과 `FW/gate/selftest/sg64.json`, `sg64_run.json`, `negb_s*.json`, `g2_shape_on_b_s31.json` (sha256 은 PINS_FO).
- [실행] v3c3 native `.lsa` 의 프로그램 위상(cycletime − simtime)이 17곳 모두 baseline offset 과 같습니다(SC1 19, SC5 114, SC6 13, SC7 119(주기 120), …, SC1001–1005 75). 그래도 G2 판정은 FO 재생 행으로만 합니다.
- 요약 도구 자기 시험(재생 칸에 B 기록을 넣음): R1–R3 은 A5·A6·A8 거짓(B 는 신호를 최적화함), R0 은 C4·C5 참 — 도구가 둘을 가름(`fog_summary_selftest.json`).
- 입력 도구 자기 시험(다른 뿌리 `FW/gate/selftest/g_root2`): 4라벨 각 95파일, 위치 못 바꾼 경로 0, provenance 의 설정 sha(FO `80e0abef`, R0 `729640af`)·freeze 핀 `d7fa4db6`·run_id(B 기록) 맞음. 첫 시도(`g_root`)에서 80자 자르기 때문에 정상 경로를 "못 바꿈" 으로 잘못 세는 결함을 찾아 고친 뒤의 판입니다(고침 = 앞머리 비교를 양방향으로).

## 6. 발사기 (B 발사기의 이름만 바꾼 사본 + 선언한 덧붙임)

| 파일 (FO 아래) | sha256 | 원본 (B) |
|---|---|---|
| `fo_launcher.ps1` | `e73990d0da6dac7603be9959acca063cacbc0b3f033b8cf0336d351c31ffd02b` | `b_launcher.ps1` `cb657ecb…` |
| `fo_wrapper.ps1` | `b79f38ac97336ed944e431c2fb43d23a7665851ce0c4a49456b6643f2038b019` | `b_wrapper_b1.ps1` `93814842…` |
| `fo_status.ps1` | `9b4e35be2e72cd186fcf3b82b33960537d4b558e9ed8ace86a1f80aceacae755` | `b_status.ps1` `f07a8f6b…` |
| `fo_launcher_start.ps1` | `b9994d2ca7c56789df710aec5d558ae77ace17b52d54f47106af82621fd895f8` | `b_launcher_start.ps1` `9c818f1f…` |
| `fo_launcher_dryrun.ps1` | `564dfbc33146255c8e27f1a6d8cc06ba7d6794c0d781b8b14525e913f43b6009` | `b_launcher_dryrun.ps1` `fa5652b5…` |
| `fo_stall_stop.ps1` (새) | `961bc521d761e4cd797f406f3af1481d91c476216c1f562baa61629378e39eae` | — (PRE_B_CONCURRENT §7 의 손 절차를 도구로) |
| `fo_stall_dryrun.ps1` (새) | `c0f82e44250c4f1c9f39d516d92a1664d66765fae2b57894972a4953164cd00b` | — |

- 생성 `FW/run/make_launcher_fo.py`, 전체 차분 `FW/run/launcher_b_to_fo.diff`. 이름 바꿈: B 폴더 → FO 폴더, 결과 뿌리 `20261026_codex_b_v3c3` → `20261028_codex_fo_v3c3`, FRZ_B1 → FRZ_FO, B 설정 → FO 설정, `b_wrapper_b1/b_launcher*/b_launch/STOP_B_LAUNCHER` → `fo_*`, 머리 낱말. 모든 파일 ASCII, PowerShell 구문 오류 0, 대소문자만 다른 변수 0 [실행]. (짓기 단계의 사전 점검 래퍼에만 `$FRZ`/`$Frz` 가 있는데, B1 래퍼에서 이어받은 것으로 같은 값을 다시 넣는 줄입니다.) 이 검사로 모의 실행 도구·관문 재생·분석 실행기에서 대소문자 충돌 셋(`$out/$OUT`, `$code/$CODE`, `$s/$S`)을 찾아 고친 뒤 sha 를 냈습니다.
- **덧붙임**: 발사기 인자 `-PreSha -RuleSha -PinsSha -GateSha`(64 hex, run 모드에서 파일은 FO 의 정해진 경로) → 네 파일이 매 발사 전 sha 고정 목록(FIXED)에 들어감; 시작 때 관문 요약 `FW/gate/fog_summary.json` 의 `pass` 가 true 가 아니면 `LAUNCH_STOPPED GATE_NOT_PASSED`; FIXED 의 B 항목을 FO 항목(FREEZE `d7fa4db6`, FO 설정 `80e0abef`, 래퍼)으로 바꿈. 시작 스크립트도 네 sha 와 관문 pass 를 확인하고 넘김.
- 정책(PRE_B_CONCURRENT §5–§7 그대로): 세션과 떨어진 WMI 발사, 시드마다 한 번(재발사는 정책에 따른 한 번뿐), 차례 s31 → s41 → s43, 우리 FO 런 동시 최대 3, **PC 전체 VISSIM < 4 일 때만 발사**(남의 것 포함, 잠금 아래 두 번 셈 + 러너 자체 검사), 남의 VISSIM 은 절대 손대지 않음·이름으로 끄지 않음, 자리 기다림 12 h, 디스크 C ≥ 8 GB·D ≥ 8 GB × (활성 + 1), 이상 종료 하나면 남은 시드 발사 멈춤, 우선순위 Normal(B 와 같음), 결과 뿌리 `D:/VISSIM_runs/20261028_codex_fo_v3c3/s<seed>`.
- 멈춤·한 번 재발사(사용자 정책): 정상 최대 간격 199 s + 5 분 = **499 s** 넘게 진행 신호가 없으면 `fo_stall_stop.ps1 -Action check` 로 그 런 프로세스 나무(래퍼 PID + 생성 시각, 그 자손, 워치독이 적은 VISSIM PID + 생성 시각)의 CPU 를 120 s 간격으로 두 번 잼 → 1 s 넘게 늘면 "느리지만 진행" → 아니면 `-Action stop`: 기록(`_launcher/stalled_s<seed>_run1.json`) → **그 PID 들만** 멈춤 → `s<seed>` → `s<seed>_try1_stalled` 이름 바꿈 → 발사기가 같은 자리 규칙으로 run2 를 한 번 띄움. run2 가 또 멈추면 기록만 하고 발사기는 이상 종료로 멈춤.
- [실행] 모의 실행(VISSIM 0, WMI 0, 프로세스 시작 0): 발사기 17/17 (B 의 15 상황 + M 관문 pass 아님 → 발사 0·GATE_NOT_PASSED, N PRE 파일이 바뀜 → s31 뒤 SHA_MISMATCH), 기록 `FO/fo_launcher_dryrun.log`, 실제 뿌리 없음 앞·뒤, 남의 VISSIM [30964, 31656] 앞·뒤 같음. 멈춤 도구 7/7 (진행 중, 느리지만 진행, 확인만, run1 멈춤 + 이름 바꿈, run2 멈춤·이름 그대로, 두 번째 멈춤 거부, 이미 끝난 시도) — 가짜 입력이라 실제 프로세스 0, 기록 `FO/fo_stall_dryrun.log`.
- 시작 명령(관문 통과 뒤, 사용자 발사 허락 뒤): `powershell -NoProfile -ExecutionPolicy Bypass -File FO/fo_launcher_start.ps1 -LauncherSha e73990d0… -WrapperSha b79f38ac… -PreSha <이 문서 sha> -RuleSha d5a47e8d… -PinsSha 5458c623… -GateSha <관문 요약 sha>` (64자 전체로).

## 7. 런 점검 V1–V8 (`FW/ana/fo_run_check.py`, 시드마다, 런 끝난 뒤)

| 칸 | 내용 | 거짓일 때 |
|---|---|---|
| V1 완주 | 래퍼 runner_exit 0, `STAGE=SIM_DONE`, `SIM_SEC=9000`, `DECISIONS_FAILED=0`, `action_*.error.txt` 0 | 그 시드 칸 "못 냄" (이상 종료면 발사기가 남은 시드를 멈춤) |
| V2 provenance | 시드, 망 `3de889f0…`, 설정 sha = FO, RW 설정 sha = FO, freeze 핀 = FRZ_FO, 유지 env | **멈춤** |
| V3 미터 명령대로 | readback 요청 = 읽음, ok 1; 미터 8 × 810 주기 readback GREEN 초 = 그 결정의 명령 녹색 (어긋남 0) | **멈춤** |
| V4 도시 신호 baseline 만 | (a) T ≥ 900 signal 행 = baseline, (b) signal_sg 일정이 모든 결정에서 하나, (c) readback 으로 실현된 도시 SG GREEN 프레임 [901, 9000] = native 프로그램(같은 시드 B `.lsa` 의 900 s 전 구간을 주기로 늘림) 0 프레임 차 | **멈춤** |
| V5 VSL 110 | 명령 CSV VSL = 110 뿐, vsl_readback 요청·읽음 110, ok 1 | **멈춤** |
| V6 900 s 전 접두 | FO 의 `lf_sha_le_895_1` = B 같은 시드; NC3 대비는 COMPARE_RULE_FO §1 의 † 규칙 | 보고(B 와 다르면 † 와 함께 따로 보고) |
| V7 워밍업 | t=1–750 명령 CSV 바이트 = B; t=1 메시지 글자 = solo 글자 | 보고 |
| V8 벽시계 | 결정 벽시계 n·평균·중앙·최대·> 1,500·> 3,600 | 보고 |

- "도시 SG 를 제어기가 쓰지 않음" 의 뜻: FO 는 900 s 부터 150 s 마다 baseline 계획을 COM 으로 다시 씁니다(codex freeway_only 와 같음). V4 는 그 쓰기가 **제어기가 고른 값이 아니라 baseline 이고, 그 GREEN 초가 native 와 같음**을 봅니다 [읽음 FACTS_FO §2.5].
- [실행] 자기 시험(B 런에 돌림): V1·V3·V5 참, V2 거짓(B 설정·FRZ_B1), V4 거짓(B 는 최적 계획; readback 대 native 122 SG 다름) — 도구가 가름. 미터 readback 은 B 에서도 810 × 8 주기 어긋남 0 (VERIFY_B D5 와 같음).

## 8. 비교 규칙

- `FO/COMPARE_RULE_FO.md` sha256 `d5a47e8dd7922121adcc9847f7a051e093525d4cdfe482ce84a7a7f72c62e9c0` (이 문서와 함께 고정).
- 요점: 짝 FO − NC3(주) · B − FO · FO − V-A, 시드별·평균 없음; 줄 Ω701 / Ω635 / Ω701 − Ω635 / ④a / ④b(첫 관측 차분) / ④ / Ω 밖 (a)(b)(Ω701·Ω635) / ① / ② / ④b 1098·1099·도시 / 링크 66 / 도시도로(codex 분할) / 감시 FW_W 본선, 두 꼴; FW_E 칸 RF1–RF11 + 함께 + DA1–DA4 (FW_E 도구 그대로, FO 데이터 전 자기 시험 102/102); B − FO 는 고정된 B 출력과의 [계산]; 점검 X1–X8.
- [실행] 표 도구 자기 시험(FO := B): FO − NC3 = B_RESULTS 의 B − NC3, FO − V-A = B − V-A, B − FO = 0 — 318칸 모두 같음; X3·X3b 참(`FW/ana/selftest/fo_tables_selftest.json`).

## 9. 멈춤 규칙 (하나라도 맞으면 멈추고 보고; 사용자가 정함)

1. 관문 5.2 의 어느 조건이든 거짓(R0 C5 다름 = HOLD 포함), 재생 stopped_cap, 잠금 60 분 못 잡음.
2. G2 에서 도시 SG GREEN 이 native 와 1 프레임이라도 다름, 또는 주기·쓰는 SG 집합이 다름.
3. FRZ_FO verify 실패, PINS_FO 의 도구 sha 다름(실행기가 거부), 발사기 FIXED sha 다름.
4. 런 이상 종료(PRE_B_CONCURRENT §7 의 (가)–(라) 그대로), run2 도 멈춤, 자리 기다림 12 h 넘음, 디스크 부족.
5. 런 점검 V2–V5 중 거짓.
6. 비교 규칙 X3·X3b·X6·X7.
7. 봉인 시드 37/59/61/67·`sealed/`·codex 64cf-s59/s61/s67·v3c3-s47 값에 닿을 일(열지 않음).
8. 이 문서에 없는 칸을 보고 싶어짐 → "데이터 뒤" 절에만, 무게 낮음으로.

## 10. 도구 핀

- `FO/PINS_FO.sha256` sha256 `5458c623ae3a19afc0db9f07f56bd9bb142ac56c78f48cffdc75cc710204723e` (124줄: 짓기·관문·발사기·분석 도구, 자기 시험 출력, FW_E 도구·기준 출력, B 고정 출력, FRZ_FO FREEZE·설정·러너, 사전 점검 provenance 넷; `cd SP; sha256sum -c` 모두 OK [실행]). 목록 원본 `FO/pins_list.txt`.
- 주요 도구: `fog_build_inputs.py` `e9741850…`, `fog_replay.ps1` `b8eda978…`, `fog_queue.ps1` `d015a692…`, `fog_summary.py` `7ac04cd5…`, `fog_sg_native.py` `751e1e4c…`, `fo_run_check.py` `acfd805b…`, `fo_fwe.py` `4e46b138…`, `fo_tables.py` `0520e1b3…`, `fo_ana.ps1` `543a6d16…`, `fo_launch_wmi.ps1` `2b6119f8…`, 사본 생성 `make_spec_fo.py`·`mkcopy.py` `8ec4f60c…`(기록 `copies_fo_record.json`) — 64자는 PINS_FO.
- FO 분석 사본(B 사본에서 런 뿌리·출력 폴더·주석만 바꿈, 20파일, 바뀐 줄 37): `CW/vhr_fo/*`, `CW/omega_fo/omega701_recount_fo.py`, `CW/rawcheck_fo/*`(codex 스캔 다섯은 바이트 복사, PINS_B 와 같은 sha).

## 11. 이 단계에서 한 일 (2026-10-27 19:50–20:35 KST)

| 일 | 결과 |
|---|---|
| 짓기 사슬(공용 잠금 아래, 19:50:15–19:57:54) | FRZ_FO·사전 점검 넷·짝 점검 통과 |
| G2 도구 양성·음성 대조, 요약·입력 도구 자기 시험 | §5.3 |
| FW_E 칸 도구 자기 시험 | 102/102 |
| 표 도구 자기 시험 | 318/318 |
| 런 점검 도구 자기 시험(B) | §7 |
| 발사기·멈춤 도구 모의 실행 | 17/17, 7/7 |
| VISSIM·COM | 0 (발사 0, 재생 0) |
| 남의 프로세스 | 손댐 0, kill 0 |
| 쓰기 | `D:/VISSIM-merge/k8_gate_trees/codexhandoff/fo/`(원천·동결·사전 점검), `SP/codex_handoff/fo/`, `CW/*_fo/`; 커밋·푸시 0 |

- 사건 하나(밝힘) [실행]: 캐시 sha 를 모으다 `rmcause/phys/scan/nc_s*.json` 글롭이 `nc_s47.json`·`nc_s53.json` 의 sha256 도 계산했습니다. 내용은 열거나 출력하지 않았고 어떤 도구에도 쓰지 않습니다. 이후 도구는 시드 31·41·43 경로만 이름으로 적습니다.

## 12. 이 선언이 알려 주지 않는 것 [추론]

- O2(작동기만) 조합은 codex 가 한 번도 돌리지 않았습니다. 관문은 첫 결정 하나만 봅니다. 뒤 결정의 짐·예외는 런에서만 압니다(예외 유지는 설계된 동작; 유지가 생기면 T 와 종류를 적음).
- 미터 결정은 도시 신호 상태에 따라 달라지므로 B − FO 에는 두 레버의 상호작용이 들어 있습니다.
- G2·V4 는 GREEN 초만 봅니다. 노랑·적색과 COM 쓰기 자체의 효과는 보지 않습니다.
- PRE_B §7·COMPARE_RULE_B §8 의 한계(64cf 계수의 v3c3 적합성 등)는 그대로입니다.

## 13. 다음 걸음

1. T=900 관문 큐 발사(§5.1 명령). 통과 → 관문 요약 sha 를 LOG 에 적고, 사용자 발사 허락 뒤 §6 시작 명령. 실패 → 멈추고 보고.
2. FO 런 동안 `-Plan prescan`(NC3·V-A, FO 데이터 아님) 가능. 런이 끝날 때마다 `-Plan stage -Seed s`, 셋 뒤 `-Plan final`.
