# NC1350의 VSL 이력 수치 오류 수정

첫3000초 비교의 무제어 런은1350초에서 실패했다. native 정체/무응답이 아니라 `vsl_exposure_history.constrain_nominal`의0 나누기이며, SDMPC arm은 시작되지 않았다. 기존 결과·로그는 `D:/VISSIM_runs/20260926_sd31_closedloop3000`에 보존했다. 해당 실행 프로세스는 모두 종료됐다.

저장된 상태에서 같은 예외를 재현했다. 셀2의 전량110km/h cohort가32.99999999999862대, 관측된 nominal 하한은33대, 다른 cohort는0대였다. 기존 입력 검사의1e-7 허용오차에는 들어가지만, 재배분 조건의1e-12보다1.378e-12 부족해0으로 나누었다.

수정은 검증을 통과한 하한을 현 총재고 이하로 제한하여 재배분량을 계산하는 한 줄이다. 차량을 만들거나 VSL 이력을110으로 초기화하지 않는다. 계수·수요·비용·후보 범위는 변경하지 않았다. 실제 숫자와 mixed-cohort 보존/초과 하한 거절을 포함한 이력10개 테스트PASS.

같은 실제1350초 상태로 전체 구성된 VSL 이력 초기화를 다시 수행했다. FW_E 시작896→종료863대, 유입285+합류115−진출159−말단274로 보존되고 최대 잔차1.378e-12대였다. 원본 실패 run에 새 checkpoint를 쓰기 직전에 별도 진단 폴더로 증거를 저장하고 종료했으므로 원본은 변경하지 않았다. optimizer와 새 native는 이 재현 검사에서 실행하지 않았다.

증거: `nc1350_reproduction.log`, `nc1350_failure/numerical_failure.json`, `nc1350_roundoff_tests.log`, `nc1350_fixed_history.log`, `nc1350_fixed_history/verified_history.json`. 수정 전 소스는 `executed_sources/vsl_exposure_history_before_nominal_roundoff.py.txt`에 보존했다.

이 수정이 들어간 새 동결본과 별도 v2 결과 폴더에서 같은 두3000초 조건을 재실행한다. 기존 실패본과 동결본을 덮어쓰거나 변경하지 않는다. 이득 검증과9000초 목표는 미완료다.

재실행 native 확인: v2 무제어 런이1350초에서 `CONTROLLER_DECISION ... result=exit=0`으로 정상 통과했다(계산8.750633초). 과거 실패 지점을 실제 VISSIM에서도 넘어갔음을 확인했으며, 전체3000초 종료나 제어 성능 통과를 뜻하지 않는다. 나머지 큐는 변경 없이 계속 진행한다.
