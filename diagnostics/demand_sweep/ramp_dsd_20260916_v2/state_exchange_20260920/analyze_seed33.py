"""Second-seed verification of the unchanged dispersion-only intervention."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.state_exchange_20260920.analyze_dispersion import (
    e,H,HERE,analyze,SpeedDistribution)


def main():
    out=HERE/'dispersion_seed33_analysis_v1';out.mkdir(exist_ok=False)
    bank=H/'state_response_20260919/native_s33_v1'
    geometry=e.ObservationData(bank/'observations/none').geometry
    paths={'none':bank/'run_none','actual100':bank/'run_vsl',
           'spread_only':HERE/'dispersion_seed33_v1/spread_only/run'}
    points=e.load(HERE/'dispersion_native_v1/protocol.json')['cases']['spread_only']['points']
    dist=SpeedDistribution(tuple((float(p['fx']),float(p['x'])) for p in points))
    results={}
    for name,run in paths.items():
        if name=='spread_only':
            execution=e.load(run/'run.json');validation=e.load(run/'fixed_validation.json')
            assert execution['completed'] and execution['seed']==33 and execution['terminal_sec']==3000 and validation['passed']
        result=analyze(run,geometry,dist if name=='spread_only' else None,
                       paths['actual100']/'vissim_eval/baseline_001.fzp' if name=='spread_only' else None)
        if name=='spread_only':
            assert result['precontrol_exact_rows']>1000000 and result['first_dsd_verified_crossings']>500
        else:
            arm='none' if name=='none' else 'vsl'
            known=e.load(H/'merge_drain_response_20260919/native_audit_v1/result.json')['33']['arms'][arm]['parts']['FW_E']
            for k,v in known.items():assert abs(result['parts'][k]-v)<1e-8
        results[name]=result;e.save(out/(name+'.json'),result)
        print('SEED33',name,result['parts'],flush=True)
    delta={name:{k:r['parts'][k]-results['none']['parts'][k] for k in r['parts']}
           for name,r in results.items() if name!='none'}
    e.save(out/'summary.json',{'seed':33,'results':results,'delta_vs_none_veh_h':delta,
        'scope':'450s FW_E+8connector component, not Omega; parameters not changed after seed23; one additional seed'})
    print('SEED33 DELTA',delta,flush=True)


if __name__=='__main__':main()
