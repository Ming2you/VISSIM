# REPIN_V3C2_PLAN 적대적 검토

- 작성 2026-10-01. **읽기만 했습니다.** 저장소·망·git·VISSIM은 건드리지 않았고, 쓴 파일은 이 문서 하나입니다.
- 대상
  - `REPIN_V3C2_PLAN.md` sha256 `d4b70c02…` (= 목록의 `plan_sha256`) [실행]
  - `repin_v3c2_inventory.json` sha256 `07028e24…`, 항목 52개 [실행]
- 기준: `D:/VISSIM-merge/sim3-n31-v3c1` @ `9ed2ef0` (`git status` 0줄) [실행]. `N31D` = `diagnostics/sdmpc_n31_20260924`. `AD` = `evaluation/controllers/vissim_stackelberg_adapter.py`.
- 표기: **[실행]** 이번에 돌려 확인 · **[읽음]** 파일에서 확인 · **[추론]** 시험하지 않은 판단.
- 금지 시험·s37/59/61/67 결과는 열지 않았습니다. 런 폴더는 v3c1·v3c2의 **s31/s41/s43/s47 fit 시드**와 v3c1 R-obs만 읽었습니다.

## 0. 요약

| 구분 | 개수 | 내용 |
|---|---|---|
| **blocking** | 3 | 모두 GA 관문(K1–K6 동일성)의 설계 결함입니다. 계획 본문의 기술적 판단은 대체로 맞습니다. 그러나 이대로 관문 선언을 동결하면 **GA-1은 구성상 실패**합니다. **GA-3은 옛 코드로 거짓 통과**할 수 있고, **P5와 P6을 병행하면 코드가 섞입니다** |
| nonblocking | 20 | 명세 모순(V-1, V-5), 목록 누락(5곳), K3 주장 범위, GB-1·GB-13 정의, 문서·위험 보강 |

질문별 판정

| 질문 | 판정 |
|---|---|
| 목록이 완전한가 | **거의 완전**합니다. 망 sha, v3c1 이름, L1 계수, 110 전용 가정을 검색했습니다(§3). 코드·시험 파일에서 목록 밖 핀은 **0건**입니다. 다만 다음이 빠졌습니다: `test_n31_urban_batch1.py:59`, `obs150_contract.validate_tuning_v2`(V-9의 실제 위치), 이월 사전값 항목(v3c1의 MA-1), grep 기록 [실행] |
| 10490 일반화가 유일한 표에서 동작을 바꾸지 않는가 | **바꾸지 않습니다.** 수송 표는 순증가이고, 겹치는 값은 10490의 {2,3} 하나뿐입니다 [실행]. 단 동일성 시험이 `==`이라 순서·키 타입 변화를 못 봅니다(N3). 또 "옛 코드가 죽던 곳에서만 달라짐"은 규칙 프로필 경로에서는 틀립니다(N3) |
| `state.py` 정렬은 마지막 ulp만 바꾸는가 | **그렇습니다.** 0 이상인 float 4개의 합이므로 순서 차이는 1–2 ulp입니다(T5 실측). SDMPC Ω는 control-area 목적함수라 이 합을 거치지 않습니다[읽음·추론]. v3c1 R-obs 대비 T5는 진단 4필드가 **어느 결정에서든** 달라질 수 있어 허용 문구를 넓혀야 합니다(N2). 진짜 문제는 정렬이 아니라 **GA-1이 provenance 변화를 허용 목록에 넣지 않은 것**입니다(B1) |
| 단일값 사상이 분포형 DSD로 조용히 되돌아갈 수 있는가 | **분포형 번호는 쓰일 수 없습니다.** 러너 허용 목록은 상수 하나이고 env로 덮을 수 없습니다. 실행 러너는 핀된 파일이고 V-9가 있습니다 [읽음]. 다만 거부가 일어나면 런은 그 구간을 **무제어로 계속**하고 exit 0으로 끝납니다. 그래서 "조용함"을 막는 것은 `DECISIONS_FAILED`·`ERROR=` 관문뿐입니다(N4). 또 writer 명세가 nearest 반올림 순서와 모순입니다(N5) |

---

## 1. Blocking

### B1. GA-1의 "action JSON 전체 비교" 허용 목록이 구성상 깨진다

