# 최종 signal/offset/strict 실패처리 통합 감사

2026-09-10. parent가 area 패키지와 strict failfast를 먼저 적용했고 native selector도 적용한 뒤, 현재 tree 기준으로 signal+experiment combined diff를 재생성했다. `git apply --check` PASS 후 parent가 통합했다. 이 문서는 production 적용을 다시 지시하는 새 patch가 아니다.

확정된 실제 순서는 **area 패키지(기존 strict 포함) → native_fixed_selector → 현재 기준으로 재생성한 signal_contract_with_offset_experiment**였다. 원 strict patch와 옛 signal combined를 이어서 그대로 적용하면 같은 VBS If문이 충돌한다. 최종 VBS는 diagnostic OR strict 환경 OR experiment를 모두 보존하고, 실패 label은 diagnostic / experiment / strict로 구분한다. strict/native는 이미 적용되어 다시 적용하지 않는다.

재생성된 signal diff의 대상은 canonical adapter, runtime_setup, 새 signal_actuation_contract, offset_promotion, canonical VBS다. 기존 native_fixed_control 함수의 selector 변경을 되돌리는 hunk는 없고, watchdog strict 설정도 건드리지 않았다. superseded adapter, .sig, network 및 inactive controller는 변경 대상이 아니다. 환경 experiment만 허용하는 whitelist 변경이 아니라 config/env 동시 선언, physical signal contract, scalar metadata, SG/axis offset 동일성 및 실패 종료를 함께 검사한다.

두 regression suite를 proposal 생성/함수 AST 실행에서 **실제 production imports**로 옮겼다. `python -m unittest diagnostics.test_signal_actuation_contract diagnostics.test_offset_experiment -v` 결과 **15 tests PASS,15.911s**. 실제 adapter writer, 선택된 mainline SG plan, 공통 runtime/worker 설치, native selector, actual VBS parser·정수 event·실패 종료를 사용한다. 37개 n7 action/17개 신호의465,460 fraction 비교, actual VBS10,395 event 비교를 포함한다. VISSIM 객체만 fake인 parser/event 검증은 실제 COM 권한 시험과 구분한다.

실제 optimizer decision에서 확인할 metadata는 `physical_signal_contract_enabled=1`, `offset_writer=experiment`, `offset_experiment=1`, `offset_production_writes=0`, 원 promotion 상태/이유, 그리고 신호별 `offset_written_sec`다. raw offset은 의도이며 signed/modulo/3자리 반올림을 거친 실제 값은 이 표 및 signal/SG CSV 양쪽과 같아야 한다. 원 config provenance는 action JSON에 보존하고 experiment CSV는 scalar marker와 SHA 참조를 쓴다. selected plan과 실제 CSV green vector가 일치해야 하므로 SC109 과거96.5초 값은 후보 전에 feasible projection된다. green10 진단의p1=10초는 이 MPC green_min20 범위 밖이며 새 optimizer 후보로 자동 승인하지 않는다.

통합 후 발견한 별도 목적함수 소비자 문제는 `area_follower_objective_handoff.md`와 추가 최소 patch에 기록했다. 기존 global-TTT offset/fallback veto는 signal clock/actuator 계약만으로 해결되지 않아 parent가 추가 helper를 통합했고, 실제 helper imports 회귀5개도 통과했다. 실제 main preflight 및 COM 시험 결과는 별도로 확인해야 최종 Ω MPC 경로가 완료된다.
