# V-B 사전 점검 STOP — 사슬 결정에서 VB-I1이 구조적으로 PASS가 될 수 없음 (2026-10-22)

- 상태: **STOP (사슬 계산 전, V-B 데이터 0개)**. 사용자 결정이 필요합니다.
- 판 r2 (VerifyVB 2026-10-22 04:29–04:42 KST): r1(`VB_PRECHECK_STOP_r1.md`, `e9a09758…`)의 숫자를 독립 도구로 다시 내 모두 같았고, 고친 곳은 §8 바뀐 곳 표에 있습니다. VerifyVB 기록은 §7입니다. 결론(STOP, Q1–Q3)은 바뀌지 않았습니다.
- 표시: [실행] 명령·작은 스크립트로 확인, [읽음] 문서·코드에서 확인, [추론] 시험하지 않은 판단.
- 줄임말(처음 한 번): SP = 세션 스크래치 `.../scratchpad/k8`, KB = `SP/k92/bundle1`, GWT8 = `D:/VISSIM-merge/sim3-n31-k8`, RR = `D:/VISSIM_runs/20261004_sdmpc31_k8`(J1 기록 런), OK2 = `D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1`, TK = `D:/VISSIM-merge/k8_gate_trees/k92b1`, ADP = `evaluation/controllers/vissim_stackelberg_adapter.py`, HARD = 보충 21 §6.2의 "딱 같아야 하는 잎" 집합, N = 비교 전 경로 정규화(보충 21 §6.1, 보충 27·29로 고침).
- 이 보고는 판정 말을 쓰지 않습니다. V-B를 돌리지 않았으므로 V-B 결과 표는 없습니다.

## 0. 한 줄 요약

사슬은 둘째 결정부터 "앞 사슬 출력"을 직전 행동으로 넘깁니다. 어댑터는 그 직전 행동 파일의 **자리(경로)와 바이트 sha**를 출력 잎에 적고, 그중 일부는 HARD 안에 있습니다. RR은 읽기 전용이라 사슬 파일 자리는 RR과 다를 수밖에 없고, N은 그 자리를 RR 자리와 같게 바꾸지 않습니다. 그래서 키 끔(OFF) 사슬 14결정 중 10결정은 사슬 기구가 완벽해도 VB-I1 결과가 FAIL(HARD 다름)이 됩니다. 데이터 없이 정해지는 결과이므로 사슬 계산 전에 멈췄습니다.

## 1. 한 일과 하지 않은 일

한 일 [실행 2026-10-22 KST]
- 보충 24–31 파일 sha256 = `.sha256` = 고정점 `KB/AMENDMENT{24..31}_FIXED.md` 안 값(8개 모두 일치). 보충 31 `8541ccb7…`, 결정 기록 `SP/K9_1_J1_NOTES_20261013.md` `09974cfc…`.
- GWT8 head `e27ceac8`(K9-2-5), `git status --porcelain` 0줄. `TK/vb_*`·`OK2/vb*` 없음. C: 40 GB, D: 388 GB 여유.
- LOG 끝 기록: VerifyGates 3(독립 검증 A31) PASS(LOG 2026-10-22 04:06 항목) → 보충 31 §4.4의 K92_GATES_PASS 조건이 채워졌고 V-B가 다음 순서 [읽음].
- V-B 정의 읽기: 보충 24 §14.1(:511-576), 보충 27 §6.2(:386-390)·§7 표(:417), 보충 29 §6.2(:388-392), 보충 31 §4.4(:376-381) [읽음].
- 재생 경로 읽기: `tools/replay_decision_n31.ps1`, `tools/make_replay_state_v2.py`, `k8_gates/sa/k92_replay.py`, 어댑터의 직전 행동 읽기 자리 [읽음, 줄 번호는 e27ceac8 기준].
- 개발용 탐침 4개(판정 도구 아님, 고정 대상 아님)로 **RR 기록 파일만** 읽음: 경로·규칙 이름·계수만 출력, 목적값·예측값 출력 0 [실행, §6 sha].

