"""Validate only the completed 60-second, three-SG native recording probe.

Exit 1 preserves the independent LSA coverage failure even when LDP passes.
No COM, model imports, FZP reads, or changes to the probe/input files.
"""
from __future__ import annotations

import argparse
import csv
from decimal import Decimal
import hashlib
import io
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
TARGETS = ((1, 1), (1004, 5), (9103, 1))
COM_TARGETS = TARGETS[1:]
# Fixed SG_BILD alphabet, checked against independent actual SigState samples.
# In these 2020.00-14 files GREEN is ASCII I (0x49), not a guessed vertical bar.
LDP_STATES = {".": "RED", "I": "GREEN", "/": "AMBER", " ": "OFF"}
CSV_FIELDS = ["sim_sec", "stage", "sc", "sg", "state", "contr_by_com"]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def number(value):
    result = Decimal(str(value).strip())
    require(result.is_finite() and result >= 0, "Invalid nonnegative native number")
    return result


def integer(value):
    result = number(value)
    require(result == result.to_integral_value(), "Noninteger clock/address")
    return int(result)


def writes_at(second):
    if second in (1, 20, 50):
        return [(key, "GREEN") for key in COM_TARGETS]
    if second in (10, 40):
        return [(key, "AMBER") for key in COM_TARGETS]
    if second in (11, 41):
        return [((9103, 1), "RED")]
    if second in (13, 43):
        return [((1004, 5), "RED")]
    return []


def parse_readbacks(raw):
    stream = csv.DictReader(io.StringIO(raw.decode("utf-16")))
    require(stream.fieldnames == CSV_FIELDS, "Wrong readback columns")
    rows = list(stream)
    expected = [(0, "initial", key) for key in TARGETS]
    for second in range(1, 61):
        expected.extend((second, "after_step", key) for key in TARGETS)
        for key, _ in writes_at(second):
            expected.extend((second, stage, key) for stage in ("before_write", "after_write"))
    require(len(rows) == len(expected), "Missing/extra readback rows")
    frames, writes, current, initial = {}, [], {}, []
    for row, (second, stage, key) in zip(rows, expected):
        require(set(row) == set(CSV_FIELDS) and None not in row.values(), "Malformed CSV row")
        require((integer(row["sim_sec"]), row["stage"],
                 (integer(row["sc"]), integer(row["sg"]))) == (second, stage, key),
                "Missing/duplicate/reordered readback address, clock or stage")
        state, owned = row["state"], row["contr_by_com"]
        if stage == "initial":
            require(state in ("", *LDP_STATES.values()) and owned in ("", "0", "1"),
                    "Malformed pre-simulation readback")
            initial.append(row)
            continue
        require(state in LDP_STATES.values() and owned in ("0", "1"), "Invalid actual state/ownership")
        expected_owned = key in COM_TARGETS and (second > 1 or stage == "after_write")
        require(owned == str(int(expected_owned)), "Unexpected COM ownership")
        if stage == "after_step":
            frames[(key, second)] = state
            current[key] = state
        elif stage == "before_write":
            require(current[key] == state, "Before-write state differs from same-time after-step")
        else:
            require(state == dict(writes_at(second))[key], "Actual write did not realize the pinned schedule")
            require(current[key] != state, "Expected test transition did not change state")
            writes.append({"key": key, "second": second, "before": current[key], "after": state})
            current[key] = state
    require(len(writes) == 14 and len(frames) == 180, "Incomplete three-SG probe")
    return frames, writes, initial


