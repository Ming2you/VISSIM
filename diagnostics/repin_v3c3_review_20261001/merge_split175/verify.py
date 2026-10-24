"""Independent saved-output balances, initial geometry, and state/gain checks."""
import ast
import gzip
import json
import math
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent


def main():
    assert not (HERE/'verification.json').exists()
    out=HERE/'forecast';protocol=h.read(HERE/'protocol.json')
    saved=h.read(out/'preservation.json');pins=dict(saved['input_sha256'])
    pins[str(Path(__file__))]=h.sha(__file__)
    def read(p):pins[str(p)]=h.sha(p);return h.read(p)
    assert read(out/'status.json')=={'status':'complete','forecasts':21}
    rows=read(out/'rows.json');mapping=read(h.F/'route_inventory/mapping31.json')['freeway_model_links']['FW_E']
    offsets=dict(zip(mapping['chain_links'],mapping['chain_offsets_m']))
    bounds=mapping['segment_bounds_m'];split=read(HERE/'spec.json')['merge_split_position_m']
    before=ast.parse((HERE/'driver_before.py.txt').read_text(encoding='utf-8'))
    current=ast.parse((h.R/'state_lateral168/run.py').read_text(encoding='utf-8'))
    getmain=lambda tree:ast.dump(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main'))
    assert getmain(before)==getmain(current)
    maxerr=0.;checks=0;maxcfl=0.;maxspeed=0.;maxsupply=-math.inf;porterr=0.;initial_checks=0
    comparison=[];predictions={};spatials={}
    for r in rows:
        key=r['case']+'_'+r['arm'];mode=r['version']
        pred=read(out/mode/(key+'.json.gz'));predictions[mode,key]=pred
        if mode=='unsplit173':
            old=read(h.R/'merge_target173/forecast/target_lanes'/(key+'.json.gz'))
            assert all(pred[k]==old[k] for k in ('cells','flows','ports','ramps'))
        for connector in ('10643','10682','10481','10483'):
            ps=[z for z in pred['ports'] if z['connector']==connector]
            for a,b in zip(ps,ps[1:]):
                # Cumulative counters must be differenced, never summed.
                error=b['n_veh']-a['n_veh']-(b['admitted_veh']-a['admitted_veh'])+(b['departed_veh']-a['departed_veh'])
                porterr=max(porterr,abs(error));assert abs(error)<1e-7
        ramps=[z for z in pred['ramps'] if z['ramp']=='RM_C10639']
        total_external=sum(z['duration_sec']*(z['start']['outside_component_backlog_veh']+z['end']['outside_component_backlog_veh'])/2/3600 for z in ramps)
        comparison.append(dict(case=r['case'],arm=r['arm'],mode=mode,
            actual_merge10639=r['actual']['merges']['RM_C10639'],predicted_merge10639=r['predicted']['merges']['RM_C10639'],
            ramp10639_internal_1s=sum(z['connector_ttt_veh_h'] for z in ramps),
            ramp10639_external_trapezoid_1s=total_external,
            end_posthead10639=ramps[-1]['end']['downstream_travelling_veh']+ramps[-1]['end']['merge_ready_veh']))
        if mode!='split175':continue
        spatial=read(out/mode/(key+'_spatial.json.gz'));spatials[key]=spatial
        initial=spatial['initial'];lengths=initial['lengths_km']
        raw=read(h.F/'route_inventory'/('initial_raw.json' if r['case']=='s29_late' else r['case']+'/initial_raw.json'))
        native=[[[] for _ in range(4)] for _ in range(2)]
        for z in raw['vehicle_records']['records']:
            if z['link_no'] not in offsets:continue
            x=offsets[z['link_no']]+z['position_m']
            if bounds[10]<=x<bounds[11]:native[int(x>=split)][z['lane_index']-1].append(z['speed_kph'])
        previous={}
        for part in (0,1):
            for lane in range(1,5):
                ns=native[part][lane-1];stock=sum(initial['stocks'][part][lane-1].values())
                assert abs(stock-len(ns))<1e-9
                if ns:assert abs(initial['speeds'][part][lane-1]-sum(ns)/len(ns))<1e-9
                previous[part,lane]=(stock,initial['speeds'][part][lane-1]);initial_checks+=1
        bytime={}
        for z in spatial['rows']:bytime.setdefault(z['time_s'],[]).append(z)
        joint={(z['time_s'],z['cell'],z['lane']):z for z in pred['diagnostics']['roads'][0]['joint_lane_region']['rows']}
        for t,zs in sorted(bytime.items()):
            assert len(zs)==8
            for z in zs:
                part,lane=z['part'],z['lane'];oldn,oldv=previous[part,lane]
                assert abs(z['n_before']-oldn)<1e-8
                error=z['n_veh']-oldn-z['incoming_veh']-z['merge_veh']+z['outgoing_veh']-z['lateral_veh']
                maxerr=max(maxerr,abs(error));assert abs(error)<1e-8
                assert abs(z['courant']-oldv/3600/lengths[part])<1e-10
                cfl=max(z['courant'],z['v_kmh']/3600/lengths[part]);assert cfl<=1.05
                maxcfl=max(maxcfl,cfl);maxspeed=max(maxspeed,z['v_kmh'])
                excess=z['incoming_veh']+z['merge_veh']-z['receiving_budget_veh']
                maxsupply=max(maxsupply,excess);assert excess<1e-8
                assert math.isfinite(z['v_kmh']) and z['n_veh']>=-1e-8
                previous[part,lane]=(z['n_veh'],z['v_kmh']);checks+=1
            for part in (0,1):
                # Independent check: lateral moves cannot create/remove stock.
                assert abs(sum(z['lateral_veh'] for z in zs if z['part']==part))<1e-8
            for lane in range(1,5):
                parts=[z for z in zs if z['lane']==lane];total=sum(z['n_veh'] for z in parts)
                assert abs(total-joint[t,10,lane]['n_veh'])<1e-8
                if total>1e-9:assert abs(sum(z['n_veh']*z['v_kmh'] for z in parts)/total-joint[t,10,lane]['v_kmh'])<1e-8
                assert abs(parts[0]['outgoing_veh']-parts[1]['incoming_veh'])<1e-9
                assert parts[0]['merge_veh']==0
    matched=[];first=[]
    for arm in ('release','release_vsl90'):
        key='s67_late_'+arm
        doc=read(h.F/'flow67'/(arm+'_frames.json.gz'));fields=doc['fields']
        frames={round(float(t),6):[dict(zip(fields,z)) for z in f.values()] for t,f in doc['frames'].items()}
        for mode in ('unsplit173','split175'):
            pred=predictions[mode,key]
            table={(round(z['time_s'],6),z['cell'],z['lane']):z for z in pred['diagnostics']['roads'][0]['joint_lane_region']['rows']}
            for lo,hi in ((2670.1,2675.1),(2670.1,2820.1),(2820.1,2970.1),(2970.1,3120.1)):
                for cell in (10,11):
                    for lane in (1,2):
                        ns=[];vs=[];actual_n=[];actual_v=[]
                        for t,frame in sorted(frames.items()):
                            if not lo+1e-6<t<=hi+1e-6:continue
                            obs=[v for v in frame if v['cell']==cell and v['lane']==lane]
                            m=table[t,cell,lane];ns.append(m['n_veh']-len(obs));actual_n.append(len(obs))
                            if obs:
                                v=sum(a['speed_kmh'] for a in obs)/len(obs);vs.append(m['v_kmh']-v);actual_v.append(v)
                        z=dict(arm=arm,mode=mode,lo=lo,hi=hi,cell=cell,lane=lane,
                            n_bias=sum(ns)/len(ns),v_bias=sum(vs)/len(vs),n_rmse=math.sqrt(sum(x*x for x in ns)/len(ns)),
                            v_rmse=math.sqrt(sum(x*x for x in vs)/len(vs)),actual_n=sum(actual_n)/len(actual_n),actual_v=sum(actual_v)/len(actual_v))
                        matched.append(z)
                        if hi-lo<6 and arm=='release' and cell==10 and lane==1:first.append(z)
    for p,d in {**pins,**protocol['protected_sha256'],protocol['STOP']['path']:protocol['STOP']['sha256']}.items():assert h.sha(p)==d,p
    h.save(HERE/'verification.json',dict(status='pass',spatial_rows_checked=checks,initial_part_lane_checks=initial_checks,
        max_local_mass_error=maxerr,max_port_counter_balance_error=porterr,max_shared_receiving_excess=maxsupply,
        max_courant=maxcfl,max_part_speed_kmh=maxspeed,baseline_tables_exact=10,main168_AST_unchanged=True,
        input_sha256=pins,protected_and_STOP_preserved=True,new_forecasts=0,new_native=0,
        gain_qualified=False,scope='Saved-output integrity and state comparison; not wholeOmega/8ramps/independent qualification.'))
    h.save(HERE/'ramp_comparison.json',comparison);h.save(HERE/'matched_states.json',matched)
    print('checks',checks,'initial',initial_checks,'mass',maxerr,'port',porterr,'maxCFL',maxcfl)
    print('first5',first)
    for z in matched:
        if z['arm']=='release' and z['lo']>2970 and z['cell']==10:print('late',z)


if __name__=='__main__':main()
