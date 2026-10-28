# K8 보충 C1-2 (Declare 판) — 보충 C1 고침: Ω701 첫 상태 설명 조건 D98, 스레드 정정, 일반형 저장 용량 가드(C1G), 보고 정의(Ω701·도시도로 codex 분할·FW_E 기준 줄·DA1–DA4·VSL 줄), P0-14–18, 탐침 r2, 관문·STOP·커밋 C1-G·퇴행 숫자·비용 (2026-10-27 KST)

- **상태: Declare 판.** 이 문서는 사용자 결정 D-K9-98·99·103(Q-V6)·104·110·111·114(와 그 앞 D-K9-100·105·107)를 보충 C1 고정판에 얹는 고침 문서입니다. 쓴 때 데이터 0: 이 보충이 정하는 P0-14–18·탐침 r2·관문·재생 출력은 하나도 없습니다 [실행 19:47 KST: `TC1/out/` 에 `probe_r2`·`p0_c12` 없음].
- **고정 방법**: 이 파일의 sha256 을 `SP/K8_PREDECLARATION_AMENDMENT_C1_2.md.sha256` 과 `C1D/LOG.md` 에 적습니다. 반박 검토(ReviewDeclare)가 글을 고칠 수 있습니다. 고치면 이 판을 `SP/K8_PREDECLARATION_AMENDMENT_C1_2_r1.md` 로 남깁니다. 검토가 끝난 판의 sha256 을 고정점 파일 `C1D/AMENDMENT_C1_2_FIXED.md`(64자)에 적은 시각이 **고정 시각**입니다. 그 전에는 P0-14–18·탐침 r2·브랜치·커밋·관문·재생을 하지 않습니다(S-C1-24).
- **구속**: 보충 C1 고정판(`SP/K8_PREDECLARATION_AMENDMENT_C1.md`, sha256 `a98580dd2d787007ab961d692668c4a4042c79d7993f87af972cbc19d1f53acf`, 고정점 `C1D/AMENDMENT_C1_FIXED.md` `7083d1369c0428edfb65a36adf8c30533abefbd1ef4e102bd0eee7adebac9fbd`)의 글·값·문턱·관문은 **이 문서가 바꾼다고 적은 곳 말고 모두 그대로** 구속합니다(이 보충 §19 이 바뀐 곳의 닫힌 목록). 보충 1–34, COMPARE_RULE_B·PINS_B 도 그대로입니다. K9-3(D1·D2)은 보류 그대로입니다.
- **사용자 결정 RV-1·RV-2(D-K9-97)는 그대로입니다**: `np_only` 를 M3 와 함께 옮김, 저장 보호 하한을 g9 뺀 머리 표에 맞춰 표 안 녹색으로 내림(보충 C1 §2.4·§2.6). 이 보충은 둘을 바꾸지 않습니다.
- **표시**: [실행] 이번에 읽기 전용 명령·작은 선언 도구로 확인 · [읽음] 문서·코드·설정에서 확인(다른 보고의 [실행] 값을 옮긴 것 포함, 출처 적음) · [추론] 시험하지 않은 판단 · [계산] 이 문서의 산술. **데이터 뒤** = 자료를 본 뒤 정한 규칙·문턱(이 보충의 가드 규칙과 D98 은 모두 데이터 뒤).
- **말 규칙**: 판정 낱말은 쓰지 않습니다. 관문 결과는 PASS / FAIL / 보류 / INCOMPLETE 와 숫자로만 적습니다. 시드는 망 접두로 적고(v3c3-s31 등) 평균 내지 않습니다. Ω 숫자는 늘 ④·Ω 밖과 같은 줄·표에 둡니다. ④b 는 첫 관측 차분이 주 값입니다. 64cf 숫자에는 "다른 망, 한 시드" 를 붙입니다.

## 줄임말 (처음 한 번만 풉니다)

