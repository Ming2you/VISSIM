### 단계 기록 (`VBR/stages/*.json`)

| 단계 | 기록 | sha256 앞 16자 |
|---|---|---|
| V0 | 있음 (PASS 기록) | `1ccd7fb14391ed4c` |
| snap_s43_vb2_v0 | 있음 (PASS 기록) | `ace1ba2da15d37a9` |
| V1 | 있음 (PASS 기록) | `f717fe26733da996` |
| V2 | 있음 (PASS 기록) | `091e01b5a415b2c5` |
| V3 | 있음 (PASS 기록) | `45acdb2f52aa201f` |
| snap_s44_vb2_zi | 있음 (PASS 기록) | `dacd0b71871379b5` |
| V4 | 있음 (PASS 기록) | `fe1f7753e9159383` |
| V5 | 있음 (PASS 기록) | `76cc5993bba65081` |
| snap_s45_vb2_off | 있음 (PASS 기록) | `f19424740a39dc17` |
| V6 | 있음 (PASS 기록) | `c8bd717357b27e21` |
| V7 | 있음 (PASS 기록) | `67beab1ac68dff9d` |
| V8 | 있음 (PASS 기록) | `8226e71c8e95cade` |
| V9 | 있음 (PASS 기록) | `bc14df47fe45b7be` |
| snap_s46_vb2_end | 있음 (PASS 기록) | `5d3c32912fe42419` |
| V10 | 있음 (PASS 기록) | `3ec43f2d9377399f` |

- STOP 파일: 없음

### ZI 세 칸 (`VBR/zi/<칸>/zi_judge.json`)

| 칸 | (z1) | (z2) CSV 같음 | (z3) KC 결과 넷 | (z4) 진행 기록 | (z5) 벽시계 잎만 | (z6) 끔에 훅 파일 0 | (z7) 훅 무결성·고르기 | 칸 결과 |
|---|---|---|---|---|---|---|---|---|
| z1_off | 참 | 참 | PASS | 참 | 참 | 참 | 참, `selected` | PASS |
| z1_b1 | 참 | 참 | PASS | 참 | 참 | 참 | 참, `selected` | PASS |
| z2_b1 | 참 | 참 | PASS | 참 | 참 | 참 | 참, `no_candidate` | PASS |

훅 비용 (보고만)

| 칸 | 훅 끔 벽시계 (s) | 훅 켬 벽시계 (s) | 켬/끔 비 | 후보 수 | 맞는 후보 | 훅 안 시간 합 (s) | 후보 파일 합 (MB) | `loaded` 파일 수 |
|---|---|---|---|---|---|---|---|---|
| z1_off | 689.2 | 694.0 | 1.007 | 10 | 1 | 11.2 | 11.3 | 11 |
| z1_b1 | 689.2 | 696.6 | 1.011 | 10 | 1 | 11.2 | 11.3 | 11 |
| z2_b1 | 29.5 | 28.9 | 0.980 | 0 | 0 | 0.0 | 0.0 | 1 |

- z1_off: 두 출력 JSON의 차이 잎 36개, 벽시계 이름 경로 17개, 그 밖 0개.
- z1_b1: 두 출력 JSON의 차이 잎 36개, 벽시계 이름 경로 17개, 그 밖 0개.
- z2_b1: 두 출력 JSON의 차이 잎 3개, 벽시계 이름 경로 3개, 그 밖 0개.
- z1_off 훅 끔 출력 대 RR 기록(보고만): 결과 넷 PASS, HARD SAME, 미분류 0, 허용 수 {'V': 6, 'F1': 12, 'F3': 33, 'R3-08': 2, 'A_K92': 2, 'R3-01': 2, 'R3-03': 2, 'R3-05': 2}.

### VB-I1 판정 4결정 (`VBR/judge/vb_i1.json`)

| 사슬·T | 결과 넷 | HARD | 미분류 | 허용 수 | A_K92 줄 | D5 뿌리 점검 | 칸 결과 |
|---|---|---|---|---|---|---|---|
| VB-41w/T000001 | **PASS** | SAME | 0 | {'V': 6, 'R3-01': 2, 'R3-03': 2, 'R3-05': 2} | 0 | 없음 | PASS |
| VB-31/T003000 | **PASS** | SAME | 0 | {'V': 6, 'F1': 12, 'F3': 31, 'A_K92': 2, 'R3-01': 2} | 2 | 참 | PASS |
| VB-43/T003000 | **PASS** | SAME | 0 | {'V': 6, 'F1': 12, 'F3': 29, 'R3-08': 2, 'A_K92': 2, 'R3-01': 2, 'R3-03': 2, 'R3-05': 2} | 2 | 참 | PASS |
| VB-41/T003000 | **PASS** | SAME | 0 | {'V': 6, 'F1': 12, 'F3': 32, 'R3-08': 2, 'A_K92': 2, 'R3-01': 2, 'R3-03': 2, 'R3-05': 2} | 2 | 참 | PASS |

- VB-I1 4결정 모두 PASS: 참. OFF 14결정 VB-I2: 참, VB-I7: 참.

### 보고 전용 10결정 (`VBR/judge/vb_reportonly.json`; 판정 아님, D-K9-62·66)

| 사슬 | T (직전 T) | 꼴 | 결과 넷(참고) | CSV 같음 | 목록 안 HARD / 목록의 HARD | 목록 안 미분류 경로 | **목록 밖 경로 수** (잎 수) | 그중 `action_token` 꼴 | 목록 밖 HARD | 잘림 | 보이지 않은 목록 잎 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| VB-41w | 150 (1) | NN | FAIL | 참 | 1 / 1 | 2 | **0** (0) | 0 | 0 | 없음 | 0 |
| VB-41w | 300 (150) | NN | FAIL | 참 | 1 / 1 | 2 | **0** (0) | 0 | 0 | 없음 | 0 |
| VB-41w | 450 (300) | NN | FAIL | 참 | 1 / 1 | 2 | **0** (0) | 0 | 0 | 없음 | 0 |
| VB-41w | 600 (450) | NN | FAIL | 참 | 1 / 1 | 2 | **0** (0) | 0 | 0 | 없음 | 0 |
| VB-41w | 750 (600) | NN | FAIL | 참 | 1 / 1 | 2 | **0** (0) | 0 | 0 | 없음 | 0 |
| VB-41w | 900 (750) | SN | FAIL | 참 | 1 / 1 | 8 | **11** (31) | 11 | 0 | 없음 | 0 |
| VB-41w | 1050 (900) | SS | FAIL | 참 | 3 / 3 | 10 | **11** (29) | 11 | 0 | 없음 | 0 |
| VB-31 | 3150 (3000) | SS | FAIL | 참 | 3 / 3 | 10 | **11** (27) | 11 | 0 | 없음 | 0 |
| VB-43 | 3150 (3000) | SS | FAIL | 참 | 3 / 3 | 10 | **11** (29) | 11 | 0 | 없음 | 0 |
| VB-41 | 3150 (3000) | SS | FAIL | 참 | 3 / 3 | 10 | **11** (31) | 11 | 0 | 없음 | 0 |

