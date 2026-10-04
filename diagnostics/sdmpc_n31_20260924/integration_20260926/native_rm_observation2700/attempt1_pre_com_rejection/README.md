# 실행 전 오류 수정

첫 실행은 VISSIM COM 생성 이전에 `OBS150_STARTUP_REJECTED single-decision diagnostic controller`로 종료됐다. 실제 시뮬레이션 시간은 진행하지 않았고 완화 조건은 시작하지 않았다. 원본 로그와 첫 동결 트리는 보존했다.

정본 runner의 `UseSingleDecisionEventMode()`가 고정 명령 재생에도 한 번만 제어하는 모드를 반환한 것이 원인이다. `RW_COMMAND_REPLAY_DIR`가 있는 경우에는 매 제어 시각 재생하도록 이 함수만 수정했다. 신호 시계·황색·수요·물리 모델·관측 주기는 바꾸지 않았다.

실제 VBScript 함수의 7조건 회귀 시험은 수정 전 재현 실패, 수정 후 통과했다. 기존 재생 파일 동일 복사·덮어쓰기 거부·가격 영수증 미생성 시험도 통과했다. 최초 샌드박스 안의 cscript 실행 실패는 런타임 시험 결과로 사용하지 않았고, 허용된 환경에서 재현·통과를 확인했다.

새 결과 경로는 `D:/VISSIM_runs/20260928_rm_observation2700_s47_v2`. 새 교통 조건을 추가하는 것이 아니라, 아직 생성되지 않은 승인된 두 VISSIM 런을 수정된 runner로 시작한다. 기존 실패 파일과 9000초 STOP은 유지한다. 자동 재시도 루프는 없다.
