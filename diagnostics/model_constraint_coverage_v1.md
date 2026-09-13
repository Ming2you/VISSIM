# 구현된 모델 제약의 계측 범위

생산 5개 파일은 고정했고 작은 회귀 52개가 0.053초에 통과했다. 실제 저장 상태 endpoint/COM은 이 작업에서 실행하지 않았다. 전체 차량 배분·업데이트 순서·legacy 반환값은 유지하며 capture ON에서 기존 한도와 실제 선택량을 검증한다. 원본 5개 파일은 `fixtures/model_constraint_coverage_before_v1.zip`에 바이트 그대로 보존하고 readback을 확인했다.

`response.model_constraint_coverage.complete`와 최상위 `conditional_model_feasibility_witness`는 실행 전에 등록한 전체 nested interval의 기대 방문, 실제 완료, 초기·착지 frame 시각이 일치하고 명시 누락이 없을 때만 참이다. 단순 성공 반환, 유한 비용, 재고 폐쇄, 몇 개 자원 기록만으로 참이 되지 않는다. 방문하지 않은 allocator, 특정 off-ramp 착지 또는 마지막 frame이 빠지면 거짓이다. 단독 unit 호출은 전체 coupled schedule로 인증하지 않는다.

| 위치 | 실제 검사하는 기존 한도 |
|---|---|
| FW query, pre-Tu | 원래 ramp release 함수의 AST·서명을 고정하고 queue/Tf, ramp cap, q_cap×density receiving, clipped request의 min을 같은 입력으로 순수 재검증한다. 반환 흐름은 원래 계산값 그대로 사용한다. |
| FW 셀·경계 | mainline sending, ramp를 뺀 잔여 receiving, entry의 수요/용량/잔여 receiving, terminal sending·선택적 유한 용량, offramp sending·공급된 receiving. |
| 도시 일반·램프 | final intended limit와 실제 source stock, receiver별 실제 batch, ramp별 실제 공간, metering 요청·보유량, 정규 shared-head debit. |
| 도시 출구·legsplit | mature source, free/목적 ramp 개별 한도, 선행 일반 수용 후 common ramp 공간, tail 추가 service, 실제 source stock. 개별 ramp entry cap을 새 공동 connector cap으로 합산하지 않는다. |
| shared69 | 목적별 due 재고, lane service, 순차 수용 공간, 새 내부 수요의 source storage 수용. |
| SC2001 | 목적별 ready/service/receiver와 실제 적용된 aggregate service 비례 배분. |
| native/route 모듈 | 기존 generation/queue receiving, branch/native fixed service, accepted incoming connector, SC11 left residual gate 기록을 소비한다. 전체 Tu에서 각 구성된 모듈의 실행 완료도 요구한다. |
| queue·착지 | 기존 qmax projection **이후** retained queue를 별도 `state_bounds`로 검증한다. 차량 흐름으로 부르지 않는다. direct/signal 실제 landing receiving과 off-ramp별 완료를 기록한다. |

이 증거의 범위는 구현된 교통 상태전이의 배분·수용 한도다. 후보 control-domain, leader total/directional equality·cap, 물리 명령 정합성은 caller가 별도로 검증해야 한다. 범용 물리 GNE 또는 실제 망의 타당성을 인증하지 않는다. `shared_capacity_certificate=False`, `physical_native_fidelity_certificate=False`는 그대로다.

SC11 W/N reference overdraw는 기존 진단에 남으며, `max(0, reference budget − WN)`에 대한 left tag의 기존 잔여 배분만 hard gate이다. SC8은 timing eligibility이며 관측하지 않은 포화용량을 추가하지 않았다. FW의 receiving-after-ramps는 mainline 잔여 한도다. 코드가 강제하지 않는 mainline+ramp 공동 storage 상한, 전체 rho≤rho_max, VSL 이하 실제 속도 상한을 새 hard constraint로 만들지 않았다. Native 차로 교환·공유 head·초기 post-head 대응의 불확실성도 별개로 남는다.

회귀에는 FW capture ON/OFF 전체 반환·상태 동치, 잘못된/비정본 ramp query 거부, shared69 목적별 receiving 및 미래 due 보존, SC2001 실제 공통 용량 경쟁, 도시 일반·공유 head·legsplit 최종 수용, 누락 방문/frame/명시 누락의 fail-closed, clone 격리와 물리 인증 false가 포함된다. 세부 SHA·함수 위치·실행 명령은 동명 JSON에 있다.
