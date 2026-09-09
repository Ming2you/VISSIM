# -*- coding: utf-8 -*-
"""ver2fix 사다리를 f4 에서 끊고 용량강하·미터탐침 가지로 넘긴다 (2026-09-09).

왜 끊나. 사다리에 남은 f5(B5)·f6(B0)·f7(SATV2)·f8(SAT3)은 rung 당 ~88 분이라 6 시간이고,
그 조각들은 **옛 망·옛 매핑에서 고른 것**이다(2026-09-09 자가점검). 지금 물어야 할 것은
"지렛대가 원래 있었는가" 이므로 0a·0b 가 먼저다. VISSIM 은 1인스턴스 라이선스라 겹칠 수 없다.

왜 큐 스크립트로 안 되나. `queue_after_ladder` 는 앞 체인이 **스스로 끝나기**를 기다린다.
여기서는 앞 체인이 f5 를 이어서 띄우므로, f4 결과가 로그에 찍히는 순간 끊어야 한다.

절차:
  1. 사다리 로그에 `RESULT f4` 가 뜰 때까지 기다린다 (f4 는 끝까지 돌린다 — 이미 30/37)
  2. 사다리 파이썬을 죽인다. f5 가 막 뜨는 창이면 그 powershell·VISSIM·cscript 도 함께 죽인다
  3. VISSIM 이 완전히 사라지고 안정화될 때까지 기다린다
  4. 용량강하·미터탐침 체인을 띄운다

f5 가 조금 돌다 죽으면 그 런 디렉터리는 미완이다. 사다리를 나중에 재개하면
`run()` 이 완주본이 없다고 보고 지우고 다시 돈다 — 오염되지 않는다.
"""
import io
import os
import subprocess
import sys
import time
from pathlib import Path

R = Path(__file__).resolve().parents[1]
LADDER_LOG = R / "evaluation/runs/chain_n21x15_ver2fix_20260909.log"
LOG = R / "evaluation/runs/cutover_20260909.log"
MARK = "RESULT f4"
NEXT = "scripts/chain_n21_capdrop_meterprobe_20260909.py"
SETTLE_SEC = 90
POLL = 45


def log(msg):
    line = "%s  %s" % (time.strftime("%m-%d %H:%M:%S"), msg)
    print(line, flush=True)
    with io.open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def ps(cmd):
    out = subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (out.stdout or "").strip()


def ps_count(cmd):
    try:
        return int(ps(cmd).splitlines()[-1])
    except Exception:
        return -1


def ladder_pids():
    # 자기 자신은 세지 않는다 — 이 스크립트의 명령줄에도 토큰이 들어 있다.
    me = os.getpid()
    out = ps("Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
             "Where-Object { $_.ProcessId -ne %d -and $_.CommandLine -like '*chain_n21_ver2fix*' "
             "-and $_.CommandLine -notlike '*cutover_after_f4*' } | "
             "Select-Object -ExpandProperty ProcessId" % me)
    return [int(x) for x in out.split() if x.strip().isdigit()]


def vissim_count():
    return ps_count("(Get-Process | Where-Object { $_.ProcessName -match 'vissim|cscript' } "
                    "| Measure-Object).Count")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    log("CUTOVER 대기 — 사다리 로그에 '%s' 가 뜨면 f5 로 넘어가기 전에 끊는다" % MARK)
    while True:
        txt = io.open(LADDER_LOG, encoding="utf-8", errors="replace").read()
        if MARK in txt:
            for line in txt.splitlines():
                if MARK in line:
                    log("f4 완료: %s" % line.strip())
            break
        if not ladder_pids():
            log("사다리 프로세스가 사라졌는데 '%s' 가 없다 — 그래도 넘어간다" % MARK)
            break
        time.sleep(POLL)

    for pid in ladder_pids():
        log("사다리 파이썬 kill pid=%d" % pid)
        ps("Stop-Process -Id %d -Force -ErrorAction SilentlyContinue" % pid)
    time.sleep(5)
    # f5 가 막 떴다면 그 러너와 VISSIM 도 같이 내린다.
    n = ps_count("(Get-CimInstance Win32_Process -Filter \"Name='powershell.exe'\" | "
                 "Where-Object { $_.CommandLine -like '*n21x15f_f5*' } | Measure-Object).Count")
    if n > 0:
        log("f5 러너 %d개 감지 — 함께 내린다" % n)
        ps("Get-CimInstance Win32_Process -Filter \"Name='powershell.exe'\" | "
           "Where-Object { $_.CommandLine -like '*n21x15f_f5*' } | "
           "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }")
    if vissim_count() > 0:
        log("VISSIM/cscript 정리")
        ps("Get-Process | Where-Object { $_.ProcessName -match 'vissim|cscript' } | "
           "Stop-Process -Force -ErrorAction SilentlyContinue")

    settle_from = None
    while True:
        if vissim_count() == 0 and not ladder_pids():
            if settle_from is None:
                settle_from = time.time()
                log("정리 확인 — %d s 안정화 대기" % SETTLE_SEC)
            elif time.time() - settle_from >= SETTLE_SEC:
                break
        else:
            settle_from = None
        time.sleep(15)

    log("START %s" % NEXT)
    rc = subprocess.call([sys.executable, str(R / NEXT)], cwd=str(R))
    log("CUTOVER 완료 rc=%s" % rc)
    return rc


if __name__ == "__main__":
    sys.exit(main())