하지 않은 일
- V-B 트리 `TK/vb_e27ceac8` 만들기, 구동기 `KB/k92_vb/vb_chain.py`·재계산기 작성과 sha 고정, OFF·B1 사슬 계산(0결정), `OK2/vb/` 만들기.
- 커밋·브랜치·푸시, VISSIM·COM·러너·동결, 금지 시험, 봉인 시드·codex 64cf 열람: 모두 0.

## 2. 찾은 것 V-B-D1: VB-I1이 사슬 결정에서 FAIL로 정해짐

### 2.1 어댑터가 직전 행동 파일의 자리와 바이트를 적는 곳 [읽음]

- `sdmpc.load_prices`(sdmpc.py:513-533): 직전 행동 옆 `.applied` 영수증을 읽고, 영수증 2째 줄이 **직전 CSV의 절대 경로**여야 받습니다(:523-528). 결과 `{'source': 영수증 경로, 'receipt_sha256': 영수증 바이트 sha}`가 `metadata.sdmpc_state.previous_application`과 `metadata.joint_leader_selection.price_state.previous_application`에 들어갑니다.
- `prediction_error_from_previous`(ADP:11084-11134): `source_action_json` = 직전 행동 경로.
- `lane_plant_runtime.applied_vsl_from_previous`(:650-673): `source` = 직전 행동 경로, `sha256` = 직전 행동 JSON 바이트 sha → `metadata.n31_binding.vsl_cohort_initialization`.
- `load_joint_historical_reference`(ADP:13051-13094 [r2 고침: 함수 끝 `return`이 :13094]): 직전 CSV 경로·sha → `diagnostics.physical_ramp_recorded_csv`(그리고 예측 순서·웜 예산 하위 트리의 사본들). [r2 보탬] 이 경로·sha를 처음 적는 곳은 `physical_ramp_branches.read_recorded_control`(physical_ramp_branches.py:350, :368: `Path(직전 행동).with_suffix('.csv')`)이고, ADP:13085는 그것을 `meter_anchor`로 옮깁니다 [읽음].

### 2.2 기록 런에서 그 잎들과, K9-2-5 판정기 규칙으로 분류한 결과 [실행 `KB/k92_vb/dev/classify.py`]

RR v3c3-s41 기록 결정에서, 값이 직전 행동 경로를 담거나 직전 JSON·CSV·영수증 바이트 sha와 같은 잎을 모두 찾고, GWT8 e27ceac8의 `k92_compare.in_hard`·`d_rule`·`r3_item`·`V`로 분류했습니다(비교 실행 아님, 규칙 함수만).

| 결정 꼴 (예) | 잎 수 | 사슬에서 반드시 다른 잎 | 그중 HARD | HARD 밖(허용 밖 → 미분류) |
|---|---|---|---|---|
| 무제어 ← 무제어 (T=150 ← 1, T=300 ← 150) | 3 | 3 | 1: `/prediction_error/source_action_json` | 2: `vsl_cohort_initialization/source`(경로), `…/sha256`(D2b) |
| 첫 SDMPC ← 무제어 (T=900 ← 750) | 21 | 12 | 1: 위와 같음 | 11: 경로 잎 9개(`physical_ramp_recorded_csv/path` 본체·예측 순서·웜 예산 사본), `vsl_cohort_initialization/source`·`/sha256` |
| SDMPC ← SDMPC (T=1050 ← 900, T=3150 ← 3000) | 25 | 16 | **3**: `/prediction_error/source_action_json`, `/metadata/sdmpc_state/previous_application/source`, `/metadata/sdmpc_state/previous_application/receipt_sha256` | 13: 위 11 + `price_state/previous_application/source`(경로), `…/receipt_sha256`(D2) |

