# 관측기·실행 방식·시뮬레이션 길이 대조 결과

**1050초인 세 런 B/C/D는 차량 궤적이 전부 같았다.** 관측기 ON/OFF, stepwise/continuous, 동일 DSD 값의 재적용 횟수 차이가 이 1050초 NoControl 결과를 바꾸지 않았다. 기존 5400초 런 A의 첫1050초와는1031초부터52행의 위치·속도·지체가 다르다. 차이는 짧은 런/긴 기준 런 구분과 일치하지만, A의 소프트웨어 버전도 과거 것이므로 SimPeriod 하나의 인과효과라고 최종 확정하지 않는다.

| 조건 | 런 이름 | 관측기 | 요청 길이 | 실행 방식 | 1050초까지 실제 명령 재적용 | 궤적 그룹 |
|---|---|---|---:|---|---|---|
| A | codex_area_observed_nc_s13_20260910 | 기능 도입 전 | 5400 | continuous | 1,900 | A |
| B | codex_contract_observed_nc_s13_1050_v2_20260910 | ON | 1050 | stepwise | 1,150,…,1050 | B=C=D |
| C | codex_contract_nc_headoff_stepwise_s13_1050_v3_20260910 | OFF | 1050 | stepwise | 1,150,…,1050 | B=C=D |
| D | codex_contract_nc_headoff_continuous_s13_1050_v3_20260910 | OFF | 1050 | continuous | 1,900 | B=C=D |

모두 seed13, 동일 네트워크·수요·물리 제어 매핑의 NoControl이다. C/D는 같은 OFF config와 동일한 전체 source manifest를 사용했다. ON/OFF config의 의미 차이는 `urban.capacity.head_observation.enabled` 불리언 하나뿐이다. B/C 전체 build는 동일하지 않다. launcher의 ForceStepwise 전달과 독립적인 adapter/local_signal_service 가격 수선 세 파일이 달랐고, OFF overlay가 추가되었다. 이 차이를 숨기지 않고 실제 물리 명령·관측·출력을 따로 비교했다.

## 물리 출력과 명령

- B/C/D는 각1,992,241개 native FZP 행의 순서와 모든 필드가 byte exact이다. 공통 SHA는 `b12c29926e17fa61f26b19806486a198e50af60cb66d56c3bf143501887c46f2`이다.
- A와의 차이는9대/52행이다. 1–1030초는 전행 exact이고, 이후 POS52·SPEED41·DELAYTM17만 다르다. 최대 차이는26.79m·37.66km/h·1.46s이다. 전체 시각·ID·link·lane·POSLAT·TMINNETTOT는 A까지 모두 같다. 기존의5bytes는 payload 길이 차이였으며, 단순 포맷 차이를 뜻하지 않는다.
- 네 런 모두1050초까지 native `.lsa` 신호 변화6,051행이 raw exact이다. SHA는 `eefd581aef8b39f4a851599574cdb438d8c269ca19c13121de2531446013d1f2`이다. SC2/16/17을 포함한 실제 native SG 변화 차이가 없다.
- 각 적용 시점의66개 VSL DSD와8개 ramp 명령 및 readback은 네 런 모두 동일하다. VSL selector120/readback120|120, ramp green10이며 실제 urban signal 적용 행은0이다. `SetClassSpeedChecked`는 동일값이라도 각 DSD의 차종10/20/30/70 selector를 다시 쓴다. global 분포곡선이나 개별 차량 Speed를 쓰는 경로는 아니다. 1050초에서8회 대2회의 재적용 차이도 출력 차이를 만들지 않았다.

따라서 다음1050초 실제 제어 smoke에는 같은1050초 NC를 기준으로 사용한다. B는 관측기 ON과 현재150초 누적창을 갖춰 해당 관측 문맥에도 맞는다. A의 첫1050초를 짧은 런의 완전 동일성 기준으로 취급하지 않는다. 장기5400초 평가에는 같은 길이·최종 source·의도한 실행/관측 설정의 NC를 따로 확보하면, 과거 코드와 horizon 영향을 더 분리할 수 있다. 이번 대조는 추가5400초 런을 실행하거나 그 결과를 추정하지 않았다.

## 관측값은 어디까지 같은가

B/C의8개 snapshot에서 순간 전체 차량/현재 route/FW셀/count/speed/demand 등 모든 top-level 물리 값은 exact이다(런 provenance만 제외). OFF8개 snapshot에는 head window가 없고, ON의235개 head는7개 nonempty 창 모두 물리 신원·15자리 직렬화 좌표·실제 native GREEN 적분이 정합했다. 동일 run/config/network/geometry 문맥의 이전 floor와 연속 두 창 후보만 유지되었다. 설치 member가 없는19개 그룹은 계속 명시되며 이를 성공한 capacity 반영으로 세지 않는다.

**누적 관측창은 의도한 기능 범위상 다르다.** B의 queue_window_samples는 첫149, 이후150으로 매초 수집한다. C는 각150초 창에5개이며, A/D는900초 결정의 긴 창에31개다. B/C에서는 far_measurement와 link_departures/window mean/max6개 필드가 달랐다. 따라서 ‘head window만 제외하면 모든 관측이 같다’ 또는 ‘MPC 선택도 동일하다’고 주장하지 않는다. 비교한 물리 NoControl 출력은 정확히 같다는 범위다.

C의 manifest는 RW_FORCE_STEPWISE transport 키 자체를 담지 않는다. 실제 `RUN_MODE=STEPWISE controller=no-control` 로그와 pinned launcher/watchdog 분기·전달 인수로 실행 근거를 보존했다. D는 actual continuous mode 로그와1/900 적용 시점으로 구분된다.

## 종료·비용·원자료

B의 native ERR는10개 lane-change 제거(Ω내5/외5), terminal24/120 제거0으로 보존됐다. 시각 없는 `Stop the simulation? : &Yes` note는 파일순서상1045 경고 뒤, 잔여입력/DLL 공지 앞에 있다. 정상 VBS는1050에서 SIM_DONE 후 COM 객체를 해제한다. 이 종료 문맥만 기록하며 note를1031 차이의 원인으로 보지 않는다. C/D의 native ERR는 root가 별도 보존했다. 삭제 차량 ID 전체를 TTD에서 제외하는 변경은 하지 않았다.

parent watchdog 경과시간은 B622s/C180s/D120s다. B의8개 decision 호출 합23.61s와 capture batch1,050회/동시각 cache 재사용45회는 확인됐다. 하지만 per-component 계측이 없어 시작/로딩·시뮬레이션·COM·직렬화 시간을 분리할 수 없으며,622−180초를 순수 collector 비용으로 단정하지 않는다.

주요 재현 자료는 `observer_four_condition_comparison.json`, `observer_on_v2_off_v3_control_pair.json`, `observer_on_v2_off_v3_build_provenance.json` 및 두 새 prefix comparison JSON이다. 원 streaming proof와 파일 size/mtime를 확인해 A/B/C의 기존 digest를 재사용했으며 최종 요약 단계는 FZP를 다시 스캔하지 않았다. D/C의 실제 prefix 비교는 각1050초 범위만 한 번씩 읽었다. 역사적 v2 실패/완료 보고서와 원본 source SHA는 수정하지 않았다.
