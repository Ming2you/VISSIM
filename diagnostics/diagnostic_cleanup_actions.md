현재 생성물52개를 다시 대조했다. **지금 제거 가능한34개, 소비자 이전이 먼저인11개, 실제 도구라 유지할4개, 미터 production 커밋까지 보류할3개**다. 파일별 정확한 경로와 tracked 여부는 `diagnostic_cleanup_actions.json`에 있다. 이번 작업에서는 삭제·source 수정·manifest 재생성·FZP 처리를 하지 않았다.

34개는 이미 통합된 변경의 patch 사본과 소비자가 없는 생성기 묶음이다. follower/phase 후보와 생성기, signal/offset 후보와 생성기, observation/transit 생성기, 이전 개별 patch들이 포함된다. 그중 tracked 파일은 `diagnostic_lever_profiles.patch` 하나이며 나머지는 로컬 생성물이다. 삭제 목록 내부의 생성기→후보 의존성은 묶어서 제거한다. 보존할 생성기에 남은 출력 patch 이름은 읽기 의존성이 아니다.

가장 먼저 없앨 helper는 committed `probe_sc2001_corridor_replay.py:64`의 `proposal_module()`이다. 외부 tracked caller는0이고 아래5개 로컬 진단이 호출한다.

| 현재 소비자 | 호출 위치 | 필요한 최소 이전 |
|---|---|---|
| `probe_all_area_snapshots.py` | 24/30, 72/98 | proposal 생성·urban body 덮기 제거. 실제 초기화 후 installed endpoint로 같은5후보×4β/재평가 검사 유지 |
| `probe_corrected_prediction_fidelity.py` | 28/42/44 | 실제 현재 config로 투영하고 같은 시점의 실측 action을 사용. proposal/count monkeypatch 제거 |
| `probe_direct_branch_order.py` | 76/106/110 | 위 초기화로 전환하고 `sys.settrace` 관찰과 물리 geometry 분석은 유지 |
| `probe_offramp_feedback_trace.py` | 44/58/127 | 위와 동일. 관측용 trace만 유지하고 제안 urban body 교체 제거 |
| `probe_single_transfer_grid.py` | 22/29 | 이전한 `probe_all_area_snapshots`에 통합. 현재 production single-transfer가 기본이므로 별도 monkeypatch wrapper 제거 |

이전 시 `probe_model_area_integration.build_projected(final_config, state_path, previous_path)`가 실제 `runtime_setup.configure_runtime`을 실행하게 한다. 이렇게 해야635 지원·FW 정확 초기 count·최종 재투영·meter context가 **초기 투영 전부터** 동일하다. 투영이 끝난 cfg에 `physical_vehicle_counts=True`만 붙이면 원래 N은 고쳐지지 않는다. `evaluate_price_point`는 설치 후 import한다. grid는 직전 action, fidelity/trace는 원래 명시한 같은 시점 action을 유지한다. 새로운 결과는 실제 source SHA와 새 파일명으로 기록하며 과거 proposal 결과를 덮어쓰지 않는다.

5개 이전 뒤 helper와 그 전용 `types` import를 제거하고 `area_production_test_migration.md`의 역사 helper 설명을 갱신하면 된다. canonical module을 반환하는 또 다른 adapter/compatibility helper는 만들 필요 없다. 기존 fixture·CLI의 production 경로는 이미 helper를 호출하지 않는다.

나머지11개를 해제하는 선행 작업은 다음과 같다.

| 보류 파일/묶음 | 선행 작업 |
|---|---|
| `audit_snapshot_readonly.patch`, `diagnostic_profile.patch` | tracked `test_audit_snapshot_windows.patched_source`, `test_diagnostic_profile.integration_source`에서 이미 적용된 현재 source만 읽도록 변경. 지금도 정상 경로는 patch를 읽지 않지만 옛 fallback이 남아 있다 |
| `freeway_count_geometry.patch` | `test_freeway_count_geometry.patched_functions`를 실제 adapter 함수로 전환. raw 초기 count 검사는 현재 `test_freeway_initial_count`와 중복 범위를 확인 |
| `build_area_routes_and_sc2001_patch.py`, `prepare_sc2001_urban_patch.py`, `proposed_area_dynamic_routes.py`, `sc2001_corridor_proposal.py` | 위5개와 `probe_area_package_runtime`의 isolated 설치 제거; 아래 옛 receiving 테스트 이전 |
| `prepare_freeway_initial_count_patch.py` | `probe_all_area_initial` 및 위 grid/fidelity/trace의 `installed_proposal` 제거. 실제 config에서 flag를 켠 뒤 투영 |
| `prepare_legsplit_receiving_patch.py`, `prepare_legsplit_single_transfer_patch.py` | 위 grid와 `test_legsplit_receiving`의 제안 재조립 제거. 후자는 실제 실패 pickle을 현재 `test_legsplit_single_transfer`로 검사하는 경로가 이미 존재한다 |
| `prepare_area_failfast_patch.py` | 옛 `probe_area_full_decide.install_proposals`/worker 설치를 제거. 실제 main 실행은 현재 `run_area_production_preflight.py`로 대체 가능 |

**고정 OFF 근거는 유지한다.** `fixed_source_reference.py`, fixture archive의6056c94/3299040 blob, 현재 OFF 비교 테스트는 삭제 대상이 아니다. 옛 clipping 버그 재현을 별도로 남길 경우도 고정 source/fixture로 남기고, 최신 파일 위에 옛 patch를 다시 적용하지 않는다.

반드시 유지할 실제 도구는 `prepare_area_candidate_configs.py`, `prepare_native_offset_network.py`, `replay_freeway_candidates.py`, `prepare_dynamic_area_routes.py`다. 마지막 파일은 실제 pinned route 입력 생성기다. `physical_projection_support_635_proposal.json`을 포함한 **모든 runtime 입력·calibration·해시 자료·실행 결과는 유지**한다. 미터3개(`area_meter_finalization.patch`, candidate, 생성기)는 검토 시점 HEAD에 production 변경이 아직 커밋되지 않았으므로 별도 보류했다.