- VB-41w T=150: 닫힌 목록 밖 차이 0개 (목록 안 HARD 1·미분류 2 경로는 보고에서 뺌).
- VB-41w T=300: 닫힌 목록 밖 차이 0개 (목록 안 HARD 1·미분류 2 경로는 보고에서 뺌).
- VB-41w T=450: 닫힌 목록 밖 차이 0개 (목록 안 HARD 1·미분류 2 경로는 보고에서 뺌).
- VB-41w T=600: 닫힌 목록 밖 차이 0개 (목록 안 HARD 1·미분류 2 경로는 보고에서 뺌).
- VB-41w T=750: 닫힌 목록 밖 차이 0개 (목록 안 HARD 1·미분류 2 경로는 보고에서 뺌).
- VB-41w T=900: **닫힌 목록 밖 차이 11개가 있습니다**: 미분류 /metadata/joint_leader_selection/budget_initialization/reference_action_token (D1); 미분류 /metadata/joint_leader_selection/control_sequence/plan_action_token (D1); 미분류 /metadata/joint_leader_selection/pfo_warm_start/iterations[*]/action_token (D1); 미분류 /metadata/joint_leader_selection/pfo_warm_start/trial_rows[*]/action_token (D1); 미분류 /metadata/joint_leader_selection/surrogate_query/rows[*]/action_token (D1); 미분류 /metadata/joint_leader_selection/surrogate_query/warm_budget_binding/initialization/reference_action_token (D1); 미분류 /metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/requested_action_token (D1); 미분류 /metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/source_action_token (D1); 미분류 /metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/warm_budget_binding/initialization/reference_action_token (D1); 미분류 /metadata/joint_leader_selection/tangent_derivatives[*]/surrogate_prediction/action_token (D1); 미분류 /metadata/joint_leader_selection/trial_rows[*]/action_token (D1)
- VB-41w T=1050: **닫힌 목록 밖 차이 11개가 있습니다**: 미분류 /metadata/joint_leader_selection/budget_initialization/reference_action_token (D1); 미분류 /metadata/joint_leader_selection/control_sequence/plan_action_token (D1); 미분류 /metadata/joint_leader_selection/pfo_warm_start/iterations[*]/action_token (D1); 미분류 /metadata/joint_leader_selection/pfo_warm_start/trial_rows[*]/action_token (D1); 미분류 /metadata/joint_leader_selection/surrogate_query/rows[*]/action_token (D1); 미분류 /metadata/joint_leader_selection/surrogate_query/warm_budget_binding/initialization/reference_action_token (D1); 미분류 /metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/requested_action_token (D1); 미분류 /metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/source_action_token (D1); 미분류 /metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/warm_budget_binding/initialization/reference_action_token (D1); 미분류 /metadata/joint_leader_selection/tangent_derivatives[*]/surrogate_prediction/action_token (D1); 미분류 /metadata/joint_leader_selection/trial_rows[*]/action_token (D1)
- VB-31 T=3150: **닫힌 목록 밖 차이 11개가 있습니다**: 미분류 /metadata/joint_leader_selection/budget_initialization/reference_action_token (D1); 미분류 /metadata/joint_leader_selection/control_sequence/plan_action_token (D1); 미분류 /metadata/joint_leader_selection/pfo_warm_start/iterations[*]/action_token (D1); 미분류 /metadata/joint_leader_selection/pfo_warm_start/trial_rows[*]/action_token (D1); 미분류 /metadata/joint_leader_selection/surrogate_query/rows[*]/action_token (D1); 미분류 /metadata/joint_leader_selection/surrogate_query/warm_budget_binding/initialization/reference_action_token (D1); 미분류 /metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/requested_action_token (D1); 미분류 /metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/source_action_token (D1); 미분류 /metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/warm_budget_binding/initialization/reference_action_token (D1); 미분류 /metadata/joint_leader_selection/tangent_derivatives[*]/surrogate_prediction/action_token (D1); 미분류 /metadata/joint_leader_selection/trial_rows[*]/action_token (D1)
- VB-43 T=3150: **닫힌 목록 밖 차이 11개가 있습니다**: 미분류 /metadata/joint_leader_selection/budget_initialization/reference_action_token (D1); 미분류 /metadata/joint_leader_selection/control_sequence/plan_action_token (D1); 미분류 /metadata/joint_leader_selection/pfo_warm_start/iterations[*]/action_token (D1); 미분류 /metadata/joint_leader_selection/pfo_warm_start/trial_rows[*]/action_token (D1); 미분류 /metadata/joint_leader_selection/surrogate_query/rows[*]/action_token (D1); 미분류 /metadata/joint_leader_selection/surrogate_query/warm_budget_binding/initialization/reference_action_token (D1); 미분류 /metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/requested_action_token (D1); 미분류 /metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/source_action_token (D1); 미분류 /metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/warm_budget_binding/initialization/reference_action_token (D1); 미분류 /metadata/joint_leader_selection/tangent_derivatives[*]/surrogate_prediction/action_token (D1); 미분류 /metadata/joint_leader_selection/trial_rows[*]/action_token (D1)
- VB-41 T=3150: **닫힌 목록 밖 차이 11개가 있습니다**: 미분류 /metadata/joint_leader_selection/budget_initialization/reference_action_token (D1); 미분류 /metadata/joint_leader_selection/control_sequence/plan_action_token (D1); 미분류 /metadata/joint_leader_selection/pfo_warm_start/iterations[*]/action_token (D1); 미분류 /metadata/joint_leader_selection/pfo_warm_start/trial_rows[*]/action_token (D1); 미분류 /metadata/joint_leader_selection/surrogate_query/rows[*]/action_token (D1); 미분류 /metadata/joint_leader_selection/surrogate_query/warm_budget_binding/initialization/reference_action_token (D1); 미분류 /metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/requested_action_token (D1); 미분류 /metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/source_action_token (D1); 미분류 /metadata/joint_leader_selection/tangent_derivatives[*]/candidate_prediction_reused/warm_budget_binding/initialization/reference_action_token (D1); 미분류 /metadata/joint_leader_selection/tangent_derivatives[*]/surrogate_prediction/action_token (D1); 미분류 /metadata/joint_leader_selection/trial_rows[*]/action_token (D1)

- 목록 밖 `action_token` 꼴 경로(서로 다른 것) 11개. STOP 판 r1의 11경로와 견주면: 같은 경로 11개, 이번에 새로 보인 경로 0개, 이번에 보이지 않은 경로 0개.
- `action_token` 꼴이 아닌 목록 밖 차이: 0건

### VB-I2·VB-I7 — OFF 14결정 (`VBR/judge/vb_i1.json` `/off_rows`)

| 사슬 | T | VB-I2 | VB-I7 | 고르기 상태 | 후보 / 맞음 | 훅 안 시간 합 (s) |
|---|---|---|---|---|---|---|
| VB-41w | 1 | 참 | 참 | no_candidate | 0 / 0 | 0.0 |
| VB-41w | 150 | 참 | 참 | no_candidate | 0 / 0 | 0.0 |
| VB-41w | 300 | 참 | 참 | no_candidate | 0 / 0 | 0.0 |
| VB-41w | 450 | 참 | 참 | no_candidate | 0 / 0 | 0.0 |
| VB-41w | 600 | 참 | 참 | no_candidate | 0 / 0 | 0.0 |
| VB-41w | 750 | 참 | 참 | no_candidate | 0 / 0 | 0.0 |
| VB-41w | 900 | 참 | 참 | selected | 10 / 1 | 10.9 |
| VB-41w | 1050 | 참 | 참 | selected | 9 / 1 | 10.2 |
| VB-31 | 3000 | 참 | 참 | selected | 8 / 1 | 8.7 |
| VB-31 | 3150 | 참 | 참 | selected | 8 / 1 | 8.5 |
| VB-43 | 3000 | 참 | 참 | selected | 6 / 1 | 7.2 |
| VB-43 | 3150 | 참 | 참 | selected | 9 / 1 | 10.2 |
| VB-41 | 3000 | 참 | 참 | selected | 9 / 1 | 10.4 |
| VB-41 | 3150 | 참 | 참 | selected | 10 / 1 | 11.1 |

### VB-I2–VB-I7 (55결정; `VBR/judge/vb_i.json`, VB-I5 = `VBR/recalc/recalc.json`)

| 점검 | 결과 |
|---|---|
| VB-I2 | 참 |
| VB-I3 | 참 |
| VB-I4 | 참 |
| VB-I6 | 참 |
| VB-I7 | 참 |
| VB-I5 (재계산 같음) | 참 |

