# v3 bounded-memory evaluation trace 인계

v3는 후보·점수·순서·실행 제어·가격·operational state를 삭제하지 않고 저장과 수집 방식을 바꾼다. 생산 controller, launcher, 정상 결과 comparator는 수정하지 않았다. **실제 전체 MPC trace는 아직 실행하지 않았다.** Root의 정상 성능 pair 동안 이 코드도 동결하며 추가 모델 import/benchmark/대량 자료 읽기를 하지 않는다.

원 v2 실패 증거는 `wu-link_t900_beta300_20260910T043126158133Z`에 그대로 있다. Root가 관측한 부모 working set 8,202,625,024 bytes와 local JSONL 614,562,203 bytes는 첫 follower 중간의 실패 수치다. `rows`, context/value 사전, operational snapshot을 계속 메모리에 보관하고 각 return 행에도 큰 snapshot을 넣던 구조를 제거했다. 이 실패를 완료 trace로 분류하지 않는다.

## 바이트 보존과 저장 계약

수정 전 v2 원문 12개는 `evaluation_trace_v2_raw_before_v3.zip`에 바이트 그대로 보존했다. ZIP 37,277 bytes, SHA256 `acc81a5d40bede839ae4df9542b3d98ceb0afe48943fbdb8db13a0cd0460e607`; member raw SHA/길이와 CRC/readback 검증은 같은 이름 `.json`에 있다. 이전 hash·원문·부분런은 덮어쓰지 않았다.

새 `evaluation_trace_storage.py`가 프로세스별 SQLite 한 개에 행, context/value 표와 lossless canonical subtree를 저장한다. JSONL은 ordinal/call/parent/kind/event와 snapshot SHA 참조만 담고, 최종 JSON은 작은 metadata와 DB/JSONL checksum만 담는다. Dictionary key 타입, float hex, signed zero, 배열 순서, 중복 task의 개수는 기존 표현을 유지한다.

Snapshot의 외부 key는 여전히 원 canonical JSON의 SHA다. 내부 subtree 참조는 저장 압축일 뿐이다. 큰 subtree를 방문할 때 **현재 전체 값의 bytes hash를 새로 계산**하고, 이미 같은 내용이 있으면 자식 SQL 순회를 생략한다. 객체 ID/shape를 동일 값의 증거로 쓰지 않는다. 작은 container에는 이 선택적 shortcut을 시도하지 않을 뿐, 어떤 값도 빠지지 않는다. 실제 nested mutation은 다른 key와 다른 복원 값으로 확인했다.

Python node/content cache는 1MiB, SQLite page cache는 2MiB이며 mmap을 사용하지 않는다. 후보 이력은 Python list/dict에 누적하지 않는다. 실패 메시지도 처음 63개와 이후 개수를 보존하여 기록기 오류가 계속돼도 메모리가 무한 증가하지 않고 결과는 invalid가 된다. 순간 메모리는 현재 모델 객체와 가장 큰 현재 canonical snapshot·그 직렬화 크기에 비례하므로 **전체 프로세스 RSS를 3MiB로 제한한다는 뜻은 아니다.**

Collector는 작은 sidecar만 읽고, 행/값은 DB에서 하나씩 복원한다. 호출 번호는 SQL window rank로 정규화하므로 Python에 모든 call ID를 쌓지 않는다. 부모 순서와 task 내부 순서는 유지하고, worker task는 기존 `task_key`와 trace hash로 정렬하며 중복을 보존한다. JSONL/backing 행 일치, 파일 checksum, context/value 존재와 내용 SHA, 호출/parent/worker 할당, 프로세스 완료를 검사한다. 기존 checksum을 다시 쓴 corruption도 내용/행 검증에서 거부했다.

`collection()['comparison']`의 큰 sequence는 이제 디스크를 읽는 view다. Launcher처럼 `comparison`을 제외한 결과를 JSON으로 저장하면 된다. `base.digest()`와 비교 함수는 이 view를 streaming 처리한다. 작은 fixture를 사람이 확인할 때만 `load_document(path, expand=True)`를 명시적으로 사용한다.

