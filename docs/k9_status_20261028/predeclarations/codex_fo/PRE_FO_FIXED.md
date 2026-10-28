# PRE_FO_FIXED — PRE_FO·동결·사전 점검·모의 실행 적대적 리뷰와 고침 (2026-10-27 20:36–21:05 KST, FO 데이터 0)

- 이 리뷰는 **FO 데이터가 하나도 없을 때** 했습니다: FO 관문 재생 0, FO VISSIM 런 0, `D:/VISSIM_runs/20261028_codex_fo_v3c3` 없음, `fo/gate` 없음 [실행 20:57 KST].
- 판정 낱말은 쓰지 않습니다. 표시: **[실행]** 명령으로 확인 · **[읽음]** 파일을 읽어 확인 · **[추론]** 시험하지 않은 판단 · **[계산]** 산술.
- SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`, FO = `SP/codex_handoff/fo`, FW = `FO/work`, RV = `FO/review`, FRZ_FO = `D:/VISSIM-merge/k8_gate_trees/codexhandoff/fo/frozen/sdmpc31_a49981ff_202610271954`, FRZ_B1 = `D:/VISSIM-merge/k8_gate_trees/codexhandoff/b1/frozen/sdmpc31_a49981ff_202610261410`. 증거는 이름 + sha256(64자는 `FO/PINS_FO.sha256` r2).

## 0. 줄임말 (처음 한 번)

- **FO** = codex SDMPC(분산 모형예측제어기)가 램프 미터만 정하고 도시 신호 17곳은 baseline(= v3c3 무제어 명령 값)을 다시 쓰기만 하는 v3c3 폐루프 런(D-K9-113, O2). **B** = 같은 codex 판이 도시 신호 + 미터를 정한 런. **NC3** = v3c3 무제어. **V-A** = 우리 묶음 B1 폐루프.
- **SC** = 신호 제어기(교차로 하나), **SG** = 신호 그룹(신호등 한 묶음), **COM** = VISSIM 을 바깥에서 움직이는 창구, **VSL** = 가변 제한속도.
- **G2** = 관문의 "FO 가 쓰는 도시 SG 일정 대 native 프로그램 GREEN 초" 대조. **V1–V9** = 런 뒤 점검. **readback** = 러너가 SG 상태를 쓴 뒤 다시 읽은 기록. **.lsa** = VISSIM 신호 상태 변화 기록. **LDP** = 신호 상태 초별 기록(codex 64cf 런에만 있음).
- **r1** = 리뷰 전 판, **r2** = 리뷰 고침 판.

## 1. 쉬운 답

1. [실행] **동결 트리는 선언대로입니다.** FRZ_FO 는 FRZ_B1 과 코드 13파일 바뀜 + 5파일 더함(새 모듈 4 + FO 설정)만 다르고, 그 17 코드 파일은 codex solo FREEZE 의 sha 와, FRZ_B1 쪽 13파일은 codex joint FREEZE 의 sha 와 바이트로 같습니다. 러너·B 설정은 바이트 같음.
2. [실행·읽음] **FO 는 도시 신호를 제어기가 고르지 않습니다.** 신호 green·offset 좌표가 아예 만들어지지 않고(`sdmpc.py:420`), 결정·3블록 계획·기준 명령이 baseline 에서 1e-9 넘게 벗어나면 예외입니다(`sdmpc.py:558`, `:931`, `sdmpc_sequence.py:196`, `sdmpc_actuator_scope.py:30-39`). 다만 900 s 부터 baseline 을 COM 으로 다시 쓰므로, 그 GREEN 초가 native 와 같은지는 관문 G2·런 점검 V4 가 봅니다.
3. [실행] **VSL 110 고정·미터 제어는 B 와 같습니다.** FO 설정 `sdmpc_fixed_vsl` = B, VSL 좌표 0(`sdmpc.py:462`), 미터 좌표는 B 기록과 같은 24개(미터 8 × 3블록)이고 미터 소유자는 FW_W·FW_E(`sdmpc.py:457` `ramp_to_freeway`).
4. **고친 것 넷**(§3): 런 점검 V1 이 B 보다 엄격하고 PRE_FO §12 와 어긋남 → B 규칙으로 맞춤; V4 가 "실현" 을 요청 글자로만 보고 쓰지 않은 SG 는 안 봄 → (d)(e) 더함; 작동기 범위 검사 때문의 유지를 잡는 칸이 없음 → V9(멈춤) 더함; 비교 규칙이 B 규칙의 진입 E·W 줄을 밝히지 않고 뺌 → 되살림.
5. [실행] **관문이 저절로 참·거짓이 되지 않음**: G2 에 v3c3 양성 대조를 더했습니다(codex 64cf 의 같은 baseline 행 → B v3c3 3시드 `.lsa` 와 136 SG 0 프레임 차). 음성 대조(B 최적 계획 → 122 SG 다름)는 r1 에 있었습니다. 요약 도구의 A6·A8 열쇠(`sdmpc_active`, `controller_status`, 지역 표지)는 B 기록에 실제로 있고/없음을 확인했습니다.
6. 남은 풀리지 않은 문제는 없습니다. 밝혀 둔 한계는 §4.

## 2. 요청한 점검별 결과

### 2.1 FO 는 정말 도시 native 인가 (제어기가 도시 SG 를 고르지 않나)

- [읽음] O2(작동기 범위만, information_scope 없음)의 코드 길: `sdmpc_actuator_scope.allows`(`:26-28`)는 freeway_only 에서 meter·vsl 만 허용 → 신호 green·offset 축 0(`sdmpc.py:420`). 축이 없는 소유자 17개는 QP 를 건너뜀(`sdmpc.py:1210`, `sdmpc_pfo.py:54`). 도시 저장 가드는 green 축이 없으면 제약을 만들지 않음(`urban_storage_guard.py:118-123`). 결정(`sdmpc.py:558`)·3블록(`sdmpc_sequence.py:196`)·기준 명령(`sdmpc.py:931`)마다 `check` 가 baseline 과의 차 > 1e-9 이면 `ValueError('Inactive urban actuator changed')`.
- [실행] baseline 값 85개(green 68 + offset 17)는 모두 정수 → 밀리초 반올림으로 다음 결정의 기준 명령이 어긋날 일 없음 [`RV/rv_cfg_diff.py` 와 같은 설정 읽기].
- [실행] **COM 쓰기 = native?** G2 양성 대조 `RV/rv_g2_pos.py` → `RV/rv_g2_pos_out.json`: codex 64cf T=900 baseline 행(`action_000900.csv` `71f32171…`) 대 B v3c3-s31·s41·s43 `.lsa` [2, 899]: 세 시드 모두 136 SG 0 프레임 차, 주기 17곳 같음, pass true. `.sig` 42개는 64cf 망 = FRZ_FO 망 바이트.
- [실행] **쓰지 않는 SG** (SC5 9–24·SC7 9–16 과 제어하지 않는 SC): B v3c3 3시드와 codex 64cf FO 런에서 900 s 뒤 `.lsa` 가 native 연장과 146 SG 0 프레임 차(`RV/rv_lsa_b.py`, `RV/rv_lsa64.py`). r1 의 V4 는 이 SG 들을 보지 않았습니다 → r2 V4(d).
- [실행] **`.lsa` 는 쓴 SG 에는 못 씀**: codex 64cf FO 런에서 쓴 122 SG 의 `.lsa` [1050, 8099] 는 LDP 와 290,691 프레임 다름, LDP 는 native 연장과 0 차(`RV/rv_lsa64_out.json`). COM 으로 정한 상태가 `.lsa` 에 안 남습니다. 그래서 쓴 SG 는 readback 으로만 봅니다(V4(c)); codex `execution.json` 의 "LSA 대조 passed=false" 와 맞음.
- [실행] readback 요청 = 읽음, ok 1: B v3c3 3시드 도시 행 49,553 / 49,631 / 49,314 행 어긋남 0, 64cf 41,264 행 0(`RV/rv_lsa_b_out.json`). r1 의 V4(c)는 요청 글자만 썼습니다 → r2 V4(e).

### 2.2 그 밖의 것은 B 와 같은가 (동결 트리 대조)

- [실행 `RV/rv_manifest_diff.py` → `rv_manifest_diff.out.txt`] FREEZE 표: FRZ_FO 7,994 / FRZ_B1 7,989; FO 에만 5(`config_fo_v3c3.json`, `sdmpc_actuator_scope.py`, `sdmpc_regional_context.py`, `sdmpc_regional_contracts.py`, `sdmpc_regional_prototype.py`), B1 에만 0, sha 다름 13(모두 `evaluation/controllers/`), 크기만 다른 것 0, exclusions·plan_subtrees 같음, git status 3,653 → 3,671(= 13 M + 5 ??).
- [실행 `RV/rv_solo_check.py` → `rv_solo_check.out.txt`] 18파일 디스크 sha = 표, 17 코드 = solo FREEZE(`f55ecec3…`), FRZ_B1 의 13 = joint FREEZE(`f980fcce…`) → 차분 = codex solo − joint 와 정확히 같음. 러너 `6ff68b38…`·B 설정 `729640af…` 두 트리 같음.
- [실행 `RV/rv_cfg_diff.py`] FO 설정 대 B 설정: 다른 잎 86 개 모두 `/adapter/sdmpc_actuator_scope` 아래, information_scope 없음, `sdmpc_fixed_vsl` 같음, 고속 경로 13칸 B 값 그대로, baseline = codex freeway_only 설정 값.
- [실행 `RV/rv_prov_diff.py`] FO 사전 점검 provenance 대 B 실제 런 provenance(경로 앞머리 맞춤 뒤), 세 시드 모두 다른 잎 = created_at, run_id, RW 설정 sha, adapter sha, 설정 경로·sha(tuning·두 config_chain), freeze sha, controller_sources(solo 17 + 새 4 로 목록 자리 밀림) 뿐. 선언과 같음.
- [읽음 13파일 차분 `FW/build/frzb1_to_fo_13files.diff` `643115b3…`] 키가 없을 때 막히지 않는 줄(`sdmpc_central` 가림 함수의 전부 참 가림, `joint_owner_neighbors` 의 `command_move_box=None`, `sdmpc_tangent_constraints`·`_surrogate`·`_worker` 의 region=None, `area_follower_objective` 의 `include_adapter_runtime=True`)은 B 와 같은 값을 냅니다. O2 에서 B 와 다른 것은 좌표 셋·검사·정책 토큰뿐(선언 M1–M6 과 같음).

### 2.3 VSL 110 고정

- [실행] 설정 같음, 좌표 0(`sdmpc.py:462`), 관문 A7(66행·JSON 110), 런 점검 V5(명령·vsl_readback 110). B 기록 JSON `vsl` 44칸 모두 110 [실행].

### 2.4 미터는 여전히 제어됨

- [실행] B 기록 T=900·1050·4500·8850 세 시드 모두 좌표 {green 138, offset 51, meter 24}; FO 는 green·offset 0 에 meter 24 를 기대(관문 A6). A6 의 `controller_status`·`sdmpc_active` 열쇠는 B 기록에 실제로 있음(ok, True) → 저절로 거짓 아님. 미터 실행은 V3(8 × 810 주기 readback = 명령, B 에서 어긋남 0).

### 2.5 관문이 저절로 참·거짓이 되지 않는가

| 칸 | 저절로 참이 아님 | 저절로 거짓이 아님 |
|---|---|---|
| A5 (신호 = baseline) | B 기록 넣으면 거짓 [r1 자기 시험] | baseline 은 B t=750 명령과 차 0, check 는 1e-9 |
| A6 (미터만 좌표) | B 기록 → 거짓 | 열쇠 있음, meter 24 = B |
| A8 (표지) | B 기록 → 거짓 | B 기록에 지역 표지 13종 0개 [실행 4개 T × 3시드], 정책은 설정 값뿐(경로 없음) [실행] |
| C4·C5 (R0) | — | B 기록 넣으면 참; 산 결정 CSV 는 쓴 뒤 안 바뀜(`.applied` 의 크기 28,349 = 파일) [실행], 결정 시한 없음(`unlimited_time` true) |
| G2 | 음성 대조 122 SG 다름 | **r2 양성 대조 136 SG 0 차** |
| V4(d) r2 | 쓴 SG 까지 넣으면 3시드 122 SG 다름 [실행 `RV/rv_runcheck_neg.py`] | B 에서 146 SG 0 차 |
| V1·V9 r2 | 범위 원인 유지 든 합성 로그 → V9 거짓 | B 3시드 V1·V9 참 |

### 2.6 발사기 자리 규칙과 5 분 정책

- [읽음] 자리: PC 전체 `^Vissim` 수 + 우리 대기 런 < 4 일 때만, 잠금 아래 다시 셈(`fo_launcher.ps1:442`, `:455`, `$CAP = 4` `:61`), 대기 = VISSIM 이 아직 안 뜬 우리 런(`:295-299`), 러너 자체 4자리 거부. 우리 FO 런은 시드 셋뿐이라 최대 3. 남의 VISSIM 은 세기만 함. 이름으로 끄는 줄 0 [실행 grep].
- [읽음] 끔: `fo_stall_stop.ps1` 는 영수증의 래퍼 PID + 생성 시각이 맞을 때만 그 자손과 워치독이 적은 VISSIM PID(생성 시각 대조)를 모아(`:77-89`) 그 PID 만 멈춤(`:109-111`). 러너 워치독은 `kill_policy=pid_only no_global_kill=True` [읽음 B s31 `launch.log`].
- 방아쇠 499 s + CPU 확인은 PRE_B_CONCURRENT §7-1·7-2(B 때 정함)와 같습니다. 모의 실행 17/17·7/7 [실행 로그 확인]. r2 에서 감시 주체(세션, 끊기면 StallSec 3,600 이 마지막 망)와 이름 바꾸기 실패 → 멈춤을 밝혔습니다.

### 2.7 비교 규칙이 다 갖췄나

- [읽음] Ω701·④·Ω 밖 (a)(b) 함께, ④b 첫 관측 차분 주 값, 도시도로 codex 분할만, FW_E 주·FW_W 감시, GREEN 만, 시드별·평균 없음, B − FO = 고정 B 출력과의 [계산], X3·X3b 멈춤 — 모두 있음.
- 빠졌던 것: COMPARE_RULE_B §4-2 의 진입 E·W 줄(codex 규칙 M). FO 는 미터만 움직이므로 미터 몫이 처음 보이는 곳입니다 → r2 §5-9 로 되살림(도구 안 바꿈, 고정 M 출력에서 [계산]).
- "쓸 수 있는 런" 이 B 와 달랐음 → r2 §1 에서 B 와 같게.

## 3. 찾은 것과 고침

| # | 무게 | 찾은 것 | 고침 | 근거 |
|---|---|---|---|---|
| R1 | 중 | 런 점검 V1 이 `DECISIONS_FAILED=0`·error.txt 0 을 요구 → 예외 유지 1회면 그 시드 전체 "못 냄". B 규칙(COMPARE_RULE_B §1: SIM_DONE·9000 이면 쓸 수 있음, 유지는 보고)보다 엄격하고 PRE_FO §12·PRE_B_CONCURRENT §7("예외 유지는 설계된 동작")과 어긋남. VBS 는 유지 때 failed·held 를 함께 늘리고 error.txt 를 요구함(`run_real_world_stackelberg_controller.vbs:714-724`, `:1289-1297`) [읽음] | V1 = runner_exit 0, SIM_DONE, SIM_SEC 9000, failed = held_on_exception, error.txt 수 = held. 유지 T·원인 보고, 표 머리에 적음 | `fo_run_check.py` r2, COMPARE_RULE_FO r2 §1 |
| R2 | 중 | O2 특유의 실패(범위 검사 예외 → 유지 → 그 구간 미터 고정)를 잡을 칸이 없음 | V9: 유지 원인·error.txt 에 범위 검사 글자 5종이 있으면 멈춤 | 같음, PRE_FO r2 §7·§9 |
| R3 | 중 | V4(c)는 readback 요청 글자만 펼침(실제 읽은 값·ok 무시), 쓰지 않은 SG(제어 SC 안 24개·제어하지 않는 SC)는 900 s 뒤를 안 봄 | V4(d) FO `.lsa` 로 쓰지 않은 SG = native, V4(e) 도시 readback 요청 = 읽음·ok 1. B 3시드 자기 시험: (d)(e) 참, (c) 거짓(최적 계획) | `FW/ana/selftest/runcheck_r2_on_b_s*.json` |
| R4 | 하–중 | 비교 규칙 r1 이 B 규칙 §4-2 의 진입 E·W 줄을 밝히지 않고 뺌 | r2 §5-9 로 되살림 | COMPARE_RULE_FO r2 |
| R5 | 하 | G2 의 v3c3 양성 대조 없음(64cf 망에서만) | `RV/rv_g2_pos.py` 로 얻어 PRE_FO r2 §5.3 에 적음 | §2.1 |
| R6 | 하 | 멈춤 확인을 누가 언제 돌리는지, 이름 바꾸기 실패 때 무엇을 하는지 없음 | PRE_FO r2 §6·§9-9 에 밝힘(도구는 그대로) | — |
| R7 | 알림 | 발사기·래퍼·상태 스크립트 머리 주석에 B 이름(FRZ_B1, b_launch, b/dryrun)이 남음. 실제 값은 FO 것 [읽음 `fo_launcher.ps1:15`, `:18`, `:31`, `fo_wrapper.ps1:3-13`, `fo_status.ps1:5`, `:12`] | 고치지 않음(모의 실행으로 검증한 sha 유지), PRE_FO r2 §6 에 적음 | — |

## 4. 고치지 않고 밝혀 둔 한계

- R0 의 C5 가 다르면(HOLD) "덮기가 B 를 바꿈" 과 "재생이 산 결정을 재현 못 함" 을 가르지 못합니다. FRZ_B1 위 대조 재생은 코드 뿌리 안 캐시(`__tangentcache__`, numba)를 써서 동결 트리를 바꾸므로 하지 않습니다(VERIFY_B R12 [읽음]). HOLD 는 그대로 멈춤.
- 499 s + CPU 확인은 사용자의 "5 분 무진행" 을 B 때 정한 꼴로 옮긴 것입니다. CPU 가 도는 채로 멈춘 런은 StallSec 3,600 의 워치독이 끕니다(이상 종료, 재발사 없음). B 와 같음.
- 워밍업(t=1–750) 무제어 결정은 FO 설정으로 미리 돌리지 않았습니다(재생 도구가 지원 안 함). 깨지면 런 첫 몇 분에 이상 종료로 드러납니다 [추론].
- NC3 의 s41·s43 망 sha(`726af589…`, `51478c39…`)는 B·FO 망(`3de889f0…`)과 다릅니다. B − NC3 와 같은 조건이며 COMPARE_RULE_B §1 의 † 접두 규칙으로 다룹니다(새 문제 아님) [읽음 PRE_FO §4].
- G2·V4 는 GREEN 초만 봅니다(사용자 규칙). 노랑·적색, COM 쓰기 자체의 VISSIM 내부 효과는 보지 않습니다.

## 5. 최종 sha256 과 시각 (2026-10-27 21:05 KST)

| 파일 | r2 (지금) | r1 (남김) |
|---|---|---|
| `FO/PRE_FO.md` | `743909fd95374568e1679f965f42e565fbe74d7486c04d4d446b26ed4691b210` | `PRE_FO_r1.md` `9a83dbaff52701f478b30f04e78d073b7ebcebf59cfb0ecda194905c7357b2fa` |
| `FO/COMPARE_RULE_FO.md` | `7ef1b03da6492de3c077e349086f6125fe4ac0e2673359bf1949bc185640c5c8` | `COMPARE_RULE_FO_r1.md` `d5a47e8dd7922121adcc9847f7a051e093525d4cdfe482ce84a7a7f72c62e9c0` |
| `FO/PINS_FO.sha256` (154줄, `sha256sum -c` 154/154 OK [실행]) | `314d51dc5006ee65f3913940f2e7064b19f1a43d2d50e3c7df049ef7760cae66` | `PINS_FO_r1.sha256` `5458c623ae3a19afc0db9f07f56bd9bb142ac56c78f48cffdc75cc710204723e` (124줄) |
| `FO/pins_list.txt` | `fcd8cd30be61c50b3b6d400ac8519e1298ca6d37053c37b2eec5a7bd77fc5820` | `pins_list_r1.txt` `a779cf485c72789027d71dd67ac7193122439932e5c1ec418889619ac7c0b152` |
| `FW/ana/fo_run_check.py` (ASCII, 구문 확인) | `1415cddcfe5029e036245c4da5278b913e14c605ed1faf148d225afa659937c9` | `fo_run_check_r1.py` `acfd805b539f9b98f9a2b1875af29d78093366a09c996c866c8a6271e9326465` |
| r2 자기 시험 `FW/ana/selftest/runcheck_r2_on_b_s31/41/43.json` | `11c218c3…` / `978c7c50…` / `14e8f708…` | — |
| 리뷰 탐침·출력 `RV/*` 19개 | PINS_FO r2 의 마지막 19줄 | — |

- 바뀌지 않은 것 [실행 sha 다시 셈]: FRZ_FO FREEZE `d7fa4db6c3ca854a3c6c7dfd352f97626d6f9ca9d0e5ea6f18e36fc779d37373`, FO 설정 `80e0abefdb25526374c97d8f7a6b45b9ad434db1f3499cec208985038ac249f3`, 관문 도구(`fog_build_inputs.py` `e9741850…`, `fog_replay.ps1` `b8eda978…`, `fog_queue.ps1` `d015a692…`, `fog_summary.py` `7ac04cd5…`, `fog_sg_native.py` `751e1e4c…`), 발사기 `fo_launcher.ps1` `e73990d0…`·`fo_wrapper.ps1` `b79f38ac…`·`fo_launcher_start.ps1` `b9994d2c…`·`fo_stall_stop.ps1` `961bc521…`, 분석 `fo_ana.ps1` `543a6d16…`·`fo_tables.py` `0520e1b3…`·`fo_fwe.py` `4e46b138…`.
- 고정 sha 파일: `PRE_FO.md.sha256`, `COMPARE_RULE_FO.md.sha256`, `PINS_FO.sha256.sha256` 을 r2 값으로 다시 씀. r1 의 sha 파일은 `*_r1.*.sha256` 로 남김.

## 6. 다음 걸음 (바뀌지 않음, sha 만 r2)

1. T=900 관문 큐: PRE_FO r2 §5.1 명령 그대로(`fo_launch_wmi.ps1 -Script FW/gate/fog_queue.ps1 …`). 통과 못 하면 멈추고 보고.
2. 통과 뒤 사용자 발사 허락이 있으면: `fo_launcher_start.ps1 -LauncherSha e73990d0da6dac7603be9959acca063cacbc0b3f033b8cf0336d351c31ffd02b -WrapperSha b79f38ac97336ed944e431c2fb43d23a7665851ce0c4a49456b6643f2038b019 -PreSha 743909fd95374568e1679f965f42e565fbe74d7486c04d4d446b26ed4691b210 -RuleSha 7ef1b03da6492de3c077e349086f6125fe4ac0e2673359bf1949bc185640c5c8 -PinsSha 314d51dc5006ee65f3913940f2e7064b19f1a43d2d50e3c7df049ef7760cae66 -GateSha <관문 요약 sha>`.

## 7. 이 리뷰에서 한 일·안 한 일

- 한 일: 파일 대조·코드 읽기·작은 기록 파일 읽기(.lsa 2.5 MB, readback, 명령 CSV/JSON, provenance), 탐침 8개, 런 점검 도구 r2 와 그 자기 시험, 문서 r2, 핀 r2, LOG 항목, 보고 사본.
- 안 한 일: VISSIM·COM 0, 관문 재생 0, FZP 읽기 0(무거운 일 0, 공용 잠금 사용 0), 남의 프로세스 손댐 0(VISSIM 30964 그대로), kill 0, `D:/VISSIM-merge/frozen/*`·FRZ_B0·FRZ_B1·V-A·K92·FRZ_FO·GWT8·codex 작업 트리 쓰기 0, `sealed/`·봉인 시드·v3c3-s47 값 0, 금지 시험 0, 커밋·푸시 0.