- SDMPC 결정의 고르기 상태 개수: {'selected': 41, 'no_match': 2}. `selected`가 아닌 SDMPC 결정: [['VB-41', 'b1', 3300, 'no_match'], ['VB-41', 'b1', 4500, 'no_match']].
- VB-I6 VB-41w: 결정마다 키 하나·이름 맞음 참, 값 줄지 않음 참, T=150 값 = T=1 값 = s 참; 값 ['1045.1613', '1045.1613', '1045.1613', '1045.1613', '1045.1613', '1045.1613', '1045.1613', '1045.1613']
- VB-I6 VB-31: 결정마다 키 하나·이름 맞음 참, 값 줄지 않음 참; 값 ['1045.1613', '1045.1613', '1045.1613', '1045.1613', '1045.1613', '1045.1613', '1384.6154', '1384.6154', '1384.6154', '1384.6154', '1384.6154']
- VB-I6 VB-43: 결정마다 키 하나·이름 맞음 참, 값 줄지 않음 참; 값 ['1509.6774', '1509.6774', '1509.6774', '1509.6774', '1509.6774', '1509.6774', '1509.6774', '1509.6774', '1509.6774', '1509.6774', '1509.6774']
- VB-I6 VB-41: 결정마다 키 하나·이름 맞음 참, 값 줄지 않음 참; 값 ['1045.1613', '1045.1613', '1045.1613', '1045.1613', '1045.1613', '1045.1613', '1045.1613', '1045.1613', '1045.1613', '1045.1613', '1045.1613']

| 사슬 | 팔 | T | VB-I2 | VB-I7 | SDMPC | 고르기 상태 | 후보 / 맞음 | 훅 안 시간 합 (s) |
|---|---|---|---|---|---|---|---|---|
| VB-41w | off | 1 | 참 | 참 | 없음 | no_candidate | 0 / 0 | 0.0 |
| VB-41w | off | 150 | 참 | 참 | 없음 | no_candidate | 0 / 0 | 0.0 |
| VB-41w | off | 300 | 참 | 참 | 없음 | no_candidate | 0 / 0 | 0.0 |
| VB-41w | off | 450 | 참 | 참 | 없음 | no_candidate | 0 / 0 | 0.0 |
| VB-41w | off | 600 | 참 | 참 | 없음 | no_candidate | 0 / 0 | 0.0 |
| VB-41w | off | 750 | 참 | 참 | 없음 | no_candidate | 0 / 0 | 0.0 |
| VB-41w | off | 900 | 참 | 참 | 참 | selected | 10 / 1 | 10.9 |
| VB-41w | off | 1050 | 참 | 참 | 참 | selected | 9 / 1 | 10.2 |
| VB-31 | off | 3000 | 참 | 참 | 참 | selected | 8 / 1 | 8.7 |
| VB-31 | off | 3150 | 참 | 참 | 참 | selected | 8 / 1 | 8.5 |
| VB-43 | off | 3000 | 참 | 참 | 참 | selected | 6 / 1 | 7.2 |
| VB-43 | off | 3150 | 참 | 참 | 참 | selected | 9 / 1 | 10.2 |
| VB-41 | off | 3000 | 참 | 참 | 참 | selected | 9 / 1 | 10.4 |
| VB-41 | off | 3150 | 참 | 참 | 참 | selected | 10 / 1 | 11.1 |
| VB-41w | b1 | 1 | 참 | 참 | 없음 | no_candidate | 0 / 0 | 0.0 |
| VB-41w | b1 | 150 | 참 | 참 | 없음 | no_candidate | 0 / 0 | 0.0 |
| VB-41w | b1 | 300 | 참 | 참 | 없음 | no_candidate | 0 / 0 | 0.0 |
| VB-41w | b1 | 450 | 참 | 참 | 없음 | no_candidate | 0 / 0 | 0.0 |
| VB-41w | b1 | 600 | 참 | 참 | 없음 | no_candidate | 0 / 0 | 0.0 |
| VB-41w | b1 | 750 | 참 | 참 | 없음 | no_candidate | 0 / 0 | 0.0 |
| VB-41w | b1 | 900 | 참 | 참 | 참 | selected | 9 / 1 | 10.4 |
| VB-41w | b1 | 1050 | 참 | 참 | 참 | selected | 7 / 1 | 7.5 |
| VB-31 | b1 | 3000 | 참 | 참 | 참 | selected | 8 / 1 | 8.9 |
| VB-31 | b1 | 3150 | 참 | 참 | 참 | selected | 11 / 1 | 12.1 |
| VB-31 | b1 | 3300 | 참 | 참 | 참 | selected | 6 / 1 | 6.7 |
| VB-31 | b1 | 3450 | 참 | 참 | 참 | selected | 7 / 1 | 8.0 |
| VB-31 | b1 | 3600 | 참 | 참 | 참 | selected | 6 / 1 | 6.8 |
| VB-31 | b1 | 3750 | 참 | 참 | 참 | selected | 5 / 1 | 6.1 |
| VB-31 | b1 | 3900 | 참 | 참 | 참 | selected | 3 / 1 | 3.5 |
| VB-31 | b1 | 4050 | 참 | 참 | 참 | selected | 2 / 1 | 2.5 |
| VB-31 | b1 | 4200 | 참 | 참 | 참 | selected | 8 / 1 | 9.4 |
| VB-31 | b1 | 4350 | 참 | 참 | 참 | selected | 5 / 1 | 5.6 |
| VB-31 | b1 | 4500 | 참 | 참 | 참 | selected | 5 / 1 | 6.0 |
| VB-43 | b1 | 3000 | 참 | 참 | 참 | selected | 9 / 1 | 10.0 |
| VB-43 | b1 | 3150 | 참 | 참 | 참 | selected | 5 / 1 | 5.9 |
| VB-43 | b1 | 3300 | 참 | 참 | 참 | selected | 4 / 1 | 4.6 |
| VB-43 | b1 | 3450 | 참 | 참 | 참 | selected | 8 / 1 | 9.2 |
| VB-43 | b1 | 3600 | 참 | 참 | 참 | selected | 6 / 1 | 6.8 |
| VB-43 | b1 | 3750 | 참 | 참 | 참 | selected | 9 / 1 | 10.0 |
| VB-43 | b1 | 3900 | 참 | 참 | 참 | selected | 8 / 1 | 8.8 |
| VB-43 | b1 | 4050 | 참 | 참 | 참 | selected | 6 / 1 | 7.0 |
| VB-43 | b1 | 4200 | 참 | 참 | 참 | selected | 11 / 1 | 12.4 |
| VB-43 | b1 | 4350 | 참 | 참 | 참 | selected | 7 / 1 | 7.6 |
| VB-43 | b1 | 4500 | 참 | 참 | 참 | selected | 7 / 1 | 7.9 |
| VB-41 | b1 | 3000 | 참 | 참 | 참 | selected | 11 / 1 | 11.9 |
| VB-41 | b1 | 3150 | 참 | 참 | 참 | selected | 4 / 1 | 4.5 |
| VB-41 | b1 | 3300 | 참 | 참 | 참 | no_match | 3 / 0 | 3.9 |
| VB-41 | b1 | 3450 | 참 | 참 | 참 | selected | 5 / 1 | 5.7 |
| VB-41 | b1 | 3600 | 참 | 참 | 참 | selected | 9 / 1 | 9.9 |
| VB-41 | b1 | 3750 | 참 | 참 | 참 | selected | 8 / 1 | 9.2 |
| VB-41 | b1 | 3900 | 참 | 참 | 참 | selected | 7 / 1 | 8.2 |
| VB-41 | b1 | 4050 | 참 | 참 | 참 | selected | 8 / 1 | 9.0 |
| VB-41 | b1 | 4200 | 참 | 참 | 참 | selected | 9 / 1 | 10.1 |
| VB-41 | b1 | 4350 | 참 | 참 | 참 | selected | 6 / 1 | 6.7 |
| VB-41 | b1 | 4500 | 참 | 참 | 참 | no_match | 2 / 0 | 2.5 |

- 재계산기 요약 키: ['equal', 'n_compared', 'n_diff', 'schema', 'tool_sha256', 'vbr']

### 훅 폴더 이름 요약 (보고만; 보충 33 §8-5)