def parse_ldp(raw, sc, sg):
    lines = raw.splitlines()
    require(lines and lines[0].startswith(b"SC Detector Record"), "Wrong LDP type")
    header, result, started = [], {}, False
    for line in lines[1:]:
        if not line.strip():
            continue
        looks_numeric = re.match(rb"\s*[+\-]?(?:\d|\.\d)", line) is not None
        if not started and not looks_numeric:
            header.append(line)
            continue
        started = True
        require(len(line) == 13, "Wrong LDP fixed-width row (7+5+1)")
        second = integer(line[:7].decode("ascii"))
        cycle = number(line[7:12].decode("ascii"))
        symbol = line[12:13].decode("ascii")
        require(symbol in LDP_STATES, "Unknown SG_BILD state symbol")
        require(second == len(result) + 1 and second <= 60, "LDP missing/duplicate/reordered second")
        result[second] = {"state": LDP_STATES[symbol], "symbol": symbol, "cycle_sec": str(cycle)}
    require(len(result) == 60, "LDP does not cover exactly 1..60")
    require(sum(line.startswith(f"SC {sc};".encode()) for line in header) == 1, "Wrong LDP SC header")
    require(header[-1] == f"      d    d{sg}".encode(), "Wrong single SG column header")
    return result


def parse_lsa(raw):
    result, started, previous = [], False, Decimal(0)
    for line in raw.splitlines():
        if not line.strip():
            continue
        if not started and b";" not in line:
            continue
        started = True
        parts = [part.strip() for part in line.decode("ascii").split(";")]
        require(len(parts) == 9 and parts[-1] == "", "Malformed LSA event")
        second, cycle, age = number(parts[0]), number(parts[1]), number(parts[5])
        require(previous <= second <= 60, "LSA clock outside ordered window")
        previous = second
        key = (integer(parts[2]), integer(parts[3]))
        require(min(key) > 0 and parts[6] == "Fixed Time", "Unexpected LSA address/controller")
        integer(parts[7])
        state = parts[4].upper().replace("/", "")
        require(state in (*LDP_STATES.values(), "REDAMBER"), "Unknown LSA state")
        result.append((second, key, state))
    require(result, "No LSA events")
    return result


def _ldp_integer(value, label, minimum=1):
    try:
        require(not isinstance(value, bool), label + " is boolean")
        result = integer(value)
    except (ArithmeticError, TypeError, ValueError) as exc:
        raise ValueError("Invalid " + label) from exc
    require(result >= minimum, "Invalid " + label)
    return result


def _ldp_groups(expected_groups):
    require(isinstance(expected_groups, dict) and expected_groups, "Missing expected LDP groups")
    result = {}
    for raw_sc, raw_sgs in expected_groups.items():
        sc = _ldp_integer(raw_sc, "SC address")
        require(sc not in result, "Duplicate expected SC address")
        require(not isinstance(raw_sgs, (str, bytes)), "Expected an SG collection")
        sgs = [_ldp_integer(sg, "SG address") for sg in raw_sgs]
        require(sgs and len(sgs) == len(set(sgs)), "Missing/duplicate expected SG address")
        result[sc] = tuple(sorted(sgs))
    return dict(sorted(result.items()))


