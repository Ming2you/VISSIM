"""Prepare, but do not dispatch, the user-authorized finite native queue."""
from pathlib import Path
import copy,hashlib,json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
RUNTIME=Path('E:/VISSIM_runtime/20261011_native348_vsl_three')
ANALYSIS=Path('E:/VISSIM_analysis/20261010_native348')
read=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    assert not RUNTIME.exists(),'Preserve any prior attempt'
    checks={}
    for key in ('window900_v3','optimized900_full_v1','window900_full_v1','optimized3300_response_v2','off900_v1','off7500_v2'):
        path=ANALYSIS/key/'completion.json';data=read(path)
        assert data['status']=='complete',key
        checks[key]=dict(path=str(path),sha256=sha(path),**data)
    parity=read(ANALYSIS/'optimized3300_response_v2/scalar_ad.json')
    assert parity['status']=='passed' and parity['objective_difference']<1e-8
    for key in ('optimized900_full_v1','window900_full_v1'):
        result=read(ANALYSIS/key/'unused.joint.json')
        assert result['completed'] and not result.get('error')
    configs={a:read(HERE/(a+'_config.json')) for a in ('window','optimized','off')}
    def plant(c):
        c=copy.deepcopy(c)
        for k in ('name','description'):c.pop(k,None)
        c['adapter'].pop('sdmpc_fixed_vsl',None)
        return c
    assert plant(configs['window'])==plant(configs['optimized'])==plant(configs['off'])
    plan=dict(schema='finite-vsl-three-comparison/v1',revision='native348',
        runtime_root=str(RUNTIME),order=['window','optimized','off'],max_native_runs=3,automatic_retries=0,
        status='validated_not_dispatched',conditions={},source_pins={},validation=checks,
        common=dict(seed=29,sim_period=8100,analysis_end_sec=8100,freeway_demand=.8,urban_demand=.9,
            area='Omega701',objective='Omega TTT',terminal_cost=False,horizon_sec=450,control_sec=150,
            freeway_exchange_sec=5,urban_exchange_sec=10,rm_min_green_sec=2,rm_delta_green_sec=2),
        limitations=['Historical seed29 service calibration is fixed; this native experiment is not held out.',
            'Large urban control gain-direction errors remain; native improvement is not pre-certified.',
            'Optimized VSL controls more zones than window VSL; not a timing-only comparison.',
            'Small projection failures retain previous control under the existing recorded error policy.'],
        validation_note='Optimized full900 preceded the copied-cfg guard repair; final3300 scalar/AD and finalwindow full900 include that repair. It changes only equal-document deep copies, not worker numeric equations.')
    for arm in plan['order']:
        config=HERE/(arm+'_config.json')
        output=Path('E:/VISSIM_runs')/('20261011_native348_'+arm+'_s29_8100')
        assert not output.exists(),output
        plan['conditions'][arm]=dict(config=config.relative_to(ROOT).as_posix(),sha256=sha(config),
            results_root=str(output),status='prepared',launches_consumed=0)
    paths=[ROOT/'evaluation/controllers'/name for name in ('runtime_setup.py','calibrated_urban_runtime.py',
        'vissim_stackelberg_adapter.py','aggregate_route_corridors.py','sdmpc.py','multirate_coupling.py','multirate_freeway.py')]
    paths += [ROOT/'evaluation/parameters.json',HERE/'calibration.json',ROOT/'tests/test_calibrated_urban_runtime.py']
    for item in read(ANALYSIS/'window900_full_v1/runtime_reads.json'):
        p=ROOT/item
        if p.suffix=='.py' and p.is_relative_to(ROOT/'diagnostics/repin_v3c3_review_20261001/urban_rm269'):
            paths.append(p)
    plan['source_pins']={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(set(paths))}
    old_queue=Path('E:/VISSIM_runtime/20261008_coupling268_vsl_three/run_queue.ps1')
    assert sha(old_queue)=='7fcdb7d3ef8deb48b7108cf670d122e74c4760711cece7d15e12823e0de0c896'
    plan['queue_script_sha256']=sha(old_queue)
    RUNTIME.mkdir()
    shutil.copyfile(old_queue,RUNTIME/'run_queue.ps1')
    blob=json.dumps(plan,indent=2,ensure_ascii=False,allow_nan=False)+'\n'
    (HERE/'plan.json').write_text(blob,encoding='utf8')
    (RUNTIME/'plan.json').write_text(blob,encoding='utf8')
    print('QUEUE_PREPARED',RUNTIME)

if __name__=='__main__':main()
