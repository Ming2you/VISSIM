# K8 보충 32 (Declare 판) — K9-2 묶음 1: V-B의 VB-I1을 사슬 첫 결정 4개로만 판정하고 사슬 이어받는 OFF 10결정은 닫힌 잎을 뺀 보고만(D-K9-62), 사슬 결정마다 측정 훅으로 `k92_record.json`(D-K9-63), 훅 영향 0 시험, V-B 구동기·재계산기 요건, 보고서 자리, 보충 24 :540 인용 고침, 검증 공개 수용(D-K9-64) (2026-10-22)

- **상태: Declare 판.** 반박 검토(ReviewDeclare)가 이 판을 읽고 고정판과 고정점 파일 `KB/AMENDMENT32_FIXED.md`를 만듭니다. 고정점에 적힌 sha256과 다른 보충 32로는 V-B의 어떤 단계(사전 점검, 트리, 팔, 훅 영향 0 시험, 사슬 계산)도 하지 않습니다.
- 이 파일의 sha256을 `SP/K8_PREDECLARATION_AMENDMENT_32.md.sha256`에 적습니다.
- **쓸 때 상태** [실행 2026-10-22 09:44–10:15 KST]: GWT8 head = K9-2-5 `e27ceac86c01c1dcfd5b2bb2d9b522be3dc33c0d`(브랜치 `claude/k92-b1-20261016`, `b9734abe..HEAD` = 커밋 6개), K8 브랜치 `claude/k8-sc1001eb-defects-20261004` = `b9734abe1c83f95c9cec5fca5e42b7b18cd45991`, `git status --porcelain` 0줄, 원격 k92 참조 0, 푸시 0. **V-B 데이터 0개**: `OK2/vb*`·`TK/vb*` 없음, 사슬 계산·결정 재생·훅 영향 0 시험 실행 0. python·VISSIM 프로세스 0(이 단계 도구가 끝난 뒤). C: 40 GB, D: 388 GB 여유.
- **구속**: 보충 1–31의 규칙·식·값·문턱·관문·표본은 §9 표에 적은 자리만 빼고 **그대로** 구속합니다.
- **알리는 말(먼저 읽을 것)**:
  1. **D-K9-62는 사용자가 권장안이 아닌 (나)를 고른 것입니다.** 권장안 (가)는 "닫힌 잎 목록에 조건을 단 좁은 허용"이었습니다. (나)에서는 사슬을 이어받는 OFF 10결정의 비교가 **판정에서 빠지고 보고만** 됩니다. 그래서 둘째 결정부터의 사슬 기구(직전 행동을 넘기는 일)가 옳은지는 통과·실패로 묶이지 않습니다. 대신 닫힌 목록 밖의 차이는 표와 쉬운 문장으로 눈에 띄게 적습니다(§2.3).
  2. **새 측정 훅이 V-B의 모든 결정 프로세스 안에서 돕니다(D-K9-63).** 훅은 읽기만 하는 도구이고, 커밋 코드·동결본·V-B 트리를 고치지 않습니다. 그래도 결정 계산과 같은 프로세스에서 돌기 때문에, V-B 데이터 전에 V-B 밖 상태 둘에서 "훅을 켜도 결정 출력이 같다"를 먼저 보입니다(§3.5). 같지 않으면 STOP입니다.
  3. **VB-M5·M6·M8의 키 끔 쪽은 훅을 단 OFF 사슬 14결정에서만 나옵니다.** 그 밖의 T는 "없음"입니다. 추가 재생은 하지 않습니다(메인 세션 처리, §1).
  4. **새 무결성 점검 VB-I7(훅 무결성) 하나를 더합니다(§2.5).** D-K9-62~64 글에는 없는 조건이고 STOP을 늘리는 쪽입니다(공개 P6).
  5. 보고서 자리(정본 + 같은 바이트 사본)와 보충 24 :540의 줄 번호 인용 고침은 메인 세션이 이 보충에 넣으라고 정한 것입니다(§5, §6).
  6. **검증 공개 수용(D-K9-64)**: 검증 3차와 VerifyVB의 공개 사항을 기록으로 받아들입니다(§7 P4).
- 표시: [실행] 이번에 돌려서 확인, [읽음] 문서·코드에서 확인, [추론] 시험하지 않은 판단, [계산] 산술.
- 이 보충은 판정 말을 쓰지 않습니다. 결과는 PASS / FAIL / 보류 / INCOMPLETE / STOP과 숫자로만 적습니다. V-B는 보고만이고, 무결성 점검(VB-I)만 통과·실패가 있습니다. 교통 성능 판정이 아닙니다.

## 줄임말 (처음 한 번만 풉니다)

- SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`. KB = `SP/k92/bundle1`. KI = `KB/impl`(구현 도우미, 바꾸지 않음). **KV** = `KB/k92_vb`(V-B 단계 폴더: 구동기·재계산기·보고서).
- **AD32** = `KB/a32decl` — 이 보충의 새 도구·확인 출력 폴더(§13). **HOOKDIR** = `AD32/vbhook`(측정 훅 파일 하나만 든 폴더).
- TK = `D:/VISSIM-merge/k8_gate_trees/k92b1`. **VBT** = `TK/vb_e27ceac8`(V-B 트리 = `git archive` K9-2-5 + CR 고침(C); 아직 없음).
- OK2 = `D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1`. **VBR** = `OK2/vb`(V-B 출력 뿌리, 아직 없음).
- RR = `D:/VISSIM_runs/20261004_sdmpc31_k8`(J1 기록 런, 읽기만). FRZ_K8 = `D:/VISSIM-merge/frozen/sdmpc31_74cd495f_202610131824`, FRZ_K8b = `D:/VISSIM-merge/frozen/sdmpc31_b9734abe_202610141821`(읽기만). GWT8 = `D:/VISSIM-merge/sim3-n31-k8`.
- ADP = `evaluation/controllers/vissim_stackelberg_adapter.py`(어댑터, 결정 하나를 계산하는 프로그램). **REC** = 커밋 K9-2-0 기록기 `diagnostics/sdmpc_n31_20260924/k8_gates/sa/k92_record.py`(블롭 `aebc6f0e`, K9-2-0 `1868b37c`에서 K9-2-5까지 그대로, 바이트 sha256 `1d1dfa36efbfa68e6ccc19cbeeb53f241437b1c5145e06fb843a9564661d4f90`). **KC** = K9-2-5 비교기 `…/k8_gates/sa/k92_compare.py`(블롭 `2b2b5523`, sha256 `3e2da987ff9e7b54ba2f51ad1b73bfdaf55f868bd6dedbf7937cf1f22fa4caba`).
- HARD = 보충 21 §6.2의 "딱 같아야 하는 잎" 묶음 H1–H5. N = 비교 전 경로 정규화(보충 21 §6.1, 보충 27·29로 고침). **결과 넷** = PASS / FAIL / 보류(HOLD) / INCOMPLETE(보충 21 §6.4).
- **사슬 첫 결정** = 직전 행동이 RR 기록 파일 그대로인 결정(VB-31·VB-43·VB-41의 T=3,000, VB-41w의 T=1). **사슬 이어받는 결정** = 직전 행동이 같은 사슬의 앞 결정 출력인 결정.
- 결정 꼴: **NN** = 무제어 ← 무제어, **SN** = 첫 SDMPC ← 무제어(T=900), **SS** = SDMPC ← SDMPC.
- 팔: **OFF** = 그 런의 튜닝 그대로(키 없음), **B1** = W + 씨앗 Hb-1 묶음(보충 24 §2). 튜닝 파일: CFG `d0f9ef39…`(VB-31 바탕), SAF-K91 `5f0d0e40…`(VB-43·VB-41·VB-41w 바탕), **CFG-B1** = 커밋 `config_n31_v2_k92b1.json` `c8e3ee2c99b66c255b2279f0aa18eaafc18d4c7689e59e260109fac3b7d71866`, **SAF-B1** = `sa_arms.py --k92b1` 출력 `config_n31_v2_stopline_observed_full_k91_k92b1.json` `65cac7ea0b33d8f0b5c8efc458307578bcae7a2e34d1d097ce448a18a65ada28`(판정 단계 `OK2/k92t/f_b1`·`jb`의 같은 이름 파일과 같은 값 [실행 sha]).
- **ZI** = 훅 영향 0 시험(zero impact, §3.5). **후보** = 훅이 `omega_costs` 호출 하나에서 만든 기록 한 벌(§3.3).
- 시드는 망 접두어를 붙입니다(v3c3-s31 등). 봉인 시드 37/59/61/67은 열지 않습니다. codex 64cf-s59·s61·s67 숫자는 쓰지 않습니다. V-B는 v3c3-s47을 쓰지 않습니다.

---

## 0. 근거 문서 [실행: sha256, 2026-10-22 09:44–10:15 KST]

| 문서 | sha256 |
|---|---|
| 결정 기록 `SP/K9_1_J1_NOTES_20261013.md`(204줄; D-K9-62~64 :195-204) | `402eaf59aa738bef1dcb27f41d51eba873a8cb6abdbfde7707dfc6b146cfbd3b` |
| V-B 사전 점검 STOP 보고 `KV/VB_PRECHECK_STOP.md` r2 / r1 | `b96637d9bc35ecf5155817058f53c6421157b24f006ae65ae9bac788a1ad9e86` / `e9a0975869def9892b5f3f46b74c467e8856a9e6f6d8fa0fd03ad918bb5113b6` |
| VerifyVB 독립 재계산 `KV/verify/out/vvb_a_01.json` / 판정기 탐침 `vvb_b_01.json` / 도구 목록 `KV/verify/vvb_pins.sha256` | `618b9592e7753147cbc3cf139d4140cc1a099bc636acf2e151f8c8aeb8323741` / `e0d5537b29de99aadfb3ea6715a7b1d65b91601366cf9b7aa5b89dc08df2700c` / `1415cc7f49a3b3836394d2a3fdd0839e86add2283c4a507152b982a319c8de49` |
| dev 탐침 분류 `KV/dev/classify_out.json` | `eda96865db22fb67165c5fa4a3569954962934405e9e17af389eeba78e9c1ea6` |
| 보충 24 / 25 / 26 / 27 고정판 | `d46db6dc3959b19525f0fce77ead5432682e3de0ef8060cdc3da09661559aadc` / `4fd7b599fe0f6131143e911dd3ab2be264a175e3f90b185bade9482d60b9ff8e` / `8f8356168a299c07960d86ef12aa9f7af6f2f040af08ba75e5233a5819edba37` / `4ce8b27a2ebf08aa0e8ac3f647b4e4336a98f7be7ec8d6f006a0fd1d12005a13` |
| 보충 28 / 29 / 30 / 31 고정판 | `9881eb40c1129af0cdff48026dc8656b4235d43f0eb80566e4be9b66d9ac345e` / `4bd6dc8de8b0a4a4ab0b8703c07d7a73d244c4a622b81585f06dc69d6d83599d` / `ba556227a6356b1733bfa8125b334cfef180c1eed97e8d69ae4ba53a3106a56a` / `8541ccb7fa6c951b4affcca67d57e25be09b061c3ae3dd006d050c9c6413e304` |
| 고정점 24 / 25 / 26 / 27 | `fbc3d59fe2e47fec00d87262d624aa9a163ed02e113609b06173841397df101a` / `d1338fbc40a2efaf6997667f59e7bd709951e1fd3f2b1a8a0a0881794c3d24ed` / `6edc55acd5aa0976701456d956e33f33c52ae0853535f6a4d8cb8bf26a354581` / `394ab15fdea0d945a3b766c208e692ee7e1086fca3c178f6b423079d71fedcdb` |
| 고정점 28 / 29 / 30 / 31 | `14451cf4d46c5c0095bc896134112148ba5700ee70b2ed78b8ee38d0e62e20e5` / `3ba1d0bdaab8a0189f903d10fc1024baed770080542cbd841f79d3a56df58e43` / `ad3fafadd59985b3b71f33d5523ceb2324aa8267395d7280039228669cb83e9c` / `605ccbd2cb392ac2ed0a6da1d27c20e93aa68fcac50ec6d99c4393236f98a053` |
| K92_GATES_PASS 기록: 적용 A31 `KB/GATES_K92B1_A31.md` / 독립 검증 A31 `KB/VERIFY_GATES_K92B1_r3.md` / 그 결과 `KB/vgates4/out/vg4_result.json` | `e2b301837feb35d652d0db088d634e07449676abd01cb0e8b2dfef6eff232885` / `6fb66ac5b8de8bbd00df420bc3b1bf5364e5f95148574dd2834204e3df3ac189` / `0b7654eca9e1165fad42ebe59b28bde91598d0b183f0cf694a21ba09a398b603` |
| `KB/GATES_K92B1.md`(§9 덧붙임 판) / `KB/a31_pins.sha256`(133줄; 127줄만 설계된 바꿈) | `449b361e96d047156e63f73bcdae905ec61408b9a5f9be047629092d3ab0a792` / `bf1ca001e8c8a4215512582871ddf439971aff04887267a0b797b3496ddc6d4e` |
| 기대 하한 키 이름 `KB/k92_probe_a25/K92_VALUES.json` `/p0_2/f_expected_floor_keys` | `296c659562e45528606599aa4df99535faa694a86533ffca6bb2fbcde7db975a` |
| 몫 가르기 훅 `SP/k92/attrib/hook/sitecustomize.py` / 방법 `SP/k92/attrib/METHOD.md`(선례) | `6ad45fd421c03f08716d71fdcdaf59491c4c1b6e5f238a9f43d4d7dd92b0f46b` / `ebd5643fbf0066b755be579f71a0f1f81d8a46a6877654147daacfa164c30104` |
| KI 도우미 `k92lib.py` / `cglib.py` / `launch.ps1` / `k92snap.py` | `ae5de0ccd90d688c0442eac2aeb35fec0aabd2abce4ba3ff75a637927fb998d9` / `be5a0c95ad7bc86da55f6cf65b3804447ebce75cf4e829f6609e86d2a292b048` / `bf7a81322086625d68b9df0961f9b00753fcf6ae499fa3aca5cad49b5d76ffff` / `0dbd7d2c75f982d867eff46f27b1c2d8fbf34301d39952bdc87ebd7a0c8beeff` |
| 준비(prepare) 도구 `SP/j1/fix/gates/gprep.py` / `gcommon.py` | `0482a53868fd3ee644724dab2dcb6af2c56d749708ccec5242f6b3549ae26f22` / `556a6511c5b17c5fc6889151f26cbfd57ffddd4b61d1fc28ec6055e4786566e9` |
| GWT8 `k92_replay.py` / `sa_arms.py` / `k92_a27.py` / `k92_common.py` | `822dd78ffde70e07baebf83e948d72ed3f82ab71107920b02a05ee8783a1b965` / `578a8707dff89b2020124eca2928121bae075c81d41d3a1bfbe30ea8a25299b1` / `d4ab3f3d4e91492e02f1b7c30807ad34744c3e7590cf890bcc1275c79baa00f5` / `cb2a0335fefc94d7eca9be0cd0a6b5d870a35a15a21266b397b33e1bd181c012` |
| GWT8 `evaluation/controllers/sdmpc.py`(블롭 `d21fdd49`) / `scripts/run_real_world_stackelberg_controller.vbs`(블롭 `00f7ea11`) / `tools/make_replay_state_v2.py`(= FRZ_K8b 사본) | `8f91298ade473bb493086b69f55e3f0bfb9dfe82d0abc8789f714ffc1e736061` / `bffb59f88440ec819551461bcca0ec103c52433e7cd6209d94bb7f396765ccbf` / `4adf41cfa7569047d87774bb648b353780fbb7ffc9b916a9c8f726e1d1de0714` |
| RR 러너 영수증(§4.5 바이트 대조용): VB-31·VB-43·VB-41 `action_003000.json.applied`, VB-41w `action_000900.json.applied`, v3c3-s41 `action_002850.json.applied` | `602f2a85…` / `61983196…` / `f72c349e…` / `574dfdc1…` / `561652c6…`(64자는 기대 고정 목록 `AD32/a32_pins.expected.sha256` 46–50줄) |
| 작업 기록 `KB/LOG.md`(이 단계 첫 항목 덧붙임 전, 244,072 B) | `0fc4b2ae6aad47fb63a2df34a6694ae8f427520a37d6b7bdfa607279165d1b2c` |
| 읽기 전용 뿌리 스냅숏 `OK2/snap/s37b_a32decl.json`(이 단계, s02 대비 SAME) | `765c287dacf5ab46f26df6f0031ab37b50b4d46495e2bffbe6a84faefa32b5ab` |

### 0.1 이 판을 쓰며 한 일

- **확인** [실행]: 보충 24–31 sha = 각 `.sha256` = 각 고정점 안의 64자(1회씩). 결정 기록 = 작업 지시 값 `402eaf59…`. GWT8·K8 상태(머리글 "쓸 때 상태"). `OK2/vb*`·`TK/vb*` 없음.
- **읽기**: 결정 기록 D-K9-49~64, V-B 사전 점검 보고 r2 전문, 보충 24 §4.2·§4.3·§14, 보충 27 §2.2·§6, 보충 29 §6, 보충 31 전문, VerifyVB 출력 `vvb_a_01.json`(경로·규칙 이름·계수만 든 파일), dev 탐침 `classify_out.json`, 몫 가르기 `METHOD.md` §5와 훅 소스; GWT8 코드: `k92_record.py` 전문, `sa_worker.py`의 기록기 호출 자리(:75, :484-541, :719-776, :1093, :1143-1148), `k92_replay.py` 전문, `k92_compare.py` 전문, `sdmpc.py:261-296`·`:513-533`, ADP의 직전 행동 읽기 자리(:1939-2060, :4626-4650, :11084-11134, :12925-12975, :13051-13100, :13615-13618), `network_pressure.py:81-97`, `lane_plant_observation.py:290-313`, `obs150_contract.py:1531-1544`, `sdmpc_tangent_runtime.py:60-175`, `sdmpc_dual.py:172-196`, VBS `:1270-1290`, `make_replay_state_v2.py:1-140`, `sa_arms.py:1-40`·`:130-200`; KI `k92lib.py`·`cglib.py`(트리·재생·CR 고침), `k92t.py:15-40`·`:239-265`.
- **읽은 기록 자료(V-B 데이터 아님, 공개 P5)**: RR 영수증 다섯 바이트와 그 CSV 크기; RR v3c3-s41 T=1·150·750·900·1,050·3,000·3,150과 v3c3-s43 T=750·1,050의 `decision_budget.json`의 `wall_sec`(비용 어림); RR v3c3-s41·s43 결정 폴더의 파일 이름·크기 목록(T=1·150·750·900·2,850·3,000, s43 600–1,050); 몫 가르기 `DA/hook/S1_A0h`의 파일 목록과 E2 기록(줄 수·키·호출자·행 수·t0·`transfers` 수·`is_ad`·첫 기록의 행동 녹색); OUTH `gh3`·`gb9` 준비 기록의 `T`·`source_decisions`·`previous_sec`; 세 튜닝(CFG·SAF-K91·CFG-B1)의 `phase_price` 절.
- **쓰기**: AD32 전부(새 도구, 닫힌 잎 목록, 확인 도구와 출력, 기대 고정 목록, 합성 트리 `AD32/dry/syn`); `OK2/snap/s37b_a32decl.json`·`OK2/logs/a32decl_snap.txt`(WMI 발사 표준 출력, 개수만); `KI/wmi_launch_lines.txt`(launch.ps1이 한 줄 덧붙임); 이 글과 `.sha256`; `KB/LOG.md` 덧붙임. RR·동결본·GWT8·저장소 `.git`·K8 브랜치·OUTK·봉인 뿌리·VBT·VBR 쓰기 0.
- **확인 실행**: `AD32/make_closed32.py`(작은 JSON 두 개 읽기) 한 번과 `AD32/dry_a32.py all`(합성 입력, 자식 python은 합성 프로그램뿐) — 모두 BelowNormal, `PYTHONHASHSEED=0`, `python -B`. 스냅숏 한 번은 `KI/launch.ps1 -Tag a32decl_snap`(WMI 분리, 51.4 s).
- **개발 중 공개**: `dry_a32.py` 첫 실행은 망가뜨림 M1(BOM 없는 영수증)에서 내 확인 함수가 `UnicodeError`로 끝났습니다(어댑터의 읽기 방식이면 예외 = 받아들이지 않음). 확인 함수가 읽기 오류를 "거짓"으로 세도록 고쳤습니다. 둘째 실행에서 망가뜨림 M8(훅이 `collect`에 T0 = 0을 넘김)이 잡히지 않았습니다. 기록기 `collect()`는 T0를 쓰지 않으므로(REC:74-118) 의미 없는 망가뜨림이었습니다. M8을 `write()`의 T0를 0으로 바꾸는 꼴로 고쳤고, 셋째 실행에서 8/8 잡혔습니다. 확인 도구 안의 비교기 sha 상수를 처음에 잘못 적었다가(앞 8자만 맞음) 고쳤습니다(실행 전, 그 상수가 틀리면 도구가 멈추게 되어 있음). 측정 훅·고르기·도움 함수의 바이트는 첫 확인 실행 뒤 바꾸지 않았습니다. 고정 목록에 든 확인 출력은 모두 마지막 실행 출력입니다.
- **하지 않은 일**: VISSIM·COM·러너·동결·결정 재생·plant 잡·어댑터 실행 0. VBT·VBR 만들기 0. 사슬 계산·훅 영향 0 시험 0. 커밋·브랜치·푸시 0. 금지 시험 0. 봉인 뿌리·봉인 시드·v3c3-s47 자료 열람 0.

---

## 1. 사용자 결정 원문 [읽음 결정 기록 :195-204, 표 행 그대로]

근거 줄(:196): `k92/bundle1/GATES_K92B1_A31.md`(보충 31 적용: scan31 134/45/0 PASS, unit31 공통 97·다름 0 PASS), `k92/bundle1/VERIFY_GATES_K92B1_r3.md`(독립 검증 A31 PASS, G-K4 plant 4행 PASS 숫자 잎 10,213 다름 0) → K92_GATES_PASS. V-B 사전 점검 STOP `k92/bundle1/k92_vb/VB_PRECHECK_STOP.md` r2(b96637d9…, r1 e9a09758…): V-B-D1 = 사슬 둘째 결정부터 직전 행동 파일의 경로·영수증 sha·직전 JSON sha 잎이 RR 기록과 반드시 달라(HARD 1–3개, 미분류 2–13개) OFF 14결정 중 사슬 이어받는 10결정이 VB-I1 FAIL로 정해짐(판정기 탐침 ctrl 10/10 PASS, pathonly·chain 10/10 FAIL); V-B-D2 = VB-M5·M6·M8·VB-I5 의 k92_record.json 은 하네스 plant 잡만 만들고 결정 재생은 안 만듦.

| # | 질문 | 사용자 답 | 효과 |
|---|---|---|---|
| D-K9-62 | VB-I1 을 어떻게 고칠까요? | **사슬 결정은 보고만** (권장안 아님; 권장은 닫힌 잎 좁은 허용) | 보충 32: VB-I1 통과·실패는 사슬 첫 결정 4개(VB-31·43·41 T=3,000, VB-41w T=1)로만, G-K0 허용 그대로 결과 넷. 사슬 이어받는 OFF 10결정은 VB_PRECHECK_STOP §2.2 닫힌 잎 목록을 뺀 비교를 보고만(판정 없음, 목록 밖 차이는 눈에 띄게 보고). VB-I2–I6 은 그대로 모든 사슬 결정에 |
| D-K9-63 | k92_record 는? | **측정 훅으로 기록 (Recommended)** | 사슬 결정마다 훅이 커밋 K9-2-0 기록기(k92_record.collect)를 부름(몫 가르기 훅 방식). 훅이 결정 출력 바이트를 바꾸지 않음을 V-B 데이터 전에 V-B 밖 기존 상태로 먼저 보이고(훅 켬·끔 대조, 훅 sha 고정), 훅 비용 보고 |
| D-K9-64 | 검증 공개 사항 | **수용 (Recommended)** | 검증 3차(고정 전 작업 지시 요약·jb_unit meta·출력 꼴 코드 열람, 멈춘 find 하나)·VerifyVB(vvb_b 가 하네스 판정기 import, 독립 vvb_a 는 import 0·같은 결과)를 기록으로 수용 |

메인 세션 처리(:204, 질문 없이, 관례): 보고서 정본 = `KB/k92_vb/K92_VB_REPORT.md`(보충 31 §4.4), 같은 바이트 사본 `KB/VB_REPORT.md`. 보충 24 :540 `sdmpc.py:461-470` → `:513-533`(load_prices 영수증 규칙) 인용 정정은 보충 32 에. VB-M5·M6·M8 의 키 끔 쪽은 훅을 단 OFF 사슬 14결정에서만 내고 그 밖 T 는 '없음'(추가 재생 없음, 공개).

- 작업 지시(메인 세션) 글이 D-K9-63을 더 자세히 적었습니다: "어떤 V-B 데이터보다 먼저 훅을 고정하고(sha를 LOG에), 55개 V-B 결정 **밖**의 기존 상태(예: G-K0 상태나 다른 기록 결정)에서 훅 켬·끔 출력이 같음을 보임 — 바이트 같음, 또는 G-K0 비교로 같고 벽시계 잎만 다름 가운데 무엇을 쓸지 실행 전에 선언 — 훅의 벽시계 비용을 보고; 훅이 출력을 바꾸면 STOP". 이 보충은 이 글을 따릅니다(§3.5).

---

## 2. VB-I1 (D-K9-62)

### 2.1 판정하는 결정 — 사슬 첫 결정 4개

| 사슬 | 런(RR, 읽기만) | T | 직전 행동 | 결정 꼴 | 옛 뿌리(old_root) |
|---|---|---|---|---|---|
| VB-31 | `sdmpc31_v3c3_k8j1r_s31` | 3,000 | RR `action_002850.json`(그 런 결정 폴더) | SDMPC | FRZ_K8b |
| VB-43 | `sdmpc31_v3c3_k8j1_s43` | 3,000 | RR `action_002850.json` | SDMPC | FRZ_K8 |
| VB-41 | `sdmpc31_v3c3_k8j1_s41` | 3,000 | RR `action_002850.json` | SDMPC | FRZ_K8 |
| VB-41w | `sdmpc31_v3c3_k8j1_s41` | 1 | 없음 | 무제어 | FRZ_K8 |

- **비교**: `KC.compare(<RR 결정 폴더>, VBR/chain/<사슬>_off/dec, T, VBT, keyed=None, old_root=<옛 뿌리>)` — 보충 29 §6.2-2 그대로입니다. 비교 규칙(N, HARD H1–H5, F1–F3·L_T, D1–D5, 허용 V ∪ R3 ∪ F − D, A_K92)도 그대로입니다. 허용은 G-K0와 같습니다(무제어 결정 D-a, SDMPC 결정 D-d; 새 허용 0).
- **통과**: 결과 넷의 **PASS**(HARD 같음 + 미분류 0). 보류·FAIL·INCOMPLETE → VB_INCOMPLETE → STOP(S-K15, S-K55).
- **SDMPC 결정 셋의 D5 RS 뿌리 점검(보충 29 §6.2-2 "먼저 봄"의 꼴)**: 그 비교 보고의 `k92_checks`에 규칙 `A_K92` 줄이 하나 이상 있고, 그 줄이 모두 `ok`·`new_is_root_rs`·`old_is_root_rs` 참이어야 합니다. 아니면 VB_INCOMPLETE → STOP. 까닭: VBT RS(`70cca680…`)와 동결본 RS(`8a5aec79…`)가 다르므로 A_K92 잎이 반드시 나타납니다 [추론, 보충 29 §6.2-2와 같은 예상]. 나타나지 않으면 옛 뿌리가 그 동결본이 아니라는 뜻이므로 STOP을 늘리는 쪽으로 둡니다(공개 P7).
- **CR 짝**: 첫 사슬 계산 전 `cr_pair(FRZ_K8b, VBT)`·`cr_pair(FRZ_K8, VBT)` 참(보충 29 §6.2-1 그대로, §4.2 V1).
- 이 4결정도 **훅을 켜고** 돕니다(D-K9-63 "사슬 결정마다"). 그래서 이 4결정의 PASS는 "훅을 켠 결정 출력 = RR 기록"의 증거도 됩니다(§3.5의 ZI와 별개, 보고에 적음).

### 2.2 보고만 하는 결정 — 사슬 이어받는 OFF 10결정과 닫힌 잎 목록

| 사슬 | T (직전 T) | 결정 꼴 |
|---|---|---|
| VB-31 | 3,150 (3,000) | SS |
| VB-43 | 3,150 (3,000) | SS |
| VB-41 | 3,150 (3,000) | SS |
| VB-41w | 150 (1), 300 (150), 450 (300), 600 (450), 750 (600) | NN |
| VB-41w | 900 (750) | SN |
| VB-41w | 1,050 (900) | SS |

- **비교**: §2.1과 같은 `KC.compare(…)` 호출(같은 인자 규칙)을 그대로 돌립니다. 그 보고에서 아래 **닫힌 잎 목록**의 경로를 뺀 나머지를 "목록 밖"으로 적습니다. 함수 = `AD32/vb_lib32.py` `reportonly(rep, 결정 꼴, 닫힌 목록)`(§2.3). **판정 없음, STOP 없음**(D-K9-62). 결과 넷 값은 "참고(판정 아님)"로만 적습니다.
- **닫힌 잎 목록**(VB_PRECHECK_STOP r2 §2.2를 경로 단위로 옮긴 것). 기계 파일 = `AD32/vb_closed_leaves.json`(sha256 `b800be45ae3e4e5030ed31ecd221e6288d52c2a287bdeaa5efee243e3cc2f426`, `AD32/make_closed32.py`가 `vvb_a_01.json`(열 결정 전부)에서 만들고 `classify_out.json`(v3c3-s41 다섯 결정)과 같음을 확인) [실행 `dry_a32_closed.json`: 다시 만들어도 바이트 같음]. 경로는 KC의 일반화 꼴(소문자, `[*]`)입니다. "직전 파일"은 그 잎 값이 가리키는 직전 행동 파일, "어떻게"는 경로 글자(path)인지 바이트 sha(sha)인지입니다. "기록 개수"는 RR 기록에서 그 일반화 경로가 나온 잎 수입니다.

**NN (무제어 ← 무제어) — 3경로, 잎 3개, HARD 1**

| # | 경로 | HARD | 직전 파일 | 어떻게 | 기록 개수 |
|---|---|---|---|---|---|
| N1 | `/prediction_error/source_action_json` | H5 | `.json` | path | 1 |
| N2 | `/metadata/n31_binding/vsl_cohort_initialization/sha256` | – (D2b) | `.json` | sha | 1 |
| N3 | `/metadata/n31_binding/vsl_cohort_initialization/source` | – | `.json` | path | 1 |

**SN (첫 SDMPC ← 무제어, VB-41w T=900) — 9경로, 잎 12개, HARD 1**

| # | 경로 | HARD | 직전 파일 | 어떻게 | 기록 개수 |
|---|---|---|---|---|---|
| F1 | `/prediction_error/source_action_json` | H5 | `.json` | path | 1 |
| F2 | `/diagnostics/physical_ramp_recorded_csv/path` | – | `.csv` | path | 1 |
| F3 | `/diagnostics/sdmpc_prediction_sequence/future[*]/diagnostics/physical_ramp_recorded_csv/path` | – | `.csv` | path | 2 |
| F4 | `/metadata/joint_leader_selection/surrogate_query/warm_budget_binding/source_action/diagnostics/physical_ramp_recorded_csv/path` | – | `.csv` | path | 1 |
| F5 | `/metadata/joint_leader_selection/surrogate_query/warm_budget_binding/source_action/diagnostics/sdmpc_prediction_sequence/future[*]/diagnostics/physical_ramp_recorded_csv/path` | – | `.csv` | path | 2 |
| F6 | `/metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/warm_budget_binding/source_action/diagnostics/physical_ramp_recorded_csv/path` | – | `.csv` | path | 1 |
| F7 | `/metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/warm_budget_binding/source_action/diagnostics/sdmpc_prediction_sequence/future[*]/diagnostics/physical_ramp_recorded_csv/path` | – | `.csv` | path | 2 |
| F8 | `/metadata/n31_binding/vsl_cohort_initialization/sha256` | – (D2b) | `.json` | sha | 1 |
| F9 | `/metadata/n31_binding/vsl_cohort_initialization/source` | – | `.json` | path | 1 |

**SS (SDMPC ← SDMPC) — 13경로, 잎 16개, HARD 3**

| # | 경로 | HARD | 직전 파일 | 어떻게 | 기록 개수 |
|---|---|---|---|---|---|
| S1 | `/metadata/sdmpc_state/previous_application/receipt_sha256` | H4 | `.json.applied` | sha | 1 |
| S2 | `/metadata/sdmpc_state/previous_application/source` | H4 | `.json.applied` | path | 1 |
| S3 | `/prediction_error/source_action_json` | H5 | `.json` | path | 1 |
| S4–S9 | F2–F7과 같은 여섯 경로(`physical_ramp_recorded_csv/path` 본체·예측 순서·웜 예산 사본) | – | `.csv` | path | 1·2·1·2·1·2 |
| S10 | `/metadata/joint_leader_selection/price_state/previous_application/receipt_sha256` | – (D2) | `.json.applied` | sha | 1 |
| S11 | `/metadata/joint_leader_selection/price_state/previous_application/source` | – | `.json.applied` | path | 1 |
| S12 | `/metadata/n31_binding/vsl_cohort_initialization/sha256` | – (D2b) | `.json` | sha | 1 |
| S13 | `/metadata/n31_binding/vsl_cohort_initialization/source` | – | `.json` | path | 1 |

- **목록에 넣지 않는 것**: CSV sha 잎 여섯(SN·SS의 `…/physical_ramp_recorded_csv/sha256` 본체·예측 순서·웜 예산 사본; D2). 사슬 앞 결정의 CSV가 기록 CSV와 바이트 같으면 같은 잎입니다. 다르면 "목록 밖 미분류(D2)"로 눈에 띄게 적힙니다(VB_PRECHECK_STOP §2.2 첫 점). 기계 파일의 `csv_sha_equal_if_same`에 있습니다.
- **목록의 뜻(닫힘)**: 목록은 위 표의 경로만입니다. 같은 결정 꼴의 다른 경로가 다르면 그것은 "목록 밖"입니다. 결정 꼴은 기계 파일의 `decisions`(위 표 10줄)로만 정합니다. 사슬 첫 결정 4개는 목록이 없습니다(`decision_type` = 없음, §2.1 판정).

### 2.3 보고 전용 표가 보이는 것 (`vb_lib32.reportonly`)

- 입력: 그 결정의 `KC.compare` 보고 하나, 결정 꼴, 닫힌 목록. 출력은 경로·종류·개수·글자뿐입니다(목적값·예측값 0).
- 계산:
  - HARD: H2–H5 묶음의 `diff_paths_generalized` 경로마다, 목록의 HARD 경로(그 결정 꼴)에 있으면 "목록 안", 없으면 "목록 밖 HARD". H1(CSV 바이트)은 목록에 없으므로 CSV가 다르면 늘 "목록 밖"입니다.
  - 미분류: 보고의 `unclassified` 항목마다, 경로가 목록의 HARD 아닌 경로에 있으면 "목록 안", 없으면 "목록 밖 미분류"(이유 `why`와 개수를 그대로).
  - 잘림: KC는 HARD 묶음마다 경로를 80개까지, 미분류는 서로 다른 항목 200개까지 적습니다. 80개·200개에 닿았거나 미분류 개수 합이 `unclassified_n`과 다르면 "잘림"으로 적고 목록 밖 차이 1개로 셉니다(다 보지 못했다는 뜻).
  - 보이지 않은 목록 잎: 목록에 있는데 이 결정에서 다르지 않은 경로(`listed_not_seen`)도 적습니다(기대와 다르다는 보고 거리).
  - **목록 밖 개수** = 목록 밖 HARD + 목록 밖 미분류 + (CSV 다름이면 1) + 잘림 수.
- **보고서에 쓰는 꼴**:
  - 결정마다 한 줄: 사슬, T, 직전 T, 결정 꼴, 결과 넷 값(참고), CSV 같음, 목록 안 HARD 수 / 목록의 HARD 수, 목록 안 미분류 수, **목록 밖 개수**, 목록 밖 경로(HARD 묶음·경로 / 미분류 경로·이유·개수), 잘림, 보이지 않은 목록 잎.
  - 쉬운 문장 한 줄(결정마다): 목록 밖 0이면 "닫힌 목록 밖 차이 0개 (…경로는 보고에서 뺌).", 아니면 굵은 글자로 "**닫힌 목록 밖 차이 n개가 있습니다**: …"(함수가 만든 글자 그대로).
  - **보고서 맨 앞 요약**(V-B 보고서 §0, 판정 말 없음): "사슬 이어받는 OFF 10결정의 닫힌 목록 밖 차이: 결정 a개에서 모두 b개" 한 문장과, b > 0이면 그 결정·경로 목록. b = 0이어도 이 문장을 씁니다.
- 합성 확인 [실행 `AD32/dry/decl/dry_a32_reportonly.json`]: 실제 KC(K9-2-5, `3e2da987…`)에 합성 결정 폴더를 넣어 — R1 목록 잎만 다름(SS) → 결과 넷 FAIL(참고), 목록 밖 0, 목록 안 HARD 3·미분류 5; R2 `green_times` 하나 더 다름 → 목록 밖 HARD 1(`/green_times/sc109_p3`), 굵은 문장; R3 목록 밖 메타 잎 → 목록 밖 미분류 1; R4 CSV 다름 → 목록 밖 1; R5 CSV sha 잎 다름 → 목록 밖 미분류 1(D2); R6 NN 세 잎만 → 목록 밖 0·보이지 않은 잎 0; R6b 같은 보고를 SS 목록으로 → 목록 밖 0·보이지 않은 잎 10; R7 출력 없음 → INCOMPLETE 문장. 8/8 기대대로.

### 2.4 VB-I2–VB-I6 (그대로, 사슬 결정 55개 모두)

- 정의는 보충 24 §14.1(:548-552)·보충 27·29가 정한 그대로입니다(D-K9-62 "그대로"). 아래는 구동기·재계산기가 읽는 자리를 적은 것이고 뜻을 바꾸지 않습니다(자리는 VerifyVB `vvb_a.py`가 RR에서 읽은 것과 같은 키입니다 [읽음 `vvb_a.py:259-284`]).
  - **VB-I2**: 어댑터 종료 코드 0; 그 결정의 출력 폴더에서 그 T 파일 가운데 이름에 `hold`(대소문자 무시)가 든 파일 0과 `*.error.txt` 0; 어댑터 표준 출력·오류에 `DECISION_FAILED` 0; `metadata.controller_status` = `ok`; 이름에 `exception`(대소문자 무시)이 든 `metadata` 키 0; `metadata.head_observation_prior_discarded` = 0.0; `metadata.head_observation_snapshot_sec` = T. 단 하나의 선언된 예외: VB-41w **B1** 사슬 T=150은 `head_observation_prior_discarded` = 1.0이고, 그 결정의 (173, p4) 하한 값 = s(`1045.1612903225805`)이며 VB-41w B1 T=1 출력에 같은 이름의 키(값 = s)가 있을 때만 참(보충 24 :548 그대로).
  - **VB-I3**: B1 팔 파일 둘(CFG-B1, SAF-B1) 각각: 바탕(CFG / SAF-K91)과의 JSON 차이 = 정확히 두 경로(`urban.sc109w_through_saturation`, `urban.capacity.head_floor_seed`), 두 증거 sha = VBT 안 커밋 증거 파일 바이트 sha. 더해(이 보충이 더함, STOP을 늘리는 쪽, 공개 P6) 파일 sha = CFG-B1 `c8e3ee2c…` / SAF-B1 `65cac7ea…`.
  - **VB-I4**: 출력 = B1 41 + OFF 14 = 55결정, 결정마다 `action_<T>.json`·`.csv` 있음, 빠짐 0.
  - **VB-I5**: 재계산기(§4.6)가 VB-M 표(와 VB-I2·I3·I4·I6·I7)를 다시 내 같음.
  - **VB-I6**: B1 사슬 결정마다 이름이 `head_discharge_floor_173_p4_`로 시작하는 `metadata` 키가 정확히 하나이고, 이름 = 그 런의 기대 이름(`K92_VALUES.json` `/p0_2/f_expected_floor_keys`: v3c3-s43 `head_discharge_floor_173_p4_3e3dc5ca5bf80727`, v3c3-s31 재실행 `…_1170360c34e5b57b`, v3c3-s41 `…_301ceabb95f116fa`), 값이 사슬 안에서 줄지 않음(VB-41w T=150 값 = T=1 값 = s).

### 2.5 새 무결성 점검 VB-I7 — 훅 무결성 (사슬 결정 55개 모두)

- 결정마다 훅 폴더(§3.4)에서 모두 참:
  1. `loaded_<pid>.json`이 하나 이상 있고, 그 가운데 `argv0` = `vissim_stackelberg_adapter.py`인 것이 정확히 하나, 모든 `loaded` 파일의 `recorder_ok` = 참(REC 바이트 sha = `1d1dfa36…`).
  2. `hook_error_*.txt`·`hook_setup_error_*.txt` 0.
  3. 모든 후보 폴더 `c_<pid>_<seq>`에 `cand.json`·`k92_record.json`이 있음.
  4. 기록 폴더의 `k92_select.json`이 있고 상태가 `selected`·`no_candidate`·`no_match`·`match_conflict` 가운데 하나(`hook_error`·`no_hook`이 아님).
- 하나라도 거짓 → VB_INCOMPLETE → STOP(S-K52).
- 상태가 `selected`가 아닌 **SDMPC 결정**(`metadata.sdmpc_active` 참)은 STOP이 아니고 보고서에 눈에 띄게 적습니다(개수와 결정 목록, "그 결정의 VB-M5·M6·M8 = 없음(이유)"). 무제어 결정의 `no_candidate`는 예상입니다(§3.3).

### 2.6 VB-I 결과 규칙 정리

- VB_INCOMPLETE(→ STOP, S-K15): VB-I1(판정 4결정) 하나라도 PASS 아님, 또는 VB-I2–VB-I7 가운데 하나라도 거짓.
- 보고 전용 10결정의 목록 밖 차이는 VB_INCOMPLETE가 아닙니다. 단 그 비교 자체가 INCOMPLETE(출력 없음 등)면 VB-I4 거짓으로 이미 STOP입니다.
- OFF 사슬을 먼저 다 돌리고 VB-I1·OFF 결정의 VB-I2·VB-I7을 먼저 봅니다. 거짓이면 B1 사슬 전에 STOP합니다(§4.2 V5, S-K55).

---

## 3. 측정 훅 (D-K9-63)

### 3.1 파일과 싣는 법 (커밋 코드·동결본·VBT 그대로)

- 파일 = `HOOKDIR/sitecustomize.py`(sha256 `4d7e0375116c3f805aa223651da0dc1c0c04b7d3315062e98e21137ba60aa321`, 248줄, LF). HOOKDIR에는 이 파일 하나만 둡니다 [실행 `dry_a32_static.json`].
- **싣는 법**(몫 가르기 훅과 같은 방법, `METHOD.md` §5.1): 결정 재생 프로세스의 `PYTHONPATH` 맨 앞에 HOOKDIR을 붙입니다. 파이썬은 시작 때 `PYTHONPATH`의 `sitecustomize`를 읽습니다. 어댑터가 띄우는 탄젠트 작업자도 환경을 이어받아 같이 실립니다(몫 가르기 선례 [실행 `DA/hook/S1_A0h`: `loaded` 11개 = 어댑터 1, 작업자 9, `make_replay_state_v2.py` 1]). Python 3.12.2와 의존 폴더(`.review-deps/sdmpc`·`sdmpc-numba`)에 다른 `sitecustomize`가 없습니다 [실행].
- **켜는 스위치**: 환경 변수 `K92VB_HOOK_DIR`이 있을 때만 켜지고, 없으면 아무것도 하지 않습니다(그 변수가 없으면 모듈은 상수 넷과 함수 하나를 정의하고 끝남). 켤 때 함께 주는 변수: `K92VB_RECORDER`(= `VBT/diagnostics/sdmpc_n31_20260924/k8_gates/sa/k92_record.py`의 절대 경로), `K92VB_RECORDER_SHA256`(= `1d1dfa36…` 64자), `K92VB_T`(결정 시각, 정수), `K92VB_SEED`(31·43·41), `K92VB_LABEL`(예: `VB-43/b1/T003150`, `ZI/z1_b1/T001050`). 구동기는 이 변수를 **그 결정의 어댑터 프로세스 환경에만** 넣습니다(준비 도구·다른 자식에는 넣지 않음). 몫 가르기 훅 변수 `K92A_*`와 이름이 겹치지 않습니다(KI `child_env`가 `K92A_`를 지우는 것과 무관).
- **방식**: `sys.monitoring` 도구 번호 하나(3, 4, 5, 1, 2 순서로 빈 것), 전역 `PY_START`. 대상이 아닌 코드 자리는 `DISABLE`을 돌려 다시 부르지 않습니다. **대상 = 이름 `omega_costs`, 파일 바닥 이름이 정확히 `sdmpc.py`**(`sdmpc_pfo.py` 등이 잡히지 않음). `PY_RETURN`은 쓰지 않습니다.
- **고치지 않는 것**: 커밋 코드(GWT8), 동결본, VBT의 어떤 파일도 바꾸지 않습니다. 훅은 VBT 밖(KB)에 있고, VBT의 기록기 파일은 읽기만 합니다.
- **읽기 규칙**(몫 가르기 훅 규칙 그대로): 속성 읽기, dict·list 순회, `isinstance`, 숫자 꺼내기만. AD 값(`evaluation.controllers.sdmpc_dual.Dual` 하위 클래스)은 `.value` 칸만 읽고 `float()`를 부르지 않습니다(`Dual.__float__`은 예외 [읽음 `sdmpc_dual.py:172-196`]). `evaluation`·`src` 모듈을 import하지 않습니다(탄젠트 작업자의 "새 프로세스" 조건 보호 [읽음 `sdmpc_tangent_runtime.py:151-163`]). 프레임에서 닿는 어떤 객체에도 쓰지 않습니다. 훅 안의 모든 예외는 잡아 `hook_error_<pid>.txt`(시작 때는 `hook_setup_error_<pid>.txt`)에 적고 원래 실행으로 올려 보내지 않습니다. 후보 번호는 `threading.Lock` 아래에서 셉니다.

### 3.2 부르는 기록기 자리와 인자 (REC의 정확한 입구)

- 훅은 시작 때 `K92VB_RECORDER` 바이트를 한 번 읽어 sha256이 `K92VB_RECORDER_SHA256`(64자)과 같은지 봅니다. 다르면 `loaded`에 `recorder_ok: false`를 적고 시작 오류 파일을 쓰고 **꺼진 채로** 있습니다(그 결정은 VB-I7 거짓). 같으면 그 바이트를 한 번 `compile`해 둡니다.
- `omega_costs(point, cfg)` 호출마다(PY_START, 함수 몸이 돌기 전):
  1. 새 모듈 객체(`types.ModuleType('k92_record')`)에 그 코드를 `exec` — **호출마다 새 이름 공간**이라 기록기의 모듈 전역(`K92`, `STAGES`)이 호출끼리 섞이지 않습니다. `sys.modules`에는 넣지 않습니다. import 장치를 거치지 않으므로 탄젠트 작업자의 변환 찾기(`Finder`, VBT 아래 `.py`를 바꿔 실음 [읽음 `sdmpc_tangent_runtime.py:133-149`])를 타지 않고, 변환 원천 sha 목록(D5 잎)에도 들어가지 않습니다 [읽음·추론].
  2. `network_facts(cfg)` — REC:63-71(SC109 서측 두 movement 용량, `head_floor_seed` 속성).
  3. `collect(point.control_area_response, T, dt)` — REC:74-118. T = `K92VB_T`(실수), dt = `cfg.simulation.T_c_sec`. 이것은 plant 잡이 부르는 것과 같은 입구·같은 입력 꼴입니다(`sa_worker.py:744` `K92R.collect(point.control_area_response, T0, dt)`).
  4. `write(<후보 폴더>, job, T, dt, 3, None)` — REC:211-240. job = `{'label': K92VB_LABEL, 'harness': 'k92vb_hook', 'seed': K92VB_SEED, 'T': T}`, H = 3블록(450 s; 보충 24 VB-M6 "지평 450 s"), keyed = None. `write`가 `k92_record.json`(schema `k92-record/v1`)과 `k92_series.npz`를 후보 폴더에 씁니다.
  5. 훅이 같은 폴더에 `cand.json`(schema `k92vb-candidate/v1`)을 씁니다: 순번·pid·argv0·스레드·`time_ns`·호출자 세 단계, **행동 서명**(호출자 프레임 세 단계 안에서 처음 보이는 지역 변수 `action`의 `green_times` 전부·`offsets` 전부·`diagnostics.sdmpc_prediction_sequence.future[i].green_times`), 첫 거주 행 시작 시각, 거주 행 수·이동 행 수, `point.states` 길이(롤아웃 블록 수), dt, AD 여부, 기록기 오류 목록, 훅이 쓴 시간(`hook_sec`).
- **부르지 않는 입구**: `on_alloc`(REC:121-129). plant 잡에서는 `_allocate_receiving_counts` 감싸개가 부르지만(`sa_worker.py:516-519`), 결정 재생에서는 감쌀 자리가 없습니다(감싸면 모형 함수를 바꾸는 것). 그래서 기록의 `horizon.w_receiving_limited_steps`는 늘 0이고 **측정하지 않은 값**입니다. V-B 보고·재계산은 이 칸을 쓰지 않습니다(§3.6, 공개 P2).
- `vissim` 칸: seed가 47이 아니므로 기록기는 `vissim` = null, 이유 `k92_vissim_ref`를 적습니다(REC:203-208). V-B는 VISSIM 쪽을 합치지 않습니다.

### 3.3 어느 프로세스에서, 몇 번 [읽음·실행 선례]

- SDMPC 결정에서 `omega_costs`는 **탄젠트 작업자**의 `predict`에서 불립니다. 몫 가르기 S1(v3c3-s43 T=3,750) A0h에서는 작업자 9개가 한 번씩, 모두 9번이었고(AD 값 6번, 아닌 것 3번), 어댑터 프로세스(pid 17620)에서는 0번이었습니다 [실행 `DA/hook/S1_A0h` `e2_*.jsonl` 9파일·9줄, 어댑터 pid에는 `e1`·`e3`만]. 한 호출의 응답은 거주 행 900(도시 450 + 착지 450), 이동 행 186,938이었습니다 [실행 같은 파일 첫 줄].
- 무제어 결정(T < 900)은 SDMPC 풀이를 하지 않으므로 `omega_costs` 호출이 없을 것으로 봅니다 [추론: 기록 결정 벽시계 17.5–21.3 s, SDMPC 결정 457–585 s; `decision_budget.json` [실행]]. 그때 후보는 0개, 고르기 상태는 `no_candidate`, 그 결정의 VB-M5·M6·M8은 "없음(무제어 결정: SDMPC 예측 없음)"입니다. ZI의 Z2 칸이 이것을 실제로 보입니다(§3.5).
- 고른 행동의 기록을 찾는 규칙(§3.4)은 몫 가르기 E2의 "고른 행동의 끝점" 규칙과 같습니다(METHOD §5.2: 블록 0 녹색 전부·오프셋 전부·미래 블록 녹색이 재생 JSON과 정확히 같은 기록, 여럿이면 AD 아닌 것 먼저·가장 이른 것). 몫 가르기에서는 네 상태 모두 맞는 기록이 있었습니다(HC5 참 [읽음 `ATTRIBUTION.md` :35]).

### 3.4 결정마다 쓰는 자리와 고르기 (`AD32/vb_select.py`)

- **자리**(사슬 이름 `vb31`·`vb43`·`vb41`·`vb41w`, 팔 `off`·`b1`, `<T6>` = 6자리 T):
  - 후보: `VBR/chain/<사슬>_<팔>/hook/t<T6>/`(`loaded_<pid>.json`, `c_<pid>_<seq>/{cand.json, k92_record.json, k92_series.npz}`, 오류 파일). 구동기가 결정 전에 빈 폴더로 만듭니다(있으면 STOP).
  - **결정의 `k92_record.json`**: `VBR/chain/<사슬>_<팔>/rec/t<T6>/k92_record.json`(+ `k92_series.npz`, `k92_select.json`). 결정 출력 폴더(`dec/`, 다음 결정의 직전 행동 자리)에는 기록을 두지 않습니다.
  - ZI: `VBR/zi/<칸>/hook_on/`, `VBR/zi/<칸>/rec_on/`.
- **고르기**: 결정 프로세스가 끝난 뒤, 그 밖에서 `python -B AD32/vb_select.py select --hook-dir <후보 폴더> --action-json <그 결정 출력 JSON> --T <T> --dest <기록 폴더>`. 규칙(`vb_select.py` 머리말 그대로):
  - 후보가 **맞음** = (m1) 행동 서명이 출력 JSON의 `green_times`(모든 키, 값 실수로 같음)·`offsets`·`diagnostics.sdmpc_prediction_sequence.future[i].green_times`(둘 다 없거나, 길이 같고 블록마다 같음)와 같음, (m2) 첫 거주 행 시작 = T, dt = 150.0, 거주 행 > 0, (m3) `k92_record.json`이 있음.
  - 상태(이 순서로 하나): `hook_error`(오류 파일, 빠진 후보 파일, `recorder_ok` 거짓) → `no_hook`(어댑터 `loaded` 없음) → `no_candidate`(후보 0) → `no_match`(맞는 후보 0) → `match_conflict`(맞는 후보 둘 이상의 `blocks`·`horizon`이 숫자 상대 1e-9(분모 max(1, |a|, |b|)) 밖에서 다르거나 숫자 아닌 값이 다름) → `selected`(맞는 후보 가운데 (AD 여부, `time_ns`, pid, 순번) 순서의 첫째 — AD 아닌 것 먼저, 그다음 가장 이른 것). `selected`이면 그 후보의 `k92_record.json`·`k92_series.npz`를 기록 폴더로 **바이트 복사**합니다.
  - `k92_select.json`(schema `k92vb-select/v1`)은 늘 씁니다: 상태, 후보 표(pid·순번·AD·m1·m2), 맞는 개수, 고른 후보와 복사한 두 파일 sha, `loaded` 요약, 오류 파일 이름, 훅 시간 합, 출력 JSON sha, `sdmpc_active`, 키 표지(`metadata.k92_w`·`k92_hb` 있음). 같은 자리에 두 번 쓰지 않습니다(있으면 멈춤).
- 합성 확인 [실행 `dry_a32_select.json`]: S1 AD·비AD 두 후보가 맞음 → `selected`, 비AD; S1b 하나만 맞음; S2 녹색 다름 → `no_match`; S2f 미래 블록 다름 → `no_match`; S3 맞는 둘의 기록 다름 → `match_conflict`(복사 0); S4 후보 0 → `no_candidate`; S5 훅 예외 → `hook_error`; S6 어댑터 아닌 프로그램 → `no_hook`; S7 T 다름 → `no_match`; S8 같은 자리 다시 → 멈춤; S9 기록기 sha 다름 → `hook_error`; 명령줄 결과 = 함수 결과(기록 sha 같음). 12/12 기대대로.

### 3.5 훅 영향 0 시험 ZI (V-B 데이터 전; 비교 규칙은 지금 선언)

**상태(55개 V-B 결정 밖)** — V-B 결정은 (k8j1r_s31, T=3,000–4,500), (k8j1_s43, 3,000–4,500), (k8j1_s41, 3,000–4,500), (k8j1_s41, {1, 150, …, 1,050})입니다. ZI 칸은 이 집합에 없습니다.

| 칸 | 런 | T | 결정 꼴 | 직전 행동 | 팔(튜닝) | 근거 |
|---|---|---|---|---|---|---|
| `z1_off` | `sdmpc31_v3c3_k8j1_s43` | 1,050 | SDMPC ← SDMPC | RR `action_000900.json` | OFF(VBT SAF-K91 `5f0d0e40…`) | G-K0 D-c 상태(OUTH `gh3/v3c3_s43/T001050`) [실행 준비 기록] |
| `z1_b1` | 같음 | 1,050 | 같음 | 같음 | B1(SAF-B1 `65cac7ea…`) | 같음 |
| `z2_b1` | `sdmpc31_v3c3_k8j1_s43` | 750 | 무제어 ← 무제어 | RR `action_000600.json` | B1(SAF-B1) | 무제어 결정에서 훅이 실려도 같음을 봄 |

**절차(칸마다, 한 번에 하나, 구동기 §4.3 발사 규칙 그대로)**

1. 준비: `gprep.py <RR 결정 폴더> <T> VBR/zi/<칸> <준비 기록>` 한 번(§4.3).
2. **훅 끔** 재생: 출력 `VBR/zi/<칸>/replay/action_<T6>.json`·`.csv`. `PYTHONPATH`에 HOOKDIR 없음, `K92VB_*` 없음. 끝나면 `replay/` → `replay_off/`로 이름만 바꿈.
3. **훅 켬** 재생: 같은 준비 폴더, 같은 출력 경로(`replay/…`). `PYTHONPATH` 앞에 HOOKDIR, `K92VB_*`(훅 폴더 `VBR/zi/<칸>/hook_on`). 끝나면 `replay/` → `replay_on/`. 고르기 → `VBR/zi/<칸>/rec_on/`.
   - 까닭: 두 실행이 같은 상태 파일·같은 출력 경로를 써야 경로 잎이 다를 일이 없어 "벽시계 잎만 다름"을 그대로 볼 수 있습니다. 둘째 실행이 다시 쓰는 `obs150/derived_<T>.json`은 "같은 바이트가 이미 있으면 그대로"입니다(`obs150_contract.py:1531-1544`) [읽음]. 다른 바이트면 어댑터가 멈춰 훅 켬 실행이 실패하고 ZI 거짓이 됩니다. 재생은 차로 관측 캐시를 읽거나 쓰지 않습니다(`lane_plant_observation.py:303` "Offline replay never reads or changes the live cache") [읽음].
4. 판정(아래 규칙) → `VBR/zi/<칸>/zi_judge.json`.

**선언하는 비교 규칙 — "G-K0 비교로 같고 벽시계 잎만 다름"** (함수 `AD32/vb_lib32.py` `zi_judge`; 바이트 같음은 쓰지 않음: 결정 JSON에는 실행마다 다른 벽시계 잎이 있음 [읽음 KC L_T 55개])

- ZI 칸 PASS = 아래가 모두 참:
  - (z1) 두 실행 모두 어댑터 종료 0, 출력 JSON·CSV 있음, 출력 폴더에 `*.error.txt` 0, 표준 출력·오류에 `DECISION_FAILED` 0.
  - (z2) CSV 바이트 같음(sha).
  - (z3) `KC.compare(replay_off, replay_on, T, VBT, keyed=None, old_root=VBT)` 결과 넷 = **PASS**(보충 21 §6.4 규칙, G-K0와 같은 비교기; 새 허용 0).
  - (z4) 진행 기록 마지막 `sdmpc_completed`의 목적값·유지 목적값 repr 같음(KC `progress_last`; 무제어면 두 쪽 모두 없음).
  - (z5) **벽시계 잎만 다름**: 두 출력 JSON을 KC `norm`으로 정규화하고 KC `deep_diff`로 낸 모든 차이 잎이 KC `is_f3`를 만족(종류 value·type, 마지막 키가 L_T 55개 이름, 두 값이 숫자·ISO 시각·둘 다 null). 그 밖의 차이(V 상태 경로, F1 16진 토큰, F2 sha 이름, R3, 있음·없음 차이 등)는 하나라도 있으면 거짓.
  - (z6) 훅 끔 실행은 훅 파일을 어디에도 만들지 않음(훅 폴더를 만들지 않았고, 준비 폴더 아래 `loaded_*`·`c_*` 0).
  - (z7) 훅 켬 실행의 VB-I7 1–3 참(어댑터 `loaded` 하나, `recorder_ok` 참, 오류 0, 후보 완전). `z1_off`·`z1_b1`은 고르기 상태 = `selected`(훅이 실제로 기록을 냄). `z2_b1`은 상태를 보고만(예상 `no_candidate` [추론]).
- **ZI 전체 PASS = 세 칸 모두 PASS.** 하나라도 거짓·실행 실패·준비 실패 → **STOP(S-K51), 사슬 계산 0인 채로** 보고합니다. 훅을 고치는 것은 사용자 결정입니다.
- **보고만(통과 조건 아님)**: (가) **훅 비용** — 칸마다 훅 켬 / 훅 끔 어댑터 벽시계 비(구동기가 잰 실행 시간), 후보 수, 후보 `hook_sec` 합(작업자들 안에서 훅이 쓴 시간), 후보 파일 크기 합; (나) `z1_off` 훅 끔 출력 대 RR 기록 `KC.compare(RR, replay_off, 1050, VBT, old_root=FRZ_K8)` 결과 넷(발사 규칙이 기록을 재현하는지; G-K0 D-c와 같은 꼴); (다) 훅 켬 실행의 고른 기록 요약 칸 이름(값 아님).
- 합성 확인 [실행 `dry_a32_zi.json`, 실제 KC]: Z1 벽시계 잎 넷만 다름(`decision_wall_sec`, `…/budget/wall_sec`, `started_at`, `/prediction/wall_sec`) → PASS; Z2 녹색 다름 → 거짓; Z3 상태 경로(V)만 다름 → KC는 PASS지만 (z5) 거짓; Z4 16진 토큰(F1)만 다름 → KC PASS, (z5) 거짓; Z5 CSV 다름 → 거짓; Z6 벽시계 이름 키가 한쪽에만 → 거짓; Z7 진행 기록 목적값 다름 → 거짓; Z8 같음 → PASS; Z9 `final_check_reserve/seconds`(L_T 이름이지만 KC가 벽시계에서 뺀 자리) → 거짓; Z10 출력 없음 → 거짓. 10/10 기대대로.

### 3.6 VB-M5·M6·M8을 기록에서 읽는 법과 키 끔 쪽

- 읽는 파일: 결정의 `rec/t<T6>/k92_record.json`·`k92_series.npz`(상태 `selected`일 때만). 그 밖의 상태면 그 결정의 세 지표는 "없음(상태 이름)"입니다. 추정하지 않습니다.
- **VB-M5** (모형 174 사슬, 보충 24 :560): (a) 지평 끝 재고 = `horizon.m1_chain_T450`(블록 3 끝 행의 세 사슬 키 합; 사슬 키 = `movement:SC109_W_SC108_to_E`, `movement:SC109_W_SC108_to_N_SC16`, `storage:SC108_to_SC109`, REC:27); 블록 끝 값 셋 `blocks[k].chain_sum`(k = 1, 2, 3)도 함께; (b) 지평 최대 = `k92_series.npz`에서 `t_end` ∈ (T, T + 450]이고 세 사슬 키가 모두 유한한 행의 세 키 합의 최대; (c) 직진이 용량에 묶인 스텝 비율 = `horizon.w_capacity_bound_steps / horizon.w_steps_with_departures`(분모 0이면 없음); (d) `SC109_E_out` 지평 최대 / 220 = `horizon.e_out_max_over_220`; (e) 할당 키가 있는 결정 수 = 사슬마다 출력 JSON `metadata`에 `k92_w`가 있는 결정 수와 `k92_hb`가 있는 결정 수(결정 JSON에서 셈, 기록 아님).
- **VB-M6** (D-K9-32, 보충 24 :561): OUTW = `horizon.outw_veh_h_450`(veh·h), FEED-4 몫 = `horizon.feed4_veh_h_450`과 그 비 `feed4 / outw`(outw ≤ 0이면 비는 없음), "모형 Ω 비용과 같은 표"의 Ω 칸 = 출력 JSON `metadata.joint_leader_selection.selected_objective`(보충 21 §6.2 H3 잎; 고른 계획의 목적값, 값 그대로). Ω 감소는 Ω 밖 증가와 함께만 인용합니다(보충 24 §7-1).
- **VB-M8** (보충 24 :563): 유령 `movement:SC109_N_SC16_to_W_SC108` 재고 지평 끝 = `horizon.phantom_end_450`.
- 쓰지 않는 칸: `horizon.w_receiving_limited_steps`(측정하지 않음, §3.2), `vissim`(null).
- **키 끔 쪽**: B1 사슬과 나란히 둘 키 끔 값은 **훅을 단 OFF 사슬 14결정**(VB-31·VB-43·VB-41의 T=3,000·3,150, VB-41w 8결정)의 기록에서만 냅니다. 그 밖의 T(VB-31·43·41의 T=3,300–4,500)의 키 끔 칸은 "없음(OFF 사슬 밖, 추가 재생 없음)"입니다. RR 기록에는 이 기록기가 없었습니다(기록 런은 J1, 기록기는 K9-2-0) [읽음]. VB-M1–M4·M7·M9의 키 끔 쪽은 보충 24 그대로 RR 기록 결정 JSON입니다.
- 합성 확인 [실행 `dry_a32_hook.json` `/cases/on_normal/record_checks`]: 합성 응답(50 s 행 9개, 이동 27개)에서 기록의 `m1_chain_T150`·`m1_chain_T450`·`e_out_max_over_220`·`outw_veh_h_450`·`feed4_veh_h_450`·`phantom_end_450`·`m2_w_dep_T450`·`w_steps_with_departures`, `T0` = 3,000·`block_sec` 150·`H` 3, 용량 5,209.8, seed·`vissim` null·이유, 오류 0, `keyed` null이 따로 계산한 값과 같음(세 후보 모두).

### 3.7 비용 [추론]

- 결정 계산: SDMPC 결정 43개(B1 33 + OFF 6 + VB-41w 900·1,050 두 팔 4) × 약 450–590 s(RR `decision_budget.json` `wall_sec` [실행]) ≈ 5.4–7.0 h, 무제어 12개 × 약 20 s + 시작·적재, 준비(사본) 61번 × 약 0.5분, ZI 6실행(SDMPC 4 × 약 520 s + 무제어 2) ≈ 0.6–0.7 h. 합 약 7–8.5 h에 훅 부담을 더합니다(보충 24 :577의 8–9 h 어림 안).
- 훅 부담: 호출마다 이동 행 약 19만 개를 한 번 훑고, 행 × 키 표를 `npz`로 압축해 씁니다. 결정마다 작업자 안 약 9번 [실행 선례 수]. ZI가 실제 비를 잽니다.
- 디스크: 결정 출력 약 110 MB(SDMPC: JSON 58 MB + `.joint.json` 53 MB [실행 RR 크기]) × 55 + 준비 사본 + 후보 기록. 약 7–10 GB. D: 388 GB 여유.

### 3.8 합성 확인 요약 (`AD32/dry_a32.py all`) [실행, 출력 sha는 §10·§13]

| 부분 | 내용 | 결과 |
|---|---|---|
| static | 네 도구의 import = 표준 라이브러리만, `evaluation`·`src`·`k92_record`·`k92_compare` import 0; HOOKDIR = 파일 하나; 대상·스위치·세 입구 글자 | 참 |
| closed | 목록 다시 만들기 바이트 같음; 꼴별 경로·잎·HARD 수 (3, 3, 1)·(9, 12, 1)·(13, 16, 3); 10결정 꼴; 사슬 첫 결정 4개 = 목록 없음 | 참 |
| hook | 합성 프로그램(이름 `vissim_stackelberg_adapter.py`, 합성 `sdmpc.omega_costs`, 합성 `Dual`)을 자식 python으로: 훅 경로 없음 / 경로 있고 스위치 끔 / 켬 — 결과값 셋 모두 같음, 끔에서 파일 0·모듈 목록 같음; 켬에서 후보 3(비AD, 비AD, AD), 후보 파일 셋, 서명·메타·기록 값 맞음, `evaluation`·`src` 모듈 더함 0, `k92_record`가 `sys.modules`에 없음; 기록기 sha 다름·`K92VB_T` 없음 → 시작 오류·후보 0·결과 같음; 응답 읽기 예외 → `hook_error` 1·결과 같음; 스레드 4개 → 후보 4·오류 0; 다른 파일의 `omega_costs`·`sdmpc.py`의 다른 함수 → 후보 0 | 참 |
| select | §3.4 12사례 | 참 |
| receipt | §4.5-2 RR 영수증 다섯과 바이트 같음, 어댑터 읽기 꼴로 읽힘; 합성 쓰기 규칙 | 참 |
| reportonly | §2.3 8사례 | 참 |
| zi | §3.5 10사례 | 참 |
| mutants | 도구 글 한 곳씩 망가뜨린 8벌(M1 BOM 없는 영수증, M2 미분류 모두 목록 안, M3 CSV 무시, M4 벽시계 점검 뺌, M5 AD 먼저, M6 시각 조건 뺌, M7 훅 sha 점검 뺌, M8 훅이 `write`에 T0 = 0) | 8/8 잡음 |

- 합성 프로그램이 훅 켬에서 더 import한 모듈은 표준 라이브러리 24개뿐이었습니다(`array`, `pathlib`, `zipfile`, `zlib`, `bz2`, `lzma`, `importlib.util` 등 — 기록기 `write`의 `numpy.savez_compressed`가 부름) [실행 `dry_a32_hook.json` `/cases/on_normal/extra_modules_vs_base`]. 실제 작업자에서도 표준 모듈이 더 실릴 수 있습니다(공개 P8). 출력에 영향이 있으면 ZI가 보입니다.

---

## 4. V-B 구동기 `vb_chain.py`와 재계산기 `vb_recalc.py`

### 4.1 만드는 때·자리·고정

- **만드는 때**: 보충 32 고정 뒤, V-B 단계가 씁니다(보충 24 §14.1-4 그대로). 커밋하지 않는 스크래치 도구입니다. 자리: `KV/vb_chain.py`, `KV/vb_recalc.py`, 자기 시험 출력 `KV/selftest/`.
- **고정(첫 사슬 계산 전 = ZI 전)**: V-B 단계는 (1) `KB/a32_pins.sha256` = 기대 파일 `AD32/a32_pins.expected.sha256`의 바이트(`cmp` 같음; 고정점 32가 정한 기대 파일), `sha256sum -c` 51줄 모두 OK; (2) 자기 시험(§4.5, §4.6)을 돌린 뒤 `KV/vb_pins.sha256`(구동기·재계산기·자기 시험 도구·자기 시험 출력의 줄, 꼴은 보충 30 §9와 같음)을 쓰고; (3) 두 목록의 sha와 줄 수, 구동기·재계산기 sha를 LOG 한 항목에 적은 **뒤에만** V0를 시작합니다. 구동기는 시작 때 자기 sha와 재계산기 sha가 LOG에 64자로 있는지 기계로 봅니다.
- 고정 뒤 구동기·재계산기·훅·고르기·도움 함수·닫힌 목록을 고치면, 결과를 보았든 아니든 S-K53(STOP·사용자)입니다(보충 24 §14.1-4·S-K12와 같은 뜻).
- 구동기와 재계산기가 꼭 지킬 이 보충의 규칙: 트리 자리(보충 27 §2.1, `TK/<이름>`), R-CR, 새 N(KC), 결과 넷, 옛 뿌리 표(보충 29 §6.2), 닫힌 목록(§2.2), 훅 싣기(§3.1), 고르기(§3.4), ZI(§3.5), 직전 행동(§4.4).

### 4.2 구동기 단계 (명령 `chain`, 한 번, WMI 분리; 단계 기록 `VBR/stages/<단계>.json`, STOP 파일 `VBR/STOP_vb_<단계>.json`, 단계 줄 `VBR/steps.jsonl`, LOG 자동 줄)

| 단계 | 내용 | 통과 조건 (하나라도 거짓 → STOP) |
|---|---|---|
| V0 사전 점검(읽기만; 첫 파일이 `VBR/check_v0.json`) | C1 보충 24–31 sha = `.sha256` = §0, 고정점 24–31 sha = §0. C2 보충 32 sha = `.sha256` = 고정점 32 글 안의 64자(Declare 판 sha는 고정점에 앞 16자만). C3 결정 기록 앞 204줄 sha = `402eaf59…`(덧붙임만 허용). C4 GWT8 head `e27ceac8…`, 브랜치, K8 `b9734abe…`, status 0줄, `b9734abe..HEAD` 6, 원격 k92 0, `git worktree list`에 vb 0. C5 `KB/a32_pins.sha256` = 기대 바이트, 51/51 OK; `KV/vb_pins.sha256` 모두 OK, 그 sha가 LOG에. C6 `KB/a31_pins.sha256` 133줄 가운데 다른 것은 127줄(`GATES_K92B1.md`, 지금 `449b361e…`, 보충 31 설계된 덧붙임)뿐. C7 K92_GATES_PASS 기록 셋 sha(§0). C8 `VBR`·`VBT`·`TK/vb_e27ceac8.build.json` 없음(처음) — 이어 하기면 §4.7. C9 RR 세 런 결정 폴더의 목록(이름·크기·수정 시각) sha 기록(끝에 다시 같음). C10 VISSIM 0, 남의 러너·재생 0(KI `census`). C11 C:·D: 여유 ≥ 8 GB. C12 세 튜닝(CFG, SAF-K91, CFG-B1)과 V2 뒤 SAF-B1의 `phase_price.mode` ≠ `observed_backpressure`(직전 행동 옆 `state_*.json`을 읽는 자리가 꺼져 있음, §4.4) | 모두 참 |
| 스냅숏 | `KI/k92snap.py take OK2/snap/s38_vb_v0.json`, s02 대비 SAME | SAME |
| V1 트리 | `cglib.build_archive('vb_e27ceac8', 'e27ceac86c01c1dcfd5b2bb2d9b522be3dc33c0d', log, cr_fix=True)`(KI `cglib.py:126-163`, CR 고침 `:115-123`, 바꾸지 않음) → `TK/vb_e27ceac8` + `TK/vb_e27ceac8.build.json`. 점검: `k92_a27.tree_root_ok(VBT)`; CR 형태 `CCCCCCCCCC`; `cr_pair(FRZ_K8b, VBT)`·`cr_pair(FRZ_K8, VBT)` 참; VBT RS `70cca680ef9f5dd84ee506ff8857712466f3779039289ca79adadc3d8f1eceba`, SHO `a6b5931ee3c4b04eacb023a0f7c29ac0f50cb1e955e9577f09ff7b5162680443`, CFG `d0f9ef39…`, SAF-K91 `5f0d0e40…`, CFG-B1 `c8e3ee2c…`, REC `1d1dfa36…`, KC `3e2da987…`(보충 29 K9-2-5 트리 `TK/a27/k925` 빌드 기록과 같은 값 [실행]). 보고만: VBT 대 GWT8 작업 트리 바이트 차이 개수 | 모두 참 |
| V2 팔 | `python -B VBT/…/k8_gates/sa/sa_arms.py --root VBT --out VBR/arms --k92b1` → `VBR/arms/sa/tuning/config_n31_v2_stopline_observed_full_k91_k92b1.json` sha = SAF-B1 `65cac7ea…`; VB-I3(§2.4) 두 팔 파일; C12를 SAF-B1에도 | 모두 참 |
| V3 ZI | §3.5 세 칸(여섯 실행), `VBR/zi/zi.json` | 세 칸 PASS |
| 스냅숏 | `s39_vb_zi.json` | SAME |
| V4 OFF 사슬 | 순서 VB-41w(8) → VB-31(2) → VB-43(2) → VB-41(2). 결정마다: 준비 → 재생(훅 켬, §4.3) → 영수증(§4.4) → 고르기(§3.4) → 그 결정의 VB-I2·VB-I7 → 결정 기록 `VBR/chain/<사슬>_off/done/t<T6>.json` | 결정마다 종료 0 |
| V5 OFF 관문 | VB-I1 판정 4결정(§2.1), OFF 14결정의 VB-I2·VB-I7, 보고 전용 10결정 표(§2.3) 계산 → `VBR/judge/vb_i1.json`, `vb_reportonly.json` | VB-I1 4/4 PASS, VB-I2·VB-I7 14/14 참 (보고 전용 표는 통과 조건 아님) |
| 스냅숏 | `s40_vb_off.json` | SAME |
| V6 B1 사슬 | 순서 VB-41w(8) → VB-31(11) → VB-43(11) → VB-41(11). 결정마다 V4와 같은 절차 | 결정마다 종료 0 |
| V7 무결성 | VB-I2·VB-I3·VB-I4·VB-I6·VB-I7 55결정 → `VBR/judge/vb_i.json` | 모두 참 |
| V8 지표 | VB-M1–M9 표(보충 24 :556-566, §3.6) → `VBR/judge/vb_m.json` | 표가 만들어짐 |
| V9 재계산 | `python -B KV/vb_recalc.py run --vbr VBR --dest VBR/recalc/recalc.json`(자식 하나, 구동기 import 0) → VB-I5 | 다시 낸 값 모두 같음 |
| 스냅숏 | `s41_vb_end.json` | SAME |
| V10 보고 | §5 보고서 둘, 끝 대조(`KB/a32_pins.sha256`·`KV/vb_pins.sha256` 모두 OK, GWT8 head·status·K8·원격, RR 목록 sha = C9, `OK2/vb` 밖 OK2 쓰기 = 스냅숏·로그뿐), LOG | 대조 OK |

- V0–V10은 한 번 돌리는 사슬입니다. V3에서 STOP이면 사슬 계산 0입니다. V5에서 STOP이면 B1 사슬 0입니다.
- 각 단계 끝에 `steps.jsonl`에 이름·rc·초·VISSIM 개수 전/후를 한 줄씩 적습니다. 기다리는 쪽은 이 파일과 `stages/`·`STOP_vb_*` 이름만 봅니다(로그 걸러 읽기 0).

### 4.3 재생 발사 규칙 (ZI와 55결정 모두)

- **준비**: KI `cglib.replay`와 같은 준비 — `python -B SP/j1/fix/gates/gprep.py <RR 결정 폴더> <T> <준비 폴더> <준비 기록>`(복사만, 하드 링크 0, 사본마다 sha 대조; F17b 이력 복사) [읽음 `gprep.py:1-40`, `cglib.py:212-226`]. 준비 기록의 `all_copies`·`state_obs150_directory_is_bundle` 참, `history_count` = `history_expected`가 아니면 STOP. 준비 폴더: 사슬 `VBR/chain/<사슬>_<팔>/prep/t<T6>`, ZI `VBR/zi/<칸>`. 이미 있으면 다시 쓰지 않습니다.
- **어댑터 인자**: `k92_replay.py:97-106`과 같은 목록·같은 순서 — `ADP --state-json <준비된 상태> --out-action-json <출력 JSON> --out-action-csv <출력 CSV> --mapping-json <재기반 대응표> --controller <제어기> [--detector-mapping-json <러너 설정의 값>] --calibration-json <재기반 보정> --tuning-json <팔 튜닝> [--previous-action-json <직전 행동>] [--mode <RW_ADAPTER_MODE>]`. 재기반·제어기 규칙(`launch_plan.json`: T < `control_start_sec`이면 `warmup_controller`, 아니면 `controller`)도 `k92_replay.py:60-95` 그대로입니다. **다른 점 둘만**: 출력 경로(사슬은 `VBR/chain/<사슬>_<팔>/dec/action_<T6>.json`·`.csv`, ZI는 §3.5)와 직전 행동 경로(§4.4).
- **환경**: KI `child_env(numba_dir=VBR/numba_cache)`(`RW_`·`K8_`·`K8G_`·`S31F_`·`GH1_`·`K92A_` 지움, `NUMBA_CACHE_DIR`, 스레드 1, `PYTHONUTF8`·`PYTHONDONTWRITEBYTECODE` 1, `PYTHONHASHSEED` 0, `NUMBA_NUM_THREADS` 지움)를 바탕으로 `k92_replay.py:107-112`와 같이: `RW_` 지움 → 런 `run_provenance` env 덮음 → `PYTHONPATH` = `[HOOKDIR;]<DEP>\sdmpc;<DEP>\sdmpc-numba`(DEP = `C:\Users\TRLAB\Documents\ChatGPT\VISSIM\.review-deps`) → `OMP`·`OPENBLAS`·`MKL` 스레드 1, `PYTHONUTF8` 1. 훅 켬이면 `K92VB_*`(§3.1)를 더합니다. 그 밖의 변수는 넣지 않습니다.
- **실행**: `python` = 런 env `RW_PYTHON`, `-B`, 작업 폴더 = VBT, 표준 출력·오류 → `<출력 JSON 이름>.stdout.txt`·`.stderr.txt`(러너 꼴; 어댑터는 이 파일을 읽지 않음), `BELOW_NORMAL`. 정체 감시: 진행 기록(`action_<T6>.joint.progress.jsonl`)이 30분 자라지 않으면 **자기 PID 나무만** 끕니다(KI `k92lib._run_watched:324-346` 꼴). 무제어 결정은 진행 기록이 없으므로 시간 상한 30분을 둡니다. 끈 결정은 STOP(S-K15).
- `make_replay_state_v2.py compare`는 돌리지 않습니다(그 비교는 `original/` 대 `replay/`를 보는 것이고, V-B의 비교는 §2·§3.5입니다).
- 실행 기록 `<출력 폴더>/run_t<T6>.json`: 인자 목록, 환경의 이름 목록과 지정 값(`PYTHONPATH`·`K92VB_*`·`PYTHONHASHSEED`·`NUMBA_CACHE_DIR`), 종료 코드, 벽시계, 출력 sha.

### 4.4 직전 행동 규칙

- **사슬 첫 결정**(T=3,000 세 개, VB-41w T=1): `k92_replay.py:63-74`가 쓸 경로 그대로 — RR `<런>/decisions_<런>/action_<직전 T6>.json`(T=1은 없음). 준비 기록의 직전 증거(sha)와 RR 파일이 같은지 봅니다(`k92_replay.py:66-72`와 같은 점검). RR에는 아무것도 쓰지 않습니다.
- **사슬 이어받는 결정**: 직전 행동 = `VBR/chain/<사슬>_<팔>/dec/action_<직전 T6>.json` — 같은 사슬·같은 팔의 앞 결정 출력. 그 결정의 `done` 기록이 있고(종료 0, 출력 sha 기록), JSON·CSV sha가 그 기록과 같아야 합니다. 그 밖의 파일을 직전 행동 자리에 두지 않습니다.
- **영수증**: 앞 결정이 끝난 뒤(종료 0) 출력 폴더에 `action_<T6>.json.sdmpc_pending`이 **있을 때만** 구동기가 `action_<T6>.json.applied`를 씁니다(러너 규칙 `run_real_world_stackelberg_controller.vbs:1281-1287`: 적용 성공 뒤, `.sdmpc_pending`이 있으면). 바이트 = `AD32/vb_lib32.receipt_bytes(T, <출력 CSV 절대 경로 글자>, <출력 CSV 바이트 크기>)` = UTF-16 LE + BOM, 줄 끝 CRLF, 세 줄(T 정수 글자, 경로, 크기). 어댑터 `load_prices`가 이것을 읽어 직전 시각·경로·크기를 봅니다(`sdmpc.py:519-528`). 이미 있으면 다시 쓰지 않습니다(멈춤). 앞 결정 종료가 0이 아니면 영수증 0이고 그 자리에서 STOP입니다. 이 영수증은 "VISSIM에 적용했다고 치는" 영수증입니다: 오프라인이라 실제 적용은 없습니다(공개 P9, 한계 §11-7).
- **직전 행동 옆 `state_*.json`**: 어댑터에서 직전 행동 경로 옆의 `state_<T−150k>.json`을 읽는 자리는 두 곳뿐입니다 — `install_observed_backpressure_price`(ADP:1939-2060; 튜닝 `phase_price.mode` = `observed_backpressure`일 때만)와 `network_pressure.previous_state_paths`(부르는 곳 없음 [실행 grep]). 세 튜닝(CFG·SAF-K91·CFG-B1)의 `phase_price`에 `mode`가 없습니다 [실행]. 그래서 사슬 폴더에 상태 사본을 두지 않습니다. 구동기는 V0 C12·V2에서 이 조건을 다시 보고, 거짓이면 STOP합니다.
- **N이 바꾸지 않는 자리**: 사슬 파일은 OK2 아래에 있으므로 N 뒤에도 경로 글자가 RR과 다릅니다(VB_PRECHECK_STOP §2.3-1). 이것이 §2.2 목록의 까닭입니다.
- 모든 사슬은 실행 기록의 `run_id`·스냅숏 시각을 바꾸지 않습니다(보충 24 §14.1-3 그대로; 상태는 RR 기록 그대로 준비).

### 4.5 구동기 자기 시험 (합성, 자식 프로세스 0; 보충 24 §14.1-4)

자기 시험 출력 `KV/selftest/vb_selftest.json`. 하나라도 거짓이면 고정하지 않고 STOP(S-K15)입니다.

1. **발사 규칙 같음**: 합성 런 폴더(합성 `run_provenance_<런>.json`·`launch_plan.json`·러너 설정·대응표·보정·튜닝·상태·준비 기록)에서 VBT의 `k92_replay.py`를 **같은 프로세스 안에서** 불러 `main()`을 돌리되, 그 모듈의 `subprocess.run`을 붙잡는 가짜로 바꿔(자식 0) 어댑터 인자·작업 폴더·환경을 받습니다(`--no-compare`). 구동기 발사 함수가 같은 입력에서 만든 인자·작업 폴더·환경과 비교합니다: (가) T=1(직전 없음), (나) RR 꼴 직전(사슬 첫 결정과 같은 경로), (다) `--extra-pythonpath HOOKDIR` — 세 경우 모두 같음; (라) 사슬 이어받는 꼴은 직전 경로 값 하나와 출력 경로 둘만 다름. 환경은 `K92VB_*`를 뺀 뒤 비교합니다.
2. **영수증 바이트**: `vb_lib32.receipt_bytes`가 RR 영수증 다섯(§0, 기대 고정 목록 46–50줄)의 바이트와 같음(각 CSV의 실제 크기와 RR 경로 글자로) — Declare가 이미 확인 [실행 `dry_a32_receipt.json`: 5/5 같음, 어댑터 읽기 꼴(`sdmpc.py:522-528`을 옮긴 함수)로 5/5 읽힘]. 구동기 자기 시험은 이것을 구동기 영수증 쓰기 함수로 다시 봅니다. 그리고 합성 폴더에서 `.sdmpc_pending` 없음 → 영수증 0, 있음 → 씀, 두 번째 → 멈춤.
3. **쓰기 범위**: 구동기의 쓰기 지킴 함수가 VBR, `TK/vb_e27ceac8`(V1에서만), `TK/vb_e27ceac8.build.json`, `KV`, `KB/LOG.md`(덧붙임), `OK2/snap/s38–s41`, `OK2/logs/vb_*` 밖 경로를 거부하고, RR·FRZ_K7/K8/K8b·GWT8·저장소 `.git`·`k92attrib`·DA·V4·OUTH·OUTK·봉인 뿌리·OK2의 다른 폴더 경로를 거부함(합성 경로 목록).
4. **사슬 계획**: 55결정의 (사슬, 팔, T, 직전 T, 첫/이어받음, 결정 꼴, 옛 뿌리, 튜닝 파일, seed, 제어기) 표가 §2.1·§2.2·보충 24 §14.1 표와 같음; OFF 14 = 첫 4 + 이어받음 10; 꼴은 닫힌 목록 `decisions`와 같음.
5. **판정 함수**: VB-I2·VB-I6·VB-I7 함수를 합성 결정 JSON·합성 훅 폴더에 — 참 사례와 거짓 사례(예외 키, hold 파일, prior 1.0, VB-41w B1 T=150 예외의 참·거짓 세 꼴, 하한 키 둘·이름 다름·값 줄어듦, 오류 파일, `recorder_ok` 거짓)가 기대대로.
6. **이어 하기**: 합성 단계 기록으로 — 완전한 결정은 건너뜀, 반쯤 된 결정 폴더는 `_interrupted_<시각>`으로 옮기고 그 결정부터 다시, 판정 파일이 있는 단계는 다시 돌리지 않음.
7. **AD32 함수 그대로 씀**: 구동기가 `vb_lib32`·`vb_select`를 고정 sha로 불러 씀(바이트 사본 아님), 그 sha가 `KB/a32_pins.sha256` 1–3줄과 같음.

### 4.6 재계산기 `vb_recalc.py` (VB-I5)

- **독립**: 표준 라이브러리와 numpy만 import합니다. 구동기, AD32 도구(`vb_lib32`·`vb_select`·훅), KI, 하네스(`sa_*`·`k92_*`), VBT·GWT8 모듈을 import하지 않습니다. 규칙은 이 보충과 보충 24 §14.1의 글에서 따로 구현합니다. 닫힌 목록 JSON은 데이터로 읽어도 됩니다(코드 아님).
- **입력**: VBR의 결정 출력 JSON·CSV, 각 결정의 훅 폴더(`cand.json`·후보 `k92_record.json`), 기록 폴더(`k92_select.json`·`k92_record.json`·`k92_series.npz`), 팔 파일, `K92_VALUES.json`.
- **다시 내는 것**: (1) 고르기 — 후보에서 §3.4 규칙으로 다시 골라 상태·고른 후보가 `k92_select.json`과 같고, 고른 후보 기록 바이트 sha = 기록 폴더 `k92_record.json` sha; (2) VB-I2·VB-I3·VB-I4·VB-I6·VB-I7; (3) VB-M1–M9 표 전부(§3.6 정의).
- **같음**: 숫자는 상대 1e-12 안(분모 max(1, |a|, |b|)), 그 밖(글자·참거짓·없음·상태 이름)은 정확히 같음. 하나라도 다르면 VB-I5 거짓 → STOP(S-K15).
- **자기 시험**(고정 전, 합성, 자식 0): 합성 VBR(두 사슬 × 세 결정, 합성 후보·기록·`npz`)에서 재계산기 결과가 손으로 낸 기대값과 같음, 그리고 결정 JSON 값 하나·후보 서명 하나·기록 숫자 하나를 바꾸면 다름을 잡음. 출력 `KV/selftest/vb_recalc_selftest.json`.

### 4.7 실행 위생·이어 하기

- 보충 24 §3.1-4 그대로: 무거운 Python 한 번에 하나, `BELOW_NORMAL`, `python -B`, `PYTHONHASHSEED=0`, 5분 넘는 일은 WMI 분리(`KI/launch.ps1 -Tag vb_chain -Script ..\k92_vb\vb_chain.py -ArgLine chain`, 표준 출력 `OK2/logs/vb_chain.txt`), 기다림 확인 한 번에 9분 이하, 자기 PID만 끔, C:·D: 8 GB 밑이면 멈춤, VISSIM 0.
- 이어 하기: 단계·결정 기록이 있고 sha가 맞으면 건너뜁니다. 반쯤 된 결정(출력·훅·기록 가운데 무엇이 있으나 `done` 기록 없음)은 지우지 않고 옮깁니다: 그 T의 준비 폴더 `prep/t<T6>`·훅 폴더 `hook/t<T6>`·기록 폴더 `rec/t<T6>`은 이름 뒤에 `_interrupted_<시각>`을 붙이고, `dec/`의 `action_<T6>.*` 파일은 `dec/_interrupted_<시각>_t<T6>/`로 옮깁니다. 그 뒤 그 결정부터 다시 돕니다(같은 코드·같은 입력이라 다시 계산은 같은 일). 옮긴 것은 이어 하기 기록에 적고, S-K54의 "다시 씀"에 들지 않습니다. 판정 파일(`judge/*.json`)이 있으면 그 판정을 다시 하지 않습니다. 사슬 중간에서 다시 시작하면 직전 행동은 마지막 완전한 결정의 출력입니다. ZI 칸이 반쯤 되었으면 그 칸 폴더 전체를 옮기고 그 칸을 처음부터 다시 합니다.
- 커밋·브랜치·푸시 0(V-A 사용자 결정 뒤에만). VISSIM·COM·러너·동결 0. 금지 시험 0.

### 4.8 VerifyVB의 범위 (보충 31 §4.4에 더함)

- 도구는 새 파일, 첫 읽기 전 LOG 고정, V-B 구동기·재계산기·AD32 도구·하네스를 import하지 않습니다. 다만 "선언된 판정기가 무엇을 내는가"를 묻는 탐침은 KC를 import할 수 있고, 그 사실을 공개합니다(D-K9-64로 받아들인 선례 `vvb_b`).
- 다시 내는 것: VB-I1 판정 4결정(보충 21 §6 글로 따로 짠 N·HARD·D·허용, `vvb_a` 꼴), 보고 전용 10결정의 목록 밖 집합, VB-I2–VB-I7, ZI 세 칸의 (z2)–(z6), 고르기, VB-M 표. 다르면 STOP(S-K50).

---

## 5. 보고서 자리와 꼴

- **정본** = `KB/k92_vb/K92_VB_REPORT.md`(보충 31 §4.4). **사본** = `KB/VB_REPORT.md`, 정본과 **같은 바이트**(`cmp` 같음; 쓰고 나서 두 sha를 LOG에). 사본만 고치는 일은 없습니다. 고치면 정본을 고치고 다시 복사합니다.
- 머리: 보충 27 §8·§13, 보충 28 §9, 보충 29 §11, 보충 30 §10, 보충 31 §5·§9의 공개와 이 보충 §7·§11을 옮깁니다. 첫 줄 가까이에 §2.3의 "목록 밖 차이" 요약 문장을 둡니다.
- 본문: V0–V10 결과, ZI 표(칸마다 (z1)–(z7), 훅 비용), VB-I 표(VB-I1 판정 4결정, 보고 전용 10결정 표, VB-I2–VB-I7), VB-M1–M9 표(B1 사슬 대 RR 기록·OFF 사슬, 같은 T끼리, 사슬·시드끼리 더하지 않음 — 보충 24 §14.1 "무엇을 비교하나" 그대로), 고르기 상태 개수(SDMPC 결정의 `selected` 아닌 것 눈에 띄게), 한계(보충 24 §14.1 "한계"와 §11).
- 판정 말 없음. 결과는 PASS / FAIL / 보류 / INCOMPLETE / STOP, 숫자, 보고만.

---

## 6. 보충 24 :540 인용 고침

- 보충 24 §14.1 사슬 규칙 2(:540)의 "`.json.applied` 영수증 등, `sdmpc.py:461-470` 규칙"을 "`.json.applied` 영수증 등, `sdmpc.py:513-533`(`load_prices`; 영수증 점검 :519-528) 규칙"으로 읽습니다.
- 근거 [실행 VerifyVB, VB_PRECHECK_STOP r2 §5 끝]: 지금 블롭 `d21fdd49…`(FRZ_K8 74cd495f·FRZ_K8b b9734abe·e27ceac8 같음)에서 :461-470은 QP 풀이 코드이고, 영수증 규칙은 `load_prices` :513-533입니다. 옛 커밋 cd06a39a의 줄 번호로 보입니다 [추론]. 뜻(영수증 세 줄 규칙)은 같습니다. 이 보충 §4.4는 새 줄 번호로 적었습니다.
- 같은 옛 인용이 GWT8 `diagnostics/sdmpc_n31_20260924/tools/make_replay_state_v2.py` 머리말(:30 근처, "sdmpc.load_prices (sdmpc.py:461-470)")에도 있습니다 [읽음]. 코드 파일이라 고치지 않습니다(묶음 2 목록 후보, 공개 P10).
- 이 고침은 보충 24 파일의 바이트를 바꾸지 않습니다(고정판 그대로, 이 보충이 읽는 법을 정함).

---

## 7. 공개 (V-B 보고서 머리에 옮김)

- **P1 D-K9-62는 (나), 권장안 아님**: 사용자는 권장안 (가)(닫힌 잎에 조건을 단 좁은 허용, 보충 28 A28-W 꼴) 대신 (나)를 골랐습니다. 그래서 사슬 이어받는 OFF 10결정의 비교는 판정이 아니라 보고입니다. 직전 행동을 넘기는 사슬 기구의 옳음은 통과·실패로 묶이지 않습니다. 목록 밖 차이는 표와 문장으로 눈에 띄게 적습니다(§2.3).
- **P2 측정 훅(D-K9-63)**: 결정 프로세스(주로 탄젠트 작업자) 안에서 도는 새 읽기 전용 도구입니다. 무제어 결정에는 기록기 호출이 없을 것으로 봅니다(SDMPC 예측 없음). `on_alloc`은 부르지 않아 "수신 제한 스텝"은 측정하지 않습니다. 기록은 결정이 고른 행동과 서명이 같은 `omega_costs` 호출의 것이고(몫 가르기 규칙), 맞는 후보가 없거나 서로 다르면 그 결정의 VB-M5·M6·M8은 "없음"입니다. 지평은 3블록(450 s)으로 고정합니다.
- **P3 키 끔 쪽(메인 세션 처리)**: VB-M5·M6·M8의 키 끔 값은 OFF 사슬 14결정에서만 있고, VB-31·43·41의 T=3,300–4,500은 "없음"입니다. 추가 재생은 하지 않습니다.
- **P4 D-K9-64 수용**: (가) 검증 3차 — 도구 고정 전 작업 지시 글의 적용 보고 요약 노출, `OUTK/jb/sa/unit_k92t.meta.txt`·`steps.jsonl`의 `jb_unit` 줄 열람, 출력 꼴을 알려고 판정기·구동기·비교기 코드 열람, 넓은 트리 메타데이터 세기 `find` 하나를 시작했다가 멈춤(출력 0) [읽음 `VERIFY_GATES_K92B1_r3.md` 공개 (1)(2)]. (나) VerifyVB — 판정기 거동 탐침 `vvb_b.py`가 하네스 판정기 `k92_compare`를 import함(보충 31 §4.4 글과 다름), 독립 재계산 `vvb_a.py`는 import 0이고 같은 결과 [읽음 VB_PRECHECK_STOP r2 §7]. 둘 다 기록으로 받아들입니다.
- **P5 이 Declare 단계가 읽은 기록 자료**: §0.1의 목록(RR 영수증 다섯·CSV 크기, RR `decision_budget.json` 벽시계, RR 결정 폴더 파일 목록 일부, 몫 가르기 S1_A0h 훅 출력의 개수·키·첫 기록의 행동 녹색, OUTH 준비 기록 머리, 튜닝 `phase_price` 절). 몫 가르기 S1(v3c3-s43 T=3,750)은 V-B 결정(VB-43 T=3,750)과 같은 상태이지만, 읽은 것은 이미 보고된 몫 가르기 재생 출력이고 V-B 데이터가 아닙니다. 값은 `ATTRIBUTION.md`에 있던 것(첫 E2 기록의 SC109 녹색 등)을 화면에 한 번 띄운 것뿐입니다.
- **P6 VB-I7과 VB-I3 파일 sha**: VB-I7은 D-K9-62~64 글에 없는 새 STOP 점검입니다. 훅이 망가져 기록이 사라졌는데 모르는 일을 막으려는 것입니다. VB-I3에는 B1 팔 파일 sha가 이미 알려진 값(CFG-B1 `c8e3ee2c…`, SAF-B1 `65cac7ea…`)과 같다는 조건을 더했습니다. 둘 다 STOP을 늘리는 쪽입니다.
- **P7 VB-I1 D5 뿌리 점검의 꼴**: 보충 29 §6.2-2의 "D5 RS 키 뿌리 = 그 동결본인지 먼저 봄"을 "KC 보고의 A_K92 줄이 하나 이상, 모두 `ok`·`new_is_root_rs`·`old_is_root_rs` 참"으로 정했습니다(STOP을 늘리는 쪽).
- **P8 작업자 안의 모듈**: 기록기 `write`의 `npz` 압축이 작업자 프로세스에 표준 라이브러리 모듈(예: `zipfile`, `lzma`)을 더 실을 수 있습니다 [실행 합성: 24개]. 계산 결과에 영향이 있으면 ZI·VB-I1이 보입니다.
- **P9 영수증**: 오프라인 사슬의 `.applied` 영수증은 VISSIM 적용 없이 구동기가 러너와 같은 바이트 꼴로 씁니다. RR 기록에서는 실제 적용 뒤 러너가 썼습니다.
- **P10 옛 줄 번호**: 보충 24 :540과 `make_replay_state_v2.py` 머리말의 `sdmpc.py:461-470`(§6).
- **P11 결정 기록 근거 줄의 계수**: D-K9-62 근거 줄의 "미분류 2–13개"는 VB_PRECHECK_STOP §2.2 표의 HARD 밖 잎 수(무제어 2, 첫 SDMPC 11, SDMPC 13)입니다. 닫힌 목록은 이 잎들과 HARD 잎(1·1·3)을 함께 담습니다(§2.2).

---

## 8. STOP 규칙 (보충 24 §8·25 §9·26 §7·27 §11·28 §7·29 §8·30 §7·31 §6에 더함)

- **S-K51** ZI: 세 칸 가운데 하나라도 PASS가 아님, 준비·재생 실패, 훅 끔 실행에서 훅 파일 생김, 판정 파일을 만들지 못함 → 사슬 계산 0인 채로 STOP, 사용자가 정함(훅 고침은 사용자 결정 뒤에만).
- **S-K52** VB-I7 거짓(훅 무결성) → VB_INCOMPLETE → STOP.
- **S-K53** 고정 위반: 보충 32 고정점·`KB/a32_pins.sha256`·`KV/vb_pins.sha256` 대조 다름(시작·끝), LOG 고정 전에 ZI·사슬 계산을 함, 고정 뒤 훅·고르기·도움 함수·닫힌 목록·구동기·재계산기를 고침 → STOP(보충 24 S-K12와 같은 뜻).
- **S-K54** 쓰기·직전 행동 위반: §4.5-3 범위 밖에 씀(특히 RR·동결본·GWT8·봉인 뿌리·OUTK), `.sdmpc_pending` 없이 영수증을 씀, 영수증 바이트가 `receipt_bytes`와 다름, 사슬 이어받는 결정의 직전 행동이 같은 사슬·팔의 앞 결정 출력이 아님, 사슬 첫 결정의 직전 행동이 RR 파일이 아님, 준비 폴더·훅 폴더·기록 폴더를 다시 씀 → STOP.
- **S-K55** OFF 관문(V5): VB-I1 판정 4결정 가운데 하나라도 PASS가 아님, 또는 OFF 14결정의 VB-I2·VB-I7 거짓 → B1 사슬 전에 STOP(S-K15와 함께).
- 그대로: S-K11(스냅숏 다름·봉인 시드·쓰기 금지 뿌리), S-K12, S-K13(V-A 행동), S-K14(드라이브 8 GB), **S-K15**(VB_INCOMPLETE·구동기 자기 시험 거짓), S-K50(VerifyVB 다름). 보충 24–31의 나머지도 그대로입니다.
- **STOP이 아닌 것**: 보고 전용 10결정의 목록 밖 차이(D-K9-62), SDMPC 결정의 고르기 상태가 `selected`가 아님(눈에 띄게 보고), VB-M 값.

---

## 9. 보충 24–31이 바뀌는 곳 (그 밖은 그대로 구속)

| 자리 | 옛 내용 | 이 보충 | 근거 |
|---|---|---|---|
| 보충 24 §14.1 VB-I1(:547), 보충 27 §6.2-2·§7, 보충 29 §6.2-2 | OFF 14결정 모두 결과 넷 PASS여야 함 | 판정은 사슬 첫 결정 4개만(§2.1). 사슬 이어받는 10결정은 닫힌 목록을 뺀 보고만(§2.2·§2.3), STOP 없음 | D-K9-62 |
| 보충 24 §14.1 VB-M5·M6·M8(:560-563) "기록기가 결정 JSON만으로 낼 수 없는 값은 없음" | 결정 재생에는 기록기 없음 | 측정 훅이 결정마다 REC를 부름(§3), 고른 기록에서 읽음(§3.6), 키 끔 쪽은 OFF 14결정만 | D-K9-63, 메인 세션 처리 |
| 보충 24 §14.1 무결성 점검 | VB-I1–VB-I6 | + VB-I7 훅 무결성(§2.5); VB-I3에 B1 팔 파일 sha 조건(§2.4) | D-K9-63, P6 |
| 보충 24 §14.1 순서 | (정하지 않음) | V0–V10(§4.2): ZI → OFF 사슬 → OFF 관문 → B1 사슬 | D-K9-63 |
| 보충 24 §14.1-2(:540) 인용 | `sdmpc.py:461-470` | `sdmpc.py:513-533`(`load_prices`; 점검 :519-528) | 메인 세션 처리 |
| 보충 24 §14.1-2 영수증 | "러너 계약 짝 파일을 그 규칙대로 만들어" | VBS :1281-1287 규칙의 바이트 꼴(`receipt_bytes`), `.sdmpc_pending`이 있을 때만(§4.4) | 구체화 |
| 보충 24 §14.1 보고서(:522) | `KB/k92_vb/K92_VB_REPORT.md` | 정본 그대로 + 같은 바이트 사본 `KB/VB_REPORT.md`(§5) | 메인 세션 처리 |
| 보충 24 §14.1-4·보충 31 §4.4 구동기·재계산기 | 첫 사슬 계산 전 sha 고정 | + `KB/a32_pins.sha256`·`KV/vb_pins.sha256`, 자기 시험 항목(§4.5·§4.6), 고정 = ZI 전 | 구체화 |
| 보충 31 §4.4 VerifyVB | VB-I1–I6·VB-M 다시 냄 | + 보고 전용 10결정 목록 밖 집합, VB-I7, ZI, 고르기(§4.8) | D-K9-62·63 |

- 바꾸지 않는 것: 비교 규칙(보충 21 §6, 보충 24 §4.2, 보충 27·29), 결과 넷의 뜻, A_K92·A_K92-M·H5 선언 차이, R-CR, 트리 자리 닫힌 목록, 옛 뿌리 표, VB-I2–VB-I6의 뜻, VB-M1–M4·M7·M9 정의, V-B 사슬·상태·팔(보충 24 §14.1 표), 봉인·블라인드 규칙, 커밋 K9-2-0…5. 코드 변경 0. 푸시 0.

---

## 10. 고정 목록 (`AD32/a32_pins.expected.sha256`, 51줄)

- 기대 파일 sha256 `9e4dc5925e36fcc092f1b4ace4c3e86600d8f96422f3720653fe7d72d4514fcb`, 51줄, 10,356 B, LF, CR 0 [실행 `sha256sum -c` 51/51 OK]. 줄 꼴: `<sha256 64자> *<절대 경로, / 구분>`(보충 30 §9·31 §8과 같음). V-B 단계의 `KB/a32_pins.sha256`은 이 바이트와 같아야 합니다(반박 검토가 파일을 고치면 고정점 32가 새 기대 파일과 sha를 정함).
- **고정점 32가 적어야 하는 것**: 고정판 보충 32의 sha256(64자)과 기대 고정 목록의 sha256(64자). Declare 판 보충 32의 sha는 앞 16자만(보충 29 §14.1 V4와 같은 까닭: 되돌린 파일이 통과하지 않게).

| 줄 | 파일 | sha256 앞 16자 |
|---|---|---|
| 1 | `AD32/vbhook/sitecustomize.py`(측정 훅) | `4d7e0375116c3f80` |
| 2 | `AD32/vb_select.py`(고르기) | `33adfd5033c277a3` |
| 3 | `AD32/vb_lib32.py`(영수증·닫힌 목록·보고 전용·ZI 판정) | `504999a196a9e085` |
| 4 | `AD32/make_closed32.py`(닫힌 목록 만들기) | `20f058b7d195c4b8` |
| 5 | `AD32/vb_closed_leaves.json`(닫힌 잎 목록) | `b800be45ae3e4e50` |
| 6 | `AD32/dry_a32.py`(데이터 없는 확인) | `4215f7f8ed70d148` |
| 7–15 | `AD32/dry/decl/dry_a32_{static,closed,hook,select,receipt,reportonly,zi,mutants,summary}.json` | `b49a75f5…` / `dda98765…` / `32178e42…` / `e0efcc52…` / `53b18e4d…` / `d7e52e6c…` / `010969ca…` / `8364c98a…` / `172c1576…` |
| 16–21 | `KV/VB_PRECHECK_STOP.md`(r2) / `_r1.md` / `KV/verify/out/vvb_a_01.json` / `vvb_b_01.json` / `KV/dev/classify_out.json` / `KV/verify/vvb_pins.sha256` | §0 값 |
| 22 | `KB/k92_probe_a25/K92_VALUES.json` | `296c659562e45528` |
| 23–27 | `KB/GATES_K92B1_A31.md` / `KB/VERIFY_GATES_K92B1_r3.md` / `KB/GATES_K92B1.md` / `KB/a31_pins.sha256` / `KB/vgates4/out/vg4_result.json` | §0 값 |
| 28–31 | KI `k92lib.py` / `cglib.py` / `launch.ps1` / `k92snap.py` | §0 값 |
| 32–33 | `SP/j1/fix/gates/gprep.py` / `gcommon.py` | §0 값 |
| 34–35 | `SP/k92/attrib/hook/sitecustomize.py` / `SP/k92/attrib/METHOD.md`(선례) | §0 값 |
| 36–41 | GWT8 `k8_gates/sa/` `k92_compare.py` / `k92_record.py` / `k92_replay.py` / `sa_arms.py` / `k92_a27.py` / `k92_common.py` | `3e2da987…` / `1d1dfa36…` / `822dd78f…` / `578a8707…` / `d4ab3f3d…` / `cb2a0335…` |
| 42–44 | GWT8 `evaluation/controllers/sdmpc.py` / `scripts/run_real_world_stackelberg_controller.vbs` / `tools/make_replay_state_v2.py` | `8f91298a…` / `bffb59f8…` / `4adf41cf…` |
| 45 | FRZ_K8b `tools/make_replay_state_v2.py`(gprep이 쓰는 사본) | `4adf41cfa7569047` |
| 46–50 | RR 영수증: k8j1r_s31 `action_003000.json.applied` / k8j1_s43 `action_003000…` / k8j1_s41 `action_003000…` / k8j1_s41 `action_000900…` / k8j1_s41 `action_002850…` | `602f2a857c13546e` / `61983196eb59ef0e` / `f72c349e10bf0984` / `574dfdc1d5c96259` / `561652c695f41c12` |
| 51 | `OK2/snap/s37b_a32decl.json`(이 단계 스냅숏) | `765c287dacf5ab46` |

- 목록에 넣지 않는 것(창 안에서 바뀜): `KB/LOG.md`, 결정 기록(앞 204줄만 V0 C3), 보충 32 자신과 고정점(구동기가 따로 봄), VBR·VBT(V-B 출력), `KV/vb_pins.sha256`(V-B 단계가 씀, LOG 고정), `AD32/dry/syn`(합성 트리).
- **고정 창**: V-B 단계의 고정(§4.1)부터 V10 끝 대조까지. 그 안에서 51개 가운데 하나라도 바이트가 바뀌면 S-K53.

---

## 11. 알려진 사실·한계 (V-B 보고서 머리에 옮김)

1. **보고 전용 10결정**: 판정에서 빠집니다(P1). 그 결정들의 사슬 기구가 옳은지는 목록 밖 차이의 보고로만 보입니다.
2. **닫힌 목록의 근거 범위**: 목록은 RR 기록 열 결정에서 "직전 행동 경로를 담거나 직전 파일 sha와 같은 잎"을 찾은 결과입니다(VB_PRECHECK_STOP §2.2, 독립 재계산 `vvb_a` 같음). 사슬 출력이 기록과 다른 꼴이면(예: 미래 블록 수가 달라 `future[*]` 잎 수가 다름) 목록의 일반화 경로가 그 수와 무관하게 맞습니다. 목록 밖의 새 경로는 목록 밖으로 보입니다.
3. **훅이 재는 자리**: `omega_costs` 호출의 응답만입니다. 결정이 고른 행동과 서명이 같은 호출을 찾습니다. 같은 서명의 다른 미터·VSL 값 후보가 섞이면 `match_conflict`로 "없음"이 됩니다(서명은 녹색·오프셋·미래 녹색만 봄, 몫 가르기와 같음).
4. **측정하지 않는 칸**: `w_receiving_limited_steps`(P2), `vissim`.
5. **지평 3블록 고정**: 결정 롤아웃 블록 수가 3보다 적으면 그 블록의 값은 없음입니다(후보 `n_states`를 보고에 적음).
6. **ZI의 범위**: V-B 밖 두 상태·세 칸에서 훅 영향 0을 직접 봅니다. 그 밖의 결정에서 훅 영향 0은 같은 훅 코드라는 데서 미루어 봅니다 [추론]. 더해 VB-I1 판정 4결정은 훅을 켠 채 RR 기록과 결과 넷 PASS여야 합니다(§2.1).
7. **영수증은 적용한 셈 치는 것**(P9).
8. **D-K9-44 계속**: 어댑터는 결정마다 봉인 시드·v3c3-s47 이름 파일의 sha를 계산합니다(V-B 결정도 같음; 기록만, 고침은 묶음 2).
9. **CR 형태**: VBT는 C×10(FRZ_K8b 바이트)입니다. RR 기록 트리(FRZ_K8b `CCCCCCCCCC`, FRZ_K8 `CCCCCC---X`)와 R-CR이 맞습니다(보충 27 §6.2-1).
10. **벽시계**: 훅 부담은 ZI의 비로만 봅니다. V-B 결정 벽시계는 보충 24 §7-4대로 보고만 합니다.
11. 보충 24 §2.6의 한계 1–13, 보충 24 §14.1 "한계", 보충 25 §11, 보충 26 §10, 보충 27 §13, 보충 28 §9, 보충 29 §11, 보충 30 §10, 보충 31 §9는 그대로입니다.

---

## 12. 자체 점검

1. **빈 칸 없음**: "나중에 정함"·자리표가 없습니다. 아직 생기지 않은 값은 규칙으로 정했습니다: 보충 32 고정판 sha(고정점 32), `KB/a32_pins.sha256`(= 기대 파일 바이트), `KV/vb_pins.sha256`과 구동기·재계산기 sha(V-B 단계가 ZI 전에 LOG에), V-B 출력 sha(구동기가 LOG에), VerifyVB 도구 sha(첫 읽기 전 LOG).
2. **D-K9-62**: 판정 4결정과 규칙(§2.1), 보고 10결정과 결정 꼴(§2.2), 닫힌 목록 경로 단위 표 셋(§2.2, 기계 파일 `b800be45…`), 보고 전용 표가 보이는 것과 문장(§2.3), VB-I2–I6 그대로 55결정(§2.4), 공개 P1.
3. **D-K9-63**: 훅 파일·싣는 법·스위치(§3.1), 기록기 입구·인자(§3.2), 프로세스·횟수(§3.3), 결정마다 자리와 고르기(§3.4), ZI 상태(55결정 밖)·절차·선언 비교 규칙·STOP·비용 보고(§3.5), VB-M5·M6·M8 읽는 법과 키 끔 14결정(§3.6), 비용(§3.7).
4. **구동기·재계산기**: 할 일(§4.2–4.4), 고정 시점(§4.1, ZI 전), 합성 자기 시험(§4.5·§4.6), VerifyVB 범위(§4.8).
5. **보고서 자리**(§5)와 **:540 인용 고침**(§6).
6. **공개**(§7, D-K9-62 (나)·D-K9-64 수용 포함), **새 STOP**(§8 S-K51–S-K55), **고정 목록**(§10, 51줄).
7. **합성 확인만**: 새 도구는 합성 입력에서만 돌렸고(§3.8), 실제 자리는 RR 영수증 바이트·CSV 크기만 읽었습니다(영수증 꼴 확인). V-B 데이터 0.
8. 판정 말 없음.

---

## 13. 파일 (AD32 = `KB/a32decl`)

| 파일 | sha256 |
|---|---|
| `vbhook/sitecustomize.py`(측정 훅, 248줄, 11,471 B, LF) | `4d7e0375116c3f805aa223651da0dc1c0c04b7d3315062e98e21137ba60aa321` |
| `vb_select.py`(고르기, 220줄, 9,899 B) | `33adfd5033c277a3ad640f745a69efb2a929b27c1ff2a88d794dfa69b489e9cc` |
| `vb_lib32.py`(영수증·닫힌 목록·보고 전용·ZI, 165줄, 8,808 B) | `504999a196a9e08582f303d4ad38d4cc661fcfc765df62d11bc4cc7c05ddc75f` |
| `make_closed32.py`(닫힌 목록 만들기, 107줄) | `20f058b7d195c4b898def664567a5ca7c0db5e14545ca39bc8b6d27de3a34802` |
| `vb_closed_leaves.json`(닫힌 잎 목록, 314줄, 10,129 B) | `b800be45ae3e4e5030ed31ecd221e6288d52c2a287bdeaa5efee243e3cc2f426` |
| `dry_a32.py`(데이터 없는 확인) | `4215f7f8ed70d148c48ec999962d37068b961e07a715b0557737193a1b155fa3` |
| `dry/decl/dry_a32_static.json` | `b49a75f535b65c7a13bbea95b42d67a25a5223088e3a60a9bbed9f2ff67f63bc` |
| `dry/decl/dry_a32_closed.json` | `dda987658010285f6379bee45956f05e3760f068ecfdfddae153bb38bd74b981` |
| `dry/decl/dry_a32_hook.json` | `32178e422a3d09e53ff4d5ff254121b95d439b4f05406e1057bedb6db8119150` |
| `dry/decl/dry_a32_select.json` | `e0efcc527059e1887eb97a9fc465b359dd02cbf8fac60a350982a5f412b8a291` |
| `dry/decl/dry_a32_receipt.json` | `53b18e4dad67e8dfa981b18f89c62b967c395bf5d3ad282a2420f2a19ef40df0` |
| `dry/decl/dry_a32_reportonly.json` | `d7e52e6c391f3f648bccbec8ae254635c075eb9498ccc97ec29ad226286cb5c0` |
| `dry/decl/dry_a32_zi.json` | `010969ca841556a516d04760654cb57700ac6654f6f09bc0f1d6948d9ef04a2f` |
| `dry/decl/dry_a32_mutants.json` | `8364c98a34ab1a73f79fc4d8a2e89cb887cf660b6e0c526542aa1741ea6643fe` |
| `dry/decl/dry_a32_summary.json`(all_ok 참, BelowNormal 참) | `172c15761e06c71cf6a0a7103328524287b72facc75f5fe73e66a2fbd0b8ff23` |
| `a32_pins.expected.sha256`(51줄) | `9e4dc5925e36fcc092f1b4ace4c3e86600d8f96422f3720653fe7d72d4514fcb` |
| `dry/syn/`(합성 트리: 합성 프로그램·합성 `sdmpc`·합성 `Dual`·기록기 바이트 사본·훅 출력·망가뜨림 사본, 약 1 MB; 고정 목록 밖) | — |

- 새 도구·목록·확인 출력과 이 글은 줄 끝 LF, CR 0입니다 [실행].