- **경로**: SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`, CP = `SP/c_port`, C1D = `CP/c1`, **C1D2** = `C1D/declared_c1_2`(이 보충의 선언 참조 바이트), GD = `C1D/guard`, GG = `GD/general`, FD = `SP/fwe_decomp`, VS = `SP/vsl_v3c3`, CH = `SP/codex_handoff`. GWT8 = `D:/VISSIM-merge/sim3-n31-k8`. TC1 = `D:/VISSIM-merge/k8_gate_trees/c1`. RC1 = `D:/VISSIM_runs/20261001_v3c3/reports/k8/c_port/c1`(보고 사본). LOCK = `D:/VISSIM-merge/k8_gate_trees/heavy.lock`. HO = codex 인계 사본 `D:/VISSIM_handoff/20261024`(읽기만).
- **트리**: OU = GWT8 의 c20aff1d(줄 번호는 `git show c20aff1d:` 기준). PT = 첫 탐침 트리 `TC1/trees/probe_5cdc6eb1`(패치 `C1D/tools/c1_probe.patch` sha256 `5cdc6eb1e42492945e7d412d194d6f4b1a125e9b948a46607b1b939fad2c8993`). **PT2** = 탐침 r2 트리 `TC1/trees/probe_<패치 r2 sha8>`(이 보충 §9). CX = codex 인계 HEAD 트리 `D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff`(읽기만).
- **코드 약칭**(모두 `evaluation/controllers/`): SD `sdmpc.py`, SEQ `sdmpc_sequence.py`, RS `runtime_setup.py`, PRB `physical_ramp_branches.py`, PS `projection_support.py`, **C1P** `c1_port.py`(보충 C1 의 새 모듈 C1M, 같은 파일), USG = CX `urban_storage_guard.py`(sha256 `2c24b570ca5ba6f2a81d47b9eedfde1af863713fefd9a337109e2f78b64173ab`).
- **런**: NC3 = v3c3 무제어 세 런, V-A = 우리 묶음 B1 폐루프 세 런, B = codex 제어기 폐루프 세 런, R-obs = v3c3 무제어 VISSIM 에서 결정을 계산만 한 런, VSL 단독 = v3c3 VSL 고정 런 세 개. 모두 읽기만(이름·자리는 보충 C1 줄임말 그대로).
- **plant** = 제어기 안의 교통 예측 모형. **결정** = 150 s 마다 내는 명령(예측 450 s = 150 s 블록 3개). **재생** = 기록 상태로 제어기만 다시 돌림(VISSIM 0). **plant 잡** = 기록 행동을 두고 plant 만 굴림. **연쇄 재생** = 재생 출력을 다음 결정의 직전 명령으로 이어 씀.
- SC = 신호 제어기, SG = 신호 그룹, 현시 p1–p4 = 우리 계획이 녹색을 나누는 단위. **머리** = 차로 위 정지선 신호등(또는 미터 신호등). 머리 차로 = 제어 SC 17개의 현시 머리가 있는 차로.
- **Ω701** = codex 목적 영역(Ω635 + 신호 17곳 접근로 66링크). Ω635 = 우리 옛 목적 영역. ④a = 망 전체 링크 체류, ④b = 미삽입 대기, ④ = ④a + ④b, Ω 밖 (a) = ④ − Ω, (b) = ④a − Ω. ① = FW_E(동측 고속도로) 본선 7링크, ② = 동측 국소 19링크.
- **D98** = D-K9-98 의 "Ω 팔 첫 상태 차이 설명" 조건 묶음(이 보충 §3). C29 = Ω701 지지 문서가 더한 직결 커넥터 29개. E = 그 29개로 설명되는 차이, K_E = E 가 0 이 아닌 장부 키. T1/T2 = 고친 "궤적 같음" 규칙. C0/C0E/C3′ = G-K1 동적 차이 무리.
- **가드** = 이 보충의 일반형 저장 용량 가드(키 `c1_port.storage_capacity_guard`). **C1G** = 보충 C1 의 7키 팔 C1 + 가드 키(8키, 새 배포 팔). **C1G⁰** = 가드 키는 있으나 빈 증거(원천 0)를 쓰는 시험 팔(§7). **U** = "넘음" 규칙 = (차 수 ≥ 1.0 × 길이 ÷ 6 m) 또는 관측 번짐 S. 구간 종류 A·L·F·M·MA·R(§5.1). **칸** = 차로를 자름점에서 자른 조각. **서버** = 그 구간 차를 내보내는 현시 또는 미터. **반공간 행** = 녹색 축 z 에 대한 부등식 w̃·z ≥ r. LP = 선형계획. seed = 결정 탐색의 출발 명령.
- M1–M5 = 보충 C1 미터 기구(M1 이웃 검사, M2 cap 3, M3 녹색 0 금지, M4 저장 보호 0.9, M4a 운영 seed, M4b held 유지, M5 FW_E 머리 표). G-A7 = 보충 C1 §2.6 의 하한 표 단언.
- **S17** = P0-17 (a) 가 쓴 가드 증거 파일 바이트의 sha256(§5.10). **S17⁰** = 같은 단계가 쓴 빈 증거(C1G⁰ 용) sha256. **T_C1** = C1 정책 토큰 `522eec6f32f198a12ddb78ddec10962a73c7ebc32e2d1fcbb11f95975218d865`(P0-6 [읽음 P0_PROBE r2 §2]).

---

## 0. 근거 (sha256) [실행 2026-10-27 19:47–20:10 KST, `sha256sum`]

고정 목록 `C1D2/PINS_C1_2_DECLARE.sha256`(이 보충 §16; 이 파일 자신은 넣지 않음)에 64자가 모두 있습니다. 아래 표는 앞 16자입니다.

| 대상 | sha256 (앞 16자) |
|---|---|
| 결정 기록 `SP/K9_1_J1_NOTES_20261013.md` (D-K9-96–114, :320-396) | `bfd3fc2bc8f9feab` (작업 지시 값과 같음) |
| 보충 C1 고정판 / 고정점 `C1D/AMENDMENT_C1_FIXED.md` / 선언 고정 목록 `C1D/declared/PINS_C1_DECLARE.sha256` | `a98580dd2d787007` / `7083d1369c0428ed` / `ad84aa2f64754ed8` |
| 일반형 가드 설계 r1 `GG/GENERAL_GUARD_DESIGN.md` / r0 / 검토 `GG/REVIEW_GENERAL.md` | `cffbef23ad1c1851` / `a53cb4f334a89623` / `d4914bbd6b4e1b8c` |
| 좁은 가드 설계 r2 `GD/GUARD_DESIGN_DRAFT.md` / 검토 `GD/REVIEW_GUARD.md` | `553227cddc6e15e6` / `d6c9eccd51250e25` |
| `GD/FACTS_CODE.md` / `GD/FACTS_DATA.md` | `212af2edd3172105` / `17dd03bcd0ab990f` |
| 재고 `GG/INVENTORY.md` / `GG/inventory.json` / 자료 `GG/DATA.md` / `GG/data.json` | `da6ecda4413e3755` / `c8584f367c968888` / `058f3a4bb5f889a8` / `2e2cfb38319b6813` |
| 구간 목록 `TC1/guard_general/data/segments.json`(1,142 구간) / 결정 시각 점유 `GG/work/occ.json`(1,133 구간 × 330 상태) | `ac374b01012c766a` / `cd4ba7f4d5edce57` |
| 자료 셈 `GG/work/gg_trig.py`·`.json` / `GG/work/review/gr_check.py`·`.json` / `gr_meter.py`·`.json` | `8c3f6f046e014b08`·`212774be1ce22d21` / `16c9cce3bf407977`·`be9385c6fb6c2fbc` / `074ee4681ad08eca`·`3c8b99ba2f3b811a` |
| D98 기구 셈 `GD/work/d98_probe_state.py`·`.json` / `GD/work/d98_row0.py`·`.json` | `5ea49ba218817c89`·`c6ca030fb89d7d02` / `03d154bb7917b074`·`92d6e07ebb0b6393` |
| P0·탐침 보고 `C1D/P0_PROBE.md` r2 / `C1D/C1_PROBE_RESULTS.md` / `.json` / `C1D/C1_VALUES.json` | `e467583f2f77b739` / `3ab78f9f3d0febe8` / `5b0bcfb05246cc70` / `7106e2403a61755e` |
| 옛 고정 목록 `C1D/PINS_P0_r2.sha256` / `C1D/PINS_PROBE.sha256` | `75ead5ba4b770d7e` / `5dfb83b1e8a3a9bc` |
| 옛 탐침 패치 / `C1D/tools/c1common.py` / `c1_probe.py` / `c1_p0.py` | `5cdc6eb1e4249294` / `99b98cc66fe6ce02` / `9446f0287fbaea33` / `4cd1bb1655eeca78` |
| PT SD / RS / C1P / SEQ / PRB | `41563db0606fe6be` / `fea820c166059780` / `dc74748d42d5d1ed` / `10a58b06d455af92` / `72bf55d7f8d8b43a` |
| CX USG / CX RS | `2c24b570ca5ba6f2` / `74941f0382868dd3` |
| K9-2 재생 도구 `SP/k92/bundle1/a25decl/tools/k92lib.py` | `cbe1d94f634caa12` |
| FW_E 분해 `FD/FWE_DECOMP.md` r2 / `FD/PRE_FWE.md` / `FD/VERIFY_FWE.md` / `FD/R3_REPORT.md` | `7f58ab3e624719bc` / `c7cc0e6cc629da15` / `aafad84d19bc4efe` / `0f5454de559f595e` |
| FW_E 기준 줄 `FD/out/FWE_REF_C1.json` / `.md` / 도구 `FD/tools/fwe_synth.py` / 핀 `FD/PINS_FWE_SYNTH.sha256` | `ce39344bfbbe1b7c` / `9838f39ed9ad1e0e` / `92904e95444b2b18` / `1546c82a1853a0e6` |
| DA 도구 `FD/tools/fwe_r2.py` / `fwe_r2_after.py` / `fwe_r1.py` / `fwe_r1_after.py` / `FD/verify/tools/vf_extra2.py` / `FD/verify/PINS_VERIFY.sha256` | `59017c86ff6d640b` / `6bccb4c4c6046a75` / `658828903f3abe36` / `d00dfb9b42e99505` / `3777458df2dcb941` / `7b60498a5adf2a52` |
| DA 기준 값 `FD/out/R2_after.json` / `FD/verify/out/VERIFY_EXTRA2.json` | `b25c30ad753dec75` / `29e49a519181e07f` |
| VSL `VS/VSL_RESULTS.md` r2 / `VS/VSL_REPORT.md` / `VS/VSL_RUNS.md` / `VS/PRE_VSL.md` | `9bbf83a3c320dd0f` / `01bf8a3122f2b6d6` / `b967b675f99af786` / `27452ae62ae84e7c` |
| codex 분할 `HO/derived/reporting_partition.json` / `HO/analysis/original_scripts/solo355_compare_20261014.py` / `CH/OMEGA701_V3C3.md` | `3142f69c0502f6d9` / `7fc91d604214b3ea` / `5c02894a84ed155c` |
| `CH/B_RESULTS.md` r2 / `CH/HANDOFF_RESULTS.md` r2 | `152a2f6fe0fd6c5c` / `964a23cea5548c99` |
| 망 v3c3 `.inpx` / 현시 계획 `native_clock_plan_local.json`(OU `diagnostics/controller_confidence_20260913/local_native_clock_v2/`) / 배포 튜닝 OUC | `3de889f0257d998b` / `8e28f983e12d67d5` / `c8e3ee2c99b66c25` |
| **이 보충의 선언 참조** `C1D2/c1g_guard_rule.json` / 선언 도구 `C1D/work/c12_declare.py` | `cebd6f05f7ef8c4a` / `4b4403b969ae84f5` |

- **선언 참조 바이트** [실행 20:03 KST, `c12_declare.py`(실행 전 LOG 고정; 19:51·20:02 의 앞 출력 둘은 글을 고치기 전 판이라 `C1D/work/c12_superseded/` 로 옮겨 남김), 입력 = 상수뿐, 런 자료 0]: `C1D2/c1g_guard_rule.json` = sha256 `cebd6f05f7ef8c4aee01eae0ca63bc02f0dacabcbf47aa0c9fb55196e43f6257`(정규 JSON sha `2fb6be4fead0d7a2ceeb10e578ac9afd515975ad640a37f85f3175fc64a43d6a`, 10,630 B, PN `data()` 직렬화). 이 파일이 §5 규칙의 기계 판입니다. 둘이 어긋나면 검토(ReviewDeclare)가 고정 전에 맞춥니다. 고정 뒤 어긋남이 보이면 STOP(S-C1-24).

---

## 1. 사용자 결정과 이 보충의 자리

### 1.1 결정 원문 (결정 기록 표 행 요약) [읽음 `SP/K9_1_J1_NOTES_20261013.md`]

| # | 줄 | 사용자 답 | 이 보충의 자리 |
|---|---|---|---|
| D-K9-96 | :325 | P0 도구 git grep 디코딩만 고쳐 P0-4 부터 | 끝남(P0_PROBE r2). P0-1–13 결과 유효 |
| D-K9-97 | :326 | RV-1·RV-2 수용 | 그대로(보충 C1 고정판에 이미 있음) |
| **D-K9-98** | :333 | 29 커넥터 `link_to_storage` 경로 남김. "Ω 팔 대 OFF 초기 상태 차이는 29 커넥터 위 차량을 선언된 저장소로 옮긴 몫으로 전부 설명되어야 함, 아니면 멈춤" 을 데이터 뒤 선언으로 고정. F 에 경로 효과 따로. '궤적 같음' 정의 고침 | §3 D98, §9 멈춤 2, §10 G-K1 동적·G-K2 (d)·G-D98, §12 F |
| **D-K9-99** | :334 | 스레드 = K9-2 도구 꼴(`NUMBA_NUM_THREADS` 지움). 보충 C1 §3 글은 정정 메모로. 이미 돈 P0·탐침 유효 | §4 |
| D-K9-100 | :335 | Q2 (가) → (나): 링크 129·10491 저장 한계 보호를 C1 에 더함. Q3 SG2 멈춤 그대로 | §5(일반형으로 바뀜, D-K9-107), S-C1-9 그대로 |
| D-K9-101·102 | :342-343 | C1 VSL = V-A VSL 그대로. VSL VISSIM 런 더 0 | 바꾸지 않음 |
| **D-K9-103** | :344 | Q-V6: C1 − B ①·1098 줄에 VSL 정책 차이·110 미만 결정 수·시각, 1099 ④b 흔들림 참고 크기 — "데이터 전 추가 보고 칸" | §13.5 |
| **D-K9-104** | :346-351 | Ω701 이 목적·주 보고 영역. 도시도로 = codex 분할 하나. FW_E 가 주 목표, FW_W 는 감시 | §13.1–§13.2 |
| D-K9-105 | :353 | 좁은 가드(G1–G12)를 사용자에게 물음 | D-K9-107 로 넘어감 |
| D-K9-106 | :354 | FW_E 개선 분해(오프라인) | 결과 = FWE_DECOMP r2 → §13.3 |
| D-K9-107 | :356-359 | G1 "모든 intersection 및 ramp 에 capacity constraint", G3 "문턱은 approach link capacity 초과", G2·G4–G12 권장 | §5(일반형) |
| **D-K9-110** | :374 | FW_E 기준 줄(결정 1·2·3·5·7 권장): DA1–DA4(DA1 셀 배정 = 100 m 칸 가운데; DA4 도구 `vf_extra2.py` `3777458d…` 데이터 전 고정), FW_E 글 첫 줄 = C1 − V-A·C1 − B, 그다음 C1 − NC3, §3.3 글 + FWE_REF_C1 + fwe_synth sha 를 데이터 전 보고 칸으로, 셀 5–9 기구 확인은 안 함, R3 '풀었다' 읽기는 정정 메모 | §13.3–§13.4 |
| **D-K9-111** | :375 | v3c3 짝 잡음 '모름', 64cf A1 − joint 잣대를 옆에 | §13.3 |
| D-K9-112·113 | :380, :387 | codex 고속도로만 팔 FO(별도 일) | 이 보충 밖(LOCK 만 같이 씀) |
| **D-K9-114a** | :394 | 방아쇠 U: 용량 이상(차 수 ≥ 길이 ÷ 6 m) 또는 줄 꼬리가 차로 위 끝에 닿음, 차로 단위, 데이터 뒤 | §5.2 |
| **D-K9-114b** | :395 | 미터: M4 0.9 + 줄이 미터 접근 링크까지 넘칠 때만 하한 상향(FW_E 미터 조임을 풀지 않음) | §5.7 |
| **D-K9-114c** | :396 | GG3–GG5·GG7–GG13 권장 일괄. 다음 = 보충 C1-2 Declare·Review·고정 → P0 추가분 → 탐침 r2 처음부터 | §5, §8, §9 |

### 1.2 가드 결정 GG0–GG13 과 좁은 설계 G6–G12 의 적용 [읽음 GG r1 §4.1–§4.2, 결정 기록 :394-396]

| # | 고른 것 | 이 보충의 자리 |
|---|---|---|
| GG0 | (가) 저장 용량(들어갈 차 수), 넘음 = ≥ 1.0 | §5.2 |
| GG1 | (가) U = (6 m ≥ 1.0) 또는 관측 번짐 | §5.2 |
| GG2 | (가) 차로 단위 | §5.1 |
| GG3 | (가) 짧은 구간(< 2대) 원천 제외, 받는 쪽에는 씀(판정은 GG13), 짧은 머리 차로는 위 공급 구간이 대신 | §5.1–§5.4 |
| GG4 | (가) 공급 416구간 전부(Ω701 밖 36 포함), 칸 그래프 귀속(같은 링크 안 차로 바꿈 포함), 겹침 최댓값 | §5.4 |
| GG5 | (가) 진출 착지 = 원천 | §5.1 |
| GG6 | **(라)** M4 0.9 그대로 + 미터 접근 링크(MA)까지 이어진 넘음 OR, 같은 하한 식·RV-2·G-A7 | §5.7 |
| GG7 | (가) codex 꼴 무게(겹침 최댓값, 받는 쪽 모두 참이면 −1, 같은 무게면 0), FW_E 덧무게 없음 | §5.5 |
| GG8 | (가) 오프라인 증거 파일(이름 + sha), 런타임은 읽기만 | §5.10 |
| GG9 | (가) 같은 시각 차로 프레임의 차 길이(sha 대조) | §5.2, §5.9 |
| GG10 | (가) r2 의 대상별 방아쇠(τ_A·τ_B) 버림 | §5(없음) |
| GG11 | (가) 탐침 S_G = 범주 K0–K6 첫 결정, 런마다 ≤ 7, 합 ≤ 14 | §9.4 |
| GG12 | (가) R-b 는 C1G 만 | §12.1 |
| GG13 | **(나)** 짧은 받는 쪽은 차 수만(≥ 1.0 × 용량) | §5.3 |
| G6 | (가′) D98 r2 §3(D98-4′ 멈춤, T1/T2, C0E 따로, 멈춤은 C3′ 대 C0) | §3 |
| G7 | (가) F-D98 + F-Ω 두 팔 | §12.3 |
| G8 | (가) 탐침 r2: 새 패치·도구·고정·출력 뿌리, 처음부터, 옛 HALT 묶음은 기록 | §9 |
| G9 | (가) 새 커밋 C1-G(C1-3 뒤, C1-4 앞), C1-4 가 8키 | §11 |
| G10·G11 | 일반형으로 바뀜(GG11, §5.7) | — |
| G12 | (가) C1-G 의 G-K4 에 C1 팔(가드 키 없음) 5결정 | §10 |

---

## 2. 이 보충이 보충 C1 에서 바꾸는 곳 (요약; 닫힌 목록은 §19)

1. **D98**(D-K9-98): Ω·C1·C1G 팔의 첫 상태 차이는 C29 경로로 전부 설명되어야 하고, 아니면 멈춤(§3). 보충 C1 §5.3 기대·§5.4-2 멈춤·G-K1 동적·G-K2 (d)·§9.2 F-Ω 를 이에 맞게 고침.
2. **스레드 정정**(D-K9-99): 보충 C1 §3 "발사" 줄 읽기(§4).
3. **일반형 가드**(D-K9-107·114): 새 하위 키 `storage_capacity_guard`, 새 배포 팔 C1G(8키), 편집 자리 E23–E30, 증거 파일 하나(§5–§7).
4. **P0-14–18**(§8), **탐침 r2**(§9), **관문 변경**(§10), **커밋 C1-G**(§11), **R·J·F 의 팔**(§12).
5. **보고 정의**(데이터 전 보고 칸): Ω701 주 영역, 도시도로 = codex 분할, FW_E 기준 줄(§3.3 글·RF1–RF11·DA1–DA4), VSL 줄(§13).
6. **STOP** S-C1-18–24 새로, S-C1-3·5·6·7·8·9·10 넓힘(§14). **퇴행 막기 숫자** RG-17–28(§15). **고정 목록**(§16). **비용**(§17).

---

## 3. D-K9-98 — Ω701 첫 상태 설명 조건 D98 (데이터 뒤 선언)

- **실는 꼴**: 좁은 가드 설계 r2(`GD/GUARD_DESIGN_DRAFT.md`, sha256 `553227cddc6e15e6…`) §3.1–§3.6(그 파일 :370-442)을 **글자 그대로** 아래 인용 상자에 싣습니다. 일반형 설계 r1 §3.8(`cffbef23…` :650-654)이 정한 대로 **D98-5 줄 하나만** 고쳤고, 그 줄에 `[C1-2 고침]` 을 붙였습니다(인용 상자를 만드는 조립 도구가 원문 바이트를 읽어 넣었고, 바꾼 줄 말고는 원문과 같음을 조립 때 확인 [실행]; 원문은 CRLF 파일이라 줄 끝만 LF 로 읽음).
- 인용 상자 안의 `§` 번호는 r2 문서의 절 번호입니다. 상자 안 "C1G" 는 이 보충의 일반형 가드 팔 C1G 입니다(r2 의 좁은 가드가 아님).

> ### 3.1 정의
>
> - **C29**: 지지 문서 B0 판(`physical_projection_support_635_proposal_ec2393.json`, sha `7d092b3db6e4107b47ecf751c60196e11a32120dc722d9221c1fb888d447faec`) `/controlled_approach_revision/added_unique_connector_support` 의 29개(§1.8 목록). L(c) = 같은 문서 `/link_to_storage/<c>`.
> - **상태 s** = (런 이름, T). **팔 a** ∈ {OFF, Ω} (결정 상태에서는 C1·C1G 도 §3.2 D98-5 로).
> - 계산은 설정만 합니다. P0-3 훅(보충 C1 §4 [검토 RV-8]: ADP 결정 프로그램을 `sdmpc.configure`·`install_cost_ownership` 뒤에서 멈춤)으로 `configure_runtime` 이 끝난 상태에서 읽습니다. plant 스텝 0.
> - 읽는 값
>   - P_a[ℓ][k] = `state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']`(OP:21-44 이 기록·감사; ℓ = 물리 링크, k = `storage:`·`movement:`·`ramp:` 키).
>   - R_Ω[c] = Ω 팔 `detector_mapping['physical_support_repair_provenance']['links'][c]` = {target, snapshot_vehicles, restored_count_channel, previous_origins}(PS:359-360).
>   - S⁰_a[k] = 장부 첫 재고 = {k: v['inside'] + v['outside'] for k, v in `get_ledger(state).stocks`}(CAO:735 `get_ledger`; 꼴은 CAO:505-506 첫 피연산자 `model_stock_veh` 와 같음), 첫 스텝 전.
>   - n_c = 기록 가운데 link_no = c 인 수(PS:16 `complete_records`).
> - **E_k(s)** = Σ_{c ∈ C29} ( P_Ω[c].get(k, 0) − P_OFF[c].get(k, 0) ).
> - **K_E** = {k : |E_k| > ε}. **E≡0** ⇔ K_E 가 빔.
> - **X_E** [검토 r2] = n_c > 0 인 c ∈ C29 의 대상 L(c) 와 OFF 원천(R_Ω[c].previous_origins) 저장소 이름의 합집합. E≡0 이면 X_E 는 n_c > 0 인 커넥터가 같은 대상·같은 수 칸인 경우만 남고, 그 저장소들의 값은 두 팔에서 같아야 합니다.
> - **ε = 1e-9 대** (부동소수 허용오차; 본 상태의 차는 0.5 의 배수였음, §1.8. 원천이 셋인 커넥터가 생기면 1/3 배수도 가능).
>
> ### 3.2 조건 (모두 참이어야 D98 참)
>
> | # | 조건 | 성격 [검토 r2] |
> |---|---|---|
> | D98-0 | R_Ω 링크 집합 − R_OFF 링크 집합 = C29 정확히, 그리고 c ∈ C29 마다 R_Ω[c].target = L(c) | 배선 확인(같은 문서를 읽으므로 대개 참). 본 상태 252 − 223 = 29 [실행 `d98_probe_state.json`] |
> | D98-1 | c ∈ C29 마다 n_c = R_Ω[c].snapshot_vehicles, 그리고 n_c > 0 이면 P_Ω[c] = {`storage:`+L(c): n_c}(|차| ≤ ε), n_c = 0 이면 c ∉ P_Ω | 앞 절반은 구성상 참(둘 다 PS:347-359 의 같은 행 수). 뒤 절반은 실제 확인(투영이 자르거나 나누면 거짓, OP:21-22 "after any clipping") |
> | D98-2 | ℓ ∉ C29 인 모든 물리 링크에서 P_Ω[ℓ] 와 P_OFF[ℓ] 의 키 집합이 같고 값 차 ≤ ε | **주된 확인**. 지지 문서가 다른 링크 투영을 건드리면 거짓 |
> | D98-3 | S⁰_Ω 와 S⁰_OFF 의 키 집합이 같고, 모든 키 k 에서 \|S⁰_Ω[k] − S⁰_OFF[k] − E_k\| ≤ ε | 투영 키에서는 D98-2 와 장부 씨앗(AR:41-58 `seed_from_projection`, :57 `assert_stocks`)·감사(OP:29-44)로 거의 저절로 참. 독립 몫 = `freeway:`·`origin:` 키(AR:47-51)와 씨앗 뒤 초기화가 옮긴 몫 |
> | **D98-4′** [검토 r2: r1 은 보고만] | (a) `freeway_density`, `shared_approach_state`, `offramp_route_inventory_state`, 포트 재고(`lane_offramp_runtime.ports[*].stock`), 미터 버퍼 snapshot(`lane_ramp_runtime.buffers[*]`), SA `stock`·`init_excess` 는 두 팔 비트 같음. (b) `urban_movement_queue`·`urban_arrival_buffer` 의 차이는 접근 저장소가 X_E 안인 movement·저장소에서만 허용. (c) 차이 목록은 늘 보고 | 실제 확인. C29 의 대상·원천은 모두 도시 저장고라(§1.8 표·`d98_probe_state.json`) 고속도로·포트·미터·SA 에는 닿을 길이 없음 [실행·추론] |
> | D98-5 | 같은 상태에서 C1·C1G 팔의 S⁰ = Ω 팔 S⁰ (비트 같음). M·H·가드 키는 투영을 바꾸지 않아야 함. 가드 RS 줄(E23)은 투영 입력(`detector_mapping`·`state_json`)을 읽기만 하고 바꾸지 않음을 확인 | 실제 확인 `[C1-2 고침: 일반형 설계 r1 §3.8, 원래 셋째 칸 "실제 확인(가드 RS 줄이 투영 앞에 있지 않음을 확인)"]` |
>
> - 멈춤(새 **S-C1-18**): D98-0·1·2·3·**4′**·5 가운데 하나라도 거짓, 또는 계산 못 함(설정 실패·키 없음 = INCOMPLETE) → STOP·질문. [검토 r2] r1 은 D98-4 를 보고만 두어 "초기 상태 차이가 전부 설명되어야 함, 아니면 멈춤"(D-K9-98) 보다 약했습니다.
> - 계산 가능성 [검토 r2, 읽음]: 장부는 `configure_runtime` 안 RS:555-557 → AR:282 에서 씨앗을 받으므로 P0-3 훅 자리(설정 끝)에서 `get_ledger(state)` 가 있습니다. P 는 `state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']`(AR:42, LPR:300)이고 설정 끝 값(뒤 초기화가 고친 뒤, LPR:541 재감사)을 씁니다.
> - 늘 참/늘 거짓 점검 [검토 r2]: D98-2·D98-4′ 는 다른 링크 투영이나 다른 초기 상태가 달라지면 거짓이 되므로 늘 참이 아닙니다. 본 상태 첫 행에서 차이가 정확히 K_E 세 키였으므로 늘 거짓도 아닙니다(데이터 뒤, 상태 하나).
> - 표지: "데이터 뒤 선언(D-K9-98)". 이 조건은 이미 본 상태 하나(v3c3-s31 T=1,500)의 첫 행 차이를 보고 정했습니다.
>
> ### 3.3 어느 상태에서 셈
>
> D98 은 Ω 를 품은 팔(Ω, C1, C1G)을 계산하는 모든 상태에서 셉니다. OFF 짝이 같은 단계에 없으면 설정만 따로 합니다.
>
> | 묶음 | 상태 | 수 |
> |---|---|---|
> | 탐침 plant | `/probe_plant_jobs` (R-obs v3c3-s31·s43 각 8) | 16 |
> | 탐침 결정 | `/probe_decisions_T900` 5 + 가드 상태 S_G(§5.4, ≤ 8) | ≤ 13 |
> | G-K1 동적 | `/gk0_plant_jobs` 33 (탐침 plant 16 과 겹침) | 17 더 |
> | R-a · G-RR (b) | 탐침 결정 T=900 과 같음 | 0 더 |
> | R-b | V-A 세 시드 T = 900 … 2,700 (39) | 36 더 |
> | F (c1t 단계에서만) | `/f_blind` 50 (R-obs v3c3-s47) | 50 |
>
> - 설정 1회 약 17 s(P0-3: 25회 7분 [읽음 LOG 13:44]) [계산]. c1t 전 약 82상태 × 2팔 ≈ 47 분, F 50상태 × 2팔 ≈ 28 분 [계산].
>
> ### 3.4 '궤적 같음' 정의를 고침 (Ω·C1·C1G 팔 대 OFF; H 팔은 그대로 비트 같음)
>
> | 규칙 | 상태 | 조건 |
> |---|---|---|
> | T1 | E≡0 | 지금 정의 그대로: 행별 `model_stock_veh` 숫자 잎 차 0 |
> | T2 | E≢0 | (i) D98 참, (ii) 두 팔 계열 `edges` 가 같음, (iii) 첫 행(t_end = T+1, 도시 단계) 차이 키 ⊆ K_E ∪ N1(K_E), N1 = 계열 `edges` 의 한 걸음 이웃. 그 뒤 행 차이는 보고(C0–C3 분류) |
>
> - 탐침 멈춤 2(보충 C1 §5.4-2): "Ω·H 궤적 ≠ OFF → STOP" 을 "H 궤적 ≠ OFF, 또는 Ω 팔이 T1/T2 거짓 → STOP" 으로.
> - G-K1 동적(보충 C1 §6.4): Ω·C1 팔에 T1/T2 를 씀.
>   - ~~r1: E≢0 상태에서는 K_E ∪ N1(K_E) 를 C0E 로 두고 C0 와 같이 셈. 규칙 "C3 첫 차이 행이 C0 첫 차이 행보다 앞서면 STOP" 은 C0 ∪ C0E 기준.~~
>   - **[검토 r2] r1 규칙은 구성상 늘 거짓이었습니다.** E≢0 이면 K_E 의 차이는 정의상 첫 행(행 0)에 있습니다(T2 (iii)). C0 ∪ C0E 의 첫 차이 행은 늘 0 이고, `c3_before_c0` 는 "C3 첫 행 < C0 첫 행"(엄격한 작음, OU `k92_gates.py:465`)이라 어떤 C3 차이도 행 0 보다 앞설 수 없습니다. 그래서 E≢0 상태에서 이 멈춤은 한 번도 걸릴 수 없었습니다.
>   - **r2 규칙**: C0 는 보충 C1 의 정의 그대로(S_add 목록·고정 경로). E≢0 상태에서는 K_E ∪ N1(K_E) 키를 **C0E** 로 따로 적고 C0 에도 C3 에도 넣지 않습니다. C3′ = 그 밖 키. 멈춤 = `c3_before_c0` 를 C3′ 과 C0 로 그대로 셈(C0 차이가 없는데 C3′ 차이가 있으면 앞선 것으로 봄, RV-10 뜻 그대로). C0E 의 첫 차이 행과 "K_E ∪ N1 밖으로 처음 번진 행"(본 상태 행 134 [실행 `d98_row0.json`])은 보고합니다.
>   - 남는 약점(보고): 원래 규칙도 C0(S_add 회계)가 행 0 에 차이를 가지면 C3′ 가 앞설 수 없습니다. 이것은 보충 C1 규칙의 성질이고 이 보충이 만든 것이 아닙니다. 그래서 상태마다 C0·C0E·C3′ 의 첫 차이 행을 함께 적습니다.
> - G-K2 (d): E≡0 상태 = 지금 식(궤적 같음 + Ω 목적 − OFF 목적 = L_Δ, 상대 1e-9). E≢0 상태 = 보고만(Ω 목적 − OFF 목적, L_Δ, D66, 경로 몫 = (Ω − OFF) − L_Δ).
> - 덮개 보고: 탐침 plant 16상태 가운데 E≡0 상태 수. 0 이면 "T1 이 한 번도 안 셈" 을 보고·질문(멈춤 아님).
> - **[검토 r2] 순서**: E≡0 은 드물 것입니다(18 커넥터 가운데 하나에라도 차가 있으면 E≢0, §1.8). 그러면 G-K2 (d) 의 식 확인(궤적 같음 + 목적 차 = L_Δ)이 거의 돌지 않습니다. 그래서 P0-16(설정만, 약 47 분)에서 E≡0 상태 수를 먼저 세어 보고합니다. 탐침 plant 16상태 가운데 E≡0 이 0 이면 plant 잡 전에 멈추고 G6 (나) "채널만" 팔을 더할지 묻습니다(데이터 뒤; 1 이상이면 보고만 하고 이어 감).
>
> ### 3.5 F 보고에 경로 효과 (D-K9-98 "F 보고에 이 경로 효과를 따로 적음")
>
> - F-D98 (c1t 단계, 보고): 상태마다 Σ_k |E_k|, 차가 있던 C29 커넥터 수, K_E 목록, K_E ∩ S_add.
> - F-Ω 를 두 팔로(권장, G7): OFF plant 잡 D66(보충 C1 §9.2 그대로) + Ω plant 잡 D66(새 50잡). 둘 다 같은 66링크 VISSIM 체류와 나란히. 차이는 "경로 효과 + 회계 몫" 으로 적음.
> - 이유 [추론]: 29 커넥터는 더한 66링크 안이고, VISSIM 66링크 체류는 그 위 차를 셉니다. OFF 는 그 차의 일부를 세지 않거나(수 칸 없음) 다른 저장고로 셉니다(§1.8).
>
> ### 3.6 이미 본 상태에서 (데이터 뒤, 판정 아님)
>
> - v3c3-s31 T=1,500: 첫 행 차이 = 정확히 세 키, 값은 §1.8 의 커넥터 기록으로 센 몫과 같음 [실행·계산]. 첫 행 차이 ⊆ K_E 이고, 이웃 밖 첫 차이는 행 134 [실행].
> - 이것은 첫 행(첫 스텝 뒤)이고 D98-3 이 요구하는 S⁰(첫 스텝 전)이 아닙니다. S⁰ 는 새 단계가 셉니다(§5.4).

