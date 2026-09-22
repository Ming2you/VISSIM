"""Two fixed local diagnostics: slow relaxation with/without pressure rescaling.

Only cells15..20. No data fitting, reward, new capacity, or default adoption.
Both tau30/nu35 and tau30/nu87.5 remain within the declared parameter ranges.
"""
from pathlib import Path
import copy
import hashlib
import inspect
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import urban_route_transport as u
import canonical_harness as ch
from evaluation.controllers.physical_lane_groups import PhysicalLaneGroups

HERE = Path(__file__).resolve().parent
ARMS = ('none', 'rm_ramp', 'vsl', 'both')


def main():
    out = HERE / 'downstream_relaxation_check_v2'
    out.mkdir(exist_ok=False)
    files = [Path(__file__), Path(u.__file__), u.e.CAL/'canonical_harness.py',
        u.e.ROOT/'evaluation/controllers/vissim_stackelberg_adapter.py',
        u.e.ROOT/'evaluation/controllers/physical_lane_groups.py',
        HERE/'transport_step1_exchange_off_v2/config.json',
        HERE/'port_travel_fit_v1/selected_parameters.json',
        HERE/'downstream_response_terms_v4/result.json',
        HERE/'downstream_relaxation_check_v1/source_before_result_reader_fix.txt',
        HERE/'downstream_relaxation_check_v1/protocol.json']
    pins = {p.relative_to(u.e.ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    u.e.save(out/'protocol.json', dict(source_pins=pins, scope='Only FW_E port-free cells15..20',
        fixed_trials={'fixed_nu':{'tau_sec':30.,'nu':35.},'preserve_pressure':{'tau_sec':30.,'nu':87.5}},
        rationale='Previous consumed tau12/nu35; keeping nu/tau constant isolates relaxation change.',
        selection='No candidate chosen or fitted using control costs; fixed diagnostic contrasts.',
        qualified=False, source_model='transport_step1_exchange_off_v2', new_native_runs=0))
    original_config = ch.CanonicalFreewayModel._config
    original_advance = PhysicalLaneGroups.advance
    results = {}
    for mode, nu in (('fixed_nu',35.), ('preserve_pressure',87.5)):
        effective = []
        calls = 0
        def configured(self, road, parameters):
            cfg = original_config(self, road, parameters)
            if road == 'FW_E':
                assert not getattr(cfg.network,'freeway_state_response',{})
                rows = cfg.network.freeway_segment_params[road]
                for c in range(15,21):
                    before = copy.deepcopy(rows[c])
                    assert abs(before['metanet_tau_h']*3600-12.)<1e-9
                    assert before['metanet_nu_km2_h']==35.
                    rows[c]['metanet_tau_h']=30./3600
                    rows[c]['metanet_nu_km2_h']=nu
                    effective.append(dict(cell=c,before=before,after=copy.deepcopy(rows[c])))
            return cfg
        def advance(self,state,control,demand,cfg,**kw):
            nonlocal calls
            if self.road!='FW_E':return original_advance(self,state,control,demand,cfg,**kw)
            mn=ch.accounting._mn
            original_speed=mn.metanet_speed_update_kmh
            def observed(*args,**kwargs):
                nonlocal calls
                f=inspect.currentframe().f_back
                if (f.f_code.co_name=='advance' and Path(f.f_code.co_filename).resolve()==
                    u.e.ROOT/'evaluation/controllers/physical_lane_groups.py' and 15<=f.f_locals['i']<=20):
                    ctx=ch.adapter._FW_SEG_CTX
                    assert ctx['armed']
                    assert abs(ctx['p']['metanet_tau_h']*3600-30.)<1e-9
                    assert args[8]==nu
                    assert not ctx.get('state_response')
                    if mode=='preserve_pressure':assert abs(args[8]/ctx['p']['metanet_tau_h']-35./(12./3600))<1e-8
                    calls+=1
                del f
                return original_speed(*args,**kwargs)
            mn.metanet_speed_update_kmh=observed
            try:return original_advance(self,state,control,demand,cfg,**kw)
            finally:mn.metanet_speed_update_kmh=original_speed
        ch.CanonicalFreewayModel._config=configured
        PhysicalLaneGroups.advance=advance
        name='downstream_tau30_'+mode+'_v1'
        reused = mode=='fixed_nu'
        try:
            if reused:
                # Four forecasts completed before v1's diagnostic-dict reader
                # failed. Preserve and verify those outputs instead of rerunning.
                old=u.e.load(HERE/'downstream_relaxation_check_v1/protocol.json')
                source=HERE/'downstream_relaxation_check_v1/source_before_result_reader_fix.txt'
                assert hashlib.sha256(source.read_bytes()).hexdigest()==old['source_pins'][Path(__file__).relative_to(u.e.ROOT).as_posix()]
                assert (HERE/name/'result.json').exists()
            else:
                u.run_probe(lateral_access=True,prefer_receiving=True,trace_limits=False,
                    network_exit_intent=True,current_exit_intent=True,branch_partition='on',
                    branch_exchange='off',partition_context='on',transport_step=1,output_name=name)
        finally:
            ch.CanonicalFreewayModel._config=original_config
            PhysicalLaneGroups.advance=original_advance
        assert calls==(0 if reused else 10800)
        for arm in ARMS:
            got=u.e.load(HERE/name/f'prediction_{arm}.json')
            base=u.e.load(HERE/'transport_step1_exchange_off_v2'/f'prediction_{arm}.json')
            for field in ('cells','flows','ports','ramps'):
                assert [r for r in got[field] if r.get('road')=='FW_W']==[r for r in base[field] if r.get('road')=='FW_W']
            assert got['local_ramp_audit']['passed']
            for d in got['diagnostics']['roads']:
                assert d['continuity_residual_max_veh']<1e-7
                assert d['negative_density_count']==0 and d['jam_density_exceedance_count']==0
        result=u.e.load(HERE/name/'result.json')
        results[mode]=dict(folder=name,checked_speed_calls_this_execution=calls,
            reused_completed_forecasts=reused,
            previous_speed_checks=('v1 reached its 10800-call assertion before the result-reader failure' if reused else None),
            effective_parameters=effective,deltas=result['deltas'],costs=result['costs'],
            nc_score=result['summaries']['none']['score'],qualified=False)
        print('DIAGNOSTIC',mode,'deltas',result['deltas'],'score',result['summaries']['none']['score'],flush=True)
    for name,digest in pins.items():assert hashlib.sha256((u.e.ROOT/name).read_bytes()).hexdigest()==digest
    base=u.e.load(HERE/'transport_step1_exchange_off_v2/result.json')
    u.e.save(out/'result.json',dict(status='LOCAL_RELAXATION_VS_PRESSURE_DIAGNOSTIC',qualified=False,
        cases=results,reference_deltas=base['deltas'],reference_nc_score=base['summaries']['none']['score'],
        new_native_runs=0,production_changes=0,source_pins_verified=True,
        note='One initial state; no multiple-state guards, fresh holdout, or qualification claim.'))


if __name__=='__main__':
    main()
