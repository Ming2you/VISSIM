# 6300초 frozen query context 실패: 읽기 전용 검토

대상: `evaluation/runs/codex_fid_cl9000_s13_v2/decisions_codex_fid_cl9000_s13_v2/action_006300.joint.json`와 현재 정본 소스. source/config 수정, 모델/native/FZP 실행 없음. root가 실제 재현·차이 추출을 담당한다.

## 기록된 사실

- 실패: `prepare_common_joint_prices`의 `callbacks['command_evidence'](reference, context)`(area_follower_objective.py:1520), `scoped` 종료 guard(joint_owner_neighbors.py:1408→1393)의 `Frozen joint query context changed`.
- 실패 joint는 `completed=false`, `sim_sec=6300`, `source_changes=[]`, source SHA 항목648개다. 이는 기록된 source 안정성 결과이며 이번 읽기 전용 검토가648파일을 새로 해시한 것은 아니다.
- 첫 reference의 response query1회/endpoint1회가 성공했다. cache 실패0, endpoint2.0742051초, local score0.1892399초; worker1개 완료·수락·종료, owned_workers_alive=[]이다. 실패는 최종 gap/후보 탐색 이전 command 검증 단계다.
- artifact의 전체 decision_budget.wall_sec=9.6467135, actual_hold_prediction_and_validation=2.9672577초이다. inclusive scope들을 더하지 않는다.
- root의 같은 기록 상태6300/이전 action6150·같은 config 무수정 재실행은 최초 native 실패 지점을 통과했다는 중간 관측이 전달됐다. 이 사실만으로 원인을 확정하거나 실제 mutation이 없었다고 결론 내리지 않는다.

## 소스에서 확인한 변화 경로

1. `uncached_command_evidence`(joint_owner_neighbors.py:1425–1499)는 action을 deepcopy하고 private action만 writer에 넘긴다. caller action의 전체 `_key(vars(action))` 및 물리 lever 불변 검사도 별도로 있다. physical meter helper `prepare_control`/`physical_commands`는 자체 copy의 rates·diagnostics만 바꾸며, 읽은 경로에서 state/forecast/cfg의 직접 수정은 보이지 않는다.
2. 다만 segment VSL 조회는 순수 getter가 아니다. :1453의 installed `segment_vsl_func`는 adapter `_patched_segment_vsl`(:8921–8947)이며 `_FW_SEG_CTX`의 `p/armed/phi/dlam/lanes/rho_crit_link`를 쓴다. 이 부수효과를 되돌리려고 `shared_query_runtime_scope`가 존재한다.
3. `_fw_seg_param_dict`(adapter:8370–8378)는 `cfg.network.freeway_segment_params[link][index]`의 row를 copy 없이 반환한다. 따라서 `_FW_SEG_CTX['p']`와 cfg 내부 row의 공유 참조가 생길 수 있다. scope는 각 global별로 독립 deepcopy를 만들고 복원하므로 context↔runtime 및 여러 global 사이의 원 alias 관계를 보존한다고 볼 수 없다.
4. 구체적인 nested set은 adapter `_MIDBLOCK_CACHE['d']`(:5592–5601)의 set[str]다. 이것은 top-level dict 안에 있다. scope의 top-level unchanged set[str] 보존 분기(:72–79)는 이를 보호하지 않는다. `_MIDBLOCK_CACHE` 자체를 query가 바꾸지 않아도 :65–70에서 매번 deepcopy/clear/update 복원한다.
5. `_joint_runtime_callbacks.fingerprint`(:1198–1201)는 `pickle.dumps((context, runtime), protocol=5)`의 SHA다. Python 값이 동일해도 nested set 반복 순서나 공유 참조 구조가 달라지면 pickle memo/stream이 달라질 수 있다. 동일 값을 새 object graph로 복원하는 과정과 실제 상태 변경을 구분해야 한다. 6300에서 실제로 어느 항목이 달라졌는지는 아직 미확인이다.

## 우선순위와 root trace의 판별점

- 1순위: scope 종료 복원 전/후 `_MIDBLOCK_CACHE['d']`의 typed 값·iteration 순서·pickle 변화. 이는 소스로 확인된 nested-set 취약 경로이며 새 process의 hash seed에 따라 재현 여부가 달라질 수 있는 후보다.
- 2순위: `_FW_SEG_CTX['p']`와 cfg row 등 원 alias 관계. global별 deepcopy가 이전 값은 복원했어도 관계를 바꿨는지 확인한다. alias 문제를 값 문제와 동일시하거나 실제 운용 의미가 없다고 선판정하지 않는다.
- 3순위: 실제 payload 변경/복원 실패. 전체 context(value)와 전체 runtime을 분리해 어느 쪽이 달라졌는지 먼저 찾고, 그 branch의 타입·값·순서·alias 차이를 비교한다. 변경된 필드를 guard에서 제외하지 않는다.
- raw pickle 차이만 있을 때는 `pickletools`의 opcode/memo 대상과 FRAME 경계 차이를 구분한다. 전체 큰 payload의 첫 다른 byte만으로 특정 물리 값 변화라고 단정하지 않는다. root 재현 시 이미 얻은 snapshots에 대한 작은 오프라인 분석으로 충분하며 새 endpoint 병렬 실행은 필요하지 않다.
- `scoped`의 finally guard는 writer body에서 발생한 다른 예외를 덮을 수 있으므로 실패 trace의 chained `__context__`도 보존한다. guard mismatch 하나만 보고 본체가 정상 반환했다고 가정하지 않는다.

## 기존 검사 범위와 보완이 필요한 회귀

`diagnostics/test_shared_owner_batch.py:126–138`은 unchanged **top-level** set[str]의 root identity·pickle 안정성을 검사한다. set을 임시로 바꾼 뒤에는 membership 복원만 검사하며, 그 경우의 pickle exact는 검사하지 않는다. :210–236은 nested runtime 값과 follower root identity를 검사하지만 cross-global/context alias 또는 nested set의 byte 안정성은 보장하지 않는다.

실제 차이가 확인되면 수정은 scope의 올바른 복원/명령 조회 부수효과 관리에 한정하고, 다음을 검증해야 한다: 변경 없는 nested-set/alias context의 반복 query fingerprint 보존; 실제 runtime 변경의 원 값·관계 복원; caller action/state/cfg 변경은 기존 guard에서 계속 실패; 예외 경로도 복원 및 원 실패 진단 보존. Python hash seed 차이에 따른 synthetic 반복은 물리 모델 호출과 분리한다. 이번 검토에서는 그러한 테스트도 새로 실행하지 않았다.

현재 결론은 **복원 과정의 nested set/alias 직렬화 변화가 구체적인 유력 후보**라는 범위다. guard 무효화, field 제외, gap/feasibility 성공으로의 오류 변환, 현 실패결정 receipt 변경은 정당화되지 않는다.
