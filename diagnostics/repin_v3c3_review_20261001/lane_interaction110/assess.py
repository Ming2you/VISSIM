"""Describe observed interactions without inferring an unobserved LC intention."""
from pathlib import Path
from collections import Counter, defaultdict
import csv
import gzip
import json
import xml.etree.ElementTree as ET

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]


def write(name, value):
    (OUT/name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def focus(r):
    return r and r['cell'] is not None and 16 <= r['cell'] <= 25


def target(r):
    return r['INTERACTTARGNO'] if r['INTERACTTARGTYPE'] == 'Vehicle' else None


def main():
    data = json.load(gzip.open(OUT/'frames.json.gz', 'rt', encoding='utf-8'))
    network = ET.parse(ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx').getroot()
    connectors = {}
    for link in network.findall('./links/link'):
        end = link.find('fromLinkEndPt')
        if end is not None:
            from_link, lane = map(int, end.get('lane').split())
            connectors[link.get('no')] = (from_link, lane, len(link.findall('./lanes/lane')), float(end.get('pos')))
    result, frame_table, event_rows, examples, overlap_rows = {}, [], [], {}, []
    exit_pos = connectors['10483'][3]
    for arm, case in data['cases'].items():
        counts, state_all, by_cell = Counter(), Counter(), defaultdict(Counter)
        unique, stop_vehicles = set(), set()
        last_lc, last_merge, seen_ramp = {}, {}, {}
        previous = {}
        frames = case['frames']
        # The initial common snapshot is compared below, not assumed.
        for frame in frames:
            t, rows = frame['t'], frame['rows']
            for vid, r in rows.items():
                old = previous.get(vid)
                current_lc = r['LNCHG'] in ('Left', 'Right')
                same_link_change = old and old['link'] == r['link'] and old['lane'] != r['lane']
                if current_lc or same_link_change:
                    last_lc[vid] = t
                if r['link'] in (10490,10484):
                    seen_ramp[vid] = r['link']
                if old and (old['link'], r['link']) in ((10490,119),(10484,24)):
                    last_merge[vid] = t
                if focus(r):
                    state_all[r['INTERACTSTATE']] += 1
                    counts['vehicle_samples'] += 1
                    unique.add(vid)
                    counts['current_lane_change_samples'] += int(current_lc)
                    counts['same_link_lane_change_intervals'] += int(bool(same_link_change))
            per_frame = Counter()
            for vid, r in rows.items():
                if not focus(r):
                    continue
                for threshold in (1, 5):
                    if r['speed'] < threshold:
                        counts[f'stopped_lt{threshold}_samples'] += 1
                        by_cell[r['cell']][f'lt{threshold}'] += 1
                        per_frame[f'lt{threshold}'] += 1
                if r['speed'] >= 5:
                    continue
                stop_vehicles.add(vid)
                # Descriptive geometric footprint, not proof of lost capacity.
                if r['link'] == 119 and r['lane'] == 1 and r['pos']-float(r['LENGTH']) <= exit_pos <= r['pos']:
                    counts['stopped_body_spans10483_branch_samples'] += 1
                    counts['through_stopped_body_spans10483_branch_samples'] += int(r['NEXTLINK\\NO'] == '10702')
                    overlap_rows.append({'case':arm,'time_sec':t,'vehicle':vid,**r})
                old = previous.get(vid)
                counts['same_link_stop_onsets'] += int(bool(old and old['link'] == r['link'] and old['speed'] >= 5))
                nxt = connectors.get(r['NEXTLINK\\NO'])
                if nxt and nxt[0] == r['link'] and not nxt[1] <= r['lane'] < nxt[1]+nxt[2]:
                    counts['stopped_outside_next_connector_lanes_samples'] += 1
                    if -2 <= nxt[3]-r['pos'] <= 20:
                        counts['stopped_wrong_lane_within20m_samples'] += 1
                chain, seen, cur = [], set(), vid
                reason = None
                while cur in rows and cur not in seen:
                    z = rows[cur]
                    seen.add(cur)
                    chain.append(cur)
                    if z['speed'] >= 5:
                        reason = 'first_vehicle_at_least5'
                        break
                    if target(z) is None:
                        reason = 'non_vehicle_target'
                        break
                    cur = target(z)
                if reason is None:
                    reason = 'cycle' if cur in seen else 'missing_target'
                counts['chain_' + reason] += 1
                followers = chain[1:]
                counts['chain_prior10s_lane_change_samples'] += int(any(t-last_lc.get(x, -100000) <= 10 for x in followers))
                counts['chain_prior10s_merge_samples'] += int(any(t-last_merge.get(x, -100000) <= 10 for x in followers))
                counts['chain_any_observed_ramp_origin_samples'] += int(any(x in seen_ramp for x in followers))
                direct = target(r)
                counts['direct_target_prior10s_lane_change_samples'] += int(direct is not None and t-last_lc.get(direct, -100000) <= 10)
                counts['direct_target_prior10s_merge_samples'] += int(direct is not None and t-last_merge.get(direct, -100000) <= 10)
                if t == 2940.1 and vid == '10917':
                    examples[arm+'_2940.1_chain10917'] = [{'vehicle': x, **rows[x]} for x in chain]
            frame_table.append({'case':arm, 'time_sec':t, 'stopped_lt1':per_frame['lt1'], 'stopped_lt5':per_frame['lt5']})
            for vid in ('19747','24572','24262','24796'):
                if 2900 <= t <= 2960 and vid in rows:
                    event_rows.append({'case':arm,'time_sec':t,'vehicle':vid,**rows[vid]})
            previous = rows
        counts['unique_vehicles'] = len(unique)
        counts['unique_ever_stopped_lt5_vehicles'] = len(stop_vehicles)
        result[arm] = {
            'counts':dict(counts),
            'mean_stopped_lt5_vehicles':counts['stopped_lt5_samples']/len(frames),
            'mean_stopped_lt1_vehicles':counts['stopped_lt1_samples']/len(frames),
            'interaction_state_all_samples':dict(state_all),
            'cell_mean_stopped_vehicles':{c:{k:v/len(frames) for k,v in cc.items()} for c,cc in sorted(by_cell.items())}}
        assert sum(cc.get('lt5',0) for cc in by_cell.values()) == counts['stopped_lt5_samples']
        assert sum(counts['chain_'+x] for x in ('first_vehicle_at_least5','non_vehicle_target','cycle','missing_target')) == counts['stopped_lt5_samples']
    a,b = [data['cases'][arm]['frames'][0]['rows'] for arm in ('release','release_vsl90')]
    initial = {arm:{k:v for k,v in rows.items() if focus(v)} for arm,rows in (('release',a),('release_vsl90',b))}
    result['initial_focus_snapshot_equal'] = initial['release'] == initial['release_vsl90']
    result['initial_focus_vehicle_counts'] = {arm:len(rows) for arm,rows in initial.items()}
    result['limitations'] = [
        '5s sampled means, not exact stopped durations or lane-change event totals.',
        'No DRIVSTATE/WAITING_FOR_LANE_CHANGE native attribute was recorded; LNCHG=None does not rule out an unfulfilled intention.',
        'A recent lane change or ramp-origin leader in an interaction chain is not proof it caused the queue.',
        'Chains stop at the first >=5km/h vehicle; they describe the stopped platoon front, not the ultimate downstream cause.',
        'Same-link changes miss intermediate changes and all within5s events that return to the original lane.',
        'One paired seed67 window with fixed RM release; cannot rank universal causal importance or validate gain prediction.'
    ]
    write('assessment.json',result)
    write('example_chains.json',examples)
    for name, rows in [('frame_counts.csv',frame_table),('example_tracks.csv',event_rows),('branch_overlap.csv',overlap_rows)]:
        with (OUT/name).open('w',encoding='utf-8-sig',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]))
            writer.writeheader();writer.writerows(rows)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
