# v3c2 재핀 계획 — SDMPC-31 핀을 v3c1에서 v3c2(+단일값 VSL 분포)로 옮기고 J1 전 결함을 함께 고치는 일

- 작성 2026-10-01. **계획만 세웠습니다.** 저장소·망·git·VISSIM은 건드리지 않았습니다. 쓴 곳은 `D:/VISSIM_runs/20260930_v3c2/reports/repin/` 하나입니다.
- 기계 판독 목록: `repin_v3c2_inventory.json` (항목 52개: 파일·줄·현재 값과 sha256·새 값 또는 유도·증명 시험).
- 근거(모두 읽기 전용): `_evidence/e1_characterize.py·.json`, `e2_fcb_sections.py·.json`, `e3_v3c3_preview.py·.json`, `build_inventory.py`.
- 줄 번호 기준: `D:/VISSIM-merge/sim3-n31-v3c1` @ `9ed2ef0` (브랜치 `claude/repin-v3c1-20260928`, `git status` 0줄 [실행]). `N31D` = `diagnostics/sdmpc_n31_20260924`.
- 템플릿: v3c1 재핀(`D:/VISSIM_runs/20260927_v3c1/reports/REPIN_PLAN.md`, 커밋 `5323faa`, `N31D/REPIN_V3C1_REPORT.md`, P10 `scratchpad/v3c1-p10/`).
- 표기: **[실행]** 이번에 직접 돌려 얻은 값 · **[읽음]** 파일·코드에서 확인 · **[추론]** 시험하지 않은 판단.

---

## 0. 요약

1. **v3c2 그대로는 단일값 VSL을 쓸 수 없습니다.** 망에 분포 81/91/101이 없어서 러너 검사가 거부합니다(`repin_scenario_v2.py:876-877`) [실행 e1 E4].
   - 그래서 재핀 대상 망은 **v3c2 + DSD 블록 3개**입니다. 블록은 N1F 2단계 바이트 그대로이고 +655 B입니다. 이 문서는 이 망을 **v3c3**이라 부릅니다(이름은 U1).
   - 6시드 예상 sha를 메모리 안에서 재현했습니다. s31은 `3de889f0…`입니다. 새 번호를 정적으로 참조하는 요소는 0개이고, 시드 파일끼리는 randSeed 한 줄(31013)만 다릅니다 [실행 e3].
   - NC 궤적이 그대로라는 것은 **v3c3 NC FZP payload = v3c2 NC 같은 시드**(바이트)로 증명합니다(GB-1). 사전 근거로, N1F는 v3b에 같은 블록을 넣은 8런에서 2,750 s까지 NC와 FZP가 같았습니다(G0 8/8) [읽음].
2. **재핀 도구는 v3c2부터 거부합니다** [실행 e1 E1, e2].
   - `vehicleCompositions` 절이 CHANGE_RULES(`repin_scenario_v2.py:303-315`) 밖에 있습니다.
   - 1098/1099의 vehComp 변경도 "volume only" 규칙 밖입니다.
   - v3c1처럼 **열거표**로만 받습니다: 구성 14 블록 sha, vehComp 12행, DSD 3블록. CHANGE_RULES는 넓히지 않습니다.
3. **단일값 VSL 사상.** 명령 공간은 {80,90,100,110} 그대로입니다(튜닝·reference·SDMPC 축·action JSON). CSV에 쓸 때만 80→81, 90→91, 100→101, 110→110으로 바꿉니다.
   - 사상은 어댑터 writer에 둡니다(U3). 러너 허용 목록은 `81,91,101,110`이 됩니다. **러너 VBS 코드는 바꾸지 않습니다.**
4. **plant 법칙 L2.** Carlson A 1.33 / E 0.87에 측정 속도 척도 m_v(80 0.72252, 90 0.81198, 100 0.90068)를 더합니다(fit_results `4091d6e1`). `speed_scale` 키가 없으면 비트 동일합니다.
   - 수준 사이 보간은 **(80, 90, 100, 110=1) 네 점을 지나는 3차 Lagrange**를 권합니다(U4).
   - 이유: 세 수준에서 정확하고, 110에서 연속이며, 매끄럽습니다. 그래서 T9(80·90·100 중앙차분 1e-4, 110 한쪽 도함수)를 통과할 수 있는 것은 아래 세 후보 가운데 이것뿐입니다 [실행 계산, 통과 여부는 추론].
   - 다른 후보의 문제: 2차식과 직선은 110에서 값이 끊깁니다(0.9886, 0.9898). 구간선형은 100에서 기울기가 12 % 꺾입니다.
5. **RM_C10490 일반 수정.** 설치할 때 서비스표를 정규화해, 같은 서비스를 내는 녹색 그룹에서는 한 녹색만 남깁니다.
   - 권고는 **가장 낮은 녹색 유지**입니다. 10490은 {0, 2, 4..10}이 됩니다(U6).
   - hybrid 방식(둘 다 빼서 {0, 4..10})은 ±2 s 상자 안에서 4 → 0으로 가는 길이 없어 폐쇄가 막힙니다 [추론].
6. **J1 전 결함 수정.**
   - `state.py:1306`의 합산 순회를 sorted로 바꿉니다.
   - `make_replay_state_v2.py:234-242`의 action_contract를 허용 집합 소속 검사로 바꿉니다.
   - 코덱스 검토의 잠복 결함 가운데 **조용한 무시 설치 검사(E2)만** 넣기를 권합니다. L2가 새 키를 들이기 때문입니다.
   - state_response 인덱스 순서 수정은 필요 없습니다. reference에 state_response가 없습니다 [실행 grep].
7. **순서.**
   - 결함 수정 K1–K6을 v3c1 기반에서 먼저 커밋하고, v3c1 자료로 동일성 관문(GA)을 통과시킵니다.
   - 그 위에 재핀 K7을 얹습니다.
   - 이어서 R-obs v3c3를 돌리고 P10(GB)을 합니다.
8. **런.** v3c3 NC 6개(fit 5 + s37 봉인), RM 3팔(s31/s41 + s37 봉인), R-obs 1개입니다. 최대 4석, WMI, 메인 세션이 발사합니다.
   - **공수**는 약 22–28 에이전트·시간, **벽시계**는 약 20–24 h입니다. VISSIM 런은 코드 작업과 병행해 대부분 가려집니다(§9).

---

## 1. 범위

**넣는 것**
- 망 v3c3 = v3c2 + DSD 81/91/101. NC 동일성 증명과 RM 팔 망도 포함합니다.
- SDMPC-31 재핀 v3c1 → v3c3입니다. 대상은 v3c1 목록 48항목과 같은 종류이고, v3c2 전용 항목(구성·vehComp 열거)이 더해집니다.
- 단일값 VSL 채택 묶음(사용자 결정 09-28·09-29):
  - 명령 → 분포 사상
  - L2 법칙
  - 러너 허용 목록
  - 시험·문서
  - L1 분포형 가족을 선택 가능하게 두는 방법(U5)
- RM_C10490 서비스 유일성의 일반 수정
- `state.py:1306` sorted
- action_contract 소속 검사
- (권고) E2 조용한 무시 설치 검사

**넣지 않는 것**
- **F10/F11**(입구 속도 경계, FW_W ρc; 브랜치 `claude/fw-inlet-wcap-20260930`).
  - 셀 0 행 v_free 85.97은 그대로 둡니다. 별도 결정 대기 중입니다.