**읽는 법 (이 보충이 정함; 위 글자는 그대로 두고 아래로 읽음)**

1. **D98-5 의 "가드 RS 줄은 읽기만" 확인 방법**: P0-16 도구가 C1G 팔 설정 때 E23 호출 바로 앞·뒤의 `detector_mapping`(pickle protocol 5 바이트의 sha256)과 `state_json`(정규 JSON sha256)을 적고 둘이 같음을 봅니다. 그리고 같은 상태의 C1G 팔 S⁰ = Ω 팔 S⁰(비트 같음)를 봅니다. 둘 중 하나라도 거짓이면 D98-5 거짓.
2. **§3.3 표 "탐침 결정" 줄**: "가드 상태 S_G(§5.4, ≤ 8)" 는 "S_G(이 보충 §9.4, ≤ 14) + C1G⁰ 상태 1(R-obs v3c3-s31 T=900, 탐침 결정 5 와 겹침)" 으로, 그 줄 수 "≤ 13" 은 "≤ 19" 로 읽습니다(GG11). 더해 `/g_rr_c_b` 3상태(B 세 시드 T=900, G-RR (c))를 표에 더합니다 — 거기서 우리 어댑터가 B 상태를 설정하지 못하면 D98 칸은 G-RR (c) 와 같이 "못 냄"(보고, 멈춤 아님); 설정되었고 D98 이 거짓이면 STOP. c1t 전 D98 상태는 모두 ≤ 16 + 19 + 17 + 36 + 3 = **≤ 91** 입니다 [계산]. 그래서 같은 표 아래 "c1t 전 약 82상태 × 2팔 ≈ 47 분" 은 "≤ 91상태, 약 1–1.5 h(§17)" 로 읽습니다.
3. **D98 을 세는 팔**: OFF·Ω(모든 D98 상태), 그리고 결정 상태(탐침 결정 5·S_G·C1G⁰·R-b 39·`/g_rr_c_b` 3)에서는 C1·C1G·C1G⁰ 의 S⁰ 도 셉니다(D98-5).
4. **P0-16 의 순서**: P0-16 은 탐침 r2 의 첫 단계로 돕니다(§9.2). E≡0 상태 수는 plant 잡 전에 셉니다. 탐침 plant 16상태 가운데 E≡0 이 0 이면 plant 잡 전에 멈추고 G6 (나) "채널만" 팔을 더할지 묻습니다(S-C1-20).
5. **ε** = 1e-9 대 그대로. D98-3 의 S⁰ 는 `get_ledger(state).stocks` 의 `inside + outside`, 첫 스텝 전 값입니다(r2 §3.1 그대로).
6. 상자 §3.4 의 "G-K1 동적(보충 C1 §6.4): Ω·C1 팔에 T1/T2" 의 C1 팔은 이 보충의 C1-4 배포 팔 C1G 입니다(§10.1). "권장, G7" 은 사용자가 고른 G7 (가)입니다(§1.2).

---

## 4. 스레드 정정 (D-K9-99) — 보충 C1 §3 "발사" 줄(보충 C1:407)의 정정 메모

아래 글은 좁은 설계 r2 §4(`553227cd…` :450)·일반형 r1 §3.9(`cffbef23…` :658)와 글자 그대로 같습니다(조립 도구가 r1 :658 바이트를 넣음 [실행]; 원문 CRLF 의 줄 끝만 LF 로 읽음). 보충 C1 고정판 바이트는 바꾸지 않습니다.

