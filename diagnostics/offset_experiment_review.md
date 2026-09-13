# Optimizer offset의 명시적 VISSIM experiment 경로

2026-09-10. 아래는 최초 제안의 검토 기록이다. **상태 갱신:** parent가 strict/native 정합 후 production에 통합했고 actual imports 회귀15개가 통과했다. 현재 적용 상태와 순서는 `final_signal_integration_review.md`를 따른다. `experiment`는 실제 최적화 offset을 쓰는 실험 선언이며 production 승격 판정이 아니다.

## 기존 경로와 변경 범위

|경로|현재 역할|제안|
|---|---|---|
|`offset_promotion.evaluate`, `lock_status`|D-core/N9 effect/N8-4의 상태와 동일 profile/topology를 검사|함수 AST 그대로. 없는 증거는 NOT_EVALUATED; 임의 PASS 없음|
|`resolve_writer`|config는 intent_only/test_only만 선언; production은 evidence 전용|config와 `RW_OFFSET_WRITER`가 **둘 다** experiment이고 `urban.physical_signal_contract is True`일 때만 experiment. 한쪽만 선언하면 예외. 기존 모드는 그대로|
|`written_offset_sec`|intent는0, test_only는 강제표/스칼라, production은 control.offsets|experiment만 optimizer의 `control.offsets`를 공통 cycle 기준 modulo→CSV 소수3자리 정규화. finite/positive cycle 검사|
|신호 공통 계약|실제 SG plan, green bounds, live-phase clearance, 정수초 event 시계|후보 clock과 두 CSV row가 같은 `written_offset_sec(control,cfg,signal)` 소비. 신호·SG offset을 다른 규칙으로 보정하지 않음|
|VBS 환경/CSV gate|환경 test_only까지 수락, 미선언 nonzero 거부; 전체 행 검증 후 COM 적용|experiment 환경값만 추가하는 데 그치지 않고 모든 row의 명시적 실험/physical-contract marker 요구. 기존 finite/cycle/SG window/conflict 검증 유지. SG offset=signal offset도 비교|
|실패 처리|일반 MPC는 실패 구간 이후 계속하고 끝의 integrity gate에서 실패|experiment는 기존 diagnostic과 같이 결정 오류/출력 누락/CSV 거부 시 즉시 Stop 및 exit3|
|최적화기 offset 유지 guard|0.5% 전역 TTT 개선이 부족하면 offset0 복귀|변경 없음. experiment가 nonzero 선택이나 성능 개선을 보장하지 않음|

명시 experiment는 나중에 세 증거가 모두 PASS가 되어도 해당 런을 production으로 바꾸지 않는다. `offset_production_writes=0`, `offset_experiment=1`, 실제 `offset_written_sec` 신호별 표, 원래 promotion 상태/이유를 action JSON에 함께 기록한다. `test_only`의 강제 offset 동작과 N9 matrix의 BLOCKED/PLANNED 판정도 그대로다.

## 발견한 두 가지 세부 의존성

현재 VBS `SignalGroupPlanRejectReason`는 `signalOffset` 인자를 받지만 실제 SG offset과 비교하지 않는다. 주석만 “이미 같음을 요구한다”라고 되어 있다. 제안은 experiment에 한해 `pendingSgOffset`과 `rowSignalOffset`의 존재/동일성을 적용 전 검증한다. 기존 mode의 행태를 이번 opt-in 패치에서 바꾸지는 않는다.

현재 `_action_csv_metadata`는 보통 status만 쓰고, physical projection provenance가 있으면 JSON을 넣는다. 그런데 VBS 파서는 단순 comma Split이다. experiment metadata는 쉼표 없는 scalar marker와 provenance SHA-256 참조를 쓰고, 원래 전체 provenance는 action JSON에 보존한다. CSV schema/열 수와 원 provenance 객체는 바꾸지 않는다. 일반 CSV quoting 지원은 별도 문제다.

`-0.0001` 또는 `cycle-0.0001`은 먼저 modulo한 후 round(3)하면 정확히 cycle이 될 수 있다. runner는 offset<cycle을 요구하므로 마지막 결과를0으로 감싼다. 이를 writer 뒤에서만 하지 않고 후보 평가에서도 같은 함수로 적용한다. 원 control.offsets는 바꾸지 않으며 실제 표현은 metadata의 `offset_written_sec`에 남는다. integer green/offset 강제는 하지 않는다.

## 적용과 실행 준비

필요 파일은 promotion, canonical adapter, VBS runner, 새 common signal contract다. shared runtime 설치는 선행 `signal_actuation_contract.patch`에 이미 들어 있다. vendor/optimizer 구현, offset keep_margin, 세 production gate, .sig/network는 변경하지 않는다.

- 순차 경로: 기존 `diagnostics/signal_actuation_contract.patch` 적용 후 `diagnostics/offset_experiment.patch`.
- 통합 경로: `diagnostics/signal_contract_with_offset_experiment.patch` 하나. 현재 frozen tree에서 `git apply --check` PASS. **두 경로를 중복 적용하지 않는다.**
- 생성: `python -m diagnostics.build_offset_experiment_patch`.
- 회귀: `python -m unittest diagnostics.test_offset_experiment -v`.

새 flattened trial config의 기존 MPC 설정을 유지하면서 아래 값만 명시한다. 얇은 extends overlay를 런처가 다르게 읽는 문제를 피하기 위해 실제 launch input은 완전한 config로 저장하는 것이 적절하다.

```json
{
  "urban": {"physical_signal_contract": true},
  "actuation": {
    "real_world_signal_control": {"enabled": true, "offset_writer": "experiment"}
  }
}
```

실행 환경은 `RW_OFFSET_WRITER=experiment`. forced diagnostic profile이 아닌 실제 wu-link/coordinated controller를 사용한다. 기존 joint/price offset search 설정을 사용하며, 이 writer mode만 켰다고 검색이 활성화되는 것은 아니다. config 선언과 env 선언은 초기 runtime configure 및 최종 writer resolve 양쪽에서 확인한다. spawned worker는 부모의 같은 cfg/환경과 공통 signal clock을 소비해야 한다.

## 검증 결과와 남은 실제 시험

**5 tests PASS, 3.219s.** 양방향 선언 불일치/contract OFF 거부, production evidence 판정 AST 불변, signed 및 wrap 경계/NaN/Inf, 17개 신호의 model/CSV 표현 동일, offset 후보에 따라 정수 event green fraction 변화, forced test_only 동작, metadata provenance 보존을 검사했다.

또한 제안 CSV를 실제 VBS `ApplyActionCsv`에 넣고 첫 `ApplyRuntimeSignals`까지 fake COM으로 실행했다. 정상 vector는 수락, SG offset 불일치/marker 누락/유효하지 않은 SG 창은 전량 거부했다. 실제 `RunControllerDecision`의 child-output 누락 경로에서도 experiment가 즉시 Stop/exit3하여 후속 simulation으로 진행하지 않음을 확인했다. Windows Script Host 설정 접근에 샌드박스 예외가 필요했으며 VISSIM 프로세스는 생성하지 않았다.

이 검증은 full MPC 최적화나 물리 신호 권한을 입증하지 않는다. 통합 후 한 observed state에서 실제 optimizer→후보 채점→선택 action JSON/CSV→VBS first-event 검사를 하고, live trial에서는 결정별 intended/written offset과 실제 COM post_step을 같은 선택 SG plan 및 절대 시각으로 확인해야 한다. offset0으로 남으면 search 활성, on/off objective, keep-margin verdict를 구분해서 보고한다. 새 모드로 production gate를 통과했다고 주장하지 않는다.
