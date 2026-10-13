"""Compare the bounded candidate to cached matched native/previous responses."""
import gzip, hashlib, importlib.util, json, pickle, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]; H=HERE.parent.parent; BEFORE=HERE.parent/'matched280'
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
read=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    target=HERE/'review.json';assert not target.exists()
    old=read(BEFORE/'review.json');audit=read(HERE/'audit.json')
    result=read(HERE/'forecast2400/summary.json')
    assert result['status']=='complete' and result['forecasts']==2
    assert all(sha(p)==v for p,v in result['source_pins'].items())
    loader=importlib.util.spec_from_file_location('boundary_identity280',BEFORE/'review.py')
    previous=importlib.util.module_from_spec(loader);loader.loader.exec_module(previous)
    cfg,initial,_=pickle.loads((HERE/'forecast2400/initial.pickle').read_bytes())
    baseline=old['variants']['authority']; arms={};head_rows=[]
    for arm,v in result['results'].items():
        assert v['shared_constraints']['feasible'] and v['writer_three_blocks'] and v['conservation_states']==4
        raw=json.loads(gzip.decompress((HERE/f'forecast2400/{arm}.response.json.gz').read_bytes()))
        states=read(HERE/f'forecast2400/{arm}.stocks.json')
        boundary=previous.model_boundary(raw,states,v['omega_ttt_veh_h'],cfg)
        costs=v['costs_by_stock']; mainline=sum(x for k,x in costs.items() if k.startswith('freeway:'))
        arms[arm]=dict(omega=v['omega_ttt_veh_h'],mainline=mainline,nonmainline=v['omega_ttt_veh_h']-mainline,
            ramp10681=costs['ramp:RM_C10681'],merge10681=v['predicted_merge']['accepted_vehicles_by_ramp']['RM_C10681'],
            boundary=boundary,wall_sec=v['wall_sec'])
        for obs in audit['rows']:
            if obs['arm']!=arm:continue
            start=obs['start'];movements=[x['movement'] for x in obs['binding']]
            rows=[x for x in raw['resource_allocations'] if x['kind']=='urban_movement_intended_limit' and x['resource'] in movements and start<=x['start_sec']<start+150]
            value=sum(x['accepted_total_veh'] for x in rows)
            head_rows.append(dict(arm=arm,start=start,group=obs['group'],actual=obs['actual'],before=obs['model'],after=value,
                receiving_rejection=sum(x['available_veh']-x['accepted_total_veh'] for x in rows)))
    delta={k:arms['selected'][k]-arms['hold'][k] for k in ('omega','mainline','nonmainline','ramp10681','merge10681')}
    bc=baseline['delta_cost_veh_h']; before=dict(omega=bc['omega'],mainline=bc['mainline'],nonmainline=bc['omega']-bc['mainline'],ramp10681=bc['ramp10681'],merge10681=baseline['extra_merge10681'])
    nc=old['native_delta_cost_veh_h']; native=dict(omega=nc['omega'],mainline=nc['mainline'],nonmainline=nc['omega']-nc['mainline'],ramp10681=nc['ramp10681'],merge10681=old['actual_extra_merge10681'])
    route_delta={}
    for k in set(arms['hold']['boundary']['routes'])|set(arms['selected']['boundary']['routes']):
        a=arms['hold']['boundary']['routes'].get(k,{});b=arms['selected']['boundary']['routes'].get(k,{})
        route_delta[k]={f:b.get(f,0)-a.get(f,0) for f in ('entered','departed','generated_inside','entry_cost','departure_cost','generation_cost')}
    gain=sum(v['entry_cost']+v['departure_cost']+v['generation_cost'] for v in route_delta.values())
    assert abs(gain-delta['omega'])<1e-7
    local={}
    for group in ('SC101_S','SC6_S'):
        rows=[r for r in head_rows if r['group']==group]
        local[group]={name:sum(abs(r[name]-r['actual']) for r in rows) for name in ('before','after')}
    report=dict(status='bounded_candidate_reviewed',native=native,before=before,after=delta,absolute=arms,
        head_rows=head_rows,head_absolute_error_sum=local,whole_gain_error_before=before['omega']-native['omega'],
        whole_gain_error_after=delta['omega']-native['omega'],whole_gain_sign_matches=delta['omega']*native['omega']>0,
        boundary_delta_by_route=route_delta,new_forecasts=2,new_optimizations=0,new_native=0,new_fits=0,
        candidate_adopted=False,limitations=old['limitations']+['Only SC101 capacity differs. Past queued-prefix achieved rate is not an unconditional saturation rate. Native command pair jointly changes city signals and multipleRM.'],
        source_pins={str(p):sha(p) for p in (Path(__file__),HERE/'forecast2400/summary.json',HERE/'audit.json',BEFORE/'review.json',BEFORE/'review.py')})
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    for k in ('native','before','after','head_absolute_error_sum','whole_gain_error_before','whole_gain_error_after','whole_gain_sign_matches'): print(k,report[k])
    for r in head_rows:print('HEAD',r)


if __name__=='__main__':main()
