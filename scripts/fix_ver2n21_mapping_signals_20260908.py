# -*- coding: utf-8 -*-
"""ver2n21 제어 매핑의 `signals` 를 통제 17개로 채운다 (2026-09-08).

무엇이 틀렸나. `generate_real_world_control_mapping.py:908` 은
`"signals": [dict(row) for row in REAL_WORLD_INTERFACE_SIGNALS]` 로 **인터페이스 컨트롤러만**
싣는다 — 이 망에서는 SC1001 한 개(`id: "D"`)다. 그런데 런타임은 그 절을 **전체 신호 목록**으로
읽는다: `vissim_stackelberg_adapter._signal_rows_for_mapping` 이 `mapping["signals"]` 를 돌며
`{id}_{phase}` 로 `control.green_times` 를 조회한다.

id 가 "D" 라 조회가 전부 빗나가면 p1/p2 는 진단 기본값(40 s), p3/p4 는 0 이 되고
`signal_group_action_rows` 가 현시 집합 불일치로 죽는다:

    SignalGroupPlanError: sc 1001: action commands green on phases ('p1','p2')
                          but the actuation plan has signal groups on ('p1','p2','p3','p4')

실측(2026-09-08 런 n21x15_n0 attempt_01): 37결정 중 **wu-link 31결정 전부** 이 예외로 죽어
`DECISION_EXIT_NONZERO` → `RUN_INTEGRITY_FAILURE decisions_failed=31`. action JSON 은 예외
**전에** 써지므로 `status=ok` 로 남아 정상처럼 보인다 — 그런데 플랜트에는 아무것도 안 갔다.
그 런은 사실상 무제어다.

왜 이제야 드러났나. ver2 계열 매핑(8셀·21셀 둘 다 같은 결함)은 FD 스윕용으로 만들어져
**무제어 런에만 쓰였다**. 제어런에 처음 쓴 것이 2026-09-08 사다리다.

무엇으로 고치나. 통제 17개의 정본은 CLAUDE.md 가 지정한
`control_mapping_distributed_core17legs4b_20260819.json` 이다. 그 `signals` 를 가져오고
SC1001 항목에는 ver2 가 갖고 있던 인터페이스 주석(coverage·phase_map·interface_head_count·note)을
합친다. 결과 sc_no 집합이 러너 VBS 의 `RW_SIGNAL_SCS` 와 같은지 검사한다 — 다르면 쓰지 않는다.

**생성기는 여기서 고치지 않는다.** `REAL_WORLD_INTERFACE_SIGNALS` 는 `RW_SIGNAL_SCS` 생성에도
쓰여(같은 파일 817행) 의미를 바꾸면 VBS 상수까지 흔들린다. 재생성 시 이 스크립트를 다시 돌려라.

사용: python fix_ver2n21_mapping_signals_20260908.py [mapping_json]
"""
import io
import json
import re
import sys
from collections import OrderedDict as OD
from pathlib import Path

R = Path(__file__).resolve().parents[1]
CANON = R / "evaluation/real_world_modi_control_distributed_20260728/control_mapping_distributed_core17legs4b_20260819.json"
DEFAULT = R / "evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json"
VBS = R / "evaluation/real_world_modi_control_ver2n21_20260907/real_world_modi_control_config_ver2n21.vbs"

ANNOTATION_KEYS = ("coverage", "phase_map", "interface_head_count", "note")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    m = json.load(io.open(path, encoding="utf-8"), object_pairs_hook=OD)
    canon = json.load(io.open(CANON, encoding="utf-8"))

    old = m.get("signals") or []
    if len(old) >= 17:
        print("이미 채워져 있다 (%d개): %s" % (len(old), path.name))
        return

    # 기존 인터페이스 주석을 sc_no 로 보관해 두었다가 합친다.
    ann = {int(r["sc_no"]): {k: r[k] for k in ANNOTATION_KEYS if k in r}
           for r in old if isinstance(r, dict) and r.get("sc_no") is not None}

    rows = []
    for r in canon["signals"]:
        row = OD()
        row["id"] = str(r["id"])
        row["sc_no"] = int(r["sc_no"])
        row["major_maps_to"] = str(r.get("major_maps_to", "p2"))
        for k in ("name", "role", "source"):
            if k in r:
                row[k] = r[k]
        row.update(ann.get(int(r["sc_no"]), {}))
        rows.append(row)

    # 러너 VBS 의 통제 SC 목록과 대조. 어긋나면 쓰지 않는다.
    txt = io.open(VBS, encoding="utf-8", errors="replace").read()
    mm = re.search(r'RW_SIGNAL_SCS\s*=\s*"([^"]*)"', txt)
    if not mm:
        raise SystemExit("VBS 에서 RW_SIGNAL_SCS 를 못 찾았다: %s" % VBS)
    want = sorted(int(x) for x in mm.group(1).split(",") if x.strip())
    got = sorted(r["sc_no"] for r in rows)
    if want != got:
        raise SystemExit("sc_no 불일치\n  VBS  %s\n  매핑 %s" % (want, got))

    m["signals"] = rows
    note = m.setdefault("known_approximations", [])
    if isinstance(note, list):
        note.append(
            "signals: 생성기(REAL_WORLD_INTERFACE_SIGNALS)는 인터페이스 컨트롤러만 싣는데 "
            "런타임(_signal_rows_for_mapping)은 전체 신호 목록으로 읽는다. 통제 17개를 정본 매핑 "
            "control_mapping_distributed_core17legs4b_20260819.json 에서 채웠다 "
            "(2026-09-08, scripts/fix_ver2n21_mapping_signals_20260908.py). 재생성하면 다시 돌려라.")
    io.open(path, "w", encoding="utf-8").write(json.dumps(m, ensure_ascii=False, indent=1))
    print("고쳤다: %s" % path.name)
    print("  signals %d -> %d" % (len(old), len(rows)))
    print("  sc_no  %s" % got)
    print("  SC1001 major_maps_to=%s (인터페이스 주석 %d키 보존)"
          % (next(r["major_maps_to"] for r in rows if r["sc_no"] == 1001),
             len(ann.get(1001, {}))))


if __name__ == "__main__":
    main()
