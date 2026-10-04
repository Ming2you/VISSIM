# OPT1_PREDECLARATION — SC1001 EB 결합 항목 안 1: 추정기·하네스·관문 사전 선언

- 동결: 2026-10-01 KST. 이 파일의 sha256은 같은 폴더 `OPT1_PREDECLARATION.md.sha256`에 있습니다.
- 동결 시점 상태
  - SA 코드는 아직 어디에도 없습니다. 구현 워크트리도 없습니다.
  - 아래 값 중 SA plant 결과를 본 것은 하나도 없습니다.
  - 이번에 돌린 것은 §8의 읽기 전용 탐침(배포 코드 무변경, 템플릿 호환·상태 수 세기)뿐입니다.
- 근거 문서: 구현 명세 `OPT1_SPEC.md`(같은 폴더), 선택지 `<E>/SC1001EB_OPTIONS.md` §6, F1 `<E>/F1_STOPLINE.md`, F2 `<E>/F2_FORECAST_ACCEPT.md`, PR `fww-struct/FWW_STRUCT_PROPOSAL.md` F12–F14.
- 표기: [실행] 명령으로 확인 / [읽음] 파일·코드에서 확인 / [계산] 입력을 밝힌 산술 / [추론]
- 경로: `<E>` = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/sc1001eb`, `<O>` = `<E>/opt1`, `<P>` = `<O>/probe`, `<T>` = 같은 scratchpad의 `termcost`, `<F2>` = `<E>/f2`, `<K6>` = `D:/VISSIM-merge/sim3-n31-v3c3-k6gate`(54d821c)

## 0. 요약 (사용자 질문 포함)

- **기존 FZP로 합니다.**
  - 추정기 재계산(E1·기하·사건 표)은 v3c3 NC FZP(fit 5시드)에서 기존 스크립트를 다시 돌리면 됩니다.
  - 섬(island) 관문(127 접근·포트·차로군·사건 체제)은 FZP로 초기화한 상태에서 **배포 LOR·UFA·SA를 그대로 돌리는 하네스(FH)**로 판정합니다. 5시드 × 9상태 = 45상태이고, 그중 VISSIM 사건 상태가 14개, 비사건 상태가 31개입니다 [실행 `<P>/p4_states_grid9.json`].
  - **새 다시드 R-obs VISSIM 런은 없습니다**(D-EB-10).
- FZP로 못 하는 것은 두 가지이고, 이미 있거나 어차피 생기는 R-obs를 씁니다.
  - (i) 배포 관측 경로(obs150·어댑터 투영): FZP에는 obs150 묶음이 없습니다. 재핀이 어차피 돌리는 v3c3-s31 R-obs로 확인합니다(DP).
  - (ii) FW_W 관문(450 s·장기): FW_W 하류 외부 상태(SC1004·10638·10645)가 함께 맞아야 합니다. 이미 있는 v3c1-s31 R-obs 템플릿 9개로 판정합니다(TL, OBS판).
- **FH 실현 가능성 = 예**
  - v3c1-s31 R-obs 포착 템플릿이 `<K6>` 트리에서 F2 OBS H3 잡으로 그대로 돌았습니다(82.7 s). termcost 트리 결과와 **숫자 필드 47,861개 차 0, 목적값 513.3271772837957 동일**이었습니다 [실행 `<P>/p3_compare_OBS_002700_H3.json`].
  - 이식에 필요한 배포 함수가 모두 있습니다: 포트 생성자(CH:76), 프레임 셀 배정 `bin_frame`(LPR:547), ledger 재시드 `seed_from_projection`(AR:41-57).
- **벽시계 추정**(에이전트 작업, §7): 직렬 약 1.5–2일, 하네스 잡 3개 병렬이면 약 1일입니다. 계산은 실측 잡 시간(H3 68–91 s, H42 40–44분)으로 셌습니다. 선택지 문서의 6–8일은 사람 작업일 단위에 다시드 R-obs 런을 전제한 값이었습니다.

## 1. 추정기 값과 출처 (SA plant 전에 고정)

| 양 | 값 | 출처 | v3c3 재계산(G-EB-0) |
|---|---|---|---|
| s_SG2 (E1) | **1783.399209486166** veh/h/차로. 포화 주기 253/260, 시드별 1,750.2–1,809.6, LOSO [1,776.946, 1,791.373] | `<E>/out/a1_stopline.json` (sha256 `9d74136840a960311f1f507488d815e82b2bcd16cbc6f1a1770ff513bebb34d1`). 선언 = `<E>/tools/a1_stopline.py` docstring **sha16 `77304deded2de68a`**. 스크립트 sha256 `b437988a5a19a2411fafc86e0c4b83fb716db55380bec644d72268b6d5b9825f` (= 실행 전 기록 `b437988a5a19a241`, `<E>/out/a1_script_sha_before_run.txt`) | 같은 스크립트를 v3c3 추출에 다시 돌림. 기대값은 위와 **비트 동일**(GB-1: v3c3 NC 궤적 = v3c2). 다르면 v3c3 값을 쓰고 차이를 보고. [1,500, 2,200] 밖이면 정지 |
| s_SG5 (E1) | **2060.625**. 포화 80/260, LOSO [2,052.0, 2,071.43] | 같음 | 같음 |
| plant 녹색 | p3 45 s, p4 24 s (주기 150, 황색 3) | F1 §2; graph `reference.green_times` | 변경 없음 |
| 그룹 용량(주기 평균) | SG2 1783.40 × 2 × 45/150 = **1,070.0**, SG5 2060.63 × 24/150 = **329.7** veh/h | [계산] | – |
| 구성원 상한 | E·S **3,566.80**, N **2,060.63** veh/h | s_g × n_g | – |
| link 127 길이 | **629.7760393736908 m** (3차로) | `<E>/out/g1_inpx.json` (sha256 `69d4a5b5b1ecb6908898d0292ceae3571e6d4d690adc4445731ee6e69281bab0`, 5시드 추출 sha12 `910bc37a8d69` 동일) | v3c3 s31 INPX에서 g1 재실행. 0.01 m 넘게 다르면 정지 |
| 정체 간격 | **6.0 m** | plant `urban_avg_vehicle_length_m`(LPR:296-298), 실측 127 중앙 5.94–6.00, 10491 6.03–6.10 (F1 §5) | – |
| S_g (기하, D-EB-5) | **S_SG2 = 209.92534645789693**, **S_SG5 = 104.96267322894847** | 길이 × 차로 / 6.0 [계산] | g1 재실행값으로 |
| 착지 → 정지선 거리 | **10491: 689.97277577 m** = (301.927 − 239.38422) + 627.43. **10481: 417.15855397 m** = 627.43 − 210.27145 | INPX 위치(g1); 정지선 기준점 627.43 = 127 출발 커넥터 10368 @627.429 (U8C `STOPLINE_FROM_POS_M`, MERGE). 1 m 커넥터 10777은 U8C 관례대로 뺌 | g1 재실행값으로 |
| 포트 회전 몫 β_g | SG2 = 0.7193088 + 0.0716429 = **0.7909516**, SG5 = **0.2090484** | 실행 중 cfg β(`SC1001_off{W,E}_to_*`, W_RAMP 0 제외, 결정 1117과 같음) [실행 graph.json] | 실행 중 값(새 값 없음) |
| 커넥터율 | `cfg.network.movement_capacity_veh_h × 차로`(10491 1, 10481 2) | LOR:51·:56 direct 관례(선택지 §3.3 "현행 스칼라") | 실행 중 값 |
| 접근 속도 | max(129 ∪ 127 위 움직이는(≥ 1 km/h) 차량 평균, **20 km/h**), 지평 동안 유지 | U8C u8b 정의 | – |
| 합류 규칙 | **지퍼 1:1**(남는 몫은 상대에게) | VISSIM "127 @210.3 지퍼 합류" (선택지 §1 표) | – |
| 129 꼬리 | 도시 게이트 저장 소유. pos ≥ 239.384에서 경로 1132:2인 차량 = `port:OR_D_W` 꼬리표 | 선택지 §3.1 관측 규칙 | – |
| 도시 입장 | 무조건(선언 근사) | SPEC §5.6 | 위반량 보고 |
| 정지·빈 정의 | 정지 = 속도 < **1.0 km/h**, 빈 = int(pos / **7.0 m**) | VBS:352·:3518·:3545·:3854 | – |
| 출신 사전 몫(보고용) | OFF_W 0.6103 / OFF_E 0.1966 / URB 0.1931 | a1_stopline `origin_share_sat` | 재계산값으로 |

- E1 재계산 입력: v3c3 FZP s31/41/43/47(`D:/VISSIM_runs/20261001_v3c3/s{seed}_v3c3nc/run/vissim_eval/baseline_s{seed}_v3c3nc_001.fzp`, GB-1 PASS)과 **s53은 v3c2 FZP**입니다(`D:/VISSIM_runs/20260930_v3c2/s53_v3c2nc/...`). K7 RA-1(8892c91)이 같은 대체를 선언했습니다(v3c3 s53 런이 run.json을 쓰지 않음).
- 추출은 `<E>/tools/x1_extract.py`(sha256 `564256eed2cb171120869073a514a2bccfb885613a5dbd1d08aa5007b61610f1`)의 사본에서 **FZP 경로만** 바꿉니다. 산출 parquet sha를 v3c2 parquet(s31 `bec558fe5c3c498125a39571f0485423a796480ca13d9b76f91b067b73511b6d`, s41 `c7faea5c46b2f75bf94a5192a75f99fff483c9cf852f714f7112c898af863504`, s43 `a43917a6de19bd1343a7702bfceb95466aad10ea1934f5c826c9d7bdf9af6fbd`, s47 `de27129e39e1131ca80289e05fc3cfceb2331897a4fa7c569c75365920d030a6`, s53 `b3e81d41f81e7a86406cd4cd68516d0946d94e7758e2d168ac78cabbb57cab6a`)과 비교해 보고합니다.

## 2. 하네스 정의

### 2.1 FH — FZP 초기화 섬 하네스 (섬 관문의 판정 하네스)

- **바탕**: `<F2>/code/f2_worker.py`(tc_worker 사본 + 메모리 훅; C00 비트 동일 확인 P §1)를 구현 트리로 옮긴 것입니다. `W`와 PYTHONPATH만 바꿉니다.
  - 이번에 `<K6>`으로 옮겨 시험했습니다. 82.7 s, 결과 비트 동일, `<K6>` `git status` 전후 빈 결과 [실행 `<P>/f2k6/`].
- **실행하는 배포 코드(수정 없음)**
  - `rollout_endpoint.evaluate_price_point` → `lane_coupling.run_interval`(LC:55-120) 매초 순서
  - LOR(포트 배수·`capacities`·`land`), DelayedPort(CH:76-170)
  - UFA `urban_substep_accounted`(도착 분할·게이트·서비스·receiving), UQM 보조 함수
  - SA(키 있음 팔)
  - AFA·LFR(본선), area ledger(`assert_stocks`)
  - 즉 **현재 P-comp처럼 off-ramp 출구를 관측 방출률로 바꾸지 않습니다.** 포트 방출·포트 만차·본선 진출 차단이 모두 plant 안에서 내생으로 생깁니다.
- **외부(template)**: 같은 T의 v3c1-s31 R-obs 포착 템플릿 `<T>/out/{T:06d}/capture/template.pickle`(T ∈ §3.1). cfg·런타임 객체·섬 밖 도시 재고·다른 포트·미터 큐는 이 템플릿 값입니다.
- **FZP 이식**(T 프레임 = FZP SIMSEC T+0.1, 시드의 FZP)
  1. FW_W·FW_E 셀 밀도·속도·흐름: 배포 `bin_frame(geometry, rows, road, drop_before_start=True)`(LPR:547-576). 빈 셀은 셀 v_free(LPR:617-623과 같은 규칙). 차로 프로파일은 템플릿 값.
  2. 포트 10491·10481: `DelayedPort(cap, length, port_profile 속도, [[pos, speed, lane]…], T, interval_service=True)`(LPR:388-390과 같은 인자). 거울 저장 `urban_link_storage[key] = cap − stock`.
  3. FW_W 진출 분율(`configs['FW_W'].network.off_ramp_split_ratio`): FZP [T−150, T] 창의 1132 분기 통과 수로 정하고 지평 동안 유지(배포 `off_split_ratio`와 같은 closure).
  4. 섬 도시 재고: link 32·129·127의 차량을 provenance에 맞춰 다시 씁니다(`storage:in_SC1001_W`, W·off·E 접근 movement 몫).
     - 큐는 **배포 연산자**로 냅니다. FZP 프레임에서 러너와 같은 `queue_bins`(빈 7.0 m, 정지 < 1.0 km/h)를 만들고, `ADP._contiguous_stopline_queue_by_lane`에 넣습니다.
     - 그다음 **SA.initialize**(키 있음 팔) 또는 배포 1/14 귀속(키 없음 팔)을 그대로 부릅니다.
  5. 진입(OBS): FW_W·FW_E 진입률 = EO `boundaries_30s.csv`의 누적 진입 차분을 150 s 블록으로 묶은 값(F2 `forecast` 훅과 같은 자리). 원천: `D:/VISSIM_runs/20260930_v3c2/reports/nc_analysis/eo/s{seed}_v3c2nc/` (K7 RA-1: v3c3 추출과 바이트 동일). origin 큐 0(C6).
  6. 도시 게이트 수요 `demand.urban_boundary['in_SC1001_W']`: FZP link 32 진입 수를 150 s 블록으로(같은 훅 자리).
  7. ledger: 이식 뒤 `area_runtime.seed_from_projection(state, cfg, physical)`(AR:41-57, 안에서 `assert_stocks`)로 다시 시드합니다.
- **신호**: NC는 고정 시간입니다. 템플릿 C00 action(같은 고정 계획)을 쓰고, SC1001 위상 정렬은 H-0에서 확인합니다.
- **선언된 차이**
  - FD1: 섬 밖 도시·다른 포트·미터 큐·SC1004 국소 런타임은 v3c1-s31 템플릿(다른 시드·망)입니다. → FW_W 하류(셀 ≥ 10)와 SC1001 하류 receiving은 보고만 합니다.
  - FD2: 진입은 관측(OBS, 배포 불가 오라클). FD3: 진출 분율은 T 창 값으로 고정.
  - FD4: FZP 프레임 해상도 5 s(러너 1 s 대신). 큐 빈은 같은 정의입니다.
  - FD5: VSL 명령 110(NC)이고, 꼬리표 없음 = 전부 110과 같습니다(LPR:672-697).
  - FD6: obs150 묶음이 없으므로 `observe_state`·`validate_*`는 거치지 않습니다. 대신 H-1이 연산자 동등성을 확인합니다.
- **팔**: BASE(구현 트리, 키 없음), SA(키 있음). 진단 팔: SA+WAVEJ(F2 `fww_net` 값 w 22.3, ρ_jam 149), SA+SGOBS(S_g = 5시드 첨두 관측 최대의 중앙값: 차로 1–2 **164**(시드 164/169/161/164/156), 차로 3 **26**(30/26/24/23/31); `<E>/out/a1_stopline.json` `seeds.*.storage.127_lanes12/127_lane3.max`, F1 §5). 둘 다 보고만 합니다.
- **스모크 확인(관문 전 필수; 하나라도 실패하면 §6 대체)**
  - H-0: 이식 없이 템플릿 그대로 FH(키 없음)를 돌리면 TL C00·OBS 결과와 숫자 필드 차 0. 하네스 경로가 비활성임을 보입니다.
  - H-1: 연산자 동등성. v3c1-s31 R-obs 런 자체의 FZP(`D:/VISSIM_runs/20260928_sdmpc31_v3c1/sdmpc31_v3c1_nc_s31/vissim_eval/sdmpc31_sdmpc31_v3c1_nc_s31_001.fzp`)에서 만든 섬 관측과, 같은 T의 원자료(`<T>/replays/{T}/state_{T}.json`)를 배포 `SA.observe`에 넣은 결과를 비교합니다.
    - 기준: 10491·10481·127·129 차량 수는 ±1 이내, 127 차로별 연속 큐는 ±2 이내. 9상태 중 8상태 이상(프레임 0.1 s 차 허용).
  - H-2: 이식 뒤 `seed_from_projection` 통과, LOR `assert_mirrors`(LOR:27-32) 통과, 섬 재고 = FZP 목표 ±1e-9.
  - H-3: 자기 이식. v3c1-s31 FZP를 같은 T의 v3c1-s31 템플릿에 이식(OBS)했을 때, T+150 W+포트가 TL(배포 투영) 값과 ±2대 이내. 9상태 중 8 이상.
  - H-4: 같은 잡을 두 번 돌리면 비트 동일.

### 2.2 TL — R-obs 템플릿 하네스 (FW_W 관문의 판정 하네스)

- 같은 f2_worker를 구현 트리에서 돌립니다.
- 상태: v3c1-s31 R-obs 포착 9개, 장기 3개.
- 팔: **OBS(판정)** / A1(보고) / WAVEJ(진단). F2 job 정의(`<F2>/code/f2_make_jobs.py`)의 값을 그대로 씁니다.
- 키 있음 팔: 하네스가 템플릿에 `SA.configure`(팔 config의 절) → `SA.initialize`(원자료 `<T>/replays/{T}/state_{T}.json`, 템플릿 `detector_mapping`)를 부르고, `seed_from_projection`으로 ledger를 다시 시드합니다. 배포 RS 순서와 같은 함수이고, 부르는 쪽만 하네스입니다.
- K7 트리는 v3c3 망을 핀하므로 v3c1 재생을 새로 포착할 수 없습니다(LPR:165-166 망 sha 확인). 그래서 기존 포착 템플릿을 씁니다 [읽음·추론].

### 2.3 DP — 배포 경로 (v3c3-s31 R-obs, 재핀 런이 생기면)
- 구현 트리의 어댑터를 `tc_capture.py`(`<T>/harness`)로 팔 config 키 있음/없음 두 번 포착합니다. RS:185·:253 배포 호출이 실제로 실행됩니다.
- 상태: 900 + 450k, k = 0…16(17상태).
- 확인하는 것: G-EB-1(d)(키 없음 = K7 HEAD 포착 동일), G-EB-2, G-EB-3(배포 투영판), G-EB-9, G-EB-11(action JSON 크기).
- 그 런이 없으면 DP 관문은 **보류**입니다. 판정(FH·TL)은 막지 않지만 승격은 막습니다.

## 3. 상태·시드

### 3.1 FH (5시드 × 9상태 = 45)
- 시드: v3c3 NC s31/41/43/47 + v3c2 NC s53. **s37(봉인)·59/61/67·`*_rm`은 쓰지 않습니다.**
- T: 900, 1200, 1800, 2250, 2700, 3000, 3600, 4200, 4950. 포착 템플릿이 있는 시각입니다(새 포착 없음).
- VISSIM 상태 분류 [실행 `<P>/p4b_states_grid9.py` → `<P>/p4_states_grid9.json`, F1 추출 parquet]
  - 사건(E): [T, T+450]에 F1 §6 FW_W 사건 창이 있거나 10491 점유 최대 ≥ 20
  - 비사건(N): [T−150, T+450]에 사건 창이 없고 점유 최대 < 20

| 시드 | 900 | 1200 | 1800 | 2250 | 2700 | 3000 | 3600 | 4200 | 4950 | E / N |
|---|---|---|---|---|---|---|---|---|---|---|
| s31 | N | N | N | N | E | E | E | E | E | 5 / 4 |
| s41 | N | N | N | N | N | N | E | E | N | 2 / 7 |
| s43 | N | N | N | N | N | E | E | E | E | 4 / 5 |
| s47 | N | N | N | N | N | N | E | E | E | 3 / 6 |
| s53 | N | N | N | N | N | N | N | N | N | 0 / 9 |
| 합 | | | | | | | | | | **14 / 31** (모호 0) |

- 분류는 v3c2 parquet로 셌습니다. G-EB-0이 v3c3 추출로 다시 세고, 다르면 v3c3 분류를 쓰고 보고합니다.
- 450 s 격자(900…8,100, 85상태)는 26 / 56 / 3이지만 새 템플릿 포착 8개가 필요하므로 계획하지 않습니다 [실행 `<P>/p4_states.json`].

### 3.2 TL (v3c1-s31)
- 9상태 분류 [실행 `<P>/p5_tl_census.json`, 그 런의 FZP]: 비사건 900·1200·1800·2250·2700·3000·3600, 사건 4200(점유 16 → 최대 29)·4950(19 → 33). P §3의 "16·19대" 두 상태와 같습니다.
- 장기: 900 H24, 2700 H42, 4950 H27.

### 3.3 DP
- v3c3-s31 R-obs 17상태(§2.3).

## 4. 관문 (D-EB-11: 기존 문턱 재사용, 새 문턱은 선택지 제안대로)

| ID | 무엇 | 하네스·상태 | 기준 | 판정/보고 | 문턱 출처 |
|---|---|---|---|---|---|
| G-EB-0 | 추정기 재계산(§1)과 sha 고정, 증거 JSON 생성 | v3c3 FZP | s ∈ [1,500, 2,200]. 기하 차 ≤ 0.01 m. E1·기하가 v3c2와 같은지 보고. 분류표 재현 | 판정(정지) | PR P0-W1, F1 선언 |
| G-EB-1 | 키 없음 비트 동일 | 단위 T2·T10·T11. TL 9상태 × {OBS, A1} H3 + 2700 H42 OBS, K7 HEAD 대 구현 트리. FH H-0. DP 17상태 포착(생기면) | 숫자 필드 차 0(타이밍 제외, `<P>/p3_compare.py` 방식), `objective_repr` 동일. K6 `lane_plant_install_check`·K3 정규화 메타데이터 동일 | 판정(정지) | 선택지 G-EB-1 |
| G-EB-2 | 구현 확인(매 스텝, 키 있음) | FH·TL·DP 전부 | #1 Σ수락_g ≤ B_g + 1e-9(구속 스텝 수 보고). #2 포트 방출 ≤ L_p + 1e-9. #3 ledger `assert_stocks` 통과, I1·I2. #4 off-ramp movement 8개 큐 ≡ 0. #5 127이 E 접근로·off-ramp movement에 주는 몫 0. #6 Q_g + R_g ≤ S_g + 도시 초과 + 1e-9. #7 미터 표·SC109 상한 동일 | 판정(정지) | PR G-F12-5 + 이 명세 |
| G-EB-3 | 한 스텝 T+150 (G-v3b (a) SC1001\|W, G-U5-127, G6-7) | **FH 45상태(판정)**, DP 17(판정, 생기면), TL 9(보고) | (a) **W + 포트**(plant Σ W 큐 + 포트 재고 대 관측 127 3차로 연속 큐 + 10491·10481 커넥터 대수): \|평균 편향\| ≤ 50 **그리고** MAE ≤ persistence MAE(T 값을 T+150 예측으로). (b) G6-7 W 정지선 큐: \|b\| ≤ 20, r ≥ 0.5. (c) G-U5-127 (b): 10481·10491 포트 편향의 짝 증분(SA − BASE) 95 % CI 하한 ≤ 0(상태 재표집 2,000회, 난수 시드 0). (d) G6-6 SC1001 W_out \|b\| ≤ 5(DP·TL 판정, FH 보고) | 판정 | 묶음 2 G-v3b (a)·G-U5-127 (b)·G6-6·G6-7 |
| G-EB-4 | 450 s | **TL 9상태 H3 OBS(판정)**, A1·FH 보고 | G-F12-1 상태별 \|FW_W(T+450) − VISSIM\| ≤ 50 (9/9). PR 완화형(중앙값 ≤ 50, 최대 ≤ 150) 병기. G-F12-2: TL 비사건 7상태에서 셀 9 v(T+450) > 60 km/h. 10491 커넥터 T+450 대 VISSIM·Ω 블록 차는 보고 | 판정 | S P0-W2, PR G-F12-1/2 |
| G-EB-5 | 장기 | **TL OBS(판정)**: 2700 H42, 4950 H27. 900 H24와 A1판은 보고 | FW_W 재고 VISSIM ±150 @6,300·6,750. 10491 기간 평균 유량 ±15 %. EB 방류(SG2 + SG5) 기간 평균 ±15 %. origin < 100. **8,550은 자름**(D-EB-7): 각 런에서 10638 차단 스텝 > 50 %인 첫 150 s 블록 이전 체크포인트만 판정. 6,300·6,750이 그 뒤면 보고로 내리고 적음 | 판정 | PR G-F12-3/4/5, F2 §4-2 |
| G-EB-6 | 사건 체제 | **FH(판정)**: 45상태 H3 + 사건 14상태 H6. TL 보고 | (a) FW_E 10481 차단 스텝 = 0(모든 상태·팔). (b) VISSIM 비사건 31상태 가운데 [T, T+450]에 plant 10491 차단(포트 여유 0)이 한 번이라도 있는 상태 비율 ≤ 0.2. (c) plant가 차단한 모든 사건 상태에서 plant 첫 차단 시각 ≥ VISSIM 127 대기 범위 ≥ 500 m 첫 시각 − 30 s(창 해상도). (d) 사건 창 3,276 m 처리량 감소 대 VISSIM −78 … −576 veh/h는 **보고**(D-EB-9). SA+WAVEJ 진단 팔 병기 | (a)(b)(c) 판정, (d) 보고 | 선택지 G-EB-6, PR F14 |
| G-EB-7 | FW_W 막힘 | **TL OBS(판정)** | VISSIM 비사건 창에서 셀 6–9 v_min 붕괴 블록 0. 셀 10–30 v < 60 km/h 150 s 블록 비율 ≤ VISSIM R-obs + 0.05(900 H24·2700 H42·4950 H27). 사건 창은 보고(D-EB-9) | 판정 | PR F13 TL 관문 |
| G-EB-8 | 허구 지렛대 | **TL 비사건 7상태(판정)**, FH 비사건 보고 | \|C11 − C00\| FW_W(T+450) ≤ 3대(C11 = `<T>/harness/candidates.py:191-199`의 SC1001 off-ramp 현시 +6/+10/+10 s). tangent \|∂FW_W(T+450)/∂g_p3\| × 6 s ≤ 3대("≈ 0"의 조작화, C11 첫 블록 폭과 같은 허용치). 사건 상태 4200·4950은 부호 보고 | 판정 | PR G-F12-6; 기울기 조작화는 이 선언 |
| G-EB-9 | G-SC109·K3 무변경 | 단위 T11, DP | SC109 movement 6개 최종 용량·spec 바이트 동일. 미터 8개 `service_by_green_veh_h`·`lane_ramp_head_service_normalisation` 바이트 동일(키 있음/없음) | 판정 | C3D §6, K3 |
| G-EB-10 | 도시 부작용 | DP·TL 판정, FH 보고 | W 구성원의 경계 allocation 구속 스텝 = 0. SC1001 하류 저장·SC1002 접근 재고, RM_C10482/10490 큐 차이는 보고 | allocation 판정, 나머지 보고 | 묶음 2 G6, PR G-F12-7 |
| G-EB-11 | 시간·미분 | FH·TL 잡 벽시계, DP 포착, 단위 T13 | H3 잡 벽시계 중앙 비(SA/BASE) ≤ 1.05. action JSON ≤ +1 %. AD 대 중앙 차분 상대 ≤ 1e-6. discrete 비교 수·연속 대 정확 도시 owner는 보고(C3D §10-8 결정 전) | 판정(앞 셋) | C3D §9.2-12/13 |
| G-EB-12 | 폐루프 | – | 이번 세대에서 돌리지 않음(D-EB-12 승인 뒤 J1-W 3시드 짝, TC 결론 (iii) 다시 돌림) | – | J1-W |

## 5. 보고만 하는 것
- G-EB-3: W만, 포트만, 127 방류 출신 몫(OFF_W + OFF_E 대 FZP ±0.10; 출신 꼬리표는 보고용), TL 판
- G-EB-4·5: A1판 전부, 900 H24, Ω 블록 차, 8,550 체크포인트
- G-EB-6 (d) 사건 창 FW_W 처리량, 사건 상태 적중률(VISSIM 사건 상태에서 plant가 한 번이라도 차단한 비율), 129 꼬리에 갇힌 10490행 대수(VISSIM ≤ 3.1대 대 plant 0)
- 진단 팔 SA+WAVEJ, SA+SGOBS(S_g = 관측 최대)
- `city_over_room_veh`(도시 무조건 입장 근사의 위반량), FH의 FW_W 하류·SC1001 하류(외부 불일치 FD1)
- G-EB-11의 discrete 비교 수, 연속 대 정확 owner

## 6. 정지·대체 규칙
1. G-EB-0이 범위 밖이거나 기하가 다르면 정지합니다.
2. G-EB-1 차이가 하나라도 있거나 G-EB-2 위반이 있으면 정지하고 고칩니다. 판정 관문은 고친 뒤 처음부터 다시 돌립니다.
3. **FH 스모크(H-0…H-4) 실패**
   - 한 번 고쳐 보고(제한 3시간), 그래도 실패하면 FH를 보고로 내립니다.
   - G-EB-3·6의 판정은 DP(v3c3-s31)와 TL(v3c1-s31)로 옮깁니다(R-obs 상태 대체). 그러면 사건 상태가 TL 2 + DP 수개로 적어지므로, D-EB-10(다시드 R-obs)을 사용자에게 다시 묻습니다.
4. DP 런이 없으면 DP 관문은 보류이고 승격을 막습니다.
5. 판정 뒤 문턱·상태·정의를 바꾸지 않습니다. 바꿔야 하면 새 선언 파일을 만들고 이 파일을 대체 사유와 함께 남깁니다.

## 7. 벽시계 추정 (에이전트 워크플로, 실측 잡 시간 기준)

| 단계 | 내용 | 에이전트 작업 | 계산(직렬) |
|---|---|---|---|
| S0 | K7 커밋 확정 대기, K7 HEAD에서 워크트리 생성 | 0.2 h | – (외부 의존) |
| S1 | G-EB-0: v3c3 FZP 4개 추출(시드당 43–44 s), a1_stopline·g1, 분류 재계산, 증거 JSON·sha | 0.7 h | 0.2 h |
| S2 | SA 모듈과 다섯 곳 분기, make_config 플래그, 증거 빌더, 단위 시험 T1–T14, 검토 한 번 | 5–6 h | 0.3 h(시험) |
| S3 | 기존 시험 회귀(금지 시험 제외) | 0.3 h | 0.5 h |
| S4 | 하네스: f2_worker 경로 전환(시험 완료), TL 키 있음 설치 훅, FH 이식 훅(FZP 프레임 추출 5시드 × 약 1분), H-0…H-4 | 3–4 h | 0.7 h |
| S5 | G-EB-1 TL: 9 × {OBS, A1} H3 × 2트리 = 36잡 × 약 80 s, 2700 H42 × 2 | 0.3 h | 2.3 h |
| S6 | FH: 45 × {BASE, SA} H3 = 90잡 × 약 85 s, 사건 14 × 2 H6(약 165 s), 진단 팔 2개 × 14 H3 | 0.5 h | 3.7 h |
| S7 | TL 키 있음: 9 × {OBS, A1} H3, 장기 OBS 3개(16 + 44 + 22분), 장기 A1 3개(보고), 2700 WAVEJ, C11/C00 7상태 × 2팔, AD 2상태 | 0.5 h | 4.6 h |
| S8 | DP: v3c3-s31 17상태 × 2팔 포착(약 30–40 s) + H1 잡 | 0.3 h | 1.2 h |
| S9 | 집계·보고서·검토 | 2–3 h | – |
| **합** | | **약 13–16 h** | **약 13.5 h** |

- **직렬**(지금처럼 무거운 잡 하나씩): 비판정 계산이 에이전트 작업과 일부 겹칩니다. 그래서 끝까지 약 **24–30 h, 1.5–2일**(밤샘 큐 포함)입니다.
- **하네스 잡 3개 병렬**(VISSIM 아님, BELOW_NORMAL; 허용될 경우): 계산이 약 5 h로 줄어 **약 1일**입니다.
- 선택지 문서의 6–8일과 다른 이유
  - (i) 사람 작업일 단위였습니다.
  - (ii) 다시드 R-obs VISSIM 런(D-EB-10)을 전제했습니다. 지금은 기존 FZP 45상태로 바뀌었습니다.
  - (iii) 하네스 이식을 하루로 잡았습니다. 지금은 경로 전환이 비트 동일로 83 s 안에 확인됐습니다.
  - (iv) H3 잡 시간을 실측(68–91 s)으로 다시 셌습니다.
- 빠진 것
  - T5 결정 재생(ps1)과 폐루프 3시드(G-EB-12)는 승인 뒤 별도입니다. VISSIM 런 3개를 병렬 상한 4 안에서 돌리면 약 3 h + 분석입니다.
  - v3c3-s31 R-obs 런 자체(재핀 워크플로 몫)

## 8. 이번 선언을 위해 한 일 [실행] (모두 읽기 전용, BELOW_NORMAL, 한 번에 하나, 쓴 곳 `<P>`)
- `p0_template.py` → `p0_template_2700.json`: `<K6>`에서 템플릿 적재 1.7 s. 섬 객체(포트 7개 DelayedPort, LOR 설명, `in_SC1001_W` 1,237.8, W 상한 413.06 / 206.53, 수용 규칙 `proportional`)를 확인했습니다. 템플릿 sha256 `5af61da64f0b1cc94cc3368de5b7ceff99f1574e283c061d9c6fafb2a61f826b`.
- `p1_step.py`(실패 기록): `urban_substep_accounted`를 결합 루프 밖에서 직접 부르면 `known_legsplit` 불변식에 걸립니다. → FH는 반드시 `run_interval` 경로로 돌려야 합니다(§2.1의 근거).
- `p2_bootstrap.py` → `p2_bootstrap_0.json`: 템플릿의 bootstrap 원자료는 비어 있습니다(`network_path`만). → 원자료는 `<T>/replays/*/state_*.json`에서 가져옵니다(`queue_bins` 7 m·차량 기록 있음).
- `f2k6/` (f2_worker의 `<K6>` 사본) + `p3_compare.py` → `p3_compare_OBS_002700_H3.json`: 숫자 필드 47,861개 차 0, 목적값 동일. `<K6>` `git status`는 전후 모두 빈 결과입니다(`f2k6/git_status_{before,after}.txt`).
- `p4_states.py` / `p4b_states_grid9.py` → `p4_states.json` / `p4_states_grid9.json`: 상태 분류(§3.1)
- `p5_tl_census.py` → `p5_tl_census.json`: TL 9상태 분류(§3.2)
- 하지 않은 것
  - 코드·config 수정, git 쓰기, VISSIM·cscript·ps1·워치독 실행
  - 금지 시험, `frozen/*` 접근, s37·59/61/67 열람
  - `<K>` 쓰기(읽기·`git --no-optional-locks` 조회만)
