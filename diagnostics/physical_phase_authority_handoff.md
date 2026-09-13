# 세 이동의 선택 SG→모델 phase 수선

`physical_movement_routes.configure_phase_authority(cfg, tuning, selected_plan, *, state_json=None)`를 추가했다. `urban.movements.physical_phase_authority`에 `diagnostics/physical_phase_authority_ver2.json` 경로를 선언하면 작동한다. 키가 없으면 파일 조회·객체 변경·캐시 무효화 없이 `{}`를 반환한다. 이 작업은 정본 adapter/runtime_setup/config를 편집하지 않았으며 root가 훅을 연결한다.

권장 위치는 `install_merged_movements` 직후, `install_phase_vector_green_patch`/movement capacity 및 measured capacity 구성 전이다. 호출 예:

```python
metadata.update(physical_movement_routes.configure_phase_authority(
    cfg, tuning, a.load_signal_group_actuation_plan(), state_json=state_json))
```

Worker는 수정된 cfg specs를 받아 local model을 새로 만든다. 이미 생성한 follower의 캐시를 뒤늦게 바꾸는 함수가 아니며, worker에서 수선을 두 번 재적용하지 않는다. 두 번째 적용도 expected old phase가 다르면 실패한다. Config 구성은 한 번이며, 런타임 메서드 복제·AST 실행은 없다.

| movement | 기존→수선 | 실제 source head / connector |
|---|---|---|
|SC1_E_to_S_SC107|SC1_p4→SC1_p3|1220008201 lane2 head10602 SG6@86.398041m →10566@92.860137m; native12:1|
|SC11_N_SC5_to_E_SC12|SC11_p2→SC11_p1|1220011001 lane2 head30402 SG4@391.371400m →10375@393.773970m; native23:1|
|SC11_W_to_N_SC5|SC11_p4→SC11_p3|1210008303 lane2 head30201 SG2@70.699889m →10372@72.218223m; native21:1 및1110:1|

각 source의 전체 차로는 같은 SG를 통과하며, 기존 phase SG 집합과 실제 SG는 겹치지 않는다. 기존 `load_evidence()`의 network SHA/native edge 및 route 검증을 재사용했다. 선택된 mainline plan 파일 SHA와 실제 전달 plan 객체도 비교한다. Source head 집합·차로·위치·모든 차종 적용·compliance, connector 양끝 lane/pos, native route 진입점 및 전체 matching route 집합, 기존 spec의 phase/signal/origin/destination/receiver/kind, 새 SG의 유일한 phase를 확인한다. 모두 통과한 뒤에만 세 spec의 `phase` 필드를 원자적으로 교체하고 해당 network의 vendor topology cache를 무효화한다.

Helper 자체는 beta, receiver, route, capacity, 관측 mapping, signal green 값, state/ledger/총 재고를 변경하지 않는다. 뒤에 실행하는 기존 capacity 구성은 새 phase 대응을 읽게 되지만 새 수치나 포화 유량을 추가하지 않는다.26개 bypass와 혼합 SG는 보류한다. SC1004/SC1005의56/57 route-only 수선이 혼합 source SG2/5의 service authority까지 해결했다는 주장은 하지 않는다(Flow에게 전달).

검증은 `python -X utf8 -m unittest diagnostics.test_physical_phase_authority diagnostics.test_physical_movement_routes -v`의 **16 tests PASS(3.37초)**. 새5개는 OFF byte identity, phase 외 전체 network 필드/원본 state 유지, stale phase/다른 selected plan 실패, 잘못된 head lane/pos·route·새phase 거부, warm cache 이후 actual follower/endpoint 동작을 검사한다. 기존11개는 원래 물리 경로/초기 재고/토폴로지 수선 회귀다. 별도로 기존 authority audit6개도 PASS했다.

Actual follower/endpoint 회귀는 retry1200의 cfg/state를 복사하고 대상 queue만10대로 설정한 명시 fixture다. 한10초(urban2step)에 새 phase만 GREEN인 offset과 기존 phase만 GREEN인 offset을 선택한다. 실제 Link follower의 local model/offset fraction/phase rollout은 수선 후 새 phase에서만 local TTS를 줄이고, 수선 전 cfg는 반대로 예전 phase를 선호한다. 실제 Ω `evaluate_price_point`→coupled plant에서도 새 phase만 켜면 대상 accepted transfer>0, 예전 phase만 켜면0이다. Endpoint의 실제 meter context/finalizer와 ledger closure를 사용하며 finalizer를 mock/bypass하지 않는다. 계측은 실제 `emit_transfer`를 호출하며 수량을 기록하는 wrapper뿐이다. 원본 candidate state는 그대로다. 이것은 물리 saturated capacity 식별이나 성능 향상 보장이 아니다.

## 한 구간의 기존 실제 통과 기록

`probe_phase_authority_passages.py`는 신호 zero 실험의(900,1050]만 indexed FZP로 읽었다(152개1초 frame,21,950,030bytes,0.58초). Source head POS-plane crossing과 이후 해당 connector에 들어간 같은 vehicle ID를 연결한다. 실제 COM은 RunContinuous chunk 시작 immediate/끝 post_step에 읽었으며 **1초 COM 측정이라고 부르지 않는다**. 각 통과는 해당 구간 양끝의 실제 일치 readback을 함께 기록한다. 보간 crossing 시각·source/connector lane/pos·미관측 outcome·lane ambiguity·raw byte-range SHA는 `physical_phase_authority_passages.json`에 있다.

| 대상 connector | matched ID | 실제 SG readback 구간의 aspect |
|---|---:|---|
|10566 /SC1 SG6|4|GREEN3, AMBER1|
|10375 /SC11 SG4|2|GREEN1, RED1|
|10372 /SC11 SG2|6|GREEN6|

**10375의 vehicle3877은 주의 사례로 그대로 보존했다.** POS 보간 crossing970.4615초이고, SG4는966~969 AMBER 뒤969~972의 실제 readback 양끝 모두 RED다.1초 위치 좌표/황색 통과 결정 등과의 관계를 이번 구간만으로 확정하지 않는다. 이를 누락시키거나 GREEN으로 바꾸지 않았으며, simulator의 위반 또는 무신호 movement라고도 단정하지 않는다. SG6의 AMBER1도 유지한다.10372 source-head cohort1대는1050까지 branch outcome을 확인하지 못해 미확정으로 남겼다.

따라서 이 기록은 해당 물리 SG/head와 실제 branch의 대응을 뒷받침하지만 **실제 모든 방출이 model GREEN window 안에서만 일어난다는 완전 정합 검증은 아니다.** 수선 후3개 phase wiring은 검증됐고, 황색 결정/차량 위치 기준·yield/공간 수용은 별도 모델 오차로 남는다. 새 VISSIM/COM 실행이나 기존 run 파일 변경은 없었다.