- CSV sha 잎(`…/physical_ramp_recorded_csv/sha256`, D2)은 사슬 앞 결정의 CSV가 기록과 바이트 같으면 같으므로 "반드시 다른 잎"에서 뺐습니다.
- 결정 폴더 이름을 담은 다른 잎은 상태 경로(V 두 줄)뿐이었습니다(T=300, T=3150) [실행 `dirleaves.py`]. 그래서 위 목록이 사슬 때문에 생기는 차이의 전부로 보입니다 [추론: 기록 한 런·다섯 결정에서 본 것].
- [r2 VerifyVB] 독립 도구 `verify/vvb_a.py`(GWT8·dev 탐침·하네스 import 0; 보충 21 §6 글로 N·HARD·D를 다시 짬)로 **세 런의 사슬 결정 10개 전부**(VB-31·43·41 T=3,150, VB-41w T=150–1,050)를 다시 셌습니다 [실행 `verify/out/vvb_a_01.json` `618b9592…`]. 결정 꼴마다 위 표와 같습니다: 무제어←무제어 다섯 결정 모두 3/3/HARD 1, 첫 SDMPC(T=900) 21/12/HARD 1, SDMPC←SDMPC 넷(T=1,050 ×1, T=3,150 ×3) 모두 25/16/HARD 3. 다섯 결정에서는 dev 결과(`classify_out.json`)와 잎 경로 집합까지 같습니다. 더 본 것: 직전 행동 경로를 담은 **사전 키는 0개**, 직전 파일 10종(.json·.csv·.json.applied·.joint.json 등) 가운데 출력 잎에 sha가 나오는 것은 .json·.csv·.json.applied 셋뿐, 결정 폴더를 담은 나머지 문자열은 결정마다 2개(상태 경로 V 두 줄; T=150에서 이름 확인). 그래서 "열 결정 모두 같은 목록"은 이제 [실행]입니다.

### 2.3 왜 피할 수 없는가

1. **자리**: 보충 24 §14.1은 RR·동결본 쓰기를 금하고 출력은 `OK2/vb/`입니다(:522). 사슬 직전 행동 파일은 `OK2/vb/…` 아래에 있게 됩니다. N(`k92_compare.py` `N2`)은 `d:/vissim_runs/20261004_sdmpc31_k8/sdmpc31_v3c3_k8j1*_s*`만 `<run>`으로 바꾸고 OK2 아래 경로는 그대로 둡니다. 그래서 경로 잎이 N 뒤에도 다릅니다 [읽음·실행]. [r2 다듬음] 정확히는 N2가 `<run>`으로 바꾸는 것은 RR 런과 NC 런(`20261001_sdmpc31_v3c3/sdmpc31_v3c3_nc_s*`) 둘이고, `reports/k8/offline_gates*/…/t<6자리>`는 `<bundle>`입니다. `reports/k8/k92_b1/…`(OK2)에 맞는 규칙은 없습니다(k92_compare.py:52-62) [읽음]. 독립 N(보충 21 §6.1 글)으로도 RR 직전 행동은 `<run>/decisions_<name>/action_003000.json`, OK2/vb 자리는 그대로여서 같지 않습니다 [실행 `vvb_a_01.json` `n_location`].
2. **영수증**: `load_prices`는 영수증 2째 줄 = 직전 CSV 실제 경로를 요구합니다(sdmpc.py:525). 사슬 영수증은 사슬 CSV 경로를 담아야 하므로 바이트가 RR 영수증과 다르고, `receipt_sha256`(HARD H4 안)이 다릅니다.
3. **JSON 바이트**: 사슬 앞 결정의 JSON은 기록과 바이트가 다릅니다(상태 경로 V 잎, 벽시계 잎). 그래서 `vsl_cohort_initialization/sha256`(D2b, 허용에서 빠짐)이 다릅니다.
4. 보충 27 §6.2-2·보충 29 §6.2-2의 VB-I1 통과 = 결과 넷의 PASS(HARD 같음 + 미분류 0). 허용은 G-K0와 같고(D-a·D-d), 직전 행동 자리 차이를 받는 허용은 없습니다 [읽음 보충 24 :547, 보충 21 §6.4].
5. [r2 보탬] 보충 24 :547의 원래 글("HARD 같음"만, 보충 27이 결과 넷으로 넓히기 전)로 읽어도 결과는 같습니다. 열 결정 모두 HARD 안에 반드시 다른 잎이 1개 이상 있기 때문입니다 [실행 `vvb_a_01.json`]. 그래서 이 결함은 보충 27의 고침에서 온 것이 아닙니다.
6. [r2 보탬] 영수증 꼴 [실행 `vvb_a_01.json` `receipts`]: 사슬 SDMPC←SDMPC 결정의 직전 RR 영수증 4개(VB-31·43·41 T=3,000, VB-41w T=900)는 모두 3줄이고, 1째 줄 = 직전 T, 2째 줄 = RR CSV 경로, 3째 줄 = CSV 크기입니다. 그래서 사슬 영수증의 2째 줄은 사슬 CSV 경로여야 하고 바이트가 RR과 달라집니다.

