# 전체 결정 계측 경계

전체 결정의 병목은 **가격 배치, PFO, 예비 리더 평가, 상세 리더 평가, 각 follower 탐색과 최종 실현**을 분리해서 재야 한다. 현재 action의 `wu_faithful_solve_time_sec`는 선택된 응답 한 번의 시간이다. 전체 follower 시간 또는 전체 결정 시간으로 읽을 수 없다. 본 문서는 읽기 전용 소스 감사이며 새 MPC/endpoint/VISSIM 실행은 없었다. 14개 읽은 소스·설정·기존 결과의 SHA와 86개 실제 함수/클로저 주소는 `decision_profile_boundary_inventory.json`에 있다. 계측 수집기는 root가 별도로 구현한다.

기존 β300 t900 preflight(`wu-link_t900_beta300_20260910T021854343272Z/action.json`)에는 결정 209.286455초, 선택 follower 18.3267409초, proxy 9개, full 3개, PFO fallback 1개, `wu_price_rollout_count=43`, `price_local_scored=63`이 기록돼 있다. 이는 **그 역사적 빌드의 부분 계수**이며 새 v4 성능 측정값이 아니다. 43과 63을 서로 다른 정의를 확인하지 않고 더하거나, 18초를 3배/4배 하여 전체 시간을 추정하지 않는다.

## 1. 부모 프로세스의 배타적 stage

| Stage | 관측할 실제 함수 | 기록할 경계/결과 |
|---|---|---|
| 초기화 | adapter `main`, `build_config`, `runtime_setup.configure_runtime`, `build_priced_wu_link_controller` | 입력 로드/투영/런타임 설치/제어기 생성; 최적화와 별도 wall |
| 전체 가격 | `PricedWuLinkStackelbergController._maybe_refresh_signal_prices` → `StackelbergWuMeteredController._maybe_refresh_signal_prices` 및 설치된 adapter `install_phased_price_local.<locals>.patched` | 외부 refresh wall 하나, 하위 채널 wall·task 수·결과 가격 벡터; wrapper 중첩 합산 금지 |
| PFO incumbent | `StackelbergWuMeteredController._evaluate_fallback_candidates` | leader=None인 실제 follower solve, 그 이후 leader endpoint·score; 일반 후보와 별도 stage |
| 예비 평가 | `StackelbergMPCController._prefilter_leader_candidates` → 현재 `area_leader_objective._proxy_score_candidate` | 요청/NP 투영 좌표, 후보 순서, proxy J, 통과 index; follower solve를 하지 않는 점 구분 |
| 상세 평가 | `PricedWuLinkStackelbergController._evaluate_full_candidate` → Wu override | `(stage,index)`, 요청/투영/실현 NP·NUF, cache hit, 실제 follower 호출 여부, J/선택 여부 |
| follower 생성/탐색 | 아래 §3의 logical solve → `_solve_followers` | 모든 상세 후보 및 PFO 호출별 독립 시간·수렴·잔차·실제 국소 평가수 |
| leader 재평가 | 현재 `area_leader_objective._install_scoring_consumers.<locals>.base` | follower 최종 score와 별개의 leader endpoint, 동일 control/spec 여부 |
| 최종 선택/확정 | `_select_with_fallback_guard`, `_apply_output_closure`, adapter policy/actuation guards | 선택 전후 control fingerprint, 값 변화와 해당 score 연결 |
| 출력 직전 예측 | adapter `build_one_step_prediction` → `apply_post_guard_safety_evaluation` | 추가 endpoint/기준선 평가수; 비활성 분기는 0회 명시 |
| 직렬화 | `area_meter_finalization.assert_writer`, signal writer validation, `control_to_json_dict`, `write_action_csv` | 최종 scored action과 실제 출력 벡터/CSV 일치 |

Wu-link의 `_evaluate_candidate_set`는 `stackelberg_wu_metered.py:2713`에서 **직렬 override**한다. base의 process-pool 코드가 존재한다는 이유만으로 상세 leader 평가도 병렬이라고 보고하면 틀린다. 실제 process pool은 아래 가격 배치에서 별도로 발생한다.

`PricedWuLinkStackelbergController._evaluate_full_candidate:831`은 이미 각 후보의 wall/reuse를 `out.metadata`에 넣는다. 그러나 base `decide_with_info`는 `best_eval.metadata`만 최종에 합친다. 따라서 **각 함수 return의 evaluation**을 수집해야 탈락 후보 시간이 남는다. `_append_progress_event`는 일부 경로에서만 호출되고 Wu 직렬 override는 base의 후보 완료 이벤트를 모두 재현하지 않으므로 기존 progress JSONL만으로 전체 상세 평가를 세지 않는다.

