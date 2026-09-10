# SC1004 / 10634: train-only 자원 방류 하한과 consumer

**검토 가능한 수정 후보는 10634 전체 자원의 GREEN service 1509.333333 veh/h이다.** 전체 관측에서 나온1484.444444는 두 검증 구간을 포함하므로 채택값으로 사용하지 않았다. 기존619.591837은 별도로 남긴 검증 구간의 확실한 실제 통과량도 허용하지 못한다. 다만 이 값은 **실현 방류율의 보수적 하한**이며, 동시3차로 포화용량 추정값이 아니다.

Root의 정상5400 종료·전체비교 완료 승인 후 shared patch 다음에 `sc1004_resource_service.patch`를 **생산 소스에 통합했다**. 기존 area 설정·원본1129 evidence는 보존했다. opt-in은 evidence_paths의 원본1129 항목만 정본 `route_choice_corridor_sc1004_calibrated.json`으로 바꾸는 한 경로 변경이며, 해당 파일은 원본1129 dict와 정확히 같고 `service_resource_calibration` pin만 추가한다. 새 runtime module은 필요 없다. 기존 `route_choice_corridor.py` 내부의 검증 함수와 configure의 service 대입만 추가했다.

통합 route SHA는 `6e616c01ae296d5c49722df37898ff4780d3b9fd999d621808e0007c617e6ae6`, 정본corridor SHA는 `fd04d42be2588a93e7175e805c78bd4985801a90b8840c77ec0f7b078abf1bfc`, calibration JSON SHA는 `7262d38b5fa981d60cf71ff59d0f6c7c3cfffb1dc3349044e02c219cc4494f9e`다. 파일명 전환 producer provenance를 갱신했으며 모든 학습 이벤트·수치·holdout은 불변이다.

## 관측 자원과 수치

자원은 실제71번 도로의 SG1004/2 head 세 개에서10634를 거쳐56으로 가는 통과 서비스다. Head90030883(lane1,pos78.980074),90030882(lane2,pos78.874358),90030881(lane3,pos78.911421) 뒤81.238116m에10634가 시작한다. 71 lane1의10642 분기는37.487450m로 head보다 앞이므로 포함하지 않는다. 포함 이벤트는 lane/position에 따른 head 통과 bracket이 완전히 native GREEN이며, 동일 차량의 후속10634 통과도 확인한 경우뿐이다.

| 자료 구간 | 통과 이벤트 / 서로 다른 ID | native GREEN초 | 관측 GREEN 방류 하한 veh/h | 기존 상한이 허용하는 veh |
|---|---:|---:|---:|---:|
| 학습:0–900,1350–2700,3150–5400 |566 /565|1350|**1509.333333**|232.346939|
| 검증:900–1350 |50 /50|135|1333.333333|23.234694|
| 검증:2700–3150 |52 /52|135|1386.666667|23.234694|
| 전체 설명용:0–5400 |668 /666|1620|1484.444444|278.816327|

계산식은 `q_lower = 3600 × verified_crossing_events / full_train_native_GREEN_seconds`다. 차량이 없거나 공급이 제한된 GREEN도 분모에 남긴다. 최초LSA 상태 이전의 GREEN도 분모에는 남기지만 그 구간 crossing은 분자에 넣지 않는다. 창 경계를 건드리는1초 crossing bracket은 보간으로 배정하지 않고 제외한다. 현재 경계 제외는0개다. 검증 구간의 관측값은 fit에 쓰지 않으며 runtime 검증 함수도 `train.events`만으로 선택값을 다시 계산한다.

학습의 반복ID11350은2034–2035초/lane1과2628–2629초/lane3의 서로 다른 방문이다. 594초 떨어진 두10634 통과가 확인되므로 자원을 두 번 사용한다. 정확히 같은 ID/head/bracket 중복은 거부한다. 이 event count를 망 완료차량수 또는Ω TTD로 해석하지 않는다.

1초 자료의 시간 불확실성은 각 crossing의 lower/upper bracket으로 남겼다. 이 하한에는 포화 headway에 대한 통계적 신뢰구간이라는 의미가 없다. 기존 queued-GREEN 분석에서lane3은 유효 표본이 있지만lane1/2는4번째 이후 연속 대기를 만족하는 표본이 없었다. 서로 다른 시간의lane3 수치를3배로 확대하거나 online4162.397을 채택할 근거가 없다.

## 원천과 재현