**결과 [추론, 규칙 함수로 확인; r2: 판정기 거동 탐침으로 실행 확인, 아래 표]**: OFF 14결정 가운데 사슬 앞 출력을 직전 행동으로 받는 10결정 — VB-31·VB-43·VB-41의 T=3,150(셋), VB-41w의 T=150·300·450·600·750·900·1,050(일곱) — 은 FAIL입니다. 사슬 첫 결정 4개(T=3,000 ×3, VB-41w T=1)는 직전 행동이 RR 파일 그대로라 G-K0 D-d·D-a와 같은 조건입니다. VB-I1 하나라도 거짓 → VB_INCOMPLETE → STOP(S-K15)이므로, 그대로 돌리면 약 2시간 계산 뒤 반드시 멈추고, 그 뒤의 고침은 "데이터를 본 뒤"가 됩니다. 그래서 지금 멈췄습니다.

**[r2 VerifyVB] 판정기 거동 탐침** [실행 `verify/vvb_b.py` → `verify/out/vvb_b_01.json` `e0d5537b…`]: 선언된 VB-I1 판정기(GWT8 K9-2-5 `k92_compare.compare`, sha256 `3e2da987…`)에 RR 기록 사본을 넣었습니다. 사본은 직전 행동 자리·영수증·JSON sha 잎**만** 바꾼 합성 출력입니다(어댑터·재생 0, V-B 데이터 아님). 열 결정 × 네 꼴 = 40번 판정했습니다.

| 꼴 | 무제어←무제어 (5) | 첫 SDMPC T=900 (1) | SDMPC←SDMPC (4) |
|---|---|---|---|
| ctrl: 바꾸지 않은 바이트 사본 | PASS ×5 | PASS | PASS ×4 |
| pathonly: 경로만 OK2/vb로 | FAIL (HARD `/prediction_error/source_action_json`) | FAIL (같은 HARD 1) | FAIL (HARD 2: 위 + `sdmpc_state/previous_application/source`) |
| chain: 경로 + JSON·영수증 sha | FAIL, 미분류 2 | FAIL, 미분류 11 | FAIL (HARD 3 = §2.2 표), 미분류 13 |
| rrsib: N이 `<run>`으로 바꾸는 RR 옆 가상 자리 + sha (쓰기 금지 자리, 문자열로만) | 보류 (HARD 같음, 미분류 1: `vsl_cohort_initialization/sha256` D2b) | 보류 (같은 미분류 1) | FAIL (HARD `sdmpc_state/previous_application/receipt_sha256`; 미분류 2: `price_state/…/receipt_sha256` D2, `vsl…/sha256` D2b) |

- 판정기가 내는 HARD 경로·미분류 경로는 §2.2 표·`vvb_a`의 목록과 같습니다. 허용으로 빠진 잎은 0입니다.
- 뜻 [추론]: 자리를 N으로 맞추는 고침만으로는 모자랍니다(rrsib에서도 보류·FAIL). 영수증 sha(HARD 1·D2 1)와 직전 JSON sha(D2b 1)는 바이트가 반드시 다르므로, Q1 (가)처럼 이 세 잎에도 조건을 다는 허용이 필요합니다(r1 §5 (가)가 이미 이 셋을 담음).