- 훅 폴더 58/58개 있음. `loaded` 파일 합 381, 서로 다른 토큰 합 381(후보가 있는 토큰 323), 후보 폴더 합 323.
- 이름 꼴: 옛 꼴 이름 0, 그 밖의 이름 0, `hook_error_*` 0, `hook_setup_error_*` 0.
- 같은 PID를 둘 이상의 토큰이 받은 묶음(= 한 폴더 안 PID 재사용): 폴더 1개에서 묶음 1개(더 생긴 토큰 1). 그 묶음들의 후보 `time_ns` 구간 겹침 0건.
- 이 표의 짝 점검(참고, 판정은 VerifyVB): 모든 후보 토큰에 `loaded` 있음 참, PID = 토큰 첫 조각 참, 순번 1부터 이어짐 참, 후보 폴더 안 파일 꼴 참, 어댑터 `loaded` 폴더마다 하나 참.

| 훅 폴더 | `loaded` | 토큰 (후보 있음) | 후보 | 같은 PID 묶음 (더 생긴 토큰) | 겹침 |
|---|---|---|---|---|---|
| VB-41w off T=1 | 1 | 1 (0) | 0 | 0 (0) | 0 |
| VB-41w off T=150 | 1 | 1 (0) | 0 | 0 (0) | 0 |
| VB-41w off T=300 | 1 | 1 (0) | 0 | 0 (0) | 0 |
| VB-41w off T=450 | 1 | 1 (0) | 0 | 0 (0) | 0 |
| VB-41w off T=600 | 1 | 1 (0) | 0 | 0 (0) | 0 |
| VB-41w off T=750 | 1 | 1 (0) | 0 | 0 (0) | 0 |
| VB-41w off T=900 | 11 | 11 (10) | 10 | 0 (0) | 0 |
| VB-41w off T=1050 | 10 | 10 (9) | 9 | 0 (0) | 0 |
| VB-41w b1 T=1 | 1 | 1 (0) | 0 | 0 (0) | 0 |
| VB-41w b1 T=150 | 1 | 1 (0) | 0 | 0 (0) | 0 |
| VB-41w b1 T=300 | 1 | 1 (0) | 0 | 0 (0) | 0 |
| VB-41w b1 T=450 | 1 | 1 (0) | 0 | 0 (0) | 0 |
| VB-41w b1 T=600 | 1 | 1 (0) | 0 | 0 (0) | 0 |
| VB-41w b1 T=750 | 1 | 1 (0) | 0 | 0 (0) | 0 |
| VB-41w b1 T=900 | 10 | 10 (9) | 9 | 0 (0) | 0 |
| VB-41w b1 T=1050 | 8 | 8 (7) | 7 | 0 (0) | 0 |
| VB-31 off T=3000 | 9 | 9 (8) | 8 | 0 (0) | 0 |
| VB-31 off T=3150 | 9 | 9 (8) | 8 | 0 (0) | 0 |
| VB-31 b1 T=3000 | 9 | 9 (8) | 8 | 0 (0) | 0 |
| VB-31 b1 T=3150 | 12 | 12 (11) | 11 | 0 (0) | 0 |
| VB-31 b1 T=3300 | 7 | 7 (6) | 6 | 0 (0) | 0 |
| VB-31 b1 T=3450 | 8 | 8 (7) | 7 | 0 (0) | 0 |
| VB-31 b1 T=3600 | 7 | 7 (6) | 6 | 0 (0) | 0 |
| VB-31 b1 T=3750 | 6 | 6 (5) | 5 | 0 (0) | 0 |
| VB-31 b1 T=3900 | 4 | 4 (3) | 3 | 0 (0) | 0 |
| VB-31 b1 T=4050 | 3 | 3 (2) | 2 | 0 (0) | 0 |
| VB-31 b1 T=4200 | 9 | 9 (8) | 8 | 0 (0) | 0 |
| VB-31 b1 T=4350 | 6 | 6 (5) | 5 | 0 (0) | 0 |
| VB-31 b1 T=4500 | 6 | 6 (5) | 5 | 0 (0) | 0 |
| VB-43 off T=3000 | 7 | 7 (6) | 6 | 0 (0) | 0 |
| VB-43 off T=3150 | 10 | 10 (9) | 9 | 0 (0) | 0 |
| VB-43 b1 T=3000 | 10 | 10 (9) | 9 | 0 (0) | 0 |
| VB-43 b1 T=3150 | 6 | 6 (5) | 5 | 0 (0) | 0 |
| VB-43 b1 T=3300 | 5 | 5 (4) | 4 | 0 (0) | 0 |
| VB-43 b1 T=3450 | 9 | 9 (8) | 8 | 0 (0) | 0 |
| VB-43 b1 T=3600 | 7 | 7 (6) | 6 | 0 (0) | 0 |
| VB-43 b1 T=3750 | 10 | 10 (9) | 9 | 0 (0) | 0 |
| VB-43 b1 T=3900 | 9 | 9 (8) | 8 | 0 (0) | 0 |
| VB-43 b1 T=4050 | 7 | 7 (6) | 6 | 0 (0) | 0 |
| VB-43 b1 T=4200 | 12 | 12 (11) | 11 | 0 (0) | 0 |
| VB-43 b1 T=4350 | 8 | 8 (7) | 7 | 0 (0) | 0 |
| VB-43 b1 T=4500 | 8 | 8 (7) | 7 | 0 (0) | 0 |
| VB-41 off T=3000 | 10 | 10 (9) | 9 | 0 (0) | 0 |
| VB-41 off T=3150 | 11 | 11 (10) | 10 | 0 (0) | 0 |
| VB-41 b1 T=3000 | 12 | 12 (11) | 11 | 0 (0) | 0 |
| VB-41 b1 T=3150 | 5 | 5 (4) | 4 | 0 (0) | 0 |
| VB-41 b1 T=3300 | 4 | 4 (3) | 3 | 0 (0) | 0 |
| VB-41 b1 T=3450 | 6 | 6 (5) | 5 | 0 (0) | 0 |
| VB-41 b1 T=3600 | 10 | 10 (9) | 9 | 0 (0) | 0 |
| VB-41 b1 T=3750 | 9 | 9 (8) | 8 | 0 (0) | 0 |
| VB-41 b1 T=3900 | 8 | 8 (7) | 7 | 0 (0) | 0 |
| VB-41 b1 T=4050 | 9 | 9 (8) | 8 | 0 (0) | 0 |
| VB-41 b1 T=4200 | 10 | 10 (9) | 9 | 1 (1) | 0 |
| VB-41 b1 T=4350 | 7 | 7 (6) | 6 | 0 (0) | 0 |
| VB-41 b1 T=4500 | 3 | 3 (2) | 2 | 0 (0) | 0 |
| ZI z1_off | 11 | 11 (10) | 10 | 0 (0) | 0 |
| ZI z1_b1 | 11 | 11 (10) | 10 | 0 (0) | 0 |
| ZI z2_b1 | 1 | 1 (0) | 0 | 0 (0) | 0 |

### 사슬 결정 벽시계 (구동기 `done` 기록, 보고만)

| 사슬 | 팔 | 결정 수 | 벽시계 합 (h) | 최소 (s) | 최대 (s) |
|---|---|---|---|---|---|
| VB-41w | off | 8 | 0.46 | 25.0 | 744.3 |
| VB-41w | b1 | 8 | 0.45 | 27.0 | 732.7 |
| VB-31 | off | 2 | 0.41 | 727.5 | 733.3 |
| VB-31 | b1 | 11 | 1.99 | 384.4 | 778.3 |
| VB-43 | off | 2 | 0.42 | 727.7 | 787.0 |
| VB-43 | b1 | 11 | 2.10 | 521.5 | 790.9 |
| VB-41 | off | 2 | 0.38 | 615.3 | 754.8 |
| VB-41 | b1 | 11 | 1.99 | 354.5 | 795.5 |

#### VB-41w — 결정별 (B1 / OFF / REC = RR 기록, 같은 T끼리; 모형 안 값)

