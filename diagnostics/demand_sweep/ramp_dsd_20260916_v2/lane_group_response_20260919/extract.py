"""Cutoff-only lane-group stocks and preceding-150s exchange observations."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e, CASES, H
from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.extract_observations import Observer
from diagnostics.analyze_no_control_corridors import native_frames
from collections import defaultdict
import xml.etree.ElementTree as ET
import time
import argparse

HERE = Path(__file__).resolve().parent
CUTOFFS = [900, 1650, 2400, 3600]
SPLIT = set(range(5, 15))


def group(cell, lane, split_cells=SPLIT):
    return min(int(lane)-1, 2) if cell in split_cells else 0


def geometry_profile(geometry, split_cells=SPLIT):
    cells = [c for c in geometry['cells'] if c['road'] == 'FW_E']
    widths = [[1., 1., c['effective_lanes']-2.] if c['cell'] in split_cells
              else [c['effective_lanes']] for c in cells]
    root = ET.parse(H/'source_dsd/baseline.inpx').getroot()
    links = {int(l.get('no')): l for l in root.findall('.//links/link')}
    ports = {'ramp_access': {}, 'off_access': {}}
    for b in geometry['boundaries']:
        if b['road'] != 'FW_E' or b['kind'] not in ('ramp', 'offramp'): continue
        l = links[b['connector']]
        end = l.find('toLinkEndPt' if b['kind'] == 'ramp' else 'fromLinkEndPt')
        first = int(end.get('lane').split()[1])
        c = b['to_cell'] if b['kind'] == 'ramp' else b['from_cell']
        counts = [0.]*len(widths[c])
        for lane in range(first, first+b['lanes']): counts[group(c,lane,split_cells)] += 1.
        ports['ramp_access' if b['kind']=='ramp' else 'off_access'][
            b['id'] if b['kind']=='ramp' else str(b['connector'])] = {'cell': c, 'weights': counts}
    # Geometric lane continuation across the real 4 -> 3 lane drop.
    drop = links[10613]
    assert drop.find('fromLinkEndPt').get('lane') == '2 2'
    assert drop.find('toLinkEndPt').get('lane') == '119 1'
    assert len(drop.findall('./lanes/lane')) == 3
    matrices = []
    for i in range(20):
        a,b = len(widths[i]),len(widths[i+1])
        if i == 12: matrix = [[0.,0.,0.],[1.,0.,0.],[0.,.5,.5]]
        elif a == b: matrix = [[float(j==k) for k in range(b)] for j in range(a)]
        elif b == 1: matrix = [[1.] for _ in range(a)]
        elif a == 1: matrix = [[w/sum(widths[i+1]) for w in widths[i+1]]]
        else: raise ValueError('Unspecified lane-group transition')
        matrices.append(matrix)
    return {'schema':'physical-mainline-lane-groups/v1','road':'FW_E',
            'widths':widths,'matrices':matrices,**ports,
            'group_definition':('Cells5..14: lane1, lane2, lanes3+; all other cells aggregate' if split_cells==SPLIT
                                else 'Cells5..20: lane1, lane2, lanes3+; cells0..4 aggregate'),
            'geometry_source':str((H/'source_dsd/baseline.inpx').relative_to(e.ROOT))}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=HERE/'observations_v1')
    parser.add_argument('--downstream-lanes',action='store_true')
    args=parser.parse_args()
    out=args.output.resolve();out.mkdir(exist_ok=False)
    split_cells=set(range(5,21)) if args.downstream_lanes else SPLIT
    runs={13:H/'rules_4500_v1/run_none',23:H/'rules_4500_s23_v1/run_none',
          33:H/'state_response_20260919/native_s33_v1/run_none'}
    for seed,folder,_,_ in CASES:
        data=e.ObservationData(folder);observer=Observer(data.geometry)
        profile=geometry_profile(data.geometry,split_cells);saved={};evidence={};previous={}
        exposures={t:defaultdict(float) for t in CUTOFFS}
        exchanges={t:defaultdict(float) for t in CUTOFFS}
        for sec,frame in native_frames(runs[seed]/'vissim_eval/baseline_001.fzp',evidence,deadline=time.monotonic()+600):
            relevant=[t for t in CUTOFFS if t-150<sec<=t]
            if not relevant:
                previous={};continue
            located={}
            moments=defaultdict(lambda:[0.,0.])
            for vid,r in frame.items():
                loc=observer.locate(r)
                if not loc or loc[0]!='FW_E':continue
                c=loc[1];g=group(c,r[1],split_cells);located[vid]=(r[0],c,g)
                moments[c,g][0]+=1.;moments[c,g][1]+=r[3]
                for t in relevant:
                    exposures[t][c,g]+=1.
                    old=previous.get(vid)
                    # Cross-link lane-number remaps are geometry, not lane changes.
                    if old and old[:2]==(r[0],c) and old[2]!=g:
                        exchanges[t][c,old[2],g]+=1.
            if sec in CUTOFFS:
                rows=[];rates=[]
                for c,ws in enumerate(profile['widths']):
                    groups=[]
                    for g in range(len(ws)):
                        n,vs=moments[c,g]
                        groups.append({'n_veh':n,'v_kmh':vs/n if n else None})
                    observed=next(r for r in data.cells[sec] if r['road']=='FW_E' and r['cell']==c)
                    assert sum(r['n_veh'] for r in groups)==observed['n_veh']
                    if observed['n_veh']:
                        assert abs(sum(moments[c,g][1] for g in range(len(ws)))/observed['n_veh']-observed['v_kmh'])<1e-8
                    rows.append(groups)
                    rates.append([[exchanges[sec][c,g,k]/exposures[sec][c,g]
                                   if exposures[sec][c,g] else 0. for k in range(len(ws))]
                                  for g in range(len(ws))])
                saved[str(sec)]={'initial_groups':rows,'exchange_rates_per_sec':rates,
                                 'observation_end_s':sec,'history_start_s':sec-150}
            previous=located
        e.save(out/f's{seed}.json',{'geometry':profile,'cutoffs':saved})
        e.save(out/f'evidence_s{seed}.json',{'file':str((runs[seed]/'vissim_eval/baseline_001.fzp').relative_to(e.ROOT)),**evidence})
        print('EXTRACTED',seed,evidence['rows'],flush=True)


if __name__=='__main__':main()
