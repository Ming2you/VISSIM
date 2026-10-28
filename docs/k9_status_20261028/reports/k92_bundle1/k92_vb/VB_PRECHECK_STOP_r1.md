# V-B 사전 점검 STOP — 사슬 결정에서 VB-I1이 구조적으로 PASS가 될 수 없음 (2026-10-22)

- 상태: **STOP (사슬 계산 전, V-B 데이터 0개)**. 사용자 결정이 필요합니다.
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
- `load_joint_historical_reference`(ADP:13051-13093): 직전 CSV 경로·sha → `diagnostics.physical_ramp_recorded_csv`(그리고 예측 순서·웜 예산 하위 트리의 사본들).

### 2.2 기록 런에서 그 잎들과, K9-2-5 판정기 규칙으로 분류한 결과 [실행 `KB/k92_vb/dev/classify.py`]

RR v3c3-s41 기록 결정에서, 값이 직전 행동 경로를 담거나 직전 JSON·CSV·영수증 바이트 sha와 같은 잎을 모두 찾고, GWT8 e27ceac8의 `k92_compare.in_hard`·`d_rule`·`r3_item`·`V`로 분류했습니다(비교 실행 아님, 규칙 함수만).

| 결정 꼴 (예) | 잎 수 | 사슬에서 반드시 다른 잎 | 그중 HARD | HARD 밖(허용 밖 → 미분류) |
|---|---|---|---|---|
| 무제어 ← 무제어 (T=150 ← 1, T=300 ← 150) | 3 | 3 | 1: `/prediction_error/source_action_json` | 2: `vsl_cohort_initialization/source`(경로), `…/sha256`(D2b) |
| 첫 SDMPC ← 무제어 (T=900 ← 750) | 21 | 12 | 1: 위와 같음 | 11: 경로 잎 9개(`physical_ramp_recorded_csv/path` 본체·예측 순서·웜 예산 사본), `vsl_cohort_initialization/source`·`/sha256` |
| SDMPC ← SDMPC (T=1050 ← 900, T=3150 ← 3000) | 25 | 16 | **3**: `/prediction_error/source_action_json`, `/metadata/sdmpc_state/previous_application/source`, `/metadata/sdmpc_state/previous_application/receipt_sha256` | 13: 위 11 + `price_state/previous_application/source`(경로), `…/receipt_sha256`(D2) |

- CSV sha 잎(`…/physical_ramp_recorded_csv/sha256`, D2)은 사슬 앞 결정의 CSV가 기록과 바이트 같으면 같으므로 "반드시 다른 잎"에서 뺐습니다.
- 결정 폴더 이름을 담은 다른 잎은 상태 경로(V 두 줄)뿐이었습니다(T=300, T=3150) [실행 `dirleaves.py`]. 그래서 위 목록이 사슬 때문에 생기는 차이의 전부로 보입니다 [추론: 기록 한 런·다섯 결정에서 본 것].

### 2.3 왜 피할 수 없는가

1. **자리**: 보충 24 §14.1은 RR·동결본 쓰기를 금하고 출력은 `OK2/vb/`입니다(:522). 사슬 직전 행동 파일은 `OK2/vb/…` 아래에 있게 됩니다. N(`k92_compare.py` `N2`)은 `d:/vissim_runs/20261004_sdmpc31_k8/sdmpc31_v3c3_k8j1*_s*`만 `<run>`으로 바꾸고 OK2 아래 경로는 그대로 둡니다. 그래서 경로 잎이 N 뒤에도 다릅니다 [읽음·실행].
2. **영수증**: `load_prices`는 영수증 2째 줄 = 직전 CSV 실제 경로를 요구합니다(sdmpc.py:525). 사슬 영수증은 사슬 CSV 경로를 담아야 하므로 바이트가 RR 영수증과 다르고, `receipt_sha256`(HARD H4 안)이 다릅니다.
3. **JSON 바이트**: 사슬 앞 결정의 JSON은 기록과 바이트가 다릅니다(상태 경로 V 잎, 벽시계 잎). 그래서 `vsl_cohort_initialization/sha256`(D2b, 허용에서 빠짐)이 다릅니다.
4. 보충 27 §6.2-2·보충 29 §6.2-2의 VB-I1 통과 = 결과 넷의 PASS(HARD 같음 + 미분류 0). 허용은 G-K0와 같고(D-a·D-d), 직전 행동 자리 차이를 받는 허용은 없습니다 [읽음 보충 24 :547, 보충 21 §6.4].

