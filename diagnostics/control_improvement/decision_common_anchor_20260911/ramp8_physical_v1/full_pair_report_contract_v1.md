# Seed13·17의 9000초 기준/폐루프 결과 보고 계약

기존 `diagnostics/summarize_fast_nc.py` 출력의 비교 규약이다. 새 추출기·모델·실행 절차를 추가하지 않는다. 현재 설정의 `control_area_objective.beta_seconds=0`이므로 모델 목적함수는 `J=TTT`이며 **처리량 보상 없이 TTT를 줄이는 진단**이다. TTD·소실·미삽입·종료 재고를 별도 결과로 보고한다.

## 비교 단위와 완료 근거

seed13과17 각각 같은 실제 망·수요표·배율·9000초 길이·제어 시작 시각의 NC/CL을 짝지어 비교한다. 우선 seed별 원값·차이·TTT 감소율 `100×(NC−CL)/NC`를 제시하고 서로 다른 seed를 직접 대조하지 않는다. 전체0–9000초와 실제 `ControlStartSec` 이후를 구분한다. 끝9000초의 새 명령은 교통 노출0초다. 두 seed의 평균만으로 통계적 유의성이나 일반적 개선을 주장하지 않는다.

정본 런은 `--completion-receipt`로 만든 `summary.json.schema=physical-run-summary/v1`과 원 completion의 `completed`, `exit_code`, `owned_native_alive`, `errors`, `native_execution_passed`를 확인한다. `completion_evidence.watchdog_exit_code`는 CScript 종료 코드가 아니다. fast NC는 `schema=fast-nc-summary/v1`와 `run.json`을 사용한다. fast baseline 재사용은 부모가 요구한 seed13의 완전9000초 궤적 동치 게이트를 먼저 통과해야 하며, fast에는 없는 head·결정·SG 기록의 동치를 만들어 쓰지 않는다. `common_source_inventory_rechecked=false`이므로 summary 자체는 공통 망·수요·형상 동치 증명이 아니다. 실제 seed는 런 manifest/readback을 따르고 준비 JSON의 seed13 표기를 seed17 실행의 seed로 오인하지 않는다.

## 보고할 실제 필드

아래 `S`는 `summary.json`, `M`은 `area_metrics.json`이다.

| 항목 | 정확한 필드 / 계산 | 집계 주의 |
|---|---|---|
| Ω TTT | `S.ttt_veh_h` = `M.ttt_veh_h` | `M.boundaries`, `M.sampling`의0–9000초·1초 완전성·tail0 확인. 좌/우 적분은 통계적 신뢰구간이 아니다. |
| Ω TTD | `S.td_observed_plus_terminal_canonical` = `M.ttd_observed_plus_terminal_events` | `M.ttd_observed_exit_events` + `M.ttd_terminal_exit_inferred_events`를 분리한다. 고유 차량 수 대신 사건 수이며 `M.ttd_repeat_exit_events`가 별도 존재한다. |
| 진입·수지 | `M.observed_entry_events` + `M.appeared_inside_events`; `M.closure.max_abs_residual_veh` | `M.reappeared_inside_events`는 appeared의 부분집합이므로 다시 더하지 않는다. 첫 관측은 입력 ID별 실제 삽입과 다르다. |
| 끝 재고·미확인 소실 | `S.censored_end_n`, `S.unknown_inside_disappearances`; 위치는 `M.unresolved_inside_disappearances_by_link` | 끝 재고는 검열된 잔여이며 유출이 아니다. full 초기 공망 규약에서 진입−TTD−소실=끝 재고인지 확인한다. |
| native 제거·대조 | `S.native_removals`, `S.native_removals_inside`, `S.native_removals_outside`, `S.native_removals_unknown_membership`, `S.removal_matches`, `S.unmatched_native_removal_indices` | `S.removal_matches[].unique_match/inside/terminal_TD_inference_collision`를 함께 본다. 제거 수를 unknown과 무조건 더하거나 TTD에서 다시 빼지 않는다. |
| 미삽입 수요 | `S.unfinished_inputs[].input_no/remaining_vehicles` | 명시적 native 종료 경고의 잔여다. 빈 배열이 관측 삽입=희망 수요를 증명하지 않는다. 실제 삽입·정상 유출·망 안 잔여와 별개다. |
| 모든 물리 도로의 체류 | `M.physical_link_residence[link].inside/ttt_veh_h/slow_veh_h` | Ω합계는 inside=true만. slow는 <5km/h이며 아래 road stopped≤1과 다르다. |
| 경고·재현성 | `S.native_ERR[].counts/sha256`, `S.producer_sha256`, `S.geometry`, `S.membership_network` | `S.elapsed_sec_not_benchmark`는 사후 집계 시간이며 controller/native 계산 시간으로 쓰지 않는다. |

