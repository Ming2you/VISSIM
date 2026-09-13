# Seed13·17 최종 9000초 비교 점검

2026-09-13 소스 검토. 실제 native/model/FZP 집계는 실행하지 않았다. 기준 문서는 `full_pair_report_contract_v1.md`이며 아래는 누락 방지용 실행·판정 체크다.

## 입력과 완료

- seed13 NC: `codex_phys8_fidelity_fw080_u050_nc9000_s13_v1`; 예정 CL retry: `codex_fid_cl9000_s13_v2`. 실패한 이전 CL3150은 성공 결과에 섞거나 receipt를 고치지 않는다. seed17 이름은 실제 launcher 확정값을 쓴다.
- 각 seed 안에서 NC/CL의 실제 network/demand_profile SHA, 8미터 형상·mapping, 9000초 길이, 150초 주기, 실제 제어 시작900초를 맞춘다. 실제 Seed는 launch 요청과 provenance를 확인한다. 준비 데이터의 seed13 표시는 seed17 실행값이 아니다.
- `selected_control_completion.py:37`의 기존 seed13 하드코딩은 별도 승인 수정 완료. sibling `launch.json`의 `execute=true`, Name/절대 OutDir/정수 SimPeriod를 검증하고 strict positive integer Seed와 provenance seed를 exact 비교한다. 새 receipt의 `launch_request.path/sha256/expected_seed`가 기대값 근거다. source SHA: `cd08cdf33f471432e47d2fd99f3112fc5f5b592533c602c61cef2081682b19f4`. 기존 NC13 receipt는 변경하지 않는다.
- 원 receipt에서 `completed=true`, `exit_code=0`, `owned_native_alive=false`, `terminal_sec=9000`, `errors=[]`, `native_execution_passed=true`를 확인한다. `native_lsa_com_coverage_passed`는 독립 판정으로 그대로 표기한다. wrapper exit는 CScript exit 관측값이 아니다.
- fast NC seed13의 전체9000 동치 gate는 **FAIL**이므로 fast baseline 지원 제안은 미적용·사용 불가다. 두 seed 모두 canonical NC를 사용한다.
- 아래 qualifier는 CL의 모든 joint source SHA를 현재 파일과 대조한다. CL 검증 완료 전 source/config를 다시 바꾸면 안 된다. NC/CL watchdog 버전 동일성을 자동 증명하지 않으며, baseline 물리 network/demand/mapping의 pin과 각 run의 기록된 provenance를 구분한다.

## 기존 도구의 정확한 명령

작업 디렉터리는 `.worktrees/control-full-review`. 아래는 준비된 명령이며 **양쪽 run의 완료/종료 확인 후에만** 실행한다. 모든 label/output은 미존재 경로를 사용한다.

```powershell
$pythonExe = 'C:/Users/alsrj/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$diagDir = 'diagnostics/control_improvement/decision_common_anchor_20260911/ramp8_physical_v1'
$nc13 = 'codex_phys8_fidelity_fw080_u050_nc9000_s13_v1'
$cl13 = 'codex_fid_cl9000_s13_v2'
& $pythonExe -B -X utf8 "$diagDir/qualify_fast_np_closedloop.py" $cl13 'final_cl9000_s13_v2_qualification_v1' --baseline $nc13 --start 900 --end 9000 --detail-start 4500
& $pythonExe -B -X utf8 diagnostics/summarize_fast_nc.py --run "evaluation/runs/$cl13" --out "$diagDir/final_cl9000_s13_v2_full_v1" --completion-receipt "evaluation/runs/$cl13/completion_receipt.json"
```

NC13의 이미 생성된 `fidelity_nc9000_s13_full_v1/{summary.json,area_metrics.json,area_timeseries.csv,...}`를 재사용한다. 완료 provenance·원 receipt와 해당 summary의 `completion_evidence`를 연결하고, 같은 FZP를 불필요하게 다시 집계하지 않는다.

