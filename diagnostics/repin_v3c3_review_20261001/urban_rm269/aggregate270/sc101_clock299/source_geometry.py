"""Locate SC101 side-entry transport mismatch using existing raw snapshots."""
import hashlib
import json
import pickle
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers.route_choice_corridor import _length,_validate_path,_travel_segments
from src.models import urban_queue_model as uqm


def geometry(root,cfg):
    path=root/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'
    data=path.read_bytes()
    tree=ET.fromstring(data)
    links={n.get('no'):n for n in tree.findall('./links/link')}
    heads=[h for h in tree.findall('./signalHeads/signalHead') if h.get('lane').split()[0]=='1220011503']
    assert {h.get('sg').split()[0] for h in heads}=={'101'}
    stop=min(float(h.get('pos')) for h in heads)
    sources={}
    for c in cfg.network.route_choice_corridor['corridors']:
        if c['decision'] not in ('1099','1100'):
            continue
        branch=c['branches']['1']
        assert branch['mode']=='free_storage' and branch['destination']=='SC1_to_SC101'
        assert branch['physical_target_link']=='1220008502'
        connector=branch['connector']
        paths=[[connector,'1220008502',con,'1220011503'] for con in ('10544','10545')]
        distances=[]
        for p in paths:
            _validate_path(p,links)
            segments=_travel_segments(p,links,{k:_length(links[k]) for k in p},stop)
            distances.append(sum(s['stop']-s['start'] for s in segments))
            for segment in segments:
                for h in tree.findall('./signalHeads/signalHead'):
                    if h.get('lane').split()[0]==segment['link'] and segment['start']<float(h.get('pos'))<segment['stop']-1e-6:
                        raise ValueError('Intermediate signal requires its own timing, not free travel')
        sources[c['decision']]=dict(source=c['prefix_storage'],connector=connector,
            target='SC1_to_SC101',paths=paths,distance_m=max(distances),distance_bounds_m=[min(distances),max(distances)],
            native_head=c['native_fixed_service']['head'],source_link=c['decision_link'],
            source_head_position_m=c['native_fixed_service']['head_position_m'])
    assert set(sources)=={'1099','1100'}
    lane_path=root/'outputs/storage_effective_lanes_20260904.json'
    lanes=json.loads(lane_path.read_bytes())['storage_effective_lanes']['SC1_to_SC101']
    return dict(sources=sources,lane_factor=lanes,network_path=str(path),network_sha256=hashlib.sha256(data).hexdigest(),
        lane_factor_path=str(lane_path),lane_factor_sha256=hashlib.sha256(lane_path.read_bytes()).hexdigest())


def main():
    assert not (HERE/'source_geometry.json').exists()
    p=HERE.parent/'citysplit287/forecast2400/initial.pickle'
    cfg,state,_=pickle.loads(p.read_bytes())
    result=geometry(ROOT,cfg)
    result['current_generic_delay_sec']=uqm._link_delay_steps(state,cfg,'SC1_to_SC101')*cfg.simulation.T_u_sec
    physical_speed=state.urban_link_speed_kph['SC1_to_SC101']/result['lane_factor']
    result['current_physical_mean_speed_kph']=physical_speed
    events=json.loads((HERE/'assessment.json').read_bytes())['native']
    raw=Path('E:/VISSIM_runs/20261008_urbanrm269_native2400_s29/hold/decisions_sdmpc31_g_2400_hold_s29/state_002400.json')
    initial=json.loads(raw.read_bytes())['vehicle_records']['records']
    initial={v['veh_no']:v for v in initial}
    for decision,d in result['sources'].items():
        d['constant_current_speed_travel_sec']=d['distance_m']/physical_speed*3.6
        d['initial_source_witnesses']={}
        for arm in ('hold','city'):
            witnessed=[]
            for event in events[arm]['events']:
                v=initial.get(event['veh'])
                if v and str(v['link_no'])==d['source_link']:
                    witnessed.append(dict(veh=event['veh'],head_sec=event['sec'],elapsed_sec=event['sec']-2400,
                        initial_position_m=v['position_m'],initial_speed_kph=v['speed_kph'],
                        initially_before_source_head=v['position_m']<=d['source_head_position_m']))
            d['initial_source_witnesses'][arm]=witnessed
    result.update(status='complete_current_geometry_and_initial_vehicle_witness',new_fzp_reads=0,new_predictions=0,
        source_pins={str(q):hashlib.sha256(q.read_bytes()).hexdigest() for q in (p,raw,HERE/'assessment.json',Path(__file__))},
        limitations=['Constant-current-speed travel is a geometry diagnostic, not a measured future arrival time.',
            'Native source-to-destination witnesses retain only vehicles crossing within the450s window.',
            'SC15 source heads are absent from the obs150 detector set, so exact departure times are unavailable.',
            'Future head identities diagnose the path only; predictive routing is unchanged.'])
    (HERE/'source_geometry.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('GEOMETRY',result['current_generic_delay_sec'],physical_speed)
    for key,d in result['sources'].items():
        print(key,d['distance_bounds_m'],d['constant_current_speed_travel_sec'],
            {a:[round(w['elapsed_sec'],2) for w in v] for a,v in d['initial_source_witnesses'].items()})


if __name__=='__main__':main()