- **계획**: GA-1(§5.1)은 원본과 다른 곳이 다음뿐이어야 통과입니다: "휘발 7필드, T5 진단 4필드, 선언한 새 메타데이터 키". 재생 FRZ는 K6 head입니다.
- **사실** [실행]: 기록된 v3c1 R-obs `action_004050.json`의 `run_provenance`(최상위와 `metadata` 둘 다)에는 다음이 들어 있습니다.
  - `workspace_root`, `numsim_repo_root`: `…\frozen\sdmpc31_5323faa4_202609281442`
  - `inputs.*.path`: 매핑·튜닝 등이 그 FRZ를 가리킴
  - `numsim_src_sha256`
  - `imported_modules`: 30개 경로와 sha. `src.models.state` 포함
  - `execution_fingerprint_sha256`
- T5-A에서 휘발 필드가 7개뿐이었던 이유는 재생 Root가 **기록과 같은 FRZ**였기 때문입니다(`T5_REPORT.md` §3).
- GA-1은 Root가 K6 FRZ이고 K1이 `state.py`를 바꿉니다. 그러면 다음이 반드시 달라집니다:
  - 위 경로 전부
  - `imported_modules['src.models.state'].sha256`
  - `numsim_src_sha256`
  - `execution_fingerprint_sha256`
- 결과: GA-1은 **구성상 실패**하고, §5.3 규칙에 따라 STOP합니다.
- **고칠 것** (동결 전)
  - (a) `run_provenance.*`의 경로·sha 필드를 "예상 변경"으로 **열거**합니다.
  - (b) 동시에 그 값이 K6 트리를 가리키는지 **양성 확인**합니다. workspace_root = K6 FRZ, state.py sha = K1 판, 바뀐 모듈 목록 = K1–K6 diff.
  - (c) 판정 필드(CSV 바이트, 제어 필드, derived)는 지금대로 둡니다. `derived` 입력은 내용 sha뿐이라 경로 영향이 없습니다 [실행 `obs150/derived_004050.json` inputs].
- GA-2·GB-7은 같은 Root끼리 비교하므로 해당하지 않습니다.

### B2. GA-3(그리고 GA-2의 반사실 900, GA-4)이 지정한 하네스는 옛 코드를 돌린다 → 거짓 통과 위험

- **계획**: GA-3은 "하네스 `scratchpad/v3c1-p10/t5/t5_chain_b.py`"를 씁니다.
- **사실** [읽음]: `t5_common.py:9-14`가 다음을 하드코딩합니다.
  - `FRZ = …/sdmpc31_5323faa4_202609281442`
  - `WT = D:/VISSIM-merge/sim3-n31-v3c1`(= 9ed2ef0, **K 커밋 없음**)
  - `TOOLS = FRZ/…/tools`(옛 `make_replay_state_v2.py`·ps1)
  - `t5_chain_b.py:144`는 `-Root str(c.WT)`로 돌립니다.
- 그대로 재사용하면 K1–K6이 **한 줄도 실행되지 않은 채** 5323faa4 기록과 "동일"이 나옵니다. 동일성 관문으로서는 최악의 실패입니다(거짓 통과).
- **고칠 것**
  - 선언에 하네스의 FRZ·WT·TOOLS 재조준을 명시합니다. FRZ는 K6 FRZ, WT는 K6 전용 작업 트리(B3), TOOLS는 K6 FRZ입니다.
  - 각 재생의 `run_provenance`가 K6 트리와 K1 판 `state.py` sha를 가리키는지를 **통과 조건**에 넣습니다(B1의 양성 확인과 같은 검사).

### B3. P5(GA)와 P6(K7 편집)을 한 작업 트리에서 병행하면 코드가 섞인다

- **계획**
  - 작업 트리는 `sim3-n31-v3c3` 하나입니다(U12).
  - §9 P6은 "P5와 일부 병행"입니다.
  - GA-2 반사실 900, GA-3, GA-4는 SDMPC 재생입니다.
- **사실** [읽음]
  - SDMPC 재생은 `<Root>/evaluation/controllers/__tangentcache__`에 씁니다(`sdmpc_tangent_runtime.py:76`, `t5_chain_b.py:10-12`).
  - 그래서 Root는 FRZ가 아닌 **작업 트리**여야 합니다.
- 그 작업 트리에서 K7 편집이 진행되면, 재생이 K6과 반쯤 편집된 K7 코드를 섞어 import합니다.
  - 망 상수, β 키, 기준 config가 바뀌는 중이므로 GA 결과가 무효가 됩니다.
  - 반대로 GA가 실패해도 원인을 가를 수 없습니다.
