"""Pure actual-module price/quantity tests; no vendor/model/native imports."""
from __future__ import annotations
import copy
import importlib.util
from pathlib import Path
from types import SimpleNamespace as NS
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('joint_terms_actual', ROOT / 'evaluation/controllers/area_leader_objective.py')
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)


def fixture():
    signals = tuple(f'SC{i}' for i in range(1, 18))
    kinds = ('boundary_in', 'off_ramp', 'boundary_out', 'on_ramp', 'internal')
    moves = {s+'_'+k: {'kind': k, 'signal': s, 'phase': s+'_p1'} for s in signals for k in kinds}
    models = {s: NS(signal=s, movements=[s+'_'+k for k in kinds],
        kind_of={s+'_'+k: k for k in kinds}) for s in signals}
    ramps = ('R1', 'R2', 'R3', 'R4')
    net = NS(control_area_enabled=True, signals=signals, urban_movements=moves,
        freeway_links=('FW_E', 'FW_W'), ramps=ramps,
        ramp_to_freeway=dict(zip(ramps, ('FW_E', 'FW_E', 'FW_W', 'FW_W'))), cycle_length=150.,
        signal_cycle_length=lambda signal: 150.)
    cfg = NS(network=net, simulation=NS(T_u_sec=1., T_u_h=1/3600, K_cu=2))
    follower = NS(cfg=cfg, _local_models=models,
        _phase_movements={s: {p: [] for p in ('p1', 'p2', 'p3', 'p4')} for s in signals},
        _local_freeway_models={d: NS(link=d, n_seg=2,
            owned_ramps=[r for r in ramps if net.ramp_to_freeway[r] == d]) for d in net.freeway_links},
        signal_phase_price=None, signal_phase_price_ref={}, signal_phase_price_weight=.25,
        signal_marginal_price={s: 1e9 for s in signals},  # deliberately excluded scalar alias
        offset_marginal_price=None, offset_marginal_price_ref={}, offset_marginal_price_weight=2.,
        vsl_marginal_price=None, vsl_marginal_price_ref={}, vsl_marginal_price_weight=3.,
        metering_marginal_price=None, metering_marginal_price_ref={}, metering_marginal_price_weight=4.,
        metering_price_split=True, green_offset_cross_price=None, vsl_meter_cross_price=None)
    action = NS(green_times={s+'_'+p: 30. for s in signals for p in ('p1', 'p2', 'p3', 'p4')},
        offsets={s: 5. for s in signals}, ramp_metering={r: 100. for r in ramps},
        vsl={k: 120. for d in net.freeway_links for k in (d, d+'__seg0', d+'__seg1')},
        N_P_star=123., N_UF_star=456.)
    response = {'schema': 'control-area-fixed-response/v1', 'residence': [], 'transfers': []}
    for i in range(2):
        response['residence'].append({'stage': 'urban', 'start_sec': 900.+i, 'end_sec': 901.+i,
            'dt_h': 1/3600, 'model_stock_veh': {'movement:'+m: 0. for m in moves}})
    for s in signals:
        for n, kind in enumerate(kinds, 1):
            m = s+'_'+kind
            response['transfers'].append({'stage': 'urban', 'start_sec': 900., 'end_sec': 901.,
                'source': 'storage:off' if kind == 'off_ramp' else 'movement:'+m,
                'target': None, 'route_key': 'movement:'+m, 'vehicles': float(n),
                'ttd_veh': 999., 'entered_veh': 999.})
    context = {'leader_present': True, 'np_mode': 'dual', 'nuf_mode': 'dual',
        'inactive_price_addresses': {name: [] for name in ('phase', 'offset', 'vsl', 'meter')}}
    return follower, action, response, context


def quantities(f, response):
    return api.shared_urban_quantities(f, response, start_sec=900., horizon_steps=1)


def price(f, action, q, context, **updates):
    kw = dict(lambda_p=.5, lambda_uf=.1, target_np_veh=0., target_nuf_veh_h=300., price_context=context)
    kw.update(updates)
    return api.fixed_joint_price_terms(f, action, q, **kw)