## 2. 가격 task와 worker

대상 배치는 `_green_price_rollouts`, `_price_batch`(VSL·offset walk), `_phase_price_rollouts`다. 실제 worker 함수는 `_price_worker_green`, `_price_worker_vsl`, `_price_worker_offset_walk`, `priced_wu_link_controller._price_worker_phase`다. `offset_walk` **한 task 안에 여러 endpoint**가 있을 수 있다. task 수, endpoint 수, 실제 coupled interval 수는 서로 다르다.

부모 batch의 wall에는 pool 생성·pickle·spawn/import·`PricedWuLinkStackelbergController.__setstate__`의 runtime 재설치·task 실행·결과 전달·join이 들어간다. `_price_worker_init` 전에 언피클/재설치가 발생하므로 initializer부터 profiler를 켜면 초기화 시간이 빠진다. 부모와 모든 spawn worker에서 process 시작부터 수집하고, `__setstate__`, `install_price_worker_runtime_patches`, `_price_worker_init` 시간을 별도 표기하는 것이 적합하다.

프로세스별 `(pid,thread,call_id,parent_call_id)`와 각 batch/task fingerprint를 사용한다. worker CPU 합계는 총 작업량이고 부모 batch wall은 경과 시간이다. 동시에 돈 worker wall 합계를 decision wall에 더하지 않는다. `parent batch wall - longest task`도 순수 spawn 시간으로 단정할 수 없다(여러 wave·queue·전송·스케줄링 포함). per-process CPU, task start/end, batch start/end를 함께 보존한다.

worker 실패→직렬 재실행은 `price_parallel_serial_rerun_count/last_error` 및 task별 attempt 번호로 노출한다. 원본 시도와 재실행을 중복으로 숨기거나 논리적 task 2개로 오인하지 않는다. `ENDPOINT_CALLS`는 프로세스 로컬이고 일부 가격 채널은 부모에서 별도 보정하므로 전역 합계의 단일 출처가 아니다.

## 3. 모든 follower와 국소 후보

현재 실제 `LinkAgentWuFollower.solve`에는 `local_signal_service` ready wrapper, `area_follower_objective` phase-finalization wrapper, Link 원메서드, Wu objective wrapper, Wu 원메서드가 중첩된다. `co_name == 'solve'`를 모두 독립 follower로 세면 중복이다. 각 installed callable의 실제 `__code__.co_filename/co_qualname/co_firstlineno`를 식별하고, 같은 receiver/self의 바깥 logical solve를 한 건으로 센다. 하위 함수는 inclusive/exclusive로 분해하되 상위 시간에 다시 더하지 않는다. `functools.wraps`로 바뀐 표시 이름만 사용하지 않는다.

| 세부 구간 | 실제 관측 경계 | 의미와 주의 |
|---|---|---|
| 반복 합의 | `WuFaithfulFollower._solve_followers`, nested `_jacobi_consensus` | leader 좌표·standing λ·coupling warm start, NP primal-dual 외부 반복 수와 Jacobi sweep 수를 분리 |
| 도시 green | Link/Wu `_solve_urban_agent_local`, 현재 shared-ready wrapper | 신호별 호출 수·p1 후보 수; override 전체 비용과 leaf 비용을 중복 합산하지 않음 |
| 추가 phase vector | `apply_phase_price_refinement.<locals>.scored`, Link `_solve_urban_agent_local.<locals>.scored` | 전자는 후속 정련, 후자는 GNE 내부; 현재 활성 경로와 후보 벡터/가격항을 구분 |
| 도시 물리 채점 | 실제 `_phase_local_cost_phased` wrapper chain, `local_signal_service.rollout_shared_ramp`, `ramp_refinement_cost`, vendor `local_signal_plant` rollout 함수 | signal·phases·offset·setup identity·cost; unpriced 진단용 drain 계산도 별도 분류 |
| 미터 탐색 | `_solve_freeway_agent_metered`, nested `_solve_with` | meter 후보 하나마다 VSL 탐색을 내포; 호출 수와 VSL sequence 수를 구분 |
| VSL 탐색 | 현재 `link_predictor.solve_freeway_agent_local` | 반환 evals는 해당 호출의 sequence 수. 선택된 한 sequence의 비용이 전체 탐색 시간이 아님 |
| offset | `_solve_offset_local`, `_solve_offset_local_ramp`, `_solve_urban_agent_joint` | 실제 mode·각 후보 offset/green 벡터와 score; offset guard의 on/off 전역 재평가 별도 |
| 최종 실현 | `area_follower_objective.rollout` → `_finalize_link_phases` → meter `finalize` → canonical endpoint | phase 정련/미터 양자화 후 actual scored fingerprint. offset guard가 켜지면 on/off/selected를 3회 평가할 수 있음 |

