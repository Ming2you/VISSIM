"""Common approaches conserve admitted inputs without bypassing selected heads."""
from copy import deepcopy
import json
from pathlib import Path
import pickle
import tempfile
import unittest
from diagnostics.test_native_internal_input import ROOT, NativeInputTests, OPTION
from evaluation.controllers import native_internal_input as native, area_runtime
from src.models.demand import DemandStep


class CommonApproachTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        NativeInputTests.setUpClass()
        cls.base=NativeInputTests()
        cls.document=json.loads((ROOT/OPTION['urban']['native_internal_inputs']).read_text(encoding='utf-8'))

    def configure_data(self,data):
        f=self.base.f
        with tempfile.TemporaryDirectory(dir=ROOT/'diagnostics') as directory:
            path=Path(directory)/'evidence.json';path.write_text(json.dumps(data),encoding='utf-8')
            return native.configure(deepcopy(f.cfg),{'urban':{'native_internal_inputs':str(path)}},f.raw,f.detectors)

    def test_actual_source_and_connector_stock_once_initial_events_zero(self):
        cfg,state,detectors,raw=self.base.fixture()
        assigned=state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
        for no in ('1085','1095','1097'):
            row=cfg.network.native_internal_inputs['inputs'][no]
            for link in row['physical_projection_links']:
                count=raw['vehicle_records']['full_network_link_counts'].get(link,0)
                self.assertEqual(assigned.get(link,{}),{'storage:'+row['target_storage']:float(count)} if count else {})
                self.assertEqual(detectors['link_to_origins'][link],[row['target_storage']])
                self.assertNotIn(link,detectors['link_to_movements'])
        ledger=state._control_area_ledger
        self.assertEqual((ledger.entered_veh,ledger.ttd_veh,ledger.event_count),(0,0,0))
        ledger.assert_stocks(area_runtime.model_inventory(state,cfg))

    def test_future_sources_once_finite_admission_paired_buffers_and_private_state(self):
        cfg,state,_,_=self.base.fixture();before=area_runtime.model_inventory(state,cfg);initial=pickle.dumps(state)
        copied=state.copy();index=copied.native_internal_input_state['last_step']+1
        rows=native.advance(copied,None,DemandStep({}, {}, {}),cfg,index)['native_internal_input_step']
        after=area_runtime.model_inventory(copied,cfg)
        self.assertEqual(pickle.dumps(state),initial)
        self.assertAlmostEqual(sum(rows[n]['desired_veh'] for n in ('1085','1095','1097')),800*5/3600)
        for no,row in rows.items():
            target=cfg.network.native_internal_inputs['inputs'][no]['target_storage'];admitted=row['generated_inside_veh']
            self.assertAlmostEqual(after['storage:'+target]-before['storage:'+target],admitted)
            self.assertAlmostEqual(copied._control_area_ledger.flow_counts['input:internal:'+no],admitted)
            for name in ('urban_arrival_buffer','urban_storage_release_buffer'):
                self.assertAlmostEqual(sum(getattr(copied,name).get(target,{}).values())-sum(getattr(state,name).get(target,{}).values()),admitted)
            self.assertEqual(row['boundary_entry_veh'],0)
        copied._control_area_ledger.assert_stocks(after)
        self.assertEqual((copied._control_area_ledger.entered_veh,copied._control_area_ledger.ttd_veh),(0,0))

    def test_missing_branch_and_invalid_native_filter_rejected(self):
        data=deepcopy(self.document);data['inputs']['1085']['approach_paths'].pop()
        with self.assertRaisesRegex(ValueError,'omit or invent'):self.configure_data(data)
        data=deepcopy(self.document);data['inputs']['1085']['branch_coverage']['138']={'basis':'native_decision','decision':'1034'}
        with self.assertRaisesRegex(ValueError,'absent, restricted or behind'):self.configure_data(data)

    def test_source21_cannot_skip_selected_sc108_signal(self):
        data=deepcopy(self.document)
        data['inputs']['1083']=json.loads((ROOT/'diagnostics/native_internal_input_deferred_paths.json').read_text())['1083']
        with self.assertRaisesRegex(ValueError,'source=21 head=90030805 sg=108 2'):self.configure_data(data)

    def test_group_membership_not_controller_alone_defines_selected_signal(self):
        cfg,_,_,_=self.base.fixture();row=cfg.network.native_internal_inputs['inputs']['1097']
        self.assertIn('90030811',row['intermediate_unselected_heads'])
        self.assertEqual(set(row['approach_heads']),{'70301','70801','70802'})

    def test_wrong_receiver_rejected(self):
        data=deepcopy(self.document);data['inputs']['1085']['target_storage']='in_SC6_S'
        with self.assertRaisesRegex(ValueError,'lacks its canonical stopline'):self.configure_data(data)

    def test_all34_schedule_field_is_explicit_opt_in_and_plain_data(self):
        f=self.base.f;off=deepcopy(f.cfg);native.configure(off,OPTION,f.raw,f.detectors)
        self.assertFalse(hasattr(off.network,'native_input_schedule'))
        on=deepcopy(f.cfg);tuning=deepcopy(OPTION);tuning['prediction']={'native_input_schedule':True}
        metadata=native.configure(on,tuning,f.raw,f.detectors);field=on.network.native_input_schedule
        self.assertEqual(metadata['native_input_schedule_inputs'],34)
        self.assertEqual(field['schema'],'native-input-schedule/v1')
        self.assertEqual(sum(r['status']=='internal' for r in field['inputs'].values()),10)
        self.assertEqual(sum(r['status']=='mapped' for r in field['inputs'].values()),21)
        self.assertEqual(field,pickle.loads(pickle.dumps(field)))
        self.assertEqual(field['inputs']['1101']['status'],'shared_stem_unmapped')
        with self.assertRaisesRegex(ValueError,'requires a validated native input declaration'):
            native.configure(deepcopy(f.cfg),{'prediction':{'native_input_schedule':True}},f.raw,f.detectors)


if __name__=='__main__':unittest.main(verbosity=2)
