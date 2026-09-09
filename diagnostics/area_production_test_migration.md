현재 통합된 production을 직접 검사하도록 area·route·SC2001·strict runner 회귀를 전환했습니다. 예전 `area_routes_and_sc2001.patch`를 현재 파일에 다시 적용하지 않습니다. 그 패치와 기존 handoff 문서는 적용 전의 역사적 증거입니다.

변경한 진단 파일:

- `test_area_projection_coverage.py`: 실제 `projection_support.configure` 호출. OFF와 이전35개 지원 자료는 git3299040의 고정 configure와 비교합니다.
- `test_dynamic_area_routes.py`, `probe_area_endpoint.py`: 실제 `evaluation.controllers.area_dynamic_routes`를 사용합니다.
- `test_sc2001_corridor.py`: 실제 corridor와 urban dispatcher 사용. corridor OFF body/state는 git3299040과 정확히 비교하며 Ω OFF에서도 실제 physics dispatcher가 작동하는지 확인합니다.
- `test_observation_projection.py`: patch builder 대신 현재 adapter의 observation summary 사용. 원래6056c94의 disabled 비교 함수만 고정 reference로 남습니다.
- `probe_sc2001_corridor_replay.py`: fixture와 CLI replay는 실제 production 모듈을 사용합니다. 다섯 진단 소비자를 현재 `build_projected`/`configure_runtime` 및 설치된 endpoint로 이전한 뒤 `proposal_module()`과 그 전용 `types` import를 제거했습니다. 실제 OFF 비교의 고정3299040/6056c94 source reference는 그대로 보존합니다.
- `test_strict_decision_failfast.py`: patch generator 없이 현재 watchdog의 실제 strict gate와 현재 VBS 함수를 직접 추출합니다. 자식 프로세스는 실제 실행하고 VISSIM은 fake 객체만 사용합니다.

최초 production 전환 당시 검증 명령과 결과:

```text
python -m unittest diagnostics.test_area_projection_coverage diagnostics.test_dynamic_area_routes diagnostics.test_sc2001_corridor diagnostics.test_observation_projection diagnostics.test_area_arrival_routes -v
36 tests PASS, 24.124 seconds

python -m unittest diagnostics.test_strict_decision_failfast -v
6 tests PASS, 7.436 seconds
```

Strict 검사에는 일반 `wu-link`의 Ω ON에서 nonzero exit·CSV 누락·불완전 CSV 각각 stop/exit3, OFF·absent·null의 기존 계속 실행과 stale env 초기화, 상속 ON 및 명시적 OFF, 정상 실제 CSV 적용, 순환 config의 실행 전 실패가 포함됩니다. 현재 production의 diagnostic OR strict OR offset-experiment 조건을 그대로 실행했습니다. Windows Script Host 초기화를 위해 sandbox 외 실행이 필요했지만 VISSIM COM 생성·접속·시뮬레이션은 하지 않았습니다.

필수 데이터 목록과 byte SHA는 `area_production_required_files.json`에 있습니다. `inventory_area_production_dependencies.py`로 재생성합니다. 추가 runtime 자료8개는 다음과 같습니다(기존 pinned network·membership·jam·gate·demand5개는 별도 목록).

```text
diagnostics/control_area_physics_overlay.json
diagnostics/control_area_route_contract_physical_routes.json
diagnostics/physical_movement_routes_ver2.json
diagnostics/dynamic_area_routes_ver2.json
diagnostics/dynamic_area_nc13_calibration.json
diagnostics/shared_approach_ver2.json
diagnostics/sc2001_corridor_nc13.json
diagnostics/physical_projection_support_635_proposal.json
```

`dynamic_area_nc13_calibration.json`은 다른 JSON에서 raw byte hash로 검증하므로 `.gitattributes`의 명시적 **CRLF** checkout 속성을 유지해야 합니다. 검증된 상태는 `i/lf`, `w/crlf`, `eol=crlf`이며 실제 raw hash는 CRLF 바이트 기준입니다. `physical_projection_support_635_proposal.json`은 이름에 proposal이 있지만 통합된 runtime에서 사용하는 고정 입력입니다. 학습용 FZP와 SC2001 audit은 runtime에 필요하지 않습니다. 같은 seed13에서 학습한 prior의 한계와 unknown45개 양수 시 중단은 유지됩니다.

후속 작업에서 **portable fixture 배포도 구현했습니다.** `diagnostics/fixtures/control_area_v1.zip`은 원본45개 JSON/CSV와 OFF용 git blob4개를5.6 MB에 보관합니다. `python -m diagnostics.run_portable_fixture_tests --include-wsh`는 새 `.review-fixtures` 하위 위치에 raw와 경로만 재연결한 사본을 분리 복원하고 실제 테스트를 실행합니다. 원래 `evaluation/runs` 접근과 git subprocess를 금지한 별도 프로세스에서 검사하므로 이전 절대경로나 로컬 history가 우연히 남아 있어도 이에 기대지 못합니다. 원본 run ID·관측수치·source SHA는 그대로이며 모든 파일 위치 변경을 별도 로그로 보관합니다. 이 한정된 회귀 묶음에는 과거 run 폴더나 deep git history가 더는 필요하지 않습니다. 상세 사용법·범위·검증 결과는 `diagnostics/fixtures/README.md`에 있습니다.

미터 finalization 통합 후 `probe_area_endpoint.py`는 실제 tuning·physical mapping·현재 raw snapshot·직전 action 경로·calibration으로 `area_meter_finalization.configure`를 호출합니다. `probe_sc2001_corridor_replay.py`도 corridor 최종 재투영 state의 spillback 문맥으로 이를 갱신합니다. 가짜 marker를 만들거나 finalizer를 우회하지 않습니다. 추가한 실제 150초 endpoint 회귀는 입력 control 불변, 관측 유량·spillback 문맥 일치, 최종 모델 차량 재고와 Ω 장부의 일치를 확인합니다.

`python -m diagnostics.run_portable_fixture_tests --include-wsh` 최신 재실행은 **49 tests PASS, 37.689초**입니다(기존48개와 새 endpoint1개). 새 격리 subprocess의 원래 run 접근 시도와 git 호출 시도는 모두0이며 결과는 `diagnostics/portable_fixture_validation.json`에 있습니다.

Production controller·watchdog·VBS에는 이 마이그레이션으로 추가 변경을 하지 않았습니다.
