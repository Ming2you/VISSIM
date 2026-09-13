# 3150초 native 중단: 관측 경로의 지난 목표를 보존하는 수정

원인 재현: `codex_phys8_fidelity_fw080_u050_cl9000_s13_v1`의 `state_003150.json`에서 12602 한 대가 STATIC1130:3을 유지한 채 10682 분기점을 지나 있었다. 1651대의 freeway 관측 중 known1441/NULL210이며 위반1대는 known의 부분집합이다. link2 lane1 position2984.55705764323m, branch10682 source2012.3574645080735m로 972.1995931351566m 뒤이다(FW_E cell11 대 sourcecell9). 1131 결정점2320.569721m도 지난 상태다.

2700/2850/3000/3150초의 같은 차량은 STATIC1130:3을 유지했고 link2 위치472.50975/1342.04825/1932.38613/2984.55706m였다. 정지 캡처·ID집합·network/mapping 핀은 정합하다. 단순 반올림이나 셀 인덱스 차이가 아니다. ERR2532초의 다른 차량10240에도 같은1130:3에서 link2끝까지10682를 찾지 못한 경고가 있지만, 이 사례의 차로변경 실패 원인이나 이후 native 삭제를 확정하는 근거로 쓰지 않는다.

수정은 `evaluation/controllers/offramp_routing.py`와 그 집중 테스트뿐이다. 원관측은 `observed_route:1130:3|missed_target:10682`로 남으며 현재 셀의1대를 삭제·이동 초기화·NULL 재분류·재추첨하지 않는다. 알려진 STATIC+컴파일된 목표+같은 본선+이미 목표를 지난 위치인 경우만 처리한다. 원 경로 밖 하류 본선 링크에도 이 표식을 보존하고 다른 본선/알 수 없는 경로는 계속 거부한다. 미래 결정이 남아도 이미 관측된 미확인 경로를 새 선택의 적격 코호트로 가정하지 않는다. 다음 실제 관측에서 정상 경로가 확인되면 그 새 관측으로 다시 초기화한다.

미확인 재고는 실제 accepted 본선 흐름을 따라 전진하되 분기 송출이나 정상 terminal TD에 넣지 않고 마지막 셀에 남겨 검열한다. 정상 terminal 재고는 원래 물리 용량을 사용할 수 있다. 미확인4+정상6, 용량2에서는 정상2만 나가고 미확인4+정상4가 남는다. 전체10대 흐름을0으로 만들거나 정상 흐름을1.2로 비례 감산하지 않는다. 이 정책은 native 운명을 아는 물리 법칙이 아니라 불확실성을 감추지 않는 보수적 예측이다. 최종 셀 재고의 TTT·수용 공간에 영향을 줄 수 있으며 정상TD가 낮아질 수 있다. 검열을 실제 정지·확정 삭제·정상 목적지 도달로 해석하지 않는다.

초기 metadata 위치:
- `offramp_route_inventory_initial_missed_target_veh`: 고정 관측 수량
- `offramp_route_inventory_initial_missed_targets`: 차량/원route/target/현재link·cell·position/초과거리/원path포함 여부
- `offramp_route_inventory_missed_target_diagnostics`: 초기 정책과 수량

예측 중/종료 진단 위치는 `state.offramp_route_inventory_state.missed_target_diagnostics`이다. `observed_missed_target_veh`는 최초관측 수량, `current_missed_target_veh`는 아직 보존된 전체 미확인 재고, `terminal_censored_veh`는 현재 마지막 셀의 검열 재고다. accepted 수송마다 갱신되므로 root의 endpoint 확인에서 이 세 값을 별도로 추출하면 된다. 해당 class가 없던 상태는 진단 키도 추가하지 않아 기존 직렬화를 유지한다.

검증: 기존 오류를 먼저 recorded3150 집중 회귀로 재현했다. 최종 관련6모듈84 tests PASS(12.972초), 기록900(기존·현재CL) 및3000의 inventory+metadata 직렬화 SHA/바이트 수가 수정 전과 같다. 마지막 소스의 실제 config/action003000/state003150를 사용한 canonical `build_projected(..., fixture_inputs=False)` 초기화도 PASS(2.122초): FW_E1027+FW_W624=1651, 관측미확인1/현재미확인1/terminal검열0. 전체 예측·새 native는 실행하지 않았다. 독립 읽기 검토에서 추가 중대 문제는 없었다.

근거 파일: `route3150_prepatch_initialization_v1.json`(정상상태 수정 전 지문), `route3150_initialization_after_fix_v1.json`(중간 초기화 이력), `route3150_initialization_after_fix_v2.json`(최종 소스/입력 핀 및 회귀). 최종 production SHA-256: `e9eef95455df833c7ab2c332d7096597165f712a30eccf3d61165dac869b1b03`. 테스트 SHA-256: `c63eb571f6033f6af93e0b3eae1ff102861f065fab734ea985555030f333ae12`.