**결과 [추론, 규칙 함수로 확인]**: OFF 14결정 가운데 사슬 앞 출력을 직전 행동으로 받는 10결정 — VB-31·VB-43·VB-41의 T=3,150(셋), VB-41w의 T=150·300·450·600·750·900·1,050(일곱) — 은 FAIL입니다. 사슬 첫 결정 4개(T=3,000 ×3, VB-41w T=1)는 직전 행동이 RR 파일 그대로라 G-K0 D-d·D-a와 같은 조건입니다. VB-I1 하나라도 거짓 → VB_INCOMPLETE → STOP(S-K15)이므로, 그대로 돌리면 약 2시간 계산 뒤 반드시 멈추고, 그 뒤의 고침은 "데이터를 본 뒤"가 됩니다. 그래서 지금 멈췄습니다.

## 3. 둘째 빈칸 V-B-D2: 사슬 결정의 `k92_record.json`을 만드는 길이 정의되지 않음

- VB-M5(174 사슬 재고·용량 묶임 비율·`SC109_E_out`/220), VB-M6(OUTW·FEED-4), VB-M8(유령 재고)과 VB-I5 재계산은 `k92_record.json`을 씁니다(보충 24 :551, :560-563) [읽음].
- 그 기록기는 하네스 plant 잡(`sa_worker.py`)의 수동 기록기입니다: `k92_record.py:1-17` "passive plant-job record", 부르는 자리 `sa_worker.py:75`, `:744`(`K92R.collect`), `:1144`. plant 잡은 포착한 요청 틀에서 REFERENCE·세 블록 계획·미터 행동을 굴립니다(`sa_worker.py:1-25`) [읽음].
- 결정 재생(`k92_replay.py`, `replay_decision_n31.ps1`)은 이 파일을 만들지 않습니다 [읽음]. 보충 24 :560은 "기록기가 결정 JSON만으로 낼 수 없는 값은 '없음'"이라고만 적어, 글대로면 VB-M5·M6·M8이 모두 "없음"이 될 수 있습니다 [추론].

## 4. 기록 런 사실 (사슬 데이터 아님) [실행 `rrflags.py`]

V-B 41결정 시각의 RR 기록(키 끔)에서:

| 사슬 | 런 | 결정 | status | `head_observation_prior_discarded` | `head_observation_snapshot_sec` | hold 파일 | (173, p4) 하한 키 |
|---|---|---|---|---|---|---|---|
| VB-31 | `sdmpc31_v3c3_k8j1r_s31` | 3,000–4,500 (11) | 모두 ok | 모두 0.0 | 모두 = T | 0 | 결정마다 1 |
| VB-43 | `sdmpc31_v3c3_k8j1_s43` | 3,000–4,500 (11) | 모두 ok | 모두 0.0 | 모두 = T | 0 | 결정마다 1 |
| VB-41 | `sdmpc31_v3c3_k8j1_s41` | 3,000–4,500 (11) | 모두 ok | 모두 0.0 | 모두 = T | 0 | 0 (대조 — "하한이 끝내 없던" 런과 맞음) |
| VB-41w | `sdmpc31_v3c3_k8j1_s41` | 1, 150–1,050 (8) | 모두 ok | 모두 0.0 | 모두 = T | 0 | 0 |

- 기록 쪽에는 VB-I2·VB-I6을 미리 막는 구조 문제가 보이지 않습니다. `sdmpc_active`는 T ≥ 900에서 참, 그 앞은 없음.

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

- 비용 [추론]: 고친 뒤 55결정 ≈ 7–9 h(보충 24 §14.1 비용 줄). Q2 (가)(나)면 더 듭니다.

## 6. 이 단계가 쓴 파일

| 파일 | sha256 | 뜻 |
|---|---|---|
| `KB/k92_vb/dev/prevleaves.py` | `d42343f7acce54801434bf717b4ce3749e145199c6ba877a20acdf756e344e96` | 기록 결정에서 직전 행동 경로·sha 잎 찾기(경로만 출력) |
| `KB/k92_vb/dev/classify.py` | `18a1e4620da26bb361ac16428414804fb149225081d66fbd182e2477aa998f32` | 같은 잎을 K9-2-5 `k92_compare` 규칙 함수로 분류(GWT8에서 import, 쓰기 0) |
| `KB/k92_vb/dev/classify_out.json` | `eda96865db22fb67165c5fa4a3569954962934405e9e17af389eeba78e9c1ea6` | 위 결과(경로·규칙 이름만) |
| `KB/k92_vb/dev/dirleaves.py` | `1c4003088ee83e28f7184eee1c924c182328fd36a40b0fbae65641911a964ad0` | 결정 폴더 이름을 담은 잎 목록 |
| `KB/k92_vb/dev/rrflags.py` | `a031c6457238c647303b338b71011a2838b6770c9135065c407275a55936bc9c` | RR 기록 계수·표지(§4) |

- 모두 개발용 탐침입니다. V-B 구동기·재계산기가 아니고, 판정에 쓰지 않습니다. 읽은 것은 RR 기록 결정 JSON·영수증·CSV(J1 런, 블라인드 아님)와 GWT8 코드뿐입니다.