- **도시 묶음 2**(C3 = U4+U5+U6, C2, C6). 키는 없는 상태로 둡니다. 묶음 2는 C3 v2 통과 뒤에 이 브랜치로 옮깁니다.
- hybrid 규칙(`freeway_rule_hybrid.py`, `adapter.sdmpc_freeway_rule`)과 그 브랜치의 10490 코드. 옮기지 않고 일반 수정으로 대체합니다.
- state_response 인덱스 순서, `physical_cell_fd` 설치기. 둘 다 이 트리에 읽는 곳이 없고, E2 검사가 "있으면 거부"로 막습니다.
- 64cf DSD 110 내용(75–145), 램프·HGV 분포, FW_W VSL 법칙
- J1 폐루프, RM 5라운드, P(붕괴 전 VSL). 각각 자기 사전 등록이 필요합니다.
- s37/59/61/67 결과 열람
- v3c1 계획의 열린 항목은 그대로 둡니다: U1 area 계약 옛 사본 1061/1128:2/1124(D5), SC7 E 1102, V2 1161.

---

## 2. 망 쪽

### 2.1 v3c2에서 확인한 것 [실행]

- **v3c1 → v3c2 절 차이**(e1 E2): `vehicleCompositions` +14, `vehicleInputs` changed 1098/1099. 이 둘뿐입니다.
- **v3c1 결정 블록**(1159 뒤 9293 B, `2b77ab01`)은 v3c2에서도 바이트 그대로입니다. `added_block_audit`이 통과합니다(E3).
- **fcb349d3(팩 망) → v3c2 절 목록**(e2): CHANGE_RULES 밖의 절은 `vehicleCompositions` 하나입니다. 1098/1099는 12구간에서 volume과 vehComp가 함께 바뀝니다. 그래서 구성 규칙을 더해도 vehicleInputs 규칙에서 다시 걸립니다.
- **분포**: 44개이고, 81/91/101은 비어 있습니다.
  - 정적 DSD 참조는 110뿐입니다: desSpeedDecisions 304, 구성 14의 3행(E5).
  - 구성 14가 DSD 110을 쓰므로 "110 = VSL 꺼짐 = NC 분포 98–140"이 입구 차량과도 맞습니다 [읽음 `V3C2_BUILD.md` §1, 추론].
- **대조군**: 같은 검사를 v3c1에 돌리면 통과합니다(E1_control) [실행].

### 2.2 DSD 81/91/101을 어디에 넣나 — 선택지

| 안 | 내용 | 판단 |
|---|---|---|
| **A (권고)** | **새 이름 v3c3** = v3c2 + 3블록 | v3c2 채택 결정(`DECISION_v3c2_adopt.md` `de71def6`), v3c2 sha 표, NC 관문 기록이 그대로 참으로 남습니다. 망 편집이 두 단계로 따로 증명됩니다 |
| B | 같은 이름 v3c2에 접기 | 권하지 않습니다. 같은 이름이 다른 바이트를 가리키게 되어, v3c2 sha 표·NC 런 핀·관문 기록이 거짓이 됩니다 |
| C | 러너가 실행 중 분포 추가(COM) | 불가능합니다. 실행 망이 핀된 망과 달라집니다(NETCOPY sha 검사) |
| D | 기존 번호 재사용 | 불가능합니다. 단일값(±1) 분포가 없습니다(E5) |

### 2.3 v3c3 빌드 규칙 (N-1, N-2, N-3)

- **블록**: `D:/VISSIM_runs/20260928_n1f_vsl_stage2/plan/n1f_plan_stage2_v1.json`(`d0e8fdba`)의 `dsd_blocks`
  - 81: 217 B `ae06360d`
  - 91: 217 B `fbb7066f`
  - 101: 221 B `f3d776c2`
- **위치**: 분포 80/90/100을 닫는 줄 바로 뒤입니다.
  - 삽입 전 오프셋은 805021/805613/806042입니다. N1F(v3b)와 같은 자리입니다. v3c1·v3c2의 편집은 모두 이보다 뒤(31195행 이후)에 있기 때문입니다 [실행 e3].
- **스크립트**
  - `v3c3_build.py`: `v3c2_build.py`(`5dae8984`)의 틀에 N1F 삽입 규칙을 얹습니다. 세 구성법(텍스트 / ElementTree / s31 randSeed 교체)이 바이트까지 같아야 합니다.
  - `v3c3_prepare.py`: `v3c2_prepare.py`(`b91153fc`)를 복사하고 경로만 바꿉니다. `prepare_native_preserve(net, out, 9000, recording_interval_sec=5, fzp_only=True)`입니다.
  - 영수증 `v3c3_edit_receipt.json`을 남깁니다.
- **예상 sha** [실행 e3, 메모리 안 재현. 실제 빌드가 같은 값을 내야 합니다]

| 시드 | 역할 | v3c2 | v3c3(예상) |
|---|---|---|---|
| 31 | fit | 597191ac | **3de889f0** |
| 41 | fit | 2b15d51e | 726af589 |
| 43 | fit | e11d19f2 | 51478c39 |
| 47 | fit | 99689b7f | 1895ca30 |
| 53 | fit | c2dd1a48 | 095fb701 |
| 37 | 봉인 | f6b0b7d6 | 7edf0f7a |

### 2.4 NC 궤적 무변화 증명 (GB-1, U2)

- **정의**: 아래 셋이 모두 성립해야 합니다.
  - v3c3 NC 시드 s의 FZP payload sha(헤더 뒤 행) = v3c2 NC 같은 시드의 payload sha. 예: v3c2 s31은 `8be8b274…`입니다 [읽음 `nc_analysis/eo/s31_v3c2nc_extraction_receipt.json`].
  - 로드 `.err`와 `VISSIG_Controller.dll.err`가 바이트까지 같음
  - run.json: completed, exit 0, terminal 9000
- **권고 범위 U2-a: fit 5시드 전부**
  - 이유: plant 기하·포트 프로필·램프 예측·U3 검증의 망 핀이 모두 v3c3 런에서 나와야 핀이 한 망으로 닫힙니다.
  - 특히 `_load_sources_v2`는 기하의 망 sha가 plant 망 sha와 같아야 통과합니다(`lane_plant_runtime.py:87-89`) [읽음].
  - 비용은 벽시계 약 3.3 h(2묶음)이지만 K1–K6 작업과 겹칩니다.
- **축소안 U2-b**
  - s31만 돌립니다(기하·포트 프로필 추출용으로는 반드시 필요).
  - 41/43/47/53은 v3c2 NC FZP와 추출을 그대로 쓰고, 출처에 "GB-1 s31 + N1F G0 근거로 궤적 동일"을 적습니다.
  - 벽시계는 약 1.6 h 줄지만, 입력 핀이 두 망에 걸칩니다.
- **s37**
  - v3c3 s37 망은 바이트 규칙으로만 만듭니다. NC s37은 봉인으로 돌립니다(RM s37의 짝).
  - FZP 해시만 출력하는 동일성 도구를 허용할지는 U2-c입니다. 허용하지 않으면 run.json의 completed·exit_code 두 필드만 봅니다.
- **실패 시**: STOP합니다. 재핀·RM·R-obs는 발사하지 않고 사용자에게 보고합니다.

### 2.5 RM 팔 망 (N-6)

- `build_v3c3rm.py`는 `D:/VISSIM_runs/20260927_v3c1/rm_build/build_v3c1rm.py`의 레시피를 따릅니다. 세 구성법이 시드마다 바이트까지 같아야 합니다.
  - (b) v3c3nc 망 + v2rm의 RM 전용 3절(`dataCollectionMeasurements`, `dataCollectionPoints`, `evaluation`) — 기준 구성
  - (a) v2rm 사슬 + 경로 절 + 구성 14 + 1098/1099 vehComp 12행 + DSD 블록
  - (c) v3c1rm + v3c2 편집 + DSD 블록
