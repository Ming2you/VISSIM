# 완료된 v1 추적: 작업 계층과 성능 수선 우선순위

반복 신호 계산과 prehead 조회의 결과 보존형 재사용을 먼저 검증할 근거가 있다. Pool 종료시간 제거 또는 후보 병렬화의 이득은 아직 입증되지 않았다. 아래 시간은 **추적 오버헤드를 포함한 중첩 경과시간**이며 정상 실행의 단계별 시간이나 예상 개선율로 환산하지 않는다.

근거는 완료된 `wu-link_t900_beta300_20260910T035232419561Z`의 35개 process trace와 별도 `032525335593Z/profile_summary.json`이다. 읽기 전용 생산자 `summarize_v1_trace_hierarchy.py`가 전체 JSONL의 enter/return 쌍, 호출 계층, 결과 및 39개 원본 SHA를 확인했다. 원본 변경 0, worker 잔존 0, 추적 valid=true다. 상세 수치·SHA·정확한 함수 위치는 `v1_trace_hierarchy_review.json`에 보존했다.

| 실행 순서와 범위 | 확인된 작업 | v1 계측 경과시간(초) |
|---|---|---:|
| 초기화 | 부모 1 + 가격 worker 34 시작·완료; 초기화/직렬화/종료는 별도 경계 없음 | 분리 불가 |
| 가격 refresh | green/offset/VSL/phase 4 batch; phase refresh는 이 안에 포함 | 331.81 |
| PFO 후보 | 1개, 내부 logical follower 1회 | 92.12 (follower 83.93 포함) |
| Leader proxy | index 0→8, 9개 | 합 67.52 |
| 상세 leader | index 0→8→7, 3개; 각각 follower 1회 | 113.44 / 130.19 / 131.93 |
| 최종 선택·출력 | PFO 선택; 최종 CSV exact, JSON은 명시된 시간/commit 6경로 외 exact | 독립 writer 경계 없음 |

상세 leader의 follower는 각각 106.05/122.28/122.97초로 이미 상위 후보에 포함된다. **네 follower를 상위 단계와 다시 더하면 이중 계산이다.** 일반 기준의 최종 `wu_faithful_solve_time_sec=15.4580716`은 선택된 PFO 한 번의 내부 기록이다. v1의 대응 값은 83.8548058초이며, PFO follower 바깥 wrapper 83.9306533초와도 경계가 다르다. 이 한 값을 전체 follower 또는 전체 decision 시간으로 부르면 안 된다.

가격 채널별 worker/task/outer endpoint 수는 green **10/34/34**, offset **10/15/52**, phase **10/63/63**, VSL **4/4/4**다. 따라서 116 tasks와 153 worker endpoints는 서로 다른 수다. 부모 endpoints 36회를 합쳐 총 189회이며 내부 vendor wrapper는 중복 계수하지 않았다. 실제 150초 실행 interval 경계는 전체 565회다. 가격 batch 경과시간에는 worker 준비·전송·작업·회수·종료가 함께 들어 있으므로 계산시간만으로 해석하지 않는다.

| 별도 cProfile의 flat 함수 호출 수 | 부모 프로세스 | 가격 workers 합계 |
|---|---:|---:|
| signal `phase_fraction` | 3,949,417 | 4,943,430 |
| signal `validate_vector` | 7,096,408 | 6,912,540 |
| signal `written_offset_sec` | 3,547,995 | 3,456,270 |
| prehead `_inputs` | 1,719,730 | 7,323,872 |
| prehead `_blocked` | 1,405,234 | 6,023,491 |
| prehead `_check` | 304,955 | 1,259,071 |

이 환경의 cProfile 부모 thread 귀속 오류 때문에 caller/self/inclusive 시간은 사용하지 않았다. 위 부모 값은 프로세스 profiler가 본 flat 호출 수이며 main thread만의 집계라고 하지 않는다. 독립 측정 CPU 399.296875초(부모)/924.4375초(workers)는 유지되지만 병렬 CPU 합을 wall time으로 해석하지 않는다.

우선순위는 ① 동일 vector/offset/실제 event-grid의 검증된 신호 결과 재사용, ② prehead 고정 lookup 재사용, ③ 정확한 lifecycle 분리 측정 후 pool 재사용 검토다. ①·②에서도 invalid 입력의 실패, cohort 검증, 합산 순서, nested config 변이 검출을 보존해야 한다. 후보별 `_prev_coupling` 및 `_wu._last_offramp_flow`가 변하므로 후보 병렬화·재정렬은 같은 문제의 단순 가속이라고 간주할 수 없다. 후보 수/순서·가격·종료 조건·물리 계산은 유지한다.

v1은 모든 도시 및 고속도로 국소 후보의 입력/점수와 초기화·최종 writer 세부시간을 수집하지 않았다. 현재 v2가 이 증거 공백을 보완하는 별도 실행이며, 이 문서는 v2 결과나 정상 속도 개선을 선취하지 않는다. 새 모델·endpoint·MPC·VISSIM 실행은 하지 않았다.