## 기존 v2 주소값 결함의 별도 정정

원 vendor `priced_wu_link_controller.py:_phase_refine_signature`의 6항 tuple 중 index 1은 `id(demand)`다. v2는 이 주소를 `_phase_ctx_cache` operational snapshot에 그대로 넣어, 같은 값·같은 동작인 fresh process도 local hash가 달라질 수 있었다. 저장 방식의 손실과 구분해야 한다.

Root 승인으로 이 **한 경로만** 다음 계약으로 표현한다. Signature ID가 실제 `ctx['demand']`를 가리키는지 검증하고, 비교에는 그 관계, 현재 호출 demand와 ctx demand가 같은 객체인지, 두 demand의 완전한 값, 나머지 5개 signature 항목과 전체 ctx를 남긴다. 원 주소는 `local_identity_provenance` 표에 별도 보존한다. 내부 signature/context 관계가 깨지면 fail-closed다. 현재 demand를 해당 경계에서 관측하지 못하면 그 사실을 명시한다. 값이 같은 다른 객체도 동일 객체와 구분하는 회귀가 있다. Runtime의 cache 정책 자체는 바꾸지 않았다.

기존 v2 hash는 수정하지 않았다. 저장만 바꾸는 재인코딩은 old hash 그대로 유지하며, 새 관계 표현을 쓰는 실제 trace의 local hash는 별도 scope다. Fresh 실제 SC1004 두 process에서 새 local hash `50949bcf3888fb2be189717625582e3a97ab8819d6eb4b25e7abf3486412ac95`가 같았다.

## Peer review 후속 수정 — focused 검증 완료

아래의 31 PASS와 재인코딩/실제 local 수치는 이전 v3 revision의 역사 검증이다. 이후 peer가 찾은 snapshot key 검증 누락과 disk parent prefix 반복 조회를 수선했고, root가 허용한 quiet interval에서 **현재 revision 35개 focused 회귀가 모두 PASS(6.574초)** 했다. 기존 `evaluation_trace_v3_validation.json`은 수정하지 않았다. 수정 직전 6개 파일 원문과 검증 문서는 `evaluation_trace_v3_before_peer_integrity.zip` 및 같은 이름 JSON에 byte-exact 보존했다.

`Store.get()`은 모든 snapshot의 완전한 현재 내용을 key SHA와 비교한다. 비교 hash에 포함되지 않는 raw identity provenance도 수집할 때 별도로 확인한다. Writer와 collector가 같은 필수 table mapping을 사용하므로 contexts/values/table count 선언을 sidecar에서 삭제해 검사를 건너뛸 수 없다. 과거 v2의 identity channel 부재는 명시적으로 호환한다. `compare_collections()`는 parent를 `zip_longest`로 한 번 순회하고, 마지막 전체 sequence 재비교도 수행하지 않는다. worker task 순서와 중복 수는 기존대로 비교한다.

새 반례는 유효한 다른 row descriptor와 갱신된 DB checksum, 필수 table/count 삭제, 실제 disk sequence의 인덱스 접근/두 번째 순회 금지, 첫 차이/길이/worker 중복을 검사한다. 수정 중간 기록은 `evaluation_trace_v3_peer_revision_pending.json`, 최종 결과와 source SHA는 `evaluation_trace_v3_peer_revision_validation.json`에 보존한다. 첫 실행은 기존 테스트가 전체 row에서 숫자 문자열 `456`을 찾다가 합법적 `perf_ns=111735229845600`에 걸려 34 PASS/1 FAIL(6.920초)이었다. 이 검사를 fixture가 제외하려는 PFO result의 `metadata`/`wall_time_sec` 필드로 한정한 후 35개 전체를 재검증했다. 해당 flaky test 수선도 테스트 파일에만 있다. 큰 재인코딩 및 실제 local/global 모델 probe는 재실행하지 않았다. 이 후속 수정에는 모델/생산 코드, launcher, root comparator, Git 변경이 없다.

