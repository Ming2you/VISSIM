"""No-fit test of the physical population used as pre-merge conflict flow."""
from pathlib import Path
import sys,json,hashlib,subprocess,statistics
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e,H,MODEL,CASES,ARMS
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.fit_response import parts
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.ramp_lane_coupling_check import audit

HERE=Path(__file__).resolve().parent


def main():
    out=HERE/'merge10681_conflict_v1/evaluation';out.mkdir(exist_ok=False)
    base=HERE/'ramp_exchange_v1/evaluation/config.json';paths={}
    for name in ('through_only','through_and_exchange'):
        cfg=e.load(base);cfg['freeway']['physical_ramp_conflict_through_inventory']=['RM_C10681']
        if name=='through_only':cfg['freeway'].pop('physical_ramp_lane_exchange')
        p=out/f'{name}.json';e.save(p,cfg);paths[name]=p
    params=e.load(HERE/'port_travel_fit_v1/selected_parameters.json')['parameters'];profile=e.load(MODEL/'port_profile.json')
    files=[Path(__file__),base,*paths.values(),HERE/'port_travel_fit_v1/selected_parameters.json',MODEL/'port_profile.json',
        e.CAL/'canonical_harness.py',e.ROOT/'evaluation/controllers/physical_lane_groups.py',e.ROOT/'evaluation/controllers/physical_ramp_boundary.py',
        H/'evaluate_response.py',HERE/'merge10681_conflict_v1/tests.json']
    pins={str(p.relative_to(e.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    e.save(out/'protocol.json',dict(pins=pins,new_native_runs=0,fit_evaluations=0,future_inputs=False,
        scope='Current predicted group stock minus same-merge origins and preceding exits; same speeds, gap law, capacities, actuator and objective. Test with/without previously unqualified stage exchange to avoid assuming its benefit.',
        guards='12 NC objectives <=1.10 established internal_cost. All states inspected development data; no fresh holdout.'))
    checks={}
    for name,p in paths.items():
        r=subprocess.run([sys.executable,'-B','-X','utf8',str(e.ROOT/'scripts/verify_parameters.py'),str(p)],cwd=e.ROOT,capture_output=True,encoding='utf-8')
        checks[name]=dict(returncode=r.returncode,stdout=r.stdout,stderr=r.stderr);assert r.returncode==0
    e.save(out/'parameter_checks.json',checks)
    established=e.load(HERE/'open_speed_fit_v2/results.json')['baseline_state_scores'];results={};exact=interfaces=0
    for seed,folder,bank,start in CASES:
        data=e.ObservationData(folder);lane=e.load(H/f'lane_group_response_20260919/observations_v1/s{seed}.json')
        origin=e.load(HERE/f'port_positions_v1/s{seed}.json');protocol=e.load(bank/'protocol.json');models={}
        for name,path in [('reference',base),*paths.items()]:
            model=e.load_base_model(data.geometry,path);prior=model._config
            def configured(road,p,prior=prior):
                cfg=prior(road,p)
                if road=='FW_E':cfg.network.terminal_zero_gradient=True
                return cfg
            model._config=configured;models[name]=model
        def window(model,t,command):
            w=e.window(data,model,t,'history_forecast',profile,command,port_origin_counts=origin['counts'])
            w['lane_group_dynamics']={'FW_E':{**lane['geometry'],**lane['cutoffs'][str(t)],
                'initial_ramp_origin':origin['counts'][str(t)],'initial_off_eligible':origin['eligible_before_off'][str(t)]}}
            return w
        result={}
        for name in paths:
            guards={};model=models[name]
            for t in (900,1650,2400,3600):
                p=e.simulate(model,window(model,t,lambda _: ({},{})),params)
                score=e.score_rollout(data,t,p,'FW_E');assert not score['invalid']
                guards[str(t)]=dict(score=score,ratio=score['objective']/established[str(seed)][str(t)]['objective'])
            result[name]=dict(guards=guards,guards_passed=sum(r['ratio']<=1.1 for r in guards.values()),costs={},lanes={})
        for arm in ARMS:
            seq=protocol['candidate_bank'].get(arm,dict(green=[],vsl=[]))
            def command(t):
                i=int((t-start)//150)
                return ({'RM_C10490':seq['green'][i]} if seq['green'] else {},
                    {d:seq['vsl'][i] for d in protocol.get('dsd_ids',[59,60,61,62])} if seq['vsl'] else {})
            reference=e.load(HERE/f'ramp_exchange_v1/evaluation/prediction_s{seed}_{arm}.json')
            p=e.simulate(models['reference'],window(models['reference'],start,command),params)
            assert json.loads(json.dumps(p))==reference;exact+=1
            for name in paths:
                model=models[name];p=e.simulate(model,window(model,start,command),params)
                interfaces+=audit(p,reference)['lane_interface_checks'];result[name]['costs'][arm]=parts(p)
                rows=[r for r in p['ramps'] if r['ramp']=='RM_C10681'];lanes=[]
                for g in (0,1):
                    rs=[r['lane_receipts'][g] for r in rows];flow=[r['receiving_node']['lane_conditions'][g] for r in rows]
                    for r in flow:
                        assert abs(r['total_group_stock_veh']-r['same_merge_origin_veh']-r['prior_exit_stock_veh']-r['conflicting_stock_veh'])<1e-7
                    lanes.append(dict(ttt=sum(r['connector_ttt_veh_h'] for r in rs),merges=sum(r['accepted_merge_veh'] for r in rs),
                        end_n=rs[-1]['end']['connector_veh'],conflict_vph=statistics.mean(r['conflicting_vph'] for r in flow),
                        mean_excluded_ramp=statistics.mean(r['same_merge_origin_veh'] for r in flow),
                        mean_excluded_exit=statistics.mean(r['prior_exit_stock_veh'] for r in flow)))
                result[name]['lanes'][arm]=lanes;e.save(out/f'prediction_s{seed}_{name}_{arm}.json',p)
        for name,row in result.items():
            costs=row['costs'];delta={a:{k:v-costs['none'][k] for k,v in values.items()} for a,values in costs.items() if a!='none'}
            for d in delta.values():d['total']=sum(d.values())
            row['deltas']=delta
            print(seed,name,'guards',row['guards_passed'],'delta',delta,'NC lanes',row['lanes']['none'],flush=True)
        results[str(seed)]=result
    for p,pin in pins.items():assert hashlib.sha256((e.ROOT/p).read_bytes()).hexdigest()==pin
    e.save(out/'result.json',dict(results=results,reference_json_exact=exact,lane_interface_checks=interfaces,
        candidate_forecasts=24,state_guard_forecasts=24,source_pins_verified=True,production_adopted=False,qualified=False))


if __name__=='__main__':main()