## 3. 둘째 빈칸 V-B-D2: 사슬 결정의 `k92_record.json`을 만드는 길이 정의되지 않음

- VB-M5(174 사슬 재고·용량 묶임 비율·`SC109_E_out`/220), VB-M6(OUTW·FEED-4), VB-M8(유령 재고)과 VB-I5 재계산은 `k92_record.json`을 씁니다(보충 24 :551, :560-563) [읽음].
- 그 기록기는 하네스 plant 잡(`sa_worker.py`)의 수동 기록기입니다: `k92_record.py:1-17` "passive plant-job record", 부르는 자리 `sa_worker.py:75`, `:744`(`K92R.collect`), `:1144`. plant 잡은 포착한 요청 틀에서 REFERENCE·세 블록 계획·미터 행동을 굴립니다(`sa_worker.py:1-25`) [읽음].
- 결정 재생(`k92_replay.py`, `replay_decision_n31.ps1`)은 이 파일을 만들지 않습니다 [읽음]. 보충 24 :560은 "기록기가 결정 JSON만으로 낼 수 없는 값은 '없음'"이라고만 적어, 글대로면 VB-M5·M6·M8이 모두 "없음"이 될 수 있습니다 [추론].
- [r2 VerifyVB] 확인 [실행 grep]: GWT8에서 `k92_record`를 부르는 곳은 `k92_gates.py`·`sa_worker.py`·`tests/test_k92_harness.py`뿐이고 `tools/`·`k92_replay.py`에는 없습니다. 보충 24 :89도 "하네스 새 기록 … `k92_record.json`에만"입니다. [r2 다듬음, 추론] VB-M5의 "할당 키가 있는 결정 수"는 결정 JSON의 키 유무로 셀 수 있어 "없음"이 아닐 수 있습니다. 그래서 "모두 없음"은 VB-M5 가운데 기록기 값(174 사슬 재고·묶임 비율·`SC109_E_out`/220), VB-M6, VB-M8에 해당합니다.

## 4. 기록 런 사실 (사슬 데이터 아님) [실행 `rrflags.py`]

V-B 41결정 시각의 RR 기록(키 끔)에서:

| 사슬 | 런 | 결정 | status | `head_observation_prior_discarded` | `head_observation_snapshot_sec` | hold 파일 | (173, p4) 하한 키 |
|---|---|---|---|---|---|---|---|
| VB-31 | `sdmpc31_v3c3_k8j1r_s31` | 3,000–4,500 (11) | 모두 ok | 모두 0.0 | 모두 = T | 0 | 결정마다 1 |
| VB-43 | `sdmpc31_v3c3_k8j1_s43` | 3,000–4,500 (11) | 모두 ok | 모두 0.0 | 모두 = T | 0 | 결정마다 1 |
| VB-41 | `sdmpc31_v3c3_k8j1_s41` | 3,000–4,500 (11) | 모두 ok | 모두 0.0 | 모두 = T | 0 | 0 (대조 — "하한이 끝내 없던" 런과 맞음) |
| VB-41w | `sdmpc31_v3c3_k8j1_s41` | 1, 150–1,050 (8) | 모두 ok | 모두 0.0 | 모두 = T | 0 | 0 |

- 기록 쪽에는 VB-I2·VB-I6을 미리 막는 구조 문제가 보이지 않습니다. `sdmpc_active`는 T ≥ 900에서 참, 그 앞은 없음.
- [r2 VerifyVB] 위 표 전부를 독립 도구로 다시 냈고 같습니다 [실행 `vvb_a_01.json` `C`]: 41결정 `controller_status` 모두 `ok`, `head_observation_prior_discarded` 모두 0.0, `head_observation_snapshot_sec` = T 모두 참, (173, p4) 하한 키 VB-31·VB-43 결정마다 1·VB-41·VB-41w 0, `exception`이 든 메타 키 0, 이름에 `hold`가 든 파일 세 결정 폴더 모두 0(r1은 `*.hold.json`만 셈; 넓혀도 0), `sdmpc_active` VB-41w T=1–750 없음·900·1,050 참, 창 결정 모두 참.