## 검증 결과와 성능 해석

`evaluation_trace_v3_validation.json`에 현재 소스 SHA, 정확한 명령과 결과를 보존했다.

| 검증 | 결과 |
|---|---|
| 기존 21 + storage/주소관계/오염 10 회귀 | 31 PASS, 5.719초; fresh spawn·예외·thread·후보 counter 포함 |
| 완료 v1 전체 35 process/116 tasks 재인코딩 | `7c52c6b370e34e7d4810e8dfa6bc5420f758c940f680f60df570f6c1d25ed28d` exact |
| old v2 실제 단일 SC1004 원문 재인코딩 | old local `1dfe7b8e…`와 v1 `c38d9c69…` 모두 exact |
| 현재 동결 코드로 위 DB들 최종 재수집 | 모두 PASS; 11.725초 / 0.379초, source changes 0 |
| 실제 SC1004 원 함수 단일 호출 | cost `0x1.4c58979ee9a45p+4` exact, 입력 pickle 불변, source changes 0 |

최종 actual probe는 `evaluation_trace_actual_local_20260910T051058033441Z`다. Parent JSON/JSONL은 1,882/309 bytes, local JSON/JSONL은 2,571/369 bytes, SQLite는 634,880 bytes다. 이는 cold head-resource fixture900/prior750의 SC1004 setup+local cost 한 번이며 global endpoint/MPC/VISSIM은 0이다. 전체 실제 후보 coverage 완료 증거가 아니다.

Storage-only 같은 actual canonical snapshot 12회 실험은 초기 v3 3.5781초 → content shortcut 단계 1.0694초 → 작은 container 중복을 줄인 단계 0.7588초였다(`trace_storage_repeat_*.json`의 각 source SHA 참조). 이 속도비는 모델/MPC 개선율이 아니다. 48행 별도 tracemalloc 검사에서 보관 중 Python 메모리는 918,255→947,164 bytes, 순간 peak는 36,442,605 bytes였다. 이는 Python 할당 계측이고 RSS/SQLite native 메모리 또는 full MPC 상한은 아니다. 해당 중간 구현의 provenance를 그대로 남겼다.

최종 actual cold call은 v3 계측 0.655초, off 0.0118초였다. 원 v2 단일 계측 약0.147초보다 느리므로 **메모리 보완을 계측 속도 향상으로 보고하지 않는다.** 다만 초기 v3 cold 1.149초에서 중복 저장 계산을 줄였다. 전체 trace의 실용성·최대 RSS·종료 수집 비용은 root의 실제 실행으로 별도 확인해야 한다.

## 적용 파일과 다음 실행

수정한 diagnostics: `evaluation_trace.py`, `evaluation_trace_local.py`, `evaluation_trace_monitor.py`, `evaluation_trace_finalize.py`, `evaluation_trace_state.py`, `test_evaluation_trace_local.py`, `probe_evaluation_trace_actual_local.py`.

새 diagnostics: `evaluation_trace_storage.py`, `test_evaluation_trace_storage.py`, `probe_trace_storage_repeat.py`, `probe_trace_storage_reencode.py` 및 위 archive/validation/인계 자료. 새 storage helper를 **launcher의 tracer source pin 목록에 추가**해야 한다. Bootstrap은 기존 monitor 설치 경로를 그대로 쓰며 `Monitor.install()`이 disk-backed를 기본으로 선택한다. 원 profile backend의 메모리 형식은 legacy fixture 비교용으로 남겨 두었다.

Root가 실제 full trace를 실행하기 전 필요한 것은 새 helper pin과 현재 소스 재확인이다. 이번 작업에서 launcher/production/config/Git index/comparator는 수정하지 않았다. Peer review는 요청했지만 아직 완료 판정을 받지 않았으므로 peer PASS로 표시하지 않는다.