- **고칠 것**
  - (a) K6에 고정한 **두 번째 작업 트리**(예: `sim3-n31-v3c3-k6`)를 SDMPC 재생 Root로 씁니다.
  - (b) T5 §7처럼 재생 전후에 "작업 트리 = FREEZE 표 바이트 동일, 캐시 목록"을 기록합니다.
  - (c) 그렇게 못 하면 P6를 P5 뒤로 직렬화합니다(벽시계 +3 h 안팎) [추론].
  - GB-9/GB-10(K7 트리 SDMPC 재생)도 같은 규칙을 따릅니다.

---

## 2. Nonblocking (중요도 순)

**N1. GA-3 판정과 K1** [읽음·추론]
- `off_ramp_storage_occupancy_veh`(`state.py:1299-1311`)는 다음 세 곳으로 들어갑니다.
  - `leader._state_accumulation_base`(`leader.py:768-777`), `objective_terms`가 `:876`에서 호출
  - `wu_distributed._system_objective`(`:799-809`)
  - `total_physical_vehicles`(`state.py:1258`)
- 그러나 control-area 목적함수가 `leader_total_objective = Ω score`로 덮어씁니다(`area_leader_objective.py:73-75`, `:85-94`). 기본 `objective_mode`도 `follower_ttt`입니다(`state.py:801`). 그래서 GA-3이 보는 Ω·held repr는 영향받지 않을 가능성이 큽니다.
- 다만 이 판단은 시험하지 않았습니다. GA-3이 다르게 나올 때 원인을 가를 수 있도록, T5 §8-1이 권한 **옛 트리 A/B**(5323faa4 FRZ, 4050 SDMPC 반사실을 PYTHONHASHSEED 0 대 2로, 약 20분)를 GA 앞에 두기를 권합니다.
- 탄젠트 트레이스 비교(`operations`, `event_counts.primal_comparisons`, `reverse_sweeps.nodes/tape_bytes` 등 19키 [실행])는 **AD 테이프 연산 수**까지 같아야 합니다.
  - 따라서 K4의 "키 없음" 경로는 값이 비트 동일한 것만으로 부족합니다. Dual 연산과 비교를 **하나도 더하지 않아야** 합니다. 명세에 적어 둡니다.

**N2. GA-1의 ulp 허용 범위** [읽음 T5 §4]
- 원본 R-obs 결정은 프로세스마다 해시 시드가 달랐습니다. 정렬된 순서가 어느 "계열"과 같은지는 상태 값에 따라 다릅니다.
- 그러므로 "T5가 찾은 4필드"가 아니라 "그 4필드가 **61개 중 어느 결정에서든** ≤2 ulp"로 적어야 합니다.

**N3. K3(10490) 주장 범위와 시험**
- 유일한 표 [실행]
  - 수송 표 `per_lane_veh_per_cycle`은 0.71 < 0.99 < 1.44 < … < 4.2로 순증가합니다. 2차로 미터도 배수라 유일합니다.
  - 측정 곡선은 10490 하나이고 {2: 1.0, 3: 1.0}만 겹칩니다(`config_n31_v2.json:8036`, reference `:8000`).
  - 따라서 "가장 낮은 녹색 유지"는 나머지 표에서 **사상으로서 항등**입니다.
- SDMPC 경로 [읽음]: 공유 녹색이 상자에 있으면 `leader_seed_domain`과 `_physical_meter_points`의 디코드가 죽습니다(`joint_owner_neighbors.py:1087`, `physical_ramp_branches.py:395`). 그래서 SDMPC에서는 "옛 코드가 죽던 상태에서만 달라짐"이 맞습니다.
- 그러나 다음 경로에서는 틀립니다 [읽음].
  - 규칙 프로필 `alinea_meter_step`(`diagnostic_profile.py:227-251`)의 키는 `(|서비스−요청|, |g−이전|, −g)`입니다. 이전 녹색이 4·5일 때 3을 고를 수 있었는데, 정규화 뒤에는 고를 수 없습니다. 옛 코드가 죽지 않던 곳에서 동작이 바뀝니다.
  - 기록된 녹색 3은 이제 `prepare_control:265-269`, `diagnostic_profile.py:308`, `:233`에서 거부됩니다.
  - 이번 런 목록에는 이 경로가 없습니다. RM 팔은 sim3의 `fast_fixed_profile.py`를 씁니다(`s31_v3c1rm/prepared/rule_runtime.txt` [실행]). 그러니 문장만 고치고, R-4에 ALINEA 사례를 넣으면 됩니다(R6과 연결).