def parse_ldp_columns(raw, sc, expected_sgs, start_sec, end_sec):
    """Read 2020 SG_BILD fixed-width columns with NUMBER/long-label headers.

    Only the supplied SC/SG set is accepted. The inclusive requested window must
    be complete; any rows outside it are still syntax/address/order checked.
    An OFF column is a literal trailing space and must never be stripped.
    """
    sc = _ldp_integer(sc, "SC address")
    sgs = _ldp_groups({sc: expected_sgs})[sc]
    start = _ldp_integer(start_sec, "start second")
    end = _ldp_integer(end_sec, "end second")
    require(start <= end, "Reversed LDP window")
    width = 12 + len(sgs)
    # REDAMBER '=' is documented in the installed 2020 manual. The other four
    # symbols retain the existing pilot's independently observed alphabet.
    states = {**LDP_STATES, "=": "REDAMBER"}
    lines = raw.splitlines()
    require(lines and lines[0].startswith(b"SC Detector Record"), "Wrong LDP type")
    header, columns, frames, previous, total = [], None, {}, 0, 0
    found_sc = False
    for line in lines[1:]:
        if not line.strip():
            continue
        numeric = re.match(rb"\s*[+\-]?(?:\d|\.\d)", line) is not None
        if columns is None and not numeric:
            if line.startswith(b"SC "):
                match = re.match(rb"SC ([1-9][0-9]*);", line)
                require(not found_sc and match is not None and int(match[1]) == sc,
                        "Wrong/duplicate LDP SC header")
                found_sc = True
            else:
                require(found_sc, "Unexpected LDP preamble")
                header.append(line)
            continue
        if columns is None:
            require(found_sc and header and all(len(h) <= width for h in header),
                    "Missing/oversized LDP column header")
            try:
                labels = [''.join(chr(h[i]) for h in header if len(h) > i and h[i] != 32)
                          for i in range(width)]
                require(labels[6] == "Simul.second" and labels[11] == "Cyclesecond"
                        and all(not labels[i] for i in range(12) if i not in (6, 11)),
                        "Wrong LDP clock column header")
                matches = [re.fullmatch(r"Sig\.DisplaySG([1-9][0-9]*)", label)
                           for label in labels[12:]]
                require(all(matches), "Unknown LDP SG column header")
                columns = tuple(int(match[1]) for match in matches)
            except (UnicodeError, IndexError) as exc:
                raise ValueError("Malformed LDP column header") from exc
            require(len(columns) == len(set(columns)) and set(columns) == set(sgs),
                    "Wrong/missing/duplicate LDP SG column address")
        require(len(line) == width, "Wrong LDP fixed-width row")
        try:
            second = _ldp_integer(line[:7].decode("ascii"), "LDP second")
            number(line[7:12].decode("ascii"))
            symbols = line[12:].decode("ascii")
        except (ArithmeticError, UnicodeError, ValueError) as exc:
            raise ValueError("Malformed LDP numeric/state row") from exc
        require(second > previous, "Duplicate/reordered LDP second")
        require(all(symbol in states for symbol in symbols), "Unknown SG_BILD state symbol")
        previous = second
        total += 1
        if start <= second <= end:
            frames[second] = {f"{sc}:{sg}": states[symbol] for sg, symbol in zip(columns, symbols)}
    require(columns is not None and set(frames) == set(range(start, end + 1)),
            "Missing LDP frame in requested window")
    return {"frames": frames, "column_order": columns, "file_row_count": total}


def read_ldp_frames(files_by_sc, expected_groups, start_sec, end_sec):
    """Read selected completed-run LDP files; no glob, COM, LSA or FZP access.

    files_by_sc and expected_groups must name exactly the same controllers.
    A subset such as only the eight meters is supported by supplying only them.
    This proves frame coverage, not that every SG made a transition.
    """
    groups = _ldp_groups(expected_groups)
    start = _ldp_integer(start_sec, "start second")
    end = _ldp_integer(end_sec, "end second")
    require(start <= end and isinstance(files_by_sc, dict), "Invalid LDP window/files")
    files = {}
    for key, path in files_by_sc.items():
        sc = _ldp_integer(key, "file SC address")
        require(sc not in files, "Duplicate file SC address")
        files[sc] = Path(path).resolve()
    require(set(files) == set(groups) and len(set(files.values())) == len(files),
            "Missing/extra/duplicate LDP file mapping")
    frames = {t: {} for t in range(start, end + 1)}
    pins, order, file_rows = {}, {}, {}
    for sc, path in sorted(files.items()):
        before = path.stat()
        raw = path.read_bytes()
        after = path.stat()
        require((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns),
                "LDP changed while reading: " + str(path))
        parsed = parse_ldp_columns(raw, sc, groups[sc], start, end)
        pins[str(path)] = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
        order[sc], file_rows[sc] = parsed["column_order"], parsed["file_row_count"]
        for t, values in parsed["frames"].items():
            frames[t].update(values)
    addresses = {f"{sc}:{sg}" for sc, sgs in groups.items() for sg in sgs}
    require(all(set(row) == addresses for row in frames.values()), "Incomplete LDP address frame")
    return {"schema": "native-ldp-frames/v1", "native_ldp_frame_coverage_passed": True,
            "frames": frames, "pins": pins, "column_order_by_sc": order,
            "file_row_count_by_sc": file_rows, "expected_groups": groups,
            "start_sec": start, "end_sec": end,
            "row_count": len(groups) * len(frames), "sample_count": len(addresses) * len(frames)}


