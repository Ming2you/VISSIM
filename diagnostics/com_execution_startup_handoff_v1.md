# 첫 실제 진행 마커: 미적용 패치

생산 VBS/PS는 수정하지 않았다. `com_execution_startup_v1.patch`는 기존 원문에 대한 독립 패치이고, `com_execution_startup_edits_v1.json`의 `targets[].edits`는 기존 writer/timing/VSL 수정과 함께 메모리에서 결합할 수 있는 정확한 문자열 교체 목록이다. 각 edit의 `count`를 검증해야 한다.

세 실행 모드의 첫 `RunSingleStep` 반환 뒤, `InitializeComRampMeterControl` 및 첫 관측·결정 전에 `RecordStartupSimulationProgress`를 한 번 호출한다. 이 함수는 실제 `Simulation.SimSec`를 읽어 양수 범위를 검사한 뒤 기존 `Num`으로 `NATIVE_SIM_PROGRESS sim_sec=...`를 출력한다. 요청 시각 상수나 일반 STARTUP 로그를 진행 증거로 사용하지 않는다. 기존 Num/현재 실행 로캘의 숫자 표현을 재사용하며 전역 로캘을 변경하지 않는다.

watchdog의 `Test-SimulationStarted`는 `FileShare.ReadWrite`로 현재 로그의 처음부터 유효 마커 또는 EOF까지 스트리밍한다. 바이트 상한과 Tail 검색은 없다. 첫 마커 이후 로그가 길어져도 누락되지 않으며, caller의 기존 `simulationStarted` latch가 이후 검색을 중단한다. 실제 양수 state CSV 시각은 그대로 fallback으로 사용하되 NaN/Infinity는 거부한다. 기존 300초 시작 타이머, 이후 StallSec 정책, 20초 poll, 정확 PID 소유권·정리 함수는 변경하지 않는다.

`test_com_execution_startup_v1.ps1`는 패치를 메모리에서 결합하고 전체 후보 PS를 AST 파싱한 뒤 **Test-SimulationStarted 함수만** 추출하여 실행한다. 실제 양수 마커, 60KiB 이후 마커, 긴 후속 결정 로그, 일반 활동·요청 시각 거부, 0/음수/NaN/Infinity/잘못된 값 거부, state fallback 등 21개 검사 PASS. PID 확인·정리 함수는 원문과 AST extent가 동일함을 검사했다. COM·모델·VISSIM 실행은 없다.

결과: `com_execution_startup_validation_v1.json`. VBS 전체 구문 검사는 root가 최종 결합 적용 뒤 canonical 파일을 인자 없이 `cscript //nologo` 실행하여 exit2·Usage·stderr 없음으로 확인할 예정이다. 이 검사는 동적 generated config와 COM 동작 검증은 포함하지 않는다.
