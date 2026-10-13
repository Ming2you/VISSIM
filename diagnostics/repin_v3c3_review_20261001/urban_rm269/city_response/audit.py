"""Closed two-arm clock/head audit; no new forecast or future model inputs."""
import ctypes, gzip, hashlib, importlib.util, json, sys
from collections import defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
H=HERE.parent
ROOT=HERE.parents[3]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine'),str(H)]
from evaluation.controllers import obs150_signal_clock as clock, signal_actuation_contract as signals
from qualify_native2400 import validate_scope
loader=importlib.util.spec_from_file_location('head_reader',H/'sc12_source/audit.py')
a=importlib.util.module_from_spec(loader);loader.loader.exec_module(a)
a.LINKS={'SC6_S':1210018302,'SC101_S':1220011503}
read=a.read

def tup(x):return tuple(tup(v) for v in x) if isinstance(x,list) else x

def clock_slots(control,network,sc,phase,start):
    c=network['signal_actuation_contract'];raw=c['nodes'][sc]
    payload=signals._native_payload(raw)
    values=tuple(control['green_times'][sc+'_'+p] for p in signals.PHASES)
    table=signals._phase_windows(tup(raw['_segments']),tup(raw['_order']),values,c['amber']+c['all_red'],payload,c['amber'])
    # Serial native basis is pinned; all four phases still share its150s cycle.
    assert raw['native_clock_basis']['kind']=='serial'
    cycle=raw['native_clock_basis']['cycle_sec']
    assert abs(sum(values)+4*(c['amber']+c['all_red'])-cycle)<1e-8
    lo,hi=table[phase];offset=control['offsets'][sc]
    return [signals._finite_fraction(cycle,offset,lo,hi,1.,t,t+1)>0 for t in range(start,start+150)]