- 주의 [추론]: 사슬의 `make_demand_variant 1099`는 volume만 바꿉니다. 그래서 (a)에는 vehComp 12행을 따로 얹어야 합니다. 빌드 때 확인합니다.
- `rule_runtime.txt`의 python 경로가 살아 있는지 확인합니다(memory `vissim-prepared-folder-absolute-paths`).

---

## 3. 코드 쪽 (커밋 K1–K7, 한 브랜치)

- **작업 트리**: `git -C D:/VISSIM-merge/sim3-n31-v3c1 worktree add D:/VISSIM-merge/sim3-n31-v3c3 -b claude/repin-v3c3-20261001 9ed2ef0` (이름은 U12)
  - `frozen/*`, hybrid, f10f11, termcost, urban-b2 작업 트리는 건드리지 않습니다.
- **커밋을 나누는 이유**: K1–K6은 망과 무관합니다. 그래서 **v3c1 자료로 먼저** 동일성을 증명할 수 있습니다(GA). 재핀 K7의 diff가 결함 수정과 섞이지 않습니다.

| K | 내용 | 파일:줄 | 키가 없을 때 | 관문 |
|---|---|---|---|---|
| K1 | 합산 순회 정렬 | `vendor/NumSim-mine/src/models/state.py:1306` | (무조건) | GA-1, GA-2 |
| K2 | 재생 action_contract 소속 검사 | `N31D/tools/make_replay_state_v2.py:234-242, :245, :300, :320-330`, `N31D/tools/n31_common.py:213-218` | 전부 110이면 판정 동일 | pytest(신규), GA-1 |
| K3 | 서비스표 정규화(10490) | `evaluation/controllers/physical_ramp_branches.py:33-78`(표 :77), `lane_plant_runtime.py:482-486` | (무조건. 옛 코드가 죽던 상태에서만 달라짐) | R-4, GA-3, GA-4 |
| K4 | L2 `speed_scale` | `evaluation/controllers/freeway_fd.py:19-46, :49-71`, `physical_lane_groups.py:211-212` | 비트 동일 | `tests/test_literature_vsl_fd.py`, T9 |
| K5 | writer 사상 + VSL 가족 일관성 검사 | `vissim_stackelberg_adapter.py:12618-12675`(:12651-12653, :12657, :12666), `runtime_setup.configure_runtime`, `N31D/tools/launch_plan.py`, `make_config_n31` 검증 | 항등 사상 = CSV 비트 동일 | GB-10, 음성 시험 |
| K6 | E2 조용한 무시 설치 검사 | `lane_plant_runtime.py:97-101`(`_load_sources_v2`) | 지금 reference는 통과 | GA-1 |
| K7 | 재핀 v3c3 | C-1…C-11, V-3/4/6/10/12, N-4/5 (목록) | — | GB-0…GB-12 |

### 3.1 K1 — `state.py:1306` (H-1, H-2)

- **변경**: `for storage_link in set(net.off_ramp_storage_link.values()):` → `sorted(set(...))`
- **근거**: T5가 4050·4500에서 예측 진단 4필드(off_ramp_storage_veh 2개, terminal_features.ramp_vehicles/stopped_vehicles)의 1–2 ulp 차이를 PYTHONHASHSEED로 재현했습니다 [읽음 `T5_REPORT.md:21`, `P10_VERIFY.md:104-108`].
- **같은 모양의 다른 곳 [실행 grep]**
  - `vissim_stackelberg_adapter.py:4457`: 집합 합집합 순서로 dict를 만듭니다.
  - `urban_queue_model.py:1424`, `distributed_coordinator.py:3537`
  - 이번에는 **고치지 않습니다.** 해시 시드 A/B 관문(GA-2, GB-7)이 차이를 보이면 STOP하고 사용자 결정을 받습니다.
- **vendor 수정 전례**: `b51791c`가 있습니다. 사용자 결정 항목이므로 범위 안입니다.

### 3.2 K2 — 재생 action_contract (P-1, P-2)

- **지금**: `speeds == [max(vsl_set)]`, 즉 VSL이 전부 110이어야 통과합니다(`make_replay_state_v2.py:240`).
- **바꾼 뒤**
  - VSL 행의 값이 모두 **"쓰는 허용 집합"** 안에 있어야 합니다. 쓰는 허용 집합 = 튜닝 vsl_set을 튜닝의 사상(`actuation.vsl_command_distribution`, 없으면 항등)으로 옮긴 상입니다.
  - 그 집합이 튜닝 트리의 러너 상수 `RW_ALLOWED_VSL_SPEEDS`와 같아야 합니다.
  - 행 수 66/8은 그대로입니다. `--vsl-expected`는 단일값 단언용 선택 인자로 남깁니다.
- **헬퍼**: `n31_common.effective_vsl_written_set(tuning)`을 더합니다.
- **시험**: 새 pytest 파일을 만듭니다(`test_tools_replay.py`는 금지이므로 건드리지 않음).
  - 통과: {110}, {91,110}
  - 거부: 단일값 가족에서 {90}, {120}
  - 행 수 오류

### 3.3 K3 — RM_C10490 서비스 유일성, 일반 수정 (R-1…R-5)

- **결함**
  - 설치된 10490 표는 녹색 2와 3이 둘 다 1.0 veh/주기(360 veh/h)입니다(`config_n31_v2.json:8036`, `reference_config_n31_v2.json:8000`).
  - 디코드(`physical_ramp_branches.py:358-360`)는 서비스 값 → 녹색 역산이 유일하지 않으면 거부합니다.
  - SDMPC 리더 씨앗(`:365-407`)은 적용 녹색 ±2 s 격자를 모두 디코드합니다. 그래서 10490 적용 녹색이 0·4·5면 결정이 죽습니다 [읽음 `92fa4b8` 메시지, 실행 사례 hybrid s31 3000 s].
- **수정**: 서비스표가 만들어지는 두 곳 뒤에 한 함수를 둡니다.
  - 두 곳: 측정 곡선 `lane_plant_runtime.py:482-486`, 수송 표 `physical_ramp_branches.py:77`
  - 함수: `physical_ramp_branches.normalise_service_table(table)`. 같은 서비스 그룹에서 한 녹색만 남깁니다.
  - 권고 규칙은 **가장 낮은 녹색 유지**(U6)입니다. 같은 측정 서비스를 가장 짧은 녹색으로 냅니다. 10490은 {0, 2, 4..10}이 됩니다.
  - 버린 녹색과 규칙은 configure 메타데이터에 기록합니다.
  - 정규화 뒤에도 유일하지 않거나, 최대 서비스 녹색이 빠지면 configure에서 거부합니다.
- **디코드 거부는 그대로 둡니다**(fail-closed). 표를 읽는 곳(`sdmpc.py:325-331`, `joint_owner_neighbors.py:1085-1106`, `sdmpc_continuous.py:85-100`, `lane_coupling.py:73-77`, `diagnostic_profile.py:299-321`, 어댑터 `:11615`)은 정규화된 표만 봅니다. 코드 변경은 없을 것으로 봅니다 [추론, R-4로 확인].
- **왜 hybrid 규칙(둘 다 제외)이 아닌가 [추론]**
  - {0, 4..10}이면 ±2 s 상자에서 4 → 0이 불가능합니다. 0에서 출발하면 {0}에 갇힙니다.
  - 가장 낮은 녹색을 유지하면 0 ↔ 2 ↔ 4 경로가 남습니다.
  - hybrid 코드는 옮기지 않습니다. 그 브랜치를 나중에 합치면 hybrid의 공유 서비스 분기는 할 일이 없어집니다(위험 R6).
