"""Check corrected geometry and preserve all waiting, including rejected entry."""
import ast
import importlib
import io
import unittest
from diagnostics.repin_v3c3_review_20261001.ramp10639_170 import check as c

HERE=c.R/'prehead_storage171'


def main():
    assert not (HERE/'verification.json').exists()
    c.pin(c.Path(__file__))
    archive=c.read(HERE/'source_archive.json')
    for original,item in archive.items():
        assert c.sha(c.ROOT/item['archive'])==item['sha256']
    physical=c.ROOT/'evaluation/controllers/physical_ramp_boundary.py'
    prior=HERE/'physical_ramp_boundary.py.before.txt'
    old=ast.parse(prior.read_text(encoding='utf-8'))
    new=ast.parse(physical.read_text(encoding='utf-8'))
    def methods(tree):
        return {(cls.name,f.name):ast.dump(f,include_attributes=False)
                for cls in tree.body if isinstance(cls,ast.ClassDef)
                for f in cls.body if isinstance(f,(ast.FunctionDef,ast.AsyncFunctionDef))}
    a,b=methods(old),methods(new)
    allowed={('PhysicalRampBoundary','finish_interval'),('PhysicalRampBoundary','current_admission_space')}
    assert set(b)-set(a)=={('PhysicalRampBoundary','_admission_space_veh')}
    assert all(a[k]==b[k] for k in a if k not in allowed)
    inputs={};reports=[];checked=0;mass_error=0.;pre_excess=0.
    records=c.read(HERE/'forecast/state/rows.json')
    for rec in records:
        name=rec['case']+'_'+rec['arm']
        prev=c.read(c.R/f'recovery_lateral169/forecast/state/{name}.json.gz')
        curr=c.read(HERE/f'forecast/state/{name}.json.gz')
        # A storage fix may move waiting without changing mainline dynamics.
        same={k:prev[k]==curr[k] for k in ('cells','flows','ports')}
        totals={label:dict(connector=0.,outside=0.) for label in ('before','after')}
        for p,q in zip(prev['ramps'],curr['ramps']):
            assert (p['start_sec'],p['ramp'])==(q['start_sec'],q['ramp'])
            dt=p['duration_sec']
            for k in ('head_service_veh','accepted_merge_veh','requested_arrivals_veh'):
                c.close(p[k],q[k],k)
            for label,x in (('before',p),('after',q)):
                # Same30s quadrature used by existing component scoring.
                if round(x['end_sec']-2670.1,6)%30==0:
                    pass
                totals[label]['connector'] += x['start']['connector_veh']*dt/3600
                totals[label]['outside'] += x['start']['outside_component_backlog_veh']*dt/3600
            for k in ('start','end'):
                error=abs((p[k]['connector_veh']+p[k]['outside_component_backlog_veh'])-
                          (q[k]['connector_veh']+q[k]['outside_component_backlog_veh']))
                mass_error=max(mass_error,error);assert error<1e-7
            meta=curr['diagnostics']['dynamic_ramp_boundary']['metadata'][q['ramp']]
            cap=meta['head_position_m']/meta['spacing_m']
            for lane in q['lane_receipts']:
                n=lane['end']['upstream_travelling_veh']+lane['end']['head_ready_veh']
                before=lane['start']['upstream_travelling_veh']+lane['start']['head_ready_veh']
                excess=max(0.,n-max(cap,before))
                pre_excess=max(pre_excess,excess);assert excess<1e-7
                c.close(lane['end']['conservation_residual_veh'],0.,'lane conservation')
                checked+=1
        for label in totals:totals[label]['sum']=sum(totals[label].values())
        c.close(totals['before']['sum'],totals['after']['sum'],'connector plus outside residence')
        assert all(same.values()), (name,same)
        reports.append(dict(case=name,unchanged_tables=same,head_merge_requests_unchanged=True,
            residence_1s_veh_h=totals,model_actual_delta_ttt=rec['predicted']['ttt']-rec['actual']['ttt']))
    module=importlib.import_module('diagnostics.demand_sweep.user_native_20260914.metanet_terms_implementation_v2.test_physical_ramp_boundary')
    loader=unittest.TestLoader();names=loader.getTestCaseNames(module.RampBoundaryTests)
    missing='test_08_actual_c10490_geometry_initial_cohort_smoke'
    # This legacy test's two source files are absent. Keep its failed log and
    # use the actual selected-network8-arm replay above, not fabricated files.
    assert not (module.HERE/'port_profile.json').exists()
    suite=unittest.TestSuite(module.RampBoundaryTests(n) for n in names if n!=missing)
    stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    (HERE/'focused_tests.log').write_text(stream.getvalue(),encoding='utf-8')
    assert result.wasSuccessful()
    protection=c.read(c.R/'recovery_lateral169/protocol.json')
    for p,d in protection['protected_sha256'].items():assert c.sha(p)==d,p
    assert c.sha(protection['STOP']['path'])==protection['STOP']['sha256']
    for p,d in c.PINS.items():assert c.sha(p)==d,p
    for path in (physical,c.R/'state_lateral168/run.py'):
        saved=HERE/(path.name+'.executed.txt');saved.write_bytes(path.read_bytes())
        inputs[str(path)]=dict(sha256=c.sha(path),archive=str(saved))
    verdict=dict(status='geometry_fix_verified_gain_not_qualified',
        source_scope='Existing physical admission helper and its two callers only; exact171 sources archived. Forecast preflight only_lateral_matrix_changed refers to serialized RouteLaneRegion versus158, NOT the additional physical admission correction.',
        unchanged_other_class_methods=len(a)-len(allowed),checked_lane_seconds=checked,
        new_prehead_excess_max_veh=pre_excess,connector_plus_outside_mass_difference_max_veh=mass_error,
        records=reports,focused_tests_passed=result.testsRun,legacy_missing_fixture_test=missing,
        legacy_failure_log=str(HERE/'after_tests.log'),input_sha256=c.PINS,source_after=inputs,
        core9_and_STOP_preserved=True,
        limitation='No transport gain from moving waiting outside connector. This correction needs full coupled urban ownership/derivative tests before SDMPC qualification.169 VSL sign error remains. Initial overcapacity is preserved.',
        forecasts=9,new_fits=0,native=0,FZP=0)
    (HERE/'verification.json').write_text(c.json.dumps(verdict,ensure_ascii=False,indent=2),encoding='utf-8')
    print('checked',checked,'tests',result.testsRun,'mass',mass_error,'excess',pre_excess)
    for r in reports:
        if r['case']=='s67_late_hold':print(r)


if __name__=='__main__':main()