> **정정 (D-K9-99, 2026-10-27)**: 보충 C1 §3 "발사" 줄의 "`OMP_NUM_THREADS=1`·`NUMBA_NUM_THREADS=1`(K9-2 재생 꼴)" 은 다음으로 읽습니다. 자식 프로세스 환경 = `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, `PYTHONHASHSEED=0`, `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUTF8=1`, `NUMBA_CACHE_DIR` = 그 단계 캐시 폴더, 그리고 **`NUMBA_NUM_THREADS` 는 환경에서 지웁니다**(값을 주지 않음). 그리고 부모 환경의 `RW_`·`K8_`·`K8G_`·`S31F_`·`GH1_`·`K92A_`(C1 도구는 `C1P0_` 도) 접두 변수를 뺍니다 [검토 r2: 덧붙임, 두 파일 :95-96·:229-230]. 이것이 K9-2 재생 도구 꼴(`SP/k92/bundle1/a25decl/tools/k92lib.py:94-102` `child_env`, sha `cbe1d94f…`, :99 `env.pop('NUMBA_NUM_THREADS', None)`)이고 V-A·K9-2 재생과 같은 조건입니다. C1 도구는 이미 이 꼴입니다(`C1D/tools/c1common.py:228-233` `child_env`, :233 `env.pop`, sha `99b98cc6…`, PINS_P0_r2·PINS_PROBE 에 고정). 그래서 이미 돈 P0(P0-1…P0-13)와 탐침(plant v3c3-s31 T=1,500 세 잡)은 유효합니다. codex 코드를 돌리는 단계의 env_hsw(`OPENBLAS_CORETYPE=Haswell`, AVX-512 끔, `NUMBA_CPU_NAME=haswell`; c1common.py:241-242)는 그대로입니다. 설계 초안 r2 §8.1 의 "스레드 1" 도 같은 뜻으로 읽습니다.

- 이 보충의 새 도구(P0-14–18, 탐침 r2, D98, 증거 빌더·재셈 도구)도 모두 같은 `child_env` 꼴을 씁니다. codex 코드를 돌리는 단계는 없습니다(가드의 codex 함수 두 개는 우리 C1P 안의 사본이라 env_hsw 대상 아님).

---

## 5. 일반형 저장 용량 가드 — 정의 (고정; 규칙·상수는 데이터 뒤)

규칙의 기계 판은 `C1D2/c1g_guard_rule.json`(`cebd6f05…`)입니다. 근거 숫자는 GG r1 §1–§2 의 [실행]·[읽음] 값이고, 이 보충에서는 다시 세지 않았습니다.

### 5.1 대상과 구간 (차로 단위)

- 구간 표 = 재고·자료의 구간 이름 그대로(`segments.json` 1,142 가운데 보고 전용 `D5:129:1` 을 뺀 **1,141**) + 받는 쪽 구간 `R:` **137**(받는 쪽 261개 가운데 위 표에 같은 [링크, 차로, 시작, 끝]이 없는 것) [읽음 GG r1 F-G1–F-G6, F-G3c].
- 종류와 범위:

| 종류 | 범위 | 원천? | 칸 판정에 씀? |
|---|---|---|---|
| `A:` 머리 차로 | 링크 시작(또는 같은 차로 위 native 머리) ~ 우리 현시 머리 | 예(짧으면 아님) | 예 |
| `L:` 진출 착지 | 진출 커넥터 착지 ~ 그 차로 다음 머리 또는 링크 끝 | 예(GG5; 짧으면 아님) | 예 |
| `F:` 공급 | 머리 없는 링크·커넥터 차로(재고 416구간·896차로) | 예(짧으면 아님) | 예 |
| `M:` 미터 머리 앞 | 미터 커넥터 차로 [0, 미터 머리] | 아님(미터 방아쇠 길의 칸으로만) | 예 |
| `MA:` 미터 접근 | 미터 커넥터가 갈라지는 링크 차로 [0, 갈림] | 예(미터 방아쇠, §5.7) | 예 |
| `R:` 받는 쪽 | 착지 ~ 그 차로 다음 머리 또는 링크 끝 | 아님 | 예 |

- **모든 intersection**: codex USG 가 빼는 현시 머리 6개(차로 5개; SC11 p1 두 차로, SC12 p3·p4, SC7 1220008601 차로 2 의 머리 둘)도 넣습니다. 위에 native 머리가 있는 차로는 [그 native 머리, 우리 머리] 구간, SC7 공유 정지선 차로는 두 현시(p1·p2)에 같은 점수 [읽음 GG r1 F-G2, §2.1].
- **모든 ramp**: 미터 8개(FW_E RM_C10484·10490·10639·10681, FW_W RM_C10480·10482·10644·10646), 진출 착지 9차로(L:10481:127:1·2, L:10483:124:1, L:10643:126:1·2, L:10682:121:1, L:10491:129:1, L:10638:70:1·2) [읽음 GG r1 F-G4·F-G5].
- **짧은 구간** = 용량 < 2.0대(156개: 공급 144, 머리 차로 10, 착지 2). 원천이 아니고(GG3), 칸 길에서는 판정 없이 지나갑니다. 받는 쪽으로 쓸 때는 §5.3.
- **받는 쪽이 없는 현시 머리 차로 3개**(SC1002 72 차로 2·3, SC107 1220000201 차로 1)는 점수 0 입니다(codex 와 같음). 이 셋은 가드가 보지 않는 차로입니다(보고서 머리에 적음) [읽음 GG r1 F-G3d].

### 5.2 넘음 규칙 U (GG0·GG1·GG9)

- 용량 C_s = 길이 ÷ `spacing_m`, `spacing_m` = `cfg.network.urban_avg_vehicle_length_m` = 6.0(증거 파일 `/spacing_m` 과 다르면 ValueError).
- 차 수 n_s = 기록 가운데 `link_no` = 링크, `lane_no` = 차로, 시작 ≤ `position_m` ≤ 끝(CX USG:51-56 셈, 허용오차 없음).
- 점유 fill_s = n_s ÷ C_s. **용량 넘음** ⇔ fill_s ≥ `capacity_threshold`(= 1.0; CX USG:79-80 꼴, 허용오차 없음). 사용자 말 "초과" 는 글자로 > 이지만 GG0 (가)로 ≥ 를 씁니다. 둘은 길이가 6 m 정수배인 구간에서만 갈립니다.
- **관측 번짐 S** (`gd_scan.py` 머리 정의 그대로, 그 스캔 전에 정한 정의):
  - S0: 속도 < 5 km/h 인 차가 시작 ≤ 위치 ≤ 시작 + 12 m 에 있음(구간이 12 m 보다 짧으면 구간 전체).
  - S: S0 이고, 구간 안 차를 위치 순으로 놓고 가장 위(상류) S0 차부터 아래로 이웃 차 빈 틈(앞차 위치 − 앞차 길이 − 뒷차 위치) ≤ 20 m 로 이어지는 줄의 마지막 차 위치 ≥ 끝 − max(20 m, 0.2 × 길이). 길이 ≤ 12 m 이면 S = S0.
  - 차 길이 = 같은 시각 차로 프레임(`/obs150/frames/current` 의 파일, 행의 6번째 칸)에서 차 번호로 맞춘 값. 상태 파일의 `/obs150/frames/current/sha256` 과 프레임 바이트 sha256 이 다르거나, 센 차의 길이가 프레임에 없으면 ValueError.
- **넘음 F** = 용량 넘음 ∨ S (`full_rule` = `count_or_spill`). 짧은 받는 쪽은 §5.3.

### 5.3 받는 쪽 (codex 정의, GG13)

- 받는 쪽 = 머리 위치 이후(머리 위치 − 1e-6 m 보다 뒤)에 떠나는 커넥터마다 착지 차로의 [착지, 그 차로 다음 머리 또는 링크 끝](CX USG:68-76). 머리 앞에서 갈라지는 커넥터는 받는 쪽이 아님.
- 받는 쪽 넘음: 보통 받는 쪽은 F(U), **짧은 받는 쪽(< 2대)은 용량 넘음만**(`short_receiver_rule` = `count`; 9.4 m 링크면 2대 이상).
- 머리 차로 h 의 받는 쪽이 있고 모두 넘음 → h 의 점수 −1. 일부만 넘음 → 영향 없음(CX USG:77-79). 받는 쪽 없음 → 0.

### 5.4 칸 그래프와 귀속 (GG4)

- **칸**: 빌더가 각 차로를 자름점(링크 시작·끝, 그 차로의 모든 머리 위치, 그 차로에 내려앉는 모든 커넥터 착지, 그 차로에서 떠나는 모든 커넥터 출발)에서 잘라 만든 조각.
- **칸 넘음** = 그 칸을 품는 구간(A·L·F·M·MA·R; D5 뺌) 가운데 가장 짧은 것의 F(같은 길이면 id 사전순 첫 것). 짧은 칸(< 2대)은 판정 없이 지나감. 품는 구간이 없는 짧지 않은 칸은 넘지 않은 것으로 봄.
- **칸 이음**: (1) 같은 차로 다음 칸(하류), (2) 칸 안(아래 끝 포함)에서 떠나는 커넥터의 차로 대응(출발 차로 first + i → 착지 차로 landing + i, CX USG:36-45 읽기)으로 착지 칸, (3) 같은 링크 안 옆 차로 칸 가운데 같은 [시작, 끝] 거리 구간을 가진 칸(양방향; 차로 바꿈).
- **멈추는 곳**: 우리 현시 머리 칸(그 머리가 서버) · 미터 머리 칸(그 미터가 서버) · native·미드블록 머리(서버 없음) · 정지선 없는 끝 · 차량 입력 · 고속도로 본선(서버 없음).
- **귀속**: 원천 구간 s 가 서버 X 에 귀속 ⇔ F_s 이고, 빌더가 미리 적은 (s, X) 부분 그래프(s 의 아래 끝 칸에서 X 의 머리 칸들 가운데 하나까지 가는 어떤 길 위에 있는 칸·이음 전부) 안에서, **넘은 칸 또는 짧은 칸만 지나** X 의 머리 칸 하나에라도 닿을 수 있음. 런타임은 그 부분 그래프 안에서만 닿음 검사를 합니다(유한, 망 전체 탐색 없음).
  - [정정, 설계 r1 §2.3 대비] r1 은 "귀속 길(칸 id 열)을 미리 적고 런타임은 그 길만 본다" 였습니다. 차로 바꿈 이음이 있으면 길의 수가 구간 길이마다 곱으로 늘 수 있어 [추론], 같은 뜻(넘은·짧은 칸만 지나는 길이 하나라도 있음)을 부분 그래프 닿음 검사로 고정합니다.
- **같은 링크 머리 제외**: 머리가 있는 링크 위의 공급 구간(F-G3 의 34차로, 예 F:37·46·52·66)은 같은 링크 머리 현시로 귀속하지 않습니다(그 현시는 머리 차로 구간이 셈). 갈림 커넥터 쪽 서버로만 귀속.
- **A 구간**: 자기 현시(SC7 공유 정지선은 두 현시)에 직접 점수(§5.5). **L 구간**: F 와 같은 칸 규칙으로 귀속(같은 차로 머리면 같은 차로 칸들, 129 처럼 머리 없는 링크면 사슬). **MA 구간**: 미터로만 귀속(§5.7). **M·R**: 원천 아님.
- 예(규칙 확인용, 값 아님) [읽음 GG r1 §2.3]: 129 차로 1 칸 = [0, 239.4] · [239.4, 300.0] · [300.0, 301.9]. F:10491·L:10491:129:1 → 칸 [239.4, 300.0] → (a) 300.0 에서 떠나는 10490 → M:RM_C10490 → 미터 RM_C10490, (b) 칸 [300.0, 301.9](짧음) → 10777(짧음) → 127 차로 1 → SC1001 p3. 10643 → 126 → 10641/10700 → 71 차로 1–3(SC1004 p3), 그리고 71 안 차로 바꿈으로 71 차로 4·5(p4).

### 5.5 점수와 현시 무게 (GG7)

- 머리 차로 h(원천일 때): 받는 쪽 모두 넘음 → −1. 그렇지 않고 F_h 이고 받는 쪽 있음 → max(1, n_h ÷ C_h). 그 밖 → 0.
- 귀속된 L·F 구간 s → 서버 X: max(1, n_s ÷ C_s). 단 위 닿음 검사로 닿는 X 의 머리 차로가 모두 "받는 쪽 모두 넘음" 이면 0.
- **겹침 최댓값**: 한 서버에 같은 차로 길이를 0.05 m 넘게 겹쳐 가진 구간이 둘 이상 들어오면, 겹침으로 이어진 묶음마다 가장 큰 점수 하나만 더합니다(예: SC1001 p3 에 A:127:1 과 L:10481:127:1 이 함께 넘으면 큰 값 하나). 묶음은 빌더가 서버마다 미리 적습니다.
- 현시 무게 w_{SC,p} = 그 현시 키에 들어온 점수의 합(CX USG:86-87).
- **같은 무게 0**: 신호마다 살아 있는 현시(`cfg.network.signal_live_phases(owner)`) 무게가 모두 같으면(차 ≤ 1e-12, 모두 0 포함) 그 신호 무게를 모두 0 으로 둡니다. 영수증 이름 `equal_weights_zeroed`. (동시현시 SC7 은 축 꼴 때문에 같은 무게에서도 p1 행이 생기므로 관측 단계에서 막음 [읽음 GG r1 §2.6].)
- 17개 신호 키는 늘 둡니다(무게가 비어도; codex `constrain` 이 신호 목록을 그대로 돔). FW_E 덧무게는 없습니다.

### 5.6 신호 행 (codex 꼴, G2)

- 블록마다 `Coordinates` 를 만들 때 신호마다 행 하나: w̃ = (현시 무게 → 녹색 축 벡터) ÷ 최대 |무게|, M_k = 기존 제약 아래 LP 최대(w̃·z), required r_k = min(2.0, 0.5 × max(0, M_k)), r_k < 0.01 이면 행 없음. CX USG:102-145 본문 그대로(읽는 속성 `urban_storage_guard` → `c1_storage_capacity_guard`, 영수증 속성 `urban_storage_receipt` → `c1_storage_capacity_receipt`, 함수 이름만 다름).
- 강제되는 몫은 "무게를 곱한 녹색 2 s" 입니다. 실제 녹색 초는 2 ÷ max|w̃_j| 이상이고, 녹색 이동 한도 6 s/결정(OU `area_follower_objective.py:1294`) 때문에 블록 0 은 3 s 까지입니다 [읽음 GG r1 §2.6].
- 실현 가능성: 직전 명령이 물리 한계 안이면 3블록 계가 비지 않습니다(GG r1 §2.6-3 논거, PT SEQ:101-154·SD:342-400 와 대조). 밖이면 codex seed 투영에 맡기고 실패하면 ValueError(→ 결정 실패, 탐침 멈춤 8·S-C1-19).
- 우선 규칙은 따로 없습니다(무게가 우선).

### 5.7 미터 (GG6 (라), D-K9-114b)

- **방아쇠**: 미터 m 에 MA 구간, 또는 그 위 F·L 구간이 §5.4 칸 규칙으로 귀속될 때 참. 그 길은 미터 머리 앞 커넥터(M:)의 칸을 지나므로 머리 앞이 넘고 접근 링크 칸까지 넘어야 켜집니다. **머리 앞 커넥터만 넘은 것은 방아쇠가 아닙니다**(FW_E 미터가 차를 잡아 두는 저장을 풀지 않게).
- **하한**: M4(저장 보호 0.9)는 그대로. 가드 방아쇠가 참이고 M4 가 거짓인 미터는 같은 식 max(base, min(`cycle_sec`, 직전 + `max_green_change_sec`)) = max(2, min(10, 직전 + 2))(CX PRB:901 꼴) → RV-2 표 내림(직전 7 → 9 → 8) → G-A7 을 `(triggered or guard_triggered)` 로.
- 기록: `meter_operating_bounds/ramps/<미터>/guard_triggered`(불), `guard_sources`(귀속된 구간 id 정렬 목록; 거짓이면 []). 가드 키가 없으면 두 칸을 쓰지 않음.
- FW_W 미터 넷도 같은 규칙입니다(감시). 직전이 g10 이면 하한 10 → 그 결정은 조이지 못합니다(M1 조임 후보가 빠짐; 후보 수 식은 보충 C1 §2.3 의 최종 하한으로 셈).

### 5.8 seed·가능 검사·최종 검사

- 블록 영수증 가운데 'constrained' 가 하나라도 있으면(= 가드 행 있음) seed = codex `operating_seed`(CX USG:148-166 본문 그대로, QP 투영 두 번, 두 번째 1.05 배). 없으면 보충 C1 의 지금 가지(미터 축만 자름) 그대로(같은 객체).
- 가능 검사: `(meter_operating_bounds is not None or guard_rows)` 이고 `coord.valid` 거짓이면 불가능. 최종 `coord.validate`(PT SD:1148)는 그대로.

### 5.9 관측 (제어기가 결정 때 받는 것만)

- `/vehicle_records/records[]`(`link_no`·`lane_no`·`position_m`·`speed_kph`), `complete` 가 참이어야 함(PS:16 `complete_records`). 같은 시각 차로 프레임(§5.2). 증거 파일 하나. FZP·런 끝 자료·다른 팔 자료는 쓰지 않습니다. 거짓·없음·sha 다름은 ValueError(키 켬 팔만).
- 런타임은 `.inpx` 를 읽지 않습니다(GG8).

### 5.10 키와 값 — `c1_port.storage_capacity_guard` (repr 고정)

배포 팔 C1G 의 `c1_port` = 보충 C1 §2.1 의 7키 그대로 + 아래 한 키를 맨 뒤에(8키). 하위 키 순서도 아래 그대로입니다.

```json
"storage_capacity_guard": {
  "segments_name": "c1g_storage_segments_v3c3.json",
  "segments_sha256": "<S17>",
  "unit": "lane",
  "full_rule": "count_or_spill",
  "capacity_threshold": 1.0,
  "min_source_capacity_veh": 2.0,
  "feeder_attribution": "cell_chain_max",
  "landing_sources": true,
  "short_receiver_rule": "count",
  "reserve_green_sec": 2.0,
  "meter_rule": "approach_chain_or_m4"
}
```

- Python repr: `{'segments_name': 'c1g_storage_segments_v3c3.json', 'segments_sha256': S17, 'unit': 'lane', 'full_rule': 'count_or_spill', 'capacity_threshold': 1.0, 'min_source_capacity_veh': 2.0, 'feeder_attribution': 'cell_chain_max', 'landing_sources': True, 'short_receiver_rule': 'count', 'reserve_green_sec': 2.0, 'meter_rule': 'approach_chain_or_m4'}`.
- **S17 의 정의**: P0-17 (a) 가 고정 빌더(§8)로 쓴 `c1g_storage_segments_v3c3.json` 바이트의 sha256(64자 소문자). 결정적이어야 합니다(두 번 따로 만든 바이트가 같음). P0-17 이 그 값을 LOG 와 고정 B `C1D/PINS_P0_C1_2_B.sha256` 에 먼저 적고(뒤에 만드는 `C1D/C1_VALUES_C1_2.json` `/p0_17/segments_sha256` 이 같은 값을 담음), 같은 단계가 `C1D2/p0/c1_port_section_c1g.json`(8키, PN `data()` 직렬화)을 배타 생성합니다. 이것은 K9-2 보충 24 의 "커밋 증거 = P0 증거 sha" 꼴과 같습니다 [읽음 보충 24:272]. S17 은 P0-14·15·16·18 과 탐침 r2 의 어떤 계산보다 먼저 적히고, 그 뒤 바뀌지 않습니다(바뀌면 S-C1-23).
- 값 검사(C1P `check_value`, 어기면 ValueError): 키 집합이 정확히 위 11개; `segments_name` 은 보충 C1 §2.0-2 이름 규칙; `segments_sha256` 64자 소문자 16진; `unit` = `"lane"` 만, `full_rule` = `"count_or_spill"` 만, `feeder_attribution` = `"cell_chain_max"` 만, `meter_rule` = `"approach_chain_or_m4"` 만, `landing_sources` = `True` 만, `short_receiver_rule` = `"count"` 만(다른 값을 조용히 켜지 않게); `capacity_threshold` 는 int/float(bool 아님)·유한·0 < x ≤ 1; `min_source_capacity_veh` 는 int/float(bool 아님)·유한·≥ 0; `reserve_green_sec` 는 int/float(bool 아님)·유한·0 < x ≤ 2(CX USG:21 범위).
- 번짐 상수(12 m, 5 km/h, 20 m, max(20 m, 0.2 × 길이), 12 m 짧은 길이)는 키가 아니라 C1P 상수와 증거 `/spill_rule` 에 둡니다. 둘이 다르면 ValueError.
- 묶기(C1P `validate`): `storage_capacity_guard` 는 `storage_release_guard` 가 함께 있어야 함(미터 하한 길 PT SD:745-750 을 지나므로). 아니면 ValueError(`'c1_port.storage_capacity_guard requires storage_release_guard (amendment C1-2)'`).
- 정책 토큰: 가드 값은 `cfg.network.sdmpc_options` 에 들어가지 않습니다 → C1G 토큰 = C1 토큰 T_C1, {가드 키} 를 다른 키 없이 켤 수는 없음(묶기). P0-14 가 확인합니다.
- **보충 C1 §2.1 (a) "키 ⊆ 위 7개" 는 "키 ⊆ 위 8개" 로**, 팔 목록에 C1G·C1G⁰ 를 더합니다(§7).

**증거 파일 `c1g_storage_segments_v3c3.json`** (C1P `C1_DIRS['c1']` 폴더 = `diagnostics/sdmpc_n31_20260924/c1/evidence`; 이름 + sha 로만 찾음)

- schema `c1g-storage-segments/v1`. 머리: `network_sha256` = `3de889f0257d998bed50611f798ea388bcf69396dbc40e5726b1e88ebdd31c2e`, `plan_sha256` = `8e28f983e12d67d5244b4865d43482ef324729e12e4af87962ee60513704a012`, `spacing_m` = 6.0, `/spill_rule`(§5.2 상수), `/guard_rule_sha256` = `cebd6f05f7ef8c4aee01eae0ca63bc02f0dacabcbf47aa0c9fb55196e43f6257`, `null_test` = false.
- `segments[]`: `id`(재고·자료 이름 그대로, 새 받는 쪽은 `R:<링크>:<차로>:<착지 m 소수 1자리>`), `kind`, `link`, `lane`, `start_m`, `end_m`, `capacity_veh`, `short`, `source`(불), `servers`(A 는 현시 키 목록, M·MA 는 미터 이름), `receivers`(A 만, 받는 쪽 구간 id 목록), `part`(codex 분할 칸, 보고용).
- `cells[]`: `id`, `link`, `lane`, `start_m`, `end_m`, `short`, `judge`(품는 가장 짧은 구간 id 또는 null), `next`(이음 칸 id 목록, 종류 표시 `lane`·`connector`·`lane_change`), `stop`(그 칸 끝이 멈추는 곳 종류와 서버).
- `attribution[]`: `segment`, `server`, `start_cell`, `head_cell`, `head_lane_segment`, `cells`(부분 그래프 칸 id), `edges`(부분 그래프 이음 쌍).
- `overlap_groups`: 서버마다 겹침 묶음(구간 id 목록의 목록).
- `meters`: 미터마다 머리 칸, M·MA 구간 id.
- 경로 문자열 없음: `/schema` 말고 어떤 문자열 값에도 `/`·`\` 가 없고 `.json`·`.inpx`·`.py`·`.csv`·`.npz`·`.fzp` 로 끝나는 값이 없음(P0-17 (h)).
- 직렬화: PN `data()`(`json.dumps(…, ensure_ascii=False, indent=2, allow_nan=False) + '\n'`), 목록 순서는 id 사전순, 실수는 Python `repr` 그대로(반올림 없음).
- **빈 증거** `c1g_storage_segments_null_v3c3.json`(C1G⁰ 용): 위 파일과 같되 `null_test` = true, 모든 `source` = false, `attribution` = [], `meters/*` 의 MA 목록 = [] 입니다. 같은 P0-17 단계가 함께 씁니다(sha = S17⁰). 커밋하지 않고, 관문 스크래치 트리에만 고정 fixture 로 넣습니다(§10).

### 5.11 메타 (가드 키가 있을 때만)

- RS 메타 `/metadata/c1_port/storage_capacity_guard` = {`evidence_sha256`, `observed_sec`, `frame_sha256`, `full_segments`(정렬 id), `full_by_kind`, `signals`(신호 → 현시 키 → 무게), `meters`(미터 → {`triggered`, `sources`}), `minus_one_lanes`, `equal_weights_zeroed`, `overlap_dropped`, `short_segment_count`}. 그리고 `/metadata/c1_port/keys` 는 8개 정렬 목록. 경로 문자열 없음(프레임은 sha 로만).
- SD 결정 메타 `/metadata/joint_leader_selection/c1_storage_capacity_guard` = {`blocks`: 블록별 영수증 목록(codex 꼴: signal, attainable_pressure_sec, required_pressure_sec, phase_weights, status), `lp_inputs`: 블록별·영수증 신호별 {`axes`(녹색 축 첨자), `green_vectors`, `axis_scale`, `G`·`glo`·`ghi`(그 축을 쓰는 현시 행, 가드 행 앞의 `len(phase_rows)` 행만), `lower`·`upper`}, `seed_projected`(불), `reference_in_phase_limits`(신호 → 불, 블록 0)}. 이 칸은 G-K2 (h) 독립 재계산의 입력입니다(codex 함수 본문은 바꾸지 않고 SD 메타 자리에서 적음).
- `meter_operating_bounds/ramps/*/{guard_triggered, guard_sources}`(§5.7).
- 이 경로들은 A_C1-M·A_C1G-M 의 선언 차이입니다(§10.2).

### 5.12 키 끔 비트 같음

- 새 줄은 모두 "`c1_port.storage_capacity_guard` 가 있을 때만" 도는 가지에 둡니다. 키가 없으면: E23 부르지 않음 → `cfg.network.c1_storage_capacity_guard` 속성 없음 → E24 부르지 않음 → E25 지금 가지(같은 객체) → E26 식 값 같음 → E28 새 줄 지나지 않음(G-A7 값 같음) → 메타 칸 없음. 보충 C1 §2.0-1 의 키 끔 = c20aff1d 길(G-K0)과 C1 팔(가드 키만 없음) 같음(G-K4 C1 팔, G12)을 둘 다 봅니다.
- 키가 있고 무게가 모두 0·미터 방아쇠 0 이면 C1G 결정 = C1 결정(가드 메타 말고). 탐침 멈춤 5·G-K2 (g) 가 봅니다(K0 상태와 C1G⁰).

### 5.13 알려진 한계 (보충 C1 §2.12 에 16–21 로 더함; 보고서 머리에 옮김)

16. Ω701 지지 문서의 29 커넥터 `link_to_storage` 가 첫 재고 투영을 바꿉니다. Ω 팔 궤적은 첫 행부터 OFF 와 다를 수 있고, 그 차이는 D98 로 설명되어야 합니다(이미 본 상태 v3c3-s31 T=1,500: 첫 행 차이 3키 +1.0 / +0.5 / −0.5대, 이웃 밖 첫 차이 행 134) [읽음 GD r2 §1.8].
17. 가드는 **반응형**입니다(결정 시각 한 장면). B 의 첫 SG2 단축(900 s 칸)은 막지 못합니다(U 첫 켜짐은 그보다 900–1,050 s 뒤, 데이터 뒤) [읽음 GG r1 §0-8].
18. 가드는 **FW_E 를 움직이는 지렛대가 아닙니다.** 미터 규칙 (라)는 FW_E 미터 줄이 접근 링크까지 넘칠 때 조임을 풉니다(B 꼴 RM_C10639 14 / 0 / 26, RM_C10681 0 / 2 / 1 미터·결정, 데이터 뒤) [읽음 GG r1 §2.4].
19. V-A 같은 운영에서 거의 매 결정 켜집니다(머리 차로 모사 신호 행이 있는 결정 54 / 54 / 54, GG13 (나)로 −1 결정 16 / 23 / 11; 받는 쪽 자료가 있는 것만 센 하한, 데이터 뒤). 목적 쪽 효과는 모릅니다 [읽음 GG r1 §1.5b].
20. 받는 쪽 없는 현시 머리 차로 3개는 보지 않습니다(§5.1). 번짐 S 는 신호 상태를 쓰지 않는 기하 정의라 녹색 방류 중 느린 줄도 켭니다 [읽음 GG r1 §2.9].
21. plant 는 바꾸지 않습니다(129 차로 1 국소 저장·26 차로 1·입구 1099 밀린 줄은 모형에 없음, G5).

---

## 6. 편집 자리 — 보충 C1 §2.13 의 닫힌 목록 E 에 E23–E30 을 더함

- 자리는 c20aff1d 줄(OU, 앵커 글로 찾음)과 첫 탐침 트리 PT 줄(패치 `5cdc6eb1…` 적용 뒤)을 함께 적습니다 [실행 `git show c20aff1d:`·PT 파일 읽기 19:52 KST]. 꼴의 뜻은 보충 C1 §2.13 그대로(가드 삽입·공유 줄 편집·새 정의).

| # | 파일:앵커 OU c20aff1d | PT(탐침 패치 r1 뒤) | 넣는 것 | 꼴 | 키 끔 논거 |
|---|---|---|---|---|---|
| E23 | RS:492 `metadata.update(physical_ramp_metadata)` 뒤, :493 `install_wout_exit_law` 앞 | RS:498 뒤, :499 앞 | `if 'storage_capacity_guard' in getattr(cfg.network, 'c1_port', {}): c1_meta['storage_capacity_guard'] = c1_port.observe_storage_capacity(cfg, tuning, state_json)` | 가드 | 속성·키 없으면 부르지 않음, `c1_meta` 칸 없음 |
| E24 | SD:363 `self.owners = …` 뒤(`Coordinates.__init__` 끝) | SD:400 뒤 | `if getattr(net, 'c1_storage_capacity_guard', None): from evaluation.controllers import c1_port; c1_port.constrain_storage_capacity(self)` | 가드 | 속성 없으면 부르지 않음(영수증 속성도 없음) |
| E25 | 커밋 C1-2 의 seed 자리(OU SD:586 `coord = coordinate_type(…)` 뒤, 보충 C1 E10) | SD:766-773 | 블록 영수증(`getattr(coord, 'blocks', [coord])` 마다 `getattr(b, 'c1_storage_capacity_receipt', [])`)에 'constrained' 가 있으면 `operating_seed = c1_port.storage_capacity_seed(coord, reference, policy)`, 없으면 지금 가지 | 공유 | 가드 행 없으면 지금 가지 그대로(같은 객체) |
| E26 | SD:618-620 `def feasible` 의 `return (` 앞 | SD:805-808 | 조건 `meter_operating_bounds is not None` → `(meter_operating_bounds is not None or guard_rows)` | 공유 | 키 끔 `guard_rows` = False → 식 값 같음 |
| E27 | SD:965 `metadata = {` | SD:1176-1177 | `**({'c1_storage_capacity_guard': …} if guard_present else {})` (§5.11) | 가드 | 키 없으면 칸 없음 |
| E28 | (C1P 는 c20aff1d 에 없음, 보충 C1 E22) | C1P:263-286 `operating_bounds` 안, `configure_operating_bounds` 뒤·표 내림 앞 | 가드 미터 방아쇠 OR → 같은 하한 식, `guard_triggered`·`guard_sources`; G-A7 조건(PT C1P:283-285)을 `(evidence['triggered'] or evidence.get('guard_triggered', False))` 로 | 가드 + 공유 | 속성 없으면 새 줄 안 지남, `evidence.get` 기본 False 라 G-A7 값 같음 |
| E29 | (C1P) | C1P:286 뒤(파일 끝) | 새 함수 `observe_storage_capacity(cfg, tuning, state_json)`(감싸개), `storage_capacity_core(records, frame_lengths, evidence, live_phases, meter_names)`(순수 함수: 셈·번짐·칸 넘음·귀속·겹침·무게·미터 방아쇠), `constrain_storage_capacity(coord)`(CX USG:102-145 본문), `storage_capacity_seed(coord, reference, policy)`(CX USG:148-166 본문), `load_segments(section)`(이름 + sha + schema + 간격 + 번짐 상수 검사) | 새 정의 | 키 끔에서 부르지 않음 |
| E30 | (C1P) | C1P:18-19 `KEYS`, :41-73 `check_value`, :76-92 `validate` | `KEYS` 에 `'storage_capacity_guard'`, `check_value` 가지(§5.10), `validate` 묶기 | 가드 | 키 없으면 새 가지 안 지남; `KEYS` 길이만 바뀌고 모르는 키 검사 결과는 같음 |

- `observe_storage_capacity` 는 codex `configure` 처럼 먼저 `cfg.network.c1_storage_capacity_guard = None` 을 두고 채웁니다(연쇄 재생에서 앞 결정 값이 남지 않게, CX USG:15 꼴). 채우는 값 = {`schema`: `c1g-observed-lane-storage/v1`, `policy`: 키 사본(`reserve_green_sec` 를 codex `constrain` 이 읽음), `signals`, `meters`, …}.
- E23 은 `state_json`·`detector_mapping` 을 읽기만 합니다(D98-5 확인, §3 읽는 법 1).
- 3블록: `SequenceCoordinates` 가 블록마다 `Coordinates` 를 만들 때(OU SEQ:116-117) E24 가 블록마다 돌고, 행은 OU SEQ:128-133 으로 쌓입니다. SEQ 는 바꾸지 않습니다.
- G-K1 정적 (h) 는 E1–E30 을 씁니다. 이 목록 밖 덩어리가 하나라도 있으면 (h) 거짓 → STOP(S-C1-5).

---

## 7. 팔·선언 파일·가드 허용 목록

- **팔**(보충 C1 §2.1 팔 줄에 더함): **C1G** = C1 7키 + `storage_capacity_guard`(S17) — **새 배포 팔**. **C1G⁰** = C1 7키 + `storage_capacity_guard` 의 `segments_name` = `c1g_storage_segments_null_v3c3.json`, `segments_sha256` = S17⁰(나머지 값 같음) — 탐침·관문의 무작용 시험 전용(배포·폐루프 아님). C1 은 보고 팔로 남김(가드 몫 = C1G − C1). OFF·Ω·M·H·M_cap1·M_noheld·C1⁻ 그대로.
- **"배포 팔" 의 뜻이 바뀝니다**: 보충 C1 에서 배포·묶음 팔(§2.0-5 의 `config_n31_v2_c1.json`, §8 R, §9.1 J-1·J-2 의 키 켬 팔, §11 폐루프)은 이 보충부터 **C1G(8키)** 입니다. 탐침의 보고 팔 "C1" 은 7키 그대로입니다. C1G⁻ = C1G − {meter_neighbor_audit}(규칙 X⁻ 가 닿을 때만; 보충 C1 §2.9 꼴, 지금 계획에서 닿는 계산 없음).
- **정책 토큰 표**(보충 C1 §2.9 에 한 줄): C1G·C1G⁰ = T_C1(`522eec6f…`), C1G⁻ = `428e650d…`.
- **선언 파일**(이름 + sha):
  - 지금(Declare): `C1D2/c1g_guard_rule.json`(`cebd6f05…`), 고정 목록 `C1D2/PINS_C1_2_DECLARE.sha256`.
  - P0-17 이 씀(배타 생성): `C1D2/p0/c1g_storage_segments_v3c3.json`(S17), `C1D2/p0/c1g_storage_segments_null_v3c3.json`(S17⁰), `C1D2/p0/c1_port_section_c1g.json`(8키), `C1D2/p0/c1_port_section_c1g_null.json`.
  - P0-15 가 씀: `C1D2/p0/c1g_states.json`(schema `c1g-states/v1`; `/s_g` 목록 {run, kind, T, category}, `/categories`(범주 → T 또는 none), `/skipped_judging_states`(이름만), `/c1g0_state` = {run `sdmpc31_v3c3_nc_s31`, kind `robs`, T 900}, `/seed_rule` = 보충 C1 `c1_states.json` 과 같은 글).
  - `C1D/declared/c1_states.json` 은 바꾸지 않습니다.
- **C1-0 가드 `c1_guard`**(보충 C1 §6.2) 고침: (1) 단계 토큰의 `--declaration-sha` 는 **보충 C1-2 고정판 sha256(64자)** 입니다(보충 C1 고정판 sha 는 C1-2 머리에 고정되어 사슬로 묶임; 그 밖의 sha·옛 토큰은 SystemExit). (2) 닫힘 때 허용 목록 A 에 `c1g_states.json` 의 `/s_g`·`/c1g0_state` 상태를 더합니다. 자체 시험 (5)에 "S_G 상태 C1G 키 허용" 하나를 더합니다.
- **U 시험 목록** `C1D/C1_U_TESTS.json`(C1-0 전에 고정): 새 `diagnostics/sdmpc_n31_20260924/tests/test_c1_guard.py` 를 넣습니다(§11).

---

## 8. P0 에 더함 (P0-14 … P0-18; 보충 C1 §4 다음 번호)

### 8.1 도구·순서·고정

- **도구**(새 파일; 옛 `c1_p0.py`·`c1_probe.py` 바이트는 그대로 둠): `C1D/tools/c12/c1g_build.py`(증거 빌더, 입력 = v3c3 `.inpx`(sha256 `3de889f0…` 인 파일, 예: V-A v3c3-s31 런 `network/` 의 사본 — 쓰는 파일 이름은 고정 A 에)·현시 계획·OUC·`inventory.json`·`segments.json`·`gr_check.json`; 런 결과 자료 0), `C1D/tools/c12/c1g_recount.py`(독립 재셈: C1P 를 import 하지 않고 상태 파일·프레임·증거만 읽어 §5.2–§5.7 을 다시 셈), `C1D/tools/c12/c1_p0_c12.py`(하위 명령 p0_14 … p0_18), `C1D/tools/c12/c1_probe_build_r2.py`(탐침 패치 r2 만들기), 자체 시험 `C1D/tools/c12/selftest_c12.py`(합성 자료만).
- **순서**: 고정점 → 개발(합성 시험 + 개발 스모크 1회) → **고정 A** `C1D/PINS_P0_C1_2.sha256`(위 도구·자체 시험 출력·입력 sha 목록) → **P0-17** → 패치 r2 만들기 → **고정 B** `C1D/PINS_P0_C1_2_B.sha256`(패치 r2·manifest·팔 파일 9개·`c1_port_section_c1g*.json`·증거 둘) → **P0-18** → **P0-14** → **P0-15** → `C1D/C1_VALUES_C1_2.json` 배타 생성·LOG 고정 → 탐침 r2 고정(§9) → **P0-16**(탐침 r2 첫 단계).
- **개발 스모크**: 합성 자체 시험과, R-obs v3c3-s31 **T=750**(탐침·S_G·판정 상태 밖) 한 상태의 C1G 팔 설정만 1회. 예외 유무만 LOG 에 적고 무게·구간 값은 보지 않습니다. 결정 재생은 고정 전에 하지 않습니다.
- 무거운 일(P0-18·P0-14·P0-15·P0-16)은 LOCK 아래 하나씩. P0-17 은 가벼움(망 파일만, 5분 넘으면 LOCK). 발사·환경은 §4.
- 출력 `TC1/out/p0_c12/<단계>/`. 보고 `C1D/P0_C1_2.md`(+ RC1 사본).

### 8.2 P0 표

| # | 내용 | 멈춤 |
|---|---|---|
| **P0-17** 증거 | (a) 빌더를 두 번 따로 돌린 바이트가 같음 → 그 바이트 = 선언 바이트, sha = S17; 빈 증거 S17⁰ 도 같은 꼴. `C1D2/p0/` 네 파일 배타 생성, S17·S17⁰ 를 LOG 에 적음(고정 B 와 뒤의 `C1_VALUES_C1_2` `/p0_17` 이 같은 값을 담음). (b) 1,141 구간의 id 집합 = `segments.json`(`ac374b01…`)에서 D5 뺀 집합, 링크·차로 같음, 시작·끝 \|차\| ≤ 1e-6 m, 용량 \|차\| ≤ 1e-6 대. (c) codex 210차로(`segments.json` `codex` 참)의 용량과 받는 쪽 [커넥터, 링크, 차로, 착지, 끝] = B v3c3-s31 T=900 결정 JSON(`action_000900.json`) `/metadata/joint_leader_selection/urban_storage_guard/observation/lanes[*]`(용량 `capacity_veh`, 받는 쪽 `receivers[*]` 의 `connector`·`link`·`lane`·`position`, 끝 = `position` + `capacity_veh` × 6 m; \|차\| ≤ 1e-6). (d) F·L 구간의 귀속 서버 집합 ⊆ `inventory.json` 의 링크 단위 서버 집합(`/feeders[*]/dist_from_end_to_server_m` 키, `/offramps/*/topology_servers`; 이름 꼴 `SC<n>:p<k>(SG<g>)` → `SC<n>_p<k>`, 미터 이름 그대로 — 바꾸는 규칙은 빌더 머리에 적고 고정 A 에 들어감). (e) 받는 쪽 261개: 새 `R:` 137개의 [착지, 끝] = `inventory.json` `/approach_lanes[*]/receivers[*]` 의 [`landing_pos_m`, `segment_end_m`](\|차\| ≤ 1e-6 m), 기존 구간을 쓰는 124개는 그 구간과 [착지, 끝] 의 차(m)를 적음(보고). (f) 칸: 모든 칸이 차로 길이를 빈틈·겹침 없이 덮음(\|차\| ≤ 1e-6 m), 모든 원천·받는 쪽 구간이 칸의 합집합, 10643 → A:71 차로 4·5 길이 차로 바꿈 이음으로 있음, 129 차로 1 칸 [239.4, 300.0] 이 10490 과 10777 두 갈래로 이어짐. (g) 서버별 겹침 묶음의 쌍 = `gr_check.json`(`be9385c6…`) `/overlaps` 61쌍에서 D5 3쌍을 뺀 58쌍과 같음. (h) 수 = RG-19, 경로 문자열 없음(§5.10), `/spill_rule` = `c1g_guard_rule.json` `/spill` 상수, `/guard_rule_sha256` = `cebd6f05…` | 하나라도 거짓 → STOP(S-C1-21) |
| **P0-18** 런타임 셈 | PT2 의 `c1_port.storage_capacity_core` 를 V-A·B 결정 상태 330개(`occ.json` `/state_sha16` 의 (런, T); 상태 파일 sha 앞 16자가 같아야 함)에 돌림. (a) 1,133 구간의 차 수 = `occ.json` `/raw_counts`(정수 같음). 다른 칸은 그 차의 위치가 구간 경계 ± 1e-9 m 안이면(occ 도구의 경계 허용과 codex 셈의 차) 그 차 목록을 적고 설명된 것으로 봄; 그 밖 차이 → STOP. (b) 착지 L 9·받는 쪽 R 137 구간의 차 수 = `c1g_recount.py` 의 같은 상태 셈(정수 같음). (c) S·F·칸 넘음·귀속·무게·미터 방아쇠 = `c1g_recount.py` 값(정수·불 같음, 무게 상대 1e-12). (d) 같은 T 의 FZP 스캔 npz(`TC1/guard_general/data/<런>.npz`)와 S 일치 몫(보고만) | (a)(b)(c) 거짓 → STOP(S-C1-21). (d) 는 보고 |
| **P0-14** 설정 | (a) 탐침 결정 5상태 × {C1, C1G} 설정만(보충 C1 P0-3 훅): `cfg.network` 깊은 비교 차 경로 집합(K7 deep_diff 꼴, 리스트 첨자 `[*]`) = {`c1_port/storage_capacity_guard`, `c1_storage_capacity_guard`} 정확히; 정책 토큰 둘 다 T_C1; `signal_live_phases` 17신호·미터 이름 8개가 5상태에서 같음(P0-15 입력으로 적음); 상태별 넘은 구간 수(종류별)·신호별 무게·미터 방아쇠를 `C1_VALUES_C1_2` `/p0_14` 에. (b) PT2 재확인: 보충 C1 P0-3(5상태 × 5팔 = 25회)·P0-6(12팔) 을 PT2 에서 다시 → `C1_VALUES.json` `/p0_3`·`/p0_3_S_add`·`/p0_3_input_changes`·`/p0_6` 와 같음. (c) 보충 C1 P0-13 비교기 자기 시험에 새 뿌리(`TC1/trees/probe_<sha8>`, `TC1/out/probe_r2/t<6자리>…`, `TC1/out/p0_c12/…`) 합성 경로를 더해 모두 `<root>`·`<bundle>` 로 바뀜 | 거짓 → STOP(S-C1-22) |
| **P0-15** S_G | R-obs v3c3-s31·s43, T ∈ {1,050, 1,200, …, 8,850}(런마다 53상태)에서 `storage_capacity_core`(입력: 상태 기록·프레임·증거 S17, P0-14 의 live phases·미터 이름)로 범주 K0–K6 을 셈(§9.4 규칙). 판정 상태(보충 C1 §6.2 C1-0 가드 (2) 의 Z1·Z2: `/f_blind`, J-1 잎 잡 상태(`gates_k91t.json` `4e59f61d…` 판정 항목, 하네스 `sa_gates.py` 사상 그대로, c20aff1d 트리 읽기)·J-2)는 건너뜀. 결과를 `C1D2/p0/c1g_states.json`·`C1_VALUES_C1_2` `/p0_15` 에(범주별 T, 없음, 건너뛴 상태 이름) | S_G 가 빔 → 보고·질문(S-C1-20). K0 없음 → 보고(C1G⁰ 가 대신) |
| **P0-16** D98 | §3 정의(D98-0…5, 4′ 포함)를 c1t 전 D98 상태 전부(§3 읽는 법 2, ≤ 91)에서 설정만으로 셈. 표·상태별 E≡0·K_E·X_E·C0E 목록을 `TC1/out/probe_r2/d98/` 에. 탐침 r2 의 첫 단계로 돎 | 거짓·INCOMPLETE → STOP(S-C1-18). 탐침 plant 16상태 E≡0 = 0 → 보고·질문(S-C1-20) |

- `C1D/C1_VALUES_C1_2.json` = P0-14·15·17·18 출력 값(S17·S17⁰, 구간 수, 상태별 무게 요약, S_G 목록 sha, 330상태 셈 일치 수). 첫 탐침 r2 계산(P0-16) **전에** LOG 에 sha 를 고정하고 그 뒤 바꾸지 않습니다. 옛 `C1_VALUES.json`(`7106e240…`)은 그대로 유효합니다(P0-14 (b) 가 PT2 에서 같음을 봄).

---

## 9. 탐침 r2 (보충 C1 §5 를 바꿈; 처음부터)

### 9.1 트리·도구·고정·출력

- 트리 PT2 = `git archive c20aff1d` + 탐침 패치 r2(옛 패치 `5cdc6eb1…` 의 모든 변경 + E23–E30 + 증거 S17). 패치 r2 manifest 의 `post` 에서, 옛 패치 파일 가운데 가드가 닿지 않는 파일(AFO·LPR·PRB·ADP·B0 배치 10·C1 증거 3)은 옛 `post` sha 와 같아야 합니다(manifest 대조, 다르면 S-C1-22).
- 도구 `C1D/tools/c12/c1_probe_r2.py`(D98 단계·C1G·C1G⁰ 팔·S_G·멈춤 1–9·보고), `C1D/tools/c12/c1_d98.py`(D98 셈, P0-3 훅 꼴), 자체 시험 `selftest_probe_r2.py`(합성). 팔 파일 `C1D/tools/arms_r2/{off, omega, m, h, c1, c1g, c1g_null, m_cap1, m_noheld}.json` — c1g·c1g_null 말고는 옛 `C1D/tools/arms/` 와 바이트 같음.
- **고정** `C1D/PINS_PROBE_r2.sha256`(첫 탐침 r2 계산 전): `C1_VALUES_C1_2.json`, `c1g_states.json`, 도구·자체 시험·자체 시험 출력, 패치 r2·manifest, 팔 9개, PT2 의 `c1_port.py`·`sdmpc.py`·`runtime_setup.py`·`k92_replay.py`·`k8b_commit_gates.py`.
- 출력 새 뿌리 `TC1/out/probe_r2/`(묶음 폴더 이름 `t<6자리>[_접미사]`). 옛 `TC1/out/probe/`(HALT.json 포함)는 기록으로 남기고 새 도구는 읽지 않습니다(G8).
- 도구 길: 결정 재생은 보충 C1 §5.1 [검토 RV-4] 꼴(가드 없는 재생 + 시작 전 (런 이름, T) 목록 점검; 목록 = `c1_states.json` 탐침 목록 ∪ `c1g_states.json` `/s_g`·`/c1g0_state`), plant 잡은 c20aff1d 하네스(F_SECOND 16상태). 단계 토큰 없음.

### 9.2 단계

1. **D98**(P0-16, ≤ 91상태 × 설정만; LOCK). 멈춤 규칙 §9.5-2 의 D98 몫과 E≡0 덮개(S-C1-20)를 여기서 봄.
2. **plant** 16상태 × {OFF, Ω, H} = 48잡(보충 C1 §5.1 그대로; 상태마다 LOCK).
3. **결정**: 탐침 5상태 × {OFF, Ω, M, H, C1, **C1G**, M_cap1, M_noheld} = 40 + **C1G⁰** × R-obs v3c3-s31 T=900 = 1 + **S_G × {C1, C1G}**(≤ 28). 합 ≤ 69. 팔 순서: c1g, c1, m, omega, h, off, m_cap1, m_noheld, 그다음 c1g_null, 그다음 S_G(상태마다 c1g, c1). 결정마다 LOCK.
4. **report**(LOCK).

### 9.3 팔·상태 (요약)

| 묶음 | 상태 | 팔 |
|---|---|---|
| plant | `/probe_plant_jobs` 16(R-obs v3c3-s31·s43 각 8) | OFF, Ω, H |
| 결정 T=900 | `/probe_decisions_T900` 5 | OFF, Ω, M, H, C1, C1G, M_cap1, M_noheld |
| 무작용 시험 | R-obs v3c3-s31 T=900 | C1G⁰ |
| 가드 상태 S_G | `c1g_states.json` `/s_g`(≤ 14) | C1, C1G |

- 모든 상태의 직전 행동: T=900 은 그 런 `action_000750`(`sdmpc_state` 없음), S_G 는 R-obs `action_<T−150>`(NoControl, `sdmpc_state` 없음 [실행 보충 C1 `rev_c1_robs2.json`]) → `load_prices` 를 지남, 규칙 X⁻ 안 닿음.

### 9.4 S_G 고르는 규칙 (GG11; 규칙 안 문턱은 데이터 뒤; 관측만)

- R-obs v3c3-s31·s43 각각, T ∈ {1,050, 1,200, …, 8,850} 를 오름차순으로 봄. 판정 상태(Z1·Z2)는 건너뜀.
- 범주(무게·방아쇠는 §5.5–§5.7 값, 같은 무게 0 을 적용한 뒤):
  - **K0** 모든 신호 무게 0 이고 미터 가드 방아쇠 0.
  - **K1** `SC1001_p3` 무게 > 0.
  - **K2** `SC1004_p3` 또는 `SC1004_p4` 무게 > 0 이고, 그 현시에 귀속된 구간 가운데 링크 71·10641·126·10643 위의 것이 있음(FW_E 10643 길).
  - **K3** FW_E 미터 넷(RM_C10639·10681·10490·10484) 가운데 하나라도 가드 방아쇠 참.
  - **K4** 한 신호에서 무게 > 0 인 현시가 둘 이상.
  - **K5** 점수 −1 인 머리 차로가 있음.
  - **K6** K1 이 처음 참인 결정 바로 앞 결정(T_K1 − 150; 대조). 그 T 가 1,050 보다 작으면 더하지 않음.
- 차례: K0, K1, K2, K3, K4, K5 가 각각 "아직 고르지 않은 T 가운데 처음 참인 T" 를 가짐; 그 뒤 K6. 같은 T 는 한 번만. 끝내 참이 아닌 범주는 "없음". 런마다 ≤ 7, 합 ≤ 14.
- 상태 열쇠 = (런 이름, T). 시드 = `c1_states.json` `/runs` 의 provenance `/seed`(폴더 이름에서 읽지 않음).
- 참고 [추론, 판정 아님]: R-obs 가 NC3 와 같은 교통이면 K1 은 v3c3-s31 2,700 s·v3c3-s43 2,100 s 근처, K2 는 1,050·1,650 s 근처 [읽음 GG r1 F-G14, §1.3]. 실제 값은 P0-15 가 셈.

### 9.5 멈춤·질문 (보충 C1 §5.4 를 바꿈; 하나라도 참이면 구현 전에 그 처리)

1. 그대로: 예외·장부·불변식 위반 1건 이상 → STOP.
2. **바꿈**: H 팔 plant 궤적(행별 `model_stock_veh`) ≠ OFF(비트), 또는 Ω 팔이 §3 의 T1(E≡0 상태)·T2(E≢0 상태) 가운데 그 상태에 맞는 규칙에서 거짓, 또는 D98 거짓 → STOP. (T2 뒤 행 차이는 C0·C0E·C3′ 로 나눠 보고.)
3. 넓힘: M·C1·C1G 팔 5상태 모두 조임 없음(보충 C1 S-C1-7 의 "조임 고름" 정의) → 보고·질문.
4. 넓힘: C1 팔 5결정 벽시계 **중앙** > 1,500 s, 또는 C1G 팔 5결정 중앙 > 1,500 s → 보고·질문. S_G 결정의 벽시계는 따로 보고(중앙·최대).
5. **새**: 가드 행·가드 하한이 없는 결정(C1G·C1G⁰ 결정 메타에 'constrained' 영수증 0 이고 `guard_triggered` 참인 미터 0; K0 상태와 C1G⁰ 상태는 늘 여기에 듦)에서 C1G(또는 C1G⁰) 결정 ≠ 같은 상태 C1 결정(§10.2 A_C1G-M 말고 보충 C1 §6.3 PASS 아님) → STOP.
6. **새**: 가드 행이 있는 결정에서 독립 재계산(§10 G-K2 (h)와 같은 셈: 관측 무게 → w̃, `lp_inputs` 로 M_k LP, r_k = min(2, 0.5 M_k), 'constrained' ⇔ r_k ≥ 0.01, 미터 하한 = §5.7 식 + RV-2)이 결정 메타와 다름(w̃ 상대 1e-12, M_k 상대 1e-9, 상태·하한 같음), 또는 관측 무게·미터 방아쇠가 `c1g_recount.py` 의 같은 상태 값과 다름(G-K2 (f) 꼴) → STOP. "계획이 행을 만족" 은 `coord.validate`(PT SD:1148)가 이미 강제하므로 구성상 참이고 보고만 합니다.
7. **새**: S_G 가 빔 → 보고·질문.
8. **새**: 가드가 만든 결정 실패(가드 ValueError: LP·seed·프레임 없음·sha 다름) → STOP.
9. **새**: 가드 행이 있는 신호의 직전 기준 녹색이 블록 0 현시 행 [glo, ghi] 밖(`reference_in_phase_limits` 거짓)인 결정이 있음 → 보고·질문(실현 논거 §5.6 의 가정이 서지 않음; 멈춤 아님).
- 그 밖: 탐침 산출이 없거나 끝나지 않음(INCOMPLETE) → 다시 돌리지 않고 보고·질문. 멈춤이면 `TC1/out/probe_r2/HALT.json` 을 쓰고 다음 계산을 하지 않습니다.
- S-C1-3 의 몫: 멈춤 1·2·5·6·8 → 구현 전 STOP·질문. 3·4·7·9·INCOMPLETE → 구현 전 보고·질문.

### 9.6 보고 항목 (보충 C1 §5.2 에 더함)

- 머리: "탐침, 판정 아님". Ω701 을 주 목적으로 앞에 적고 Ω635·OUTW·④ 쪽 값은 같은 표에.
- D98 표(상태별 E≡0, K_E, X_E, C0E 첫 차이 행, "K_E ∪ N1 밖 첫 행").
- 상태별 넘은 구간(종류별 수, 귀속 근거·부분 그래프 칸 수), 신호별 무게·블록별 영수증(r_k, M_k, status, max|w̃|, 실제 녹색 초 = r_k ÷ max|w̃|), `equal_weights_zeroed` 신호, 겹침 최댓값으로 버린 점수, seed 투영 여부, C1G − C1 의 신호별 계획 녹색(블록 0), 미터 블록 0 녹색과 가드 하한(그 결정에서 M1 이 조이려 했는지), M_k < 4 s 블록 수, −1 차로 목록, 연속 행 결정 수(S_G 안에서).
- FW_E 줄(SC1001 p3, SC1004 p3·p4, FW_E 미터 넷)과 FW_W 감시 줄(10491·RM_C10480·10482·10644·10646).
- 보고서 `C1D/C1_PROBE_R2_RESULTS.md`·`.json`, 설명 `C1D/P0_C1_2.md` 이어 씀(+ RC1 사본).

---

## 10. 관문 바뀜 (보충 C1 §6.3–§6.5)

### 10.1 관문 표

| 관문 | 바뀜 |
|---|---|
| G-K0 | 그대로(키 끔). 커밋 C1-G 에서도 돌림(전부) |
| G-K1 정적 | (e) C1G: 같은 상태 P0-14 (a) 집합과 같음; C1·Ω·M·H 는 보충 C1 그대로. (g) 옮긴 함수에 `constrain_storage_capacity`·`storage_capacity_seed` 를 더함(9개) — `ast.dump` 가 CX `constrain`·`operating_seed` 와 같되 함수 이름, 읽는 속성(`urban_storage_guard` → `c1_storage_capacity_guard`), 영수증 속성(`urban_storage_receipt` → `c1_storage_capacity_receipt`)만 다름. (h) E1–E30. (i) 불변 목록 그대로 |
| **G-K1 동적** | Ω(C1-1)·H(C1-3)·**C1G(C1-4; 보충 C1 의 "C1 팔")** 33잡. H 는 그대로(행별 `model_stock_veh` 숫자 잎 차 0). Ω·C1G 는 §3 T1/T2: E≡0 상태 = 숫자 잎 차 0, E≢0 상태 = T2 (i)(ii)(iii). 차이 무리: C0 = 보충 C1 정의 그대로(S_add 목록·고정 경로), E≢0 상태의 K_E ∪ N1(K_E) 키는 **C0E** 로 따로 적고 C0·C3 어디에도 넣지 않음, **C3′** = 그 밖 키. 멈춤 = `c3_before_c0` 를 C3′ 과 C0 로 그대로 셈(C0 차이가 없는데 C3′ 차이가 있으면 앞선 것으로 봄; OU `k92_gates.py:465` 꼴). C0·C0E·C3′ 첫 차이 행을 상태마다 보고 |
| **G-K2 (d)** | E≡0 상태: 궤적 같음 + Ω 목적 − OFF 목적 = L_Δ(상대 1e-9). E≢0 상태: 보고만(Ω 목적 − OFF 목적, L_Δ, D66, 경로 몫 = (Ω − OFF) − L_Δ) |
| **G-K2 (f) 새** | 재현: `c1g_recount.py`(C1P 를 import 하지 않음)가 같은 상태 기록·프레임·증거에서 다시 센 구간 차 수·S·F·칸 넘음·귀속·겹침 최댓값·같은 무게 0·무게·미터 방아쇠 = RS 메타 값(정수·불 같음, 무게 상대 1e-12). 대상 = G-K4 의 C1G·C1G⁰ 결정 상태 |
| **G-K2 (g) 새** | 무작용: 가드 행·하한이 없는 결정(§9.5-5 정의; K0 상태와 C1G⁰ 상태)에서 C1G·C1G⁰ 결정 = C1 결정(A_C1G-M 말고 §6.3 PASS). 대상이 0개면 INCOMPLETE(통과로 세지 않음) — C1G⁰ 상태가 늘 있으므로 0 이 되려면 그 결정이 없어야 함 |
| **G-K2 (h) 새** | 작용: 행이 있는 결정에서 §9.5-6 의 독립 재계산 = 결정 메타. 계획의 행 만족은 보고 |
| G-K3 | 더함(모두 ValueError, 자식 프로세스 0): §5.10 키 검사 위반 각각; `storage_capacity_guard` 만 있고 `storage_release_guard` 없음; 증거 sha·schema·간격(≠ 6.0)·번짐 상수 다름; `complete` 거짓; 프레임 없음·sha 다름·센 차의 길이 없음; `reserve_green_sec` > 2; 고르지 않은 선택값(`unit: "link"`, `full_rule: "count"`, `feeder_attribution: "first_server"`, `meter_rule: "m4_or"`, `short_receiver_rule: "spill"`, `landing_sources: false`); `make_config --c1` 이 하위 키 **8개** 전부를 씀 |
| G-K4 | C1-G 커밋 트리로: C1G 팔 탐침 5결정 + C1G⁰ 1결정 + S_G × C1G(≤ 14) 가 탐침 r2 같은 팔과 같음(보충 C1 G-K4 조건: 모든 차이가 상대 1e-9 이하이고 연산 순서로 설명, 결정 HARD 같음, D5 는 A_C1 조건). 그리고 C1 팔(가드 키 없음) 5결정이 탐침 r2 C1 팔과 같음(G12) |
| G-K5a | 그대로(키 끔 벽시계, C1-G 에서도) |
| G-K5b | 대상 팔 C1G: C1-G 관문 = G-K4 의 C1G 5결정 **중앙** ≤ 1,500 s, R 단계 = R-a 5 + R-b 39(C1G). C1-2 관문 값(M 팔)은 그대로 |
| G-RR (b) | 키 켬 팔 = C1G. A_C1-M 에 §10.2 의 가드 경로를 "새 쪽에만 있을 때 허용" 으로 더함 |
| **G-D98 새** | P0-16 과 같은 정의를 커밋 C1-1(Ω)·C1-4(C1G)·C1-G(C1G) 트리에서 G-K1 동적 33상태(설정만, Ω·C1G·OFF)에 다시 셈. 거짓·INCOMPLETE → STOP(S-C1-18) |
| **B (가드) 새** | `build_c1_evidence.py guard --check`: 커밋 증거 바이트 = `C1D2/p0/c1g_storage_segments_v3c3.json` 바이트(S17) |

- 관문 스크래치 트리에 빈 증거를 넣는 법: G-K2 (g)·G-K4 의 C1G⁰ 결정은 `git archive <커밋>` 트리에 `C1D2/p0/c1g_storage_segments_null_v3c3.json`(S17⁰)을 같은 증거 폴더로 복사한 트리(`TC1/trees/c1_g_<sha8>_null`)에서 돌립니다. 복사 뒤 그 파일 sha = S17⁰, 그 밖 파일은 커밋 트리와 같음을 `tree_manifest.json` 으로 봅니다.

### 10.2 선언 차이 더함 (보충 C1 §6.3)

- **A_C1-M 에 더함**(키 켬 대 기록·대 키 끔; 새 쪽에만 있을 때만 허용): `/metadata/joint_leader_selection/c1_storage_capacity_guard`, `/metadata/joint_leader_selection/meter_operating_bounds/ramps/*/guard_triggered`, `/metadata/joint_leader_selection/meter_operating_bounds/ramps/*/guard_sources`. `/metadata/c1_port`(하위 전체)는 이미 있음. 결정적 잎 조건 더함: `/metadata/c1_port/storage_capacity_guard/evidence_sha256` = S17(C1G⁰ 이면 S17⁰).
- **A_C1G-M 새**(C1G·C1G⁰ 대 같은 상태 C1 비교에서만; 탐침 멈춤 5·G-K2 (g)): 값 차이로 허용 — `/metadata/c1_port/keys`(옛 = 7키 정렬 목록, 새 = 그 목록 + `storage_capacity_guard` 정렬). 새 쪽에만 있을 때 허용 — `/metadata/c1_port/storage_capacity_guard`, `/metadata/joint_leader_selection/c1_storage_capacity_guard`, `/metadata/joint_leader_selection/meter_operating_bounds/ramps/*/guard_triggered`, `…/guard_sources`. 결정적 잎 조건은 위와 같음. 그 밖 차이는 미분류(→ 보류 → STOP).
- C0–C3 분류: 가드 메타는 무리에 넣지 않음(조건으로만). 가드 때문에 바뀐 신호 녹색은 C1 무리(보충 C1 정의 그대로).

### 10.3 커밋별 관문 표 (보충 C1 §6.5 를 바꿈)

| 커밋 | 관문 (순서대로; 앞이 PASS 가 아니면 다음 없음) |
|---|---|
| C1-0 | 보충 C1 그대로 + 가드 자체 시험 (5) 의 S_G 항목(§7) |
| C1-1 | 보충 C1 그대로(U, B(omega), G-K0, G-K1(Ω 정적 + 동적 T1/T2), G-K2(d) 새 정의, G-K3(Ω), G-K4(Ω), G-K5a) + **G-D98(Ω)** |
| C1-2 | 보충 C1 그대로 |
| C1-3 | 보충 C1 그대로 |
| **C1-G** | U(새 `test_c1_guard.py` 포함), B(가드), G-K0(전부), G-K1 정적(가드 몫 (e)(g)(h)(i)), G-K2 (f)(g)(h), G-K3(가드 몫), G-K4(C1G 5 + C1G⁰ 1 + S_G + C1 팔 5), G-K5a, G-K5b(C1G G-K4 값), G-D98(C1G) |
| C1-4 | G-K0(D-c·plant), G-K3(전부, 8키), G-K1(C1G 팔 정적 + 동적 33잡 T1/T2), G-D98(C1G), 팔 동일성(`sa_arms.py --c1` 팔 파일 − 바탕 = `c1_port` 하위 8키만), `make_config_n31.py --c1 --check` |

---

## 11. 커밋 계획 (보충 C1 §6.1–§6.2 에 더함)

- 브랜치·공통 규칙은 보충 C1 §6.1 그대로(새 브랜치 `claude/c1-port-20261027` 를 c20aff1d 에서, 명시 경로만, `git -c user.name=Ming2you -c user.email=alsrjsrb1915@snu.ac.kr`, 끝 줄 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, 푸시 0, `ls-tree` 블롭 = `hash-object --no-filters` 작업 바이트 확인).
- 메시지 첫 줄 꼴(모든 C1 커밋): `C1-n: <요약> (amendment C1 a98580dd2d787007 + C1-2 <C1-2 고정판 sha16>)`.
- **커밋 순서**: C1-0 → C1-1 → C1-2 → C1-3 → **C1-G** → C1-4.

| 커밋 | 파일 (명시 경로) | 런타임 |
|---|---|---|
| C1-0 | 보충 C1 그대로 + 기록기 새 필드에 가드 칸(`/metadata/c1_port/storage_capacity_guard`·`/metadata/joint_leader_selection/c1_storage_capacity_guard` 가 있으면 `c1_record.json` 에 요약: 넘은 구간 수, 신호별 무게, 영수증 상태 수, 미터 가드 하한) — C1-1…C1-4 는 하네스를 바꾸지 않는다는 보충 C1 G-K0 [검토 RV-21] 규칙 때문에 여기서 미리 넣음. 가드 `c1_guard` 의 §7 고침 | 0 |
| C1-1 … C1-3 | 보충 C1 그대로. 단 C1P 의 `KEYS` 에 가드 키를 넣지 않음(C1-1 의 "다른 하위 키 → ValueError" 규칙이 C1-G 전까지 가드 키도 막음) | 있음(키 없으면 0) |
| **C1-G** | `evaluation/controllers/c1_port.py`(E28·E29·E30), `evaluation/controllers/runtime_setup.py`(E23), `evaluation/controllers/sdmpc.py`(E24–E27), `diagnostics/sdmpc_n31_20260924/c1/evidence/c1g_storage_segments_v3c3.json`(S17), `diagnostics/sdmpc_n31_20260924/c1/build_c1_evidence.py`(하위 명령 `guard`, `--check`), `diagnostics/sdmpc_n31_20260924/tests/test_c1_guard.py` | 있음(키 없으면 0) |
| C1-4 | `make_config_n31.py --c1`(OUC 에 `c1_port` 8키 = `c1_port_section_c1g.json` 값), `config_n31_v2_c1.json`, `c1/README.md`, `c1/WORKLOG_20261027.md` | 0 |

- **줄 끝·바이트**(보충 C1 §6.1 꼴): `c1_port.py` LF(`text eol=lf` 줄, C1-1 이 더함), RS(줄 끝 섞임: 앵커 줄 규칙, 커밋 뒤 바뀐 줄 밖 CR 수 그대로), SD(작업 CRLF·블롭 LF: `git hash-object <작업 파일>` = 블롭, `git diff c20aff1d --ignore-cr-at-eol` = `git diff c20aff1d`), 증거·빌더·시험(`diagnostics/sdmpc_n31_20260924/** -text`, 블롭 = `hash-object --no-filters` 작업 바이트).
- **`test_c1_guard.py`(합성, 새 시험; 모두 통과해야 함)**: 차 수·경계(허용오차 없음), 번짐 S0·S(12 m 이하 구간 포함, 프레임 길이), 용량 넘음 ≥ 경계(길이 6 m 정수배), 짧은 원천 제외·짧은 칸 지나감, 칸 그래프 갈림(129 [239.4, 300.0] → 10490·10777), 차로 바꿈 귀속(10643 → 71 차로 4·5), 같은 링크 머리 제외, 받는 쪽 −1·짧은 받는 쪽 차 수만, 겹침 최댓값(A:127 + L:10481), 같은 무게 0(SC7 동시현시 포함), 거의 같은 무게(정규화 차 0.05) 영수증·실제 초, 행·영수증(codex 꼴), 3블록 M_0 < r 경우, 밀리초 반올림 seed(1.05), 미터 OR + RV-2 + G-A7(미터 8개 표 × 직전 녹색 모든 표 값), 머리 앞만 넘음 → 방아쇠 아님, 키 끔 같음(같은 객체·속성 없음), 빈 증거 무작용, 거부(G-K3 목록), 옮긴 두 함수 `ast` 같음.

---

## 12. R·J·F 의 팔 (보충 C1 §8–§9)

### 12.1 R

- R-a·R-b 팔 = **C1G**(배포 팔 값, 튜닝 `config_n31_v2_c1.json` 8키), 트리 = C1-4 커밋 트리. 상태·식·표지("이미 본 상태(V-A 기록), 독립 근거 아님")는 그대로.
- **S-C1-9(R-b SG2) 그대로**: 같은 식(보충 C1 §8.2, GREEN 만), 같은 100 s, 팔만 C1G. ⟨Q3⟩ 는 바꾸지 않음(D-K9-100).
- R-b 보고 표에 더함: 결정별 넘은 구간 수(종류별), 신호별 무게·영수증 상태, 미터 가드 하한·`guard_sources`, SC1001 p3 무게, 연속 행 결정 수. R-b 에서는 V-A 관측이라 가드가 거의 매 결정 켜질 것입니다 [추론, GG r1 §1.5]. 가드 몫을 R-b 에서 따로 가르지 않습니다(GG12 (가)); 몫은 탐침의 C1G − C1 짝으로 봅니다.
- 닫힌 잎 11개(`c1_chain_closed_leaves.json`)는 그대로. 가드 메타에는 경로 문자열이 없어 닫힌 잎을 늘리지 않습니다.
- `/g_rr_c_b` 의 D98 은 §3 읽는 법 2 대로.

### 12.2 J (c1t, 보고만)

- J-1·J-2 의 키 켬 팔 = **C1G**(SAF-K91 계열 `--k92b1 --c1`, 8키). 규칙 X⁻ 그대로(R-obs 상태는 직전 NoControl 이라 C1G 그대로).
- 단계 토큰: `--gates-stage c1t --declaration-sha <보충 C1-2 고정판 sha256>`(§7).

### 12.3 F (c1t, 블라인드, 보고만)

- **F-D98**: F 표본 50상태(`/f_blind`)마다 Σ_k |E_k|, 차가 있던 C29 커넥터 수, K_E 목록, K_E ∩ S_add(설정만, OFF·Ω).
- **F-Ω 두 팔**(G7 (가)): OFF plant 잡 D66(보충 C1 §9.2 그대로) + **Ω plant 잡 D66**(새 50잡). 둘 다 같은 66링크 VISSIM 체류와 나란히. 차이는 "경로 효과 + 회계 몫" 으로 적습니다.
- **F-G**: F 표본 50상태의 가드 관측(`storage_capacity_core`, 관측만): 넘은 구간 수·신호별 무게·미터 방아쇠 수.
- 나머지 F 칸(F-S·F-S2·F-M)은 그대로. 절대 문턱 없음.

---

## 13. 보고 정의 (데이터 전 보고 칸; 숫자 없음, 문턱 없음)

### 13.1 목적·주 보고 영역 = Ω701 (D-K9-104)

- 모든 보고(탐침 r2·R·폐루프 §11.2)의 첫 줄은 Ω701 입니다. Ω635·Ω701 − Ω635(66링크)는 그 아래 보조 줄로 둡니다. Ω 숫자는 늘 ④·Ω 밖과 같은 표에.
- 우선순위 표시: ① FW_E 본선·② 동측 국소 줄을 표 위쪽(주 목표)에, FW_W 본선(26·120·10771)·④b 1099·FW_W 미터 넷 줄은 "감시" 로 표시합니다.

### 13.2 도시도로 = codex 분할 하나 (D-K9-104)

- 정의: Ω701 안 링크에서 양방향 본선 사슬(FW_E·FW_W), 진입(미터) 커넥터 8개(10480·10482·10646·10644·10639·10681·10490·10484), Ω701 안 진출 커넥터를 뺀 링크 전부. 진출램프 = Ω701 안 진출 커넥터(10479·10645 는 Ω701 밖) [읽음 `CH/OMEGA701_V3C3.md:16`, `HO/analysis/original_scripts/solo355_compare_20261014.py:49-61`, `HO/derived/reporting_partition.json`].
- 분할 칸(codex 꼴 이름): FW_E(사슬) · FW_W(사슬, 감시) · onramps_E · onramps_W · **urban_roads(도시도로)** · offramps(진출램프) · outside(Ω701 밖). 검사: FW_E + FW_W + onramps_E + onramps_W + urban_roads + offramps = Ω701(\|차\| ≤ 1e-6 veh·h).
- 우리 규칙 분할은 주 표에서 뺍니다(HANDOFF_RESULTS H12 (a) 를 바꿈).
- 보충 C1 §11.2 표에 줄 더함: "도시도로(codex 분할) / 진출램프(codex) / onramps_E / onramps_W(감시)". 이 분할은 가드 규칙에 쓰지 않습니다(증거 `part` 칸은 보고용).
- 도구 점검(COMPARE_RULE_C1 고정 때, C1 런 전; 보충 C1 §11.3 에 **X9** 로 더함): 분할을 구현한 도구가 64cf-s29 codex NC·joint 의 codex 요약 FW_E·도시도로·Ω701·FW_W 수준을 \|차\| ≤ 1e-6 veh·h 로 재현(VERIFY_FWE 가 같은 재현을 1.3e-11 로 보였음 [읽음 FD LOG 18:12]). 아니면 STOP.

### 13.3 C1 FW_E 기준 줄 (D-K9-106·110·111)

- 아래 인용은 `FD/FWE_DECOMP.md` r2(`7f58ab3e…`) §3.3 의 글(그 파일 :260)을 **글자 그대로** 실은 것입니다(조립 도구가 원문 바이트를 넣음 [실행]). 글 안의 "C1" 은 이 보충의 배포 팔 C1G 의 런을 뜻합니다(§7).

> **C1 FW_E 기준 줄 (데이터 전 보고 칸, D-K9-106)**. C1 의 규칙·관문·문턱은 바꾸지 않는다. C1 런이 끝나면 같은 시드(v3c3-s31·s41·s43)마다 C1 − NC3 · C1 − V-A · C1 − B 를 칸 RF1–RF11 과 "함께"(Ω701·④·Ω 밖 (a)(b))로 적고, `FWE_REF_C1.json`(sha256 은 고정 목록)의 같은 칸(P-VA·P-B·P-BVA·P-VSL)과 나란히 둔다. 칸 정의는 `PRE_FWE.md` §6.2·§5·§7(sha256 `c7cc0e6c…ce94`), 도구는 거기 핀된 것과 `fwe_synth.py` 를 그대로 쓴다. 판정 문턱은 없다. 시드 평균 없음. 64cf joint − NC 는 옆 열로만 둔다. FW_W(④b 1099·FW_W 본선·FW_W 미터)는 감시 칸에만 둔다. 도시도로는 codex 분할만 쓴다. 미터 녹색은 GREEN 초만 센다. LDP 가 모든 초 빈칸인 미터는 "상태 기록 없음" 으로 적고 조임으로 읽지 않는다.

- 고정 목록에 넣는 것(이름 + sha256): `FD/out/FWE_REF_C1.json`(`ce39344bfbbe1b7c0b7d88ba129791b1772d551dad0ab74a0d8d2c36a90febc4`), `FD/out/FWE_REF_C1.md`(`9838f39ed9ad1e0e2ca2c311e443788615568f6309acf783ced614f561ddb2eb`), `FD/tools/fwe_synth.py`(`92904e95444b2b18e3745f5ba7d7b9e2dbc2a13064bcb3ad1e5680e244e97245`), `FD/PINS_FWE_SYNTH.sha256`(`1546c82a…`), `FD/PRE_FWE.md`(`c7cc0e6c…ce94`), `FD/PINS_FWE*.sha256`·`FD/verify/PINS_VERIFY.sha256`(§16).
- **글의 차례**(D-K9-110 결정 2 (가)): FW_E 글의 첫 줄은 C1 − V-A 와 C1 − B, 그다음 C1 − NC3. 칸은 세 짝 모두 적습니다. 까닭 [읽음 FWE_DECOMP §4-2]: 셀 5–9 공통 몫이 지워지고(B − V-A ±0.3), C1 − V-A 는 VSL 정책이 같음(D-K9-101).
- **잡음 줄**(D-K9-111): v3c3 같은 시드 짝의 잡음은 "모름" 으로 적고, 64cf A1 − joint 잣대(① +32.5, Ω701 −11.0, ④ −28.9 veh·h; 다른 망, 한 시드)를 옆에 둡니다 [읽음 결정 기록 :375]. 세 시드에서 "조임 → 합류 감소 → B1·B2 감소" 의 때·자리가 함께 맞는지를 나란히 적습니다(판정 문턱 없음).
- **가드 옆 칸**: C1G 보고에 "가드 미터 하한이 걸린 결정 수(FW_E 미터별)" 를 RF4 옆에 둡니다(GG r1 §3.11; 문턱 없음).
- **읽기 정정 메모**(D-K9-110): `FD/R3_REPORT.md`(`0f5454de…`) :27·:31·:422 의 "풀렸다/풀었다" 읽기는 FWE_DECOMP r2 §6 #1–#3 대로 읽습니다 — 그 칸에서 B 의 미터는 풀리지 않았고(평균 GREEN 2.0 / 2.7, 모든 주기 GREEN < 10), 합류 차 + 는 NC3 쪽 합류가 줄어 생긴 것입니다 [읽음 FD/VERIFY_FWE X4]. R3 바이트는 바꾸지 않습니다. 셀 5–9 기구 확인은 지금 하지 않습니다.

### 13.4 데이터 뒤 칸 DA1–DA4 (C1 보고 전용; 깃발·판정에 쓰지 않음)

| 칸 | 정의 | 도구(이름 + sha256) | 기준 값 |
|---|---|---|---|
| **DA1** | 셀 5–9(2,631–4,543 m) d① 900 s–끝과 × 900 s. **셀 배정 = 100 m 칸 가운데**(칸 b 의 가운데 (b + 0.5) × 100 m 가 놓인 셀; `fwe_r2.py:604-607` `cell_of((b + 0.5) * 100.0, CB)`) | `fwe_r2.py` `59017c86ff6d640bf72709a13ed88790ca0deb2785ba8da0a3d18df1c1218850` → `fwe_r2_after.py` `6bccb4c4c6046a75b2108e5c84be06eaac4d779cee11588c3fc1d07ad49833e2` | `FD/out/R2_after.json`(`b25c30ad…`): P-VA −0.2/−63.1/−13.0, P-B +0.1/−63.4/−12.9, P-BVA +0.3/−0.3/+0.1 [읽음 FWE_DECOMP §3.4] |
| **DA2** | 4,300 m 머리 분과 셀 5–9 혼잡 분(R1 규칙, 900 s 칸) | `fwe_r1.py` `658828903f3abe361484b90edd2f8f3a7f63bb23c64c8b8567002cdea1769d93` → `fwe_r1_after.py` `d00dfb9b42e9950f759190a307496f9804ca0fcb1d358c5809a82e8e0a2cc68f` | NC3 머리 0/34/15 분, 셀 5–9 혼잡 0/136/40 분 [읽음 FWE_DECOMP §3.4] |
| **DA3** | "묶인 합류 칸 수" = 900 s 칸 가운데 그 미터 `tight` ≥ 0.30 이고 합류 차 `d` ≤ −60 veh/h 인 칸 수(미터마다). DA4 출력에서 그 두 칸만으로 셈(산술만, 새 도구 없음) | DA4 출력 | B ×3·codex joint 는 `VERIFY_EXTRA2.json`(`29e49a51…`)에서 같은 산술로 셈(C1 런 전, COMPARE_RULE_C1 고정 때) |
| **DA4** | RF5 의 900 s 칸마다 같은 칸 미터 평균 GREEN(`g`)·조임 몫(`tight`)·팔 합류 수준(`arm`)·기준 합류 수준(`base`)·합류 차(`d`)·미터 쪽 재고 차를 나란히. "합류 차 > 0" 칸을 미터가 풀었다고 읽지 않게 함 | `FD/verify/tools/vf_extra2.py` `3777458df2dcb941436b2649cbb4006dd4f00ee62ed8d583d1d80007cb8d9a7e`(입력 도구 `vf_fzp.py` `f0ad6e4c…`·`vf_meter.py` `4425fd99…`·`vf_compare.py` `ab8c6091…`, 핀 `PINS_VERIFY.sha256` `7b60498a…`) | `VERIFY_EXTRA2.json`(`29e49a51…`; B ×3·codex joint, 미터 넷) |

- C1 짝(C1 − NC3·C1 − V-A·C1 − B)에 쓰는 사본: 위 도구의 **짝·런 상수만 바꾼 사본**(바뀐 줄 목록과 사본 sha 는 COMPARE_RULE_C1 고정 때, 첫 C1 런 전 LOG 에). 사본이 B 짝에서 원본 출력(`R2_after.json`·`VERIFY_EXTRA2.json`)의 같은 칸을 같게 냄(보충 C1 §11.3 X3 꼴, 아니면 STOP; §11.3 에 **X10** 으로 더함).
- 표지 "데이터 뒤 칸(보고 전용)". 시드 평균 없음.

### 13.5 VSL 줄 (D-K9-103 Q-V6)

- C1 − B 의 **① FW_E 본선 줄과 ④b 입력 1098 줄**에 함께 적음:
  - "VSL 정책 다름: C1(V-A 꼴 VSL, DSD 59–66 에 101) 대 B(110 고정)".
  - 두 팔의 FW_E VSL 110 미만 결정 수와 시각: 결정 `T` 의 행동 CSV `action_<T>.csv` 에 `kind = vsl` 이고 `speed_kph` < 110 인 행이 하나라도 있으면 그 결정을 셈(RF10 꼴). 참고 V-A 9 (3,450–4,650 s) / 10 (2,550–4,050 s) / 14 (2,850–4,950 s), B 0 [읽음 FWE_DECOMP §3.2 RF10].
  - 참고 크기: v3c3 VSL 단독 − NC3 의 ④b 1099 −57.8 / +145.9 / +53.0 veh·h(v3c3-s31 / s41 / s43) [읽음 `VS/VSL_REPORT.md:93`, `VS/VSL_RESULTS.md` r2 §1.2]. "잡음 추정 아님" 표지를 붙임.
- C1 − V-A 줄에는 "같은 VSL 정책, 폐루프라 VSL 출력은 다를 수 있음" 과 두 팔의 110 미만 결정 수·시각을 적습니다.

### 13.6 가드 보고 칸 (폐루프 §11.2 에 더함)

- 결정별 가드: 넘은 구간 수(종류별), 행이 있는 신호 수, −1 차로 수, 미터 가드 하한 수(미터별), seed 투영 수. 사슬 줄(보충 C1 §11.2) 옆에 SC1001 p3 무게와 L:10481·F:129·L:10491 넘음 결정 수.

### 13.7 보충 C1 §11.1–§11.2 를 이 꼴로 읽음 (숫자 없음; 발사는 다시 물음)

- §11.1: 런 = **C1G** 팔(`config_n31_v2_c1.json` 8키, 우리 러너·우리 동결본) v3c3-s31·s41·s43. 짝 NC3(같은 시드), V-A(같은 시드, 같은 줄기, **C1G 8키만 다름**), 참고 B(다른 제어기). 시드 3, 평균·신뢰구간 없음, 발사 전 다시 물음(S-C1-13).
- §11.2 표 (veh·h; 시드마다 짝 하나; 열 = C1G − NC3 · C1G − V-A · 참고 C1G − B; 줄 순서 고정):

| 줄 | 비고 |
|---|---|
| **Ω701**(주) / Ω635 / Ω701 − Ω635(66링크) | Ω 는 ④·Ω 밖과 같은 표 |
| ④a / **④b(첫 관측 차분, 주 값)** / **④** | |
| **Ω 밖 (a) Ω701 기준** / Ω635 기준, Ω 밖 (b) Ω701 기준 | |
| **① FW_E 본선 7링크** / **② 동측 국소 19링크**(주 목표) | C1G − B 줄에 VSL 줄(§13.5) |
| FW_E 기준 줄 RF1–RF11 + 함께(Ω701·④·Ω 밖 (a)(b)), 데이터 뒤 칸 DA1–DA4 | §13.3–§13.4, FWE_REF_C1 의 P-VA·P-B·P-BVA·P-VSL 와 나란히, 64cf A1 − joint 잣대 옆 |
| 도시도로(codex 분할) / 진출램프 / onramps_E / onramps_W(감시) | §13.2 |
| ④b 중 입력 1099(감시) / **1098** / 도시 입력 | 1098 의 C1G − B 줄에 VSL 줄 |
| 링크 66 (SC1004 남측) | |
| 링크 124·10483·10480 (Q6), 링크 70·10639·10638·120 | |
| FW_W 본선(26·120·10771)·링크 26 (감시) | |
| 가드 칸(§13.6) | C1G 만 |
| 사슬 줄·미터 줄 | 보충 C1 §11.2 그대로(GREEN 만) |

- §11.3 에 점검 **X9**(codex 분할 재현, §13.2)·**X10**(DA·RF 사본의 B 짝 재현, §13.4)을 더함. 둘 다 첫 C1G 런 전, 거짓이면 STOP.

---

## 14. STOP 규칙 (보충 C1 §12 를 바꾸거나 더함)

- **S-C1-3 넓힘**: 탐침 r2 멈춤 1·2·5·6·8 → 구현 전 STOP·질문. 3·4·7·9·INCOMPLETE → 구현 전 보고·질문.
- **S-C1-5 읽기**: "Ω/H 궤적 차" 를 §3 T1/T2 와 §10 G-K1 동적(C0E 따로, 멈춤 = C3′ 대 C0)으로 읽음. 대상 팔에 C1G.
- **S-C1-6 넓힘**: B(가드) 거짓, A_C1-M·A_C1G-M 결정적 잎 조건 거짓 → STOP.
- **S-C1-7 넓힘**: "조임 고름" 대상에 탐침 C1G 팔 5상태를 더함(탐침 M·C1·C1G 15결정 + R-b C1G 39결정을 통틀어 0 이면 폐루프 전 멈춤·질문).
- **S-C1-8**: G-K5b 대상 팔 C1G.
- **S-C1-9 그대로**: R-b SG2 멈춤(같은 식·100 s), 팔 C1G.
- **S-C1-10 넓힘**: 단계 토큰의 sha 는 보충 C1-2 고정판 sha(§7).
- **S-C1-18 새**: D98(0·1·2·3·4′·5) 거짓 또는 계산 못 함(INCOMPLETE) → STOP·질문(P0-16, G-D98, R 단계 `/g_rr_c_b` 는 "못 냄" 예외 §3 읽는 법 2).
- **S-C1-19 새**: G-K2 (f)(g)(h) 거짓·INCOMPLETE, 탐침 멈춤 5·6·8, 또는 R·관문·J 에서 가드가 만든 결정 실패 → STOP.
- **S-C1-20 새**: S_G 빔, 또는 탐침 plant 16상태 E≡0 = 0 → 보고·질문.
- **S-C1-21 새**: P0-17 (a)–(h) 하나라도 거짓, P0-18 (a)(b)(c) 거짓 → STOP.
- **S-C1-22 새**: P0-14 (a)(b)(c) 거짓, 또는 패치 r2 manifest 의 가드 밖 파일 sha 가 옛 `post` 와 다름 → STOP.
- **S-C1-23 새**: S17·S17⁰·`c1_port_section_c1g.json` 이 P0-17 뒤 바뀜, 또는 팔 파일·배포 파일·커밋의 가드 키 값이 §5.10 repr(S17 포함)과 다름 → STOP.
- **S-C1-24 새**: 고정점 `C1D/AMENDMENT_C1_2_FIXED.md` 전에 P0-14–18·탐침 r2·브랜치·커밋·관문·재생을 함, 또는 고정 뒤 이 보충의 정의·값·문턱·표본 규칙·판정 도구를 바꿈 → 무효, STOP(S-C1-1 꼴).
- 그 밖: 보충 C1 §12 그대로. 어떤 관문·점검이든 FAIL·보류·INCOMPLETE 는 STOP 이고 사용자가 정합니다.

---

## 15. 퇴행 막기 숫자 (보충 C1 §13 다음; 지금 고정)

| # | 값 | 출처 |
|---|---|---|
| RG-17 | U = (차 수 ÷ (길이 ÷ 6 m) ≥ 1.0) ∨ S; S 상수 12 m·5 km/h·20 m·max(20 m, 0.2 × 길이)·12 m 이하 S = S0; 짧은 구간 < 2.0대; 짧은 받는 쪽 = 차 수만; 겹침 최댓값(0.05 m); 같은 무게 0(1e-12); 미터 (라) (데이터 뒤) | §5, `c1g_guard_rule.json` `cebd6f05…` |
| RG-18 | r = 2.0 s, 검사 0 < r ≤ 2, required = min(r, 0.5 M), < 0.01 행 없음, seed 1.05 | CX USG:21, :134-138, :160 |
| RG-19 | 구간 수: 머리 차로 항목 216(codex 210 + codex 가 빼는 현시 머리 6; 차로로는 5), 공급 416구간·896차로(머리 차로와 겹침 34차로), 착지 9, 미터 머리 앞 10·접근 10, 짧은 156(공급 144·머리 10·착지 2), 받는 쪽 261(새 `R:` 137, 기존 구간 124), 겹침 61쌍(D5 뺀 58), 받는 쪽 없는 현시 머리 차로 3, 증거 구간 1,141 + 137 = 1,278 | GG r1 §1.1, RG-19 |
| RG-20 | 자료 비교(데이터 뒤): V-A 머리 차로 모사 행 결정 54 / 54 / 54, −1 결정 GG13 (나) 16 / 23 / 11(U/U 39 / 39 / 31), codex B 실측 −1 12 / 21 / 1; B 사슬 U 첫 켜짐 1,950 / 1,800 / 1,800 s; 미터 (라) B RM_C10639 14 / 0 / 26·RM_C10681 0 / 2 / 1 미터·결정; `gg_trig.json` `212774be…`, `gr_check.json` `be9385c6…`, `gr_meter.json` `3c8b99ba…` | GG r1 §1.3, §1.5b, §2.4 |
| RG-21 | D98: ε 1e-9 대; C29 29개 = 10049·10121·10127·10129·10130·10133·10134·10135·10139·10144·10149·10153·10225·10229·10430·10434·10435·10436·10459·10485·10489·10502·10503·10505·10506·10507·10524·10609·10633; 지지 문서 B0 판 `7d092b3db6e4107b47ecf751c60196e11a32120dc722d9221c1fb888d447faec`; 차가 있으면 E≢0 를 만드는 커넥터 18, E 에 0 을 더하는 커넥터 11(10049·10129·10133·10135·10144·10153·10225·10485·10502·10503·10609) | GD r2 :203·:205, §3.1 |
| RG-22 | 이미 본 상태 v3c3-s31 T=1,500 첫 행 차 `storage:SC106_to_SC12` +1.0, `storage:SC2005_to_SC101` +0.5, `storage:SC101_to_SC1002` −0.5(3키), 이웃 밖 첫 차이 행 134; Ω 궤적 차 82/638키 | GD r2 §1.8, C1_PROBE_RESULTS |
| RG-23 | 정책 토큰: C1·C1G·C1G⁰·M 계열 `522eec6f32f198a12ddb78ddec10962a73c7ebc32e2d1fcbb11f95975218d865`, 키 끔·C1G⁻ `428e650ded2f1cb8bb4365abac76ea9765da4783d19e8c2dab1bcd7b688399f9` | P0-6, §7 |
| RG-24 | 탐침 r2 수: D98 ≤ 91상태, plant 48잡, 결정 40 + 1 + S_G × 2(≤ 28) ≤ 69, S_G 런마다 ≤ 7·합 ≤ 14; P0-18 330상태(1,133 구간); P0-15 106상태 | §8, §9 |
| RG-25 | `c1_port` 8키, 가드 하위 키 11개 순서·repr(§5.10), 가드 규칙 파일 `cebd6f05f7ef8c4aee01eae0ca63bc02f0dacabcbf47aa0c9fb55196e43f6257`(정규 `2fb6be4f…`) | §5.10, §0 |
| RG-26 | FW_E 기준 줄: `FWE_REF_C1.json` `ce39344b…`, `.md` `9838f39e…`, `fwe_synth.py` `92904e95…`, PRE_FWE `c7cc0e6c…`, DA 도구 sha(§13.4); 64cf A1 − joint ① +32.5·Ω701 −11.0·④ −28.9 | §13.3–§13.4 |
| RG-27 | VSL 줄: V-A FW_E VSL<110 결정 9 / 10 / 14, B 0; VSL 단독 ④b 1099 −57.8 / +145.9 / +53.0 | §13.5 |
| RG-28 | codex 분할: 진입 커넥터 8개(10480·10482·10646·10644·10639·10681·10490·10484), Ω701 밖 진출 10479·10645, `reporting_partition.json` `3142f69c0502f6d9d12416b5b6131d57799bf8f2d17d207b4b0312e854f1dd2b`, 분할 코드 `7fc91d604214b3ea757c2e7c34f59a694a801ac21bf83c7e02fd57cde27e7fd1` | §13.2 |
| (폐기) | 좁은 설계 r2 의 RG-17(τ_A·τ_B)·RG-18 은 일반형으로 대체(GG10) | D-K9-107·114 |

---

## 16. 고정 목록 (pins) 차례

- **Declare 때**(이 판): `C1D2/PINS_C1_2_DECLARE.sha256` — 근거 문서·자료·도구·코드·선언 참조(§0 표 전부, 64자). 이 보충 파일 자신은 넣지 않습니다(`.sha256` 와 LOG 가 따로 고정).
- **고정점**: `C1D/AMENDMENT_C1_2_FIXED.md`(검토 뒤 이 보충 sha 64자 + 고정 목록 sha).
- **P0 앞(고정 A)**: `C1D/PINS_P0_C1_2.sha256` — `c1g_build.py`·`c1g_recount.py`·`c1_p0_c12.py`·`c1_probe_build_r2.py`·자체 시험과 그 출력·입력 sha 목록.
- **P0-17 뒤(고정 B)**: `C1D/PINS_P0_C1_2_B.sha256` — 증거 둘(S17·S17⁰), `c1_port_section_c1g*.json`, 패치 r2·manifest, 팔 파일 9개.
- **탐침 r2 앞**: `C1D/C1_VALUES_C1_2.json` sha → LOG; `C1D/PINS_PROBE_r2.sha256`(§9.1).
- **C1-0 앞**: 보충 C1 그대로 + `C1_U_TESTS.json` 에 `test_c1_guard.py`, 가드 자체 시험 출력(§7).
- **COMPARE_RULE_C1 고정 때**(첫 C1 런 전): 분할 도구(X9), DA·RF 사본(X10), VSL 줄 셈 규칙, 사슬·미터 줄 도구(보충 C1 그대로).
- 각 고정 목록은 고정 뒤 바이트가 바뀌면 S-C1-24·S-C1-12 입니다.

---

## 17. 비용 어림 [추론] (보충 C1 §15 의 약 103–163 h 위에)

| 단계 | 어림 | 근거 |
|---|---|---|
| 개발(가드 코드·증거 빌더·재셈 도구·P0 도구·탐침 r2 도구·자체 시험) | 1.5–2.5 일 | GG r1 §2.9·§3.7(칸 그래프·`R:` 빌더 더함) |
| P0-17 | < 15 분 | 망 파일 읽기 |
| P0-18 | 약 0.5–1 h | 상태 330 × 기록·프레임 읽기 |
| P0-14 | 약 15 분 | 설정 10 + 37회 × 약 17 s |
| P0-15 | 약 20–30 분 | 상태 106 읽기 |
| P0-16 D98 | 약 1–1.5 h | ≤ 91상태 × 2–3팔 × 약 17 s |
| 탐침 r2 결정(보충 C1 의 35 위에 더한 몫: C1G 5 + C1G⁰ 1 + S_G ≤ 28) | 약 8.5–20 h | ≤ 34결정 × 15–35 분 |
| 탐침 r2 plant 48잡(다시) | 약 2.5 h | 보충 C1 §15 미니 탐침 몫 안(첫 상태 3잡만 더) |
| 커밋 C1-G 관문 | 약 14–30 h | G-K0 전부 6–9 h + G-K4 ≤ 25결정 + G-K5a + G-D98 |
| G-D98(C1-1·C1-4·C1-G) | 약 1 h | 33상태 × 2팔 × 17 s × 3 |
| F 더함(Ω plant 잡 50 + F-D98·F-G 설정) | 약 2–3 h | |
| **합** | **약 +30–58 h 계산**, 개발 1.5–2.5 일 따로 | LOCK 기다림 빼고 |

- LOCK 은 VSL·FO 워크플로와 함께 씁니다. 기다림 시간은 넣지 않았습니다. 디스크 [추론]: PT2·관문 트리 각 1–2 GB, 출력 약 2–3 GB 더(C: 18 GB, D: 198 GB 여유 [실행 19:47]).

---

## 18. LESSONS 적용 (처음부터)

| LESSON | 이 보충에서 지키는 자리 |
|---|---|
| 튜닝·증거에 경로 문자열 없음(이름 + sha) | 가드 키(§5.10 이름 + sha), 증거 파일 경로 칸 0(P0-17 (h)), 메타는 프레임 sha 만(§5.11), 선언 참조 `c1g_guard_rule.json` 에 경로 0 |
| 긴 목록은 파일로 | 구간·칸·귀속 = 증거 파일, S_G = `c1g_states.json`, 규칙 = `c1g_guard_rule.json`, 시험 = `C1_U_TESTS.json`, 구동기 인자는 그 파일 이름 하나 |
| 임시 이름은 PID 로 유일 | 새 도구의 임시 파일·폴더 = `<앞머리>_<pid>_<time_ns>_<순번>`, 배타 생성; 판정 도구는 이름을 쪼개지 않음 |
| 판정기는 폴더 이름에서 시드를 읽지 않음 | S_G·P0-18 상태 열쇠 = (런 이름, T), 시드 = provenance `/seed`(§9.4) |
| 새 키의 메타 표지는 기록 대 재생 관문에 선언 차이로 | A_C1-M 더함·A_C1G-M 새(§10.2) |
| 승격 전 `make_config --check` | C1-4 `make_config_n31.py --c1 --check`(8키) |
| 벽시계는 중앙값으로만 판정 | 탐침 멈춤 4(C1·C1G 중앙), G-K5b(C1G 중앙) |
| 시험은 기준과 시험별로 | U 그대로 + 새 `test_c1_guard.py` 는 모두 통과 |
| 연쇄 재생: 직전 행동 경로·영수증은 닫힌 잎, 보고만 | R-b 닫힌 잎 11개 그대로, 가드 메타에 경로 0 |
| 경로 정규화는 새 트리 뿌리까지 | P0-14 (c)(PT2·`probe_r2`·`p0_c12`·`c1_g_<sha8>_null` 뿌리) |
| NC3 녹색 초는 GREEN 만 | SG2 식·사슬 줄 그대로, DA4 미터 GREEN 만(§13.4) |
| 새 정책 토큰으로 기록 상태 재생은 `load_prices` 에서 멈춤 | C1G 토큰 = T_C1; 탐침 상태는 T=900 또는 직전 NoControl(S_G), R-b 연쇄 안 토큰 같음(§9.3) |
| codex 머리 표 g9=g10 대 K3(g9 빼고 g10 남김) | 그대로(M5·RV-2 바꾸지 않음) |
| 데이터 전 고정 | 가드 규칙·S_G 규칙·D98·보고 칸을 이 문서로, 도구 sha 는 각 고정 목록으로, 결과를 본 뒤 바꾸지 않음(S-C1-24) |

---

## 19. 보충 C1 대비 바뀐 곳 (닫힌 목록; 이 밖은 그대로)

| # | 보충 C1 자리 | 바뀜 | 이 보충 자리 |
|---|---|---|---|
| 1 | 머리 "구속"·§12 S-C1-1 | 보충 C1-2 고정점도 함께 구속(S-C1-24) | 머리, §14 |
| 2 | §2.0-5·§2.1 팔·§2.1 (a) | 배포 팔 = C1G(8키), 키 ⊆ 8개, 팔 C1G·C1G⁰·C1G⁻ 더함 | §5.10, §7 |
| 3 | §2.2 [검토 RV-20] 끝 문장("셀·저장고 궤적은 바꾸지 않는다고 봅니다") | D98 로 읽음(29 커넥터가 첫 재고를 바꿀 수 있고, 차이는 D98 로 설명되어야 함) | §3, §5.13-16 |
| 4 | §2.9 정책 토큰 표 | C1G·C1G⁰ = T_C1, C1G⁻ = 키 끔 토큰 | §7 |
| 5 | §2.12 알려진 한계 | 16–21 더함 | §5.13 |
| 6 | §2.13 편집 목록 E | E23–E30 더함 | §6 |
| 7 | §3 "발사" 줄 | 스레드 정정 메모 | §4 |
| 8 | §4 P0 | P0-14–18 더함, 순서·고정 A/B·`C1_VALUES_C1_2` | §8 |
| 9 | §5 미니 탐침 | 탐침 r2(새 트리·도구·고정·출력 뿌리, D98 단계, C1G·C1G⁰·S_G, 멈춤 1–9) | §9 |
| 10 | §5.3 기대 첫 줄(Ω·H 궤적 = OFF) | H 는 그대로, Ω 는 T1/T2 | §3, §9.5-2 |
| 11 | §6.2 C1-0 가드·기록기, 커밋 표 | 토큰 sha = C1-2, 허용 A + S_G, 기록기 가드 칸, 새 커밋 C1-G, C1-4 8키, 메시지 꼴 | §7, §11 |
| 12 | §6.3 A_C1-M | 가드 경로 더함, A_C1G-M 새 | §10.2 |
| 13 | §6.4 G-K1·G-K2 (d)·G-K3·G-K4·G-K5b | §10.1 대로 바꿈, G-K2 (f)(g)(h)·G-D98·B(가드) 새 | §10.1 |
| 14 | §6.5 커밋별 관문 | §10.3 | §10.3 |
| 15 | §7 G-RR (b) | 팔 C1G, 선언 차이 더함 | §10 |
| 16 | §8 R-a·R-b | 팔 C1G, 보고 칸 더함, `/g_rr_c_b` D98 | §12.1 |
| 17 | §9.1 J 팔, §9 단계 토큰 | C1G, 토큰 sha = C1-2 | §12.2 |
| 18 | §9.2 F | F-D98·F-Ω 두 팔·F-G | §12.3 |
| 19 | §10 VerifyC1 | 다시 셈에 더함: S17·S17⁰ 바이트, 구간 수 RG-19, 토큰 RG-23, G-K2 (f)(g)(h) 값, G-D98 표, S_G 목록 | §19 아래 줄 |
| 20 | §11.1–§11.3 폐루프 비교 꼴 | 팔 C1G, Ω701 주, 도시도로 codex 분할, FW_E 기준 줄·DA1–DA4·VSL 줄·가드 칸, 점검 X9·X10 | §13 |
| 21 | §12 STOP | S-C1-3·5·6·7·8·9·10 넓힘·읽기, S-C1-18–24 새 | §14 |
| 22 | §13 퇴행 숫자 | RG-17–28 더함 | §15 |
| 23 | §14 고정 목록·§15 비용 | §16·§17 더함 | §16, §17 |

- §10(VerifyC1) 더함: 판정기·하네스를 import 하지 않는 재계산 도구가 위 19번 줄의 값을 다시 셈. 다르면 STOP(S-C1-16).
- **바꾸지 않은 것**: 사용자 결정 D-K9-91–97 의 뜻, `c1_port` 7키 값·repr(보충 C1 §2.1, 정규 JSON `c2f3cf19…`), 보충 C1 선언 참조 8파일 바이트, 문턱(G-K5a 1.0158, G-K5b 1,500 s, SG2 100 s), SG2 식, 상태 목록 `c1_states.json`, S-C1-7 의 "조임 고름" 뜻, RV-1·RV-2, VSL 정책(V-A 그대로, D-K9-101), K9-3 보류, 폐루프는 발사 전 다시 물음(S-C1-13).

---

## 20. 이 문서를 쓰며 한 일·하지 않은 일·파일

- **한 일** [실행, 모두 읽기 전용 + 선언 도구 하나, 19:47–20:10 KST]: 결정 기록·보충 C1 고정판·설계 r1·r0·r2·검토·FACTS·재고·자료·P0_PROBE r2·탐침 결과·FWE_DECOMP r2·VERIFY_FWE·VSL 보고 읽기와 sha256; GWT8 `git rev-parse`·`git status`·`git show c20aff1d:`(RS·SD·SEQ 앵커 줄), PT 의 RS·SD·C1P 줄, CX USG 전체·CX SD:428-442·:848-866·:1266-1275·CX PRB:866-910 읽기; V-A·R-obs 상태 파일 하나씩의 `/obs150/frames` 키 꼴(값 읽지 않음); `occ.json`·`segments.json`·`inventory.json` 머리 꼴; HO 분할 파일 sha 와 분할 코드 :40-70. 선언 도구 `C1D/work/c12_declare.py`(실행 전 LOG 고정) → `C1D2/c1g_guard_rule.json`. 이 문서를 만든 조립 도구 `C1D/work/c12_assemble.py`(인용 상자 셋을 원문 바이트에서 넣음; sha 는 LOG).
- **하지 않은 일**: 코드 변경·브랜치·커밋·푸시·동결 0; P0-14–18·탐침·관문·재생·plant 잡·FZP 스캔 0; VISSIM·COM·러너 0; 금지 시험 0; kill 0; LOCK 0(무거운 일 없음; `heavy.lock` 은 다른 워크플로 것, 건드리지 않음); 봉인 시드 37·59·61·67 자료 0, codex 64cf-s59/s61/s67 숫자 0, v3c3-s47 값 0; 동결본·런 폴더·HO·CX·FRZ_B1·Y: 쓰기 0. 보충 C1 고정판·설계 문서 바이트 그대로.
- **파일**: 이 문서 `SP/K8_PREDECLARATION_AMENDMENT_C1_2.md`(sha256 은 `.sha256`·LOG), `C1D2/c1g_guard_rule.json`, `C1D2/PINS_C1_2_DECLARE.sha256`, 선언·조립 도구 `C1D/work/c12_declare.py`·`c12_assemble.py`·`c12_template.md`, 보고 사본 RC1.

## 변경 기록

- Declare 판 (2026-10-27 KST): 첫 판. D-K9-98·99·103(Q-V6)·104·110·111·114 + GG0–GG13 + G6–G12, RV-1·RV-2 그대로.
