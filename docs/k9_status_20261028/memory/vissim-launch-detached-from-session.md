---
name: vissim-launch-detached-from-session
description: Claude 세션이 끝나면 run_in_background 로 띄운 VISSIM 런이 같이 죽는다 — 긴 런은 WMI Win32_Process.Create 로 분리 발사 (2026-09-24)
metadata:
  node_type: memory
  type: feedback
  originSessionId: 491ef689-f002-4605-9dc5-e6d363495788
  modified: 2026-09-24T02:43:34.499Z
---

Bash/PowerShell `run_in_background` 로 띄운 발사기(→ Start-Job → cscript → VISSIM)는 Claude Code 프로세스에 묶여 있다.
- 2026-09-24 11:10, 세션이 끝나자 stage-1 재실행 3런이 7200–7500 s 에서 한꺼번에 죽었다.
- 산출물은 `run_killed_1110` 이다.
- 런 로그에는 `completed=false` 만 남는다.

**Why:** 사용 한도 리셋과 세션 교체가 잦다. 9000 s SDMPC 런(10시간+)은 거의 확실히 세션 경계를 넘는다.

**How to apply:**
- 1시간 넘는 VISSIM 런은 세션과 분리해서 띄운다.
  - 방법: `Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine='cmd.exe /c powershell ... > log 2>&1'; CurrentDirectory=...}`
  - 부모가 WmiPrvSE 가 되므로 Claude 의 job 객체 밖에서 돈다.
- 감시는 Monitor 로 로그와 run.json 을 폴링한다.
- 여러 런이 같은 순간 죽으면, 먼저 이것과 [[vissim-legacy-watchdog-global-kill]] 을 의심한다.
