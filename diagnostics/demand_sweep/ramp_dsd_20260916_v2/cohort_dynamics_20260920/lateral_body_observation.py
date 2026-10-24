"""Current lateral geometry of projected overlap; no collision/flow inference.

PosLat and nominal model width locate a lateral reference cross-section. Rear
coordinates/orientation are not recorded, so this is not a full-body polygon.
"""
from pathlib import Path
from collections import Counter, defaultdict
import hashlib
import json
import math
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import downstream_wave_audit as d

K,e=d.HERE,d.e
OUT=K/'lateral_body_observation_v1'
STARTS=(2280,2400,2550,2700)


def geometry(network):
    root=ET.parse(network).getroot();link=root.find('./links/link[@no="24"]')
    widths=[float(v.get('width')) for v in link.findall('./lanes/lane')]
    bt=root.find('./linkBehaviorTypes/linkBehaviorType[@no="'+link.get('linkBehavType')+'"]')
    behavior=root.find('./drivingBehaviors/drivingBehavior[@no="'+bt.get('drivBehavDef')+'"]')
    assert all(x.get('drivBehav')==bt.get('drivBehavDef') for x in bt.findall('./vehClassDrivBehav/vehClassDrivingBehavior'))
    models={x.get('no'):x for x in root.findall('./models2D3D/model2D3D')}
    distributions={x.get('no'):x for x in root.findall('./model2D3DDistributions/model2D3DDistribution')}
    by_length={}
    for vt in root.findall('./vehicleTypes/vehicleType'):
        if vt.get('category') not in ('CAR','HGV','BUS'):continue
        for el in distributions[vt.get('model2D3DDistr')].findall('./model2D3DDistrEl/model2D3DDistributionElement'):
            parts=models[el.get('model2D3D')].findall('./model2D3DSegs/model2D3DSegment')
            assert len(parts)==1 and float(parts[0].get('yawAngle'))==0
            p=parts[0];length=round(float(p.get('length')),3);width=float(p.get('width'))
            if length in by_length:assert by_length[length]==width
            by_length[length]=width
    return dict(lane_widths=widths,vehicle_width_by_length=by_length,
        behavior_number=int(behavior.get('no')),behavior={k:behavior.get(k) for k in
            ('obsrvAdjLn','rearCorr','rearCorrMaxSpeed','rearCorrStart','rearCorrEnd','lnChgRule','desLatPos')})


def observe(frame,geo):
    """One current frame only; keep unique mass apart from occupied lanes."""
    widths=geo['lane_widths'];bodies={}
    for vid,v in frame.items():
        lane=v['lane'];lat=v['poslat'];assert 1<=lane<=len(widths) and 0<=lat<=1
        width=geo['vehicle_width_by_length'][round(v['length'],3)]
        y=sum(widths[:lane-1])+lat*widths[lane-1];lo,hi=y-width/2,y+width/2
        occupied=[i+1 for i in range(len(widths)) if min(hi,sum(widths[:i+1]))>max(lo,sum(widths[:i]))]
        bodies[vid]=dict(**v,y_reference_m=y,width_m=width,lateral_interval=[lo,hi],reference_occupied_lanes=occupied)
    projected=[];neighbors=[]
    for lane in range(1,len(widths)+1):
        order=sorted((vid for vid,v in bodies.items() if v['lane']==lane),key=lambda vid:bodies[vid]['pos'])
        for back,front in zip(order,order[1:]):
            b,f=bodies[back],bodies[front];gap=f['pos']-f['length']-b['pos']
            if gap<0:
                lateral_overlap=min(b['lateral_interval'][1],f['lateral_interval'][1])-max(b['lateral_interval'][0],f['lateral_interval'][0])
                projected.append(dict(back=back,front=front,lane=lane,longitudinal_gap_m=gap,
                    reference_cross_section_overlap_m=lateral_overlap,reference_sections_separate=lateral_overlap<=0,
                    back_state=b,front_state=f))
    for vid,b in bodies.items():
        ahead=[(f['pos'],i) for i,f in bodies.items() if i!=vid and f['pos']>b['pos']]
        old=[(p,i) for p,i in ahead if bodies[i]['lane']==b['lane']]
        across=[(p,i) for p,i in ahead if min(b['lateral_interval'][1],bodies[i]['lateral_interval'][1])>
                max(b['lateral_interval'][0],bodies[i]['lateral_interval'][0])]
        original=min(old)[1] if old else None;lateral=min(across)[1] if across else None
        if b['target_type']=='Vehicle' and b['target'] in bodies:
            neighbors.append(dict(vehicle=vid,target=b['target'],current_lane=b['lane'],lane_change=b['lane_change'],
                old_leader=original,lateral_leader=lateral,old_matches_target=original==b['target'],
                lateral_matches_target=lateral==b['target']))
    return dict(unique_vehicle_count=len(bodies),reference_lane_occupancies=sum(len(v['reference_occupied_lanes']) for v in bodies.values()),
                bodies=bodies,projected_overlaps=projected,neighbor_comparison=neighbors)


