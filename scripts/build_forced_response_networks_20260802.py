# 강제응답 그리드용 파생 .inpx 생성기 — 역할별 배수를 전 시간구간에 적용하고 평가창 수요를 평탄화한다.
#
# 왜 필요한가.
#   [2026-08-02 정정] 이 헤더는 원래 "Volume(2) 이상은 COM 쓰기가 거부된다"고 적었으나
#   그것은 오진이었다. COM 직접 프로브 결과 Volume(2)~Volume(6) 및
#   VehicleInput.TimeIntVehVols 항목의 Volume 은 모두 쓰기·리드백이 정상 동작한다
#   (scripts/probe_vehicle_input_time_interval_api.vbs).
#   진짜 원인은 런너가 Volume(1) 하나만 쓴 것이었고 지금은 고쳤다
#   (run_real_world_stackelberg_controller.vbs 의 ApplyDemandMultipliers).
#   따라서 -DemandScale / -DemandProfile 은 이제 전 시간구간에 적용된다.
#
#   이 스크립트가 여전히 필요한 이유는 수요 배수가 아니라 평탄화다.
#   런너는 .inpx 의 시간 프로파일 모양을 그대로 두고 배수만 곱하므로
#   분석창 동안 수요가 계속 변한다. tau/nu 식별에는 평탄한 수요가 필요하고
#   그 평탄화는 .inpx 를 고쳐야만 얻을 수 있다.
#
# 무엇을 하는가.
#   1) 역할(freeway_* / urban_*)별 배수를 모든 시간구간 volume 에 곱한다.
#   2) plateau_start_sec 이후 구간은 그 입력 자신의 peak(배수 적용 후) 로 고정한다.
#      분석창 동안 수요가 일정해야 tau/nu 식별에서 수요 추세가 교란으로 섞이지 않는다.

from __future__ import annotations

import argparse
import csv
import json
import shutil
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path


def time_int_start_sec(value: str | None) -> int:
    parts = str(value or "").split()
    if not parts:
        return 0
    try:
        return int(round(float(parts[-1]) / 1000.0))
    except ValueError:
        return 0


def load_roles(path: Path) -> dict[str, str]:
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return {str(row["no"]): (row.get("role") or "").strip().lower() for row in csv.DictReader(f)}


def format_volume(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".")


def summarize(root: ET.Element, roles: dict[str, str]) -> list[dict[str, float]]:
    totals: dict[int, dict[str, float]] = defaultdict(lambda: {"urban": 0.0, "freeway": 0.0})
    for vi in root.iter("vehicleInput"):
        role = roles.get(str(vi.get("no")), "")
        key = "freeway" if role.startswith("freeway") else "urban"
        for row in vi.findall("./timeIntVehVols/timeIntervalVehVolume"):
            totals[time_int_start_sec(row.get("timeInt"))][key] += float(row.get("volume", "0") or 0.0)
    out = []
    for sec in sorted(totals):
        out.append(
            {
                "sec": sec,
                "urban_vph": round(totals[sec]["urban"], 3),
                "freeway_vph": round(totals[sec]["freeway"], 3),
            }
        )
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--inpx", required=True)
    p.add_argument("--layx", default="")
    p.add_argument("--out-inpx", required=True)
    p.add_argument("--out-layx", default="")
    p.add_argument("--roles", required=True)
    p.add_argument("--plateau-start-sec", type=int, default=900)
    p.add_argument("--freeway-mult", type=float, default=1.0)
    p.add_argument("--urban-mult", type=float, default=1.0)
    p.add_argument("--report", default="")
    args = p.parse_args()

    tree = ET.parse(args.inpx)
    root = tree.getroot()
    roles = load_roles(Path(args.roles))
    before = summarize(root, roles)

    touched = 0
    for vi in root.iter("vehicleInput"):
        container = vi.find("./timeIntVehVols")
        if container is None:
            continue
        rows = container.findall("./timeIntervalVehVolume")
        if not rows:
            continue
        role = roles.get(str(vi.get("no")), "")
        mult = args.freeway_mult if role.startswith("freeway") else args.urban_mult
        scaled = {
            id(r): float(r.get("volume", "0") or 0.0) * mult for r in rows
        }
        peak = max(scaled.values()) if scaled else 0.0
        for r in rows:
            sec = time_int_start_sec(r.get("timeInt"))
            new = peak if sec >= args.plateau_start_sec else scaled[id(r)]
            r.set("volume", format_volume(new))
        touched += 1

    after = summarize(root, roles)
    out_inpx = Path(args.out_inpx)
    out_inpx.parent.mkdir(parents=True, exist_ok=True)
    tree.write(out_inpx, encoding="utf-8", xml_declaration=True)

    if args.layx and args.out_layx and Path(args.layx).exists():
        shutil.copy2(args.layx, args.out_layx)

    report = {
        "source_inpx": str(Path(args.inpx).resolve()),
        "out_inpx": str(out_inpx.resolve()),
        "plateau_start_sec": args.plateau_start_sec,
        "freeway_mult": args.freeway_mult,
        "urban_mult": args.urban_mult,
        "vehicle_inputs_touched": touched,
        "demand_before": before,
        "demand_after": after,
    }
    print(json.dumps(report, indent=1, ensure_ascii=False))
    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
