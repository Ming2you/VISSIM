# 기록 6300초: scope 복원 수정 전후의 선택 결과 비교

`fidelity_recorded6300_context_v1`(무수정 재현 PASS)와 `fidelity_recorded6300_scope_fix_v1`(복원 수정 및 실패 증거 코드 적용 후 PASS)의 완료 산출물만 읽었다. 두 실행은 동일한 state_006300, 이전 action_006150 JSON/CSV 및 config 해시를 사용했고, 실행 중 source_changes는 모두 빈 배열이다. 본 비교에서 모델·FZP·native 실행/스캔 및 canonical 편집은 없다. 상세 경로·원본 SHA/크기는 sibling `fidelity_recorded6300_scope_comparison_v1.json`에 보존했다.

| 항목 | 수정 전 | 수정 후 | 판정 |
|---|---:|---:|---|
| 전체 기록 decision wall sec | 245.042854 | 252.920884 | 다름; 단일쌍 속도 인증 아님 |
| 실제 명령 7개 필드 | 동일 | 동일 | 전 필드 exact |
| writer 물리 명령 행 | 213 | 213 | ordered SHA 동일; CSV 전체 bytes도 동일 |
| 선택 목적함수 veh·h | 171.61282229893962 | 171.61282229893962 | exact |
| N_P 실제 / cap veh | 217.42990163976677 / 2400 | 동일 | exact; 제약 만족 |
| N_UF 실제 / target veh/h | 1683.9317048547193 / 동일 값 | 동일 | exact; 제약 만족 |
| 선택 응답의 model coverage | 1125/1125 | 1125/1125 | 108493 allocation·32040 state 검사 동일 |
| 6450초 예측 total_model_vehicles | 1649.3028913823257 | 동일 | raw state_summary exact |
| 6450초 예측 freeway_total_veh | 483.3285869564255 | 동일 | exact |
| 6450초 예측 raw freeway_mean_speed_kph | 103.83998526240991 | 동일 | exact |
| 선택 응답의 탐색 evaluations | 101 | 96 | 다름 |
| decision 전체 endpoint calls | 187 | 179 | 다름 |

7개 필드는 `N_P_star`, `N_UF_star`, `ramp_metering`, `vsl`, `green_times`, `offsets`, `inflow_outflow_allocation`이다. seven-fields SHA는 `403bfdd4263f316a0722b4d108b3abc4bdc766968799465fab0ed74a2ca71b45`, ordered physical rows SHA는 `f305068dfa6a78a34360a156084973ac88de36b93cb3e28b8b64b0f6920936cd`로 두 결과가 같다. 두 writer receipt의 prewrite/postwrite binding은 모두 true이며 실제 CSV SHA도 각 receipt와 일치한다.

선택 응답의 quantity_constraints 전체와 model_constraint_coverage 전체, 목적함수 및 주요 검증 스칼라는 exact이다. `prediction.state_summary`, `terminal_features`, `calibrated_state_summary`, `audit_calibration`도 각각 전체 JSON 값이 exact이다. 단, 선택 quantity의 창은 6300–6750초(450초), one-step prediction은 6300–6450초(150초)다. raw와 calibrated 값이나 두 창을 합쳐 해석하지 않았다.

두 실행 모두 486개 leader domain 중 [1,240,120]을 시도하고 index 1을 선택했지만, per-owner audit와 search history는 다르다. 선택 응답 모두 `interrupted_search_time_budget`, final_check_complete=false, finite_neighborhood_certified=false, maximum_finite_candidate_gap=null이다. 따라서 실제 선택 결과의 일치만 확인하며 전체 탐색 등가·완전한 GNE·실시간 인증은 하지 않는다.

소스 pin 차이는 area_follower_objective.py와 vissim_stackelberg_adapter.py 두 파일이다. fixed_inputs_token과 frozen_context_token은 달라졌으나 final_action_token과 response_token은 같다. 소스/context 토큰 차이를 물리값 차이로 취급하지 않는다. 원래 native 6300초 실패 원인은 여전히 미확정이고, 이 두 기록 재현은 모두 PASS였다. 두 receipt의 native_run=false 및 writer native_execution_status=pending이므로 후속 native 실행/9000초 완료를 입증하지 않는다.
