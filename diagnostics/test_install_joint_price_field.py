"""Pure holder installation tests; no vendor import, endpoint, COM or native run."""
import copy
from types import SimpleNamespace
import unittest
from diagnostics.test_joint_price_field import fixture, api


def inputs(fixed=False):
    f, ref, edges, _ = fixture(fixed_meter_rate=1800. if fixed else None)
    kw = {} if not fixed else {'nuf_price_policy':'bounded_direction_equality',
        'directional_nuf_targets_veh_h': {'FW_E':3600.,'FW_W':3600.}, 'nuf_equality_tolerance_veh_h':0.,
        'final_meter_bounds_veh_h': {r:{'lower':0.,'upper':1800.} for r in f.cfg.network.ramps}}
    field = api.fit_joint_price_field(f,ref,edges,**kw)
    f._wu = SimpleNamespace(untouched={'scalar':123.}, metering_marginal_price={'not-a-consumer':456.})
    return f,ref,field


class InstallJointPriceFieldTest(unittest.TestCase):
    def install(self,f,ref,field,**kwargs):
        args={'expected_owners':tuple(f.cfg.network.signals)+tuple(f.cfg.network.freeway_links),
              'expected_context':copy.deepcopy(field['context']), 'nuf_mode':'equality'}
        args.update(kwargs)
        return api.install_joint_price_field(f,ref,field,**args)

    def reject_unchanged(self,f,ref,field,**kwargs):
        before=copy.deepcopy(vars(f)); identities={k:id(v) for k,v in vars(f).items()}
        with self.assertRaises((ValueError,KeyError,TypeError)): self.install(f,ref,field,**kwargs)
        self.assertEqual(vars(f),before)
        self.assertEqual({k:id(v) for k,v in vars(f).items()},identities)

    def test_complete_install_detaches_all_maps_keeps_wu_flags_and_weights(self):
        f,ref,field=inputs(); before=copy.deepcopy(vars(f)); wu=f._wu; report=self.install(f,ref,field)
        self.assertTrue(report['installed']); self.assertTrue(report['caller_must_rebuild_context_and_callbacks'])
        self.assertFalse(report['nested_wu_synchronized']); self.assertIs(f._wu,wu)
        for name,values in field['holder_values'].items():
            self.assertEqual(getattr(f,name),values); self.assertIsNot(getattr(f,name),values)
        for name,value in before.items():
            if name not in field['holder_values']: self.assertEqual(getattr(f,name),value)
        field['holder_values']['signal_phase_price']['SC1']['p1']=999.
        field['holder_values']['vsl_marginal_price_ref']['FW_E__seg0']=999.
        self.assertNotEqual(f.signal_phase_price['SC1']['p1'],999.)
        self.assertEqual(f.vsl_marginal_price_ref['FW_E__seg0'],ref.vsl['FW_E__seg0'])
        ref.green_times['SC1_p1']=666.
        self.assertNotEqual(f.signal_phase_price_ref['SC1']['p1'],666.)

    def test_fixed_zero_meter_equality_still_rejects_non_split(self):
        f,ref,field=inputs(True); self.assertTrue(all(v==0. for v in field['holder_values']['metering_marginal_price'].values()))
        f.metering_price_split=False
        self.reject_unchanged(f,ref,field)
        self.assertFalse(f.metering_price_split); self.assertIsNone(f.metering_marginal_price)

    def test_fixed_zero_with_explicit_split_installs_and_preserves_both_addresses(self):
        f,ref,field=inputs(True); self.install(f,ref,field)
        self.assertEqual(set(f.metering_marginal_price),set(f.cfg.network.ramps))
        self.assertEqual(set(f.metering_marginal_price.values()),{0.})

    def test_equality_tangent_cannot_be_installed_for_dual_unrestricted_mode(self):
        f,ref,field=inputs(True); self.reject_unchanged(f,ref,field,nuf_mode='dual')

    def test_expected_owner_or_measured_owner_omission_rejected(self):
        f,ref,field=inputs(); owners=tuple(field['owner_fits'])
        self.reject_unchanged(f,ref,field,expected_owners=owners[:-1]+(owners[0],))
        del field['owner_fits']['SC17']; self.reject_unchanged(f,ref,field)

    def test_context_and_reference_mismatch_rejected(self):
        f,ref,field=inputs(); ctx=copy.deepcopy(field['context']); ctx['frozen_digest']='other'
        self.reject_unchanged(f,ref,field,expected_context=ctx)
        field['reference_levers']['offsets']['SC1']+=1.; self.reject_unchanged(f,ref,field)

    def test_missing_extra_and_nonfinite_holder_values_rejected(self):
        for mutation in ('missing','extra','nan','bool','bare_alias'):
            with self.subTest(mutation=mutation):
                f,ref,field=inputs(); holders=field['holder_values']
                if mutation=='missing': del holders['metering_marginal_price_ref']
                elif mutation=='extra': holders['unknown_price']={}
                elif mutation=='nan': holders['signal_phase_price']['SC17']['p4']=float('nan')
                elif mutation=='bool': holders['offset_marginal_price']['SC17']=False
                else: holders['vsl_marginal_price']['FW_E']=0.
                self.reject_unchanged(f,ref,field)

    def test_dark_phase_gauge_and_expanded_reference_checks(self):
        for mutation in ('dark','gauge','ref','missingcell','measured_bool'):
            with self.subTest(mutation=mutation):
                f,ref,field=inputs(); holders=field['holder_values']
                if mutation=='dark': holders['signal_phase_price']['SC17']['p4']=1.
                elif mutation=='gauge': holders['signal_phase_price']['SC1']['p1']+=1.
                elif mutation=='ref': holders['vsl_marginal_price_ref']['FW_E__seg0']-=20.
                elif mutation=='missingcell': del holders['vsl_marginal_price']['FW_E__seg0']
                else: field['reference_levers']['green_times']['SC17_p4']=False
                self.reject_unchanged(f,ref,field)

    def test_cross_price_nonfinite_weight_and_rank_fail_before_install(self):
        for mutation in ('cross','weight','rank'):
            f,ref,field=inputs()
            if mutation=='cross': f.green_offset_cross_price={}
            elif mutation=='weight': f.offset_marginal_price_weight=float('inf')
            else: field['owner_fits']['FW_E']['rank']-=1
            self.reject_unchanged(f,ref,field)

    def test_descriptor_setters_are_rejected_without_partial_install(self):
        f,ref,field=inputs()
        class WithSetter:
            @property
            def metering_marginal_price(self): return self.__dict__.get('metering_marginal_price')
            @metering_marginal_price.setter
            def metering_marginal_price(self,value): raise AssertionError('must not invoke setter')
        protected=WithSetter(); protected.__dict__.update(vars(f))
        self.reject_unchanged(protected,ref,field)


if __name__=='__main__': unittest.main()