- **동일성**: 적용 녹색 ±2 s 안에 공유 녹색이 없는 모든 상태에서, 표·격자·축·디코드가 옛 코드와 같습니다. 10490이 아닌 7개 표와 수송 표는 `==`입니다. 공유 녹색이 상자에 있는 상태에서는 옛 코드가 죽었으므로 비교할 옛 동작이 없습니다.
- **시험(R-4)**
  - hybrid `SharedServiceTests`(`92fa4b8:N31D/tests/test_n31_hybrid_rule.py:509-720`)의 의도를 일반형으로 옮겨 `diagnostics/test_physical_ramp_branches.py`에 둡니다.
  - 적용 녹색 0/2/4/5/6/10에서 모든 씨앗이 디코드되는지
  - SDMPC meter 축 허용 집합
  - 공유 녹색이 상자에 없을 때 결과 동일
  - configure 거부 경우

### 3.4 K4 — L2 법칙 (V-1, V-2)

- **spec**: `{'law':'carlson','A':1.33,'E':0.87,'alpha':0.0,'speed_scale':{'form':'cubic_lagrange','levels':{'80':0.7225223093088844,'90':0.8119772280655296,'100':0.9006844904146349},'maximum':110.0}}`
  - 수준 값은 `D:/VISSIM_runs/20260928_n1f_vsl_stage2/reports/fit_results.json`(`4091d6e1`) `k4_stage2.D6.fits.L2` 그대로입니다 [실행].
  - 사용자 결정문의 0.901/0.812/0.723은 반올림값입니다. 정확값을 쓰기를 권합니다(U4).
- **b(c)**
  - c = 110: 1(비활성, 지금과 같음)
  - c < 110: (80, m80), (90, m90), (100, m100), (110, 1) 네 점을 지나는 3차식을 **Lagrange 형**으로 계산합니다. 매듭에서 값이 정확히 매듭 값이 되고, Dual 연산에도 안전합니다.
  - 이 b를 속도·ρc·형상 세 곳에 모두 씁니다(`freeway_fd.py:39-46`, 적합기 정의 `n1f_fit.py:566-568`과 같음).
  - `speed_scale`이 없으면 b = c/max로, 비트 동일합니다.
- **수치** [실행]
  - 3차식은 [80, 110]에서 단조 증가합니다. 기울기 0.00872–0.01084/km/h
  - 매듭 기울기: 80 0.00936, 90 0.00872, 100 0.00921, 110(좌) 0.01084. L1의 1/110 = 0.00909보다 110에서 19 % 가파릅니다.
  - 구간선형 대비 최대 차이 0.0020
- **검증 호출**
  - `configure_literature_vsl`(:68, 명령 90/최대 110), `physical_lane_groups.py:212`(100/120)
  - 키 집합 검사(:27-28)가 `speed_scale`을 받아야 합니다(carlson만).
  - `maximum`이 마지막 매듭과 다르면 거부합니다. 120 경로는 lane group이 꺼진 v2에서는 닿지 않습니다.
- **시험**: `tests/test_literature_vsl_fd.py`에 다음을 더합니다.
  - 키 없음 비트 동일
  - 세 수준 정확, 110 → 공칭 FD
  - frejo에서 speed_scale 거부
  - 단조, ρc < 잼 밀도

### 3.5 K5 — 명령 → 분포 사상과 가족 일관성 (V-5, V-6, V-9, V-11)

- **키 (튜닝)**: `actuation.vsl_command_distribution = {'model':'single_value','distribution_by_command':{'80':81,'90':91,'100':101,'110':110}}`
  - `iter_action_csv_rows`가 이미 `actuation`을 받으므로(`:12618-12628`) 새 인자가 필요 없습니다.
- **쓰기**: `speed_kph` = 사상[명령]입니다.
  - 사상에 없는 값(120 확장 `:12652-12653` 포함)은 ValueError로 막습니다(fail-closed).
  - 키가 없으면 항등이라 CSV가 비트 동일입니다. `110.0` 서식도 그대로입니다.
  - action JSON의 `control.vsl`은 명령 공간 그대로입니다. 직전 적용 명령 → cohort 초기화, ±`max_vsl_step` 상자(`CONTRACT.md:691`, :718-721)는 바뀌지 않습니다.
  - `verify_joint_written_action`(`area_leader_objective.py:501`)은 같은 반복자로 행을 다시 만듭니다. 그래서 자동으로 일치합니다 [읽음].
- **러너**
  - `repin_scenario_v2.VSL_SPEEDS` = (81,91,101,110) → `lane_native_b110.vbs:34`
  - VBS는 받은 수를 분포 번호로 네 클래스에 쓰고, 되읽어 같은지 봅니다(`run_real_world_stackelberg_controller.vbs:1343`, :1446-1454, :1937-1968). 그래서 **VBS 변경 없이** 맞물립니다 [읽음].
  - `runner_config_check`가 v3c3 후보에서 통과하고, v3c2에서는 `[81, 91, 101]` 부재로 거부하는 것을 확인했습니다 [실행 e1 E4].
- **VBS 쪽 사상(U3-b)을 권하지 않는 이유**: 7,897줄 VBS를 고치게 되고, 러너 sha와 핀이 연쇄로 바뀝니다. 또 그 검증 시험(`test_native_vbs_clock.py` 등)은 돌릴 수 없습니다.
  - 대가(위험 R3): CSV의 `speed_kph` 열이 "분포 번호"가 됩니다. CSV를 읽는 분석 도구는 명령을 action JSON에서 읽어야 합니다.
- **가족 일관성 검사(V-9, 새로 추가)**: 아래가 모두 성립하지 않으면 거부합니다. 튜닝 생성기(`validate_tuning_v2`), `launch_plan.py`, 실행 시 `configure_runtime`(plant 적재 뒤) 세 곳에 둡니다.
  - 러너 허용 목록 = 사상의 상
  - plant 법칙에 `speed_scale`이 있음 ⇔ 사상이 단일값
  - 110 → 110
  - 음성 시험: L2 + 항등 사상, L1 + 단일값 사상, 러너 80,90,100,110 + 단일값 사상 — 모두 거부
- **L1 분포형 가족 유지(U5, V-11)**
  - 법칙은 reference(plant 성분) 전용입니다(`runtime_setup.py:44-46`가 튜닝 쪽을 거부). 러너 목록은 plant·obs150 사이드카에 핀됩니다. 그래서 "키 하나로 전환"은 핀 구조상 안 됩니다 [읽음].
  - 권고 U5-a: 생성기 옵션 `--vsl-family distribution`이 한 벌을 따로 만듭니다(L1 A 0.94/E 1.44, 항등 사상, 러너 80,90,100,110). 이 벌은 살아 있는 설정으로 커밋하지 않습니다.
  - 두 가족 모두 생성기 시험에서 V-9를 통과해야 합니다. 코드 경로(키 없음·항등)는 단위 시험이 실행하므로 죽은 코드가 아닙니다.

### 3.6 K6 — E2 조용한 무시 설치 검사 (E-1)

- **위치**: `lane_plant_runtime._load_sources_v2`, 성분을 만든 직후(`:97-101`)
- **내용**
  - reference의 `freeway.vsl_fd_response`·`component_vsl_transport`가 설치된 성분 속성(`component.base.network.freeway_vsl_fd_response`, `component_vsl_transport`)과 같아야 합니다. `speed_scale`까지 비교합니다.
  - reference에 `physical_cell_fd`나 `state_response`가 있으면 거부합니다. 이 트리에는 설치기가 없기 때문입니다.
- **근거**: `PLANT_PORTING_GUIDE.md:426-428`((d)-3 1), 코덱스 검토 `REVIEW_CHECK.md` E2 [읽음]
- **동일성**: 지금 reference는 통과해야 합니다(GA-1).

### 3.7 K7 — 재핀 (v3c1 P5–P8과 같은 순서)

