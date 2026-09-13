# Native 신호 기준점의 선택적 표현

`signal_group_plan.py`에 명시적 `NodePlan.native_clock_basis`를 추가했다. 현재 선택된 계획 JSON·설정·망은 바꾸지 않았으며, 제어 실행에도 아직 활성화하지 않았다. 필드가 없는 계획은 기존 주기식과 SG 창을 그대로 사용한다.

`build_native_clock_basis(plan, parse_sig(...), amber_sec=3, all_red_sec=0)`는 기존 파서와 SG 매핑에서 다음을 도출하고 전체 source 상태를 검증한다.

- 일반 15개 SC: native 순서와 150초 주기, 기존 녹색 합.
- SC16: p3→p2→p1, p3 황색 뒤 34초 고정 공백, 녹색 합 107초, 주기 150초.
- SC7: p1/p2 동시 시작, p4 시작=g2+3초, g2+g4=114초, g1+3≤g2, 주기 120초. g1은 고정합 밖의 독립 좌표다.

`native_phase_windows`가 현시 창을 만들고 기존 `plan_windows`가 SG 창으로 전개한다. `node_cycle_sec`는 유효 명령의 고정 native 주기를 반환한다. `plan_state_at`은 해당 SG의 녹색 뒤에 황색을 적용한다. 따라서 SC7의 67–70초 SG4·8 황색은 동시 SG7 녹색 때문에 사라지지 않는다.

원점은 `.sig`의 0초로 유지한다. writer가 `(t+offset) % C`를 사용하면 `reference_offset_sec=(-program_offset_sec-controller_offset_sec) % C`다. 현재 SC7은 119초, SC16은 1초다.

`native_clock_basis_source_v1.json`은 활성화하지 않은 17개 SC의 basis, 원망·원계획·모든 `.sig` SHA256, 초기 SG 상태와 검사 결과를 담는다. 실제 phase 매핑에 속한 SG만 검사하며, 매핑 밖 midblock SG는 제외한다. 영구적색인 소유 SG는 포함한다. source의 모든 상태 경계와 구간 중점, 별도 0.5초 간격 40,320개 상태가 일치했다. 이는 source 표현 검증이며 새 COM 실행 검증 결과는 아니다.

검사: `python -B -X utf8 -m unittest diagnostics.test_native_clock_plan tests.test_signal_group_plan tests.test_action_csv_signal_group_rows tests.test_model_plant_native_share_identity` → **44개 통과**. 기존 테스트 하나는 SC16에서 p1/p2/p3 명령을 잘못 불가능하다고 가정해 실패했다. 수정 전 git HEAD 구현도 같은 명령을 허용함을 확인하고, 실제 live set을 벗어나는 명령을 생성하도록 테스트를 고쳤다.

`signal_actuation_contract.py`의 선택적 모델 연결도 구현했다. 설정 시 기존 파서로 `.sig`를 다시 읽어 선언한 basis와 대조하고, 모델의 주기·live set·green budget을 검사한다. SC7의 budget114는 p2+p4 합이며 p1은 독립이다. SC16의 budget은107이다. `phase_bounds(net,signal)`가 phase별 경계를 제공한다. 캐시 키에는 native basis·설정 주기·minimum policy가 포함된다.

native 최소녹색 예외는 `net.native_signal_minimum_policy='include_source_reference'`를 명시할 때만 적용한다. 각 phase 최소값은 `max(writer_min5, min(configured_min, source_green))`이다. configured_min20일 때 SC16의 p2만17로 낮아지고 p1/p3은20을 유지한다. 이는 실제 native 기준점을 포함하기 위한 공개적인 제어 조건 수정이며 순수 계산 최적화가 아니다. 변경 한도는 여전히 실제 이전 행동에 고정된 별도 박스에서 검사한다.

추가 검사: `python -B -X utf8 -m unittest diagnostics.test_native_signal_contract diagnostics.test_joint_urban_neighbors diagnostics.test_native_clock_plan tests.test_signal_group_plan` → **38개 통과**. 이 중 native phase 구간2016개를 source와 비교하고, basis 없는 기존 경로544개 값을 보존한 함수와 float bit까지 대조했다. SC7 독립 p1/쌍교환, SC16 19→17초 반환, source와 설정 불일치, 캐시 문맥 변경도 검사했다.

전체 cohort는 미활성이다. adapter·writer 연결, SG별 황색, 최초 native→COM 소유권 전환의 짧은 LSA 확인은 별도 통합 작업이다. 진단용 기존 `test_signal_clock_cache.py`는 과거 소스 SHA를 고정하므로, 이 선택적 기능의 소스 변경 뒤에는 그 과거 판정을 현재 기능의 qualification으로 사용할 수 없다. 위 새 검사는 과거 함수의 수치 결과를 직접 비교한다.
