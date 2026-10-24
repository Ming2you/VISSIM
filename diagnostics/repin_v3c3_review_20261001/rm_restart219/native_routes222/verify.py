"""Check bounded saved predictions and the current-route initialization."""
from pathlib import Path
import gzip
import hashlib
import json
import math

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
W='SC1004_N_SC1003_to_W';S='SC1004_N_SC1003_to_S';E='SC1004_N_SC1003_to_E_SC1005'
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    results={};mass=0.
    for name in ('baseline_v2','candidate'):
        folder=HERE/name;protocol=read(folder/'protocol.json')
        assert read(folder/'completion.json')['status']=='COMPLETE'
        for path,digest in protocol['inputs'].items():assert sha(Path(path))==digest
        stop=protocol['STOP'];assert sha(Path(stop['path']))==stop['sha256']
        for rel,digest in protocol['source_sha256'].items():
            p=ROOT/rel
            if p.name=='observation_projection.py':
                assert sha(HERE/'observation_projection.executed.py.txt')==digest
            else:assert sha(p)==digest,rel
        s=read(folder/'summary.json');parity=read(folder/'endpoint_parity.json')
        assert s['status']=='PASS' and len(parity['fields'])==93
        if name=='baseline_v2':assert parity['exact']
        rows=json.loads(gzip.decompress((folder/'receipts.json.gz').read_bytes()))
        assert len(rows)==1200
        for m,r in s['ramps'].items():
            selected=[x for x in rows if x['ramp']==m]
            a=math.fsum(x['after_finish']['cumulative_admitted_veh']-x['before']['cumulative_admitted_veh'] for x in selected)
            q=math.fsum(x['receipt']['accepted_merge_veh'] for x in selected)
            h=math.fsum(x['receipt']['head_service_veh'] for x in selected)
            assert all(abs(x-y)<1e-9 for x,y in ((a,r['predicted']['arrivals']),(q,r['predicted']['merge']),(h,r['predicted']['head'])))
            residual=r['initial']['connector_veh']+a-q-r['end']['connector_veh']
            mass=max(mass,abs(residual));assert abs(residual)<1e-9
        response=json.loads(gzip.decompress((folder/'response.json.gz').read_bytes()))
        assert response['model_constraint_coverage']['complete'] and response['conditional_model_feasibility_witness']
        assert not response['physical_native_fidelity_certificate']
        results[name]=dict(wall_sec=read(folder/'replayed_prediction.json')['wall_sec'],
            ramps={m:dict(predicted=r['predicted'],end=r['end']['connector_veh'],errors=r['errors']) for m,r in s['ramps'].items()})
    before=read(HERE/'baseline_v2/route_initial.json');after=read(HERE/'candidate/route_initial.json')
    assert after['queue']=={W:0.,S:1.,E:2.}
    assert sum(after['queue'].values())==sum(before['queue'].values())==3.
    assert before['source_stock']==after['source_stock']==4.5
    assert sum(sum(r.values()) for r in after['tags'].values())==4.
    assert all(set(r)=={W} for r in after['tags'].values())
    assert after['arrivals']==after['releases'] and after['arrivals']['915']==.5
    assert sum(after['arrivals'].values())==4.5
    meta=read(HERE/'candidate/runtime_metadata.json')['kinematic_arrivals']['SC1003_to_SC1004']
    assert meta['known_destination_veh']==7 and meta['before_choice_veh']==0
    # This last edit only namespaces metadata to retain earlier source proofs.
    old=(HERE/'observation_projection.executed.py.txt').read_text(encoding='utf-8')
    new=(ROOT/'evaluation/controllers/observation_projection.py').read_text(encoding='utf-8')
    a="metadata.update(configure_native_choice_groups(cfg, detectors,\n            {'urban': {'movements': {'physical_route_topology': native_path}}}, state_json=raw))"
    b="metadata.update({'kinematic_' + key: value for key, value in configure_native_choice_groups(cfg, detectors,\n            {'urban': {'movements': {'physical_route_topology': native_path}}}, state_json=raw).items()})"
    assert old.count(a)==1 and old.replace(a,b)==new
    tests=(HERE/'tests_final.log').read_text(encoding='utf-8-sig')
    assert 'Ran 23 tests' in tests and tests.rstrip().endswith('OK')
    output=dict(status='PASS_BOUNDED_INITIALIZATION_AND_REPLAY_NOT_GAIN_QUALIFICATION',
        predictions150=2,fit=0,optimizer=0,new_native=0,FZP=0,tests=23,
        prediction_wall_sec=sum(v['wall_sec'] for v in results.values()),max_mass_residual=mass,
        same_initial_ramp_inventory=all(read(HERE/'baseline_v2/summary.json')['ramps'][m]['initial']==read(HERE/'candidate/summary.json')['ramps'][m]['initial'] for m in results['candidate']['ramps']),
        initial_north_total_preserved=7.5,known46_destinations_preserved=7,
        unchanged_other_source_reservation=.5,results=results,
        current_metadata_namespace_only_change=True,executed_source_sha256=sha(HERE/'observation_projection.executed.py.txt'),
        current_source_sha256=sha(ROOT/'evaluation/controllers/observation_projection.py'),STOP_unchanged=True,
        limits=['First900 state only; no heldout congestion/seed, derivatives, candidate ordering or gain validation.',
                'Current destinations retained; unresolved observations beyond choice are explicit errors, not redrawn.',
                'Other physical supports, future generic link travel and capacities were not recalibrated.',
                'Candidate config is separate; frozen native9000 remains unchanged.'])
    (HERE/'verification.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in output.items() if k not in ('results','limits')}))

if __name__=='__main__':main()
