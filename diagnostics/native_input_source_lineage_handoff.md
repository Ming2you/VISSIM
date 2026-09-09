10379는 합류 뒤 가까운 저장고로 임의 분배하지 않고, 합류 전 원점 경로가 모두 같은 수신 저장고를 가리킨다는 증거로 `SC11_to_SC1`에 한 번 투영합니다. `projection_support.py`가 실제 source의 모든 유입 connector, 현재 canonical movement의 receiving_link, native1104 경로, 신호·input 부재, 전진 위치와 계약 SHA를 검사합니다. 다른 원점이 섞이는 하류1210008203의 소유권은 변경하지 않습니다. 이는 초기 위치의 투영 수선이며 신호 서비스 권한 변경이 아닙니다.

10381은 input1091에서 발생한 별도 원점이므로 같은 저장고로 합치지 않습니다. 실제 실행에 사용한 `urban_input_gate_map_ver2_20260907.csv`에서도1091은 gate가 비어 있는 internal 행입니다. 과거 legs4b 행도 같으므로 문서의 오래된 파일명만으로 생긴 차이는 아닙니다. native236→10381→SC1 E 접근 경로는 `in_SC1_E`로 이어지고 Ω 안에서 발생합니다. `native_internal_input.py`는 해당 물리 입력·전체 접근 경로·SC1 도착 movement를 검증한 opt-in helper입니다. 새 어댑터, 새 저장 용량, player territory 또는 Ω 변경은 없습니다.

희망 수요와 실제 모델 유입을 구분했습니다. 원래 INPX의1091 시간표는112/160/168/144/112/80 veh/h이고, 기록된 실행의 demand scale1과 urban_input 배율1에서는 그대로 유지됩니다. 전체5400초 희망 수요 적분은194대입니다. helper는 기록 manifest의 network/profile/role 파일과 실제 배율, 현재 internal aggregate2120 veh/h까지 검증하며, 다른 시나리오에 원래 시간표를 무조건 주입하지 않습니다. VBS는 각 interval write를 readback으로 검사하지만1091 개별 readback 값은 당시 로그에 따로 없었다는 한계가 있습니다.

미래 유입은 기존 finite receiver가 수용한 양만 stock에 추가하고 도착·release buffer에 한 번씩 예약합니다. 수용하지 못한 희망량은 후보별 unadmitted demand로 보존하며 TTT stock에는 넣지 않습니다. 외생 gate forecast의 `in_SC1_E`가 양수면 이중 유입을 막기 위해 실패합니다. 미래 수용량은 Ω 내부 발생(`input:internal:1091`)으로 보존식에 반영하고 boundary entry/TTD는0입니다. 초기 관측236/10381 재고에는 발생·entry·exit 이벤트를 새로 만들지 않습니다.10381은 무조건적 support alias로 추가하지 않았고 검증된 helper claim이 있을 때만 미확정 양수 guard를 통과합니다.

현재 정본 runtime의 configure→prepare→projection support→state→paired transit→initialize→area seed 순서와 worker/Ω OFF dispatch까지 연결되어 있습니다. 도시5초 step마다 advance를 한 번 호출합니다. 기존 SC1 접근 routing/phase와 중간SC2 지연 모델은 유지하므로 native12 회전 비중·중간 신호 지연을 새로 보정했다는 주장은 하지 않습니다. 새 기능이 없으면 helper와 claim guard는 기존 객체와 buffer를 그대로 반환합니다.

검증은 두 범위로 나뉩니다.

- `route_input_fixture_validation.json`: 새 복원 위치에서 원래 run/Git 접근을 금지한46개 실제 production 회귀 PASS. path/receiver/claim 변조, 초기 stock closure와 출입0, 희망량=수용량+대기량, 한 번만 전이, candidate copy와 fresh worker, 신호 phase 계약을 포함합니다.10379 양수 회귀는 실제 FZP 기록 값을 새로운 ID로1350 복사본에 삽입한 **명시적 합성 장면**입니다. 실제1350에10379가 있었다고 주장하지 않습니다.
- `native_internal_input_canonical_1350_450.json`: 실제1350 상태와 직전1200 명령으로450초 canonical main/repeat/fresh worker가 동일하고 Ω ON/OFF의 물리 상태도 동일합니다.1091 희망20대=수용20대, 미수용0, 내부 발생 ledger20대, 외생 `in_SC1_E` forecast0, caller payload 불변, source 변경0입니다. 이 과거 관측에는 현재 route 정보가 없어6대의 지난 분기 선택을 명시적으로 holding한 진단입니다. live error 정책과 새 COM route 관측 검증을 대체하지 않습니다.

기존7개와1128 시험은 새 기능을 별도로 켜도록 `fixtures/area_baseline_before_route_choice_beta0.json` 또는beta300을 시작 설정으로 사용합니다. 이는 고정된 과거 진단 설정이며 활성 실행 설정을 덮어쓰지 않습니다. pure1200을 사용하는5개 CLI migration 시험은 현재 production endpoint의 명시적 입력 전달 범위를 확인하며 새 route/input ON 성능 검증으로 해석하지 않습니다.

`route_input_v1.zip`은 실제1350/1200 raw snapshot, 직전1200/1050 action, 원래 run manifest, baseline 설정2개,10379 관측 레코드 등8파일을403,552 bytes로 보관합니다. SHA256은 `0f6529401ca39b1c4dbb7188757290139480b4eb518bcd5efcba9e6fc87be04c`입니다. 원본 바이트·SHA는 ZIP에 그대로 남고 복원 복사본만 절대 경로 문자열을 옮깁니다. 기존 control_area_v1/receiver_turns_v1 ZIP과 과거 `portable_fixture_validation_custom.json`은 바꾸지 않았습니다.

재현 명령: `python -X utf8 -m diagnostics.run_route_input_fixture_tests`. production/vendor/pinned 자료는 현재 checkout에서 읽으며 VISSIM을 실행하지 않습니다. 해당 helper·tests·자료의 정확한 배포 목록은 `route_input_handoff_paths.json`에 기록합니다.
