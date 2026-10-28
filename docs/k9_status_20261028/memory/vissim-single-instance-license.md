---
name: vissim-single-instance-license
description: 정정 - VISSIM 동시 실행은 가능하다. 순차는 라이선스가 아니라 러너의 PID 소유권 정책 때문
metadata: 
  node_type: memory
  type: project
  originSessionId: 491ef689-f002-4605-9dc5-e6d363495788
  modified: 2026-09-22T14:03:07.404Z
---

**2026-09-22 정정.** 이전 기록("두 번째 인스턴스는 뷰어 모드, 동시 불가")은 **틀렸다.**

실측: 9000초 런이 도는 중에 2차 COM 인스턴스를 띄워
`Simulation.AttValue("RandSeed")` 를 42 -> 99 로 **쓰기 성공**했고, 1차 런은 멈추지 않고
계속 진행했다(CPU 3191 -> 3270초, fzp 계속 증가). 뷰어 모드가 아니다.

순차 실행의 진짜 이유는 둘 다 **코드 정책**이다:

1. `diagnostics/fast_nc_run.ps1:53`
   `if (@(Get-Process -Name 'VISSIM*').Count) { throw 'Existing VISSIM instance: do not share ownership' }`
   메시지 그대로 **소유권** 문제다. 라이선스 오류가 아니다.

2. PID 귀속이 창 제목으로 자기 프로세스를 찾는다(같은 파일 `:112-114`):
   `$_.StartTime -ge $started -and $_.MainWindowTitle.IndexOf(<network filename>) -ge 0`
   `$new.Count -eq 1` 을 요구하므로 **망 파일명이 같으면 구분을 못 한다.**
   변형마다 `baseline.inpx` 를 쓰면 동시 실행이 깨진다. 파일명을 유일하게 만들면 된다.

`AGENTS.md` 규칙 3 의 "워크스테이션 한 대에서만 순차로 돈다" 는 **작업 협약**이지
라이선스 사실이 아니다. docs/*.md 와 AGENTS.md 에 라이선스 언급은 0건이다.

**동시 상한은 4개다** (2026-09-22 실측). 5번째 인스턴스는
`fast_nc_runner.vbs(218,5) ActiveX 구성 요소는 개체를 작성할 수 없습니다: 'Vissim.Vissim'`
로 COM 생성 자체가 거부된다. 좌석 4개로 보인다. 4개까지는 정상 동작한다.

워크스테이션 여력은 그보다 넉넉하다: 논리 코어 20, 메모리 128GB, 런 1개가 코어 1개 +
0.7~1.3GB. 4개 동시에도 전체 CPU 30%. 즉 병목은 하드웨어가 아니라 좌석이다.
처리량은 4개 동시에 약 2.4배(단독 153 sim-sec/분 -> 4개 합계 약 360).

동시 실행하려면: (a) 변형마다 망 파일명을 유일하게(창 제목 귀속 때문), (b)
`fast_nc_run.ps1` 에 `-AllowConcurrent` 옵트인 스위치(2026-09-22 추가, 기본은 비트 동일).

**주의**: 같은 파일 `:174` 의 완료 판정
`if ($null -eq $owned -and @(Get-Process -Name 'VISSIM*').Count) { error='Native identity
was not established and a VISSIM process remains' }`
도 동시 실행에 안전하지 않다. 남의 런 프로세스 때문에 무조건 걸려서 **진짜 원인을 가린다.**
실패를 진단할 때는 이 메시지 말고 `run/stderr.txt` 를 먼저 봐라.