1. **RA-1 추출**
   - v3c3 NC fit 시드 추출을 `metanet_calibration_v1/v3c3_nc_<날짜>/`에 둡니다. 명령은 v3c1 영수증과 같습니다(§4).
   - 한 번에 하나씩, BELOW_NORMAL로 돌립니다.
2. **C-4 `repin_scenario_v2.py`** [목록 C-4]
   - 망 상수 `:102-111`
   - `VSL_SPEEDS = (81,91,101,110)` (`:162`)
   - 새 열거표: `V3C2_EDIT_RECEIPT`(`cf8b0cb2…`), `V3C2_ADDED_COMPOSITION`(14, 13 뒤, 391 B, `82c11cd5…`), `V3C2_INPUT_COMPOSITION_EDITS`(12행 vehComp 1→14), `V3C3_EDIT_RECEIPT`·`V3C3_ADDED_DISTRIBUTIONS`
   - `characterize_changes`(`:506-585`)는 열거된 것만 받고 나머지는 거부합니다. 구성·분포는 바이트 감사를 둡니다(`added_block_audit`식). CHANGE_RULES는 넓히지 않습니다.
   - 시험: 받기·거부 합성 시험과 실제 팩 시험 → `build` → `verify`
3. **손 기록과 도시 유도 연쇄**
   - 손 기록(explicit, entry, nonexistent, offramp prior)은 망 핀만 바꿉니다.
   - C-8/C-9 DEFAULTS를 바꾸고, v3c1 순서로 유도합니다(`make_config_n31.py:101-113` 주석 순서).
   - β 원천 이름은 U8입니다.
4. **plant 연쇄**
   - C-3 + RA-3 포트 프로필
   - C-7 + DA-5 obs150
   - V-3 reference(L2)
   - (2에서 만든) VBS
   - C-2 plant(QUALIFICATION)
   - C-6 + RA-4 램프 예측
   - C-1 config 세 벌(+ K5 키)
   - C-10 β 키
5. **점검과 문서**
   - 시험 묶음
   - `repin_scenario_v2.py configure-check`(임시 폴더에만 씀)
   - `scripts/preflight_tuning_paths.py` 세 벌
   - `CONTRACT.md:687-721`, `PLANT_PORTING_GUIDE.md`
   - 새 보고서 `N31D/REPIN_V3C3_REPORT.md`
6. **v3c1 파일 처리**: v3c1 파일은 트리에서 뺍니다. v3c1 재생은 FRZ `sdmpc31_5323faa4_202609281442`에서만 합니다(memory `vissim-supersede-dont-flag`).

### 3.8 바꾸지 않는 것

- 러너 VBS(`8c753c08`)
- `sdmpc.py` VSL 축(`:333-341`, 명령 공간, 기준 110)
- 발사기 `run_sdmpc_n31.ps1`, `freeze_worktree.ps1`, `prepare_sdmpc31_network.py`
- 표지 셀 `[0,3,5,8,14,18,26,28]`(desSpeedDecisions 불변)
- `max_vsl_step` 40, `vsl_set` 명령값

---

## 4. v3c3 fit 시드에서 다시 만들 파생 증거

| id | 대상 | 명령·생성기 | 예상 변화 | 확인 |
|---|---|---|---|---|
| RA-1 | `metanet_calibration_v1/v3c3_nc_<날짜>/observations/s{31,41,43,47,53}_v3c3nc_observations` + 영수증 | `extract_observations.py --run <v3c3 run> --out <폴더> --phase-sec 0.1 --geometry-profile …/controller_response_v1/geometry_profile.json --refined-geometry …/segment_resolution_20260921/geometry_200_branch_guard.json` (시드당 약 90 s) | 새 폴더. v3c1 폴더는 기록으로 남김 | checks 18538, 마지막 프레임 8995.1, 망 sha = 시드 v3c3 sha. GB-1이 통과했다면 `boundaries_30s.csv`가 `nc_analysis/eo` 같은 시드와 같아야 함 |
| RA-2 | s31 `geometry.json` | RA-1 | 출처 키(network, source_network, 입력 경로)만 다름 | make_plant `--check`, `_load_sources_v2` 기하 동일 |
| RA-3 | `N31D/port_profile_v2/{port_profile.json, obs/port_travel_v2.json, obs/port_events_le900.csv}` | C-3 → `extract_port_profile.py` | **내용 변화 예상.** v3c2 입구 차량이 0–900 s에 110으로 들어옴 | `--check`, 포트별 \|Δ\| 표 |
| RA-4 | `make_config_n31.RAMP_FORECAST` (:161-179) | C-6 → `derive_ramp_forecast_n31.py` | 내용 변화 | `--check` |
| RA-5 | `N31D/urban/unsignalized_validation_v3c3nc_<날짜>.json` | C-8 → `derive_unsignalized_validation.py` (FZP 5개, 약 5.9 GB) | 내용 변화 | `--check` 두 번 같은 sha |
| DA-1 | β 표(routing, routing_2)와 손 기록(explicit, entry) | `derive_routing_turn_beta.py`(+explicit), `derive_routing_beta_physical.py` | **β 값 0 변화**(경로결정 불변). 망 경로·sha 필드만 바뀜. 이름은 U8 | 핀 사상 뒤 JSON 포인터 비교 = 0, `check_complete_beta_runtime`의 망 sha |
| DA-2 | 도시 묶음 1 표 6개(phase authority, area contract+provenance, route queue, unsignalized turns, nonexistent, offramp prior) | C-9 생성기(v3c1 순서) | sha만. unsignalized_turns는 RA-5의 검증 수치만 바뀜. area 계약은 바이트 동일, 옛 사본 유지(D5) | GB-3 |
| DA-3 | 시나리오 선언 20개 + historical_prior_transfer + repin_receipt + base config | repin build | sha만. transfer에 구성·분포 기록 추가. 1083·635 수정은 v3c3에서 재증명 | `REPIN_VERIFY_OK`, configure-check |
| DA-4 | `control_area_membership_213a5d.json` | repin build | sha만. 1134/1135 lineage 5행 그대로 | lineage 시험 2개 |
| DA-5 | `obs150/obs150_detectors_v2.csv` + manifest | C-7 → `build_obs150_detectors.py` | CSV 바이트 동일(`108debbb`, 294행). 사이드카 핀만 | `--check` |
| DA-6 | `plant_n31_v2.json`, `config_n31_v2*.json` ×3, `reference_config_n31_v2.json` | reference → plant → config 연쇄(`CONTRACT.md:692`) | 새 sha | `--check`, preflight ×3 |
| RA-6 | U1 T1 재판정(선택) | scratchpad `v3c1-p10/u1t1` 스크립트 | 경로 불변이라 114/119 근처 예상 [추론] | 보고 |
| (없음) | b110 segment_params·boundary fit | 이월 사전값(라벨만) | — | QUALIFICATION |

- **L2 이월 [추론]**
  - L2는 v3b 기반 N1F 팔(입구 DSD 40)에서 맞췄습니다. 모멘트 셀은 2–4, 6–9, 15–20입니다. v3c2 입구 변경은 셀 0–1 부근에만 직접 닿습니다.
  - 그래서 L2를 사전값으로 이월하고, QUALIFICATION에 적습니다. v3c1이 L1을 v3b에서 이월한 것과 같은 처리입니다.

---

## 5. 시험과 동일성 관문 (사전 선언)

- **동결 시점**: 실행 세션은 이 절을 `gate_predeclaration_repin_v3c3.md`로 옮겨 sha를 고정합니다. 순서는 다음과 같습니다.
  - GB-0/GB-1은 NC 발사 전에 고정합니다.
  - GA는 FRZ(K6) 재생 전에 고정합니다.
  - GB-5 이후는 R-obs 발사 전에 고정합니다.
- K3·K6이 새로 쓰는 메타데이터 키 이름도 이때 적습니다. 허용 diff는 그 키뿐입니다.

