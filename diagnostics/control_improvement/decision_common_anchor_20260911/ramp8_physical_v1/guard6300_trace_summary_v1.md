# 6300 guard bounded 계측 결과

0..7에서 실패를 재현하지 못해 상한대로 중단했다. 실제 native/model 제어 소스와 guard는 수정하지 않았다. 원인 확정이나 guard 완화의 근거가 아니다.

| PYTHONHASHSEED | 진입 | 시간(초) | endpoint | fingerprint 변화 |
|---|---|---:|---:|---|
| 0 | import→main | 17.974 | 1 | 없음(5개 전체 pickle bytes 동일) |
| 1 | import→main | 18.368 | 1 | 없음(5개 전체 pickle bytes 동일) |
| 2 | import→main | 17.948 | 1 | 없음(5개 전체 pickle bytes 동일) |
| 3 | import→main | 19.273 | 1 | 없음(5개 전체 pickle bytes 동일) |
| 4 | script __main__ | 20.176 | 1 | 없음(5개 전체 pickle bytes 동일) |
| 5 | script __main__ | 20.909 | 1 | 없음(5개 전체 pickle bytes 동일) |
| 6 | script __main__ | 21.704 | 1 | 없음(5개 전체 pickle bytes 동일) |
| 7 | script __main__ | 20.157 | 1 | 없음(5개 전체 pickle bytes 동일) |

각 실행은 최초 command_evidence 반환 직후 DiagnosticStop으로 종료했다. 전체 game/common-price 탐색은 수행하지 않았다.8개 endpoint만 실행했으며 모든 worker가 닫혔고 source_changes=[]다. canonical joint는 모두 completed=false/DiagnosticStop이며 유효 제어 명령으로 취급하지 않는다.

4..7은 기존 adapter 파일을 runpy.run_path(...,run_name="__main__")로 실행했다. binder 이후 __name__=__main__, canonical_is_main=true, package_alias_same=true다.5..7의 실제 joint worker initializer/evaluator는 evaluation.controllers.area_follower_objective의 정본 함수로 기록됐다. legacy price-worker bootstrap module 이름은 __main__이며 해당 legacy 값과 active joint entrypoint를 혼용하지 않는다.

모든 probe의 출력 경로를 제외한 adapter 인자는 root의 무수정6300 PASS 실행과 같다. canonical joint source pin648개도 실제 native 실패의 pin 집합과 모두 같다. 실제 native 시작 process의 PYTHONHASHSEED는 미기록이므로 이8개로 당시 seed를 덮었다고 주장할 수 없다.0..3의 hash("guard6300_probe")는 당시 미수집이며 사후값을 만들지 않았다.4..7의 실제 hash 값은 각 trace.json에 있다.

각 guard 호출의 원 fingerprint 반환값과 별도로 캡처한 전체 pickle SHA가 모두 같았다. 최초 대비 전체 pickle bytes·top-field pickle·typed 값·set iteration·dict order·alias·FRAME/memo stream의 실제 차이는 관측되지 않았다. 따라서 nested set/alias 복원은 소스상 후보로 남지만6300 원인으로 확정할 수 없다. 관측 wrapper의 추가 직렬화/순회에 따른 timing·GC 효과도 배제하지 않는다.

다음 판단 제안: 추가 전체 decision을 반복하기보다 현재 보존된 snapshots와 실패 당시 환경 근거를 먼저 비교한다. 필요 시 root 승인 하에 first-command scope 종료 전후에만 raw bytes를 저장하는 더 가벼운 진단 또는 실제 nested-set 값만 이용한 순수 복원 회귀로 후보를 검증한다. PYTHONHASHSEED 고정이나 guard field 제외로 성공시켜서는 안 된다.

원자료: guard6300_hash0_trace_v1 ... guard6300_hash3_trace_v1, guard6300_hash4_script_trace_v1 ... guard6300_hash7_script_trace_v1의 trace.json, snapshot_00..04.pickle, canonical failure receipt, stdout/stderr. 집계: guard6300_trace_summary_v1.json.