seed17도 동일 CLI를 사용한다. `$nc17`, `$cl17`은 실제 확정 이름을 대입하며 다음 세 호출만 필요하다: (1) CL17 qualifier의 `--baseline $nc17 --start 900 --end 9000 --detail-start 4500`; (2) NC17 summary; (3) CL17 summary. 두 summary 모두 자신의 `--completion-receipt`가 필수이며 `--out`은 별개의 새 diagnostics 경로다. summary에는 `--start/--end` 옵션이 없다. 전체 길이는 receipt에서9000을 읽는다. 부분창은 기존 누적 CSV 양 끝 차이를 쓴다.

## Qualification 결과 체크

`qualify_fast_np_closedloop.py`는 두 완료 run의 seed·network·demand 동일성, 첫1..900초 raw FZP 동치, 900초 state/head history exact(명시된5개 identity 필드만 제외)를 확인한다. 213같은 고정 행수를 가정하지 않고 각 명령의 자신의 binding·row count를 확인한다.

| 확인 항목 | 결과 필드 / 요구 조건 |
|---|---|
| 전체 검증 | `completed=true`, `source_changes=[]`; `warmup_prefix.all_raw_data_rows_equal=true` 및 비어 있지 않은 prefix; `initial_observations_and_head_history_exact=true` |
| 전 결정 포함 | `decisions` 키가900,1050,…,9000의55개. 마지막9000 명령의 교통 노출은0초이며 실제 노출구간은54개 |
| 실제 명령 결합 | `decisions[t].written_command_binding`: prewrite/written binding=true, action JSON/CSV SHA 및7개 물리 필드/ordered physical row SHA 일치. 17도시 owner와 SC9101..9108의8미터 완전성 |
| NP·NUF | `model_quantity_constraints.np`는17도시 signed net inflow cap; `nuf`는 predicted accepted mainline merge equality ±40. 각 decision 진입에서 산출한 `decision_entry_nuf_target_veh_h`와 모든 attempted 후보 target 일치, `fixed_nuf_this_decision=true`. 다음 decision의 target은 새 상태에서 갱신할 수 있음 |
| 모델과 실제 구분 | `forecast_quality_or_actual_nuf_attainment_certified=false` 유지. 모델 quantity feasible이 actual NUF ±40 실현·예측 정확도·native capacity 증명은 아님 |
| gap | `gap_coverage.final_check_complete/complete_owner_count/owner_count/maximum_finite_candidate_gap` 기록. 미완료 owner gap과 미완료 전체 max는 null. validated actual hold에는 owner count가 저장되지 않을 수 있으므로 임의0/19를 만들지 않음. `GNE_certified=false` 유지 |
| 실제 변경·시간 | `changes_from_previous_written_action.physical_rows_by_kind/eight_written_meters`로 녹색·offset·VSL·8미터를 보고. 첫 signal 행 추가를 모든 timing 변경으로 세지 않음. `decision_budget.wall_sec` 전 결정의 원값·150초 초과 수/최대값; qualifier `wall_sec`는 후처리 시간 |

`native_ramps_by150s`, `sc1004`, `corridor_52_66_71`은 위 명령에서는4500–4950초 **450초 상세창만** 다룬다. 이 표를900–9000의 실제 NUF·상세 도로 전 구간 인증으로 쓰지 않는다. 필요하면 이미 확보한 전체 summary/30초 도로·셀 표를 재사용한다.

## 최종 표와 TD/삭제 판정

S=`summary.json`, M=`area_metrics.json`. 각 seed의 NC/CL 원값과 차이를 먼저 제시하고 TTT 감소율은 `100*(NC-CL)/NC`(NC>0)로 계산한다. 두 seed의 평균만으로 통계적 유의성·일반적 개선을 주장하지 않는다.

