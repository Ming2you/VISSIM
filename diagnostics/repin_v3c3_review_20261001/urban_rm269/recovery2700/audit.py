"""Separate verified removal from local recovery, using closed obs150 records.

No native run, FZP scan, fit, or future input to the prediction.
"""
from pathlib import Path
from collections import Counter
import hashlib, json, sys

HERE = Path(__file__).resolve().parent
H = HERE.parent
ROOT = HERE.parents[3]
sys.path[:0] = [str(ROOT), str(H)]
from qualify_native2400 import validate_scope
from evaluation.controllers import obs150_contract as oc
RUNS = Path('E:/VISSIM_runs/20261008_urbanrm269_native2400_s29')
PINS = {}

def read(path):
    data = path.read_bytes()
    PINS[str(path)] = hashlib.sha256(data).hexdigest()
    return json.loads(data)

def main():
    assert not (HERE/'audit.json').exists()
    validate_scope(read(H/'native2400_analysis/summary.json'),
                   read(H/'native2400_analysis/observed_input_qualification.json'))
    arms = {}
    prior = read(H/'connector_attribution/assessment.json')
    for arm in ('hold', 'selected'):
        folder = RUNS/arm/f'decisions_sdmpc31_g_2400_{arm}_s29'
        frames, removals = {}, []
        for end in (2550, 2700, 2850):
            raw = read(folder/f'state_{end:06}.json')['obs150']
            for side in ('previous', 'current'):
                desc = raw['frames'][side]
                p = folder/desc['path']; f = read(p)
                assert PINS[str(p)] == desc['sha256'] and f['complete']
                frames[f['time_s']] = {int(v[0]): v for v in f['vehicles']}
            p = folder/raw['err']['chunk']; data = p.read_bytes()
            PINS[str(p)] = hashlib.sha256(data).hexdigest()
            assert PINS[str(p)] == raw['err']['chunk_sha256']
            rows = [json.loads(line) for line in data.splitlines()]
            removals.extend(oc.window_removals(rows, end-150, end))
        assert len({r['vehicle_id'] for r in removals}) == len(removals)
        canonical = read(H/f'native2400_analysis/{arm}/native_errors.json')
        expected = [r for r in canonical['unique_events'] if r['kind']=='lane_change_removal'
                    and 2400 <= r['time_sec'] < 2850]
        assert {r['raw_line_sha256'] for r in removals} == {r['raw_line_sha256'] for r in expected}
        road_removed = [r for r in removals if int(r['link']) == 68]
        witnesses = []
        for event in road_removed:
            vid = event['vehicle_id']
            seen = [(t,f[vid]) for t,f in frames.items() if t < event['time_sec'] and vid in f]
            t,v = max(seen, key=lambda item:item[0])
            witnesses.append(dict(vehicle_id=vid, deletion_sec=event['time_sec'],
                deletion_position_m=event['position_m'], wait_sec=event['wait_sec'],
                decision=event['route_decision'], route=event['route_index'],
                last_observed_sec=t, last_link=v[1], last_lane=v[2], last_position_m=v[3],
                last_speed_kph=v[4], current_route=[v[6],v[7]], raw_line_sha256=event['raw_line_sha256']))
        snapshots = []
        for t,f in sorted(frames.items()):
            by_lane = {}
            for lane in (1,2,3,4):
                vs = sorted((v for v in f.values() if v[1]==68 and v[2]==lane), key=lambda v:v[3])
                by_lane[str(lane)] = dict(count=len(vs), stopped=sum(v[4]<1 for v in vs),
                    route_counts=dict(Counter(str((v[6],v[7])) for v in vs)),
                    vehicles=[dict(id=int(v[0]),position_m=v[3],speed_kph=v[4],decision=v[6],route=v[7]) for v in vs])
            snapshots.append(dict(time_sec=t,lanes=by_lane))
        initial = frames[2400]
        identity_rows = []
        for vid,v in initial.items():
            if v[1]!=68 or v[2]<3: continue
            end = frames[2850].get(vid)
            deleted = next((r for r in road_removed if r['vehicle_id']==vid), None)
            # Location elsewhere proves a move, not necessarily normal network exit.
            elsewhere = [(t, f[vid][1], f[vid][2]) for t,f in sorted(frames.items())
                         if t>2400 and vid in f and f[vid][1]!=68]
            identity_rows.append(dict(vehicle_id=vid, initial_lane=v[2], initial_position_m=v[3],
                initial_decision=v[6],initial_route=v[7], removal_sec=deleted['time_sec'] if deleted else None,
                observed_elsewhere=elsewhere,
                final_link=end[1] if end else None,
                absence_without_location_or_removal=not end and not deleted and not elsewhere))
        blocks = []
        for j,start in enumerate((2400,2550,2700)):
            deaths = [r for r in road_removed if start<=r['time_sec']<start+150]
            blocks.append(dict(start_sec=start, removals68=len(deaths),
                removals_W_out=sum(int(r['link']) in {68,121,10772,10625,10629,10633}
                                  and start<=r['time_sec']<start+150 for r in removals),
                arrival10681=prior['arms'][arm][j]['native']['total_arrival'],
                initial_RM_disposition=prior['arms'][arm][j]['native']['initial_RM_disposition']))
        arms[arm] = dict(removed_total=len(removals),removed68=len(road_removed),
            direct_remaining_residence_ceiling_veh_h=sum((2850-r['time_sec'])/3600 for r in road_removed),
            deletion_witnesses=witnesses, snapshots=snapshots, initial_wrong_lane_history=identity_rows, blocks=blocks)
    assert arms['selected']['blocks'][-1]['removals_W_out'] == 0
    # A clean final W_out interval is useful as a same-command local diagnostic,
    # but these two arms have DIFFERENT2700 states: never subtract them as causal gain.
    source = read(H/'connector_lane/forecast2400/summary.json')['results']
    for arm in arms:
        arms[arm]['predicted_lane_endpoints'] = [dict(time_sec=2550+150*j,
            lanes={str(lane):sum(c['vehicles']*c.get('lane68',{}).get('shares',{}).get(str(lane),0.)
                                  for c in rows) for lane in range(1,5)})
            for j,rows in enumerate(source[arm]['known_endpoint_cohorts'])]
    PINS[str(Path(__file__))] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    report = dict(status='complete',arms=arms,source_pins=PINS,new_native=0,new_fzp_scans=0,new_fits=0,
        next_diagnostic=dict(arm='selected',start_sec=2700,end_sec=2850,max_predictions=1,
            meaning='Fresh observed initial state, executed commands, autonomous boundary forecast; no W_out deletion in target interval',
            controller_horizon_unchanged_sec=450,diagnostic_forecast_sec=150),
        limitations=['Removal is an explicit simulator sink, never a normal exit or physical lane-change success.',
            'The own-vehicle remaining-residence ceiling excludes induced delays and is NOT a corrected counterfactual TTT.',
            'Observed endpoint geometry is not a continuous trajectory or proof of instantaneous available gaps.',
            'Fewer deletions with selected control does not eliminate contamination of the held-selected recovery comparison.',
            'The2700 reinitialization is a diagnostic state from previously examined seed29, not independent heldout validation.',
            'No active network timeout, frozen queue, model coefficient or optimizer budget is changed.'])
    (HERE/'audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps({a:{k:r[k] for k in ('removed_total','removed68','direct_remaining_residence_ceiling_veh_h','blocks')} for a,r in arms.items()},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