- R-4의 `==`는 dict **순서와 키 타입**을 보지 못합니다.
  - 순서가 쓰이는 곳: `allowed` 순서는 `sdmpc.py:328`에서 정해지고 `:388`·`:425`의 `min` 열거와 결정 metadata에 그대로 나갑니다. `str` 키는 모든 `str(int(g))` 조회의 전제입니다.
  - 순서를 보존하는 필터(10490에서는 `'3'`만 삭제)로 구현하고, `list(items())` 동일 시험을 두기를 권합니다. 예컨대 문자열 정렬로 재구성하면 `'0','10','2',…`가 됩니다.
- 규칙 이름을 "가장 낮은 **허용** 녹색(0 또는 ≥ `min_green_sec`, 지금 2.0)"으로 고칩니다.
- 측정 곡선은 결정마다 `lane_plant_runtime.py:482-486`에서 다시 설치됩니다. 그래서 거부 검사는 configure만이 아니라 그 설치 경로에도 둬야 합니다.

**N4. 단일값 사상의 "조용한 되돌림"** [읽음]
- 분포형 번호가 쓰이는 경로는 없습니다. 근거는 다음과 같습니다.
  - VBS 허용 목록은 생성 상수뿐입니다(`run_real_world_stackelberg_controller.vbs:294` 기본값을 `lane_native_b110.vbs`가 덮음). `ExpandEnvironmentStrings`로 덮을 수 없습니다.
  - 실행 러너는 핀과 같습니다(`launch_plan.py:153-158` sha 핀, `obs150_contract.validate_tuning_v2:205-206` `execution.signal_vbs_config` = 핀).
  - 직전 적용 VSL은 action **JSON**의 명령 공간에서 읽습니다(`lane_plant_runtime.py:613-635`). CSV `speed_kph`를 명령으로 다시 읽는 컨트롤러 코드는 0건입니다.
- 남는 구멍은 거부가 일어날 때의 처리입니다.
  - `ERROR=ACTION_CSV_CONTRACT`(`:1426-1436`)와 `VSL_COM_WRITE_READBACK`(`:1459-1463`)은 `decisionsFailed++`만 하고, 그 구간은 직전 DSD로 계속합니다(`:1241-1251`).
  - 그래서 GB-5의 `DECISIONS_FAILED 0`·`ERROR= 0`을 **모든 제어 런의 상시 관문**으로 적으라고 권합니다(J1 사전 선언 포함).

**N5. V-5/K5 명세 모순** [읽음]
- 계획은 "사상에 없는 값은 ValueError"이고, 목록 V-5 시험은 "120/95 거부"입니다.
- 그러나 writer는 먼저 `nearest(value, vsl_set ∪ {120})`(`AD:688-689`, `:12651-12657`)로 반올림합니다. 그래서 95는 90으로, 다시 91로 **조용히** 바뀌고 거부되지 않습니다.
- 사상이 있을 때 할 일:
  - `|raw − snapped| ≤ 1e-9`를 요구하고, 아니면 ValueError로 막습니다.
  - 120 확장을 뺍니다.
  - 이 순서를 명세와 시험에 적습니다.
- SDMPC 블록 0은 `min(a['allowed'],…)`에서 정확한 허용값을 냅니다(`sdmpc.py:391`). 그래서 엄격화해도 정상 경로는 그대로입니다[추론].

**N6. V-1 명세 "command ≥ maximum: 1"** [실행 계산]
- 문자 그대로 구현하면 110의 Dual 좌도함수가 0이 됩니다. 그러면 T9와 GB-8의 "110 탄젠트 ≠ 0"이 깨집니다.
- Lagrange 형은 110에서 **정확히 1.0**이고(계산 확인), 기울기는 0.010840입니다. 그러니 c ≤ 110 전체에 다항식을 쓰고 분기는 primal > 110 거부에만 두면 됩니다.
- 80 미만으로 외삽한 값은 b(75) = 0.674로 단조입니다. T9가 80에서 중앙차분을 쓰므로 80 미만을 거부하면 안 됩니다.

