"""Measure sampled residence and observed exits of the verified physical area.

Example: python scripts/measure_control_area.py --run evaluation/runs/<name>
FZP sampling is not continuous observation: terminal departures are explicitly
inferred, interior disappearances are unresolved, and the final frame is censored.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.controllers.control_area_objective import MembershipError, physical_membership_from_ledger


@dataclass(frozen=True)
class Vehicle:
    link: str
    position_m: float
    speed_kph: float


@dataclass
class Frame:
    time_sec: float
    vehicles: dict[str, Vehicle]
    source: str = "fzp"


def number(value, label, *, signed=False):
    result = float(value)
    if not math.isfinite(result) or (result < 0 and not signed):
        raise ValueError(f"{label} must be finite and nonnegative: {value!r}")
    return result


def integer_id(value, label):
    val = number(value, label)
    if not val.is_integer():
        raise ValueError(f"{label} is not an integer: {value!r}")
    return str(int(val))


def read_fzp_frames(path: Path) -> Iterable[Frame]:
    """Stream complete timestamp groups; row order within a timestamp is arbitrary."""
    names, indexes, current = None, {}, None
    required = ("SIMSEC", "NO", "LANE\\LINK\\NO", "POS", "SPEED")
    with path.open(encoding="utf-8-sig", errors="replace") as file:
        for lineno, line in enumerate(file, 1):
            text = line.strip()
            if not text or text.startswith("*"):
                continue
            if text.startswith("$VEHICLE:"):
                if names is not None:
                    raise ValueError(f"Repeated FZP vehicle header at line {lineno}")
                names = [x.strip().upper() for x in text.split(":", 1)[1].split(";")]
                if len(names) != len(set(names)):
                    raise ValueError("Duplicate FZP header columns")
                for key in required:
                    if key not in names:
                        raise ValueError(f"Required FZP column missing: {key}")
                    indexes[key] = names.index(key)
                continue
            if text.startswith("$"):
                continue
            if names is None:
                raise ValueError(f"FZP data before header at line {lineno}")
            row = text.split(";")
            if len(row) != len(names):
                raise ValueError(f"FZP column count mismatch at line {lineno}")
            values = {k: row[i].strip() for k, i in indexes.items()}
            t = number(values["SIMSEC"], "SIMSEC")
            if current is not None and t < current.time_sec:
                raise ValueError(f"FZP timestamps decrease at line {lineno}")
            if current is None or t != current.time_sec:
                if current is not None:
                    yield current
                current = Frame(t, {})
            veh = integer_id(values["NO"], "vehicle number")
            if veh in current.vehicles:
                raise ValueError(f"Duplicate vehicle {veh} at t={t}")
            current.vehicles[veh] = Vehicle(integer_id(values["LANE\\LINK\\NO"], "link"),
                                            number(values["POS"], "position",signed=True),
                                            number(values["SPEED"], "speed"))
    if names is None or current is None:
        raise ValueError("FZP contains no vehicle snapshots")
    yield current


def state_frame(path: Path, expected_time: float, *, expected_run_id=None, expected_manifest_path=None) -> Frame:
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    provenance = raw.get("run_provenance", {})
    if expected_run_id is not None and provenance.get("run_id") != expected_run_id:
        raise ValueError("Final state belongs to a different run_id")
    if expected_manifest_path is not None:
        recorded = provenance.get("manifest_path")
        if not recorded or Path(recorded).resolve() != Path(expected_manifest_path).resolve():
            raise ValueError("Final state manifest differs from the validated run/network manifest")
    if abs(float(raw["sim_sec"]) - expected_time) > 1e-6:
        raise ValueError("Final state timestamp differs from requested end")
    envelope = raw.get("vehicle_records", {})
    records = envelope.get("records")
    if envelope.get("complete") is not True or not isinstance(records, list):
        raise ValueError("Final state requires complete per-vehicle records")
    for key in ("collection_count_before", "collection_count_after", "record_count"):
        if envelope.get(key) != len(records):
            raise ValueError(f"Final state {key} differs from record count")
    for key in ("capture_sim_sec_before", "capture_sim_sec_after"):
        if abs(float(envelope.get(key, -1)) - expected_time) > 1e-6:
            raise ValueError(f"Final state {key} not paused at requested end")
    if raw.get("total_vehicles") != len(records):
        raise ValueError("Final state total_vehicles differs from record count")
    vehicles = {}
    for r in records:
        no = integer_id(r["veh_no"], "vehicle number")
        if no in vehicles:
            raise ValueError(f"Duplicate final-state vehicle {no}")
        vehicles[no] = Vehicle(integer_id(r["link_no"], "link"), number(r["position_m"], "position",signed=True),
                               number(r["speed_kph"], "speed"))
    return Frame(expected_time, vehicles, "final_state")


def measure_frames(frames: Iterable[Frame], membership: dict[str, bool], terminal_lengths_m: dict[str, float],
                   *, start_sec=0.0, end_sec=5400.0, final_frame: Frame | None = None,
                   max_tail_extrap_sec=10.0, terminal_margin_m=10.0, terminal_acceleration_m_s2=3.0,
                   simulation_step_sec=1.0):
    """Account every observed stock change without converting unknown loss to TTD."""
    if start_sec != 0:
        raise ValueError("Only fresh-run start_sec=0 is supported; a later start needs an initial frame")
    end_sec = number(end_sec, "end_sec")
    max_tail_extrap_sec = number(max_tail_extrap_sec, "max_tail_extrap_sec")
    terminal_margin_m = number(terminal_margin_m, "terminal_margin_m")
    terminal_acceleration_m_s2 = number(terminal_acceleration_m_s2, "terminal_acceleration_m_s2")
    simulation_step_sec = number(simulation_step_sec, "simulation_step_sec")
    if simulation_step_sec <= 0:
        raise ValueError("simulation_step_sec must be positive")
    prev = Frame(start_sec, {}, "assumed_initial_empty")
    cumulative = Counter()
    observed_exit_ids, terminal_exit_ids, all_seen = set(), set(), set()
    exit_pairs, unknown_links, terminal_links, reappeared_ids = Counter(), Counter(), Counter(), set()
    first_time, last_fzp, periods, record_count = None, None, [], 0
    left, right, trapezoid, max_abs_closure = 0.0, 0.0, 0.0, 0
    link_ttt, link_slow_ttt = Counter(), Counter()
    rows = []

    def inside(v):
        if v.link not in membership:
            raise MembershipError(f"Observed physical link missing from area ledger: {v.link}")
        return membership[v.link]

    def consume(frame, *, transitions=True):
        nonlocal prev, left, right, trapezoid, max_abs_closure
        dt = frame.time_sec - prev.time_sec
        if dt <= 0:
            raise ValueError("Measurement frames must have strictly increasing timestamps")
        before = {no for no, v in prev.vehicles.items() if inside(v)}
        after = {no for no, v in frame.vehicles.items() if inside(v)}
        step = Counter()
        if transitions:
            contradicted = frame.vehicles.keys() & terminal_exit_ids
            if contradicted:
                # A verified dead-end terminal has no reentry path. Do not keep
                # a departure reward when later observations refute its basis.
                raise ValueError("Terminal disappearance inference contradicted by reappearing vehicle IDs: "
                                 + ", ".join(sorted(contradicted)[:10]))
            for no, old in prev.vehicles.items():
                if no in frame.vehicles:
                    new = frame.vehicles[no]
                    if inside(old) and not inside(new):
                        step['observed_exit_events'] += 1
                        observed_exit_ids.add(no)
                        exit_pairs[old.link+'->'+new.link] += 1
                    elif not inside(old) and inside(new):
                        step['observed_entry_events'] += 1
                elif inside(old):
                    # Absence at the next full snapshot, terminal membership, and
                    # physically reachable endpoint are evidence for inference.
                    length = terminal_lengths_m.get(old.link)
                    reach = old.speed_kph / 3.6 * dt + 0.5 * terminal_acceleration_m_s2 * dt * dt + terminal_margin_m
                    # This runner uses SimRes=1. Native records can retain a
                    # terminal link ID with Pos already past its geometric end
                    # by one integration step (verified in actual 2020 FZP).
                    # A static 10 m tolerance discarded 1,086 otherwise valid
                    # NC terminal departures. Bound overshoot by ONE simulator
                    # step, not the longer vehicle-record sampling interval.
                    overshoot = (old.speed_kph / 3.6 * simulation_step_sec
                                 + 0.5 * terminal_acceleration_m_s2 * simulation_step_sec**2
                                 + terminal_margin_m)
                    if length is not None and -overshoot <= length - old.position_m <= reach:
                        step['terminal_exit_inferred_events'] += 1
                        if old.position_m > length + terminal_margin_m:
                            step['terminal_overshoot_inferred_events'] += 1
                        terminal_exit_ids.add(no)
                        terminal_links[old.link] += 1
                    else:
                        step['unresolved_inside_disappearances'] += 1
                        unknown_links[old.link] += 1
            for no in frame.vehicles.keys() - prev.vehicles.keys():
                if inside(frame.vehicles[no]):
                    step['appeared_inside_events'] += 1
                    if no in all_seen:
                        step['reappeared_inside_events'] += 1
                        reappeared_ids.add(no)
            closure = len(after)-len(before)-step['observed_entry_events']-step['appeared_inside_events']+step['observed_exit_events']+step['terminal_exit_inferred_events']+step['unresolved_inside_disappearances']
            max_abs_closure = max(max_abs_closure, abs(closure))
            if closure:
                raise AssertionError(f"Observed stock ledger does not close at {frame.time_sec}: {closure}")
            cumulative.update(step)
            all_seen.update(frame.vehicles)
        else:
            closure = 0
        left += len(before)*dt/3600
        right += len(after)*dt/3600
        trapezoid += (len(before)+len(after))*0.5*dt/3600
        # The same timestamps/end treatment as area TTT, disaggregated for
        # locating congestion gains/losses. Never substitute density*speed.
        for endpoint in (prev, frame):
            counts = Counter(v.link for v in endpoint.vehicles.values())
            slow = Counter(v.link for v in endpoint.vehicles.values() if v.speed_kph < 5)
            for link, count in counts.items():
                link_ttt[link] += count * .5 * dt / 3600
            for link, count in slow.items():
                link_slow_ttt[link] += count * .5 * dt / 3600
        rows.append({'sim_sec':frame.time_sec,'source':frame.source,'interval_sec':dt,'network_vehicles':len(frame.vehicles),
                     'inside_vehicles':len(after),'outside_vehicles':len(frame.vehicles)-len(after),
                     'ttt_veh_h_cumulative':trapezoid,
                     **{k:step[k] for k in ('observed_exit_events','terminal_exit_inferred_events','unresolved_inside_disappearances','observed_entry_events','appeared_inside_events','reappeared_inside_events')},
                     'ttd_observed_plus_terminal_cumulative':cumulative['observed_exit_events']+cumulative['terminal_exit_inferred_events'],
                     'stock_closure_residual_veh':closure})
        prev = frame

    for frame in frames:
        if frame.time_sec < start_sec or frame.time_sec > end_sec:
            raise ValueError("FZP contains snapshots outside requested run bounds")
        if frame.time_sec == start_sec:
            if frame.vehicles:
                raise ValueError("Nonempty initial state contradicts fresh empty-run assumption")
            continue
        if first_time is None:
            first_time = frame.time_sec
        if last_fzp is not None:
            periods.append(frame.time_sec-last_fzp)
        last_fzp = frame.time_sec
        record_count += len(frame.vehicles)
        consume(frame)
    if first_time is None:
        raise ValueError("No FZP snapshots after the initial boundary")
    if final_frame is not None:
        if final_frame.time_sec != end_sec:
            raise ValueError("Final frame must be at end_sec")
        if prev.time_sec == final_frame.time_sec:
            if {n:v.link for n,v in prev.vehicles.items()} != {n:v.link for n,v in final_frame.vehicles.items()}:
                raise ValueError("Final FZP and full state disagree on vehicle IDs/links")
        else:
            consume(final_frame)
    observed_through = prev.time_sec
    observed_ttt = trapezoid
    tail_sec = max(0.0,end_sec-prev.time_sec)
    tail_inside = sum(inside(v) for v in prev.vehicles.values())
    tail_extrap = None
    if 0 < tail_sec <= max_tail_extrap_sec:
        tail_extrap = tail_inside*tail_sec/3600
        consume(Frame(end_sec,dict(prev.vehicles),'censored_hold_extrapolation'),transitions=False)
    elif tail_sec == 0:
        tail_extrap = 0.0
    counted_exit_ids = observed_exit_ids | terminal_exit_ids
    events = cumulative['observed_exit_events']+cumulative['terminal_exit_inferred_events']
    nominal_period = statistics.median(periods) if periods else None
    max_period = max(periods) if periods else None
    missing_snapshot_gaps = sum(x > nominal_period*1.5 for x in periods) if nominal_period else 0
    result = {
        'schema':'control-area-measurement/v1','precision':'sampled; boundary transitions observed, terminal departures inferred',
        'ttt_veh_h':trapezoid if tail_extrap is not None else None,
        'ttt_observed_through_last_frame_veh_h':observed_ttt,'ttt_censored_tail_extrapolation_veh_h':tail_extrap,
        'ttt_left_rule_veh_h':left,'ttt_right_rule_veh_h':right,
        'ttt_integration_rule':'trapezoid in actual timestamp space; left/right are integration choices, not statistical confidence bounds',
        'physical_link_residence': {link: {'inside': membership[link], 'ttt_veh_h': value,
                                   'slow_veh_h': link_slow_ttt[link]} for link, value in sorted(link_ttt.items())},
        'slow_threshold_kph': 5.0,
        'ttd_observed_exit_events':cumulative['observed_exit_events'],
        'ttd_terminal_exit_inferred_events':cumulative['terminal_exit_inferred_events'],
        'ttd_terminal_overshoot_inferred_events':cumulative['terminal_overshoot_inferred_events'],
        'ttd_observed_plus_terminal_events':events,
        'ttd_observed_unique_vehicle_ids':len(observed_exit_ids),'ttd_counted_unique_vehicle_ids':len(counted_exit_ids),
        'ttd_repeat_exit_events':events-len(counted_exit_ids),
        'unresolved_inside_disappearances':cumulative['unresolved_inside_disappearances'],
        'observed_entry_events':cumulative['observed_entry_events'],'appeared_inside_events':cumulative['appeared_inside_events'],
        'reappeared_inside_events':cumulative['reappeared_inside_events'],'reappeared_inside_unique_ids':len(reappeared_ids),
        'censored_last_observed_inside_vehicles':tail_inside,
        'boundaries':{'start_sec':start_sec,'initial_state':'empty fresh network assumption','first_fzp_sec':first_time,
                      'last_fzp_sec':last_fzp,'observed_through_sec':observed_through,'requested_end_sec':end_sec,
                      'final_state_used':final_frame is not None,'unobserved_tail_sec':tail_sec,
                      'tail_method':'none' if tail_sec==0 else ('hold last stock; no inferred exit' if tail_extrap is not None else 'too long; full-run TTT unavailable')},
        'sampling':{'fzp_rows':record_count,'fzp_snapshots':len(periods)+1,'nominal_step_sec':nominal_period,'maximum_step_sec':max_period,'missing_snapshot_gaps':missing_snapshot_gaps},
        'closure':{'initial_inside_vehicles':0,'last_observed_inside_vehicles':tail_inside,'max_abs_residual_veh':max_abs_closure,
                   'equation':'N_after-N_before = observed_entry + appeared_inside - observed_exit - terminal_inferred - unresolved_inside_disappearance',
                   'warning':'This closes the sampled bookkeeping, not a proof that every between-sample physical crossing was observed.'},
        'exit_events_by_observed_link_pair':dict(exit_pairs.most_common()),'terminal_inferred_by_link':dict(terminal_links),
        'unresolved_inside_disappearances_by_link':dict(unknown_links.most_common()),
        'terminal_inference':{'terminal_lengths_m':terminal_lengths_m,'position_margin_m':terminal_margin_m,'maximum_assumed_acceleration_m_s2':terminal_acceleration_m_s2,
                              'simulation_step_sec':simulation_step_sec,
                              'rule':'absent next frame, last on verified terminal, reachable endpoint or bounded one-simulation-step position overshoot; no TMINNETTOT assumption'},
        'limitations':['An inside→outside→inside excursion completed between snapshots is not observed.',
                       'First appearances inside may be admitted vehicles or missed entrance transitions; reported separately.',
                       'Removal near a terminal is indistinguishable from normal departure with sampled records; terminal inference is separately reported.',
                       'The final observed vehicles are censored, never counted as exits just because the file ended.',
                       'No route inference is performed for skipped short connectors.'],
    }
    inside_sum = sum(row['ttt_veh_h'] for row in result['physical_link_residence'].values() if row['inside'])
    if not math.isclose(inside_sum, trapezoid, rel_tol=1e-10, abs_tol=1e-8):
        raise AssertionError(f"Physical link residence does not sum to area TTT: {inside_sum} vs {trapezoid}")
    return result, rows


def sha256(path):
    digest=hashlib.sha256()
    with path.open('rb') as file:
        for block in iter(lambda:file.read(1024*1024),b''):
            digest.update(block)
    return digest.hexdigest()


def terminal_lengths(document):
    targets={str(x) for x in document['terminal_inside_links']}
    result={}
    for item in document.get('sources',[]):
        if 'control_mapping_' not in item['path']: continue
        mapping=json.loads((ROOT/item['path']).read_text(encoding='utf-8-sig'))
        for row in mapping['freeway_model_links'].values():
            for link,length in zip(row['chain_links'],row['chain_lengths_m']):
                if str(link) in targets: result[str(link)]=number(length,'terminal length')
    if set(result)!=targets:
        raise ValueError(f"Missing verified terminal lengths: {targets-result.keys()}")
    return result


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run',type=Path,required=True)
    ap.add_argument('--fzp',type=Path)
    ap.add_argument('--membership',type=Path,default=ROOT/'diagnostics/control_area_membership.json')
    final_source = ap.add_mutually_exclusive_group()
    final_source.add_argument('--final-state',type=Path)
    final_source.add_argument('--fzp-only',action='store_true',
        help='Use the native recording phase only. A same-time COM snapshot may already have removed terminal vehicles.')
    ap.add_argument('--end-sec',type=float)
    ap.add_argument('--simulation-step-sec',type=float,default=1.0,
                    help='Runner SimRes=1 implies a 1-second integration step; independent of FZP sampling.')
    ap.add_argument('--out',type=Path)
    args=ap.parse_args(argv)
    run=args.run.resolve()
    led_path=args.membership.resolve()
    document=json.loads(led_path.read_text(encoding='utf-8-sig'))
    membership=physical_membership_from_ledger(document)
    for item in [document['network']]+document.get('sources',[]):
        path=ROOT/item['path']
        if sha256(path)!=item['sha256']:
            raise ValueError(f"Membership source changed: {path}")
    provenance=list(run.glob('run_provenance_*.json'))
    if len(provenance)!=1: raise ValueError('Expected exactly one run provenance file')
    manifest=json.loads(provenance[0].read_text(encoding='utf-8-sig'))
    if manifest['files']['network']['sha256']!=document['network']['sha256']:
        raise ValueError('Run network differs from membership network')
    end=args.end_sec if args.end_sec is not None else float(manifest['sim_period_sec'])
    files=[args.fzp] if args.fzp else list((run/'vissim_eval').glob('*.fzp'))
    if len(files)!=1: raise ValueError('Expected one FZP; specify --fzp explicitly')
    fzp=files[0].resolve()
    final_path=args.final_state
    if final_path is None and not args.fzp_only:
        candidates=list(run.glob(f'decisions*/state_{int(end):06d}.json'))
        if len(candidates)>1: raise ValueError('Multiple final states; specify --final-state')
        final_path=candidates[0] if candidates else None
    final=state_frame(final_path,end,expected_run_id=manifest['run_id'],expected_manifest_path=provenance[0]) if final_path else None
    metrics,rows=measure_frames(read_fzp_frames(fzp),membership,terminal_lengths(document),end_sec=end,final_frame=final,
                                simulation_step_sec=args.simulation_step_sec)
    metrics['observation_phase'] = ('native FZP only; vehicles present in the final record remain censored, including endpoint overshoots'
        if args.fzp_only else 'native FZP, supplemented by a validated later full COM snapshot when available')
    metrics['provenance']={'run':str(run),'run_id':manifest.get('run_id'),'seed':manifest.get('seed'),'controller':manifest.get('controller'),
                           'fzp':{'path':str(fzp),'sha256':sha256(fzp),'bytes':fzp.stat().st_size},
                           'membership':{'path':str(led_path),'sha256':sha256(led_path),'inside_links':sum(membership.values())},
                           'run_manifest':{'path':str(provenance[0]),'sha256':sha256(provenance[0])},
                           'measurement_script':{'path':str(Path(__file__).resolve()),'sha256':sha256(Path(__file__))},
                           'final_state':{'path':str(final_path),'sha256':sha256(final_path)} if final_path else None}
    output=(args.out or run/'analysis').resolve()
    output.mkdir(parents=True,exist_ok=True)
    with (output/'area_timeseries.csv').open('w',encoding='utf-8',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)
    (output/'area_metrics.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (output/'physical_link_residence.csv').open('w',encoding='utf-8',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=['physical_link','inside','ttt_veh_h','slow_veh_h'])
        writer.writeheader()
        writer.writerows({'physical_link': link, **row} for link, row in metrics['physical_link_residence'].items())
    print(json.dumps({k:metrics[k] for k in ['ttt_veh_h','ttd_observed_exit_events','ttd_terminal_exit_inferred_events','ttd_counted_unique_vehicle_ids','ttd_repeat_exit_events','unresolved_inside_disappearances','boundaries','sampling','closure']},ensure_ascii=False,indent=2))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
