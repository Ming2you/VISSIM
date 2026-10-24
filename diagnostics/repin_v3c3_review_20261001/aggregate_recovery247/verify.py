"""Check conditional247 equations independently in SI units and prior ledgers."""
import math
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent


def main():
    protocol=h.read(HERE/'protocol.json');rows=h.read(HERE/'rows.json')
    parameters=h.read(HERE/'parameters.json');completion=h.read(HERE/'completion.json')
    pins={**protocol['input_pins'],**protocol['protected_sha256'],protocol['STOP']['path']:protocol['STOP']['sha256']}
    assert all(h.sha(p)==v for p,v in pins.items())
    prior=h.read(h.F/'merge_population/rows.json')
    old={(r['arm'],r['time_s'],r['cell']):r for r in prior}
    total=0;prior_checks=0;maximum=0.;triggers=[]
    for row in rows:
        cell=row['cell'];p=parameters[str(cell)]['parameters'];spec=parameters[str(cell)]['response']
        assert abs(row['observed_mean_rate']-sum(row[k] for k in ('stayer_contribution','enter_contribution','leave_contribution')))<1e-10
        if row['case']=='s67_late' and row['arm']=='release':
            previous=old[row['arm'],row['time_s'],cell]
            assert row['n0']==previous['n_before'] and row['n1']==previous['n_after']
            assert abs(row['observed_mean_rate']-previous['observed_mean_rate'])<1e-10
            assert abs(row['stayer_contribution']-previous['parts']['stayer_acceleration'])<1e-10
            assert abs(row['leave_contribution']-previous['parts']['exiting_composition'])<1e-10
            prior_checks+=1
        for lanes,merges,data in [(3.,row['merges5'],row['aggregate'])]+[(1.,row['merges5'] if x['lane']==1 else 0,x['terms']) for x in row['lanes']]:
            if data is None:continue
            length_m=p['segment_length_km']*1000
            density_m=data['rho']/1000
            down_m=data['downstream_rho']/1000
            kappa_m=p['metanet_kappa_veh_km_lane']/1000
            v=data['v']/3.6;up=data['upstream_v']/3.6
            expected={
                'relaxation':3.6*((data['desired']/3.6-v)/data['tau_sec']),
                'convection':3.6*v*(up-v)/length_m,
                'anticipation':-3.6*(data['nu']*1e6/3600)*(down_m-density_m)/(data['tau_sec']*length_m*(density_m+kappa_m)),
                'merge_loss':3.6*spec.get('delta_merge',0.)*(merges/5)*v/(length_m*lanes*(density_m+kappa_m)),
            }
            expected['material_unclipped']=expected['relaxation']+expected['anticipation']-expected['merge_loss']
            expected['eulerian_unclipped']=expected['material_unclipped']+expected['convection']
            nominal=p['v_free']*math.exp(-(data['rho']/p['rho_crit'])**p['metanet_a_m']/p['metanet_a_m'])
            assert abs(nominal-data['desired'])<1e-9
            assert abs(data['n']-data['rho']*p['segment_length_km']*lanes)<1e-10
            for key,value in expected.items():
                error=abs(value-data[key]);maximum=max(maximum,error);assert error<1e-8,(cell,key,error)
            total+=1
        if row['lane_mean'] is not None:
            assert sum(x['terms']['n'] for x in row['lanes'])==row['n0']
            for key,value in row['lane_mean'].items():
                calculated=math.fsum(x['terms']['n']*x['terms'][key] for x in row['lanes'])/row['n0']
                assert abs(calculated-value)<1e-10
    assert len(rows)==1350 and total==completion['force_checks']==5380 and prior_checks==450
    for case,arm in sorted({(r['case'],r['arm']) for r in rows}):
        for cell in range(21,26):
            rr=[r for r in rows if (r['case'],r['arm'],r['cell'])==(case,arm,cell)]
            selected=[r for r in rr if r['current_mean_acceleration']>0 and r['aggregate']['desired']<r['aggregate']['v']]
            triggers.append(dict(case=case,arm=arm,cell=cell,samples=len(rr),
                positive_native_acceleration_but_negative_relaxation=len(selected),
                also_downstream_less_dense=sum(r['aggregate']['downstream_rho']<r['aggregate']['rho'] for r in selected)))
    h.save(HERE/'regimes.json',triggers)
    frozen=Path('E:/VISSIM_runtime/20261005_rm10681_reopen238/frozen/sdmpc31_26569d54_202610050857')
    runtime_pins={}
    for p in (Path(protocol['model_manifest']),Path(context_path(protocol,'reference_config')),Path(context_path(protocol,'parameters'))):
        rel=p.relative_to(h.ROOT);assert h.sha(p)==h.sha(frozen/rel)
        runtime_pins[str(rel)]=h.sha(p)
    result=dict(status='PASS',rows=1350,independent_SI_force_checks=total,max_force_error=maximum,
        prior_population_rows_exact=prior_checks,current_vs_frozen_reference_pins=runtime_pins,
        protected_sources_inputs_STOP_unchanged=True,adopted=False,forecasts=0,native=0,
        qualification='Current-state force/averaging diagnostic; not autonomous gain validation.')
    h.save(HERE/'verification.json',result);print(result)


def context_path(protocol,key):
    document=h.read(protocol['model_manifest'])
    return h.ROOT/document['sources'][key]['path']


if __name__=='__main__':main()
