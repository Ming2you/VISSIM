"""One completed native FZP pass; cached local rows, no simulation or fitting."""
from collections import Counter, defaultdict
from pathlib import Path
import gzip
import hashlib
import json
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = Path('D:/VISSIM_runs/20260928_rm_observation2700_s47_v3/hold/vissim_eval/sdmpc31_g_2700_hold_s47_001.fzp')
LINKS = {10643, 10638, 70, 10776, 126, 10641, 71, 10700, 10640, 10634, 10635, 10642}
LOW, HIGH, CUTOFF = 2550., 3150.1, 2700.


def extract():
    target = HERE/'rows.json.gz'
    if target.exists():
        raise FileExistsError('Do not scan again; use the existing local cache')
    stat = SOURCE.stat()
    sha = hashlib.sha256()
    fields = None
    rows, times = [], Counter()
    all_rows = 0
    start = time.perf_counter()
    last_t = -1.
    with SOURCE.open('rb') as stream:
        for line in stream:
            sha.update(line)
            if line.startswith(b'$VEHICLE:'):
                fields = line.split(b':', 1)[1].strip().split(b';')
                assert fields[:5] == [b'SIMSEC', b'NO', b'LANE\\LINK\\NO', b'LANE\\INDEX', b'POS']
                ix = {x.decode('ascii'): i for i, x in enumerate(fields)}
                continue
            if not line[:1].isdigit():
                continue
            assert fields is not None
            all_rows += 1
            parts = line.split(b';', 3)
            t, vid, link = float(parts[0]), int(parts[1]), int(parts[2])
            assert t >= last_t
            last_t = t
            if not LOW <= t <= HIGH:
                continue
            times[t] += 1
            if link not in LINKS:
                continue
            values = line.rstrip(b'\r\n').split(b';')
            if values[-1] == b'' and len(values) == len(fields)+1:
                values.pop()
            assert len(values) == len(fields)
            def number(key):
                b = values[ix[key]]
                return float(b) if b else None
            rows.append([t, vid, link, int(values[3]), float(values[4]), number('SPEED'),
                number('ROUTDECNO'), number('ROUTENO'), values[ix['ROUTDECTYPE']].decode('ascii'),
                number('NEXTLINK\\NO'), number('DESTLANE'), values[ix['LNCHG']].decode('ascii'),
                values[ix['INTERACTSTATE']].decode('ascii'), number('LENGTH')])
    after = SOURCE.stat()
    assert (stat.st_size, stat.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
    epochs = sorted(times)
    cadence = Counter(round(b-a, 6) for a, b in zip(epochs, epochs[1:]))
    assert len(cadence) == 1, cadence
    assert len({(r[0], r[1]) for r in rows}) == len(rows)
    payload = dict(columns=['time','vehicle','link','lane','position','speed','decision','route',
                           'route_type','next_link','dest_lane','lane_change','interaction','length'],
        rows=rows, source=str(SOURCE), source_sha256=sha.hexdigest(), source_bytes=stat.st_size,
        source_mtime_ns=stat.st_mtime_ns, all_fzp_rows=all_rows, epochs=epochs,
        cadence_sec=dict(cadence), extraction_wall_sec=time.perf_counter()-start,
        information_cutoff_sec=CUTOFF, future_rows_usage='evaluation only; not autonomous forecast input')
    with gzip.open(target, 'wt', encoding='utf-8') as out:
        json.dump(payload, out)
    print('EXTRACT', len(rows), 'cadence', dict(cadence), 'wall', payload['extraction_wall_sec'], flush=True)
    return payload


def summarize(data):
    # Resolve the currently assigned path, never infer intention from future exit.
    from evaluation.controllers.physical_urban_transport import geometry
    contract = json.loads((HERE.parent/'unrouted10646/route_contract.json').read_text(encoding='utf-8'))
    network = ROOT/contract['network']['path']
    assert hashlib.sha256(network.read_bytes()).hexdigest() == contract['network']['sha256']
    routes, exits = geometry(network)

    def intent(r):
        if r[2] == 71 and r[9] in exits:
            return int(r[9])
        path = routes.get((r[6], r[7])) if r[8].lower() == 'static' else None
        if path and 71 in path:
            k = path.index(71)
            if k+1 < len(path) and path[k+1] in exits:
                return path[k+1]
        return None

    by_time = defaultdict(dict)
    for r in data['rows']:
        by_time[r[0]][r[1]] = r
    dt = float(next(iter(data['cadence_sec'])))
    result = {}
    for phase, lo, hi in [('past', LOW, CUTOFF), ('evaluation', CUTOFF, HIGH)]:
        exposure, events, entries, departures = Counter(), Counter(), Counter(), Counter()
        witnesses = []
        for a, b in zip(data['epochs'], data['epochs'][1:]):
            if a < lo or b > hi:
                continue
            assert abs((b-a)-dt) < 1e-6
            prev, now = by_time[a], by_time[b]
            for vid, r in prev.items():
                road, lane, target = r[2], r[3], intent(r)
                if road not in (126, 10641, 71):
                    continue
                exposure[(road, lane, target)] += dt
                n = now.get(vid)
                if n is None or n[2] != road or n[3] == lane:
                    continue
                required = exits[target]['lanes'] if target in exits and road == 71 else None
                kind = ('mandatory' if required and lane not in required else
                        'eligible_exchange' if required and n[3] in required else
                        'leaves_required_lane' if required else 'unresolved_or_upstream')
                events[(road, lane, n[3], target, kind)] += 1
                witnesses.append(dict(t0=a,t1=b,vehicle=vid,road=road,from_lane=lane,to_lane=n[3],
                    destination_before=target,destination_after=intent(n),kind=kind,
                    position_before=r[4],position_after=n[4],speed_before=r[5],speed_after=n[5],
                    route_before=r[6:9],route_after=n[6:9]))
            for vid, r in now.items():
                p = prev.get(vid)
                if r[2] in (126, 10641, 71) and (p is None or p[2] != r[2]):
                    entries[(p[2] if p else None,p[3] if p else None,r[2],r[3],intent(r))] += 1
                if p and p[2] == 71 and r[2] in exits:
                    departures[(p[3],r[2])] += 1
        result[phase] = dict(window=[lo,hi],exposure_left_rectangle_veh_s=[dict(road=k[0],lane=k[1],destination=k[2],value=n) for k,n in exposure.items()],
            events=[dict(road=k[0],from_lane=k[1],to_lane=k[2],destination=k[3],kind=k[4],count=n,
                         rate_per_veh_s=n/exposure[k[0],k[1],k[3]]) for k,n in events.items()],
            entries=[dict(from_road=k[0],from_lane=k[1],road=k[2],lane=k[3],destination=k[4],count=n) for k,n in entries.items()],
            observed_exit_pairs=[dict(lane=k[0],connector=k[1],count=n) for k,n in departures.items()],
            witnesses=witnesses)
    out = dict(status='COMPLETED_NATIVE_LOCAL_LANE_AUDIT',cases=result,
        source_sha256=data['source_sha256'],network_sha256=contract['network']['sha256'],
        rows_sha256=hashlib.sha256((HERE/'rows.json.gz').read_bytes()).hexdigest(),
        cadence_sec=dt,fit=0,forecasts=0,new_native=0,new_fzp_scan=1,
        previous_goal_turn='no_new_physics_evidence_report_only',
        limitations=['Same-road consecutive-sample net lane transitions only; intervening changes can be missed.',
          'Link/connector lane renumbering is not counted as a lane change.',
          'Sampled exit pairs undercount short connectors; not a replacement for MER/boundary balances.',
          'Past interval ends before controller cutoff; all later rows are evaluation only.',
          'No new lateral law, future-input fit or parameter update is qualified by this audit alone.'])
    (HERE/'audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for phase,r in result.items():
        print(phase, 'EVENTS', r['events'], flush=True)
        print(phase, 'EXITS', r['observed_exit_pairs'], flush=True)


if __name__ == '__main__':
    import sys
    if '--cached' in sys.argv:
        with gzip.open(HERE/'rows.json.gz','rt',encoding='utf-8') as f:
            data=json.load(f)
    else:
        data=extract()
    summarize(data)
