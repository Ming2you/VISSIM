# -*- coding: utf-8 -*-
"""앞 체인이 끝나면 다음 체인을 이어 돌린다 (2026-09-09).

왜 큐가 필요한가. VISSIM 은 **1인스턴스 라이선스**라 두 번째 인스턴스는 뷰어 모드로 떨어져
쓰기·시뮬이 실패한다. 그래서 체인은 절대 겹치면 안 되고, 앞 체인이 완전히 끝난 뒤에
띄워야 한다.

무엇을 기다리나 (셋 다 만족해야 시작):
  1. 앞 체인 파이썬 프로세스가 사라짐
  2. VISSIM200 / cscript 가 하나도 없음
  3. 안정화 유예 (기본 60 s) — 워치독이 재시도를 띄우는 창을 넘긴다

사용: python queue_after_ladder_20260909.py <기다릴_스크립트_토큰> <다음_스크립트> [다음 인자...]
  예) python queue_after_ladder_20260909.py chain_n21_ladder_20260908 scripts/chain_n21_nometer_20260909.py
"""
import io
import os
import subprocess
import sys
import time
from pathlib import Path

R = Path(__file__).resolve().parents[1]
LOG = R / "evaluation/runs/queue_20260909.log"
POLL_SEC = 60
SETTLE_SEC = int(os.environ.get("QUEUE_SETTLE_SEC", "60"))
MAX_WAIT_SEC = int(os.environ.get("QUEUE_MAX_WAIT_SEC", str(24 * 3600)))


def log(msg):
    line = "%s  %s" % (time.strftime("%m-%d %H:%M:%S"), msg)
    print(line, flush=True)
    with io.open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def ps_count(cmd):
    out = subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        return int((out.stdout or "0").strip().splitlines()[-1])
    except Exception:
        return -1


def waiting_for(token):
    return ps_count(
        "(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
        "Where-Object { $_.CommandLine -like '*%s*' } | Measure-Object).Count" % token)


def vissim_busy():
    return ps_count("(Get-Process | Where-Object { $_.ProcessName -match 'vissim|cscript' } | Measure-Object).Count")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    token, nxt = sys.argv[1], sys.argv[2]
    args = sys.argv[3:]
    log("QUEUE 대기 시작 — '%s' 가 끝나면 %s 실행" % (token, nxt))
    t0 = time.time()
    settle_from = None
    while True:
        if time.time() - t0 > MAX_WAIT_SEC:
            log("QUEUE 타임아웃 — 시작하지 않는다")
            return 2
        n_prev = waiting_for(token)
        n_vis = vissim_busy()
        if n_prev == 0 and n_vis == 0:
            if settle_from is None:
                settle_from = time.time()
                log("앞 체인 종료 확인 — %d s 안정화 대기" % SETTLE_SEC)
            elif time.time() - settle_from >= SETTLE_SEC:
                break
        else:
            if settle_from is not None:
                log("재개 감지(앞 체인 %d · VISSIM %d) — 대기 계속" % (n_prev, n_vis))
            settle_from = None
        time.sleep(POLL_SEC)

    log("START %s %s" % (nxt, " ".join(args)))
    rc = subprocess.call([sys.executable, str(R / nxt)] + args, cwd=str(R))
    log("QUEUE 완료 rc=%s" % rc)
    return rc


if __name__ == "__main__":
    sys.exit(main())
