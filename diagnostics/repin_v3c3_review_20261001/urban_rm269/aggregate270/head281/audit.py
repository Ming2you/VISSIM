"""Reuse native clock and past stopped-prefix evidence against the current model."""
import gzip, hashlib, importlib.util, json, pickle, sys
from pathlib import Path
import xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]; H=HERE.parent.parent; PREV=HERE.parent/'matched280/authority'
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
M='SC101_S_SC1_to_N_SC2005'
read=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def support():
    legacy=H/'service_ceiling/assessment.json'
    report=read(legacy)
    drift=[]
    for p,digest in report['source_pins'].items():
        if sha(p)!=digest:
            # audit.py pins this file only as historical provenance; its
            # queued-prefix estimator uses storedvehicleIDs/MER/signalclock.
            assert Path(p).resolve()==(ROOT/'evaluation/controllers/head_service_resources.py').resolve(),p
            drift.append(dict(path=p,recorded=digest,current=sha(p),role='historical observer implementation; not recomputing stored queued-prefix measurements'))
    spec=importlib.util.spec_from_file_location('legacy_prefix_math',H/'service_ceiling/candidate.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    value=module.paired_support(report,cutoff=2400)
    assert value['end_sec']==[1800,1950]
    netpath=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'
    tree=ET.parse(netpath)
    heads=[h for h in tree.findall('./signalHeads/signalHead') if h.get('no') in value['per_head_rate_veh_h']]
    assert len(heads)==3 and {h.get('sg') for h in heads}=={'101 8'}
    assert {h.get('lane') for h in heads}=={f'1220011503 {i}' for i in (1,2,3)}
    links={x.get('no'):x for x in tree.findall('./links/link')}
    direct=links['10538']; a,b=direct.find('fromLinkEndPt'),direct.find('toLinkEndPt')
    assert a.get('lane')=='1220011503 1' and len(direct.findall('./lanes/lane'))==3 and b.get('lane').split()[0]=='1220016101'
    for node in links.values():
        src=node.find('fromLinkEndPt')
        if src is None or node.get('no')=='10538' or src.get('lane').split()[0]!='1220011503':continue
        lanes=set(range(int(src.get('lane').split()[1]),int(src.get('lane').split()[1])+len(node.findall('./lanes/lane'))))
        assert not any(int(h.get('lane').split()[1]) in lanes and float(src.get('pos'))>=float(h.get('pos')) for h in heads)
    right=links['10528'].find('fromLinkEndPt')
    assert right.get('lane')=='1220011503 1' and float(right.get('pos'))<float(next(h for h in heads if h.get('lane').endswith(' 1')).get('pos'))
    return dict(support=value,legacy_source_drift=drift,pins={str(p):sha(p) for p in
        (legacy,H/'service_ceiling/candidate.py',H/'service_ceiling/audit.py',netpath,Path(__file__))})


def install(cfg):
    proof=read(HERE/'audit.json')
    assert all(sha(p)==v for p,v in proof['past_evidence']['pins'].items())
    net=cfg.network
    expected={'signal':'SC101','phase':'SC101_p1','origin':'SC1_to_SC101','receiving_link':'SC101_to_SC2005'}
    assert all(net.urban_movements[M][k]==v for k,v in expected.items())
    turns=net.control_area_routes['movement:'+M]['physical_turns']
    assert len(turns)==1 and turns[0]['connector']=='10538'
    assert M not in net.local_service_pool['group_of']
    assert expected['receiving_link'] in net.urban_link_storage_veh
    before=dict(net.movement_capacity_by_movement_veh_h)
    assert abs(before[M]-proof['baseline_rate'])<1e-7
    net.movement_capacity_by_movement_veh_h={**before,M:proof['past_evidence']['support']['rate_veh_h']}
    assert {k for k,v in before.items() if net.movement_capacity_by_movement_veh_h[k]!=v}=={M}
    return dict(before=before[M],after=net.movement_capacity_by_movement_veh_h[M],past_only_cutoff=2400,other_rates_unchanged=True)


def main():
    target=HERE/'audit.json';assert not target.exists()
    from evaluation.controllers import signal_actuation_contract as signals,vissim_stackelberg_adapter as adapter,sdmpc_sequence as seq
    from src.models.state import ControlAction
    cfg,state,forecast=pickle.loads((PREV/'initial.pickle').read_bytes())
    assert cfg.simulation.T_f_sec==5 and cfg.simulation.T_u_sec==10
    clock=read(H/'city_response/assessment.json')
    pins={str(p):sha(p) for p in (PREV/'summary.json',PREV/'initial.pickle',H/'city_response/assessment.json',Path(__file__))}
    rows=[]
    for arm in ('hold','selected'):
        response=read(PREV/(arm+'.json'))
        raw=json.loads(gzip.decompress((PREV/(arm+'.response.json.gz')).read_bytes()))
        rr={(x['resource'],x['start_sec'],x['kind']):x for x in raw['resource_allocations']
            if x['kind'] in ('urban_movement_stock','urban_movement_intended_limit')}
        for j,start in enumerate((2400,2550,2700)):
            path=H/'selection2400_discrete'/arm/f'action_{start:06}.json'
            action=seq.first_action(adapter.control_from_json(path,cfg,ControlAction));pins[str(path)]=sha(path)
            for group,phase,movements in [('SC101_S','p1',[M]),('SC6_S','p1',['SC6_S_SC12_to_N_SC103','SC6_S_SC12_to_E_SC104'])]:
                fractions=[signals.phase_fraction(action,cfg,cfg.network.urban_movements[movements[0]],t/10) for t in range(start,start+150,10)]
                prior=clock['arms'][arm][j]['phases'][group+'_'+phase]
                assert abs(sum(fractions)*10-prior['model_green_sec'])<1e-8
                binding=[]
                for m in movements:
                    counts=dict(green_steps=0,ready_limited=0,rate_limited=0,other_limited=0,receiver_rejected_veh=0.,accepted_veh=0.)
                    for t,g in zip(range(start,start+150,10),fractions):
                        q=rr[m,t,'urban_movement_stock']['available_veh']
                        x=rr[m,t,'urban_movement_intended_limit'];intent=x['available_veh'];accepted=x['accepted_total_veh']
                        counts['receiver_rejected_veh']+=intent-accepted;counts['accepted_veh']+=accepted
                        if g>0:
                            counts['green_steps']+=1;cap=cfg.network.movement_capacity_by_movement_veh_h[m]*g*10/3600
                            if abs(intent-q)<1e-7:counts['ready_limited']+=1
                            elif abs(intent-cap)<1e-7:counts['rate_limited']+=1
                            else:counts['other_limited']+=1
                    binding.append(dict(movement=m,**counts))
                rows.append(dict(arm=arm,start=start,group=group,phase=phase,actual=prior['native_head_veh'],model=sum(x['accepted_veh'] for x in binding),
                    native_green=prior['native_green_sec'],model_green=sum(fractions)*10,legacy_clock_mismatch_seconds=prior['clock_mismatch_seconds'],binding=binding))
    result=dict(status='current_binding_and_unchanged_phase_budget_confirmed',baseline_rate=cfg.network.movement_capacity_by_movement_veh_h[M],
        past_evidence=support(),rows=rows,pins=pins,new_predictions=0,new_native=0,
        interpretation='Revisit one previously measured bound only after upstream sharedsupply repair; no newratefit/grid. Native clock evidence reused,10s phaseexposure checked.',
        limitations=['Past achieved prefix support is not an unconditional future capacity.', 'Native persecond phase match comes from earlier immutable command audit,not a fresh simulator execution.', 'Whole gain still unqualified.'])
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print('RATE',result['baseline_rate'],result['past_evidence']['support']['rate_veh_h'])
    for r in rows: print(r['arm'],r['start'],r['group'],r['actual'],r['model'],r['binding'])


if __name__=='__main__':main()