def main():
    out=HERE/'assessment.json';assert not out.exists()
    kernel=ctypes.WinDLL('kernel32');kernel.GetCurrentProcess.restype=ctypes.c_void_p
    kernel.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_uint32]
    assert kernel.SetPriorityClass(kernel.GetCurrentProcess(),0x4000)
    validate_scope(read(H/'native2400_analysis/summary.json'),read(H/'native2400_analysis/observed_input_qualification.json'))
    network=read(H/'native_beta/forecast2400_checked/network.json')
    tree=ET.fromstring(a.pin(ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'))
    heads={h.get('no'):h.attrib for h in tree.findall('./signalHeads/signalHead')}
    phases={'SC6_S':{'p1':['SC6_S_SC12_to_N_SC103','SC6_S_SC12_to_E_SC104'],'p2':['SC6_S_SC12_to_W_SC5']},
            'SC101_S':{'p1':['SC101_S_SC1_to_N_SC2005'],'p2':['SC101_S_SC1_to_W_SC1002']}}
    # SC101 right connector leaves upstream of the actual straight head; its
    # model movement must not be counted as a native head crossing.
    conn=tree.find("./links/link[@no='10528']/fromLinkEndPt")
    assert conn.get('lane')=='1220011503 1' and float(conn.get('pos'))<float(heads['1010803']['pos'])
    origins={'SC6_S':'SC12_to_SC6','SC101_S':'SC1_to_SC101'}
    arms={}
    for arm in ('hold','selected'):
        folder=a.NATIVE/arm/f'decisions_sdmpc31_g_2400_{arm}_s29'
        response=json.loads(gzip.decompress(a.pin(H/'native_beta/forecast2400_checked'/(arm+'.response.json.gz'))))
        interests={m for g in phases.values() for ms in g.values() for m in ms}
        resource=defaultdict(dict)
        for r in response['resource_allocations']:
            if r['resource'] in interests and r['kind'] in ('urban_movement_stock','urban_movement_intended_limit'):
                resource[r['resource'],r['start_sec']][r['kind']]=r
        rows=[]
        for start in (2400,2550,2700):
            actual=read(folder/f'state_{start+150:06}.json')
            control=read(H/'selection2400_discrete'/arm/f'action_{start:06}.json')
            physical,_=a.heads_and_entries(folder,start+150)
            log=actual['obs150']['signal_log']
            scoped={**log,'scs':['6','101'],'start':{k:v for k,v in log['start'].items() if k.split('-')[0] in ('6','101')},
                    'events':[e for e in log['events'] if e[1] in ('6','101')]}
            assert all(v['owner']=='com' for v in scoped['start'].values())
            clocks=clock.windows(scoped,{},actual['obs150']['window'])
            phases_out={}
            for group,ph in phases.items():
                sc=group.split('_')[0];c=network['signal_actuation_contract']['nodes'][sc]
                for phase,movements in ph.items():
                    observed_heads=[h for h in physical[group]['rows'] if heads[h['head_id']]['sg'].split()[1] in c['phase_signal_groups'][phase]]
                    keys={heads[h['head_id']]['sg'].replace(' ','-') for h in observed_heads}
                    assert observed_heads and all(clocks[k]['complete'] for k in keys)
                    observed_slots={k:[any(lo<=t<hi for lo,hi in clocks[k]['green']) for t in range(start,start+150)] for k in keys}
                    assert all(v==next(iter(observed_slots.values())) for v in observed_slots.values())
                    native=next(iter(observed_slots.values()));model=clock_slots(control,network,sc,phase,start)
                    metrics={m:dict(requested=0.,accepted=0.,green_steps=0,green_empty_queue_steps=0,green_ready_exhausted_steps=0,
                        green_request_below_ready_steps=0,green_zero_request_with_ready_steps=0,receiver_rejection_veh=0.,
                        ready_veh_s=0.,service_ceiling_veh=0.) for m in movements}
                    for m in movements:
                        for t in range(start,start+150):
                            rr=resource[m,t];q=rr['urban_movement_stock']['available_veh']
                            intent=rr['urban_movement_intended_limit']['available_veh'];accepted=rr['urban_movement_intended_limit']['accepted_total_veh']
                            assert -1e-8<=accepted<=intent+1e-8 and intent<=q+1e-8
                            z=metrics[m];z['requested']+=intent;z['accepted']+=accepted;z['receiver_rejection_veh']+=intent-accepted
                            if model[t-start]:
                                z['green_steps']+=1;z['ready_veh_s']+=q
                                z['service_ceiling_veh']+=network['movement_capacity_by_movement_veh_h'][m]/3600
                                if q<=1e-8:z['green_empty_queue_steps']+=1
                                elif intent<=1e-8:z['green_zero_request_with_ready_steps']+=1
                                elif abs(intent-q)<=1e-8:z['green_ready_exhausted_steps']+=1
                                else:z['green_request_below_ready_steps']+=1
                    phases_out[group+'_'+phase]=dict(native_head_veh=sum(h['crossings'] for h in observed_heads),
                        model_head_veh=sum(z['accepted'] for z in metrics.values()),native_green_sec=sum(native),model_green_sec=sum(model),
                        clock_mismatch_seconds=[start+j for j,(n,m) in enumerate(zip(native,model)) if n!=m],heads=observed_heads,movements=metrics)
            transfers=[t for t in response['transfers'] if start<=t['start_sec']<start+150]
            sources={}
            for group,origin in origins.items():
                vals=defaultdict(float)
                for t in transfers:
                    if t['target']=='storage:'+origin and t['source']!=t['target']:vals[t['source'] or 'exogenous_boundary']+=t['vehicles']
                sources[group]=dict(vals)
            rows.append(dict(start_sec=start,phases=phases_out,model_origin_incoming=sources))
        arms[arm]=rows
        del response
    for p in (Path(__file__),ROOT/'evaluation/controllers/obs150_signal_clock.py',ROOT/'evaluation/controllers/signal_actuation_contract.py',
              H.parent/'upstream_worklog/02_urban_b2/diag_c3/C3_DIAGNOSIS.md'):
        a.pin(p)
    report=dict(status='complete',new_forecasts=0,new_native=0,fzp_scans=0,arms=arms,source_pins=a.PINS,
        limitations=['Exact clock comparison covers the two audited intersections and these three150s blocks, not every network signal.',
            'Ready_veh_s is queue exposure, not an independent vehicle count; positive request below ready does not uniquely identify every upstream request limiter.',
            'Model origin incoming excludes current ready stock; native head counts are discharge, not arrivals.',
            'SC101 pre-head right turn is excluded from the straight-head comparison.'])
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    for arm,rows in arms.items():
        for r in rows:
            print(arm,r['start_sec'],{k:dict(actual=v['native_head_veh'],model=round(v['model_head_veh'],2),green=(v['native_green_sec'],v['model_green_sec']),mismatch=len(v['clock_mismatch_seconds'])) for k,v in r['phases'].items()},flush=True)

if __name__=='__main__':main()
