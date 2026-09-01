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
    if not path.exists():
        return {}
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return {str(row["no"]): row.get("role", "") for row in csv.DictReader(f)}


def summarize(root: ET.Element, roles: dict[str, str]) -> list[dict[str, float | int]]:
    totals: dict[int, dict[str, float]] = defaultdict(lambda: {"total": 0.0, "urban": 0.0, "freeway": 0.0})
    for vi in root.iter("vehicleInput"):
        role = roles.get(str(vi.get("no")), "")
        key = "freeway" if role.startswith("freeway") else "urban"
        for row in vi.findall("./timeIntVehVols/timeIntervalVehVolume"):
            sec = time_int_start_sec(row.get("timeInt"))
            volume = float(row.get("volume", "0") or 0.0)
            totals[sec]["total"] += volume
            totals[sec][key] += volume
    peak = max((v["total"] for v in totals.values()), default=0.0)
    rows: list[dict[str, float | int]] = []
    for sec in sorted(totals):
        total = totals[sec]["total"]
        rows.append(
            {
                "sec": sec,
                "total_vph": round(total, 3),
                "urban_vph": round(totals[sec]["urban"], 3),
                "freeway_vph": round(totals[sec]["freeway"], 3),
                "total_vs_peak_pct": round(total / peak * 100.0, 3) if peak else 0.0,
            }
        )
    return rows


def format_volume(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".")