| T | 쪽 | p2 | p3 | p4 | (173,p4) 하한 | 씨앗 묶임 | 나름/갱신 | 174 사슬 T+450 | 사슬 최대 | 직진 용량 묶임 비 | E_out/220 | OUTW (veh·h) | FEED-4 (몫) | Ω | 유령 끝 | PFO>유지 / 고름>유지 | selection_status | CSV=REC | 벽시계 (s) | 고르기 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | B1 | 20.00 | 90.00 | 31.00 | 1045.1613 | 1.0 | 0/0 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 없음 | 없음 | 없음/없음 | 없음 | 참 | 27 | no_candidate |
| 1 | OFF | 20.00 | 90.00 | 31.00 | 없음 | 없음 | 0/0 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 없음 | 없음 | 없음/없음 | 없음 | 참 | 25 | no_candidate |
| 1 | REC | 20.00 | 90.00 | 31.00 | 없음 | 없음 | 0/0 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 없음 | 없음 | 없음/없음 | 없음 | – | 17 | REC: recorder not run (J1 record) |
| 150 | B1 | 20.00 | 90.00 | 31.00 | 1045.1613 | 1.0 | 0/0 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 없음 | 없음 | 없음/없음 | 없음 | 참 | 27 | no_candidate |
| 150 | OFF | 20.00 | 90.00 | 31.00 | 없음 | 없음 | 0/0 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 없음 | 없음 | 없음/없음 | 없음 | 참 | 26 | no_candidate |
| 150 | REC | 20.00 | 90.00 | 31.00 | 없음 | 없음 | 0/0 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 없음 | 없음 | 없음/없음 | 없음 | – | 18 | REC: recorder not run (J1 record) |
| 300 | B1 | 20.00 | 90.00 | 31.00 | 1045.1613 | 0.0 | 1/10 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 없음 | 없음 | 없음/없음 | 없음 | 참 | 29 | no_candidate |
| 300 | OFF | 20.00 | 90.00 | 31.00 | 없음 | 없음 | 0/10 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 없음 | 없음 | 없음/없음 | 없음 | 참 | 30 | no_candidate |
| 300 | REC | 20.00 | 90.00 | 31.00 | 없음 | 없음 | 0/10 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 없음 | 없음 | 없음/없음 | 없음 | – | 20 | REC: recorder not run (J1 record) |
| 450 | B1 | 20.00 | 90.00 | 31.00 | 1045.1613 | 0.0 | 10/22 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 없음 | 없음 | 없음/없음 | 없음 | 참 | 31 | no_candidate |
| 450 | OFF | 20.00 | 90.00 | 31.00 | 없음 | 없음 | 9/22 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 없음 | 없음 | 없음/없음 | 없음 | 참 | 30 | no_candidate |
| 450 | REC | 20.00 | 90.00 | 31.00 | 없음 | 없음 | 9/22 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 없음 | 없음 | 없음/없음 | 없음 | – | 20 | REC: recorder not run (J1 record) |
| 600 | B1 | 20.00 | 90.00 | 31.00 | 1045.1613 | 0.0 | 21/35 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 없음 | 없음 | 없음/없음 | 없음 | 참 | 31 | no_candidate |
| 600 | OFF | 20.00 | 90.00 | 31.00 | 없음 | 없음 | 20/35 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 없음 | 없음 | 없음/없음 | 없음 | 참 | 29 | no_candidate |
| 600 | REC | 20.00 | 90.00 | 31.00 | 없음 | 없음 | 20/35 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 없음 | 없음 | 없음/없음 | 없음 | – | 21 | REC: recorder not run (J1 record) |
| 750 | B1 | 20.00 | 90.00 | 31.00 | 1045.1613 | 0.0 | 35/41 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 없음 | 없음 | 없음/없음 | 없음 | 참 | 31 | no_candidate |
| 750 | OFF | 20.00 | 90.00 | 31.00 | 없음 | 없음 | 34/41 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 없음 | 없음 | 없음/없음 | 없음 | 참 | 31 | no_candidate |
| 750 | REC | 20.00 | 90.00 | 31.00 | 없음 | 없음 | 34/41 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 없음 | 없음 | 없음/없음 | 없음 | – | 21 | REC: recorder not run (J1 record) |
| 900 | B1 | 26.00 | 85.41 | 29.59 | 1045.1613 | 0.0 | 41/45 | 14.66 | 34.88 | 0.237 | 0.126 | 671.13 | 56.83 (0.085) | 328.36 | 4.46 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 710 | selected |
| 900 | OFF | 26.00 | 88.09 | 26.91 | 없음 | 없음 | 40/45 | 78.88 | 78.88 | 0.929 | 0.016 | 674.10 | 55.99 (0.083) | 332.98 | 4.34 | 거짓/거짓 | best_observed_feasible_sdmpc | 참 | 734 | selected |
| 900 | REC | 26.00 | 88.09 | 26.91 | 없음 | 없음 | 40/45 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 332.98 | 없음 | 거짓/거짓 | best_observed_feasible_sdmpc | – | 576 | REC: recorder not run (J1 record) |
| 1050 | B1 | 32.00 | 79.41 | 29.59 | 1045.1613 | 0.0 | 45/40 | 19.38 | 42.13 | 0.185 | 0.120 | 805.29 | 63.23 (0.079) | 410.88 | 2.92 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 733 | selected |
| 1050 | OFF | 30.90 | 88.63 | 21.47 | 없음 | 없음 | 44/40 | 80.82 | 80.82 | 0.926 | 0.062 | 807.18 | 61.98 (0.077) | 414.57 | 3.24 | 거짓/거짓 | best_observed_feasible_sdmpc | 참 | 744 | selected |
| 1050 | REC | 30.90 | 88.63 | 21.47 | 없음 | 없음 | 44/40 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 414.57 | 없음 | 거짓/거짓 | best_observed_feasible_sdmpc | – | 546 | REC: recorder not run (J1 record) |

| 쪽 | 결정 수 | p3 ≤ 24.5 결정 수 (첫 T) | Δp3 수 | 부호 바뀜 (절댓값 ≥ 0.5만) | 평균 절댓값 Δp3 | k92_w / k92_hb 키 결정 수 | PFO>유지 / 고름>유지 결정 수 | 기록과 CSV 처음 다른 T | selection_status 개수 | 고르기 selected |
|---|---|---|---|---|---|---|---|---|---|---|
| REC | 8 | 0 (없음) | 7 | 1 | 0.35 | 0 / 0 | 0 / 0 | – | {'None': 6, 'best_observed_feasible_sdmpc': 2} | – |
| OFF | 8 | 0 (없음) | 7 | 1 | 0.35 | 0 / 0 | 0 / 0 | 없음 | {'None': 6, 'best_observed_feasible_sdmpc': 2} | 2 |
| B1 | 8 | 0 (없음) | 7 | 0 | 1.51 | 8 / 8 | 0 / 0 | 900 | {'None': 6, 'best_observed_feasible_sdmpc': 2} | 2 |

- VB-41w B1 하한 = max(기록 하한, s): ['T=1 참', 'T=150 참', 'T=300 참', 'T=450 참', 'T=600 참', 'T=750 참', 'T=900 참', 'T=1050 참']

#### VB-31 — 결정별 (B1 / OFF / REC = RR 기록, 같은 T끼리; 모형 안 값)

