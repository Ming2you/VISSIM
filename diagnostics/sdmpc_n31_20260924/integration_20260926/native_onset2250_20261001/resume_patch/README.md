# Native 종료 지연으로 중단된 큐의 재개

2026-10-01 05:34:13에 기존 큐가 `VISSIM is already open`으로 종료됐다. held_actual과 rm_only는 각각2700초·DECISIONS_FAILED/OBSERVATION_FAILURES/SIGNAL_FAILURES/ACTION_FORMAT_FAILURES/COM_FAILURES=0이며 watchdog 정상 종료를 기록했다. rm_only의 watchdog가 반환된 직후 다음 조건의 전역 존재 검사가 아직 닫히는 중인 VISSIM을 발견했다. 05:34:34의 OS 조회에서는 VISSIM/cscript가 없었다. 런 두 개의 성공과 이후 사후 검증 통과는 구분한다.

기존 `native_pair1200/run_pair.ps1`만 보완했다. 정상 종료 후 watchdog가 기록한 소유 VISSIM PID와 현재 생성시각을 대조하고 최대30초 종료를 기다린다. 다른 PID·재사용된 PID·시간 초과는 실패 처리하며 프로세스를 강제 종료하지 않는다. 기본 실행은 기존 결과를 덮어쓰지 않는다. 명시적 `-ResumeCompleted`에서만 완료 마커·오류0·watchdog 성공·seed/기간/동결 경로·network/tuning/VBS SHA·native 종료 관측을 검사하고 완료 런을 재사용한다. 실패한 교통 런은 재실행하지 않는다.

12개 검사 통과: 실제 완료 두 런의 소규모 파일 사본으로 정상 재사용·잘못된 seed/tuning·미완료 거부를 확인했다. OS mock으로 소유 종료 대기·다른 PID/재사용 PID 거부·시간 초과 시 kill/retry 없음도 확인했다. `verification.json`, `verify_resume.ps1` 참조. 시험 중 live VISSIM 조회/조작·새 native 런0이다.

기존 coordinator는 검토된 새 launcher SHA를 명시한 재개를 허용한다. 물리 VBS/adapter/watchdog/명령/분석기는 기존 동결본을 계속 쓰며, 동결 파일은 수정하지 않았다. 원래 실패 로그·상태 및 수정 전 두 스크립트는 보존했다. 기존9000 STOP도 그대로다.

05:40:28에 일회성 작업 `Codex-VISSIM-onset2250-resume1-20261001`을 시작했다. coordinator PID46580(생성05:40:28.0494705+09), launcher PID23828(05:40:29.223743+09)이다. 완료된 held_actual/rm_only를 재사용하고 **미실행 vsl_release/both 두 조건만** 진행한다. 이후 기존 사후 검증을 한 번 실행한다. 반복 예약·자동 재시도·추가 후보 없음. `resume1_receipt.json`에 소스 SHA·명령·범위를 기록했다. 재개 출력을 `coordinator_resume1.log`, `native_launch_resume1.log`로 분리했다.

목표 ACTIVE / NOT_QUALIFIED. 현재 결과가 모두 검증됐다는 뜻은 아니다. 새 큐의 `job_status.json`과 실제 소유 프로세스를 근거로 이어서 판단하고 중복 실행하지 않는다.
