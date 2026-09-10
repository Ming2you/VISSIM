"""Capture native ERR bytes and classify explicit removals; no simulator/model access."""
from __future__ import annotations
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from diagnostics.probe_e8_lane_receiving import IndexedFzp

NUMBER = r"([0-9]+(?:\.[0-9]+)?)"
REMOVAL = re.compile(r"Simulation second "+NUMBER+r": After "+NUMBER+
    r" seconds of waiting for lane change the vehicle (\d+) \(on Static Vehicle Route (\d+) - (\d+)(?:\s*:[^)]*)?\)"
    r" was removed from link (\d+) at position "+NUMBER+r"\.", re.I)
IGNORED = re.compile(r"Simulation second "+NUMBER+r": Vehicle (\d+) ignores the (static routing|desired speed)"
    r" decision (\d+) because it has left link (\d+) at position "+NUMBER, re.I)
TT = re.compile(r"Simulation second "+NUMBER+r": vehicle (\d+) already passed start of travel time section"
    r" (\d+) at simulation second "+NUMBER, re.I)
NEXT_LINK = re.compile(r"Simulation second "+NUMBER+r": Vehicle (\d+) \(on Static Vehicle Route (\d+) - (\d+)(?:\s*:[^)]*)?\)"
    r" arrived at the end of link (\d+) without having found the next link \((\d+)\) of its route\.", re.I)
INPUT_REMAINDER = re.compile(r"Vehicle input (\d+)(?::.*?)? could not be finished completely \(remain: (\d+) vehicles\)\.", re.I)


def digest(data): return hashlib.sha256(data).hexdigest()
def load(path): return json.loads(Path(path).read_text(encoding="utf-8-sig"))
def rel(path):
    path=Path(path).resolve()
    return path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)


def interval_check_candidates(removals, start, end):
    # Native warning time and FZP disappearance can differ by one sample.
    # Include the start-edge neighbourhood, then assign by observed upper time.
    return [r for r in removals if start-1 <= r["time_sec"] <= end]


def parse_bytes(data):
    end = data.rfind(b"\n")+1
    complete = data[:end]
    for encoding in ("utf-8-sig", "cp949"):
        try:
            text = complete.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("Complete ERR lines have unsupported encoding")
    rows, unknown, counts = [], [], Counter()
    offset = 0
    for line_number, raw in enumerate(complete.splitlines(keepends=True), 1):
        line = raw.decode(encoding).strip()
        line_offset = offset
        offset += len(raw)
        if not line:
            continue
        row = {"line_number": line_number, "byte_offset": line_offset,
               "raw_line_sha256": digest(raw), "message": line}
        match = REMOVAL.search(line)
        if match:
            t, wait, vehicle, decision, route, link, pos = match.groups()
            row.update(kind="lane_change_removal", time_sec=float(t), wait_sec=float(wait),
                       vehicle_id=int(vehicle), route_decision=int(decision), route_index=int(route),
                       link=link, position_m=float(pos))
        elif match := IGNORED.search(line):
            t, vehicle, kind, decision, link, pos = match.groups()
            row.update(kind="ignored_static_routing" if kind.lower()=="static routing" else "ignored_desired_speed",
                       time_sec=float(t), vehicle_id=int(vehicle), decision=int(decision),
                       link=link, position_m=float(pos))
        elif match := TT.search(line):
            t, vehicle, section, previous = match.groups()
            row.update(kind="duplicate_travel_time_section_start", time_sec=float(t),
                       vehicle_id=int(vehicle), section=int(section), previous_start_sec=float(previous))
        elif match := NEXT_LINK.search(line):
            t, vehicle, decision, route, link, target = match.groups()
            row.update(kind="route_next_link_not_found",time_sec=float(t),vehicle_id=int(vehicle),
                       route_decision=int(decision),route_index=int(route),link=link,next_link=target,
                       explicitly_says_removed=False)
        elif match := INPUT_REMAINDER.search(line):
            row.update(kind="unfinished_vehicle_input", input_no=int(match[1]), remaining_vehicles=int(match[2]),
                       explicitly_says_removed=False)
        elif line == 'Note\tStop the simulation? : &Yes':
            row["kind"] = "simulation_stop_prompt_answer"
        elif 'The signal controller DLL "VISSIG_Controller.dll" has written error messages' in line:
            row["kind"] = "signal_controller_dll_error_notice"
        elif "is located only" in line and "upstream of the first connector" in line:
            row["kind"] = "setup_routing_near_connector" if "Routing Decision" in line else "setup_desired_speed_near_connector"
        else:
            row["kind"] = "unparsed"
            unknown.append(row)
        counts[row["kind"]] += 1
        rows.append(row)
    return {"encoding": encoding, "complete_line_prefix_bytes": end, "complete_line_prefix_sha256":digest(complete),
            "partial_tail_bytes":len(data)-end, "counts":dict(counts), "events":rows, "unparsed":unknown,
            "unparsed_removal_lines": [r for r in unknown if "removed from link" in r["message"].lower()]}