| T | 쪽 | p2 | p3 | p4 | (173,p4) 하한 | 씨앗 묶임 | 나름/갱신 | 174 사슬 T+450 | 사슬 최대 | 직진 용량 묶임 비 | E_out/220 | OUTW (veh·h) | FEED-4 (몫) | Ω | 유령 끝 | PFO>유지 / 고름>유지 | selection_status | CSV=REC | 벽시계 (s) | 고르기 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3000 | B1 | 72.61 | 43.65 | 24.74 | 1045.1613 | 0.0 | 50/39 | 86.53 | 158.72 | 0.621 | 0.285 | 1018.03 | 144.03 (0.141) | 473.44 | 6.09 | 참/거짓 | best_observed_feasible_sdmpc | 거짓 | 600 | selected |
| 3000 | OFF | 77.30 | 36.71 | 26.99 | 1045.1613 | 없음 | 50/39 | 234.65 | 234.65 | 0.832 | 0.066 | 1021.80 | 146.16 (0.143) | 483.18 | 6.18 | 참/거짓 | best_observed_feasible_sdmpc | 참 | 728 | selected |
| 3000 | REC | 77.30 | 36.71 | 26.99 | 1045.1613 | 없음 | 50/39 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 483.18 | 없음 | 참/거짓 | best_observed_feasible_sdmpc | – | 490 | REC: recorder not run (J1 record) |
| 3150 | B1 | 74.62 | 40.69 | 25.68 | 1045.1613 | 0.0 | 51/38 | 84.93 | 129.20 | 0.720 | 0.230 | 1006.14 | 151.26 (0.150) | 464.01 | 5.35 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 750 | selected |
| 3150 | OFF | 76.83 | 35.21 | 28.96 | 1045.1613 | 없음 | 51/38 | 208.91 | 208.91 | 0.838 | 0.019 | 1009.87 | 151.43 (0.150) | 473.69 | 5.44 | 거짓/거짓 | best_observed_feasible_sdmpc | 참 | 733 | selected |
| 3150 | REC | 76.83 | 35.21 | 28.96 | 1045.1613 | 없음 | 51/38 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 473.69 | 없음 | 거짓/거짓 | best_observed_feasible_sdmpc | – | 494 | REC: recorder not run (J1 record) |
| 3300 | B1 | 69.37 | 45.94 | 25.68 | 1045.1613 | 0.0 | 51/35 | 88.53 | 159.55 | 0.716 | 0.319 | 993.46 | 147.10 (0.148) | 454.83 | 3.82 | 참/거짓 | best_observed_feasible_sdmpc | 거짓 | 740 | selected |
| 3300 | REC | 75.33 | 35.21 | 30.46 | 1045.1613 | 없음 | 51/35 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 467.89 | 없음 | 참/참 | best_observed_feasible_sdmpc | – | 237 | REC: recorder not run (J1 record) |
| 3450 | B1 | 67.72 | 50.44 | 22.84 | 1045.1613 | 0.0 | 51/39 | 101.05 | 168.55 | 0.782 | 0.337 | 971.60 | 146.92 (0.151) | 461.94 | 5.38 | 참/거짓 | best_observed_feasible_sdmpc | 거짓 | 675 | selected |
| 3450 | REC | 79.46 | 30.71 | 30.83 | 1045.1613 | 없음 | 51/39 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 472.95 | 없음 | 참/거짓 | best_observed_feasible_sdmpc | – | 389 | REC: recorder not run (J1 record) |
| 3600 | B1 | 62.96 | 56.44 | 21.60 | 1045.1613 | 0.0 | 51/40 | 103.34 | 179.83 | 0.810 | 0.399 | 936.57 | 144.20 (0.154) | 435.71 | 4.70 | 참/거짓 | best_observed_feasible_sdmpc | 거짓 | 752 | selected |
| 3600 | REC | 76.27 | 29.96 | 34.77 | 1045.1613 | 없음 | 51/40 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 447.54 | 없음 | 참/거짓 | best_observed_feasible_sdmpc | – | 478 | REC: recorder not run (J1 record) |
| 3750 | B1 | 62.37 | 55.97 | 22.66 | 1045.1613 | 0.0 | 51/38 | 102.49 | 153.67 | 0.903 | 0.333 | 919.26 | 141.81 (0.154) | 441.50 | 4.58 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 738 | selected |
| 3750 | REC | 74.73 | 27.00 | 39.27 | 1045.1613 | 없음 | 51/38 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 453.49 | 없음 | 참/거짓 | best_observed_feasible_sdmpc | – | 488 | REC: recorder not run (J1 record) |
| 3900 | B1 | 60.87 | 55.97 | 24.16 | 1384.6154 | 0.0 | 51/41 | 116.73 | 174.84 | 0.811 | 0.295 | 924.08 | 142.65 (0.154) | 443.58 | 3.76 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 514 | selected |
| 3900 | REC | 73.04 | 23.25 | 44.71 | 1384.6154 | 없음 | 51/41 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 453.38 | 없음 | 참/거짓 | best_observed_feasible_sdmpc | – | 478 | REC: recorder not run (J1 record) |
| 4050 | B1 | 57.87 | 58.97 | 24.16 | 1384.6154 | 0.0 | 51/39 | 117.64 | 212.05 | 0.635 | 0.357 | 926.06 | 137.36 (0.148) | 451.89 | 4.50 | 참/참 | best_observed_feasible_sdmpc | 거짓 | 384 | selected |
| 4050 | REC | 69.48 | 22.31 | 49.21 | 1384.6154 | 없음 | 51/39 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 462.19 | 없음 | 거짓/거짓 | best_observed_feasible_sdmpc | – | 501 | REC: recorder not run (J1 record) |
| 4200 | B1 | 54.95 | 63.71 | 22.34 | 1384.6154 | 0.0 | 51/38 | 121.87 | 232.05 | 0.675 | 0.474 | 906.45 | 138.83 (0.153) | 433.29 | 5.69 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 778 | selected |
| 4200 | REC | 75.48 | 20.00 | 45.52 | 1384.6154 | 없음 | 51/38 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 444.91 | 없음 | 참/거짓 | best_observed_feasible_sdmpc | – | 481 | REC: recorder not run (J1 record) |
| 4350 | B1 | 52.25 | 67.87 | 20.88 | 1384.6154 | 0.0 | 51/37 | 127.56 | 263.55 | 0.844 | 0.581 | 861.28 | 127.50 (0.148) | 420.42 | 4.18 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 613 | selected |
| 4350 | REC | 73.86 | 20.00 | 47.14 | 1384.6154 | 없음 | 51/37 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 434.67 | 없음 | 거짓/거짓 | best_observed_feasible_sdmpc | – | 257 | REC: recorder not run (J1 record) |
| 4500 | B1 | 49.05 | 71.62 | 20.33 | 1384.6154 | 0.0 | 52/37 | 86.97 | 264.52 | 0.866 | 0.815 | 832.42 | 117.81 (0.142) | 407.31 | 4.85 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 604 | selected |
| 4500 | REC | 73.86 | 20.00 | 47.14 | 1384.6154 | 없음 | 52/37 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 422.51 | 없음 | 참/거짓 | best_observed_feasible_sdmpc | – | 444 | REC: recorder not run (J1 record) |

| 쪽 | 결정 수 | p3 ≤ 24.5 결정 수 (첫 T) | Δp3 수 | 부호 바뀜 (절댓값 ≥ 0.5만) | 평균 절댓값 Δp3 | k92_w / k92_hb 키 결정 수 | PFO>유지 / 고름>유지 결정 수 | 기록과 CSV 처음 다른 T | selection_status 개수 | 고르기 selected |
|---|---|---|---|---|---|---|---|---|---|---|
| REC | 11 | 5 (3900) | 10 | 0 | 1.67 | 0 / 0 | 8 / 1 | – | {'best_observed_feasible_sdmpc': 11} | – |
| OFF | 2 | 0 (없음) | 1 | 0 | 1.50 | 0 / 0 | 1 / 0 | 없음 | {'best_observed_feasible_sdmpc': 2} | 2 |
| B1 | 11 | 0 (없음) | 10 | 1 | 3.48 | 11 / 11 | 5 / 1 | 3000 | {'best_observed_feasible_sdmpc': 11} | 11 |

#### VB-43 — 결정별 (B1 / OFF / REC = RR 기록, 같은 T끼리; 모형 안 값)