기존 `wu_faithful_local_evals`는 전체 cost 호출을 세지 않는다. 특히 Link in-GNE 추가 phase 탐색은 `scored(vec)`를 반복해도 `out[2]`(기존 evals)를 그대로 반환한다(`priced_wu_link_controller.py:684`). 후속 phase 정련도 별도다. 실제 leaf 호출 수를 얻어야 한다. 현재 v4 config는 phase_price `refine_rounds=12`, `in_gne` 키 없음이므로 builder 이후의 `self.phase_price_in_gne`, round 수, 실제 call stack을 기록하고 “전 레버 GNE” 여부를 별도로 판정한다. 이 감사에서 설정은 바꾸지 않았다.

VSL sequence마다의 score는 독립 함수가 없어 일반 function profiler만으로 개별 후보가 안 보인다. 필요하면 **선택된 해당 code object 한 개에서만** `link_predictor.py:491`의 `evals += 1` 직전 line event를 수집한다. 그때 `sequence`, `first_vec`, `cost`, `link`, 고정 meter 값을 읽는다. 전체 Python 줄/매 5초·10초 substep 추적은 오버헤드가 크므로 피한다. green phase의 nested `scored`는 함수 call/return으로 바로 수집 가능하다.

## 4. 행동을 바꾸지 않는 fingerprint 계약

1. 시작 한 번만 config/source/실제 state/previous/forecast 원자료 hash를 기록한다. hot leaf마다 전체 cfg/state를 pickle/hash하지 않는다. 입력 `state/previous/forecast`의 기존 immutability 검증은 별도 경계에서 유지한다. 제어기 self의 warm start/cache는 원 알고리즘이 합법적으로 바꾸므로 whole-self 불변을 요구하지 않는다.
2. candidate identity는 `(logical stage, stage-local ordinal, raw leader coords, projected coords, effective context ID)`다. 수치 벡터는 `float.hex()` 등 원 float를 보존하고 dictionary key를 정렬한다. 임의 소수자리 rounding으로 같은 후보로 합치지 않는다. `id(self)`, 시간, phase token은 프로세스 내 연결용이지 비교 fingerprint가 아니다.
3. control fingerprint에는 `N_P_star/N_UF_star`, **VSL·meter·green·offset 전체 벡터**, allocation 및 물리 meter command를 포함한다. 요청 control, finalization 후 control, 실제 scored control, 반환/output control의 hash를 따로 둔다. area meter marker의 `requested_rates/realized_rates/context_sha256`도 기록하되 counter/token/성능 metadata는 숫자 동치 비교에서 제외한다.
4. 동일 action이라도 price·standing λ·coupling warm start·objective spec/box-walk·forecast·beta가 다르면 다른 평가다. batch/solve 경계에서 이 context를 한 번 fingerprint하고 leaf는 그 ID만 참조한다. `N_UF` cache hit는 관측만 하며, profiler가 `setdefault`, cache warm-up, 추가 solve, candidate sort, 재평가를 해서는 안 된다.
5. endpoint는 현재 `area_runtime.install.<locals>.evaluate_price_point`의 **바깥 논리 호출**을 한 건으로 기록하고 vendor endpoint와 `_rollout`은 하위 stage로 둔다. 전후 수치에는 J, ΩTTT/TD, states 길이, abort, 실제 `coupled` 호출 수와 final control hash가 필요하다. 아직 점검하지 않은 일치/불일치를 스킵하여 PASS로 쓰지 않는다.
6. profiler OFF의 기존 actual fullmain와 프로파일 run의 후보 순서·각 raw/projected/realized fingerprint·price 벡터·cache-hit pattern·J·최종 JSON/CSV 벡터가 같은지 비교한다. 시간은 계측 오버헤드가 포함된 값임을 표시한다. 함수 경계만의 1차 수집으로 후보 수/단계 wall을 얻고 필요할 때만 leaf trace를 켠다.

프로파일러는 `LEADER_CURV_SWEEP`/`LEADER_GRID_SWEEP`를 켜지 않아야 한다. 이름은 진단이지만 추가 full 후보를 평가한다. 기존 trace 옵션도 원래 실행 환경과의 차이를 명시하고 결과 비교 없이 “동작 불변”이라 선언하지 않는다. 이번 작업은 소스 조회와 이 새 문서/JSON 작성뿐이며 production/config/VISSIM을 바꾸거나 실행하지 않았다.
