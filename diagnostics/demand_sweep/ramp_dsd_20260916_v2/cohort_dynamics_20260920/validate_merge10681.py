"""Compatibility receipt and diagnostic removal of only the10681 gap ceiling.

The relaxed instance is an identification bound, not a proposed merge model.
It retains nominal service, signals, storage and all vehicle/cost accounting.
"""
from pathlib import Path
import sys,json,hashlib,math,xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e,H,MODEL,CASES,ARMS
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.fit_response import parts
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.ramp_lane_coupling_check import audit

HERE=Path(__file__).resolve().parent


def main():
    out=HERE/'merge10681_conflict_v1/validation';out.mkdir(exist_ok=False)
    config=HERE/'merge10681_conflict_v1/evaluation/through_only.json'
    source=H/'state_response_20260919/native_s33_v1/source/network/baseline.inpx'
    network=ET.parse(source).getroot()
    proof=dict(network=str(source.relative_to(e.ROOT)),sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        simulation=network.find('simulation').attrib,
        areas=[dict(r.attrib) for r in network.find('conflictAreas') if {r.get('link1'),r.get('link2')}=={'2','10681'}],
        connector=next(dict(r.attrib) for r in network.find('links') if r.get('no')=='10681'),
        behavior=next(dict(r.attrib) for r in network.find('drivingBehaviors') if r.get('no')=='3'),
        references=['https://cgi.ptvgroup.com/vision-help/VISSIM_2020_ENG/Content/5_Netzbearbeiten/Konfliktflaechen_modellieren.htm',
                    'https://www.cgi.ptvgroup.com/vision-help/VISSIM_2020_ENG/Content/5_Netzbearbeiten/Konfliktflaechen_Attr.htm'],
        interpretation='PASSIVE does not impose conflict-area right of way. This does NOT remove car-following, lane-changing or finite receiving constraints. Model3/2s parameters are an effective approximation, not native priority settings.')
    assert proof['areas'] and all(r['status']=='PASSIVE' for r in proof['areas'])
    assert proof['simulation']['simRes']=='1'
    e.save(out/'network_evidence.json',proof)
    gap=e.load(HERE/'merge10681_gap_v1/result.json')
    pin_checks=0
    for protocol in (gap,e.load(HERE/'merge10681_conflict_v1/evaluation/protocol.json')):
        for file,pin in protocol['pins'].items():
            assert hashlib.sha256((e.ROOT/file).read_bytes()).hexdigest()==pin,file
            pin_checks+=1
    test=e.load(HERE/'merge10681_conflict_v1/tests.json');assert test['passed'] and test['tests']==127
    evaluation=e.load(HERE/'merge10681_conflict_v1/evaluation/result.json')
    assert evaluation['reference_json_exact']==12 and evaluation['lane_interface_checks']==2160
    checks=e.load(HERE/'merge10681_conflict_v1/evaluation/parameter_checks.json')
    assert all(r['returncode']==0 and 'PASS' in r['stdout'] for r in checks.values())
    params=e.load(HERE/'port_travel_fit_v1/selected_parameters.json')['parameters'];profile=e.load(MODEL/'port_profile.json')
    established=e.load(HERE/'open_speed_fit_v2/results.json')['baseline_state_scores']
    pins={str(p.relative_to(e.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
        [Path(__file__),config,e.CAL/'canonical_harness.py',e.ROOT/'evaluation/controllers/physical_lane_groups.py',
         e.ROOT/'evaluation/controllers/physical_ramp_boundary.py',HERE/'port_travel_fit_v1/selected_parameters.json',source]}
    e.save(out/'protocol.json',dict(pins=pins,fit_evaluations=0,new_native_runs=0,
        future_inputs=False,diagnostic_only=True,intervention='Remove only10681 Poisson gap ceiling; canonical total/lane stock/actuator limits remain. No capacity or reward fitted.',
        interpretation='Neither PASSIVE nor successful no-gap flow would validate unlimited merge access; compare components and state guards.'))
    exact=interfaces=0;result={};calls=0
    for seed,folder,bank,start in CASES:
        data=e.ObservationData(folder);lane=e.load(H/f'lane_group_response_20260919/observations_v1/s{seed}.json')
        origin=e.load(HERE/f'port_positions_v1/s{seed}.json');protocol=e.load(bank/'protocol.json');models={}
        for name,path in [('original',HERE/'port_origin_split_v1/config.json'),('relaxed',config)]:
            model=e.load_base_model(data.geometry,path);prior=model._config
            def configured(road,p,prior=prior):
                cfg=prior(road,p)
                if road=='FW_E':cfg.network.terminal_zero_gradient=True
                return cfg
            model._config=configured;models[name]=model
        model=models['relaxed'];module=sys.modules[type(model).__module__];normal=module.gap_acceptance_supply_vph
        target=model.ramp_receiving_nodes['RM_C10681'];signature=(target['critical_gap_sec'],target['followup_sec'])
        assert signature==(3.,2.)
        assert all((r['critical_gap_sec'],r['followup_sec'])!=signature for key,r in model.ramp_receiving_nodes.items() if key!='RM_C10681')
        def relaxed_gap(q,tc,tf):
            nonlocal calls
            if (tc,tf)==signature:calls+=1;return math.inf
            return normal(q,tc,tf)
        def simulate(model,t,command,relax=False):
            w=e.window(data,model,t,'history_forecast',profile,command,port_origin_counts=origin['counts'])
            w['lane_group_dynamics']={'FW_E':{**lane['geometry'],**lane['cutoffs'][str(t)],
                'initial_ramp_origin':origin['counts'][str(t)],'initial_off_eligible':origin['eligible_before_off'][str(t)]}}
            try:
                if relax:module.gap_acceptance_supply_vph=relaxed_gap
                return e.simulate(model,w,params)
            finally:module.gap_acceptance_supply_vph=normal
        guards={};costs={};lane_stats={}
        for t in (900,1650,2400,3600):
            p=simulate(model,t,lambda _: ({},{}),True);score=e.score_rollout(data,t,p,'FW_E')
            assert not score['invalid']
            guards[str(t)]=dict(score=score,ratio=score['objective']/established[str(seed)][str(t)]['objective'])
        for arm in ARMS:
            seq=protocol['candidate_bank'].get(arm,dict(green=[],vsl=[]))
            def command(t):
                i=int((t-start)//150)
                return ({'RM_C10490':seq['green'][i]} if seq['green'] else {},
                    {d:seq['vsl'][i] for d in protocol.get('dsd_ids',[59,60,61,62])} if seq['vsl'] else {})
            golden=e.load(HERE/f'terminal_probe_v1/prediction_s{seed}_open_outlet_{arm}.json')
            original=simulate(models['original'],start,command)
            assert json.loads(json.dumps(original))==golden,(seed,arm);exact+=1
            p=simulate(model,start,command,True)
            reference=e.load(HERE/f'merge10681_conflict_v1/evaluation/prediction_s{seed}_through_only_{arm}.json')
            interfaces+=audit(p,reference)['lane_interface_checks'];costs[arm]=parts(p)
            rows=[r for r in p['ramps'] if r['ramp']=='RM_C10681']
            lane_stats[arm]=[dict(ttt=sum(r['lane_receipts'][g]['connector_ttt_veh_h'] for r in rows),
                merges=sum(r['lane_receipts'][g]['accepted_merge_veh'] for r in rows),
                end_n=rows[-1]['lane_receipts'][g]['end']['connector_veh']) for g in (0,1)]
            e.save(out/f'prediction_relaxed_s{seed}_{arm}.json',p)
        delta={a:{k:v-costs['none'][k] for k,v in values.items()} for a,values in costs.items() if a!='none'}
        for d in delta.values():d['total']=sum(d.values())
        result[str(seed)]=dict(guards=guards,guards_passed=sum(x['ratio']<=1.1 for x in guards.values()),costs=costs,deltas=delta,lanes=lane_stats)
        print(seed,'exact',exact,'guards',result[str(seed)]['guards_passed'],'delta',delta,'NC lanes',lane_stats['none'],flush=True)
    assert calls==24*45*2,calls
    for file,pin in pins.items():assert hashlib.sha256((e.ROOT/file).read_bytes()).hexdigest()==pin
    e.save(out/'result.json',dict(status='VERIFICATION_PASS_GAIN_NOT_QUALIFIED',original_disabled_json_exact=exact,
        source_pin_checks=pin_checks,exact_native_merge_event_checks=gap['exact_merge_event_checks'],tests=test,
        prior_candidate_forecasts=evaluation['candidate_forecasts'],prior_lane_interface_checks=evaluation['lane_interface_checks'],
        diagnostic_gap_calls=calls,relaxed_lane_interface_checks=interfaces,results=result,
        qualified=False,production_adopted=False,new_native_runs=0,source_pins_verified=True))


if __name__=='__main__':main()