| T | 쪽 | p2 | p3 | p4 | (173,p4) 하한 | 씨앗 묶임 | 나름/갱신 | 174 사슬 T+450 | 사슬 최대 | 직진 용량 묶임 비 | E_out/220 | OUTW (veh·h) | FEED-4 (몫) | Ω | 유령 끝 | PFO>유지 / 고름>유지 | selection_status | CSV=REC | 벽시계 (s) | 고르기 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3000 | B1 | 57.73 | 44.65 | 38.63 | 1509.6774 | 0.0 | 49/37 | 50.62 | 113.00 | 0.669 | 0.324 | 1019.94 | 144.01 (0.141) | 459.08 | 4.42 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 791 | selected |
| 3000 | OFF | 57.15 | 37.09 | 46.76 | 1509.6774 | 없음 | 49/37 | 171.69 | 176.13 | 0.835 | 0.126 | 1022.80 | 145.35 (0.142) | 470.01 | 4.83 | 참/거짓 | best_observed_feasible_sdmpc | 참 | 787 | selected |
| 3000 | REC | 57.15 | 37.09 | 46.76 | 1509.6774 | 없음 | 49/37 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 470.01 | 없음 | 참/거짓 | best_observed_feasible_sdmpc | – | 533 | REC: recorder not run (J1 record) |
| 3150 | B1 | 55.76 | 47.27 | 37.97 | 1509.6774 | 0.0 | 49/36 | 51.64 | 135.55 | 0.717 | 0.299 | 1008.50 | 148.13 (0.147) | 464.89 | 4.45 | 참/거짓 | best_observed_feasible_sdmpc | 거짓 | 660 | selected |
| 3150 | OFF | 55.29 | 35.59 | 50.12 | 1509.6774 | 없음 | 49/36 | 193.16 | 196.44 | 0.836 | 0.076 | 1013.05 | 149.57 (0.148) | 476.61 | 4.23 | 거짓/거짓 | best_observed_feasible_sdmpc | 참 | 728 | selected |
| 3150 | REC | 55.29 | 35.59 | 50.12 | 1509.6774 | 없음 | 49/36 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 476.61 | 없음 | 거짓/거짓 | best_observed_feasible_sdmpc | – | 520 | REC: recorder not run (J1 record) |
| 3300 | B1 | 54.26 | 48.77 | 37.97 | 1509.6774 | 0.0 | 49/37 | 58.10 | 157.00 | 0.775 | 0.372 | 997.67 | 144.39 (0.145) | 460.30 | 3.70 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 522 | selected |
| 3300 | REC | 54.16 | 31.84 | 55.00 | 1509.6774 | 없음 | 49/37 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 470.24 | 없음 | 참/거짓 | best_observed_feasible_sdmpc | – | 523 | REC: recorder not run (J1 record) |
| 3450 | B1 | 54.03 | 49.70 | 37.27 | 1509.6774 | 0.0 | 49/38 | 93.73 | 164.68 | 0.597 | 0.305 | 991.76 | 143.09 (0.144) | 460.86 | 3.94 | 참/거짓 | best_observed_feasible_sdmpc | 거짓 | 740 | selected |
| 3450 | REC | 53.77 | 28.09 | 59.14 | 1509.6774 | 없음 | 49/38 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 471.75 | 없음 | 거짓/거짓 | best_observed_feasible_sdmpc | – | 546 | REC: recorder not run (J1 record) |
| 3600 | B1 | 54.03 | 53.45 | 33.52 | 1509.6774 | 0.0 | 49/37 | 101.92 | 194.00 | 0.601 | 0.289 | 965.97 | 141.36 (0.146) | 451.47 | 4.82 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 593 | selected |
| 3600 | REC | 55.27 | 28.09 | 57.64 | 1509.6774 | 없음 | 49/37 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 462.17 | 없음 | 거짓/거짓 | best_observed_feasible_sdmpc | – | 416 | REC: recorder not run (J1 record) |
| 3750 | B1 | 51.96 | 58.32 | 30.72 | 1509.6774 | 0.0 | 49/39 | 107.45 | 190.55 | 0.556 | 0.306 | 933.73 | 141.90 (0.152) | 441.86 | 3.66 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 738 | selected |
| 3750 | REC | 56.45 | 23.59 | 60.96 | 1509.6774 | 없음 | 49/39 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 452.47 | 없음 | 참/거짓 | best_observed_feasible_sdmpc | – | 528 | REC: recorder not run (J1 record) |
| 3900 | B1 | 50.67 | 62.24 | 28.09 | 1509.6774 | 0.0 | 49/37 | 117.96 | 225.55 | 0.633 | 0.435 | 919.37 | 143.39 (0.156) | 424.62 | 5.47 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 743 | selected |
| 3900 | REC | 59.63 | 20.50 | 60.86 | 1509.6774 | 없음 | 49/37 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 436.37 | 없음 | 참/거짓 | best_observed_feasible_sdmpc | – | 544 | REC: recorder not run (J1 record) |
| 4050 | B1 | 49.17 | 63.74 | 28.09 | 1509.6774 | 0.0 | 49/34 | 91.88 | 264.64 | 0.903 | 0.652 | 918.99 | 140.66 (0.153) | 432.98 | 4.66 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 656 | selected |
| 4050 | REC | 59.07 | 21.78 | 60.15 | 1509.6774 | 없음 | 49/34 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 445.16 | 없음 | 거짓/거짓 | best_observed_feasible_sdmpc | – | 520 | REC: recorder not run (J1 record) |
| 4200 | B1 | 47.76 | 68.89 | 24.34 | 1509.6774 | 0.0 | 49/34 | 134.62 | 285.55 | 0.664 | 0.551 | 911.25 | 141.26 (0.155) | 429.55 | 4.56 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 738 | selected |
| 4200 | REC | 62.64 | 20.44 | 57.92 | 1509.6774 | 없음 | 49/34 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 443.13 | 없음 | 참/거짓 | best_observed_feasible_sdmpc | – | 562 | REC: recorder not run (J1 record) |
| 4350 | B1 | 46.26 | 70.39 | 24.34 | 1509.6774 | 0.0 | 49/37 | 140.89 | 297.55 | 0.699 | 0.614 | 886.60 | 132.74 (0.150) | 421.94 | 3.83 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 665 | selected |
| 4350 | REC | 58.20 | 20.39 | 62.42 | 1509.6774 | 없음 | 49/37 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 436.74 | 없음 | 거짓/거짓 | best_observed_feasible_sdmpc | – | 519 | REC: recorder not run (J1 record) |
| 4500 | B1 | 44.61 | 76.39 | 20.00 | 1509.6774 | 0.0 | 49/36 | 75.71 | 314.32 | 0.860 | 0.821 | 824.45 | 124.89 (0.151) | 400.63 | 6.73 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 701 | selected |
| 4500 | REC | 58.82 | 22.58 | 59.60 | 1509.6774 | 없음 | 49/36 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 417.80 | 없음 | 참/거짓 | best_observed_feasible_sdmpc | – | 481 | REC: recorder not run (J1 record) |

| 쪽 | 결정 수 | p3 ≤ 24.5 결정 수 (첫 T) | Δp3 수 | 부호 바뀜 (절댓값 ≥ 0.5만) | 평균 절댓값 Δp3 | k92_w / k92_hb 키 결정 수 | PFO>유지 / 고름>유지 결정 수 | 기록과 CSV 처음 다른 T | selection_status 개수 | 고르기 selected |
|---|---|---|---|---|---|---|---|---|---|---|
| REC | 11 | 6 (3750) | 10 | 3 | 2.14 | 0 / 0 | 6 / 0 | – | {'best_observed_feasible_sdmpc': 11} | – |
| OFF | 2 | 0 (없음) | 1 | 0 | 1.50 | 0 / 0 | 1 / 0 | 없음 | {'best_observed_feasible_sdmpc': 2} | 2 |
| B1 | 11 | 0 (없음) | 10 | 0 | 3.17 | 11 / 11 | 2 / 0 | 3000 | {'best_observed_feasible_sdmpc': 11} | 11 |

#### VB-41 — 결정별 (B1 / OFF / REC = RR 기록, 같은 T끼리; 모형 안 값)

