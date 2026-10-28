# FACTS_FO — codex '고속도로만' 팔의 스위치, 그리고 FRZ_B1 에서 쓸 수 있는지 (2026-10-27 18:40 KST, VISSIM 0)

- 근거 결정: D-K9-112 (`SP/K9_1_J1_NOTES_20261013.md` sha `4d47ce5b…` :380) — "B 와 다른 것은 도시 제어 끔 하나(VSL 은 B 와 같이 110 고정)" 그리고 "codex 64cf freeway_only 팔 정의를 먼저 읽어 같은 스위치를 씀".
- 판정 낱말은 쓰지 않습니다. VISSIM·COM 0, 무거운 오프라인 일 0(파일 대조만), kill 0, 커밋·푸시 0, frozen 트리·GWT8·codex 작업 트리 쓰기 0, sealed/ 열기 0, 봉인 시드 0.
- 표시: **[실행]** 명령으로 확인 · **[읽음]** 파일을 읽어 확인 · **[추론]** 시험하지 않은 판단 · **[계산]** 산술.
- SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`. HO = 인계 묶음 `D:/VISSIM_handoff/20261024`(sealed/ 제외). FRZ_B1 = `D:/VISSIM-merge/k8_gate_trees/codexhandoff/b1/frozen/sdmpc31_a49981ff_202610261410`(FREEZE `558de2c1…`). W = `SP/codex_handoff/fo/work`.
- codex 파일과 인계 문서는 자료로만 읽었습니다.

## 0. 줄임말 (처음 한 번)

- **FO** = 이번에 만들려는 팔. codex SDMPC 가 고속도로 쪽(램프 미터)만 움직이고 도시 신호는 움직이지 않는 v3c3 폐루프 런.
- **B** = codex 판(a49981ff)을 v3c3 로 옮긴 폐루프 런(도시 신호 + 미터 최적화, VSL 110 고정). **NC3** = v3c3 무제어 3시드. **V-A** = 우리 묶음 B1 폐루프.
- **SDMPC** = codex 의 분산 모형예측제어기. **RM** = 램프 미터(진입 램프 신호). **VSL** = 가변 제한속도. **TSC** = 도시 교차로 신호 제어.
- **solo 판** = codex 가 64cf-s29 의 'freeway_only'·'urban_only' 팔을 돌린 코드 판. 브랜치 `codex/solo355-local-information`, HEAD `2f28000a…` [읽음 HO/HANDOFF.md:220]. **joint 판** = codex 공동제어 판 `ca181e84…`(dirty). a49981ff 는 joint 판을 담은 인계 커밋입니다.
- **NP / NUF** = SDMPC 의 두 공유 자원. NP = 도시 순유입 상한, NUF = 램프→본선 합류량 목표.
- **고속 경로(hotpath)** = 같은 문제를 빨리 풀려는 캐시·병렬 스위치(`sdmpc_fast_primitives` 등).
- **정책 토큰** = SDMPC 설정 묶음의 해시. 직전 결정의 가격을 다음 결정이 이어 받을 때 같은지 검사합니다.
- **Ω701** = codex 목적 영역(링크 701개). **④** = ④a 망 전체 링크 체류 + ④b 미삽입 대기(COMPARE_RULE_B §0).

## 1. 쉬운 답

1. [읽음·실행] codex 의 freeway_only 팔은 **설정 스위치 하나가 아닙니다.** 다른 코드 판(solo 판) 위에서, 설정 키 2개를 켜고 고속 경로 18칸을 끈 것입니다.
2. [읽음] 스위치 키 2개: `adapter.sdmpc_actuator_scope = {mode: "freeway_only", baseline: {green_times 68개, offsets 17개}}` 와 `adapter.sdmpc_information_scope = "freeway_only"`.
3. [실행] 이 두 키를 읽는 코드는 FRZ_B1(a49981ff)에 **없습니다**(grep 0건). codex git 저장소에도 solo 커밋 `2f28000a` 객체가 없습니다.
4. [읽음·추론] FRZ_B1 은 모르는 adapter 키를 거부하지 않고 그냥 지나갑니다(FRZ_B1 `sdmpc.py:95-261`). **키만 넣으면 조용히 B 가 다시 돕니다.**
5. [실행] solo 판의 코드는 인계 사본에 바이트 그대로 있습니다: 고친 파일 13 + 새 파일 4, 모두 `evaluation/controllers/`. solo FREEZE 와 sha 18/18 같음. B0 고침 7파일과 겹치는 파일 0.
6. [읽음] 그런데 `information_scope` 는 "도시 신호 끔" 보다 많이 바꿉니다: 목적함수(고속도로 소유자 2개만), 예측기(실험용 지역 예측기), NP 자원 끔, 고속 경로 강제 끔. codex 스스로 "목적·정보·액추에이터가 함께 다르다" 고 적었습니다(HO/HANDOFF.md:222, plan.json `interpretation`).
7. **멈춤.** D-K9-112 의 두 조건("같은 스위치" 와 "B 와 하나만 다름")이 이 사실로는 동시에 맞지 않습니다. 선택지는 §6 입니다. 사용자가 정합니다.

---

## 2. codex freeway_only 팔(64cf-s29)이 joint 팔과 다른 점

### 2.1 런의 정체 [읽음]

| 항목 | joint | freeway_only | 근거 |
|---|---|---|---|
| 런 폴더(원래) | `E:/VISSIM_runs/20261012_adopted355_optimized_s29_8100/sdmpc` | `D:/VISSIM_runs/20261013_solo355_local_freeway_only_s29_8100/sdmpc` | HO/HANDOFF.md:41, :217 |
| 코드 판 | ca181e84(dirty) | solo 2f28000a(dirty), FREEZE `f55ecec3…` | HANDOFF:45, :220-221; provenance `observation.freeze.sha256` |
| 설정 | `…/native413_adopted355/optimized_config.json` `c9088262…` | `diagnostics/solo355_local_20261013/freeway_only_config.json` `cd193948…` | provenance `files.tuning` |
| 어댑터 sha | `a615d8ca…` | `48fba73b…` | provenance `files.adapter` |
| VBS·워치독·러너 | `14722088…` · `b56e1b36…` · 같은 정본 러너 | 같음 | provenance `files.*`; [실행] solo vs joint FREEZE 코드 대조에서 차이 0 |
| 러너 인자 | `-SimPeriod 8100 -Seed 29 -Arms sdmpc -TuningRelativePath <설정>` 외 | 같음, `-TuningRelativePath` 만 다름(큐 `run_queue.ps1` 이 조건별 설정만 바꿈) | HANDOFF:111-113; plan.json `conditions` |
| env (RW_*) | 20개 | 값이 같음. 다른 것은 경로 글자와 `RW_SIGNAL_OBSERVATION_CONFIG_SHA256`(= 설정 sha) 뿐 | [실행] 두 provenance `env` 대조 |
| 망·시드·길이 | 64cf `64cf5f55…`, seed29, 8,100 s | 같음 | provenance `files.network` |

- provenance sha: freeway_only `run_provenance_sdmpc31_sdmpc8100_s29.json` `9efb542b…`, joint `40afc822…` [실행].
- codex 의 말 [읽음 HO/evidence/solo_runtime/plan.json `8c2dfd32…`]: `common.objective` = "regional residence TTT (freeway+onramps / urban+offramps)", `design` = "Regional objectives and information-isolated control … Whole Omega701 is posthoc evaluation only", `interpretation` = 목적·정보·액추에이터가 함께 다르며 메시지만 뺀 비교가 아님.

### 2.2 설정 차이: joint → freeway_only, 잎 22개 [실행 `W/jdiff.py` `57efcff2…`]

| 묶음 | 잎 | joint | freeway_only |
|---|---|---|---|
| 스위치 | `/adapter/sdmpc_actuator_scope` | 없음 | `{mode:"freeway_only", baseline:{green_times 68, offsets 17}}` |
| 스위치 | `/adapter/sdmpc_information_scope` | 없음 | `"freeway_only"` |
| 고속 경로 true→false (10) | `sdmpc_response_cap_cache, fast_primitives, prediction_hotpath, prediction_cache, compact_audit, initial_shared_prediction, initial_derivative_overlap, trial_derivative_overlap, tangent_shared_primal, ramp_stock_cache` | true | false |
| 고속 경로 없음→false (7) | `sdmpc_stock_geometry_hotpath, receiving_geometry_cache, persistent_urban_fifo, array_urban_pipeline, array_transport, spatial_receiving, flow_update_cache` | 없음 | false |
| 고속 경로 지움 (1) | `sdmpc_tangent_concurrent_primal` | true | 없음 |
| 이름 | `/name`, `/description` | `native348_FW5_U10_optimized` | `solo355_local_freeway_only` |

- [읽음] 고속 경로를 끈 까닭은 코드의 강제입니다: information_scope 가 있으면 16개 고속 경로 중 하나라도 켜져 있을 때 `ValueError('Unqualified global hotpath in regional information policy')`(solo `sdmpc.py:270-277`). 나머지 둘(ramp_stock_cache·flow_update_cache)은 prediction_cache 를 요구하므로 함께 꺼짐(FRZ_B1 `sdmpc.py:203-206` 과 같은 줄).
- [읽음] VSL: 두 설정 모두 `sdmpc_fixed_vsl` 이 없습니다. 둘 다 VSL 최적화를 허용합니다.
- [읽음] baseline 값 예: SC1 = p1 54 · p2 21 · p3 32 · p4 31 · offset 19, SC1001–1005 = 46·23·45·24 · 75.

### 2.3 코드 차이: solo 판 − joint 판 [실행 `W/cmp_freeze_code.py` `57206d03…` → `W/cmp_freeze_code.json` `f35c0b7a…`]

- 두 FREEZE 파일표(solo `f55ecec3…`, joint `f980fcce…`)를 코드 파일(.py·.ps1·.vbs·.yaml, evaluation·scripts·vendor·tools·harness·plant·러너)로 견줌: **고친 13 + 새 4, 모두 `evaluation/controllers/`.** 러너·워치독·VBS·vendor NumSim 은 같은 바이트.
- 코드 밖 차이: 시험 `tests/test_solo355_scope.py` 1개와 `diagnostics/solo355_*` 설정·탐침 25개(인계 사본에는 freeway_only_config.json 만 있음, 시험 파일 바이트는 없음) [실행].

| 파일 | 하는 일 (solo 줄) |
|---|---|
| 새 `sdmpc_actuator_scope.py` (44줄) | `configure`(:5-24) baseline 이 17 신호×p1–p4·offset 을 다 덮는지 검사. `allows`(:26-28) freeway_only 면 meter·vsl 만 허용. `check`(:30-44) 명령의 green/offset 이 baseline 과 1e-9 안에서 같은지 검사, 다르면 `ValueError('Inactive urban actuator changed')` |
| `sdmpc.py` | :103-112 information_scope 읽기 → `regional_prediction_prototype`, `regional_context_required`. :264-269 actuator_scope 설치, information 이 있으면 같은 mode 의 actuator 를 요구(반대 방향 요구는 없음). :270-277 고속 경로 금지. :343 비용 소유자 = `active_owners`(freeway_only 면 FW_W·FW_E). :420/:447/:462 좌표에서 green·offset(신호), meter, vsl 축을 `allows` 로 거름. :885-886 freeway_only 면 직전 명령의 NP 목표 0. :931 기준 명령 범위 검사. :939 전역 공유 질의 안 만듦. :1054-1055 리더 NP 후보 (0,) 만. :1375·:1408 메타데이터 표지 |
| `runtime_setup.py` | :83-84 wu-link 도 지역 모드면 1 s 시작을 무예측 시작으로. :333 시작 메시지 글자(**모드와 무관하게 바뀜**). :344-352 지역 경계 관측(freeway_only 면 `ramp_arrival` 역할만) 저장 |
| `vissim_stackelberg_adapter.py` | :12681-12690 지역 모드면 `sdmpc_regional_context.prepare` 로 자기 정보 그래프를 만든 뒤 풂. :13329-13335 지역 모드 시작 명령 = 무제어 명령 + 범위 검사 + `regional_startup_baseline` |
| 새 `sdmpc_regional_context.py` (169줄) | :85-91 freeway_only 면 도시 movement 용량·압력 비움, 저장 0, beta 0. :147-148 정보 mode = 액추에이터 mode 요구 |
| 새 `sdmpc_regional_contracts.py` (127줄) | :23-26 활성 자원 [NP=False, NUF=True]. :29-40 예측 수요에서 램프 도착·도시 경계 0. :43-45 소유자 = 고속도로 링크 |
| 새 `sdmpc_regional_prototype.py` (377줄) | 머리말(:1-6) "Experimental cut-boundary regional predictor; not a production controller". :37-59 램프 도착 = 마지막 닫힌 창 횡단율을 지평 동안 고정. :232-234 진출 출구 = `freeway_capacity_veh_h` 로 열린 경계(도시 역류 안 봄). :248 진출 램프 `'10643'` 이 글자로 박혀 있음 |
| `sdmpc_tangent_worker.py` | :264 지역 모드면 위 지역 예측기로 예측(전체 rollout 대신) |
| 나머지 9개 | `area_follower_objective, joint_owner_neighbors, sdmpc_budget, sdmpc_central, sdmpc_pfo, sdmpc_sequence, sdmpc_tangent, sdmpc_tangent_constraints, sdmpc_tangent_surrogate` — 자원 가림(mask), 소유자 수, 3블록 명령 증거, 범위 검사 연결. 전체 차분 `W/solo_vs_frzb1_13files.diff` `d29cdb26…` |

- [읽음·추론] 스위치 키가 없으면 solo 코드는 joint 코드와 같은 길을 갑니다(모든 새 분기가 `regional`·`actuator_scope` 로 막혀 있음). 예외: `runtime_setup.py:333` 메시지 글자, `sdmpc_central.next_budget` 의 0 방향 건너뜀(원래도 같은 점이라 걸러질 것으로 봄 [추론]).

### 2.4 레버가 실제로 한 일 (action CSV) [실행]

| | joint | freeway_only |
|---|---|---|
| 행 수 (vsl / ramp_meter / signal / signal_sg) | 3,630 / 440 / 833 / 5,978 | 같음 |
| VSL 명령 | 110 만 3,630 | 110 3,551 · **100 68 · 90 11** |
| 미터 녹색(s/10 s) | 2–10, 9 종 | 2–8·10, 8 종 |
| 도시 신호 계획 종류(신호별) | 46–48 종 | **1 종 = baseline**(17 신호 모두) |
| 신호 행 시작 | 900 s(제어 시작), 그 뒤 150 s 마다 | 같음 |

- 근거: `HO/raw/freeway_only/sdmpc/action_sdmpc31_sdmpc8100_s29.csv` `4581afe1…`, joint 같은 이름. HANDOFF:223 "freeway_only 에서는 실제로 100/90 명령도 선택됐으므로 순수 RM-only 로 부르면 안 된다".
- 결정 건강(codex PC): 48/48 새로 풂, 유지 0 [읽음 `freeway_only_control_health.json` `e3bc00c1…`].

### 2.5 "도시 native" 의 정확한 뜻 [실행·읽음]

- baseline = codex 신호 계약이 표현한 **native 프로그램 값**입니다. 무제어 명령을 만드는 `_make_no_control` → `represent_native_no_control_signals`(FRZ_B1 adapter `:11223-11267`)가 `native_clock_basis` 의 `native_green_sec`·`reference_offset_sec` 로 채웁니다. 이때 `new_com_command = False`.
- 그러나 freeway_only 에서는 **900 s 부터 150 s 마다 이 baseline 을 COM 으로 다시 씁니다**(signal·signal_sg 행 있음). codex 실행 점검 `execution.json`(`33b7072d…`): 명령 시계 대 native LDP 대조 통과, `native_only_groups` = SC5 9–24·SC7 9–16(이 SG 들만 VISSIM 자체 프로그램). LSA 대조는 `passed=false`.
- 그래서 FO 의 도시 신호는 "VISSIM 이 손대지 않은 native 프로그램"(NC3)이 아니라 "native 값을 명령으로 다시 쓴 것" 입니다. 둘이 같은 신호 시각을 내는지는 이 단계에서 확인하지 않았습니다 [추론].

### 2.6 codex 64cf-s29 수치(참고, 한 시드, 망·수요가 v3c3 와 다름) [읽음 `HO/derived/metrics_0_8100.csv` `a2757f72…`]

| 지표 (veh·h, 0–8100 s) | NC | joint − NC | freeway_only − NC |
|---|---|---|---|
| Ω701 | 7,406.17 | −494.66 | +409.90 |
| ④a(망 전체 FZP 체류) | 8,994.93 | −448.99 | +384.84 |
| ④b(미삽입 대기) | 모름 | 모름 | 모름 |
| Ω 밖 (b) = ④a − Ω701 | 1,588.76 | +45.67 | −25.06 |
| FW_E 7링크(codex 정의) | 2,124.52 | −283.65 | −351.84 |
| 도시도로 | 3,642.61 | −294.56 | +256.67 |
| 동측 진입램프 | 121.75 | +85.02 | +125.00 |

- ④b 는 NC 의 0–8100 s 미삽입 적분이 없어 모름(HANDOFF §1, §9). codex FW_E 7링크는 우리 FWE_DECOMP 의 FW_E 정의와 다릅니다.

---

## 3. FRZ_B1(a49981ff)에 같은 스위치가 있나 — 없음

1. [실행] FRZ_B1 `evaluation/controllers` 에서 `actuator_scope|information_scope|regional_prediction_prototype` grep 0건. 모듈 4개(`sdmpc_actuator_scope.py`, `sdmpc_regional_*.py`) 없음. `diagnostics/solo355_local_20261013` 없음.
2. [실행] codex 작업 트리(a49981ff, 읽기만): `evaluation scripts tools harness` 에 `freeway_only|actuator_scope|information_scope|solo355` 0건. `handoff/` 의 맞는 줄은 인계 증거 표(지표·결정 녹색)뿐. `git cat-file 2f28000a…` → 객체 없음, `ca181e84…` → commit.
3. [읽음] FRZ_B1 `sdmpc.configure`(`sdmpc.py:95-261`)는 아는 키만 `tuning.get('adapter',{}).get(...)` 로 읽고, 모르는 키를 거부하는 검사가 없습니다(adapter·runtime_setup·sdmpc·joint_owner_game 에서 unknown-key 검사 grep 0 [실행]). → 두 키를 B 설정에 넣기만 하면 **아무 일도 일어나지 않고 B 가 돕니다** [추론]. 메모리 교훈 "게이트가 config 밖이면 죽은 코드다" 와 같은 함정.
4. [읽음] codex FO 설정의 고속 경로 끔을 FRZ_B1 에 그대로 넣으면 설정 단계에서 멈춥니다: `central-pfo-cap-v3` 는 `prediction_hotpath` 를 요구(FRZ_B1 `sdmpc.py:223-225`). solo 판은 이 줄을 `regional` 일 때 풀었습니다.
5. [실행] 세 판의 코드 대조(`W/cmp_freeze_code.json`):

| 대조 | 한쪽만 | 다름 |
|---|---|---|
| solo − joint | solo 4(새 모듈) | 13 (모두 evaluation/controllers) |
| joint − FRZ_B1 | joint 1(`tools/vbs_compile_check.ps1`, 실행 무관) | 7 = B0 고침 F1·F2·F3·H1·H2·H3 + 러너(N1+B1) |
| solo − FRZ_B1 | solo 5 | 20 = 위 13 + 위 7 |

   → solo 고침 17파일과 B0/B1 고침 7파일은 **서로 겹치지 않습니다.** FRZ_B1 의 그 13파일은 joint 판과 같은 바이트입니다(그래서 solo 파일을 통째로 덮으면 "FRZ_B1 + codex solo 고침" 이 정확히 됩니다) [실행 `W/cmp_solo_vs_frz.py` `58ec5196…` → `W/cmp_solo_vs_frzb1.json` `ad0b936d…`].
6. [실행] 인계 사본 `HO/original_code_dependencies/solo/` 의 17파일 + freeway_only_config.json 은 solo FREEZE 의 sha 와 18/18 같습니다.

## 4. v3c3 에서 FO 를 만드는 최소 변경 (사실만, 아직 아무것도 만들지 않음)

### 4.1 코드 (두 갈래 공통)

- 새 원천 = FRZ_B1 원천 + solo 17파일 바이트 복사. 새 동결은 `D:/VISSIM-merge/k8_gate_trees/codexhandoff/fo/frozen/` 아래. B0/B1 고침은 그대로 남음(겹침 0).
- 복사할 파일과 sha 앞 12자(전체 sha 는 `W/cmp_solo_vs_frzb1.json`):

| 파일 | solo(넣을 것) | FRZ_B1(지금) |
|---|---|---|
| sdmpc.py | ffe0f8a4ae01 | 5c1ba251a352 |
| vissim_stackelberg_adapter.py | 48fba73b198d | a615d8caa54c |
| runtime_setup.py | 5bbb1fb55a3d | 74941f038286 |
| area_follower_objective.py | 74a6fda4cbac | 9e94bcd3e344 |
| joint_owner_neighbors.py | c3a0d1d5f81b | ecb0f13e1e59 |
| sdmpc_budget.py | 7643ef910678 | 66c5081e7475 |
| sdmpc_central.py | 30e00fec0b49 | b442a7ed5c25 |
| sdmpc_pfo.py | c8b31563a2e1 | e00a42dbd506 |
| sdmpc_sequence.py | ea7396965e3e | c5004c7ad5fb |
| sdmpc_tangent.py | 950fefa4cbfc | 57cc85f468fd |
| sdmpc_tangent_constraints.py | 3b77240b6915 | eb75f0cb3299 |
| sdmpc_tangent_surrogate.py | 8a474094ef90 | a7e45a7d4c06 |
| sdmpc_tangent_worker.py | fea0badf8b6e | f10b6020db25 |
| 새 sdmpc_actuator_scope.py | 606726622356 | 없음 |
| 새 sdmpc_regional_context.py | 519df9b7858a | 없음 |
| 새 sdmpc_regional_contracts.py | b6294641bdb0 | 없음 |
| 새 sdmpc_regional_prototype.py | cf6213359462 | 없음 |

- 복사하지 않는 것: solo 판의 `control_area_objective.py`·`control_hold.py`·`lane_offramp_runtime.py`·`physical_movement_routes.py`(그리고 워치독·VBS·러너)는 codex 원본 바이트라 FRZ_B1 의 B0 고침(F1·F2·F3·H1·H2·H3·N1)과 다릅니다. 이 파일들은 FRZ_B1 것을 그대로 둡니다 [실행 `W/cmp_solo_vs_frzb1.json`].
- codex 의 이 고침용 시험(`tests/test_solo355_scope.py`, `diagnostics/solo355_local_20261013/test_regional_*.py`)은 인계 사본에 바이트가 없어 돌릴 수 없습니다 [실행].

### 4.2 설정 — 갈래 A: codex freeway_only 그대로 (VSL 만 B 처럼 110 고정)

- B 설정 `diagnostics/b0_v3c3/config_b0_v3c3.json`(`729640af…`) + §2.2 의 adapter 잎 20개(스위치 2 + 고속 경로 18) + 이름. B 의 VSL 고정(`/adapter/sdmpc_fixed_vsl`)은 그대로 둡니다.
- [실행] baseline 값은 v3c3 에서도 그대로 맞습니다: B 3시드(v3c3-s31·s41·s43)의 무제어 명령(t=1, t=750) green 68·offset 17 이 codex baseline 과 **0 차이**, VSL 110, 미터 10, `sdmpc_state` 없음. `check_scope` 가 시작·첫 결정에서 통과할 값입니다 [추론].
- [실행] B 설정의 고속 경로 값은 codex joint 와 같습니다(B0 는 이 키들을 건드리지 않음). 그래서 갈래 A 의 고속 경로 델타 18칸은 codex 의 joint→FO 델타와 같습니다.
- [읽음] codex FO 와 다른 점: VSL 최적화 대신 110 고정. solo 코드에서 고정 VSL 은 축을 만들지 않습니다(solo `sdmpc.py:462`). codex 가 "지역 모드 + 고정 VSL" 을 함께 돌린 기록은 찾지 못했습니다 [읽음 HANDOFF §5 표].

### 4.3 설정 — 갈래 B: 액추에이터 범위만 (information_scope 없음)

- B 설정 + `/adapter/sdmpc_actuator_scope`(갈래 A 와 같은 값) 하나. 고속 경로·목적함수·예측기는 B 그대로.
- [읽음] 코드는 이 조합을 막지 않습니다: solo `sdmpc.py:264-269` 는 "information 이 있으면 actuator 필요" 만 검사하고 반대는 검사하지 않습니다. 고속 경로 금지(:270-277)도 information 이 있을 때만입니다.
- [읽음] 이 조합에서 신호 축이 없는 소유자는 건너뜁니다(solo `sdmpc.py:1210` `if not len(ix): continue`, `sdmpc_pfo.py` 같은 줄). 목적함수는 Ω701 19 소유자 그대로입니다(:343 은 regional 일 때만 바뀜).
- [추론] codex 가 이 조합을 돌린 기록은 없습니다. 고속 경로(prediction_hotpath, fast_primitives, tangent_shared_primal …)가 신호 축 0개를 받아도 되는지는 시험 전에는 모릅니다.

### 4.4 러너·env·VBS (두 갈래 공통) [읽음·추론]

- 러너 인자: B(PRE_B §1)와 같고 `-FrozenTree`(새 FRZ)·`-ResultsRoot`(`D:/VISSIM_runs/20261028_codex_fo_v3c3/s<seed>`)·`-TuningRelativePath`(새 설정)만 다릅니다. codex 도 조건 사이에 설정만 바꿨습니다(§2.1).
- env: 워치독이 설정에서 세우는 RW_* 는 같고 `RW_SIGNAL_OBSERVATION_CONFIG_SHA256` 만 새 설정 sha 가 됩니다(codex 두 provenance 차이와 같은 꼴).
- VBS·워치독: FRZ_B1 것 그대로(H1·H3 유지 고침 포함).

## 5. B 와 달라지는 것 (갈래별)

| 항목 | B | 갈래 A (codex FO 정의) | 갈래 B (액추에이터만) |
|---|---|---|---|
| 도시 신호 | 17 SC green·offset 최적화, 900 s 부터 COM | baseline 고정, 900 s 부터 150 s 마다 COM 으로 다시 씀 | 갈래 A 와 같음 |
| 램프 미터 | 최적화 | 최적화 | 최적화 |
| VSL | 110 고정 | 110 고정(codex FO 는 최적화, 100·90 선택) | 110 고정 |
| 목적함수 소유자 | Ω701 19개(17 신호 + FW_W·FW_E) | FW_W·FW_E 2개 + 수동(passive) | B 와 같음 |
| 예측기 | 전체 lane plant rollout(도시 포함) | `sdmpc_regional_prototype`(실험용): 램프 도착 = 마지막 창 고정, 출구 = 열린 경계, 도시 모형 없음 | B 와 같음 |
| 자원 | NP·NUF | NUF 만(NP 0, 리더 NP 후보 (0,)) | B 와 같음 |
| 고속 경로 | 켬 | 18칸 끔(코드 강제) | B 와 같음 |
| 코드 판 | FRZ_B1 | FRZ_B1 + solo 17파일 | 같음 |
| 정책 토큰 | B 값 | 다름(옵션에 `actuator_scope`·`regional_*`·고속 경로 값이 들어감, solo `sdmpc.py:807-814`) | 다름(`actuator_scope` 가 들어감) |
| 메타데이터 표지 | — | `sdmpc_state.regional_mode/active_resources`(:1375), 결정 `regional_mode, active_resources, active_cost_owners, nuf_definition, input_isolation_qualified, input_context_schema`(:1408), 보고 `regional_context`(adapter :12688), 명령 `regional_prediction_blocks`(area_follower_objective :1496), 시작 `regional_startup_baseline`(adapter :13335), 시작 메시지 글자(runtime_setup :333) | 시작 메시지 글자(runtime_setup :333)만 [읽음]. 신호 축 없음은 결정 기록의 좌표 수에 보임 [추론] |
| 시작 경로 | t=1 무제어(no-control) | wu-link 도 지역 무예측 시작 허용(runtime_setup :83-84) | B 와 같음 |
| 결정 시간 | 이 PC 중앙값 448–469 s(3시드, n=55씩) [실행 decision_budget] | 모름. codex PC 에서 FO 중앙 262 s 대 joint 276 s [실행] | 모름 |
| 시험 기록 | B 3시드 | codex 64cf-s29 한 런(48/48 새로 풂) | 0 |
| v3c3 적합 위험 | — | `'10643'` 글자 고정(prototype :248). v3c3 상태에 `ramp_arrival:RM_C*` 8개·`off_entry:10643` 은 있음 [실행 B s31 `state_000900.json`]. `lane_exact` 등 조건 통과 여부는 모름 | 신호 축 0 + 고속 경로 조합 [추론] |

- 두 갈래 모두: FO 의 도시 신호는 NC3 의 "손대지 않은 native" 와 다릅니다(§2.5). FO − NC3 에는 고속도로 제어 몫과 함께 "native 값 다시 쓰기" 효과가 섞일 수 있습니다 [추론].
- 갈래 A 의 B − FO 에는 도시 제어 몫 말고도 목적함수·정보·예측기·고속 경로 차이가 섞입니다 [읽음 §2.3]. 갈래 B 의 B − FO 는 도시 신호 끔 하나에 가깝지만(위 표), 시작 메시지 글자와 정책 토큰은 다릅니다.

## 6. 선택지 (사용자가 정함) — 깨끗한 스위치가 없으므로 여기서 멈춥니다

| | 무엇 | 갖춘 것 | 걸리는 것 |
|---|---|---|---|
| O1 | 갈래 A: codex freeway_only 그대로 이식 + VSL 110 | "같은 스위치" 그대로. codex 가 64cf 에서 한 번 끝까지 돌린 조합(고정 VSL 은 빼고) | "B 와 하나만 다름" 이 아님. B − FO 를 "도시 제어 몫" 으로 읽을 수 없음. 실험용 예측기, `'10643'` 고정 |
| O2 | 갈래 B: 액추에이터 범위만 | D-K9-112 의 "도시 제어 끔 하나" 에 가장 가까움. 목적·예측기·고속 경로가 B 와 같음 | codex 실행 0회 조합. "같은 스위치" 는 반만(두 키 중 하나). 시작 전에 T=900 관문 재생으로 돌아가는지부터 봐야 함 |
| O3 | O1 과 O2 를 둘 다(각 3시드, 6런) | B − O2 = 도시 제어 몫, O2 − O1 = 목적·정보·예측기·고속 경로 몫(한 덩어리)으로 나눌 수 있음 | VISSIM 런 2배(런당 이 PC 10–14 h, 우리 동시 3개 상한) |
| O4 | FRZ_B1 설정만으로 흉내(예: 신호 이동 폭 0) | 코드 이식 없음 | codex 스위치가 아님. 검증 0. 키만 넣는 방식은 조용히 B 가 됨 |

- [추론] 권하는 순서: **O2 를 먼저 오프라인 T=900 관문 재생(3시드, B 의 기록 상태)으로 확인** → 돌아가면 O2 3시드. O1 은 codex 표와 나란히 보려는 목적이 있을 때 더함(O3). 까닭: D-K9-112 가 원한 분해(B − FO = 도시 제어 몫)를 지키는 것은 O2 뿐이고, 돌아가는지는 VISSIM 없이 싸게 확인할 수 있습니다.
- 어느 쪽이든 발사 전에 필요한 것 [추론]: 새 원천·동결(FREEZE 검증)·러너 사전 점검 3시드, PRE_FO(설정 차이·관문·비교 규칙·표·멈춤 규칙·도구 sha) 고정, T=900 재생 관문(B 와 다른 메타데이터 표지를 미리 선언), baseline SG 일정 대 native .sig 활성 프로그램 대조(오프라인, §2.5 의 빈틈), 결정 시간으로 StallSec 3,600 여유 확인.

## 7. 한 일

| 차례 | 일 (모두 2026-10-27 오후, 18:40 KST 에 끝남) | 근거 |
|---|---|---|
| 1 | HANDOFF §5·plan.json·두 provenance 읽음 | [읽음] |
| 2 | 설정 대조(joint→FO 22잎; joint→B 는 이 도구 단위로 53줄 — B0 의 "잎 30 + 이름" 과 세는 단위가 다름, 램프 표 키를 하나씩 셈) | [실행 `W/jdiff.py`] |
| 3 | solo 사본 대 FRZ_B1·codex 작업 트리 파일 대조, 세 FREEZE 코드 대조, git 객체 확인 | [실행 `W/cmp_solo_vs_frz.py`, `W/cmp_freeze_code.py`] |
| 4 | action CSV 레버 집계(joint·FO), B 3시드 무제어 명령 대 baseline, 결정 시간 집계 | [실행] |
| 5 | v3c3 .sig 프로그램 offset 목록, B s31 T=900 상태의 경계 이름 | [실행] |

- 무거운 일(관문 재생·FZP 훑기) 0, 잠금 파일 사용 0. VISSIM 0. 남의 프로세스 0.

## 8. 산출물 (sha256) [실행]

| 파일 | sha256 |
|---|---|
| `W/jdiff.py` | 57efcff268b32c51b676a5556ac86afbca9d13bc45bd5e66ce1a57baf45b7479 |
| `W/cmp_solo_vs_frz.py` | 58ec5196038174f39d53d4356ca6cafcb6576314fd8d546322e9a5c0f3ae134d |
| `W/cmp_solo_vs_frzb1.json` | ad0b936dec7c911659b93a2ae200fd9d4a355faad976a568814e02ea76f03bc2 |
| `W/cmp_freeze_code.py` | 57206d035678a257e3e3c9334c48ff737d10489c6cd6fe8cf9bed7e8716da30e |
| `W/cmp_freeze_code.json` | f35c0b7ad2ed22b7167e59cba660668313f1b058fd6e610918e213af9f2cc670 |
| `W/solo_vs_frzb1_13files.diff` | d29cdb26578d8cc4c114a8ce04f9a419e35db8087ffeb16bb0c8c98a1088aeee |

| 읽은 근거 | sha256 |
|---|---|
| HO/HANDOFF.md | e2cef38c99ad22dfcd575581cec35a40c7c66c4891e9dd57abf9d0458c605b56 |
| HO/evidence/original_solo_FREEZE.json | f55ecec3bf442d5491b8f091abf800d05f5d2c1d76160dd44516ecf93b72f174 |
| HO/evidence/original_FREEZE.json (joint) | f980fcce97f4dfa207a39dfe5151e6b1c3c3775340a8ac70dac6fac40d45e2d0 |
| FRZ_B1/FREEZE.json | 558de2c1b80799a9bedfb192b40b6f5cfa2775853b3431eb181f7b25beca10d1 |
| codex freeway_only_config.json | cd193948e7267c40373ea9bcd92013f7ffe34dff36438239113db58b7d433778 |
| codex joint optimized_config.json | c90882628ddc75c0c75c9a82771c96a50614b297839ec32c506859a969dc1df3 |
| B 설정 config_b0_v3c3.json | 729640af754a90c8d7fbe8f81577b27bae02b86f1d504e18333c0fc99717f983 |
| FO provenance / joint provenance | 9efb542b4a64402b50d7c69c4accac2f6e248332bc3b08f25ff58d199d067aa2 / 40afc8223b79a6b6d181ff61dbeac474638f0472e56ab22e87b7733e4931d2cf |
| solo plan.json / FO control health | 8c2dfd323ff11c0d6ea5879d79112c38284bd276ec518be143a15e02f3884420 / e3bc00c17d0a600d4754de8c95d991bb2917bbe829c4f3e136cdf44b5157e307 |
| FO action CSV / FO execution.json | 4581afe173d9af54ef496b474638a60d6f075c8afaf98cf74e4ad379ab97143d / 33b7072d93a86c29f4652bbbc6b256535f72c14577563bd26dd17643f910a8c0 |
| HO/derived/metrics_0_8100.csv | a2757f7288ba3f0e0d91222c25d353c0f3f015af28e2f9ebdb594508e3cfc37a |
| PRE_B_CONCURRENT / B0 / COMPARE_RULE_B / B_RESULTS | 3d21dddd… / 11fa7578… / f902f7f0… / 152a2f6f… |