**N7. V-9의 실제 위치와 빠진 검사**
- `validate_tuning_v2`는 `make_config_n31`이 아니라 `evaluation/controllers/obs150_contract.py:192`에 있습니다. 생성기와 런타임이 모두 호출합니다. 목록 V-9에 이 파일을 넣어야 GB-3 허용 diff와 맞습니다.
- 추가 검사를 권합니다.
  - 사상의 정의역 = `vsl_set`
  - 사상이 단사일 것
  - `speed_scale.levels` 키 = `vsl_set − {max}`
  - 사상의 상 ⊂ 핀된 망의 DSD

**N8. CHANGE_RULES는 이미 DSD 추가를 통째로 받는다** [읽음]
- `repin_scenario_v2.py:307`이 `'desSpeedDistributions': {'added': True}`입니다.
- `V3C3_ADDED_DISTRIBUTIONS` 열거가 의미를 가지려면 characterize_changes가 이 절의 `added`를 **열거 목록과 정확히 같음**으로 좁혀야 합니다. 이 목록에는 팩 대비 v2 시절 추가분도 포함해야 합니다.
- 그러지 않으면 실수로 들어간 다른 분포(예: 1단계 94)도 통과합니다. GB-0 빌드 검사가 막아 주지만, 도구 자체의 보증은 약합니다.

**N9. GB-1 정의 보강** [실행]
- NC 런의 오류 파일은 셋입니다.
  - `run/<net>.err`(200 B, 로드)
  - `run/<net>_001.err`(약 300 KB, 시뮬 경고·차량 번호)
  - `prepared/network/VISSIG_Controller.dll.err`(464 B, v3c1·v3c2 동일 `f144ab0c`)
- 셋 다 경로나 시각이 없어 바이트 비교가 가능합니다. 계획은 `_001.err`를 빠뜨렸는데, 가장 정보가 많은 파일입니다.
- `run.json runner_sha256`이 v3c2 NC와 같다는 것(`bf07acda`, s41/43/47 확인)과 VISSIM 빌드가 같다는 것을 **전제 조건**으로 넣습니다. 그래야 불일치를 망 탓으로 돌릴 수 있습니다.

**N10. GB-13(RM 팔 900 s 접두 동일)은 근거가 없다** [실행]
- v3c1 RM과 NC의 prepared를 비교했습니다. `vehicle_recording.csv`는 같지만 `native_simulation.csv`와 평가 출력(knr/lsa/rsr/ldp)은 다릅니다.
- 접두 동일은 그럴듯하지만, v3c1 RM s31 대 NC s31 FZP로 확인한 적이 없습니다.
- 동결 전에 기존 v3c1 자료로 900 s까지 확인하거나(fit 시드라 허용), 아니면 "보고만"으로 낮춥니다.

**N11. 목록 누락** [실행 grep, §3]
- `N31D/tests/test_n31_urban_batch1.py:59`
  - `values['generated'] = '2026-09-28'  # the v3c1 re-pin date of every batch-1 table`
  - 5323faa에서 실제로 바뀐 줄입니다. C-5 목록에 없습니다.
- `evaluation/controllers/obs150_contract.py`(N7)
- 이월 사전값 항목이 목록에 없습니다. v3c1 목록 MA-1에 해당합니다.
  - b110 segment_params(`res10_b110_20260923/…/segment_params.json`), boundary fit
  - 10490 측정 곡선(R-5 데이터 불변)
  - 계획 §4 표에만 있고 목록 항목은 없습니다.
- `evaluation/controllers/physical_movement_routes.py:456`(docstring "network v3c1"). C-10은 `:571`만 적었습니다.
- `evaluation/controllers/diagnostic_profile.py:29-36, :262-266`
  - 물리 속도 ∩ 명령 속도를 가정하고, 120 기준을 둡니다.
  - 단일값 가족과 맞지 않지만 지금 쓰는 경로는 아닙니다. "비호환"으로 CONTRACT에 적습니다.
- v3c1 목록에 있던 `grep` 기록(패턴·범위·건수)과 `step3a_drift`가 v3c2 목록에는 없습니다. 완전성 주장이 기록으로 남지 않습니다(N17).