def read_frames(path):
    stamp=(path.stat().st_size,path.stat().st_mtime_ns)
    wanted={t for start in STARTS for t in range(start-10,start+31)}
    frames={t:{} for t in sorted(wanted)};header=None
    with path.open('rb') as stream:
        for line in stream:
            if line.startswith(b'$VEHICLE:'):header=line.decode('ascii').strip()
            if not line[:1].isdigit():continue
            t=float(line.split(b';',1)[0])
            if t>max(wanted):break
            if t not in wanted:continue
            f=[x.strip() for x in line.rstrip(b'\r\n').split(b';')]
            if int(f[2])!=24:continue
            vid=int(f[1]);assert vid not in frames[int(t)]
            frames[int(t)][vid]=dict(vehicle=vid,lane=int(f[3]),pos=float(f[4]),poslat=float(f[5]),
                v=float(f[6]),length=float(f[10]),destination_lane=int(f[15]) if f[15] else None,
                lane_change=f[16].decode(),target_type=f[18].decode(),target=int(f[19]) if f[19] else None)
    assert header.split(';')[5]=='POSLAT' and header.split(';')[15]=='DESTLANE'
    assert all(frames.values()) and stamp==(path.stat().st_size,path.stat().st_mtime_ns)
    return frames,dict(path=path.relative_to(d.ROOT).as_posix(),size=stamp[0],mtime_ns=stamp[1],header=header,
        selected_frames=len(frames),selected_rows=sum(map(len,frames.values())),hash_policy='unchanged size/mtime of existing verified native FZP')


def main():
    OUT.mkdir(exist_ok=False)
    network=d.H/'source_dsd/baseline.inpx';geo=geometry(network)
    native=K/'route_state_native_v1/none_s23/run_retry1/vissim_eval/baseline_001.fzp'
    frames,receipt=read_frames(native);e.save(OUT/'frames.json',frames)
    current={t:observe(frame,geo) for t,frame in frames.items()}
    overlap_rows=[];summaries=[];snapshots={}
    for start in STARTS:
        counts=Counter();changed=[]
        for t in range(start,start+30):
            state=current[t];counts['unique_vehicle_seconds']+=state['unique_vehicle_count']
            counts['reference_occupancy_vehicle_seconds']+=state['reference_lane_occupancies']
            for row in state['projected_overlaps']:
                overlap_rows.append(dict(t=t,start=start,**row));counts['projected_overlap_pairs']+=1
                counts['reference_sections_separate']+=row['reference_sections_separate']
                counts['either_current_lane_change']+=any(row[k]['lane_change']!='None' for k in ('back_state','front_state'))
            for row in state['neighbor_comparison']:
                counts['observed_native_targets']+=1;counts['old_matches_target']+=row['old_matches_target']
                counts['lateral_matches_target']+=row['lateral_matches_target']
                counts['lateral_changes_candidate']+=row['old_leader']!=row['lateral_leader']
            for vid,b in state['bodies'].items():
                if b['lane_change']=='None':continue
                counts['active_lane_change_vehicle_seconds']+=1
                counts['destination_equals_reported_lane']+=b['destination_lane']==b['lane']
                counts['reference_spans_multiple_lanes']+=len(b['reference_occupied_lanes'])>1
                previous=current.get(t-1,{}).get('bodies',{}).get(vid)
                later=current[t+1]['bodies'].get(vid)
                changed.append(dict(t=t,vehicle=vid,lane=b['lane'],dest=b['destination_lane'],poslat=b['poslat'],
                    y=b['y_reference_m'],direction=b['lane_change'],previous_y=previous['y_reference_m'] if previous else None,
                    next_lane=later['lane'] if later else None,next_y=later['y_reference_m'] if later else None,
                    future_values_are_labels_only=True))
        summaries.append(dict(start=start,counts=dict(counts),active_transitions=changed))
        snapshots[start]=current[start]
    e.save(OUT/'snapshots.json',snapshots);e.save(OUT/'overlap_pairs.json',overlap_rows)
    files=[Path(__file__),network,OUT/'frames.json']
    e.save(OUT/'result.json',dict(qualified=False,new_native_runs=0,production_changes=0,geometry=geo,summaries=summaries,
        source_receipt=receipt,source_pins={p.relative_to(d.ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        references=['https://cgi.ptvgroup.com/vision-help/VISSIM_2020_ENG/Content/9_SimulationundTest/Simulation_Fz_im_Netz_anz.htm',
            'https://cgi.ptvgroup.com/vision-help/VISSIM_2020_ENG/Content/4_BasisdatenSim/FahrverhaltensparameterFahrstreifenwechsel_bearb.htm'],
        limitations=['Current reference cross-sections are not oriented full vehicle bodies.',
            'Nominal widths are uniquely matched from native model length; actual vehicle orientation/rear coordinates are unavailable.',
            'A native target reflects the previous internal simulation step; target agreement is a diagnostic, not ground-truth instantaneous leader accuracy.',
            'Occupied-lane counts are space exposure only, never additional vehicles or waiting cost.',
            'Future labels are stored separately from the current-frame observe function.',
            'No collision inference, closure/capacity law, autonomous prediction or gain qualification.']))
    print(json.dumps([dict(start=r['start'],counts=r['counts']) for r in summaries]))


if __name__=='__main__':main()
