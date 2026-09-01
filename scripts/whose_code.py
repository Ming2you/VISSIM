# -*- coding: utf-8 -*-
"""심볼이 **이 팔에서 실제로 실행되는 코드인지** 판정한다. grep 하지 말고 이걸 써라.

왜 이 도구가 필요한가 (2026-08-31).

같은 실수를 반복했다 — `stackelberg` 팔의 코드를 읽고 `wu-link` 팔의 동작이라고 설명하고,
그 반대도 했다. 원인은 grep 이 팔을 구분하지 못하는 것이다.

    blocked_to_urban        -> distributed_coordinator.py 에만 있다 (stackelberg 팔)
                               우리 wu-link 팔에는 그 식이 **없다** (FIFO 이월, 계수 없음)
    ramp_metering_weight    -> wu_faithful_follower.py (live) · f1_wu_faithful_follower.py (dead)
                               · local_signal_plant.py (모듈 함수, live 에서 호출)

`scripts/resolve_live_controller.py` 는 **파일 단위**라 여기서 부족하다.
`distributed_coordinator.py` 는 어댑터가 몽키패치하려고 import 하므로 "미도달 7개" 에 안 나오는데,
그 안의 `DistributedCoordinator` 클래스는 wu-link 가 인스턴스화하지 않는다. 즉 파일은 살아 있고
클래스는 죽어 있다. 판정 단위가 **클래스**여야 한다.

무엇을 하는가.

    1) config·controller 로 실제 컨트롤러를 만들어 leader/follower 객체를 얻는다
    2) 그 객체들의 MRO 를 펴서 **살아 있는 (모듈, 클래스)** 집합을 만든다
    3) vendor controllers/ 전체에서 심볼을 찾고, ast 로 각 히트의 **소속 클래스**를 구한다
    4) 클래스가 live 집합에 있으면 LIVE, 없으면 DEAD
       클래스 밖(모듈 수준 함수)이면 그 함수 이름이 live 클래스 본문에서 호출되는지 본다

사용:
    python scripts/whose_code.py blocked_to_urban
    python scripts/whose_code.py ramp_metering_weight --controller wu-link
    python scripts/whose_code.py --list-classes          # 이 팔의 live 클래스만 나열
"""
import argparse
import ast
import importlib.util
import re
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
VENDOR = R / "vendor/NumSim-mine/src"


def live_classes(tuning, controller):
    """실제로 컨트롤러를 만들어 leader/follower 의 MRO 를 편다."""
    sys.path.insert(0, str(R))
    sys.path.insert(0, str(R / "vendor/NumSim-mine"))
    sp = importlib.util.spec_from_file_location(
        "qb", R / "evaluation/controllers/vissim_stackelberg_adapter.py")
    qb = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(qb)
    tun = qb.load_optional_json(str(R / tuning))
    cal = qb.load_optional_json(
        str(R / "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json"))
    cal = qb.deep_update(dict(cal), tun.get("calibration_override") or {})
    qb.install_config_switches(tun)
    cfg = qb.build_config(R / "vendor/NumSim-mine", 150.0, 5400.0, controller,
                          cal, tun, local_observation=True, flagship=True)
    qb._plant_rollout_far_into(cfg, tun)
    if controller == "wu-link":
        ctl = qb.build_priced_wu_link_controller(cfg, tun)
    elif controller == "pstack-flagship":
        ctl = qb.build_pstack_flagship_controller(cfg, tun)
    else:
        raise SystemExit("!! --controller 는 wu-link · pstack-flagship 만 지원한다 "
                         "(stackelberg 는 빌더가 달라 별도 배선이 필요하다)")

    objs = [ctl]
    for attr in ("nash_solver", "leader", "follower", "_wu"):
        o = getattr(ctl, attr, None)
        if o is not None and not isinstance(o, (str, int, float, bool)):
            objs.append(o)
    live = set()
    for o in objs:
        for k in type(o).__mro__:
            if k.__module__.startswith("src.") or k.__module__ == "__main__":
                live.add((k.__module__, k.__name__))
    return live, ctl


def enclosing_class(tree, lineno):
    """ast 로 그 줄을 감싸는 최내곽 클래스명. 없으면 None (모듈 수준)."""
    best = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            end = getattr(node, "end_lineno", None) or lineno + 1
            if node.lineno <= lineno <= end:
                if best is None or node.lineno > best.lineno:
                    best = node
    return best.name if best else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("symbol", nargs="?")
    ap.add_argument("--controller", default="wu-link")
    ap.add_argument("--tuning", default="evaluation/configs/canon_fdfit3_20260828.json")
    ap.add_argument("--list-classes", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    live, ctl = live_classes(args.tuning, args.controller)
    live_names = {c for _m, c in live}
    if args.list_classes or not args.symbol:
        print("팔 %s 의 live 클래스 %d개" % (args.controller, len(live)))
        for m, c in sorted(live):
            print("   %-46s %s" % (m, c))
        return 0

    # live 클래스들의 소스를 모아 둔다 (모듈 함수 호출 여부 판정용)
    live_src = []
    for m, c in live:
        mod = sys.modules.get(m)
        f = getattr(mod, "__file__", None)
        if f and Path(f).is_file():
            live_src.append(Path(f).read_text(encoding="utf-8", errors="replace"))
    live_blob = "\n".join(live_src)

    pat = re.compile(re.escape(args.symbol))
    rows = []
    for p in sorted(VENDOR.rglob("*.py")):
        if "__pycache__" in str(p) or "/tests/" in p.as_posix():
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        if not pat.search(text):
            continue
        try:
            tree = ast.parse(text)
        except SyntaxError:
            tree = None
        modname = "src." + p.relative_to(VENDOR).with_suffix("").as_posix().replace("/", ".")
        for i, line in enumerate(text.splitlines(), 1):
            if not pat.search(line):
                continue
            cls = enclosing_class(tree, i) if tree else None
            if cls is None:
                fn = None
                if tree:
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            end = getattr(node, "end_lineno", None) or i + 1
                            if node.lineno <= i <= end:
                                fn = node.name
                                break
                called = bool(fn and re.search(r"\b%s\s*\(" % re.escape(fn), live_blob))
                verdict = ("LIVE(모듈함수 %s — live 에서 호출됨)" % fn) if called else \
                          ("확인필요(모듈함수 %s — live 호출 못 찾음)" % fn if fn else "확인필요(모듈수준)")
            else:
                verdict = "LIVE" if cls in live_names else "DEAD"
            rows.append((p.relative_to(R).as_posix(), i, cls or "-", verdict, line.strip()[:78]))

    if not rows:
        print("'%s' 를 vendor controllers/models 에서 못 찾았다." % args.symbol)
        return 0
    print("심볼 '%s' · 팔 %s" % (args.symbol, args.controller))
    print()
    print("%-52s %6s %-30s %s" % ("파일", "행", "소속 클래스", "판정"))
    for f, i, c, v, _l in rows:
        print("%-52s %6d %-30s %s" % (f.replace("vendor/NumSim-mine/src/", ""), i, c, v))
    nl = sum(1 for r in rows if r[3].startswith("LIVE"))
    nd = sum(1 for r in rows if r[3] == "DEAD")
    print()
    print("LIVE %d · DEAD %d · 확인필요 %d" % (nl, nd, len(rows) - nl - nd))
    if nd and not nl:
        print()
        print(">>> 이 심볼은 **%s 팔에서 실행되지 않는다.** 다른 팔의 코드다." % args.controller)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
