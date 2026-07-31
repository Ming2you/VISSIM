from __future__ import annotations

import argparse
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inpx", default="network/real_world_gaepo_modi/modi.inpx")
    parser.add_argument("--layx", default="network/real_world_gaepo_modi/modi.layx")
    parser.add_argument("--out-inpx", default="network/real_world_gaepo_modi/modi_eval_sanitized.inpx")
    parser.add_argument("--out-layx", default="network/real_world_gaepo_modi/modi_eval_sanitized.layx")
    parser.add_argument("--eval-out-dir", default="network/real_world_gaepo_modi/vissim_eval")
    parser.add_argument("--report", default="outputs/real_world_modi_eval_sanitization_20260718.json")
    args = parser.parse_args()

    inpx = Path(args.inpx)
    out_inpx = Path(args.out_inpx)
    eval_out_dir = Path(args.eval_out_dir).resolve()
    eval_out_dir.mkdir(parents=True, exist_ok=True)

    tree = ET.parse(inpx)
    root = tree.getroot()
    changes: list[dict[str, str]] = []

    for evaluation in root.iter("evaluation"):
        old = evaluation.get("databaseConnection", "")
        evaluation.set("databaseConnection", "")
        changes.append({"object": "evaluation", "attribute": "databaseConnection", "old": old, "new": ""})

        old = evaluation.get("evalOutDir", "")
        evaluation.set("evalOutDir", str(eval_out_dir))
        changes.append({"object": "evaluation", "attribute": "evalOutDir", "old": old, "new": str(eval_out_dir)})

        old = evaluation.get("listAutoExportType", "")
        evaluation.set("listAutoExportType", "FILE")
        changes.append({"object": "evaluation", "attribute": "listAutoExportType", "old": old, "new": "FILE"})

    for element in root.iter():
        if "writeDatabase" in element.attrib and element.get("writeDatabase") != "false":
            old = element.get("writeDatabase", "")
            element.set("writeDatabase", "false")
            changes.append(
                {
                    "object": element.tag,
                    "attribute": "writeDatabase",
                    "old": old,
                    "new": "false",
                }
            )

    for simulation in root.iter("simulation"):
        for attr, new_value in {
            "numRuns": "1",
            "useMaxSimSpeed": "true",
            "simRes": "1",
        }.items():
            old = simulation.get(attr, "")
            simulation.set(attr, new_value)
            changes.append({"object": "simulation", "attribute": attr, "old": old, "new": new_value})

    out_inpx.parent.mkdir(parents=True, exist_ok=True)
    tree.write(out_inpx, encoding="utf-8", xml_declaration=True)

    out_layx = Path(args.out_layx)
    if Path(args.layx).exists():
        out_layx.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(args.layx, out_layx)

    report = {
        "source_inpx": str(inpx),
        "output_inpx": str(out_inpx),
        "output_layx": str(out_layx),
        "eval_out_dir": str(eval_out_dir),
        "changes": changes,
        "note": "Geometry, demand, routes, signal controllers, and signal timings are unchanged.",
    }
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
