# 동결 본선 모델의 독립seed67 검증

2026-09-30. **네 native3300초 런과 세 동결 모델×네 명령의450초 예측12회를 완료했다.** 네 실행은exit0이고 LDP/명령 적용 검증을 통과했다. 공통 초기 궤적은 정확히 일치했다. 기존9000초 STOP은 유지했다. 전체 목적은 본선 물리 반응 검증 후 전체 Ω·SDMPC 연결 및9000초 비교이며, 이번 짧은 시험으로 그 완료를 대신하지 않는다.

결과는 `../baseline_reproduction_20260929/cellwise_calibration/freeway_first/choice67/README.md` 및 같은 폴더의 `summary.json`, `flow_decomposition.json`, `verification.json`에 있다. **RM 유지의 큰 이득과 최선 명령은 세 모델 모두 구별했지만, VSL 방출 반응 검증은 미완료다. 새 계수 채택·재보정·9000초 실행·push는 하지 않았다.** 아래 종료 후 절차는 모두 실행 완료했으므로 다시 호출하지 않는다.

## 조건

- 선택80–90 DSD110 망64cf5f55…에서 randSeed29→67만 변경했다. 수요·경로·기하·도시 신호·본선 입구110·SimRes10·FZP5초는 동일하다.
- 기존seed29 ALINEA 명령 이력을 재생한 공통 상태에서,2700초부터 RM 유지/허용폭 내 완화와 VSL110/90을 조합한4조건이다. 새 ALINEA 피드백이나 무제어 시작 실험이 아니다.
- 비교 초기2670.1초, 예측/실측450초, 평가 끝3120.1초. native 종료는기존 실행기에 맞춰3300초다.
- expanded036+경로재고, 연결FD, 셀24·25 회복부 후보 세 모델을 모두 사전에 동결했다. `protocol.json/comparison_pins`에 모든 모델·설정 출처를 고정했다. seed67로 재보정하지 않는다.
- 기존 의미 있는 차이 기준을 유지한다: 본선|ΔTTT|≥0.5veh·h인 모든 쌍의 방향, 선택 손실0.5veh·h, 합류·방출 차이≥10대의 방향. 작은 효과는 미확인으로 둔다. 램프 대기·진출부 비용·삭제·외부 대기·전체Ω는 구분한다.

## 실행

결과 폴더: `D:/VISSIM_runs/20260930_release2670_s67`.

네 조건의 기존 실행기 dry-run이 모두exit0. 기존seed61 큐에서 결과 경로와seed만 바꿨고, 다른VISSIM이 있으면 시작하지 않는다. 네 조건 병렬, 자동 재시도0회, 소유PID·생성시각을 이용하는 초기300초 실제 무진행 watchdog을 사용한다. 상세분석은 모든native가 종료된 뒤에만 수행한다.

큐 시작: PID11012, 생성2026-09-29T21:30:30.2993511Z. 권위 있는 현재 상태는D드라이브`task_status.json`과 실제 프로세스/개별`run.json`이다. 이 문서의 시작 기록이나 상태 파일만으로 실행 중이라고 가정하지 않는다. `STOP`이 생기면 재개하지 않는다.

## 종료 후 사용할 기존 경로

새 분석 프레임워크를 만들지 않았다. U worktree에서 기존 Python과`PYTHONPATH=.;vendor/NumSim-mine`를 사용한다.

1. 기존`heldout53_response_v2/postprocess.py extract --case-dir <이 폴더>`.
2. 같은postprocessor의`capture --case-dir <이 폴더>`.
3. 기존`replay_congested_component.py capture-route-seed67` — 공통초기2670.1초의 현재 경로·위치만 추출하고31셀 N/v 정합을 확인한다.
4. 같은helper의`check-frozen-seed67` — 현재 경로재고+동적off-ramp 저장/배수로 세 동결 모델×네 명령,12회 예측. 미래 관측은 점수에만 사용한다.

**기존postprocessor의`all` 또는`predict`는 호출하지 않는다.** 그 구경로는 현재 경로재고·storage 조건 없이 예측하므로 이번 세 모델 비교와 다르다. 새 예측은`freeway_first/choice67`에 저장한다. 이미 존재하는 완료/실패 산출물이 있으면 자동 반복하지 않고 실제 상태를 먼저 확인한다.

추출·capture·예측 함수는기존코드를재사용했고,추가옵션은새seed/현재snapshot전용/세동결모델평가에한정했다. 기존core와vendor는 이번에 수정하지 않았다. 새seed 결과를 본 뒤 모델 pin이나 판정 문턱을 바꾸지 않는다.
