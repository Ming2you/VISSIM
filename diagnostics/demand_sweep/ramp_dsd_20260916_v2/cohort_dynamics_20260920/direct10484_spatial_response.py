"""Matched-vehicle onset and spatial response, from completed native FZPs."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import direct10484_probe as d
from diagnostics.analyze_no_control_corridors import native_frames
from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.extract_observations import Observer
from collections import defaultdict
import time,argparse


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--seed',type=int,choices=[33],required=True,
        help='New paired repeat; historical seed23 output and exact source are preserved separately.')
    args=parser.parse_args();d.select_seed(args.seed)
    e,OUT,BASE,NC,START,END,check_pins,sha=d.e,d.OUT,d.BASE,d.NC,d.START,d.END,d.check_pins,d.sha
    check_pins()
    data = e.ObservationData(NC); observer = Observer(data.geometry)
    evidence = [{},{}]
    paths = [BASE/'run/vissim_eval/baseline_001.fzp', OUT/'rm10484/run/vissim_eval/baseline_001.fzp']
    streams = [native_frames(p, ev, deadline=time.monotonic()+600) for p,ev in zip(paths,evidence)]
    first = {}; cells = []; all_trace = []; first_by_link = {}
    for (t,nc),(tt,rm) in zip(*streams):
        assert t == tt
        if t < START:continue
        if t > END:break
        if t == START:
            assert nc == rm
            initial_ids=set(nc)
        moments = [defaultdict(lambda:[0,0.]),defaultdict(lambda:[0,0.])]
        changed = defaultdict(int); max_delta = defaultdict(float)
        for mode,frame in enumerate((nc,rm)):
            for vid,r in frame.items():
                loc = observer.locate(r)
                if loc:
                    key = (loc[0],loc[1]); moments[mode][key][0]+=1; moments[mode][key][1]+=r[3]
        # Changed generation can assign the same numeric ID to different later
        # vehicles. Only vehicles already present at intervention are matched.
        for vid in nc.keys() & rm.keys() & initial_ids:
            a,b=nc[vid],rm[vid]
            differs = a[:2]!=b[:2] or abs(a[2]-b[2])>=.05 or abs(a[3]-b[3])>=.05
            if not differs:continue
            first_by_link.setdefault(str(a[0]),dict(time_s=t,vehicle=vid,baseline=a,controlled=b))
            loc = observer.locate(a)
            if loc:
                key=f'{loc[0]}:{loc[1]}'
                changed[key]+=1;max_delta[key]=max(max_delta[key],abs(a[3]-b[3]))
                first.setdefault(key,dict(time_s=t,vehicle=vid,baseline=a,controlled=b,baseline_chain_pos_m=loc[2]))
        all_trace.append(dict(time_s=t,changed_initial_vehicles=dict(changed),max_speed_difference=dict(max_delta)))
        for key in moments[0].keys() | moments[1].keys():
            a,b=moments[0][key],moments[1][key]
            cells.append(dict(time_s=t,road=key[0],cell=key[1],baseline_n=a[0],controlled_n=b[0],
                baseline_v=a[1]/a[0] if a[0] else None,controlled_v=b[1]/b[0] if b[0] else None))
    costs={}
    for c in range(21):
        rows=[r for r in cells if r['road']=='FW_E' and r['cell']==c and START<r['time_s']<=END]
        assert len(rows)==450
        costs[str(c)]=sum(r['controlled_n']-r['baseline_n'] for r in rows)/3600
    expected=e.load(OUT/'review.json')['actual_delta']['mainline']
    assert abs(sum(costs.values())-expected)<1e-7
    e.save(OUT/'spatial_response.json',dict(first_initial_vehicle_difference=first,first_by_link=first_by_link,
        cell_delta_ttt_veh_h=costs,frames=all_trace,cell_states_1s=cells,
        observation_rule='Only identical IDs present at the exact paired intervention frame; all vehicles contribute to aggregate stocks/costs. Lane/link differs, or position/speed differs by at least0.05m/kmh. Earliest row per cell is not a causal propagation-speed estimate.',
        source_paths=list(map(str,paths)),partial_read_evidence=evidence,code_sha256=sha(Path(__file__))))
    print('FIRST_BY_CELL',first,flush=True)
    print('CELL_COST',costs,flush=True)
    check_pins()


if __name__=='__main__':main()
