# -*- coding: utf-8 -*-
"""정본 통합 마무리. 어댑터 1벌 · config 3개만 남기고 나머지는 격리한다.

왜. 2026-08-27 기준 어댑터 19벌(155,827행)·config 139개(정본 사슬 24단)였다. 최상위
함수 217개 중 195개가 중복 정의고 17개는 구현이 갈렸다(`main` 10종). TTT 사다리 11개
팔이 어댑터 9개·sha 10종으로 돌아 팔 간 차이가 설정인지 코드인지 분리되지 않았다.
그리고 새 시나리오에서 플래그를 제대로 안 읽어 구버전 경로가 조용히 살아나는 사고가
반복됐다 — `urban.capacity.perimeter` 는 코드·테스트·A/B 팔까지 만들고 기본 off 인 채
잊혔고, `rollout_far` 는 24단 체인 어디에도 없어 far 가 실런에서 한 번도 계산되지
않았다(결정 37개에 far 진단 키 0회).

원칙(사용자 지시). 승격된 수정의 구버전은 격리 폴더로 옮겨 참조만 하고, 정본에서는
흔적도 남기지 않는다. 플래그로 옛 경로를 남겨두지 않는다.

실행 전 조건. VISSIM 런이 돌고 있으면 안 된다 — 러너가 결정마다 어댑터·config 를
경로로 다시 읽는다. `--force` 없이는 실행 중인 런을 감지하면 중단한다.

되돌리기. 옮기기만 하고 지우지 않는다. 각 격리 폴더의 MANIFEST 에 원래 이름과 sha 가
있으므로 되돌릴 수 있다.
"""
import argparse
import glob
import hashlib
import io
import json
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path

R = Path(__file__).resolve().parent.parent
CTRL = R / "evaluation/controllers"
CFG = R / "evaluation/configs"
STAMP = "20260827"
CTRL_OLD = CTRL / ("_superseded_%s" % STAMP)
CFG_OLD = CFG / ("_superseded_%s" % STAMP)

CANONICAL_ADAPTER = "vissim_stackelberg_adapter.py"
PROMOTE_FROM = "vissim_stackelberg_adapter_qbind_20260826.py"
def canon_configs() -> set[str]:
    """정본 config 는 `canon_` 접두로 **자동 인식**한다.

    2026-08-27 감사 지적. 종전에는 세 파일 이름을 하드코딩해서, 새 팔(canon_fdfit 등)을
    만든 뒤 이 스크립트를 다시 --apply 하면 그 팔들이 통째로 격리 폴더로 사라지고
    러너의 -Tuning 이 다시 dangling 이 됐다. 즉 멱등하지 않았다.
    """
    return {p.name for p in CFG.glob("canon_*.json")}


def sha8(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:8]


def running_now() -> list[str]:
    """진행 중으로 보이는 런. state 파일이 37개 미만이고 최근에 갱신된 것."""
    import time
    live = []
    now = time.time()
    for d in glob.glob(str(R / "evaluation/runs/*/decisions_*")):
        run = Path(d).parent.name
        # 중단·실패 표시가 붙은 런은 살아 있지 않다. 표시가 mtime 보다 신뢰도가 높다.
        if any(t in run for t in ("ABORTED", "FAILED", "INVALID", "_superseded")):
            continue
        st = glob.glob(d + "/state_*.json")
        if not st or len(st) >= 37:
            continue
        newest = max(Path(f).stat().st_mtime for f in st)
        if now - newest < 900:
            live.append(Path(d).parent.name)
    return sorted(set(live))


def provenance_index() -> tuple[dict, dict]:
    ad, tu = defaultdict(set), defaultdict(set)
    for p in glob.glob(str(R / "evaluation/runs/*/run_provenance_*.json")):
        try:
            d = json.load(io.open(p, encoding="utf-8"))
        except Exception:
            continue
        run = Path(p).parent.name
        files = d.get("files") or {}
        a = Path((files.get("adapter") or {}).get("path", "")).name
        t = Path((files.get("tuning") or {}).get("path", "")).name
        if a:
            ad[a].add(run)
        if t:
            tu[t].add(run)
    return ad, tu


def promote_adapter(dry: bool) -> list[str]:
    """qbind 를 정본 이름으로 승격하고 현행 정본을 격리한다."""
    log = []
    src = CTRL / PROMOTE_FROM
    dst = CTRL / CANONICAL_ADAPTER
    if not src.is_file():
        log.append("건너뜀: %s 없음 (이미 승격됐을 수 있다)" % PROMOTE_FROM)
        return log
    CTRL_OLD.mkdir(exist_ok=True)
    if dst.is_file():
        log.append("격리 %s (%s) -> %s/" % (dst.name, sha8(dst), CTRL_OLD.name))
        if not dry:
            shutil.move(str(dst), str(CTRL_OLD / ("legacy_base_%s.py" % STAMP)))
    log.append("승격 %s (%s) -> %s" % (src.name, sha8(src), CANONICAL_ADAPTER))
    if not dry:
        shutil.move(str(src), str(dst))
    return log