def set_time_int_start_sec(attrs: dict[str, str], sec: int) -> None:
    parts = str(attrs.get("timeInt", "1 0")).split()
    prefix = parts[0] if parts else "1"
    attrs["timeInt"] = f"{prefix} {int(sec) * 1000}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inpx", default="network/real_world_gaepo_modi/modi_eval_rw_control.inpx")
    parser.add_argument("--layx", default="network/real_world_gaepo_modi/modi_eval_rw_control.layx")
    parser.add_argument(
        "--out-inpx",
        default="network/real_world_gaepo_modi/modi_eval_rw_control_peakplateau_20260729.inpx",
    )
    parser.add_argument(
        "--out-layx",
        default="network/real_world_gaepo_modi/modi_eval_rw_control_peakplateau_20260729.layx",
    )
    parser.add_argument("--roles", default="evaluation/real_world_modi_inventory/vehicle_input_roles.csv")
    parser.add_argument("--plateau-start-sec", type=int, default=1800)
    parser.add_argument(
        "--recovery-shift-sec",
        type=int,
        default=0,
        help=(
            "If positive, delay all demand intervals after plateau-start-sec by this many seconds "
            "instead of holding peak demand forever. For example, 1800 turns 1800->2700->3600->4500 "
            "into 1800 peak hold, then recovery at 4500->5400->6300."
        ),
    )
    parser.add_argument("--scale", type=float, default=1.0)
    parser.add_argument(
        "--summary-csv",
        default="outputs/real_world_peakplateau_demand_20260729.csv",
    )
    parser.add_argument(
        "--report",
        default="outputs/real_world_peakplateau_demand_20260729.json",
    )
    args = parser.parse_args()

    inpx = Path(args.inpx)
    out_inpx = Path(args.out_inpx)
    tree = ET.parse(inpx)
    root = tree.getroot()
    roles = load_roles(Path(args.roles))

    before = summarize(root, roles)
    changes = []

    for vi in root.iter("vehicleInput"):
        volume_container = vi.find("./timeIntVehVols")
        if volume_container is None:
            continue
        volume_rows = volume_container.findall("./timeIntervalVehVolume")
        if not volume_rows:
            continue
        if args.recovery_shift_sec > 0:
            original_rows = sorted(
                [(time_int_start_sec(row.get("timeInt")), dict(row.attrib)) for row in volume_rows],
                key=lambda item: item[0],
            )
            peak_volume = max(float(attrs.get("volume", "0") or 0.0) for _sec, attrs in original_rows) * args.scale
            shifted_rows: list[tuple[int, dict[str, str]]] = []
            for sec, attrs in original_rows:
                base_volume = float(attrs.get("volume", "0") or 0.0) * args.scale
                if sec <= args.plateau_start_sec:
                    new_attrs = dict(attrs)
                    new_attrs["volume"] = format_volume(base_volume)
                    shifted_rows.append((sec, new_attrs))
                    continue

                if sec <= args.plateau_start_sec + args.recovery_shift_sec:
                    hold_attrs = dict(attrs)
                    set_time_int_start_sec(hold_attrs, sec)
                    hold_attrs["volume"] = format_volume(peak_volume)
                    shifted_rows.append((sec, hold_attrs))
                    changes.append(
                        {
                            "vehicle_input_no": vi.get("no", ""),
                            "name": vi.get("name", ""),
                            "time_start_sec": sec,
                            "new_volume_vph": peak_volume,
                            "reason": "insert_peak_hold_row",
                        }
                    )

                moved_sec = sec + args.recovery_shift_sec
                moved_attrs = dict(attrs)
                set_time_int_start_sec(moved_attrs, moved_sec)
                moved_attrs["volume"] = format_volume(base_volume)
                shifted_rows.append((moved_sec, moved_attrs))
                changes.append(
                    {
                        "vehicle_input_no": vi.get("no", ""),
                        "name": vi.get("name", ""),
                        "old_time_start_sec": sec,
                        "new_time_start_sec": moved_sec,
                        "volume_vph": base_volume,
                        "reason": "shift_recovery_row",
                    }
                )

            for child in list(volume_container):
                volume_container.remove(child)
            for _sec, attrs in sorted(shifted_rows, key=lambda item: item[0]):
                ET.SubElement(volume_container, "timeIntervalVehVolume", attrs)
        else:
            peak_volume = max(float(row.get("volume", "0") or 0.0) for row in volume_rows) * args.scale
            for row in volume_rows:
                sec = time_int_start_sec(row.get("timeInt"))
                if sec >= args.plateau_start_sec:
                    old = float(row.get("volume", "0") or 0.0)
                    new = peak_volume
                    if abs(old - new) > 1.0e-9:
                        row.set("volume", f"{new:.6f}".rstrip("0").rstrip("."))
                        changes.append(
                            {
                                "vehicle_input_no": vi.get("no", ""),
                                "name": vi.get("name", ""),
                                "time_start_sec": sec,
                                "old_volume_vph": old,
                                "new_volume_vph": new,
                            }
                        )

    after = summarize(root, roles)

    out_inpx.parent.mkdir(parents=True, exist_ok=True)
    tree.write(out_inpx, encoding="utf-8", xml_declaration=True)

    layx = Path(args.layx)
    out_layx = Path(args.out_layx)
    if layx.exists():
        out_layx.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(layx, out_layx)

    summary_csv = Path(args.summary_csv)
    summary_csv.parent.mkdir(parents=True, exist_ok=True)
    after_label = "peakhold_recovery" if args.recovery_shift_sec > 0 else "peakplateau"
    with summary_csv.open("w", newline="", encoding="utf-8-sig") as f:
        fieldnames = [
            "scenario",
            "sec",
            "total_vph",
            "urban_vph",
            "freeway_vph",
            "total_vs_peak_pct",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for scenario, rows in (("original", before), (after_label, after)):
            for row in rows:
                writer.writerow({"scenario": scenario, **row})

    report = {
        "source_inpx": str(inpx),
        "output_inpx": str(out_inpx),
        "output_layx": str(out_layx),
        "plateau_start_sec": args.plateau_start_sec,
        "recovery_shift_sec": args.recovery_shift_sec,
        "scale": args.scale,
        "summary_csv": str(summary_csv),
        "changes_count": len(changes),
        "after_label": after_label,
        "before": before,
        "after": after,
        "note": (
            "If recovery_shift_sec is positive, intervals after plateau_start_sec are delayed while preserving "
            "their original volumes, creating an extended peak with recovery. Otherwise, intervals at or after "
            "plateau_start_sec are set to each input's peak volume. Routes, signals, geometry, and control objects "
            "are unchanged."
        ),
    }
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