### 5.1 GA — K1–K6, v3c1 기반 (FRZ = K6 head, 망 v3c1)

| 관문 | 내용 | 통과 조건 |
|---|---|---|
| GA-1 | v3c1 R-obs(`D:/VISSIM_runs/20260928_sdmpc31_v3c1/sdmpc31_v3c1_nc_s31`) 결정 61개 재생(`make_replay_state_v2.py prepare` + `replay_decision_n31.ps1`) | 판정 61/61 IDENTICAL(새 action_contract 포함). action JSON 전체 비교에서 원본과 다른 곳은 휘발 7필드, T5가 찾은 예측 진단 4필드(ulp 수준), 선언한 새 메타데이터 키뿐 |
| GA-2 | 해시 시드 A/B: 재생 4050·4500 + 반사실 900을 PYTHONHASHSEED 미설정/0/2로 | 세 실행의 action JSON(휘발 제외), CSV, 목적함수 repr가 서로 바이트 동일. 다르면 해당 필드를 적고 **STOP** |
| GA-3 | T5-B 반사실 SDMPC 5개 재현(900 r1/r2, 2700, 4950 r1/r2; 하네스 `scratchpad/v3c1-p10/t5/t5_chain_b.py`, 기준 `t5/B/*.summary.json`) | CSV 바이트, 목적함수 repr, 제어 필드, 탄젠트 트레이스(시간 키 제외)가 5323faa4 기록과 같음. 이 상태들은 10490 적용 녹색이 10이라 상자에 공유 녹색이 없습니다 [실행 R-obs 4050 확인]. 예측 진단 4필드의 ulp 차이만 허용 |
| GA-4 | 10490 양성 대조: hybrid s31 `state_003000`(직전 2850 적용 10490 = 5)에서 배포 튜닝으로 wu-link 반사실 | K2 트리에서는 `Service coordinate has no unique physical green: RM_C10490`으로 실패해야 함(재현). K3 트리에서는 완료, 선택 녹색 ∈ 정규화 표, 버린 씨앗이 기록됨. 하네스가 hybrid 직전 행동을 다른 이유로 거부하면 R-4 합성 fixture로 대체하고 그 사실을 기록 |
| GA-5 | 시험 묶음(금지 제외): N31 unittest, T9, repin/prepare pytest, tools(plant_gate, verify_gt, watch, common), obs150 비-ps1, `tests/test_literature_vsl_fd.py`, `diagnostics/test_physical_ramp_branches.py`, 새 시험 | 모두 통과. `extra` 묶음은 실패 id 집합이 기준과 같음 |

### 5.2 GB — v3c3

| 관문 | 내용 | 통과 조건 |
|---|---|---|
| GB-0 | v3c3 정적 빌드 | 순수 삽입 18줄, 블록 바이트·sha = N1F 계획, 분포 44 → 47, 새 번호는 이전에 없던 것이고 정적 참조 0, 순서 80,81,85 / 90,91,100 / 100,101,110, 시드 간 randSeed 한 줄, ET 왕복·fzp_only 재작성 항등, sha = §2.3 표, prepared 미러 키가 v3c2와 같음, 드라이런 exit 0 |
| GB-1 | NC 동일성(§2.4) | 시드마다 payload sha 동일 + .err 동일 + 완료. s31은 반드시, U2-a면 fit 5시드 |
| GB-2 | 도구·생성기 | repin `build`/`verify` OK, `configure-check` t = 1/150/900 OK(구성·분포 열거 포함), `--check` 연쇄 전부(unsignalized validation 포함), preflight ×3, 시험 묶음(GA-5와 같은 목록) |
| GB-3 | 허용 diff(v3c1 트리 대비, 핀 사상 뒤) | 목록의 변화만: 망 핀, transfer의 구성·분포 기록, RA-3/4/5 내용, 기하·β 출처, L2 + 사상 + 러너 81,91,101,110, QUALIFICATION, 문서, K1–K6. 다른 내용 차이는 0 |
| GB-4 | 동결 + 사전점검(VISSIM 없음) | `FREEZE_VERIFIED … head=<K7>`, `LAUNCH_PLAN_DETAIL … network_sha=3de889f0 detectors=294 controller=no-control`, `NETCOPY … sha256=3de889f0… sig=42`, `PREFLIGHT PROVENANCE_OK`, `EXIT … code=0` |
| GB-5 | R-obs 완료 | `EXIT … code=0`, 결정 61, `DECISIONS_FAILED` 0, 런로그 `SKIPS` 0(memory `vissim-midblock-sg-com-red-env-leak`), `ERROR=` 0, t = 1 configure 통과 |
| GB-6 | 짝: R-obs FZP 대 NC v3c3 s31 FZP | 헤더와 0.10 s 행만 다르고(v3c1 145 B) 나머지 바이트 동일. 이러면 R-obs를 짝 비교의 NC 대용으로 씀 |
| GB-7 | T5 | `test_g1_frame` PASS(state_000900). 결정 61/61 IDENTICAL, action JSON 전체 61/61 동일(휘발 제외, **이번에는 ulp 예외 없음**). 해시 시드 미설정/0/2 × 3결정 동일 |
| GB-8 | L2 all-110 동일성(R-obs 상태 2700·6300, `scratchpad/v3c1-p10/l0l1` 방식) | 명령 전부 110일 때 L2 / L1 / 키 없음 reference의 롤아웃 digest(FW_E, FW_W)가 비트 동일. 110 탄젠트는 L2 ≠ L1이고 ≠ 0, FW_W 0. 대조 fwe100은 달라야 함 |
| GB-9 | 반사실 SDMPC 4상태(900, 2700, 4950, 6300; r1/r2 한 쌍) | 완료. 블록 0 허용 집합 = (80,90,100,110). action JSON VSL ⊂ 명령 공간, CSV VSL ⊂ {81,91,101,110}, 행마다 CSV = 사상(JSON). r1 = r2 |
| GB-10 | 110 미만 쓰기 경로(오프라인) | GB-9 결정 하나에서 FW_E 구역 VSL을 80/90/100으로 바꿔 `write_action_csv`에 넣으면 CSV가 81/91/101이 됨. VBS 수용 규칙의 파이썬 거울(66행, `VslActionKeyValid`, `IsCsvFiniteNumber` 대 `lane_native_b110.vbs`)이 받아들임. 음성: 90 행과 120 행은 거부 |
| GB-11 | (U9) 네이티브 쓰기 확인 | 탐침 런, 또는 J1 첫 런의 사전 선언 감사: `vsl_trace` requested = readback, ok = 1, 구역 차량 DESSPEED ∈ [80,82]/[90,92]/[100,102] |
| GB-12 | U1 T1 재집계(선택) | 보고만 |
| GB-13 | RM 팔 | 세 구성 바이트 동일, 드라이런 OK. 런 뒤 fit 시드 FZP가 NC v3c3 같은 시드와 900 s 전까지 같음(첫 규칙 쓰기 전) [추론: 규칙 시작 900 s]. s37은 run.json 두 필드만 |

### 5.3 멈춤 규칙

- GB-0·GB-1 실패: 발사 중단, 사용자 보고
- GA-2·GB-7 해시 차이: K1 범위를 넓히지 않고 STOP
- GA-3 비동일: 원인 키 목록과 함께 STOP
- GB-3 목록 밖 diff: STOP
- R-obs t = 1 거부: 검증기 이름과 함께 STOP

### 5.4 돌리지 않는 것 (금지)

- `test_b1a_watchdog_attempt_launch.py`, `run_plant_fidelity_matrix`, `test_runner_ps1_obs150.py`, `test_native_vbs_clock.py`, `test_tools_launch.py`, `test_tools_replay.py`, real_watchdog
- C-5는 `test_tools_launch.py:175`의 상수를 **편집만** 합니다. 실행하지 않습니다.