원자료는 완료된 `codex_area_observed_nc_s13_20260910`, seed13이다. 원 FZP는1,415,953,087bytes /26,693,633rows이며SHA256은 `55c1bc02c68bb8def9c0c3b3ce163a918c20845b4e7113a4768ffe9616986340`이다. 최초 감사에서 한 번만 전체를 읽어16개 물리 link의 정확한 원문1,408,275행을 `sc1004_head_service_identifiability.selected.fzp.gz`에 남겼다. 추출 파일20,877,658bytes의SHA는 `48742104b8c077d6d10726b8d2f74591f7655deef94c1999594ace6791acd05a`이다. 선택 원문 비압축 SHA는 `b9c1068b2e8cf91f65a5dee1cc855562a768b887bf5a93d8170ff477f43a14c4`이다.

후속 학습 producer는 저장된 head-crossing CSV와 추출 hash를 소비한다. 전체 FZP를 재검색하지 않는다. `sc1004_resource_service_calibration.json`에는 모든 학습 이벤트ID/head/lane/bracket과 후속connector, 원천·SIG·producer hashes가 있다. native INPX의 SC1004 FIXEDTIME/prog1/controller offset0, SIG 내부offset75초/cycle150초를 사용했다. 원 head 감사에서SG2 실제LSA와 처음 관측75초부터5399초까지 정수초 상태 불일치는0이었다.

`probe_sc1004_physical_holdout.py`는 별도로 네 시점만 binary seek해 총1,043,087bytes를 읽었고, 각 원문 범위를 다시 hash검증했다. prefix는 정본의7개physical link(10627/10632/10634/10636/75/10701/56)이며 FZP 재고는900→1350에1→1대,2700→3150에8→2대다. 검증 말단 모두 stopped≤5km/h 차량은0이다. 자료는 `sc1004_resource_service_physical_holdout.json`에 보존했다.

FZP의900/2700 전체 차량수는2599/6248, pausedCOM은2591/6243으로 lifecycle 수록 범위가 완전히 같지는 않다. 그러나 이번 초기prefix의 ID집합은 같고 위치·속도 차이는 각0.00496m/0.00397km/h 이하로 FZP 두 자리 반올림 범위다. 전체N 차이를 시간축1초 이동의 증거로 해석하지 않는다. source proof는 동일prefix 초기재고와 원래1초 head-event bracket 기준이다.

## 최소 consumer와 적용 계약

통합 대상은 `evaluation/controllers/route_choice_corridor.py` 한 파일이다. 추가 함수 `_calibrated_turn_services`는 다음을 검증한다.

- pinned calibration/network/SIG/prog/offset와 실제 head/lane/connector endpoints.
- 단일10634에 속하는 기존 세 member의 완전한 집합과 동일SC1004/p3, 실제 신호 서비스.
- 기존 lane-normalized scale과 evidence의 inherited619.591837 일치.
- 고정된 두 time holdout 제외, 각 실제GREEN1초 bracket, 이벤트 중복·잘못된head·source identity 거부.
- 학습분자/분모/선택1509.333333 재계산과 finite 양수 검증.

검증 후 세 member `SC1004_W_to_E_SC1005`, `SC1004_offE_to_E_SC1005`, `SC1004_offW_to_E_SC1005`의 `turn.service_veh_h` 및 `movement_capacity_by_movement_veh_h`에 **같은 자원 rate의 view**를 넣는다. `merge_audit.single_capacity_veh_h`도 같은 값이다. 이 세 값을 합산하지 않는다. global `intended_departure → limit_intended_batch → receive_accepted`는 현재와 같이 key10634의 한 GREEN budget에서 최종 수용된 양만 차감한다. 원래 beta총합, prefix/local storage capacity, 다른connector rate, 실제 receiving 제약은 변경하지 않는다.

**운영 활성화에는 Dewey의 공유자원/ready 패치와 `urban.shared_local_service_pool=true`가 필수다.** `shared_service_ready_handoff.md`의 `local_signal_service.py`가 같은 turn/capmap rate를 읽으며, configure와 worker install 양쪽에서 보정 resource가 있는데 pool이 OFF/없으면 fail-closed하도록 보완되어 있다. 해당 패치는 service rate를 하드코딩하지 않는다. 기존global-only endpoint 실험은 로컬 follower/refinement 정합 증명으로 쓰지 않는다.

권장 적용 순서는 shared ready patch → 이번 resource patch → 별도 clock patch다. 첫 둘은 상대 순서를 바꿔도 같은 route source가 되는 것을 peer가 확인했다. 이번 patch는 configure 부분, shared patch는 intended/accepted/batch 부분으로 비중복이다. Ω 목적함수의 활성 여부와 물리 service 수정은 별개이며, ΩOFF에서도 같은 물리 공유자원이 필요하다. vendor 변경은 없다.

## 제한된 held endpoint 결과