## 5. 사용자가 정할 것

**Q1. VB-I1을 어떻게 고칠까요?** (보충 32 후보; 데이터 전)
- (가) **좁은 허용 A_VB** [추론, 권장 후보]: §2.2 표의 닫힌 잎 목록에만, 사슬 앞 출력을 받은 OFF 결정에서만 허용. 조건: 경로 잎은 새 쪽 = 구동기가 넘긴 사슬 직전 파일의 실제 경로, 옛 쪽 = RR 기록 직전 파일 경로, 파일 이름 같음; `receipt_sha256` 두 자리는 새 쪽 = 구동기가 만든 영수증 바이트 sha이고 그 영수증 1·3째 줄(시각·CSV 크기)이 RR 영수증과 같고 2째 줄 = 사슬 CSV 경로; `vsl_cohort_initialization/sha256`은 새 쪽 = 사슬 직전 JSON 바이트 sha, 옛 쪽 = RR 직전 JSON 바이트 sha. CSV sha 잎은 허용 없음(같아야 함). 그 밖은 결과 넷 그대로. 보충 28 A28-W와 같은 꼴입니다.
- (나) 사슬 결정은 위 잎을 뺀 HARD 비교로 보고만 하고, 통과·실패는 첫 결정 4개로만.
- (다) VB-I1을 사슬 첫 결정만으로 줄임(사슬 기구 시험이 빠짐).

**Q2. VB-M5·M6·M8과 VB-I5의 `k92_record.json`은?**
- (가) 사슬 결정마다 측정 훅으로 `k92_record.collect`를 부름(새 도구; 결정 출력 바이트 영향 0을 먼저 보여야 함).
- (나) 사슬 상태마다 하네스 포착 + plant 잡(행동 = 사슬 출력)을 새로 정의.
- (다) 보충 24 :560 글대로 "없음"으로 적음.

**Q3. 보고서 자리**: 보충 31 §4.4는 `KB/k92_vb/K92_VB_REPORT.md`, 작업 지시는 `KB/VB_REPORT.md`입니다. 두 자리에 같은 바이트로 쓸지 정해 주세요.

- 비용 [추론]: 고친 뒤 55결정 ≈ 8–9 h(보충 24 :577 비용 줄; 그 줄은 `no-control` 예열 결정이 더 짧을 수 있다고 적음) [r2 고침: r1 "7–9 h"는 인용한 줄과 달랐음]. Q2 (가)(나)면 더 듭니다.
- [r2 보탬] **보충 24 :540의 줄 번호**: 사슬 규칙 2는 영수증 규칙을 "`sdmpc.py:461-470` 규칙"이라 적었습니다. GWT8 e27ceac8의 sdmpc.py(블롭 `d21fdd49…`, FRZ_K8 74cd495f·FRZ_K8b b9734abe와 같은 블롭)에서 :461-470은 QP 풀이 코드이고, 영수증 규칙은 `load_prices` :513-533(영수증 점검 :519-528)입니다 [실행 `git show`]. 옛 커밋 cd06a39a에서는 `load_prices`가 :455에서 시작해 :461-470이 그 안에 듭니다. 그래서 옛 판의 줄 번호를 옮긴 것으로 보입니다 [추론]. 뜻(영수증 3줄 규칙)은 같고, 보충 32를 쓰면 줄 번호를 바로잡는 것이 좋겠습니다. (V-B 반환 글의 열린 항목은 이것을 ":550"이라 적었는데, 줄은 :540입니다.)

## 6. 이 단계가 쓴 파일

