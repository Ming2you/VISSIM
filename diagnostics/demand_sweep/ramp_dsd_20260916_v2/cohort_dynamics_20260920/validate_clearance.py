"""Validate rejected local-response probes without promoting their hypotheses."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.clearance_probe import *


def main():
    out=HERE/'clearance_validation_v1.json';assert not out.exists();checks={}
    for q in [0.,500.,1000.,2000.]:
        for v in [0.,5.,30.,100.]:
            base=min(1800.,gap_acceptance_supply_vph(q,2.5,2.5))
            assert supply(q,v,10,2.5,2.5,0.)==base
            assert supply(q,v,0,2.5,2.5,6.)==base
            assert 0<=supply(q,v,10,2.5,2.5,9.)<=supply(q,v,10,2.5,2.5,3.)<=base
    checks['clearance_limit_and_monotonic_cases']=16
    c={'start':0,'initial':[[10.,0.,1]],'length':10.,'speed':36.,'capacity':10.,
       'inputs':[{'head':0,'q':0.,'v':0.,'local_n':0} for _ in range(450)],
       'crossings':[-100.,550.],
       'observed':{'ttt':2.5/3600,'end_n':0,'exits':1,
          'trace':[{'n':int(t<2.5),'cumulative_exits':int(t>=2.5)} for t in range(1,451)]}}
    r=replay_gaps(c,(2.5,2.5),True)
    assert not r['overstorage'] and r['conservation_max']==0
    assert r['predicted']['exits']==1 and abs(r['predicted']['ttt']-2.5/3600)<1e-12
    c['initial']=[]
    r=replay_gaps(c,(2.5,2.5));assert r['predicted']=={'ttt':0.,'end_n':0.,'exits':0.}
    checks['event_queue_conservation_and_no_creation']=2
    training=prepare(13,'none',H/'controller_response_4500_v1/none',[900,1350,1800,2250,2700,3150,3600,4050])
    local50=prepare(13,'none',H/'controller_response_4500_v1/none',[900,1350,1800,2250,2700,3150,3600,4050],HERE/'clearance_local50_v1')
    exact=0;models=0
    for folder,runner,cases in [('clearance_conditional_v1',replay,training),
                               ('clearance_conditional_local50_v1',replay,local50),
                               ('gap_timing_conditional_v1',replay_gaps,training)]:
        saved=e.load(HERE/f'{folder}/training.json');best=min((r for r in saved['candidates'] if r['loss'] is not None),key=lambda r:r['loss'])
        assert best['parameters']==saved['selected']
        for c,expected in zip(cases,best['cases']):
            assert runner(c,best['parameters'])==expected;exact+=1
        for seed,row in e.load(HERE/f'{folder}/validation.json').items():
            for name,variant in row.items():
                for arm,result in variant['arms'].items():
                    assert not result['overstorage'] and result['conservation_max']<1e-7;models+=1
    checks['selected_training_case_exact_replays']=exact
    checks['validation_replays_with_finite_storage_and_conservation']=models
    # The narrow strip is a true subset of the original200m observation.
    contained=0
    for seed,arm in [(13,'none'),(23,'none'),(23,'rm_ramp'),(33,'none'),(33,'rm_ramp')]:
        small=e.rows(HERE/f'clearance_local50_v1/{seed}_{arm}/merge_lane_1s.csv')
        wide={r['time_s']:r for r in e.rows(LOCAL/f'{seed}_{arm}/merge_lane_1s.csv') if r['lane']=='1'}
        for r in small:
            w=wide[r['time_s']]
            for field in ['n','below5','below30']:assert int(r[field])<=int(w[field])
            assert float(r['speed_sum'])<=float(w['speed_sum'])+1e-7
            contained+=1
    checks['nested_local_observation_rows']=contained
    audit=e.load(HERE/'route71_readonly_v1.json')
    assert hashlib.sha256((e.ROOT/audit['source']).read_bytes()).hexdigest()==audit['source_sha256']
    assert len(audit['access'])==9 and len(audit['input69_conditional_demand'])==6
    for row in audit['input69_conditional_demand']:assert abs(sum(row['configured_destinations_vph'].values())-row['input_vph'])<1e-9
    checks['network_unchanged_and_configured_demand_conserved']=True
    files=[Path(__file__),HERE/'clearance_probe.py',HERE/'audit_71_routes.py',HERE/'rm_gap_summary_v1.json',HERE/'route71_readonly_v1.json']
    e.save(out,{'passed':True,'checks':checks,'qualification':'NOT_QUALIFIED; conditional probes rejected',
        'pins':{str(p.relative_to(e.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}})
    print(checks,flush=True)


if __name__=='__main__':main()