def check_ldp_command_clock(record, clock, first_control_sec_by_group):
    """Compare native after-step states to the existing one-second command oracle.

    LDP at t precedes a new write at t: the oracle uses post_step, hence t-1.
    t <= first control application is preserved as pre-control native evidence.
    The row-shaped oracle input below is only a state-comparison adapter, NOT
    COM requested/readback evidence. Actual initial immediate reads are separate.
    LSA coverage is neither filled nor changed by this function.
    """
    groups = _ldp_groups(record["expected_groups"])
    addresses = {f"{sc}:{sg}" for sc, sgs in groups.items() for sg in sgs}
    require(set(first_control_sec_by_group) == addresses, "Missing/extra first-control address")
    first = {key: _ldp_integer(value, "first control second")
             for key, value in first_control_sec_by_group.items()}
    for key in addresses:
        sc, sg = key.split(":")
        applications = [t for t, snapshot in zip(clock.times, clock.snapshots)
                        if (sc in snapshot["ramps"] and sg == "1")
                        or (sc in snapshot["signals"] and sg in clock.groups.get(sc, {}))]
        require(applications and first[key] == applications[0],
                "First-control time differs from command clock: " + key)
    start, end = record["start_sec"], record["end_sec"]
    require(set(record["frames"]) == set(range(start, end + 1)), "Incomplete LDP clock input")
    require(all(value <= end for value in first.values()), "No controlled LDP window")
    errors, initial, counts, transitions, previous = [], {}, dict.fromkeys(addresses, 0), dict.fromkeys(addresses, 0), {}
    for t, values in sorted(record["frames"].items()):
        require(set(values) == addresses, "Incomplete LDP clock address input")
        for key, state in sorted(values.items()):
            require(state in (*LDP_STATES.values(), "REDAMBER"), "Unknown LDP actual state")
            if t <= first[key]:
                initial.setdefault(t, {})[key] = state
                continue
            sc, sg = key.split(":")
            try:
                clock.check_signal({"sim_sec": t, "stage": "post_step", "sc_no": sc, "sg_no": sg,
                                    "requested_state": state, "readback_state": state, "ok": "1"})
            except ValueError as exc:
                errors.append({"sim_sec": t, "address": key, "actual_state": state, "error": str(exc)})
            counts[key] += 1
            if key in previous and previous[key] != state:
                transitions[key] += 1
            previous[key] = state
    require(all(counts.values()), "No post-control sample for an expected group")
    return {"schema": "native-ldp-command-clock/v1", "passed": not errors,
            "native_ldp_command_clock_passed": not errors,
            "comparison_clock": "primary_1s_post_step_at_t_uses_command_clock_t_minus_1",
            "compared_samples": sum(counts.values()), "samples_by_group": counts,
            "observed_post_control_transitions_by_group": transitions,
            "pre_control_native_frames": initial, "mismatches": errors,
            "initial_immediate_readback_required_separately": True,
            "lsa_coverage_assessed": False}