def isolate_configs(dry: bool) -> list[str]:
    """canon_* 3개만 남기고 나머지 config 를 격리한다."""
    log = []
    _, tu = provenance_index()
    keep = canon_configs()
    if not keep:
        log_msg = "!! canon_*.json 이 하나도 없다. 격리를 중단한다(전부 지워질 뻔했다)."
        return [log_msg]
    CFG_OLD.mkdir(exist_ok=True)
    man = []
    for p in sorted(CFG.glob("*.json")):
        if p.name in keep:
            continue
        man.append({"file": p.name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                    "runs": sorted(tu.get(p.name, []))})
        if not dry:
            shutil.move(str(p), str(CFG_OLD / p.name))
    log.append("config 격리 %d개 -> %s/" % (len(man), CFG_OLD.name))
    if not dry:
        mpath = CFG_OLD / ("MANIFEST_%s.json" % STAMP)
        if mpath.exists():
            # 덮어쓰지 않고 합친다. 2차 실행이 1차 기록(135건)을 1줄로 날리던 문제.
            try:
                prev = json.loads(mpath.read_text(encoding="utf-8")).get("entries") or []
            except Exception:
                prev = []
            known = {e.get("file") for e in prev}
            man = prev + [e for e in man if e.get("file") not in known]
        io.open(str(mpath), "w", encoding="utf-8").write(
            json.dumps({"moved_at": "2026-08-27",
                        "reason": "정본 3개(canon_tau/bstoA/plantfix)를 자립 파일로 평탄화했으므로 extends 사슬 전체가 불필요해졌다.",
                        "note": "run_provenance 의 tuning sha256 대조용 증거다. 지우지 마라.",
                        "entries": man}, ensure_ascii=False, indent=1))
    return log


def rewire_references(dry: bool) -> list[str]:
    """스크립트의 어댑터·config 참조를 정본으로 다시 잇는다."""
    log = []
    moved_adapters = {p.name for p in CTRL_OLD.glob("vissim_stackelberg_adapter*.py")}
    moved_adapters.add(PROMOTE_FROM)
    canon_by_src = {"real_world_modi_pstack_distributed_core17legs4b_tau_20260825.json": "canon_tau_%s.json" % STAMP,
                    "real_world_modi_pstack_distributed_core17legs4b_bstoA_20260826.json": "canon_bstoA_%s.json" % STAMP,
                    "real_world_modi_pstack_distributed_core17legs4b_plantfix_20260826.json": "canon_plantfix_%s.json" % STAMP}
    targets = [Path(p) for p in glob.glob(str(R / "scripts/*.ps1")) + glob.glob(str(R / "scripts/*.py"))]
    for p in targets:
        if p.name == Path(__file__).name:
            continue
        try:
            txt = p.read_text(encoding="utf-8-sig")
        except Exception:
            continue
        orig = txt
        for name in sorted(moved_adapters, key=len, reverse=True):
            txt = txt.replace(name, CANONICAL_ADAPTER)
        for src, dstn in canon_by_src.items():
            txt = txt.replace(src, dstn)
        if txt != orig:
            n = sum(1 for a, b in zip(orig.splitlines(), txt.splitlines()) if a != b)
            log.append("  재배선 %-46s %d행" % (p.name, n))
            if not dry:
                p.write_text(txt, encoding="utf-8-sig")
    log.insert(0, "스크립트 재배선 %d개 파일" % len(log))
    return log


def verify() -> list[str]:
    log = []
    left = sorted(p.name for p in CTRL.glob("vissim_stackelberg_adapter*.py"))
    log.append("정본 어댑터: %s" % left)
    log.append("  기대: ['%s'] 하나" % CANONICAL_ADAPTER)
    cfgs = sorted(p.name for p in CFG.glob("*.json"))
    log.append("정본 config %d개: %s" % (len(cfgs), cfgs))
    stale = []
    for p in list(R.glob("scripts/*.ps1")) + list(R.glob("scripts/*.py")):
        try:
            t = p.read_text(encoding="utf-8-sig")
        except Exception:
            continue
        for m in re.findall(r"vissim_stackelberg_adapter[A-Za-z0-9_]*\.py", t):
            if m != CANONICAL_ADAPTER:
                stale.append("%s -> %s" % (p.name, m))
    log.append("남은 구버전 어댑터 참조 %d건%s" % (len(stale), (": " + ", ".join(stale[:6])) if stale else ""))
    return log


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="실제로 옮긴다. 없으면 예행연습.")
    ap.add_argument("--force", action="store_true", help="진행 중인 런이 있어도 강행.")
    args = ap.parse_args()
    dry = not args.apply
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    live = running_now()
    if live and not args.force:
        print("!! 진행 중인 런: %s" % ", ".join(live))
        print("   러너가 결정마다 어댑터·config 를 경로로 다시 읽는다. 끝난 뒤 실행하라.")
        return 1

    print("=== %s ===" % ("예행연습 (--apply 로 실제 실행)" if dry else "실행"))
    for step, fn in (("어댑터 승격", promote_adapter), ("config 격리", isolate_configs),
                     ("참조 재배선", rewire_references)):
        print("\n[%s]" % step)
        for line in fn(dry):
            print("  " + line)
    if not dry:
        print("\n[검증]")
        for line in verify():
            print("  " + line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