| 필수 결과 | 정확한 필드 |
|---|---|
| Ω TTT | `S.ttt_veh_h`, M의 `boundaries/sampling/closure`(1초 완전관측, tail0) |
| TD | `S.td_observed_plus_terminal_canonical`; `M.ttd_observed_exit_events`, `M.ttd_terminal_exit_inferred_events`, `M.ttd_repeat_exit_events` 별도. 고유 차량 수와 사건 수를 혼용하지 않음 |
| 진입·잔여·소실 | `M.observed_entry_events`, `M.appeared_inside_events`, `S.censored_end_n`, `S.unknown_inside_disappearances`, `M.unresolved_inside_disappearances_by_link`. reappeared는 appeared의 부분집합 |
| 제거 | `S.native_removals/inside/outside/unknown_membership`의 실제 전체 필드명은 `native_removals`, `native_removals_inside`, `native_removals_outside`, `native_removals_unknown_membership`; `removal_matches[].unique_match/inside/terminal_TD_inference_collision`, `unmatched_native_removal_indices`, `terminal_removal_collisions` |
| 미삽입 | `S.unfinished_inputs[].input_no/remaining_vehicles`; 빈 경고 배열은 희망 수요의 실제 삽입 완료 증명이 아님 |
| 근거 | `S.schema=physical-run-summary/v1`, `seed`, `terminal_sec`, `completion_evidence`, `native_ERR[].counts/sha256`, `producer_sha256`, `geometry`, `membership_network` |

**TD 판정은 S.status 또는 S.TD_usable_for_ranking만으로 통과시키지 않는다.** 현재 코드는 terminal-removal collision만 이 두 필드에 반영한다. 다음을 별도로 적용한다.

1. 충돌이 있으면 TD ranking 보류. unknown 소실>0, non-unique removal match, unmatched removal, membership 미확정이 남으면 표본 기반 TD 수치는 그대로 보고하되 완전 TD 인증·처리량 우월 주장은 보류하고 사유·수를 함께 적는다. 특히 inside 소실/제거의 방향과 크기를 공개한다.
2. 제거가 발생하면 unknown에 무조건 더하거나 TD에서 다시 빼지 않는다. 같은 사건이 두 표에 나타날 수 있고 과거의 정상 유출 사건은 그대로 유효하다. 실제 warning 대조를 바탕으로만 분류한다.
3. TTT 감소는 측정 결과로 보고할 수 있지만 CL에서 삭제·미삽입 증가 또는 진입 감소가 재고/체류를 줄였다면 이를 서비스 회복·처리량 개선의 증거로 승격하지 않는다. 소실 차량의 가상 체류시간을 만들어 보정 TTT를 계산하지 않는다. 진입·TD·끝 재고·unknown·제거·미삽입을 같은 표에 놓고 교통 효익은 제한적으로 판정한다.
4. β=0인 본 비교의 목적함수는 TTT이며 처리량 보상이 없다. 10% 미달·음의 개선은 그대로 보고한다. 양쪽 모두 불확실성이0이어도1초 표본 사이 이동까지 연속 관측한 것은 아니다.
5. 부분창900–9000의 TTT/TD는 `area_timeseries.csv`의9000 누적값−900 누적값. interval 사건 열은 `(900,9000]` 합계. 전체 초기 공망 수지 규칙을 부분창에 그대로 적용하지 않고900초 시작 재고를 포함한다.
6. 회복은 `road_recovery.csv`의 `last_window_normal_exit_minus_entry/last_window_absent/last_window_native_removal`을 구분한다. stock 감소를 전부 정상 방출로 세지 않으며9000 끝 재고는 censored이다.4500부터9000까지는 마지막 수요를 계속 유지하므로 'cooldown'을 무수요 배출 실험으로 해석하지 않는다.

`common_source_inventory_rechecked=false`인 summary는 망·geometry 동치 증명이나 명령 검증을 대신하지 않는다. 실행 완료 / 모델·명령 유효 / 실제 교통 효과 / 실시간 / GNE 판정은 각각 독립이다.

## 이번 검토의 수정·시험 범위

canonical controller/config 및 실제 run은 변경하지 않았다. root의 동결 예외 승인으로 completion helper와 기존 `diagnostics/test_selected_control_demand.py` Completion fixture만 수정했다. `python -B -X utf8 -m unittest diagnostics.test_selected_control_demand.Completion diagnostics.test_summarize_fast_nc_completion`:23 tests PASS,1.958초. seed13/17 정상, 양방향 seed mismatch, 잘못된 타입/비양수/누락/다른 run·period·execute 요청 FAIL, fixture 원본 bytes 불변을 확인했다. 기존 NC13 receipt 재작성 없음.