**N12. 번호 겹침** [읽음 N1F 계획 `number_overlap_note`]
- 분포 81/91/101과 FW_W desSpeedDecision 81/91/101(`RW_EXPECTED_VSL_DSD_IDS`)이 번호가 같습니다. 그래서 CSV 행이 `dsd_no=91,…,speed_kph=91`처럼 보일 수 있습니다. R3과 CONTRACT에 적습니다.
- 선택안: 사상이 있을 때 VSL 행 metadata에 `vsl_command=90` 토큰을 더합니다.
  - VBS `ExperimentMetadataValid`는 필수 토큰 3개만 봅니다 [읽음].
  - 그러면 VBS를 바꾸지 않고도 CSV만으로 명령을 복원할 수 있습니다. 키가 없으면 비트 동일입니다.

**N13. FW_W도 사상된다**
- 사상은 66행 전부에 적용되므로 FW_W 명령 < 110도 81/91/101로 쓰입니다.
- FW_W plant 법칙은 `min(no_vsl, (1+α)·vsl)`(`metanet.py:93-96`)이고 단일값에서 맞춘 적이 없습니다.
- QUALIFICATION에 적습니다.

**N14. K2와 금지 시험**
- `test_tools_replay.py:143-158`이 `compare(case, 110.0)`과 `(case, 120.0)` 위치 인자를 씁니다. 이 시험은 돌릴 수 없으므로 깨져도 모릅니다.
- `compare(out_dir, vsl_expected)`의 의미를 그대로 두고, 새 소속 검사는 `--tuning` 경로에만 붙인다고 명시합니다.

**N15. U4 판단 기준**
- 보간 후보 선택은 T9 통과 여부보다 **110 좌기울기**(R8)로 해야 합니다 [실행 계산].
  - 3차: 0.010840
  - 구간선형 마지막 구간: 0.009932
  - L1: 0.009091
- SDMPC가 tangent-v1으로 110을 떠날지는 이 값이 정합니다. 구간선형도 매듭에서 한쪽 차분으로 T9를 돌리면 시험할 수 있습니다.
- 사용자 결정문은 "수준별 척도 추가"뿐이고 수준 사이 법칙은 정하지 않았습니다. 그러니 U4는 결정 사항이 맞습니다.

**N16. U5-a "선택 가능"의 실체**
- 생성기 옵션으로만 있으면 메모리 규칙("config 밖 게이트는 죽은 코드")에 걸립니다.
- GB-2에 L1 가족 한 벌의 `configure-check t=1`(임시 폴더)을 넣고, 그 가족의 발사 경로(plant·obs150 사이드카·VBS 핀)를 문서에 적기를 권합니다.

**N17. 재핀 전 drift 기준선**
- v3c1 재핀은 `step3a_drift`로 옛 망에서 생성기를 다시 돌렸습니다.
- 이번에도 K1 전에 기준 트리에서 `--check` 연쇄와 `preflight_tuning_paths` ×3을 한 번 돌립니다. 그래야 GB-3 diff에서 기존 drift를 가를 수 있습니다.

**N18. H-2와 그 밖의 `set` 순회** [실행 grep, 읽음]
- `evaluation/controllers`와 NumSim models/controllers에서 `for … in set(`이 걸린 곳을 모두 봤습니다.
  - `AD:4457`(키별 max), `AD:8562`(키별 max)
  - `urban_queue_model.py:1424`(키별 행 합)
  - `distributed_coordinator.py:3537`(max)
  - `physical_urban_transport.py:527`·`:821`(키별 보존 검사)
  - `area_runtime.py:71`(소속만)
- 모두 순서에 무관합니다. 원소를 가로지르는 float 합은 `state.py:1306` 하나입니다.
- 견고성을 위해 `sorted(…, key=str)`을 권합니다. 다른 설정에서 값 타입이 섞이면 TypeError가 나기 때문입니다.

**N19. U2-c(s37 FZP 해시 도구)**
- 판정 한 단어라도 봉인 출력을 읽는 일입니다. v3c1 관행(run.json 두 필드만)을 따라 **허용하지 않음**을 권합니다.

**N20. 기타**
- K6 FRZ를 "v3c1 + 결함 수정" 재생 트리로 남긴다고 명시합니다. K7이 v3c1 파일을 빼면 5323faa4 FRZ에는 K1–K6이 없기 때문입니다.
- U2-b를 고르면 41–53 추출도 repo 명령으로 `v3c3_nc_<date>` 폴더에 영수증과 함께 만듭니다. repo 밖의 `nc_analysis/eo`(다른 드라이버)를 직접 핀하지 않습니다.
- GB-0에 v3c3 후보의 `added_block_audit` 한 번을 추가합니다. 정규식 기반이라 통과할 것으로 봅니다[추론].

---