| 파일 | sha256 | 뜻 |
|---|---|---|
| `KB/k92_vb/dev/prevleaves.py` | `d42343f7acce54801434bf717b4ce3749e145199c6ba877a20acdf756e344e96` | 기록 결정에서 직전 행동 경로·sha 잎 찾기(경로만 출력) |
| `KB/k92_vb/dev/classify.py` | `18a1e4620da26bb361ac16428414804fb149225081d66fbd182e2477aa998f32` | 같은 잎을 K9-2-5 `k92_compare` 규칙 함수로 분류(GWT8에서 import, 쓰기 0) |
| `KB/k92_vb/dev/classify_out.json` | `eda96865db22fb67165c5fa4a3569954962934405e9e17af389eeba78e9c1ea6` | 위 결과(경로·규칙 이름만) |
| `KB/k92_vb/dev/dirleaves.py` | `1c4003088ee83e28f7184eee1c924c182328fd36a40b0fbae65641911a964ad0` | 결정 폴더 이름을 담은 잎 목록 |
| `KB/k92_vb/dev/rrflags.py` | `a031c6457238c647303b338b71011a2838b6770c9135065c407275a55936bc9c` | RR 기록 계수·표지(§4) |

- 모두 개발용 탐침입니다. V-B 구동기·재계산기가 아니고, 판정에 쓰지 않습니다. 읽은 것은 RR 기록 결정 JSON·영수증·CSV(J1 런, 블라인드 아님)와 GWT8 코드뿐입니다.

## 7. VerifyVB 기록 (r2, 2026-10-22 04:29–04:42 KST)

- 대상: 이 보고 r1. V-B 사슬 출력·`VB_REPORT.md`·`K92_VB_REPORT.md`·`OK2/vb`·`TK/vb_*`는 없습니다 [실행]. 그래서 보충 31 §4.4의 VerifyVB 본뜻(VB-I1–I6·VB-M 표를 V-B 출력에서 다시 냄)은 할 대상이 없고, 대신 r1의 사실·숫자·논리를 다시 냈습니다.
- 도구 고정(첫 실행 전, LOG 2026-10-22 04:29 항목): `verify/vvb_pins.sha256` `1415cc7f…` = `vvb_a.py` `b3e62b1f…`, `vvb_b.py` `ea352627…`, `vvb_launch.ps1` `2be8b445…`. 실행은 모두 WMI 분리·BELOW_NORMAL·PYTHONHASHSEED=0·`python -B`, 한 번에 하나(`verify/out/wmi_launch_lines.txt`).
- 다시 낸 것과 결과:
  1. 보충 24–31 sha = `.sha256` = 고정점 8개 모두 같음, 결정 기록 `09974cfc…`, GWT8 head `e27ceac8`·status 0줄·K8 `b9734abe`·원격 k92 0 [실행]. 같음.
  2. §2.1 코드 자리 4곳과 줄 번호 [읽음]: 같음(ADP 끝 줄 :13094만 고침).
  3. §2.2 잎 표 [실행 `vvb_a_01.json` `618b9592…`]: 열 결정 모두 같음, dev 다섯 결정과 경로 집합까지 같음.
  4. §2.3 결과(열 결정 FAIL) [실행 `vvb_b_01.json` `e0d5537b…`]: 판정기 자체가 FAIL을 냄. ctrl 10/10 PASS로 탐침 틀이 공정함을 보임.
  5. §3 기록기 자리 [실행 grep]: 같음.
  6. §4 표 [실행 `vvb_a_01.json`]: 같음.
  7. VB-I1 결정 수 14·사슬 10·첫 결정 4, VB-I4 합 55 = B1 41 + OFF 14 [실행 `vvb_a_01.json` `counts`]: 같음.
