"""Matched directional-price arithmetic against explicit 19-owner envelopes."""
from __future__ import annotations
import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('matched_secant_actual', ROOT/'evaluation/controllers/area_leader_objective.py')
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)


def fixture(owner='SC1', kind='phase_exchange'):
    owners = tuple(f'SC{i}' for i in range(1,18)) + ('FW_E','FW_W')
    context = {'beta_seconds':300., 'frozen_digest':'fixed-physical-inputs',
               'local_cost_definition':'shared-physical-local-base/v1', 'horizon_sec':450.}
    base = {'objective_veh_h':100., 'local_base_costs':dict.fromkeys(owners,10.),
        'context':context, 'response_token':'base-response', 'local_cost_response_token':'base-response',
        'physical_owner_tokens':{s:s+'-base-physical' for s in owners},
        'price_or_quantity_terms_included':False, 'local_cost_contains_omega_beta':False}
    probe = copy.deepcopy(base)
    probe.update(objective_veh_h=112., response_token='probe-response', local_cost_response_token='probe-response')
    probe['local_base_costs'][owner] = 14.
    probe['physical_owner_tokens'][owner] = owner+'-probe-physical'
    if owner.startswith('SC'):
        values={owner+'_'+p:30. for p in ('p1','p2','p3','p4')}; values[owner]=10.
        kinds={a:'offset' if a==owner else 'green' for a in values}
        after=dict(values); after[owner+'_p1']+=6.; after[owner+'_p2']-=6.
        direction={a:(after[a]-values[a])/6. for a in values}
        unit='s'; step=6.; cycles={owner:150.}
    else:
        values={f'{owner}__seg{i}':120. for i in range(4)}; values.update(R1=100.,R2=100.)
        kinds={a:'meter' if a.startswith('R') else 'vsl' for a in values}
        after=dict(values); after[owner+'__seg2']=100.; after[owner+'__seg3']=100.
        direction={a:(after[a]-values[a])/20. for a in values}
        unit='km/h'; step=20.; cycles={}
    coordinate={'owner':owner,'kind':kind,'parameter_unit':unit,'displacement':step,
        'base_values':values,'probe_values':after,'direction':direction,
        'address_kinds':kinds,'address_owners':dict.fromkeys(values,owner),'offset_cycles':cycles}
    model_values = {s: {**{s+'_'+p:30. for p in ('p1','p2','p3','p4')}, s:10.}
                    for s in owners if s.startswith('SC')}
    model_values.update({s: {**{f'{s}__seg{i}':120. for i in range(4)}, s:120.,
                           ramps[0]:100., ramps[1]:100.}
                         for s, ramps in (('FW_E', ('R1','R2')), ('FW_W', ('R3','R4')))})
    base['model_owner_values'] = copy.deepcopy(model_values)
    probe['model_owner_values'] = copy.deepcopy(model_values)
    args = base,probe,owners,owner,coordinate
    bind_changed_model(args)
    return args


def bind_changed_model(args):
    """Synthetic producer binds the requested coordinate to its response input."""
    b,p,_,owner,c = args
    for point, field in ((b,'base_values'),(p,'probe_values')):
        values = dict(c[field])
        if owner.startswith('FW_'):
            values[owner] = min(v for a,v in values.items() if a.startswith(owner+'__seg'))
        point['model_owner_values'][owner] = values


def score(args):
    b,p,owners,owner,c=args
    return api.matched_external_secant(b,p,owners=owners,owner=owner,coordinate=c)