def validate(folder):
    folder = Path(folder).resolve()
    pins = {}

    def read(path, expected=None):
        path = Path(path).resolve()
        before = path.stat()
        raw = path.read_bytes()
        after = path.stat()
        require((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns),
                f"Evidence changed while reading: {path}")
        digest = hashlib.sha256(raw).hexdigest()
        require(expected is None or expected == digest, f"Pinned hash differs: {path}")
        pins[str(path)] = {"sha256": digest, "bytes": len(raw)}
        return raw

    process = json.loads(read(folder / "process.json"))
    preflight = json.loads(read(folder / "preflight.json"))
    require(process["native_completed"] is True and process["exit_code"] == 0
            and process["actual_sim_sec"] == 60 and process["owned_vissim_remaining"] is False
            and process["error"] is None, "Process did not complete the owned 60-second run")
    network = Path(preflight["network"]).resolve()
    require(network.parent == folder, "Network is outside this probe folder")
    require(process["network_sha256"] == preflight["network_sha256"], "Process/preflight network differs")
    net_raw = read(network, preflight["network_sha256"])
    script = ROOT / "diagnostics/probe_native_signal_record.vbs"
    read(script, process["script_sha256"])
    output = folder / "vissim_eval"
    require(process["arguments"] == f'//nologo "{script}" "{network}" "{output}"',
            "Process does not bind this script/network/output")
    sources = {Path(path).resolve(): read(path, digest) for path, digest in preflight["sources"].items()}
    baseline = (ROOT / "diagnostics/fixed_beta300v3_network_arms_flat_v1/baseline.inpx").resolve()
    require(baseline in sources and len(sources) == 2, "Missing source/example pin")
    require(preflight["source_network_modified"] is False, "Original network was modified")
    require(len(preflight["auxiliary_files"]) == 42, "Wrong native SIG input catalog")
    for name, digest in preflight["auxiliary_files"].items():
        require(Path(name).name == name and name.lower().endswith(".sig"), "Invalid auxiliary path")
        read(folder / name, digest)
    root = ET.fromstring(net_raw)
    configs = root.findall(".//scDetRecConf")
    require(len(configs) == 3, "Wrong detector-record configuration count")
    for sc, sg in TARGETS:
        parent = root.find(f".//signalController[@no='{sc}']")
        conf = parent.find("scDetRecConf")
        expected = [dict(configName=name, detPort="0", title="", varNo="0", wttFilename="vissim")
                    for name in ("SIM_SEK", "UML_SEK")]
        expected.append(dict(configName="SG_BILD", detPort="0", sg=f"{sc} {sg}",
                             title="", varNo=str(sg), wttFilename="vissim"))
        require(conf is not None and all(c.tag == "signalOutputConfigurationElement" for c in conf)
                and [c.attrib for c in conf] == expected, "Wrong SG_BILD input address/schema")
        parent.remove(conf)

    def xml_value(node):
        return node.tag, sorted(node.attrib.items()), (node.text or "").strip(), tuple(xml_value(c) for c in node)

    require(xml_value(root) == xml_value(ET.fromstring(sources[baseline])), "Non-recording network changes")
    stdout = read(folder / "stdout.txt").decode("utf-8-sig").splitlines()
    require(read(folder / "stderr.txt") == b"", "Probe stderr is not empty")
    require(stdout.count("NATIVE_RECORD_PROBE_DONE=1") == 1 and stdout.count("EVAL_LSA=1 LDP=1") == 1
            and not any(line.startswith(("FAILED=", "ERROR=")) for line in stdout), "Probe completion/output failure")
    require([line for line in stdout if line.startswith("ACTUAL_SIMSEC=")] ==
            [f"ACTUAL_SIMSEC={t}" for t in range(1, 61)], "Incomplete actual progress log")
    frames, writes, initial = parse_readbacks(read(output / "actual_readback.csv"))
    prefix = network.stem
    ldps = {key: parse_ldp(read(output / f"{prefix}_{key[0]}_001.ldp"), *key) for key in TARGETS}
    lsa = parse_lsa(read(output / f"{prefix}_001.lsa"))
    lsa_events = set(lsa)
    ldp_mismatches = [{"sc": key[0], "sg": key[1], "sim_sec": t,
                      "ldp": ldps[key][t]["state"], "actual": state}
                     for (key, t), state in frames.items() if ldps[key][t]["state"] != state]
    com_changes = [{"sc": w["key"][0], "sg": w["key"][1], "write_sec": w["second"],
                    "before_state": w["before"], "after_state": w["after"],
                    "same_frame_state": ldps[w["key"]][w["second"]]["state"],
                    "next_frame_sec": w["second"] + 1,
                    "next_frame_matches": ldps[w["key"]][w["second"] + 1]["state"] == w["after"],
                    "next_actual_matches": frames[w["key"], w["second"] + 1] == w["after"],
                    "lsa_at_write_matches": (Decimal(w["second"]), w["key"], w["after"]) in lsa_events,
                    "lsa_at_next_frame_matches": (Decimal(w["second"] + 1), w["key"], w["after"]) in lsa_events}
                   for w in writes]
    native_changes = [{"sim_sec": t, "state": frames[(1, 1), t],
                       "ldp_matches": ldps[(1, 1)][t]["state"] == frames[(1, 1), t],
                       "lsa_matches": (Decimal(t), (1, 1), frames[(1, 1), t]) in lsa_events}
                      for t in range(2, 61) if frames[(1, 1), t] != frames[(1, 1), t - 1]]
    initial_frames = [{"sc": key[0], "sg": key[1], "sim_sec": 1,
                       "actual_before_com": frames[key, 1], "ldp": ldps[key][1]["state"],
                       "lsa_matches": (Decimal(1), key, frames[key, 1]) in lsa_events}
                      for key in TARGETS]
    ldp_ok = not ldp_mismatches and all(w["next_frame_matches"] and w["next_actual_matches"] for w in com_changes)
    lsa_ok = all(w["lsa_at_write_matches"] for w in com_changes)
    # Recheck bytes, not just size/mtime; this validator reads only small stated inputs/outputs.
    for name, pin in list(pins.items()):
        read(name, pin["sha256"])
    read(Path(__file__))
    return {"schema": "native-signal-record-validation/v1", "completed": True,
            "passed": ldp_ok and lsa_ok, "ldp_per_step_coverage_passed": ldp_ok,
            "native_lsa_com_coverage_passed": lsa_ok, "source_and_evidence_unchanged": True,
            "run_directory": str(folder), "window": {"first_sec": 1, "last_sec": 60, "sim_res": 1},
            "process": process, "pins": pins, "pre_simulation_rows": initial,
            "mapping": {"symbols": LDP_STATES, "basis": "Fixed SG_BILD alphabet verified against independent actual SigState; I is ASCII 0x49",
                        "independently_matched_counts": {symbol: sum(row["symbol"] == symbol and row["state"] == frames[key, t]
                            for key, rows in ldps.items() for t, row in rows.items()) for symbol in LDP_STATES}},
            "ldp": {"status": "PASS" if ldp_ok else "FAIL", "files": 3, "frames_per_file": 60,
                    "compared_frames": 180, "duplicate_or_missing_frames": 0, "mismatches": ldp_mismatches,
                    "com_changes": com_changes, "matched_next_frame_changes": sum(w["next_frame_matches"] and w["next_actual_matches"] for w in com_changes),
                    "native_SC1_transitions": native_changes, "initial_frames": initial_frames},
            "lsa": {"status": "PASS" if lsa_ok else "FAIL", "total_events": len(lsa),
                    "com_changes_checked": len(writes), "matched_at_write": sum(w["lsa_at_write_matches"] for w in com_changes),
                    "matched_at_next_frame": sum(w["lsa_at_next_frame_matches"] for w in com_changes),
                    "missing_com_changes": [w for w in com_changes if not w["lsa_at_write_matches"]],
                    "native_SC1_transition_count": len(native_changes),
                    "native_SC1_transition_matches": sum(w["lsa_matches"] for w in native_changes)},
            "limitations": ["Only two COM-owned SGs and one native SG for 60 seconds; no other SG/long-run coverage claim.",
                "LDP is the after-step state before later COM writes at the same SimSec; immediate writes appear at the next frame.",
                "The t0 empty readbacks are unavailable, not OFF. The t1 LDP is pre-COM; applied initial GREEN is verified by immediate readback and t2 LDP.",
                "One native sample per second does not prove subsecond or multiple same-time COM writes.",
                "LDP/command values never fill missing LSA events; independent LSA coverage remains FAIL.",
                "No traffic improvement, execution-equivalence or adaptive-controller result is claimed."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    require(not args.out.exists(), "Preserve previous verification; choose a new output path")
    result = validate(args.folder)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: result[k] for k in ("completed", "passed", "ldp_per_step_coverage_passed", "native_lsa_com_coverage_passed")}))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
