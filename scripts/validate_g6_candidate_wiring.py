# G6 후보집합 배선을 실행 전에 검증한다.
#
# 후보 id 는 세 곳에 흩어져 있고 하나라도 어긋나면 배치가 첫 케이스에서 죽는다.
#   (1) harness/g6/g6_core.py   ACTIVE_CANDIDATE_SET   — 하네스가 채점에 쓰는 정의
#   (2) scripts/run_g6_branch_grid.ps1  $controllerByCandidate — 배치가 쓰는 id->variant 표
#   (3) evaluation/controllers/vissim_stackelberg_adapter.py  --controller 허용 목록
#
# 실제로 2026-08-03 에 (1)(3)만 고치고 (2)를 빠뜨려 "Unknown candidate: c01_vsl100" 으로
# 5 시간짜리 배치가 첫 케이스 직후 죽었다. 그 재발을 막는 것이 이 스크립트다.
#
# 사용법: python validate_g6_candidate_wiring.py     (종료코드 0=정상, 1=불일치)

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness" / "g6"))


def ps1_mapping(path: Path) -> dict[str, str]:
    txt = path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"\$controllerByCandidate\s*=\s*@\{(.*?)\n\}", txt, re.S)
    if not m:
        raise SystemExit("run_g6_branch_grid.ps1 에서 $controllerByCandidate 를 찾지 못했다")
    out = {}
    for line in m.group(1).splitlines():
        mm = re.match(r'\s*"([^"]+)"\s*=\s*"([^"]+)"', line)
        if mm:
            out[mm.group(1)] = mm.group(2)
    return out


def ps1_default_candidates(path: Path) -> list[str]:
    txt = path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"\[string\[\]\]\$Candidates\s*=\s*@\((.*?)\n\s*\),", txt, re.S)
    if not m:
        return []
    return re.findall(r'"([^"]+)"', m.group(1))


def adapter_allowed(path: Path) -> set[str]:
    txt = path.read_text(encoding="utf-8", errors="replace")
    return set(re.findall(r'"(diagnostic-[a-z0-9-]+)"', txt))


def main() -> int:
    import g6_core as core

    grid = ROOT / "scripts" / "run_g6_branch_grid.ps1"
    adapter = ROOT / "evaluation" / "controllers" / "vissim_stackelberg_adapter.py"

    harness = {c.candidate_id: c.variant for c in core.ACTIVE_CANDIDATE_SET}
    mapping = ps1_mapping(grid)
    defaults = ps1_default_candidates(grid)
    allowed = adapter_allowed(adapter)

    print(f"하네스 ACTIVE_CANDIDATE_SET : {len(harness)} 후보")
    print(f"배치 표 $controllerByCandidate: {len(mapping)} 항목")
    print(f"배치 기본 -Candidates        : {len(defaults)} 후보")
    print(f"어댑터 diagnostic 변형        : {len(allowed)} 개\n")

    bad = 0

    missing = [c for c in harness if c not in mapping]
    if missing:
        bad += 1
        print(f"[FAIL] 배치 표에 없는 후보 {len(missing)}: {missing}")

    mismatch = [(c, harness[c], mapping[c]) for c in harness if c in mapping and mapping[c] != harness[c]]
    if mismatch:
        bad += 1
        print(f"[FAIL] variant 불일치 {len(mismatch)}:")
        for c, h, g in mismatch:
            print(f"        {c}: 하네스={h}  배치={g}")

    notallowed = sorted({v for v in harness.values() if v not in allowed})
    if notallowed:
        bad += 1
        print(f"[FAIL] 어댑터가 모르는 variant {len(notallowed)}: {notallowed}")

    excl = [c for c, v in harness.items() if v in getattr(core, "EXCLUDED_VARIANTS", {})]
    if excl:
        bad += 1
        print(f"[FAIL] EXCLUDED_VARIANTS 인데 후보에 들어있다: {excl}")

    dflt_missing = [c for c in defaults if c not in mapping]
    if dflt_missing:
        bad += 1
        print(f"[FAIL] 배치 기본 목록에 있는데 표에 없는 후보: {dflt_missing}")

    dflt_vs_harness = sorted(set(defaults) ^ set(harness))
    if dflt_vs_harness:
        print(f"[WARN] 배치 기본 목록과 하네스 후보집합이 다르다: {dflt_vs_harness}")
        print("        (의도한 부분집합 실행이면 무시해도 된다)")

    if bad == 0:
        print("[OK] 세 곳의 배선이 일치한다.")
        for c in sorted(harness):
            print(f"   {c:<22} -> {harness[c]}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
