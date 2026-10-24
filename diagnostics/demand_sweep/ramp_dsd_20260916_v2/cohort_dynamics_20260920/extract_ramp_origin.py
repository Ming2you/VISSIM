"""Current mainline stocks that entered at an on-ramp inside the same cell.

Only current positions plus past native ramp-departure IDs are used. No future
route, future exit or future state is used to tag the initial population.
"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e,H,CASES,MODEL
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.state_exchange_20260920.analyze_dispersion import records
from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.extract_observations import Observer
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.lane_group_response_20260919.extract import group
from collections import defaultdict
import argparse

HERE=Path(__file__).resolve().parent;LANE=H/'lane_group_response_20260919'
CUTOFFS=[900,1650,2400,3600]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--positions',action='store_true')
    parser.add_argument('--subcells',type=int,choices=[2])
    parser.add_argument('--output',type=Path,default=HERE/'ramp_origin_v1');args=parser.parse_args()
    cutoffs=sorted(set(CUTOFFS+[t-150 for t in CUTOFFS])) if args.positions else CUTOFFS
    out=args.output.resolve();out.mkdir(exist_ok=False)
    runs={13:H/'rules_4500_v1/run_none',23:H/'rules_4500_s23_v1/run_none',
          33:H/'state_response_20260919/native_s33_v1/run_none'}
    for seed,folder,bank,start in CASES:
        data=e.ObservationData(folder);model=e.load_base_model(data.geometry,MODEL/'config.json')
        observer=Observer(data.geometry);lane=e.load(LANE/f'observations_v1/s{seed}.json')
        east={str(p['connector']):(r,p) for r,p in model.ramps.items() if p['road']=='FW_E'}
        past={t:{} for t in cutoffs}
        for row in e.rows(folder/'port_events.csv'):
            if row['kind']!='departure' or str(row['connector']) not in east:continue
            sec=float(row['time_s']);vid=int(row['vehicle']);ramp,spec=east[str(row['connector'])]
            for t in cutoffs:
                if sec<=t and (vid not in past[t] or sec>past[t][vid][0]):past[t][vid]=(sec,ramp,spec['to_cell'])
        result={str(t):{r:[0.]*len(lane['geometry']['widths'][spec['to_cell']])
            for r,spec in east.values()} for t in cutoffs}
        offs={o:p for o,p in model.offramps.items() if p['road']=='FW_E'}
        eligible={str(t):{o:[0.]*len(lane['geometry']['widths'][p['from_cell']]) for o,p in offs.items()} for t in cutoffs}
        subcells={str(t):[[[{'n_veh':0.,'v_sum':0.} for w in ws] for half in range(args.subcells or 1)]
                         for ws in lane['geometry']['widths']] for t in cutoffs}
        counts={t:defaultdict(int) for t in cutoffs};found=set()
        path=runs[seed]/'vissim_eval/baseline_001.fzp';before=path.stat()
        for p in records(path):
            t=int(float(p[0]))
            if t>max(cutoffs):break
            if t not in past:continue
            loc=observer.locate((int(p[2]),int(p[3]),float(p[4]),float(p[6])))
            if not loc or loc[0]!='FW_E':continue
            g=group(loc[1],int(p[3]));counts[t][loc[1],g]+=1;found.add(t)
            if args.subcells:
                bounds=data.geometry['bounds']['FW_E'];c=loc[1]
                half=min(args.subcells-1,int((loc[2]-bounds[c])/(bounds[c+1]-bounds[c])*args.subcells))
                entry=subcells[str(t)][c][half][g];entry['n_veh']+=1;entry['v_sum']+=float(p[6])
            for off,spec in offs.items():
                if spec['from_cell']==loc[1] and loc[2]<=spec['chain_pos_m']:eligible[str(t)][off][g]+=1
            old=past[t].get(int(p[1]))
            if old is not None and old[2]==loc[1]:result[str(t)][old[1]][g]+=1
        assert found==set(cutoffs)
        for t in cutoffs:
            if t in CUTOFFS:
                for c,groups in enumerate(lane['cutoffs'][str(t)]['initial_groups']):
                    for g,row in enumerate(groups):assert counts[t][c,g]==row['n_veh']
            for row in data.cells[t]:
                if row['road']=='FW_E':assert sum(v for (c,g),v in counts[t].items() if c==row['cell'])==row['n_veh']
        after=path.stat();assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
        if args.subcells:
            for t in cutoffs:
                for c,halves in enumerate(subcells[str(t)]):
                    for half in halves:
                        for entry in half:
                            entry['v_kmh']=entry.pop('v_sum')/entry['n_veh'] if entry['n_veh'] else None
                            entry.pop('v_sum',None)
                    for g in range(len(halves[0])):
                        assert sum(half[g]['n_veh'] for half in halves)==counts[t][c,g]
        e.save(out/f's{seed}.json',{'counts':result,'source':str(path.relative_to(e.ROOT)),
            **({'eligible_before_off':eligible} if args.positions else {}),
            **({'subcell_initial_groups':subcells,'subcells_per_cell':args.subcells} if args.subcells else {}),
            'cutoff_causality':'Only departure records at/before current snapshot; current native positions',
            'existing_group_stocks_exact':True})
        print(seed,{t:{r:sum(ns) for r,ns in a.items()} for t,a in result.items()},flush=True)


if __name__=='__main__':main()