**TTD 판정 함정:** full summary의 `S.status`와 `S.TD_usable_for_ranking`는 `terminal_removal_collisions`만 반영한다(`summarize_fast_nc.py:350–359`). unknown이나 모호/미대조 제거가 있어도 complete/true일 수 있다. 기존 `demand_sweep/fw080_urban050_cooldown9000/results/summary.json`도 unknown343에서 complete/true다. 최종 보고에서는 충돌·unknown·모호 대조·미대조를 각각 공개하고, 필요 검토가 남으면 TTD 완전 인증으로 표시하지 않는다. 수지0은 표본 집계가 닫힌다는 뜻이며 표본 사이 모든 경계 이동을 관측했다는 뜻이 아니다. native LDP/명령 적용 통과와 독립 LSA 실패도 분리한다.

## 지역 전파와 회복

- `area_timeseries.csv`: `sim_sec`, `inside_vehicles`, `ttt_veh_h_cumulative`, `ttd_observed_plus_terminal_cumulative`로 동일 시각의 누적량·재고를 비교한다. 제어 이후/부분창 TTT·TTD는 양 끝 누적값의 차이로 계산하고 누적행들을 합산하지 않는다. 사건 열은 해당 간격량이므로 `(시작,끝]`에서 합산한다.
- `fw_cells_30s.csv`: `(sec,direction,cell)`로 대응하고 `n`, `stopped`, `mean_speed_kph`, `speed_eligible_n_ge5`로 혼잡의 상·하류 전파를 본다. 셀 번호는0–20이다. 빈 속도는 null이며 속도 비교는 n≥5만. 30초 관측에서 정밀한 충격파 속도·1초 peak를 만들지 않는다.
- `roads_30s.csv`: `(sec,link)`의 `n/stopped/mean_speed_kph`; `road_windows_900s.csv`: `(start_sec,end_sec,link)`의 `initial_n/entry/normal_other_link_exit/absent/matched_native_removal/end_n/end_stopped/closure`. `absent` 안에 대조 제거가 포함되므로 둘을 더하지 않는다. 도로 간 정상 이탈은 Ω TTD와 다르다.
- `road_recovery.csv`: `peak_n/peak_n_sec/peak_stopped/peak_stopped_sec`, `final_n/final_stopped`, `last_window_normal_exit_minus_entry/last_window_absent/last_window_native_removal`. 재고 감소가 정상 방출인지 제거·유입 감소인지 나누고, 마지막 상태 하나로 회복 완료를 선언하지 않는다. peak는1초 전체 관측의 최초 최대 시각이며30초 표의 최대와 다를 수 있다.

도로 CSV는 코드의 고정 `ROADS` 목록만 포함한다. 예를 들어10481은 목록에 없으므로 없는 행을0으로 간주하지 않는다. 기존 full 출력에서10481의 정확한 전체 체류·<5km/h 체류는 `M.physical_link_residence['10481']`로 비교할 수 있지만 ≤1km/h 정지 체류·30초 회복은 그 출력만으로 만들 수 없다. 물리 도로·42개 셀·Ω 체류는 공간 범위가 겹치므로 합산하지 않는다.

## 9000초 tail과 최종 판정

준비 자료의 `tail_demand`는 **4500초에서 시작한 마지막 native 수요 구간을9000초까지 유지**한다. `cooldown9000`이라는 폴더명은 수요를 끈 배출 실험의 뜻이 아니다. native 읽기 확인과 선언 수요를 유지하고 회복을 위해 tail을0으로 바꾸지 않는다. `source_inputs_900s.csv`의 `first_observed_insertions/seen_id_reappearances_excluded`는 격리 source74→input1098,66→1100,69→1101에만 해당한다.1099의 source26은 합류10480도 받아 제외돼 있고1초 사이 source를 지나간 삽입은 빠질 수 있어 이 표를 전체 희망 수요로 쓰지 않는다.

최종 표는 seed별 **TTT 감소율·TTD 변화·진입·끝 재고·unknown·제거·미삽입**을 함께 놓는다. β0의 TTT 감소를 처리량 향상과 동일시하지 않으며10%에 미달하면 그 수치를 그대로 적는다. 실행 완료, 모델/명령 유효성, 실제 교통 효과, 실시간, GNE는 별도 판정이다. 기존 qualification의 `decisions[t].decision_budget.wall_sec`, `gap_coverage.final_check_complete/complete_owner_count/owner_count/maximum_finite_candidate_gap`, `GNE_certified`, `written_command_binding`과 native 적용 검증을 재사용한다. full summary에는 이 판정이 없으므로 거기서 추론하지 않는다. 전체 결정 시간의 모든 기록을150초와 비교하며 시간 한도로 잘린 gap은0으로 바꾸지 않는다. 녹색·offset·VSL·8미터의 실제 명령 변화와 적용을 모두 기록하고, 첫 도시 명령 행 추가를 모든 신호 타이밍 변경으로 세지 않는다.

근거: `diagnostics/summarize_fast_nc.py`, `scripts/measure_control_area.py`, `evaluation/controllers/control_area_objective.py`, `evaluation/controllers/shared_approach.py::demand_amount`, 기존 cooldown9000의 summary/area_metrics/prepared JSON, `fast_nc9000_seed17_eligibility_v1.txt`. 기존 결과와 소스 정의만 확인했으며 새 FZP·모델·native 작업은 수행하지 않았다.
