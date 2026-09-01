# -*- coding: utf-8 -*-
"""tuning config 가 가리키는 경로를 **발사 전에** 검사한다.

왜 필요한가 (2026-08-26).
  config 에 윈도우 경로를 백슬래시 한 개로 적으면 JSON 이 그것을 이스케이프로 먹는다.
  "evaluation" + 백슬래시 + "real_world..." 는 캐리지리턴 + "eal_world..." 가 된다.
  load_optional_json 은 없는 파일에 조용히 빈 dict 를 돌려주고, 어댑터는 관측 없이
  결정을 계속한다. map4etau_20260826 이 그렇게 92분을 무제어로 완주했고 진단은
  basename 만 찍어 정상처럼 보였다.

  러너는 어댑터가 죽어도 그 구간만 무제어로 넘기고 완주하므로, 어댑터 안의 가드로는
  시간을 못 아낀다. 발사 전에 세우는 자리가 여기다.

검사 둘.
  1. 제어문자 — 값에 ord < 32 가 있으면 JSON 이스케이프 사고다.
  2. 존재    — 상대경로는 저장소 루트 기준으로 푼다.

extends 사슬을 끝까지 따라간다. 부모가 가리키는 경로도 실런에 그대로 쓰이기 때문이다.
"""
import argparse
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "evaluation/configs"
SUFFIXES = {".json", ".vbs", ".inpx", ".csv", ".sig", ".py"}
# 자유문 키는 경로가 아니다. 여기에 파일명을 적는 관례가 있어 오탐이 난다.
FREE_TEXT = {"notes", "note", "description", "why", "rationale"}


def load_chain(path: Path, seen=None):
    """extends 사슬을 부모까지 따라가며 (출처, dict) 목록을 만든다."""
    seen = seen if seen is not None else set()
    rp = path.resolve()
    if rp in seen or not rp.is_file():
        return []
    seen.add(rp)
    doc = json.loads(rp.read_text(encoding="utf-8"))
    out = [(rp, doc)]
    parent = str(doc.get("extends", "") or "").strip()
    if parent:
        cand = Path(parent)
        if not cand.is_absolute():
            cand = CONFIG_DIR / parent
        out.extend(load_chain(cand, seen))
    return out


def deep_merge(base, over):
    """자식이 이긴다. 실런의 유효값은 병합 결과다."""
    out = dict(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def walk(node, trail=""):
    """문자열 잎을 (키경로, 값) 으로 훑는다."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield from walk(v, trail + "." + str(k) if trail else str(k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk(v, "%s[%d]" % (trail, i))
    elif isinstance(node, str):
        yield trail, node


def looks_like_path(key, value):
    head = key.split(".")[0].split("[")[0]
    if head in FREE_TEXT:
        return False
    if any(ord(c) < 32 for c in value):
        return True            # 제어문자가 있으면 무조건 본다
    if Path(value).suffix.lower() not in SUFFIXES:
        return False
    return "/" in value or "\\" in value or key.endswith(("_json", "_path", "_csv", "_file"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tuning", help="tuning config 경로")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    start = Path(a.tuning)
    if not start.is_absolute():
        start = ROOT / a.tuning
    chain = load_chain(start)
    if not chain:
        print("!! tuning 을 못 읽었다: %s" % start)
        return 1

    # 조상 -> 자손 순으로 병합한다. 조상의 옛 절대경로는 자손이 덮으므로 실런에 안 쓰인다.
    merged = {}
    for src, doc in reversed(chain):
        merged = deep_merge(merged, doc)

    # leaf 가 직접 쓴 키를 따로 안다. 지금 발사하는 config 의 저자가 방금 쓴 값이라
    # 여기서 파일이 없으면 사고다. 조상만 가진 값은 죽은 키인 경우가 많아(어댑터가
    # tuning 의 calibration_json 을 안 읽는다) 경고로만 남긴다.
    leaf_keys = {k for k, _ in walk(chain[0][1])}

    problems = []
    warnings = []
    checked = 0
    for key, value in walk(merged):
        if not looks_like_path(key, value):
            continue
        checked += 1
        ctrl = [i for i, c in enumerate(value) if ord(c) < 32]
        cand = Path(value)
        if not cand.is_absolute():
            cand = ROOT / value
        exists = cand.is_file()
        if ctrl:
            problems.append((chain[0][0].name, key, value, ctrl, exists))
        elif not exists:
            row = (chain[0][0].name, key, value, ctrl, exists)
            (problems if key in leaf_keys else warnings).append(row)
        elif not a.quiet:
            print("  OK   %-28s %s" % (key, value))

    print("검사 %d개 · 사슬 %d단(%s)"
          % (checked, len(chain), " <- ".join(s.stem[-28:] for s, _ in chain)))
    for _n, key, value, _c, _e in warnings:
        print("  WARN %-28s %r  (조상만 가진 값 · 어댑터가 안 읽는다)" % (key, value))
    if not problems:
        print("사전점검 PASS%s" % ("" if not warnings else "  (경고 %d건)" % len(warnings)))
        return 0
    print()
    for name, key, value, ctrl, exists in problems:
        print("!! FAIL  %s" % key)
        print("     출처   %s" % name)
        print("     값     %r" % value)
        if ctrl:
            print("     제어문자 위치 %s  <- JSON 백슬래시 이스케이프다. 슬래시로 써라." % ctrl)
        else:
            print("     파일 없음")
    print()
    print("사전점검 FAIL — 문제 %d건. 런을 시작하지 않는다." % len(problems))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