| T | 쪽 | p2 | p3 | p4 | (173,p4) 하한 | 씨앗 묶임 | 나름/갱신 | 174 사슬 T+450 | 사슬 최대 | 직진 용량 묶임 비 | E_out/220 | OUTW (veh·h) | FEED-4 (몫) | Ω | 유령 끝 | PFO>유지 / 고름>유지 | selection_status | CSV=REC | 벽시계 (s) | 고르기 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3000 | B1 | 62.01 | 56.81 | 22.19 | 1045.1613 | 1.0 | 50/42 | 44.44 | 82.64 | 0.493 | 0.235 | 989.71 | 119.70 (0.121) | 459.75 | 5.51 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 784 | selected |
| 3000 | OFF | 66.18 | 54.20 | 20.61 | 없음 | 없음 | 50/42 | 171.27 | 171.27 | 0.890 | 0.058 | 993.84 | 120.55 (0.121) | 467.58 | 5.39 | 거짓/거짓 | best_observed_feasible_sdmpc | 참 | 615 | selected |
| 3000 | REC | 66.18 | 54.20 | 20.61 | 없음 | 없음 | 50/42 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 467.58 | 없음 | 거짓/거짓 | best_observed_feasible_sdmpc | – | 449 | REC: recorder not run (J1 record) |
| 3150 | B1 | 62.76 | 55.67 | 22.57 | 1045.1613 | 0.0 | 51/38 | 45.71 | 80.98 | 0.431 | 0.227 | 986.90 | 119.78 (0.121) | 443.94 | 4.89 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 625 | selected |
| 3150 | OFF | 65.76 | 55.01 | 20.23 | 없음 | 없음 | 50/38 | 178.46 | 179.78 | 0.896 | 0.076 | 989.68 | 119.26 (0.121) | 452.02 | 4.82 | 거짓/거짓 | best_observed_feasible_sdmpc | 참 | 755 | selected |
| 3150 | REC | 65.76 | 55.01 | 20.23 | 없음 | 없음 | 50/38 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 452.02 | 없음 | 거짓/거짓 | best_observed_feasible_sdmpc | – | 553 | REC: recorder not run (J1 record) |
| 3300 | B1 | 62.76 | 55.67 | 22.57 | 1045.1613 | 0.0 | 51/39 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 444.03 | 없음 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 526 | no_match |
| 3300 | REC | 66.70 | 54.11 | 20.19 | 없음 | 없음 | 50/39 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 449.85 | 없음 | 거짓/거짓 | best_observed_feasible_sdmpc | – | 550 | REC: recorder not run (J1 record) |
| 3450 | B1 | 67.26 | 51.17 | 22.57 | 1045.1613 | 0.0 | 51/41 | 23.39 | 65.16 | 0.493 | 0.193 | 966.85 | 125.97 (0.130) | 441.42 | 5.20 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 456 | selected |
| 3450 | REC | 70.37 | 50.61 | 20.02 | 없음 | 없음 | 50/41 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 449.41 | 없음 | 참/거짓 | best_observed_feasible_sdmpc | – | 553 | REC: recorder not run (J1 record) |
| 3600 | B1 | 65.04 | 50.42 | 25.54 | 1045.1613 | 0.0 | 51/39 | 59.33 | 81.68 | 0.480 | 0.191 | 937.53 | 124.46 (0.133) | 427.09 | 4.80 | 참/거짓 | best_observed_feasible_sdmpc | 거짓 | 759 | selected |
| 3600 | REC | 70.02 | 48.27 | 22.71 | 없음 | 없음 | 50/39 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 434.31 | 없음 | 참/거짓 | best_observed_feasible_sdmpc | – | 550 | REC: recorder not run (J1 record) |
| 3750 | B1 | 64.36 | 49.68 | 26.96 | 1045.1613 | 0.0 | 51/39 | 20.81 | 98.96 | 0.853 | 0.203 | 898.58 | 122.34 (0.136) | 419.47 | 4.78 | 참/거짓 | best_observed_feasible_sdmpc | 거짓 | 796 | selected |
| 3750 | REC | 70.41 | 50.59 | 20.00 | 없음 | 없음 | 50/39 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 428.39 | 없음 | 참/거짓 | best_observed_feasible_sdmpc | – | 513 | REC: recorder not run (J1 record) |
| 3900 | B1 | 64.25 | 48.70 | 28.05 | 1045.1613 | 0.0 | 51/39 | 42.98 | 92.02 | 0.699 | 0.192 | 901.97 | 127.97 (0.142) | 408.08 | 4.76 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 756 | selected |
| 3900 | REC | 67.41 | 53.59 | 20.00 | 없음 | 없음 | 50/39 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 418.31 | 없음 | 거짓/거짓 | best_observed_feasible_sdmpc | – | 367 | REC: recorder not run (J1 record) |
| 4050 | B1 | 62.37 | 48.58 | 30.05 | 1045.1613 | 0.0 | 51/37 | 81.77 | 99.29 | 0.434 | 0.185 | 876.35 | 128.56 (0.147) | 404.45 | 3.68 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 732 | selected |
| 4050 | REC | 69.14 | 47.59 | 24.27 | 없음 | 없음 | 50/37 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 411.72 | 없음 | 거짓/거짓 | best_observed_feasible_sdmpc | – | 300 | REC: recorder not run (J1 record) |
| 4200 | B1 | 61.88 | 45.58 | 33.54 | 1045.1613 | 0.0 | 51/37 | 36.36 | 80.27 | 0.675 | 0.251 | 856.99 | 129.67 (0.151) | 388.07 | 3.72 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 729 | selected |
| 4200 | REC | 69.14 | 47.59 | 24.27 | 없음 | 없음 | 50/37 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 395.91 | 없음 | 거짓/거짓 | best_observed_feasible_sdmpc | – | 151 | REC: recorder not run (J1 record) |
| 4350 | B1 | 59.25 | 48.21 | 33.54 | 1045.1613 | 0.0 | 51/39 | 31.75 | 79.77 | 0.630 | 0.247 | 846.02 | 129.22 (0.153) | 373.20 | 3.63 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 634 | selected |
| 4350 | REC | 67.64 | 49.09 | 24.27 | 없음 | 없음 | 50/39 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 380.99 | 없음 | 거짓/거짓 | best_observed_feasible_sdmpc | – | 374 | REC: recorder not run (J1 record) |
| 4500 | B1 | 59.25 | 48.21 | 33.54 | 1045.1613 | 0.0 | 51/39 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 365.65 | 없음 | 거짓/거짓 | best_observed_feasible_sdmpc | 거짓 | 354 | no_match |
| 4500 | REC | 67.64 | 49.09 | 24.27 | 없음 | 없음 | 50/39 | 없음 | 없음 | 없음 | 없음 | 없음 | 없음 (없음) | 372.33 | 없음 | 거짓/거짓 | best_observed_feasible_sdmpc | – | 144 | REC: recorder not run (J1 record) |

| 쪽 | 결정 수 | p3 ≤ 24.5 결정 수 (첫 T) | Δp3 수 | 부호 바뀜 (절댓값 ≥ 0.5만) | 평균 절댓값 Δp3 | k92_w / k92_hb 키 결정 수 | PFO>유지 / 고름>유지 결정 수 | 기록과 CSV 처음 다른 T | selection_status 개수 | 고르기 selected |
|---|---|---|---|---|---|---|---|---|---|---|
| REC | 11 | 0 (없음) | 10 | 4 | 2.04 | 0 / 0 | 3 / 0 | – | {'best_observed_feasible_sdmpc': 11} | – |
| OFF | 2 | 0 (없음) | 1 | 0 | 0.80 | 0 / 0 | 0 / 0 | 없음 | {'best_observed_feasible_sdmpc': 2} | 2 |
| B1 | 11 | 0 (없음) | 10 | 1 | 1.39 | 11 / 11 | 2 / 0 | 3000 | {'best_observed_feasible_sdmpc': 11} | 9 |