def dll_program_messages(data):
    # This DLL writes adjacent messages and omits the final newline. Match only
    # explicit, punctuated full messages; retain raw bytes and tail separately.
    return [int(x) for x in re.findall(rb"The signal controller (\d+) has no signal program\.",data)]


def capture_file(source, directory):
    row = {"source":rel(source)}
    if not source.is_file():
        return {**row, "capture_status":"missing"}
    before = source.stat()
    row.update(size_before=before.st_size, mtime_ns_before=before.st_mtime_ns)
    try:
        data = source.read_bytes()
    except PermissionError as error:
        # Some live VISSIG DLL logs are held exclusively, including a zero-byte log.
        return {**row, "capture_status":"locked_unreadable", "error":str(error),
                "empty_size_observed":before.st_size==0, "raw_bytes_captured":False}
    after = source.stat()
    target = directory/source.name
    target.write_bytes(data)
    parsed = parse_bytes(data)
    return {**row, "capture_status":"captured", "capture":target.name, "raw_bytes_captured":True,
            "bytes":len(data), "sha256":digest(data), "size_after":after.st_size, "mtime_ns_after":after.st_mtime_ns,
            "source_unchanged_during_read":(before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns),
            **parsed, **({"no_signal_program_controllers":dll_program_messages(data),
                         "dll_message_scope":"Explicit complete punctuated messages from all captured bytes, including the final no-newline message; line-parser completeness is separate."}
                        if source.name=="VISSIG_Controller.dll.err" else {})}


def read_frame(reader, second, ranges):
    reader.seek_time(second)
    values, h, first, last, later = {}, hashlib.sha256(), None, None, None
    while raw := reader.line():
        if not raw.endswith(b"\n"):
            raise ValueError("Requested FZP frame is not closed")
        fields = raw.rstrip(b"\r\n").split(b";")
        if len(fields) != len(reader.names):
            raise ValueError("FZP row schema changed")
        t = float(fields[reader.index["SIMSEC"]])
        if not math.isfinite(t):
            raise ValueError("Nonfinite FZP time")
        if t < second:
            continue
        if t > second:
            later = t
            break
        if first is None:
            first = reader.handle.tell()-len(raw)
        last = reader.handle.tell()
        h.update(raw)
        i = reader.index
        no = int(fields[i["NO"]])
        value = {"link":fields[i["LANE\\LINK\\NO"]].decode(), "lane":int(fields[i["LANE\\INDEX"]]),
                 "position_m":float(fields[i["POS"]]), "speed_kph":float(fields[i["SPEED"]])}
        if no in values or any(not math.isfinite(value[k]) for k in ("position_m","speed_kph")):
            raise ValueError("Duplicate ID or nonfinite FZP observation")
        values[no] = value
    if not values or later is None:
        raise ValueError("FZP frame and later-row closure required")
    ranges.append({"second":second,"first_byte":first,"end_byte_exclusive":last,
                   "sha256":h.hexdigest(),"rows":len(values),"lookahead_sec":later})
    return values


def verify_ranges(path, ranges):
    with path.open("rb") as stream:
        for row in ranges:
            stream.seek(row["first_byte"])
            data=stream.read(row["end_byte_exclusive"]-row["first_byte"])
            if digest(data)!=row["sha256"]:
                raise ValueError("Selected FZP bytes changed")