class SharedJointTests(unittest.TestCase):
    def test_physical_eight_nuf_and_dual_use_accepted_merge_not_service_ceiling(self):
        f,a,r,c=fixture(); n=f.cfg.network
        n.ramps=tuple('RM'+str(i) for i in range(8))
        n.ramp_to_freeway={mid:('FW_E' if i<4 else 'FW_W') for i,mid in enumerate(n.ramps)}
        n.physical_ramp_branches={'ramps':{mid:{'to_model_link':owner} for mid,owner in n.ramp_to_freeway.items()}}
        for owner,model in f._local_freeway_models.items():
            model.owned_ramps=[mid for mid in n.ramps if n.ramp_to_freeway[mid]==owner]
        a.ramp_metering={mid:2000. for mid in n.ramps}
        r['freeway_frames']=[{'start_sec':900.,'end_sec':902.,
            'actual_ramp_release_veh_h':{mid:(1200. if mid=='RM0' else 0.) for mid in n.ramps}}]
        q=quantities(f,r)
        checked=self.constraints(f,a,q,target_nuf_veh_h=1200.)
        self.assertTrue(checked['feasible'])
        self.assertEqual(checked['nuf']['actual'],1200.)
        self.assertEqual(checked['nuf_definition'],'predicted_accepted_mainline_merge')
        self.assertNotEqual(checked['nuf']['actual'],sum(a.ramp_metering.values()))
        self.assertFalse(self.constraints(f,a,q,target_nuf_veh_h=7200.)['feasible'])
        terms=price(f,a,q,c,lambda_p=0.,lambda_uf=.1,target_nuf_veh_h=1200.)
        self.assertEqual(terms['owners']['FW_E']['lambda_UF'],120.)
        self.assertEqual(terms['owners']['FW_W']['lambda_UF'],0.)
        self.assertEqual(terms['nuf_residual_veh_h'],0.)
        self.assertEqual(a.N_UF_star,456.)
        checked['physical_ramp_merge']['rate_veh_h_by_ramp']['RM0']=0.
        self.assertEqual(q['predicted_ramp_merge']['rate_veh_h_by_ramp']['RM0'],1200.)
        del q['predicted_ramp_merge']
        with self.assertRaises(ValueError):self.constraints(f,a,q,target_nuf_veh_h=1200.)

    def constraints(self, f, a, q, **updates):
        kw = dict(start_sec=900., horizon_steps=1, np_mode='cap', target_np_veh=0.,
                  np_tolerance_veh=0., nuf_mode='equality', target_nuf_veh_h=400.,
                  nuf_tolerance_veh_h=0.)
        kw.update(updates)
        return api.shared_quantity_constraints(f, a, q, **kw)

    def test_np_cap_uses_shared_signed_total_not_per_owner_quota(self):
        f, a, r, c = fixture()
        r['transfers'] = [row for row in r['transfers'] if row['route_key'] in
                          ('movement:SC1_boundary_in', 'movement:SC2_boundary_out')]
        r['transfers'][0]['vehicles'] = 30.
        r['transfers'][1]['vehicles'] = 20.
        q = quantities(f, r)
        result = self.constraints(f, a, q, target_np_veh=10.)
        self.assertEqual(result['net_inflow_veh_by_owner']['SC1'], 30.)
        self.assertEqual(result['net_inflow_veh_by_owner']['SC2'], -20.)
        self.assertTrue(result['feasible'])
        self.assertEqual(result['np']['actual'], 10.)
        self.assertFalse(result['individual_np_quotas_created'])
        failed = self.constraints(f, a, q, target_np_veh=9.)
        self.assertFalse(failed['feasible'])
        self.assertEqual((failed['np']['residual'], failed['np']['violation']), (1., 1.))
        self.assertEqual(failed['np']['target'], 9.)

    def test_cap_is_hard_constraint_with_no_lambda_penalty_substitution(self):
        f, a, r, c = fixture(); q = quantities(f, r)
        c.update(np_mode='cap', nuf_mode='equality')
        result = price(f, a, q, c, lambda_p=0., lambda_uf=0., target_np_veh=-69.)
        self.assertEqual(result['np_residual_veh'], 1.)
        self.assertTrue(all(row['total'] == 0. for row in result['owners'].values()))
        self.assertFalse(result['feasibility_certified'])
        self.assertFalse(self.constraints(f, a, q, target_np_veh=-69.)['feasible'])
        for lp, lu in ((1., 0.), (0., 1.)):
            with self.assertRaises(ValueError): price(f, a, q, c, lambda_p=lp, lambda_uf=lu)

    def test_global_nuf_equality_uses_final_rate_sum_not_target_alias_or_accepted_release(self):
        f, a, r, c = fixture(); q = quantities(f, r)
        result = self.constraints(f, a, q)
        self.assertEqual(a.N_UF_star, 456.)  # Different outer semantic field is not the supplied frozen target.
        self.assertEqual(result['nuf']['actual'], 400.)
        self.assertTrue(result['nuf']['satisfied'])
        self.assertEqual(result['meter_rate_veh_h_by_owner'], {'FW_E': 200., 'FW_W': 200.})
        a.ramp_metering['R1'] = 101.
        failed = self.constraints(f, a, q)
        self.assertFalse(failed['feasible'])
        self.assertEqual(failed['nuf']['residual'], 1.)
        self.assertEqual(failed['nuf']['target'], 400.)
        self.assertFalse(failed['directional_nuf_constraints_checked'])

    def test_constraints_report_explicit_tolerance_and_dual_nonconstraint_separately(self):
        f, a, r, c = fixture(); q = quantities(f, r)
        result = self.constraints(f, a, q, target_np_veh=-68.5, np_tolerance_veh=.5,
                                   target_nuf_veh_h=399.75, nuf_tolerance_veh_h=.25)
        self.assertTrue(result['feasible'])
        self.assertEqual((result['np']['residual'], result['np']['tolerance']), (.5, .5))
        self.assertEqual((result['nuf']['residual'], result['nuf']['tolerance']), (.25, .25))
        dual = self.constraints(f, a, q, np_mode='dual', nuf_mode='dual', target_np_veh=-100.)
        self.assertFalse(dual['np']['constraint_checked'])
        self.assertIsNone(dual['np']['satisfied'])
        self.assertIsNone(dual['nuf']['satisfied'])
        self.assertTrue(dual['feasible'])
        self.assertTrue(dual['quantity_constraints_only'])
        self.assertFalse(dual['physical_feasibility_certified'])

    def test_constraint_quantity_state_horizon_catalog_and_kind_authority(self):
        for mode in ('start', 'horizon', 'sample_count', 'missing_owner', 'catalog', 'kind', 'inventory'):
            f, a, r, c = fixture(); q = quantities(f, r); kw = {}
            if mode == 'start': kw['start_sec'] = 902.
            elif mode == 'horizon': kw['horizon_steps'] = 2
            elif mode == 'sample_count': q['provenance']['urban_samples'] = 1
            elif mode == 'missing_owner': del q['owners']['SC17']
            elif mode == 'catalog': q['provenance']['movement_catalog']['SC1_internal']['owner'] = 'SC2'
            elif mode == 'kind': q['owners']['SC1']['net_inflow_veh'] += 1.
            else: q['provenance']['configured_movement_count'] += 1
            with self.subTest(mode=mode), self.assertRaises(ValueError): self.constraints(f, a, q, **kw)

    def test_constraint_invalid_tolerance_rate_and_unknown_meter_fail(self):
        for mode in ('negative_np_tol', 'nan_nuf_tol', 'bool_tol', 'nan_rate', 'unknown_meter', 'duplicate_owner'):
            f, a, r, c = fixture(); q = quantities(f, r); kw = {}
            if mode == 'negative_np_tol': kw['np_tolerance_veh'] = -1.
            elif mode == 'nan_nuf_tol': kw['nuf_tolerance_veh_h'] = float('nan')
            elif mode == 'bool_tol': kw['np_tolerance_veh'] = True
            elif mode == 'nan_rate': a.ramp_metering['R1'] = float('nan')
            elif mode == 'unknown_meter': a.ramp_metering['unknown'] = 1.
            else: f._local_freeway_models['FW_W'].owned_ramps[0] = 'R1'
            with self.subTest(mode=mode), self.assertRaises(ValueError): self.constraints(f, a, q, **kw)

    def test_constraints_are_read_only_and_do_not_certify_directional_budgets(self):
        f, a, r, c = fixture(); q = quantities(f, r)
        a.ramp_metering.update(R1=150., R3=50.)  # Global equality remains 400; directions changed.
        before = copy.deepcopy((a.__dict__, q))
        result = self.constraints(f, a, q)
        self.assertTrue(result['feasible'])
        self.assertFalse(result['directional_nuf_constraints_checked'])
        self.assertEqual(result['meter_rate_veh_h_by_owner'], {'FW_E': 250., 'FW_W': 150.})
        result['net_inflow_veh_by_owner']['SC1'] = 99.
        self.assertEqual((a.__dict__, q), before)

    def test_actual_service_signs_storage_offramp_and_not_omega(self):
        f, a, r, c = fixture()
        q = quantities(f, r)
        self.assertEqual(len(q['owners']), 17)
        self.assertEqual(q['owners']['SC1']['net_inflow_veh'], -4.)
        self.assertEqual(q['owners']['SC1']['by_kind_veh']['off_ramp'], 2.)
        self.assertFalse(q['provenance']['legacy_cycle_average_equivalent'])
        self.assertFalse(q['provenance']['omega_crossing_quantity'])

    def test_zero_events_require_complete_grid_and_inventory(self):
        f, a, r, c = fixture(); r['transfers'] = []
        self.assertEqual(quantities(f, r)['owners']['SC1']['net_inflow_veh'], 0.)
        del r['residence'][0]['model_stock_veh']['movement:SC1_off_ramp']
        with self.assertRaises(KeyError): quantities(f, r)

    def test_nonservice_arrival_and_meter_release_not_counted(self):
        f, a, r, c = fixture()
        before = quantities(f, r)
        r['transfers'].append({'route_key': 'arrival:SC1_on_ramp'})
        r['transfers'].append({'route_key': 'ramp:R1->merge_pending:R1'})
        self.assertEqual(quantities(f, r), before)

    def test_unknown_duplicate_owner_or_kind_rejected(self):
        for mode in ('unknown_route', 'duplicate', 'kind', 'missing_owner', 'missing_controlled', 'wrong_signal'):
            f, a, r, c = fixture()
            if mode == 'unknown_route': r['transfers'][0]['route_key'] = 'movement:unknown'
            elif mode == 'duplicate': f._local_models['SC2'].movements.append('SC1_internal'); f._local_models['SC2'].kind_of['SC1_internal'] = 'internal'
            elif mode == 'kind': f._local_models['SC1'].kind_of['SC1_internal'] = 'boundary_out'
            elif mode == 'missing_owner': del f._local_models['SC17']
            elif mode == 'missing_controlled':
                f._local_models['SC1'].movements.remove('SC1_internal')
                del f._local_models['SC1'].kind_of['SC1_internal']
            else: f.cfg.network.urban_movements['SC1_internal']['signal'] = 'SC2'
            with self.subTest(mode=mode), self.assertRaises((ValueError, KeyError)): quantities(f, r)

    def test_clock_and_event_finiteness_rejected(self):
        for mode in ('row_order', 'event_stage', 'event_end', 'nan', 'bool'):
            f, a, r, c = fixture()
            if mode == 'row_order': r['residence'].reverse()
            elif mode == 'event_stage': r['transfers'][0]['stage'] = 'landing'
            elif mode == 'event_end': r['transfers'][0]['end_sec'] = 902.
            else: r['transfers'][0]['vehicles'] = float('nan') if mode == 'nan' else True
            with self.subTest(mode=mode), self.assertRaises(ValueError): quantities(f, r)

    def test_inactive_prices_and_separate_lambda_units_targets(self):
        f, a, r, c = fixture(); q = quantities(f, r)
        result = price(f, a, q, c)
        self.assertEqual(len(result['owners']), 19)
        self.assertEqual(result['owners']['SC1']['total'], -2.)
        self.assertEqual(result['owners']['FW_E']['total'], 20.)
        self.assertEqual(result['np_residual_veh'], -68.)
        self.assertEqual(result['nuf_residual_veh_h'], 100.)
        self.assertEqual(result['units']['lambda_UF'], 'h^2')
        self.assertEqual((a.N_P_star, a.N_UF_star), (123., 456.))

    def test_fullphase_only_including_headless_phase(self):
        f, a, r, c = fixture(); q = quantities(f, r)
        f.signal_phase_price = {'SC1': {p: float(i) for i, p in enumerate(('p1', 'p2', 'p3', 'p4'), 1)}}
        f.signal_phase_price_ref = {'SC1': {p: 30. for p in ('p1', 'p2', 'p3', 'p4')}}
        c['inactive_price_addresses']['phase'] = [k for k in a.green_times if not k.startswith('SC1_')]
        a.green_times['SC1_p3'] += 6.; a.green_times['SC1_p4'] -= 6.
        result = price(f, a, q, c)
        self.assertEqual(result['owners']['SC1']['phase'], .25*(3.*6 + 4.*-6))
        self.assertFalse(result['scalar_green_channel_included'])

    def test_circular_offset_and_expanded_vsl_once_meter_rates(self):
        f, a, r, c = fixture(); q = quantities(f, r)
        f.offset_marginal_price = {'SC1': .1}; f.offset_marginal_price_ref = {'SC1': 145.}
        c['inactive_price_addresses']['offset'] = [s for s in f.cfg.network.signals if s != 'SC1']
        f.vsl_marginal_price = {'FW_E__seg0': .1, 'FW_E__seg1': .2}
        f.vsl_marginal_price_ref = {'FW_E__seg0': 100., 'FW_E__seg1': 100.}
        c['inactive_price_addresses']['vsl'] = ['FW_W__seg0', 'FW_W__seg1']
        f.metering_marginal_price = {'R1': .1}; f.metering_marginal_price_ref = {'R1': 90.}
        c['inactive_price_addresses']['meter'] = ['R2', 'R3', 'R4']
        result = price(f, a, q, c)
        self.assertEqual(result['owners']['SC1']['offset'], 2.)
        self.assertEqual(result['owners']['FW_E']['vsl'], 3.*.1*20. + 3.*.2*20.)
        self.assertEqual(result['owners']['FW_E']['meter'], 4.)

    def test_sparse_active_missing_reference_unknown_alias_rejected(self):
        for mode in ('missing', 'ref', 'alias'):
            f, a, r, c = fixture(); q = quantities(f, r)
            f.vsl_marginal_price = {'FW_E__seg0': 0.}; f.vsl_marginal_price_ref = {'FW_E__seg0': 120.}
            if mode != 'missing': c['inactive_price_addresses']['vsl'] = ['FW_E__seg1', 'FW_W__seg0', 'FW_W__seg1']
            if mode == 'ref': f.vsl_marginal_price_ref = {}
            elif mode == 'alias': f.vsl_marginal_price['FW_E'] = 0.; f.vsl_marginal_price_ref['FW_E'] = 120.
            with self.subTest(mode=mode), self.assertRaises(ValueError): price(f, a, q, c)

    def test_signal_specific_cycle_wrap_and_dark_address_required(self):
        f, a, r, c = fixture(); q = quantities(f, r)
        f.cfg.network.signal_cycle_length = lambda signal: 120. if signal == 'SC1' else 150.
        f.offset_marginal_price = {'SC1': .1, 'SC2': .1}
        f.offset_marginal_price_ref = {'SC1': 115., 'SC2': 145.}
        c['inactive_price_addresses']['offset'] = list(f.cfg.network.signals[2:])
        result = price(f, a, q, c)
        self.assertEqual(result['owners']['SC1']['offset'], 2.)
        self.assertEqual(result['owners']['SC2']['offset'], 2.)
        del f._phase_movements['SC17']['p4']
        with self.assertRaises(ValueError): price(f, a, q, c)

    def test_finite_price_and_cumulative_internal_service(self):
        f, a, r, c = fixture(); q = quantities(f, r)
        with self.assertRaises(ValueError): price(f, a, q, c, lambda_p=float('nan'))
        event = next(row for row in r['transfers'] if row['route_key'] == 'movement:SC1_internal')
        event['vehicles'] = 1e308
        r['transfers'].append(copy.deepcopy(event))
        with self.assertRaises(ValueError): quantities(f, r)

    def test_pfo_cross_soft_anchor_and_policy_missing_rejected(self):
        for mode in ('pfo', 'cross', 'soft', 'missing', 'lambda'):
            f, a, r, c = fixture(); q = quantities(f, r)
            if mode == 'pfo': c['leader_present'] = False
            elif mode == 'cross': f.green_offset_cross_price = {}
            elif mode == 'soft': f.metering_marginal_price = {}; f.metering_price_split = False; c['nuf_mode'] = 'equality'
            elif mode == 'missing': del c['np_mode']
            else: c['nuf_mode'] = 'equality'
            with self.subTest(mode=mode), self.assertRaises(ValueError): price(f, a, q, c)

    def test_complete_action_and_quantity_binding_required(self):
        for mode in ('phase', 'alias', 'owner', 'kind_total'):
            f, a, r, c = fixture(); q = quantities(f, r)
            if mode == 'phase': del a.green_times['SC17_p4']
            elif mode == 'alias': a.vsl['FW_E'] = 110.
            elif mode == 'owner': q['provenance']['movement_catalog']['SC1_internal']['owner'] = 'SC2'
            else: q['owners']['SC1']['net_inflow_veh'] += 1.
            with self.subTest(mode=mode), self.assertRaises(ValueError): price(f, a, q, c)

    def test_no_mutation_repeated_query(self):
        f, a, r, c = fixture(); q = quantities(f, r)
        before = copy.deepcopy((vars(a), r, q, c, f.signal_marginal_price))
        first = price(f, a, q, c)
        self.assertEqual(first, price(f, a, q, c))
        self.assertEqual(before, (vars(a), r, q, c, f.signal_marginal_price))

    def test_nonowner_service_is_validated_reported_and_excluded_from_np(self):
        f, a, r, c = fixture()
        m = 'SC102_N_to_S'
        f.cfg.network.urban_movements[m] = {'signal': 'SC102', 'phase': '', 'kind': 'boundary_in'}
        for row in r['residence']: row['model_stock_veh']['movement:'+m] = 3.
        r['transfers'].append({'stage': 'urban', 'start_sec': 901., 'end_sec': 902.,
            'source': 'movement:'+m, 'target': 'storage:downstream',
            'route_key': 'movement:'+m, 'vehicles': 7.})
        q = quantities(f, r)
        self.assertEqual(len(q['owners']), 17)
        self.assertEqual(q['nonowner_service']['by_signal']['SC102']['by_kind_veh']['boundary_in'], 7.)
        self.assertEqual(q['served_by_movement_veh'][m], 7.)
        self.assertFalse(q['nonowner_service']['constant_traffic_assumed'])
        self.assertFalse(q['nonowner_service']['included_in_owner_np'])
        self.assertEqual(price(f, a, q, c)['np_residual_veh'], -68.)
        constrained = self.constraints(f, a, q, target_np_veh=-68.)
        self.assertTrue(constrained['feasible'])
        self.assertEqual(constrained['np']['actual'], -68.)
        self.assertFalse(constrained['nonowner_service_included_in_np'])
        del r['residence'][0]['model_stock_veh']['movement:'+m]
        with self.assertRaises(KeyError): quantities(f, r)

    def test_nonowner_missing_identity_phase_or_bad_event_rejected(self):
        for mode in ('empty_signal', 'missing_signal', 'phase', 'kind', 'bad_event'):
            f, a, r, c = fixture(); m = 'SC102_N_to_S'
            entry = {'signal': 'SC102', 'phase': '', 'kind': 'internal'}
            if mode == 'empty_signal': entry['signal'] = ''
            elif mode == 'missing_signal': del entry['signal']
            elif mode == 'phase': entry['phase'] = 'SC102_p1'
            elif mode == 'kind': entry['kind'] = 'unknown'
            f.cfg.network.urban_movements[m] = entry
            for row in r['residence']: row['model_stock_veh']['movement:'+m] = 0.
            r['transfers'].append({'stage': 'landing' if mode == 'bad_event' else 'urban',
                'start_sec': 901., 'end_sec': 902., 'route_key': 'movement:'+m, 'vehicles': 1.})
            with self.subTest(mode=mode), self.assertRaises((ValueError, KeyError)): quantities(f, r)


if __name__ == '__main__':
    unittest.main()