---

## 6. 런과 발사 순서

### 6.1 런 목록

| 런 | 망 | 발사 방식 | 좌석 | 벽시계 | 선행 | 관문 |
|---|---|---|---|---|---|---|
| NC v3c3 s31/s41/s43/s47 (묶음 A) | v3c3 | `fast_nc_run.ps1 … -Execute -MinimumFreeGiB 8 -AllowConcurrent`, WMI | 4 | 약 95 min(v3c2 실측 92–95) [실행 run.json] | GB-0, 선언 동결 | GB-1 |
| NC v3c3 s53, s37(봉인) (묶음 B) | v3c3 | 같음 | 2 | 약 95 min | 좌석 | GB-1(s53) / run.json(s37) |
| RM v3c3 s31, s41 | v3c3rm | 같음(rule runtime) | 2 | 약 107–109 min [읽음] | GB-1 s31 통과 | GB-13 |
| RM v3c3 s37(봉인) | v3c3rm | 같음 | 1 | 약 108 min | 좌석 | run.json |
| **R-obs** `sdmpc31_v3c3_nc_s31` | v3c3(N31D 사본) | `run_sdmpc_n31.ps1 … -Controller no-control`, FRZ, WMI | 1(dev) | 약 2.1 h(v3c1 7,452 s) [실행 로그] | K7 커밋, GB-2…GB-4 | GB-5…GB-12 |
| (선택) VSL 탐침 | v3c3 | U9: 발사기의 컨트롤러 목록 확장 필요 | 1 | 약 20–30 min | R-obs 뒤 | GB-11 |

### 6.2 좌석 시간표 (PC 전체 VISSIM ≤ 4)

- **t0**: NC 묶음 A 4석
- **t0 + 1.6 h**: 묶음 A 종료 → GB-1(4시드). 이어서 NC s53, s37 + RM s31, s41 (4석)
- **t0 + 3.3 h**: NC B 종료 → RM s37 발사. RA-1(fit 5)이 가능해져 K7 파생이 시작됨
- **R-obs**: K7 커밋 뒤, 좌석이 ≤ 3이고 dev VISSIM이 0일 때(`run_sdmpc_n31.ps1:84-86`)
- **주의**: GA의 SDMPC 반사실 재생(파생 8 + 응답 8 워커)은 fast_nc 런과 겹치지 않게 둡니다. ps1의 300 s 무진행 종료를 피하기 위해서입니다(N1F README §2-4) [읽음].

### 6.3 명령 틀 (메인 세션)

**NC·RM** (v3c2 `launch_lines_nc.txt`와 같은 꼴, 경로만 바꿈):
```powershell
Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine='cmd.exe /c powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\VISSIM-merge\sim3\diagnostics\fast_nc_run.ps1 -Prepared <root>\s31_v3c3nc\prepared -Output <root>\s31_v3c3nc\run -Execute -MinimumFreeGiB 8 -AllowConcurrent > <root>\s31_v3c3nc\launch.log 2>&1'; CurrentDirectory='<root>'}
```

**R-obs** (v3c1 보고 §5와 같은 꼴):
```powershell
New-Item -ItemType Directory -Force D:\VISSIM_runs\20261001_sdmpc31_v3c3 | Out-Null
Set-Location D:\VISSIM-merge\sim3-n31-v3c3
powershell -NoProfile -ExecutionPolicy Bypass -File D:\VISSIM-merge\tools\run_sdmpc_n31.ps1 -Freeze -PreflightOnly `
  -Tuning diagnostics\sdmpc_n31_20260924\config_n31_v2.json -Name sdmpc31_v3c3_nc_s31 -SimPeriod 9000 -Seed 31 `
  -Controller no-control -RunsRoot D:\VISSIM_runs\20261001_sdmpc31_v3c3
# GB-4 통과 뒤, 로그의 FRZ= 경로로:
$frz = 'D:\VISSIM-merge\frozen\sdmpc31_<head8>_<yyyyMMddHHmm>'
$log = 'D:\VISSIM_runs\20261001_sdmpc31_v3c3\wmi_sdmpc31_v3c3_nc_s31.log'
$cmd = 'cmd.exe /c powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\VISSIM-merge\tools\run_sdmpc_n31.ps1 ' +
       '-Tuning diagnostics\sdmpc_n31_20260924\config_n31_v2.json -Name sdmpc31_v3c3_nc_s31 -SimPeriod 9000 -Seed 31 ' +
       '-Controller no-control -RunsRoot D:\VISSIM_runs\20261001_sdmpc31_v3c3 > ' + $log + ' 2>&1'
Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine = $cmd; CurrentDirectory = $frz}
```

