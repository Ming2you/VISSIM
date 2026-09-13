# v4 전체 decision 계측과 계측기 한계

동일 state900/action750, β300 전체 adapter의 일반 실행은180.057479초, cProfile 실행은530.701765초였다. 이는 최적화 효과 비교가 아니다. 35개 프로세스(부모1+가격 worker34)가 모두 종료·flush됐고, 원본 입력·runtime source 변경과 잔존 worker가 없었다. 최종 제어 CSV가 byte exact이며, 전체 action JSON은 네 시간 필드와 두 commit provenance 경로 외 IEEE float bytes까지 같다. 탈락 후보의 중간 값은 이 비교만으로 보증하지 않으므로 별도 evaluation trace를 준비했다.

일반 기준은 `area_production_preflight/wu-link_t900_beta300_20260910T030601849283Z`, 계측 결과는 `area_production_preflight/wu-link_t900_beta300_20260910T032525335593Z`다. 후자의 `strict_result_comparison.json`, `profile_summary.json`, 원본 `.pstats`와 프로세스별 sidecar를 보존한다.

## 시간 귀속 오류를 먼저 배제

이 환경의 Python3.12.14 cProfile에서 부모가 시작한 profiler에 다른 thread의 호출이 섞인다. 부모 profile의 `shutdown` 약124.9초와 잘못된 caller/count0 항목을 보고 별도 최소 재현을 수행했다. `probe_cprofile_thread_attribution.py`의 실제 자식 함수 caller는 `child_target`인데 profile은 `threading.wait`, callcount0으로 기록했다. 결과는 `cprofile_thread_attribution.json`이다.

[CPython3.12.14 원본](https://github.com/python/cpython/blob/v3.12.14/Modules/_lsprof.c)은 하나의 `currentProfilerContext`와 monitoring callback 등록을 사용한다. 로컬 재현과 함께 볼 때 concurrent thread가 있는 부모의 caller·self·inclusive 시간 귀속은 이 분석에 사용할 수 없다. 따라서 pool 종료124.9초를 제거 가능한 비용으로 해석하지 않는다. 기존 sidecar의 "main thread" 문구는 잘못됐으며 원본을 덮어 고치지 않고 이 정정과 새 summary 한계를 남긴다.

34개 가격 worker에는 secondary-thread bootstrap이 기록되지 않았다. 아래 worker 함수 호출량과 단독 프로세스 profile은 중복 작업의 위치를 찾는 자료다. CPU/IO 대기가 포함된 함수 wall, 중첩 inclusive 시간, 동시에 실행된 worker 시간을 합해 전체 decision 시간이나 회수 가능한 시간을 만들지 않는다. 전체/후보/가격 경계의 별도 thread-aware 측정으로 보완한다.

## 계측으로 확인한 작업량

| 항목 | 부모 | 전체 가격 worker |
|---|---:|---:|
|signal phase_fraction 호출|3,949,417|4,943,430|
|signal validate_vector 호출|7,096,408|6,912,540|
|signal written_offset_sec 호출|3,547,995|3,456,270|
|prehead _inputs 호출|1,719,730|7,323,872|
|prehead _blocked 호출|1,405,234|6,023,491|
|prehead _check 호출|304,955|1,259,071|
|독립 측정 process CPU 합계(초)|399.296875|924.437500|

전체 process CPU는1323.734375초로, parallel work의 양이며 경과530.7초와 다르다. 작업자 구성은green10개/34task, offset10개/15task, phase10개/63task, VSL4개/4task다. Offset task 하나가 여러 endpoint를 실행하므로 task 수와 rollout 수를 혼동하지 않는다. 이 실행에서 outer Ω endpoint는 부모36회, worker153회다. 안쪽 vendor endpoint와 이중 합산하지 않는다.

계측 실행의 peak working set은 부모114.16MiB, 개별 worker70.08–71.08MiB였다. 서로 다른 시점의 peak 합계는 동시에 사용한 메모리가 아니다. 이후 캐시의 상한·보유 객체·worker별 메모리와 함께 비교해야 한다.

## 적용 순서

반복되는 신호 validation·writer·event-grid 계산의 불변 결과 재사용을 먼저 검토한다. 이는 이후 전 레버 follower game에서도 계속 사용할 계산이다. 작은 fixture의 속도비를 전체 MPC 개선율로 사용하지 않으며, test-only offset의 absent/None 등 독립 리뷰에서 발견한 경계 오류를 해결한 뒤 실제 코드에 적용한다.

Native prehead의 반복 config lookup도 검토한다. 모든 cohort 검증·합산 순서·실패 시점은 유지해야 한다. source dictionary identity와 크기만으로 nested 값의 불변성을 보장할 수 없으므로, 해당 제안은 값 의존성 계약을 만족할 때까지 보류한다.

Pool 재사용·추가 병렬화는 위의 잘못된 shutdown 귀속 수치에 근거해 추진하지 않는다. 평가 추적에서 candidate/task 범위와 실제 경계를 검증한 뒤 우선순위를 다시 결정한다. 목적함수·물리 모델·후보 수/순서·GNE 종료 조건·가격 계산은 이 성능 단계에서 변경하지 않는다.

## 첫 후보 경계 추적 완료

`area_production_preflight/wu-link_t900_beta300_20260910T035232419561Z`의 별도 sys.setprofile 추적은35개 process/116개 price task를 모두 저장했다. 부모의352개 enter/return 행과8개 값 문맥이 유효하며 source/input 변화와 잔존 worker가 없다. 이 hook은 함수·반환값을 바꾸지 않는다. 최종 CSV와 반환 JSON은 기존 일반 기준과 정확히 같았다(동일한6개 시간/commit 경로만 제외). 비교 도구는 signed zero와 타입 차이도 구분한다.

이 실행의 decision은875.821121초이며 정상 속도 측정이 아니다. 선택 경계의 관측은 price refresh331.81초(phase refresh93.75초 포함), PFO92.12초, proxy9개 합67.52초, 상세 leader3개113.44/130.19/131.93초다. 네 logical follower는83.93/106.05/122.28/122.97초로, 이미 PFO·상세 leader 시간 안에 들어 있다. 이들을 상위 stage에 다시 더하지 않는다. 정상 코드의 stage 비율로 환산하지도 않는다.

v1 coverage는 leader/PFO/가격/outer follower/실행 interval까지다. 도시·고속도로의 모든 국소 후보별 점수는 아직 미포함이므로 전체 후보 동치 완료를 뜻하지 않는다. Python callback이 모든 call/return을 관측하는 비용이 커서, 다음 추적은 선택한 함수·후보 지점만 기록하는 monitoring backend로 보완한다. 이 계측 개선은 controller 계산 최적화의 속도 성과와 분리한다.