- 재현: `vvb_a.py`를 따로 다시 돌린 `vvb_a_02.json`이 `vvb_a_01.json`과 바이트가 같습니다(둘 다 `618b9592…`, 화면 기록도 같음 `e235b6f8…`) [실행 `cmp`]. **사슬 한 토막을 다시 돌려 비트 같음을 보는 일은 하지 않았습니다.** 사슬 출력이 0개이고, 지금 사슬을 돌리면 보충 32 전에 V-B 데이터를 만드는 것이기 때문입니다.
- RR 읽기 전용: 결정 폴더 3개 목록(`ls -l --time-style=full-iso`) sha256 앞·뒤 모두 `db86b508…`(645파일씩). RR 위에 새 폴더 0. 합성 사본 폴더 `verify/syn_b_01`(CSV·진행 기록 사본 60개, 1 MB)은 판정 뒤 지웠습니다(합성 JSON은 비교마다 지우고 sha만 `vvb_b_01.json`에).
- 공개:
  - (1) `vvb_b.py`는 하네스 파일인 판정기 `k92_compare`를 import합니다. 보충 31 §4.4 글("하네스를 import하지 않음")과 다릅니다. 이 탐침은 V-B 출력의 재계산이 아니라 "선언된 판정기가 무엇을 내는가"를 묻는 것이라 판정기를 부를 수밖에 없습니다. 독립 재계산은 `vvb_a.py`(import 0)가 맡았고, 두 결과가 같습니다.
  - (2) 고정 전에 읽은 것: r1 보고, LOG 끝, dev 탐침 4개 소스(출력 `classify_out.json`은 고정 뒤에 읽음), 보충 21 §6·24 §14.1, GWT8 코드, RR 파일 이름·크기, T=150 한 결정의 상태 경로 이름(고정 뒤).
  - (3) 블라인드: 도구는 경로·규칙 이름·계수·sha만 냅니다. 목적값·예측값·용량 값 출력 0. 봉인 시드·codex 64cf·봉인 뿌리 접근 0.
- 지킨 것: VISSIM·COM·러너·동결·재생·어댑터 실행 0, 커밋·브랜치·푸시 0, 금지 시험 0, 끈 프로세스 0.

## 8. 바뀐 곳 (r1 `e9a09758…` → r2)

| # | 자리 | r1 | r2 | 까닭 |
|---|---|---|---|---|
| 1 | 머리 | – | 판 r2 줄 | VerifyVB 고침 표시 |
| 2 | §2.1 넷째 줄 | ADP:13051-13093 | ADP:13051-13094 + 경로를 처음 적는 곳(physical_ramp_branches.py:350, :368) | 함수 끝 줄; 출처 보탬 |
| 3 | §2.2 끝 | 한 런·다섯 결정 [추론] | 세 런·열 결정 [실행], 사전 키 0, 다른 직전 파일 sha 0 | 독립 재계산으로 넓힘 |
| 4 | §2.3-1 | "N2는 RR 런만 `<run>`" | NC 런·`<bundle>` 규칙도 적음, 줄 :52-62, 독립 N 결과 | 정확도 |
| 5 | §2.3-5·6 | – | 원래 글(HARD만)로도 FAIL; 영수증 꼴 사실 | 결함이 보충 27에서 오지 않음을 보임 |
| 6 | §2.3 끝 | 규칙 함수로 확인 | 판정기 거동 탐침 표(40번) | 판정기 자체 결과 |
| 7 | §3 | "모두 없음" | grep 확인 + VB-M5 "할당 키가 있는 결정 수"는 결정 JSON에서 셀 수 있음 [추론] | 정확도 |
| 8 | §4 | rrflags 결과 | 독립 재계산 같음, hold 이름 검사를 넓혀도 0 | 재계산 |
| 9 | §5 비용 | ≈ 7–9 h | ≈ 8–9 h (보충 24 :577) | 인용한 줄과 맞춤 |
| 10 | §5 끝 | – | 보충 24 :540 `sdmpc.py:461-470` 줄 번호가 지금 코드와 다름(옛 cd06a39a 꼴로 보임); V-B 반환 글의 ":550"은 :540 | 사실 정정 |
| 11 | §7·§8 | – | VerifyVB 기록·이 표 | – |

- 결론(STOP, V-B-D1·V-B-D2, Q1–Q3)은 바뀌지 않았습니다. r1의 숫자 가운데 틀린 것은 0개입니다. 고친 것은 줄 번호 1개, 비용 인용 1개, 설명 다듬음입니다.
- V-B 반환 글의 요약 "dev 탐침 5개"는 탐침 4개 + 출력 1개입니다(이 보고 §1·§6은 바름).
