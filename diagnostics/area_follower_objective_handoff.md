# Ω follower ranking와 두 global-TTT veto 정합

2026-09-10. `area_follower_objective.patch`는 새로운 작은 helper와 canonical adapter builder/area runtime 두 접점만 바꾼다. vendor 수정, class 복제, production AST 실행, β 재적용, nonzero offset 강제는 없다.

**초기 통합 이력:** parent가 patch를 production에 적용했다. 회귀를 실제 `evaluation.controllers.area_follower_objective` import로 옮긴 뒤5tests가 다시 PASS(0.298s)했다. 그 시점의 역사적 helper SHA-256은 `fc6d017c7e780f1f4f49281ac3cf8567d612ab5672f4ed7a18c9307ee41ce9b5`다. 이후 확인된 정련 후단 불일치와 적용된 수선은 [area_phase_finalization_handoff.md](area_phase_finalization_handoff.md)를 따른다. 현재 helper hash로 이 초기 hash를 사용하지 않는다.

기존 actual `LinkAgentWuFollower`가 상속한 `_rollout_horizon_ttt`는 patched endpoint를 호출해도 `point.objective`나 Ω `point.ttt` 대신 `point.freeway_ttt + point.urban_ttt`를 반환한다. 이 때문에 offset guard는 Ω 목적이 좋아져도 global TTT가0.5% 개선되지 않으면 offset0을 선택한다. `solve`의 NashResult.objective_value도 같은 global 값을 받는다. `probe_offset_objective_veto.py`는 실제 메서드 및 원 guard 식을 호출하여 이 소비자 불일치를 재현했다. endpoint response만 합성한 call-path 재현이며, VISSIM 성능 결과를 생성한 것이 아니다.

새 helper는 `control_area_enabled=True`에서만 같은 canonical endpoint의 **전체 objective**를 follower ranking/offset guard에 반환한다. endpoint가 이미 ΩTTT−βTD와 기존 추가 비용을 합쳤으므로 helper는 β를 다시 빼지 않는다. `offset_keep_margin`은 solve 실행 중에만0으로 두고 finally 원복한다. 원 guard의 수치 오차1e−9를 넘는 엄격한 J 개선만 offset을 유지한다. J가 음수일 때 기존 `J_on*1.005`를 쓰는 부호 오류를 피하며 동률·악화는0으로 돌아간다. OFF 경로는 원 메서드를 그대로 호출하고 설정/진단을 추가하지 않는다.

또한 area mode에서만 `stackelberg_fallback_guard_use_rollout_ttt=False`로 기존 objective 비교 분기를 사용한다. 이 분기의 `objective_gain=fallback−leader`, `objective_worse=leader>=fallback−1e−12`는 음수에서도 유효하다. moderate terminal/completion 악화 때 요구하는5% 기준은 `max(abs(fallback),1)`에 곱하므로 부호를 뒤집지 않는다. severe terminal/completion 거부는 그대로 남는다. 같은 cfg의 area mode를 끄고 installer를 다시 호출하면 원 설정을 복원한다.

flow_feedback의 actual n7 caller 감사: `StackelbergWuMeteredController._evaluate_fallback_candidates`는 PFO에 대해서도 `_leader_evaluation_base`로 future endpoint를 평가하고 같은 `leader.objective_terms`를 호출한다. 따라서 현재 n7의 leader/PFO 후보는 같은 penalty 정의로 비교되며 β를 두 번 보상하지 않는다. base `_make_fallback_evaluation`의 frozen-state 경로는 이 override에 가려진다. 이 결론을 모든 다른 controller variant로 일반화하지 않는다.

metadata 계약:

- `NashResult.objective_value`: 해당 endpoint의 전체 Ω 목적값 J.
- `control_area_follower_ttt_veh_h`, `ttd_veh`, `near_score_veh_h`, `additional_cost_veh_h`, `objective_veh_h`: 서로 구분한 Ω 성분.
- `distributed_response_rollout_ttt`, `...freeway_ttt`, `...urban_ttt`: 기존 의미의 global TTT. J를 음수 TTT로 기록하지 않는다.
- `wu_faithful_offset_ttt_on/off`: 기존 의미의 global TTT. 실제 guard 비교값은 `control_area_offset_on/off_objective_veh_h`에 별도로 기록하고 ΩTTT/TD도 함께 기록한다.
- `control_area_offset_guard_evaluated`, `control_area_offset_keep_margin=0`, `control_area_fallback_uses_objective=1`: 적용 경로를 명시한다.

초기 회귀 **5 tests PASS(0.302s)**. 실제 follower.solve를 실행하고 비용이 큰 내부 검색만 원 offset guard AST를 포함한 bounded fixture로 대체했다. ΩJ 개선/globalTTT 악화, 음수J 동률/악화, OFF 원 동작, 예외시 scope 원복, 실제 fallback comparator의 negativeJ 및 severe 조건을 검사했다. 합성 endpoint response를 사용하므로 실제 ledger/물리 rollout은 최종 main preflight에서 별도로 확인한다. worker 재설치와 controller 재설치는 중복 wrapper를 만들지 않는다.

stale guard diagnostics 점검: `_solve_followers:4125`는 `ControlAction.uncontrolled` 새 객체에 previous.green_times와 vsl만 복사한다. previous.diagnostics를 복사하지 않아 현재 분기에서 지난 결정의 `wu_faithful_offset_ttt_*`가 남아3회 endpoint sequence 검사에 걸리는 문제는 없다.

후속 관측으로 대체됨: 완료된 실제 t3300 preflight의 네 반환쌍 모두 base 평가 뒤 녹색이 바뀌었다. 실제 `phase_price_in_gne=False`이므로 원인은 pending GNE commit이 아니라 `LinkAgentWuFollower.solve` 후단 `apply_phase_price_refinement`다. 최초 쌍33현시/max42초 변경이 확인되었고, 기존 정련을 첫 Ω 채점 전 한 번 수행하는 수선을 parent가 적용했다. 최종 leader/PFO 재평가와 β 중복 여부에 대한 위 수치 근거는 그대로이며, 새 수선 및 실제 production10tests PASS는 별도 phase-finalization 문서에 기록했다.

재현: `python -m diagnostics.prepare_area_follower_objective`, `git apply --check diagnostics/area_follower_objective.patch`, `python -m unittest diagnostics.test_area_follower_objective -v`. patch 적용 후에는 생성기를 다시 실행하지 말고 actual imports 회귀와 실제 main preflight를 수행한다. parent가 통합 및 VISSIM 실행을 맡는다.
