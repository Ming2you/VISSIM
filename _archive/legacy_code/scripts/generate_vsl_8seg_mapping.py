"""Generate vsl_segment_mapping_8seg.json from vsl_8seg_manifest.csv.

Schema follows evaluation/vsl_install/vsl_segment_mapping.json (5-seg,
schema_version 1) with additions:
  * schema_version 2
  * per-segment corridor coordinates (segment_start_m/segment_end_m measured
    from the entry-extension link start, gap connectors included in S0/S7)
  * pos_m/link per DSD stay in own-link coordinates (actuation needs them)
  * top-level "mainline_extension" block: entry/exit link + connector numbers
  * top-level "runner_binning" block: main-link boundary arrays for S1..S7
    and link->segment assignments for the extension links/connectors
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
MANIFEST = WORKSPACE / "evaluation/vsl_install/vsl_8seg_manifest.csv"
OUT = WORKSPACE / "evaluation/vsl_install/vsl_segment_mapping_8seg.json"

NETWORK = r"C:/Users/TRLAB/Desktop/찐찐막/Network_Vissim_Work/modi_eval_vsl_8seg.inpx"

MAIN_LINK_LEN = 2900.003
GAP_M = 4.0

# Main-link segment boundaries (S1 start .. S7 end), own-link coordinates.
MAIN_BOUNDS = {
    "EB": [0.0, 350.0, 800.0, 1300.0, 1800.0, 2300.0, 2600.0, MAIN_LINK_LEN],
    "WB": [0.0, 350.0, 850.0, 1350.0, 1900.0, 2450.0, 2750.0, MAIN_LINK_LEN],
}
MAIN_LINK = {"EB": 33, "WB": 34}

PURPOSE_RAMP = {
    "EB_S2_D_DIVERGE": "off_ramp OR_D diverge at 499.03 (model off_ramp_segment_index 2)",
    "EB_S3_D_MERGE": "on_ramp R_D merge at 812.39, metering (model ramp_merge_segment_index 3)",
    "EB_S4_F_DIVERGE": "off_ramp OR_F diverge at 1735.61 (model off_ramp_segment_index 4)",
    "EB_S5_F_MERGE": "on_ramp R_F merge at 2029.15, metering (model ramp_merge_segment_index 5)",
    "WB_S2_F_DIVERGE": "off_ramp OR_F diverge at 537.74 (model off_ramp_segment_index 2)",
    "WB_S3_F_MERGE": "on_ramp R_F merge at 1155.25, metering (model ramp_merge_segment_index 3)",
    "WB_S4_D_DIVERGE": "off_ramp OR_D diverge at 1743.46 (model off_ramp_segment_index 4)",
    "WB_S5_D_MERGE": "on_ramp R_D merge at 2398.24, metering (model ramp_merge_segment_index 5)",
}


def main() -> None:
    rows = list(csv.DictReader(MANIFEST.open(encoding="utf-8")))
    dsd_rows = [r for r in rows if r["object_type"] == "desSpeedDecision"]
    link_rows = {r["segment_id"]: r for r in rows if r["object_type"] == "link"}
    conn_rows = [r for r in rows if r["object_type"] == "connector"]

    ext = {
        "EB_entry_link": int(link_rows["EB_S0_W_EXT_ENTRY"]["no"]),
        "EB_exit_link": int(link_rows["EB_S7_E_EXIT"]["no"]),
        "WB_entry_link": int(link_rows["WB_S0_E_EXT_ENTRY"]["no"]),
        "WB_exit_link": int(link_rows["WB_S7_W_EXIT"]["no"]),
        "connectors": {
            r["name"]: int(r["no"]) for r in conn_rows
        },
        "gap_m": GAP_M,
    }

    entry_len = {
        "EB": float(link_rows["EB_S0_W_EXT_ENTRY"]["segment_end_m"]),
        "WB": float(link_rows["WB_S0_E_EXT_ENTRY"]["segment_end_m"]),
    }
    exit_len = {
        "EB": float(link_rows["EB_S7_E_EXIT"]["segment_end_m"]),
        "WB": float(link_rows["WB_S7_W_EXIT"]["segment_end_m"]),
    }

    segments = []
    by_seg: dict[str, list[dict]] = {}
    for r in dsd_rows:
        by_seg.setdefault(r["segment_id"], []).append(r)

    for seg_id, group in by_seg.items():
        g0 = group[0]
        direction = g0["direction"]
        idx = int(seg_id.split("_S")[1][0])
        corridor_start = float(g0["segment_start_m"])
        corridor_end = float(g0["segment_end_m"])
        # include the gap connectors in the end segments' effective lengths
        if idx == 0:
            corridor_end += GAP_M
        if idx == 7:
            corridor_end += GAP_M
        segments.append(
            {
                "segment_id": seg_id,
                "model_link": "FW_E" if direction == "EB" else "FW_W",
                "model_segment_index": idx,
                "direction": direction,
                "link": int(g0["link"]),
                "segment_start_m": corridor_start,
                "segment_end_m": corridor_end,
                "length_m": round(corridor_end - corridor_start, 3),
                "default_speed_kph": int(float(g0["default_speed_kph"])),
                "veh_classes": [10, 20, 30],
                "dsd_by_lane": {
                    r["lane"]: {
                        "dsd_no": int(r["no"]),
                        "pos_m": float(r["pos"]),
                        "name": r["name"],
                    }
                    for r in group
                },
                "purpose": PURPOSE_RAMP.get(seg_id, g0["purpose"]),
            }
        )

    segments.sort(key=lambda s: (s["direction"], s["model_segment_index"]))

    runner_binning = {
        "main_link_bounds": {
            str(MAIN_LINK[d]): MAIN_BOUNDS[d] for d in ("EB", "WB")
        },
        "main_link_segment_offset": 1,
        "link_to_segment": {
            str(ext["EB_entry_link"]): {"model_link": "FW_E", "segment": 0},
            str(ext["connectors"]["FW_E entry->main"]): {"model_link": "FW_E", "segment": 0},
            str(ext["EB_exit_link"]): {"model_link": "FW_E", "segment": 7},
            str(ext["connectors"]["FW_E main->exit"]): {"model_link": "FW_E", "segment": 7},
            str(ext["WB_entry_link"]): {"model_link": "FW_W", "segment": 0},
            str(ext["connectors"]["FW_W entry->main"]): {"model_link": "FW_W", "segment": 0},
            str(ext["WB_exit_link"]): {"model_link": "FW_W", "segment": 7},
            str(ext["connectors"]["FW_W main->exit"]): {"model_link": "FW_W", "segment": 7},
        },
        "entry_len_m": entry_len,
        "exit_len_m": exit_len,
    }

    out = {
        "schema_version": 2,
        "network": NETWORK,
        "control_action": "speed_limit_kph_by_segment_id",
        "notes": [
            "8 control segments per direction; one ramp junction per segment.",
            "Model geometry: off_ramp_segment_index {OR_D:2, OR_F:4} (EB) / {OR_F:2, OR_D:4} (WB order),",
            "ramp_merge_segment_index {R_D:3, R_F:5} (EB) / {R_F:3, R_D:5} (WB order)",
            "matching Numerical-Sim feature/segment-agents-13p default.yaml (segments 8, off 2/4, merge 3/5).",
            "Links 33/34 unchanged from the 5-seg network; mainline extended with entry/exit links + 4 m gap connectors.",
            "S0 lives on the entry extension link; S7 spans the main-link tail + exit extension link.",
            "segment_start_m/segment_end_m are corridor coordinates (0 = entry link start).",
            "dsd pos_m is in the DSD's own link coordinates.",
        ],
        "mainline_extension": ext,
        "runner_binning": runner_binning,
        "segments": segments,
    }

    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"WROTE {OUT}")
    print(f"segments={len(segments)} dsds={sum(len(s['dsd_by_lane']) for s in segments)}")
    for s in segments:
        print(
            f"  {s['segment_id']:22s} link={s['link']:>5} idx={s['model_segment_index']} "
            f"corridor=[{s['segment_start_m']:8.2f},{s['segment_end_m']:8.2f}) len={s['length_m']:7.2f}"
        )


if __name__ == "__main__":
    main()
