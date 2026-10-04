# Gate 상한·이동시간 후보의 실제 SDMPC 연결 확인

2026-09-29 완료. selected64cf 망, seed29, SimRes10/FZP5초, 900초 제어 시작/150초 갱신. 동결본 `cb42f1a3`, `combined_config.json`을 기존 정본 runner로 실행했다. 새 네이티브1회, 재시도0회, 계수 적합0회다.

## 결과

- 실제1200초 종료, task exit0 및 소유 owner/watchdog/cscript/VISSIM 모두 종료. 전체 실행 경과1261초. 이 수치는 로딩·설정·simulation·controller 계산을 포함하므로 simulation 단독 시간이나 최적화 속도 개선율로 쓰지 않는다.
- 기존 무제어 `D:/VISSIM_runs/20260927_sd31_wiring9000/nc`와 네트워크·수요·42개 신호 파일이 동일하다. 제어 전 FZP431,233행/마지막895.1초의 데이터 SHA가 정확히 같다.
- 900·1050초 결정은 실행 가능, N_P/N_UF cap 통과, 생성 명령과 writer 결합 통과. native LDP와 적용 시 VSL readback으로 실행을 검증했다. LSA의 COM 이벤트 누락은 계속 실패이며 사용자가 승인한 대체 기준만 통과했다.
- 현재/과거 관측8개 window의 해시·VSL cohort 보존·이력 연결을 확인했다. 명령 CSV만으로 실행을 판정하지 않았다.

|시점|PFO 최대/실행/수락|SDMPC 최대/실행/수락|수렴|PFO 초|PFO 이후 초|
|---|---|---|---|---:|---:|
|900|2/2/2|2/1/0|아니오|140.51|54.00|
|1050|2/2/2|2/2/2|아니오|148.44|177.02|

900초에는 PFO 명령 이후 추가 실행 가능한 SDMPC step을 찾지 못했고,1050초에는2회를 수락했다. 두 시점 모두 도시 신호를 변경했으며 VSL110과8미터 g10을 유지했다. 아직 본격 혼잡 상태의 제어 이득을 시험한 결과가 아니다. 보고된 지평 예측 감소4.686/4.282veh·h를 합산해 실제 이득으로 사용하지 않는다.

1200초에서도 현재 runner가 마지막 명령을 계산·작성했다. 그 뒤 simulation 구간은 없으므로 **실제 적용 효과가 있는 결정은900/1050초2개**다. 마지막 계산 PFO154.31초+이후164.30초는 실행시간에 포함된다. 이 런을 변경하지 않고 한계로 기록한다.

## 판정 범위와 남은 작업

짧은 폐루프 연결은 통과했다. 일반 실행 검사 파일의 `passed=false`(LSA·자체 종료 증명 미포함)는 덮어쓰지 않았다. 종료는 별도 `runtime_closure.json`, 대체 native 실행 기준은 `native_execution_passed`, 연결 전체는 `summary.json`으로 각각 증명한다.

8램프 합류 오차는 줄었지만 말단 재고 오차가 늘었고, 독립 상태의 전체 Ω 순위 검증이 충분히 끝난 것은 아니다. seed29 6000초의 작은 VSL 완화 이득 방향은 맞췄지만 크기를 과대 예측했다. 큰 손익·선택 순위를 중심으로 기존 자료를 이어 검증하며, 미미한 부호를 맞추기 위한 무제한 계수 탐색은 하지 않는다. 이1200초 통과를9000초 성능 또는 이득 보정 완료로 대신하지 않는다.

결과: `D:/VISSIM_runs/20260929_sd31_gate_short1200`.
근거: `short_native_analysis/{summary,execution,decisions,observation_history,runtime_closure}.json`, `matched_nc_conditions.json`, `completion_review.json`.
기존9000 STOP 유지, 추가 자동 런 없음, push 없음.