`probe_sc1004_resource_service_holdout.py`는 두 time holdout에서 각450초의 기존/보정4개 endpoint만 실행했다. 마지막 검증 실행28.579초이며 source/config 변화0, 두arm의 초기state/control/forecast pickle hash 동일, 원 입력 불변, 매150초Ω재고 보존과 매5초10634 한 budget을 검증했다. 실제 calibration+detector mapping을 넘기는 canonical demand forecast를 사용했다. 각arm의45개 FW step에서 최종 physical VSL/meter/green/offset/budget 벡터가 고정됨도 확인했다.

반드시 clock 범위를 구분해야 한다. 원 warmup JSON의 SC1004 greens는34.5초씩이며 native replay가 아니다. 두arm 공통으로 SC1004의 native-derived axis46/23/45/24초, offset0을 사용하여 **SG2의450개 정수초 GREEN**이 native와 완전히 같음을 확인했다. SG3/4/7/8 또는 다른16SC까지 native clock을 복원한 것은 아니다.2700의 meter도 canonical finalizer가 R_F_W1762.112027로 실현한다. 따라서 아래는 **SG2 노출이 일치하는 모형 counterfactual**이며 전체 native holdout 예측 정확도나 실측 처리효과 검증이 아니다.

| 450초 구간 | 실제 확인10634 통과 | 기존→보정 모형accepted veh | 기존→보정 말단prefix veh | 실제FZP 말단prefix veh | ΩTTT veh·h 변화 | ΩTD veh 변화 |
|---|---:|---:|---:|---:|---:|---:|
|900→1350|50|23.234694→56.600000|10.880037→36.902895|1|314.441999→314.424806|1497.212513→1498.027951|
|2700→3150|52|23.234694→56.600000|10.792493→38.473339|2|636.046451→636.056011|1765.462300→1765.711510|

보정으로 지나는 차량은 늘지만 하류 prefix에 남는 차량도 늘고 전체TTT 효과는 작다. 기존은 모두offW가 budget을 소비한다. 보정900은offW50.987287+offE5.612713,2700은offW47.912875+offE8.687125이며 W는0이다. 현재 source 순서·수요·ready 제한이 남아 있으므로 관측 origin별 방류나 공정성을 맞췄다는 뜻이 아니다. 이 역사적 실험 당시에는 shared-local-ready가 미적용이었으므로 그 수선 효과도 섞지 않았다.

현재 producer는 actual production import 및 정본 evidence를 사용하고 shared pool을 활성화한다. 재실행 시 별도 `sc1004_resource_service_holdout_integrated.json`으로 저장하여 위 역사적 결과를 덮지 않는다. 당시 exact producer bytes는 `fixtures/sc1004_holdout_before_integration.py`에 결과에 기록된SHA `0bb167921375d93b16f454984a6f062a1e43c7ee50bf37833d317f1eec4db484`와 일치하게 보존했다.

## 회귀와 다음 검증

`python -X utf8 -m unittest diagnostics.test_sc1004_resource_service -v`의5개 focused tests는2.087초에PASS했다. 기존 evidence에서 원 함수와 전체cfg/반환값의 pickle 동치, 세view만 변경·beta/다른 storage 불변,9종 변조 거부, partialGREEN·최종accepted 차감·statecopy 격리·다음substep budget 재설정을 확인한다. 구성 pickle roundtrip은 확인했지만 이번5개만으로 actual fresh worker의 local follower를 검증했다고 주장하지 않는다.

`git apply --check diagnostics/sc1004_resource_service.patch`와 diffcheck는PASS다. Hubble의 `sc1004_resource_service_peer_review.md`는 CSV 독립 재계수566/50/52/668 및 원천SHA, 반복ID 방문구분, 세view/단일budget을 검토했고 blocker를 찾지 못했다. 그가5개 테스트도 독립PASS했으며 endpoint는 중복 실행하지 않았다.

통합 후에는 테스트를 actual import로 전환하고 여섯 번째 회귀를 추가하여 **6 tests PASS(2.335초)**를 확인했다. 추가 회귀는 calibrated resource에서 pool OFF main/worker 거부, ON의 cfg pickle 및 실제worker installer가 같은1509.333333을 읽는지를 확인한다. OFF 비교는 shared 적용 후/pre-calibration의 exact `_configure_one`만 SHA검증된 `fixtures/sc1004_configure_before_calibration.py`에서 읽는다. runtime에 proposal builder 또는 frozen fixture가 연결되지 않는다.

적용한 패치SHA는 `68c475859b5afbb4d04e20001f097694bc8733a97b23005c4966c2f6bb8e6952`다. shared 적용 후 sourceSHA `84490a6f0551e464ed9870bdc17c8fee5913717f86d1ea0e3826c08df1941129`에서 contextual applycheck를 통과한 뒤 덮어쓰기 없이 적용했다. Root의 새 contract 설정 main/fresh-worker/ΩOFF preflight는 별도로 필요하다. 새 VISSIM 실런·성능 채택·seed14 검증은 아직 수행하지 않았다.
