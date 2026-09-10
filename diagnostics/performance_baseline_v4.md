# 성능 최적화 전 고정 기준

사용자의 추가 지시에 따라 장기 제어 실험보다 계산 성능 계측·개선을 먼저 진행한다. 모든 레버의 follower game 통합과 GNE 검증은 그 뒤의 별도 알고리즘 변경이다. 요청 원문은 `docs/REQUEST_20260910_gne_and_performance.md`에 보존했다.

성능 기준은 head resource 수정을 포함한 `contract_candidate_configs_v4`다. 137개 source/data와 네 config의 checkout 바이트를 검증했다. head 자원의 실제 runtime 7개 연속 관측창·국소 비용·worker 회귀는 16개 PASS다. W_out 목적지 보존, E8 분기 순서/차로 모형, GNE 구조 변경은 이 기준에 포함하지 않았다.

| 일반 실행 | adapter decision wall | 범위 |
|---|---:|---|
| 실제 state1, no-control, β0 |2.835738초|이전 행동 없는 실제 main 초기화|
| 실제 state900, wu-link, β300 |180.057479초|전체 main·가격·leader/PFO/follower·최종 변환 및 평가|

900초 입력은 `codex_contract_observed_nc_s13_1050_v2_20260910`의 원본 state900/action750이다. 신규 head resource namespace의 이전 이력이 없는 cold migration이며10629 관측 pool이 아직 활성화되지 않는다. 이 단일 일반 실행 시간으로 평균·변동성이나 달성 가능한 단축률을 주장하지 않는다. 프로파일링 실행은 별도이며 그 시간을 일반 benchmark와 혼합하지 않는다.

성능 변경은 목적함수·가격 갱신·물리 모형·후보 집합/순서·수렴 기준을 그대로 둔다. 같은 문제에서 중복 계산을 제거하는 변경만 먼저 비교한다. 최종 실행 CSV 외에도 가격과 목적값 성분, 모든 후보 점수·선택, 공유 제약 및 반복 진단, 다음 decision에 전달되는 상태를 확인해야 한다. 비트 차이가 생기면 원인과 선택 경계 영향을 따로 밝힌다.

실행 계측은 adapter와 spawn worker의 `sitecustomize`에서 cProfile을 시작해 unpickle·runtime 설치를 포함한다. 각 process의 CPU 시간과 시작/종료 시각, peak working set도 기록한다. 함수별 cumulative 시간은 중첩되고 worker 실행은 병렬로 겹치므로 합계를 전체 decision wall로 쓰지 않는다. profiler의 export 비용도 분리한다.

현재 알려진 `nash_converged`/결합 잔차를 GNE 보증으로 해석하지 않는다. 성능 최적화의 결과 동일성이 확보된 후, 같은 follower game 안의 green+offset 및 VSL+metering 공동 탐색, 공유 제약, 최종 실행 제어에서의 검사 후보 개선 잔차를 별도로 구현·검증한다. β=0/60/150/300 선택과 TTT/cost-to-go 대안은 아직 확정하지 않았다.