## 3. 완전성 검사 기록 [실행]

| 패턴 | 범위 | 결과 |
|---|---|---|
| `2577209b` (v3c1 s31) | 9ed2ef0 전체, worklog 제외 | 코드·시험 10개 파일. 모두 C-1/2/3/4/5/6/7/10에 있습니다. JSON 데이터 33개는 DA-*·RA-*에서 재생성됩니다 |
| `226baa37`/`b8e7cf1f`/`ec0cd81d`/`385f40da` (fit 41–53) | 같음 | `derive_ramp_forecast_n31.py:15`, `make_config_n31.py:161` 주석, v3c1 추출 폴더. 모두 C-1/C-6에 있습니다 |
| `3eb06c63`, v3c1rm sha | 같음 | 0건 |
| `5c9e43e8`(FZP), `8752f0cd`(기하), `42515ae9`, `108debbb`, `f0ed036e`, `6c597e25` | 같음 | C-3·DA-5·DA-6·RA-*의 파생 파일과 문서뿐입니다 |
| `v3c1` (코드 `.py/.ps1/.vbs`) | 같음 | 29개 파일. `test_n31_urban_batch1.py:59`, `physical_movement_routes.py:456` 외에는 모두 목록에 있습니다. `test_n31_source_decision_guard.py`는 선언의 망 경로를 따라가므로 변경할 필요가 없습니다 |
| L1 계수 `0.94`/`1.44` | 코드 | `make_reference_config.py:23,65,69`, `make_plant_n31.py:76`, 시험 4곳 → V-3·C-2·V-10 |
| `RW_ALLOWED_VSL_SPEEDS`, `80,90,100,110`, `vsl_set` | 코드·시험 | N31 경로는 모두 목록에 있습니다. `diagnostic_profile`, `generate_real_world_distributed_players`, `validate_baseline_snapshot`, `test_action_csv_contract`는 다른 설정용입니다 |
| 110 전용 가정 | N31 tools·컨트롤러 | `make_replay_state_v2.py:234-242`·`:329-330`, `n31_common.py:213-218`(K2) |
| `speed_kph`를 km/h로 읽는 분석 도구 | — | `audit_lever_utilization.py:93-94`(`==80`), `audit_area_live_actuation.py:132-135`, `com_execution_equivalence/verify_pair.py`. R3에 해당하고 코드 경로에는 없습니다 |

그 밖에 확인한 사실 [실행]
- 다음 sha가 계획과 같습니다:
  - 증거 E1–E5
  - `v3c2_edit_receipt.json`(`cf8b0cb2`), N1F 2단계 계획(`d0e8fdba`), `fit_results.json`(`4091d6e1`)
  - L2 = (1.33, 0.87, m_v 정확값), `DECISION_v3c2_adopt.md`(`de71def6`)
- 3차 Lagrange 수치가 계획과 같습니다: 매듭 정확, 110에서 1.0, 기울기 범위 0.008716–0.010840, 2차식·직선의 110 값 0.98864/0.98989, 구간선형 꺾임 12 %.
- N1F 적합식은 b = m_v를 속도·ρc·형상 세 곳에 씁니다(`n1f_fit.py:126-129`, `:566-568`, `:584-586`). `freeway_fd.py:39-46`의 구조와 같습니다.
- 구성 1과 14는 차종과 비율이 같고 DSD만 40/30에서 110으로 바뀝니다. 컨트롤러·생성기에는 vehComp를 읽는 곳이 없습니다.
- RM 팔 규칙 런타임은 sim3 `fast_fixed_profile.py`라서 K3의 영향을 받지 않습니다.

## 4. 관문 동결 전에 할 일 (순서대로)

1. B1: GA-1 허용 목록에 `run_provenance`의 경로·sha 필드를 열거하고, K6 코드가 실제로 실행됐는지 양성 확인을 넣습니다.
2. B2: GA-2·3·4 하네스의 FRZ·WT·TOOLS를 재조준하고, 재생 provenance 검사를 통과 조건으로 넣습니다.
3. B3: K6 전용 작업 트리를 만들거나 P5→P6를 직렬화하고, 재생 전후 트리 무결성을 기록합니다.
4. 문장만 고치면 되는 것: N2, N3, N5, N6, N9. 목록 보강: N7, N11.
5. (선택) N1의 옛 트리 A/B 20분, N10의 v3c1 RM 접두 확인을 GA 전에 해 둡니다.