def check_removals(path, events, inside, terminals, max_bytes=64*1024*1024):
    reader = IndexedFzp(path,max_bytes=max_bytes)
    ranges, output = [], []
    try:
        for event in events:
            t=event["time_sec"]
            times=range(max(1,math.floor(t)-1), math.ceil(t)+2)
            observed=[{"sec":sec,"vehicle":read_frame(reader,sec,ranges).get(event["vehicle_id"])} for sec in times]
            vanished=[{"lower_sec":a["sec"],"upper_sec":b["sec"],"last_vehicle":a["vehicle"]}
                      for a,b in zip(observed,observed[1:]) if a["vehicle"] is not None and b["vehicle"] is None]
            row={"vehicle_id":event["vehicle_id"],"native_time_sec":t,"native_link":event["link"],
                 "native_position_m":event["position_m"],"observations":observed,"disappearances":vanished}
            if len(vanished)==1:
                last=vanished[0]["last_vehicle"]
                row.update(last_link_matches_native=last["link"]==event["link"],
                           last_position_difference_m=last["position_m"]-event["position_m"],
                           last_link_inside=last["link"] in inside,
                           last_link_is_terminal=last["link"] in terminals)
            output.append(row)
        verify_ranges(path,ranges)
    finally:
        reader.handle.close()
    return {"fzp_path":rel(path),"source_size_at_open":reader.size,"bytes_read":reader.bytes_read,
            "max_bytes":max_bytes,"ranges":ranges,"checks":output,
            "scope":"Only native-warning IDs in selected +/-1-second windows; no full FZP scan or global disappearance search."}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run",required=True)
    parser.add_argument("--run-id",required=True)
    parser.add_argument("--complete",action="store_true")
    parser.add_argument("--output",type=Path)
    parser.add_argument("--fzp-checks",action="store_true",
                        help="Three examples plus all native removals in the three existing audited intervals; bounded64MiB")
    args=parser.parse_args()
    run=ROOT/"evaluation/runs"/args.run
    provenance_path=run/("run_provenance_"+args.run+".json")
    provenance_bytes=provenance_path.read_bytes(); provenance=json.loads(provenance_bytes.decode("utf-8-sig"))
    if provenance["run_id"]!=args.run_id:
        raise ValueError("Run provenance ID differs")
    network=Path(provenance["files"]["network"]["path"])
    if not network.is_absolute():network=ROOT/network
    network_sha=digest(network.read_bytes())
    if network_sha!=provenance["files"]["network"]["sha256"]:
        raise ValueError("Current network SHA differs from recorded run")
    membership_path=ROOT/"diagnostics/control_area_membership.json"; membership=load(membership_path)
    if membership["network"]["sha256"]!=network_sha:
        raise ValueError("Physical membership network differs")
    inside=set(map(str,membership["inside_links"])); outside=set(map(str,membership["outside_links"]))
    terminals=set(map(str,membership["terminal_inside_links"]))
    input_links={node.get("link") for node in ET.parse(network).getroot().findall("./vehicleInputs/vehicleInput")}
    log_path=run/("runlog_"+args.run+".txt"); log_bytes=log_path.read_bytes()
    done=b"STAGE=SIM_DONE" in log_bytes
    if args.complete and not done:
        raise ValueError("Complete capture requires current run log STAGE=SIM_DONE")
    now=datetime.now(timezone.utc)
    directory=(args.output.resolve() if args.output else
               ROOT/"diagnostics/native_runtime_error_capture"/(args.run+"_"+("complete_" if args.complete else "prefix_")+now.strftime("%Y%m%dT%H%M%S%fZ")))
    if not directory.is_relative_to(ROOT/"diagnostics") or directory.exists():
        raise ValueError("New diagnostic-only output directory required")
    directory.mkdir(parents=True,exist_ok=False)
    sources=[network.with_name(network.stem+"_001.err"),network.with_suffix(".err"),network.parent/"VISSIG_Controller.dll.err"]
    files=[capture_file(path,directory) for path in sources]
    runtime=files[0]
    if runtime["capture_status"]!="captured":
        raise ValueError("Runtime ERR could not be captured; other raw evidence remains in output")
    events=runtime["events"]; removals=[dict(e) for e in events if e["kind"]=="lane_change_removal"]
    for row in removals:
        row["omega"] = "inside" if row["link"] in inside else "outside" if row["link"] in outside else "unknown"
        row["terminal_inside"] = row["link"] in terminals
        row["physical_input_source_link"] = row["link"] in input_links
    duplicates=Counter((r["time_sec"],r["vehicle_id"],r["link"]) for r in removals)
    created=datetime.fromisoformat(provenance["created_at"]).timestamp()
    times=[e["time_sec"] for e in events if "time_sec" in e]
    latest_log=max(map(float,re.findall(rb"sim_sec=([0-9]+(?:\.[0-9]+)?)",log_bytes)),default=None)
    audits=[]
    for interval in ("900_1050","1200_1350","3300_3450"):
        path=ROOT/("diagnostics/source_interval_"+interval+".json")
        if not path.is_file():continue
        audit=load(path)
        if audit["run"]!=args.run:continue
        a,b=audit["interval_sec"]
        native=[r for r in removals if a<r["time_sec"]<=b]
        audits.append({"audit_path":rel(path),"audit_sha256":digest(path.read_bytes()),"interval_sec":[a,b],
                      "native_removals":native,"native_count_by_membership":dict(Counter(r["omega"] for r in native)),
                      "fzp_check_candidates":interval_check_candidates(removals,a,b),
                      "cached_unresolved_inside_disappearance_veh":audit["physical"]["totals"].get("unresolved_inside_disappearance_veh",0),
                      "cached_unresolved_links":audit["physical"]["unresolved_disappearance_links"],
                      "comparison_scope":"Native warning time/link aggregate; exact FZP ID join is separate."})
    samples=[]
    for audit in audits:
        eligible=[r for r in audit["native_removals"] if r["omega"]=="inside"]
        if eligible:samples.append(eligible[0])
    samples=(samples+removals)[:3] if len(samples)<3 else samples[:3]
    checks=None
    if args.fzp_checks:
        selected={(r["time_sec"],r["vehicle_id"],r["link"]):r for r in samples}
        for audit in audits:
            selected.update({(r["time_sec"],r["vehicle_id"],r["link"]):r for r in audit["fzp_check_candidates"]})
        fzps=list((run/"vissim_eval").glob("*.fzp"))
        if len(fzps)!=1:raise ValueError("One recorded FZP required")
        checks=check_removals(fzps[0],list(selected.values()),inside,terminals)
        for audit in audits:
            a,b=audit["interval_sec"]
            joined=[]
            for row in checks["checks"]:
                for event in row["disappearances"]:
                    if (a<event["upper_sec"]<=b and row.get("last_link_inside")
                            and row.get("last_link_matches_native") and not row.get("last_link_is_terminal")):
                        joined.append({"vehicle_id":row["vehicle_id"],"native_time_sec":row["native_time_sec"],**event})
            audit["exact_native_id_inside_nonterminal_disappearances"]=joined
            audit["exact_join_count"]=len(joined)
            audit["cached_unresolved_minus_known_native_count"]=audit["cached_unresolved_inside_disappearance_veh"]-len(joined)
            joined_links=Counter(r["last_vehicle"]["link"] for r in joined)
            if any(n>audit["cached_unresolved_links"].get(k,0) for k,n in joined_links.items()):
                raise ValueError("Joined removals exceed cached unknown count on a physical link")
    counts=Counter(r["omega"] for r in removals)
    capture={"schema":"native-runtime-error-capture/v1","mode":"complete" if args.complete else "prefix",
             "capture_time_utc":now.isoformat(),"run":args.run,"run_id":args.run_id,"run_created_at":provenance["created_at"],
             "run_provenance":{"path":rel(provenance_path),"sha256":digest(provenance_bytes)},
             "network":{"path":rel(network),"sha256":network_sha},
             "membership":{"path":rel(membership_path),"sha256":digest(membership_path.read_bytes())},
             "run_log":{"path":rel(log_path),"sha256_of_captured_bytes":digest(log_bytes),"bytes":len(log_bytes),"sim_done":done,"latest_logged_sim_sec":latest_log},
             "native_run_association":{"native_file_contains_run_id":False,
                 "runtime_mtime_not_before_run_created":runtime["mtime_ns_before"]/1e9>=created,
                 "first_warning_sim_sec":min(times,default=None),"last_warning_sim_sec":max(times,default=None),
                 "warning_time_not_beyond_latest_log":max(times,default=0)<=latest_log if latest_log is not None else None,
                 "limitation":"Network/run manifest and times support association, but native ERR has no embedded run ID. This is not a cryptographic native-run binding."},
             "files":files,"removal_count":len(removals),"removal_count_by_membership":dict(counts),
             "unfinished_vehicle_inputs":[dict(e) for e in events if e["kind"]=="unfinished_vehicle_input"],
             "removal_count_by_link":dict(Counter(r["link"] for r in removals)),
             "removal_count_by_wait_sec":dict(Counter(str(r["wait_sec"]) for r in removals)),
             "removals_on_physical_input_link":sum(r["physical_input_source_link"] for r in removals),
             "input_link_scope":"A removal physically on an input link; this is not proof of that vehicle's generation source or entry history.",
             "terminal_inside_removal_count":sum(r["terminal_inside"] for r in removals),
             "repeated_removal_keys":[{"key":list(k),"count":v} for k,v in duplicates.items() if v>1],
             "removals":removals,"sample_keys":[[r["time_sec"],r["vehicle_id"]] for r in samples],
             "audited_intervals":audits,"bounded_fzp_checks":checks,
             "producer_sha256":digest(Path(__file__).read_bytes()),
             "complete_line_removal_parse_complete":not runtime["unparsed_removal_lines"],
             "complete_runtime_bytes":bool(args.complete and runtime["source_unchanged_during_read"] and runtime["partial_tail_bytes"]==0),
             "limitations":["A prefix omits unflushed/later native warnings; use complete capture after SIM_DONE.",
                "A locked empty DLL log is reported as unreadable, not asserted to be a captured empty file.",
                "Explicit lane-change removal is not an outward crossing. Interior loss already excluded from TD can reduce TTT and truncate congestion.",
                "No vehicle-ID blacklist is created. Earlier observed outward crossings by a later-removed vehicle remain valid TD; only the deletion disappearance is classified here.",
                "Terminal-road membership alone does not establish a counted terminal exit. Compare each removal's last position and next-frame absence with the measurement's endpoint reach criterion; the removal count above reports road membership only.",
                "No measurement or production code was changed; duplicate travel-time-section warnings are separate records, not vehicle removals."]}
    (directory/"capture.json").write_text(json.dumps(capture,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    with (directory/"removals.csv").open("w",encoding="utf-8",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(removals[0]) if removals else ["vehicle_id"]);writer.writeheader();writer.writerows(removals)
    lines=[f"# Native error {capture['mode']} capture",f"Run: {args.run}; run ID: {args.run_id}.",
           f"Explicit removals: {len(removals)}; Ω {dict(counts)}; inside terminal removals: {capture['terminal_inside_removal_count']}.",
           f"Runtime warning categories: {runtime['counts']}.",
           f"Raw runtime bytes: {runtime['bytes']}; complete-line prefix: {runtime['complete_line_prefix_bytes']}; partial tail: {runtime['partial_tail_bytes']}.",
           "", "| Interval | Native removals | Inside | Cached unknown | Exact ID join |","|---|---:|---:|---:|---:|"]
    for row in audits:
        lines.append(f"| {row['interval_sec']} | {len(row['native_removals'])} | {row['native_count_by_membership'].get('inside',0)} | {row['cached_unresolved_inside_disappearance_veh']} | {row.get('exact_join_count','not checked')} |")
    lines+=[""]+capture["limitations"]+[capture["native_run_association"]["limitation"]]
    (directory/"capture.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps({"output":rel(directory),"removals":len(removals),"membership":dict(counts),
                      "terminals":capture["terminal_inside_removal_count"],"runtime_counts":runtime["counts"],
                      "fzp_bytes_read":checks["bytes_read"] if checks else 0},ensure_ascii=False))


if __name__=="__main__": main()
