#!/usr/bin/env python3
"""어댑터 한 번 호출을 **스택 샘플링**으로 프로파일한다.

## 왜 cProfile 이 아닌가

cProfile 은 호출마다 후크를 걸어 호출이 잦은 코드에서 수십 배 느려진다. 실제로 이 어댑터를
cProfile 로 감싸니 10분 넘게 안 끝났다(맨몸 242초). 그러면 어느 구간이 무거운지가 왜곡된다.

대신 데몬 스레드가 `sys._current_frames()` 로 주기적으로 스택을 떠서 집계한다. 오버헤드가
샘플 주기에 비례할 뿐이라 거의 없고, "어디에 시간이 있나" 에는 이게 맞는 도구다.

## 쓰는 법

    python scripts/sample_adapter_profile.py --out prof.json -- \
        --state-json ... --out-action-json ... (어댑터 인자 그대로)

`--` 뒤는 어댑터에 그대로 넘어간다. 어댑터가 `__main__` 으로 도는 것과 같게 실행한다.

## 주의

러너가 쓰는 인터프리터로 돌려야 의미가 있다. 후보 사다리가 conda 를 먼저 잡으므로
보통 `C:\\ProgramData\\anaconda3\\python.exe` 다. 셸의 `python` 은 다른 것일 수 있다.
"""

from __future__ import annotations

import argparse
import collections
import json
import runpy
import sys
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ADAPTER = REPO / "evaluation" / "controllers" / "vissim_stackelberg_adapter.py"

_samples_leaf: collections.Counter = collections.Counter()
_samples_stack: collections.Counter = collections.Counter()
_sample_count = 0
_stop = threading.Event()


def _sampler(interval: float, main_ident: int, depth: int) -> None:
    global _sample_count
    while not _stop.wait(interval):
        frame = sys._current_frames().get(main_ident)
        if frame is None:
            continue
        stack = []
        f = frame
        while f is not None and len(stack) < 200:
            code = f.f_code
            stack.append(f"{Path(code.co_filename).name}:{code.co_name}")
            f = f.f_back
        if not stack:
            continue
        _sample_count += 1
        _samples_leaf[stack[0]] += 1
        # 루트에서 depth 개만 남겨 서명을 만든다 - 호출 경로를 알아보되 폭발하지 않게.
        sig = " < ".join(stack[: max(1, depth)])
        _samples_stack[sig] += 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--interval", type=float, default=0.05)
    ap.add_argument("--depth", type=int, default=6)
    ap.add_argument("--label", default="")
    ap.add_argument("rest", nargs=argparse.REMAINDER)
    args = ap.parse_args()

    adapter_argv = [a for a in args.rest if a != "--"]
    sys.argv = [str(ADAPTER)] + adapter_argv

    t = threading.Thread(
        target=_sampler, args=(args.interval, threading.get_ident(), args.depth), daemon=True
    )
    t0 = time.time()
    t.start()
    status = 0
    try:
        runpy.run_path(str(ADAPTER), run_name="__main__")
    except SystemExit as exc:
        status = int(exc.code or 0)
    finally:
        _stop.set()
        t.join(timeout=2.0)
    elapsed = time.time() - t0

    total = max(_sample_count, 1)
    payload = {
        "schema_version": "adapter-stack-sample-v1",
        "label": args.label,
        "interpreter": sys.executable,
        "python": sys.version.split()[0],
        "elapsed_sec": elapsed,
        "samples": _sample_count,
        "interval_sec": args.interval,
        "exit_status": status,
        "leaf": [
            {"frame": k, "samples": v, "pct": 100.0 * v / total, "sec": elapsed * v / total}
            for k, v in _samples_leaf.most_common(30)
        ],
        "stack": [
            {"frames": k, "samples": v, "pct": 100.0 * v / total, "sec": elapsed * v / total}
            for k, v in _samples_stack.most_common(25)
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8", newline="\n")

    sys.stderr.write(f"\n경과 {elapsed:.1f}s  샘플 {_sample_count}개  ->  {args.out}\n")
    sys.stderr.write("가장 무거운 프레임(leaf):\n")
    for row in payload["leaf"][:12]:
        sys.stderr.write(f"  {row['pct']:5.1f}%  {row['sec']:8.1f}s  {row['frame']}\n")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