class MatchedSecantTests(unittest.TestCase):
    def test_eight_meters_require_the_frozen_complete_owner_catalog(self):
        args=fixture()
        catalog={'FW_E':['R1','R2','R5','R6'], 'FW_W':['R3','R4','R7','R8']}
        for point in args[:2]:
            point['context']['physical_meter_addresses_by_owner']=copy.deepcopy(catalog)
            for owner,keys in catalog.items():
                point['model_owner_values'][owner].update({k:100. for k in keys})
        self.assertEqual(score(args)['external_delta_veh_h'],8.)
        bad=copy.deepcopy(args)
        bad[1]['context']['physical_meter_addresses_by_owner']['FW_W'][-1]='R6'
        with self.assertRaisesRegex(ValueError,'catalog'):score(bad)
        bad=copy.deepcopy(args)
        for point in bad[:2]:point['context'].pop('physical_meter_addresses_by_owner')
        with self.assertRaisesRegex(ValueError,'configured meters'):score(bad)

    def test_phase_direction_only_subtracts_changed_owner(self):
        args=fixture(); args[1]['local_base_costs']['SC2']=1000.
        r=score(args)
        self.assertEqual((r['delta_global_veh_h'],r['delta_local_veh_h'],r['external_delta_veh_h']),(12.,4.,8.))
        self.assertEqual(r['directional_secant'],8./6.)
        self.assertTrue(r['directional_only'])
        self.assertFalse(r['per_phase_gradient_constructed'])
        self.assertFalse(r['gauge_selected'])
        self.assertEqual(r['all_owner_costs_checked'],19)
        self.assertEqual(r['all_owner_model_values_checked'],19)

    def test_beta_not_reapplied_to_global_or_local_difference(self):
        args=fixture(); first=score(args)
        for point in args[:2]: point['context']['beta_seconds']=0.
        self.assertEqual(score(args)['directional_secant'],first['directional_secant'])
        # Negative J is valid with beta-weighted TD, while Ci stays its own base functional.
        args[0]['objective_veh_h']=-100.;args[1]['objective_veh_h']=-88.
        self.assertEqual(score(args)['external_delta_veh_h'],8.)

    def test_local_beta_or_additive_price_inclusion_rejected(self):
        for key in ('local_cost_contains_omega_beta','price_or_quantity_terms_included'):
            args=fixture();args[1][key]=True
            with self.subTest(key=key),self.assertRaises(ValueError):score(args)

    def test_same_response_and_context_required(self):
        for mode in ('beta','state','cost_definition','response','nan_context','reuse_response'):
            args=fixture();b,p,*_=args
            if mode=='beta':p['context']['beta_seconds']=150.
            elif mode=='state':p['context']['frozen_digest']='different-state'
            elif mode=='cost_definition':p['context']['local_cost_definition']='virtual-blocked-local/v1'
            elif mode=='response':p['local_cost_response_token']='another-local-rollout'
            elif mode=='nan_context':p['context']['horizon_sec']=float('nan')
            else:p['response_token']=p['local_cost_response_token']=b['response_token']
            with self.subTest(mode=mode),self.assertRaises(ValueError):score(args)

    def test_full_local_catalog_and_finiteness_required(self):
        for mode in ('missing','extra','nan','bool'):
            args=fixture();costs=args[1]['local_base_costs']
            if mode=='missing':del costs['FW_W']
            elif mode=='extra':costs['ghost']=0.
            else:costs['FW_W']=float('nan') if mode=='nan' else True
            with self.subTest(mode=mode),self.assertRaises(ValueError):score(args)

    def test_physical_alias_foreign_change_missing_owner_rejected(self):
        for mode in ('alias','foreign','missing','owner'):
            args=fixture();b,p,owners,owner,c=args
            if mode=='alias':p['physical_owner_tokens'][owner]=b['physical_owner_tokens'][owner]
            elif mode=='foreign':p['physical_owner_tokens']['FW_W']='changed-other'
            elif mode=='missing':del p['physical_owner_tokens']['SC17']
            else:c['owner']='SC2'
            with self.subTest(mode=mode),self.assertRaises(ValueError):score(args)

    def test_zero_and_nominal_instead_of_realized_step_rejected(self):
        for step in (0.,3.,float('nan'),True):
            args=fixture();args[-1]['displacement']=step
            with self.subTest(step=step),self.assertRaises(ValueError):score(args)
        args=fixture();c=args[-1];c['probe_values']=dict(c['base_values']);c['direction']=dict.fromkeys(c['direction'],0.)
        bind_changed_model(args)
        with self.assertRaises(ValueError):score(args)

    def test_phase_budget_hidden_offset_or_missing_dark_phase_rejected(self):
        for mode in ('budget','hidden_offset','missing_dark','foreign_address'):
            args=fixture();c=args[-1]
            if mode=='budget':c['probe_values']['SC1_p2']=30.;c['direction']['SC1_p2']=0.
            elif mode=='hidden_offset':c['probe_values']['SC1']+=6.;c['direction']['SC1']=1.
            elif mode=='foreign_address':c['address_owners']['SC1_p4']='SC2'
            else:
                for k in ('base_values','probe_values','direction','address_kinds','address_owners'):del c[k]['SC1_p4']
            bind_changed_model(args)
            with self.subTest(mode=mode),self.assertRaises(ValueError):score(args)

    def test_signed_reversal_retains_direction_metadata(self):
        args=fixture();c=args[-1]
        c['displacement']=-6.;c['direction']={a:-v for a,v in c['direction'].items()}
        self.assertEqual(score(args)['directional_secant'],-8./6.)

    def test_owner_circular_offset_uses_realized_small_displacement(self):
        args=fixture(kind='offset');c=args[-1]
        c['base_values']['SC1']=119.;c['probe_values']=dict(c['base_values']);c['probe_values']['SC1']=1.
        c['displacement']=2.;c['direction']=dict.fromkeys(c['direction'],0.);c['direction']['SC1']=1.
        c['offset_cycles']={'SC1':120.}
        bind_changed_model(args)
        self.assertEqual(score(args)['directional_secant'],4.)
        c['offset_cycles']={'SC1':150.}
        with self.assertRaises(ValueError):score(args)

    def test_expanded_vsl_and_joint_meter_direction(self):
        args=fixture('FW_E','vsl');r=score(args)
        self.assertEqual(r['directional_secant'],.4)
        c=args[-1];c['kind']='joint_direction';c['parameter_unit']='1';c['displacement']=1.
        c['probe_values']['R1']=70.;c['probe_values']['R2']=130.
        c['direction']={a:c['probe_values'][a]-v for a,v in c['base_values'].items()}
        bind_changed_model(args)
        r=score(args)
        self.assertEqual(r['directional_secant'],8.)
        self.assertEqual(r['realized_deltas']['R1'],-30.)
        self.assertEqual(r['secant_unit'],'veh*h')

    def test_derived_vsl_alias_and_incomplete_vector_rejected(self):
        for mode in ('alias','gap'):
            args=fixture('FW_E','vsl');c=args[-1]
            if mode=='alias':
                for k in ('base_values','probe_values','direction'):c[k]['FW_E']=0.
                c['address_kinds']['FW_E']='vsl';c['address_owners']['FW_E']='FW_E'
            else:
                for k in ('base_values','probe_values','direction','address_kinds','address_owners'):del c[k]['FW_E__seg1']
            with self.subTest(mode=mode),self.assertRaises(ValueError):score(args)

    def test_return_and_inputs_do_not_alias(self):
        args=fixture();before=copy.deepcopy(args);r=score(args)
        self.assertEqual(args,before)
        r['coordinate']['direction']['SC1_p1']=999.
        r['context']['frozen_digest']='mutated-return'
        r['model_owner_values']['base']['FW_E']['R1']=-99.
        self.assertEqual(args,before)

    def test_foreign_all_green_model_rate_alias_is_not_unilateral(self):
        args=fixture()
        args[1]['model_owner_values']['FW_W']['R3'] += 1.
        # Foreign physical token remains exactly the same all-GREEN schedule.
        with self.assertRaisesRegex(ValueError, 'foreign model owner changed'):score(args)

    def test_changed_coordinate_must_be_the_actual_model_input(self):
        for side, field in ((0,'base_values'),(1,'probe_values')):
            args=fixture()
            args[side]['model_owner_values']['SC1']['SC1'] += 1.
            with self.subTest(field=field),self.assertRaisesRegex(ValueError, 'changed owner model input'):
                score(args)

    def test_model_catalog_missing_invalid_alias_and_overlap_rejected(self):
        for mode in ('absent','missing_owner','missing_dark','missing_alias','wrong_alias',
                     'nan_foreign','duplicate_meter','changed_address','bool_foreign'):
            args=fixture();p=args[1];models=p['model_owner_values']
            if mode=='absent':del p['model_owner_values']
            elif mode=='missing_owner':del models['SC17']
            elif mode=='missing_dark':del models['SC17']['SC17_p4']
            elif mode=='missing_alias':del models['FW_W']['FW_W']
            elif mode=='wrong_alias':models['FW_W']['FW_W']=119.
            elif mode=='nan_foreign':models['FW_W']['R3']=float('nan')
            elif mode=='bool_foreign':models['FW_W']['R3']=True
            elif mode=='duplicate_meter':models['FW_W']['R1']=models['FW_W'].pop('R3')
            else:models['FW_W']['changed_meter']=models['FW_W'].pop('R3')
            with self.subTest(mode=mode),self.assertRaises(ValueError):score(args)


if __name__=='__main__':unittest.main()