- `<root>` = `D:\VISSIM_runs\20261001_v3c3` (U12). 발사마다 PID와 명령을 `wmi_launch_lines*.txt`에 적습니다.
- **발사 전 확인**
  - VISSIM 수
  - 각 폴더에 `run\`과 `launch.log`가 없음
  - D: 여유 ≥ 30 GB(NC 6 + RM 3 + R-obs 약 15 GB [추론])
  - `STOP` 표시 없음

### 6.4 감시

- 진행 파일을 봅니다: `run/progress.csv`, `WATCHDOG_PROGRESS.txt`, 런처 로그의 `EXIT` 줄.
- 5분 동안 진행이 없으면 **소유 PID만** kill하고 다시 띄웁니다(memory `vissim-watchdog-policy`, `vissim-legacy-watchdog-global-kill`; 런처는 `-NoGlobalKill`).
- 발사는 세션과 분리된 WMI로만 합니다(memory `vissim-launch-detached-from-session`).
- 런 폴더와 런로그에 `RW_*` 누출이 없는지 확인합니다(memory `vissim-parent-run-launch-traps`).

---

## 7. 위험

| # | 위험 | 대응 |
|---|---|---|
| R1 | DSD 블록이 NC 궤적을 바꿈(가능성 낮음: N1F G0 8/8) | GB-1 STOP. v3c3 NC 5런을 새 기준으로 삼을지 사용자 결정 |
| R2 | 구성·vehComp를 보는 숨은 런타임 검증기(1098/1099 입력) | 선언 20개 가운데 vehComp를 박은 것은 sc2001(1106/1107)뿐입니다 [실행 grep]. configure-check와 R-obs t = 1이 최종 확인 |
| R3 | CSV `speed_kph`가 분포 번호가 되어, 이 열을 km/h로 읽는 분석 도구가 틀림(예: `diagnostics/com_execution_equivalence/verify_pair.py`, `audit_lever_utilization.py`) [실행 grep, 개별 확인 안 함] | CONTRACT에 열 의미를 명시. 명령은 action JSON에서 읽음. J1 분석 도구는 사상 표를 함께 읽음 |
| R4 | L2가 80에서 B2 방류를 비관(예측 −4.0 %, 관측 −0.34 %) | 알려진 약점으로 QUALIFICATION에 기록. SDMPC가 80을 드물게 고를 것 [추론] |
| R5 | L2·L1 모두 v3b 기반 적합을 이월, 입구 DSD 변경(v3c2)과 F10 미해결 | 이월 사전값으로 명시. F10 결정 뒤 재평가 |
| R6 | 10490 "가장 낮은 녹색 유지"가 hybrid 브랜치 규칙({0,4..10})과 다름 | hybrid 합칠 때 공유 서비스 분기가 무효가 됨을 기록하고 재검증 |
| R7 | 다른 집합 순회(어댑터 :4457 등)가 SDMPC 경로에서 순서 의존을 만듦 | GA-2·GB-7이 탐지하면 STOP |
| R8 | 110 미만 네이티브 쓰기가 J1 전까지 한 번도 실행되지 않음. L2의 110 좌기울기가 가팔라 SDMPC가 110을 고수할 수 있음 [추론] | GB-10(오프라인) + GB-11(U9). 러너가 fail-closed(`ERROR=VSL_COM_WRITE_READBACK`)라 오류가 조용히 지나가지 않음 |
| R9 | T9 1e-4가 L2 3차식에서 안 맞음 | 허용 오차를 넓히지 않고 원인을 조사(곡률, h) |
| R10 | 묶음 2·F10·termcost 브랜치를 옮길 때 충돌(β 키 `routing_v3c1_2` → `routing_v3c3_2`, 상수) | 각 이식 때 다시 적용 목록을 씀 |
| R11 | 금지 시험 때문에 발사기·재생 도구 변경(K2)을 그 묶음으로 검증하지 못함 | K2는 새 pytest + 실제 재생(GA-1·GB-7)으로 확인. 발사기는 바꾸지 않음(U9 제외) |
| R12 | 봉인 s37 누출 | s37 출력은 run.json 두 필드만. U2-c 해시 도구는 IDENTICAL/DIFFERENT만 출력 |
| R13 | E2 검사가 예상 밖 키로 현재 reference를 거부 | GA-1이 확인 |
| R14 | 좌석·자원(다른 세션의 VISSIM, SDMPC 워커 CPU) | 발사 직전 좌석 확인, GA 재생은 NC와 겹치지 않게 |

---

## 8. 사용자가 정할 것

| # | 질문 | 권고 |
|---|---|---|
| U1 | 망 이름: v3c2 + DSD 81/91/101을 새 이름 **v3c3**로 할지, v3c2에 접을지 | v3c3(§2.2 A) |
| U2 | NC 동일성 범위: (a) fit 5시드 전부 v3c3로 / (b) s31만 + v3c2 NC 자료 재사용 / (c) s37 해시 전용 동일성 확인 허용 여부 | (a). (c)는 허용 권고. 출력은 판정 한 단어 |
| U3 | 사상 위치: (a) 어댑터 writer(CSV `speed_kph` = 분포 번호, VBS 무변경) / (b) VBS 상수 + 코드 | (a) |
| U4 | L2 수준 사이 보간과 값: (a) 네 점 3차 Lagrange + 정확 m_v / (b) 80–100 직선(90에서 −0.0004, 110 불연속) / (c) 구간선형(꺾임) | (a) |
| U5 | L1 분포형 가족: (a) 생성기 옵션으로만(살아 있는 설정 아님) / (b) 후보 설정 한 벌을 커밋(plant·reference·VBS·튜닝 각 1) / (c) 버림(FRZ 5323faa4 재생만) | (a) |
| U6 | 10490 정규화 규칙: (a) 같은 서비스 그룹에서 가장 낮은 녹색 유지 / (b) 모두 제외(hybrid) | (a) |
| U7 | E2 조용한 무시 설치 검사를 이번에 넣을지 | 넣음 |
| U8 | β 원천 이름: (a) `routing_v3c3{,_2}` + `*_v3c3_<날짜>.json`(어댑터·beta_source·시험 변경, v3c1 D1과 같은 방식) / (b) 키·경로 유지, 내용만 갱신 | (a) |
| U9 | 네이티브 110 미만 쓰기 확인: (a) J1 첫 런 사전 선언 감사(GB-11) / (b) R-obs 뒤 탐침 런(발사기 컨트롤러 목록 확장 필요, 금지 시험 때문에 발사기 시험 불가) | (a) |
| U10 | 승인 범위: 작업 트리·브랜치 생성, 커밋 K1–K7, 푸시, 동결, NC·RM·R-obs 발사(메인 세션) | v3c1 때처럼 한 번에 승인 |
| U11 | J1 발사 줄에 `PYTHONHASHSEED=0` 고정(hybrid 관행) | J1에서는 고정. 관문(GA-2·GB-7)은 고정하지 않고 A/B로 |
| U12 | 이름: 브랜치 `claude/repin-v3c3-20261001`, 작업 트리 `sim3-n31-v3c3`, 런 루트 `D:\VISSIM_runs\20261001_v3c3`, R-obs 루트 `…\20261001_sdmpc31_v3c3` | 이대로 |

---

## 9. 공수와 벽시계

| 단계 | 내용 | 에이전트 시간 | 벽시계 | 선행 |
|---|---|---:|---:|---|
| P0 | 사용자 결정 U1–U12 | — | — | — |
| P1 | 작업 트리, v3c3 빌드·prepare·GB-0, 관문 선언 동결 | 1.5 h | 1.5 h | P0 |
| P2 | NC 묶음 A → B(+ GB-1) | 감시 0.5 h | 3.3 h | P1 |
| P3 | K1–K6 구현과 단위 시험 | 8–10 h | P1·P2와 병행 | P0 |
| P4 | RM 빌드·드라이런 → 발사 | 1.5 h | 1.8 h(런) | P1, GB-1 s31 |
| P5 | GA(FRZ K6: 재생 61 약 1.5 h, 해시 A/B, 반사실 5 × 약 11 min, 양성 대조) | 1 h + 대기 | 3–3.5 h | P3 |
| P6 | K7 재핀(추출 5 × 90 s, 도구, 유도, FZP 검증 5.9 GB, plant 연쇄, 시험, 문서) | 5–7 h | 5–6 h(P5와 일부 병행) | P2, P3 |
| P7 | 커밋(·푸시)·동결·사전점검·R-obs | 0.5 h | 2.2 h | P5, P6 |
| P8 | P10(GB-5…GB-12: T5 61 + 해시, L2 all-110, 반사실 4–5, 짝, 쓰기 경로) | 2 h + 대기 | 4–5 h | P7 |
| **합계** | | **약 22–28 h** | **약 20–24 h** | 임계 경로 P1 → P3 → P5/P6 → P7 → P8 |

- VISSIM 런 합계는 NC 6 + RM 3 + R-obs 1 = 10개, 약 17 VISSIM·시간입니다. 모두 코드 작업과 겹칩니다.
- U2-b를 고르면 NC가 4개 줄고 K7을 약 1.6 h 일찍 시작합니다.

---

## 10. 하지 않은 것과 파일

- **하지 않은 것**
  - 코드·핀·망 변경, git 쓰기, VISSIM·cscript·fast_nc_run, 금지 시험, 시험 묶음 실행, FZP 읽기(receipt JSON만 읽음)
  - s37·59/61/67 결과 열람
  - 저장소는 쓰기 전후 모두 `git status` 0줄입니다 [실행].
- **공개**
  - e3에서 v3c2 s37 **원본 망 파일**(입력)을 읽어 v3c3 s37 예상 sha를 계산했습니다. 런 출력은 열지 않았습니다.
  - hybrid 런 폴더는 파일 목록만 봤습니다(`state_003000.json` 존재 확인).
- **파일**
  - 이 계획: `D:/VISSIM_runs/20260930_v3c2/reports/repin/REPIN_V3C2_PLAN.md`
  - 목록: `D:/VISSIM_runs/20260930_v3c2/reports/repin/repin_v3c2_inventory.json` (`build_inventory.py`가 생성. 증거 파일 sha는 `evidence`에 있음)
  - 증거: `D:/VISSIM_runs/20260930_v3c2/reports/repin/_evidence/`
    - `e1_characterize.py` → `.json`: E1 거부, E2 절 차이, E3 블록 감사, E4 v3c3 후보의 러너 검사, E5 분포 목록
    - `e2_fcb_sections.py` → `.json`: fcb → v3c2 절, 1098/1099 12행
    - `e3_v3c3_preview.py` → `.json`: 6시드 예상 sha와 삽입 검사
