
"""Canonical context graph isolation, actual price loader and startup contracts."""
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from diagnostics.solo355_local_20261013.regional_context_probe import load,prepare,inputs,token
from evaluation.controllers import sdmpc,runtime_setup,sdmpc_actuator_scope
from evaluation.controllers import vissim_stackelberg_adapter as adapter
from evaluation.controllers.sdmpc_regional_contracts import active_resources
from evaluation.controllers.sdmpc_regional_context import OWN_NETWORK

CAPTURE='D:/VISSIM_analysis/20261013_solo355_local/projected.pkl'
MODES=('freeway_only','urban_only')


class RegionalContext(unittest.TestCase):
    def test_surrogate_batch_contract_requires_eight_reverse_workers(self):
        for mode in MODES:
            x=load(mode,CAPTURE);cfg=x['args'][0].cfg
            self.assertEqual(cfg.network.sdmpc_options['derivative_workers'],8)
            tuning=json.loads(Path('diagnostics/solo355_local_20261013/'+mode+'_config.json').read_text(encoding='utf-8'))
            for workers in (1,2,4):
                tuning['adapter']['sdmpc_derivative_workers']=workers
                with self.assertRaisesRegex(ValueError,'eight workers'):
                    sdmpc.configure(tuning,cfg)

    def test_all_retained_graph_inputs_ignore_opposite_payloads(self):
        for mode in MODES:
            x=load(mode,CAPTURE)
            baseline=inputs(prepare(x),x)
            before=token(baseline.view)
            y=copy.deepcopy(x);c,s,f,h,m=y['args']
            other='urban_only' if mode=='freeway_only' else 'freeway_only'
            for cfg in (c.cfg,*s.lane_freeway_runtime.configs.values()):
                cfg.network.control_area_meter_context.update(
                    raw={'opposite_records':[999999]},previous_diagnostics={'opposite_price':999},
                    spillback={'opposite_queue':999999},sim_sec=-777)
                for field in OWN_NETWORK[other]:
                    if hasattr(cfg.network,field):setattr(cfg.network,field,{'forbidden_remote':999999})
                cfg.network.forbidden_remote={'raw':[999999]}
            if mode=='freeway_only':
                s.urban_queue=dict.fromkeys(s.urban_queue,999999.)
                s.urban_movement_queue=dict.fromkeys(s.urban_movement_queue,999999.)
                s.lane_urban_runtime=None;s.lane_offramp_runtime=None
                h.N_P_star=999999.
                for demand in f:demand.urban_boundary=dict.fromkeys(demand.urban_boundary,999999.)
            else:
                s.freeway_density={k:[999999.]*len(v) for k,v in s.freeway_density.items()}
                s.freeway_speed={k:[0.]*len(v) for k,v in s.freeway_speed.items()}
                h.N_UF_star=999999.
                for demand in f:
                    demand.freeway_mainline=dict.fromkeys(demand.freeway_mainline,999999.)
                    demand.freeway_lane_loss={'opposite':999};demand.incident_capacity_factor=.001
            for demand in f:demand.ramp_arrival=dict.fromkeys(demand.ramp_arrival,999999.)
            h.diagnostics['remote_diagnostics']={'state':[999999.],'prices':[999999.]}
            h.infeasibility={'remote':999999.}
            c.last_decision={'remote':999999.};c.previous_control={'remote':999999.}
            c.nash_solver._prev_coupling={'remote':999999.}
            c.nash_solver._lambda_UF=999999.;c.nash_solver._lambda_P=999999.
            c.nash_solver.vsl_marginal_price={'remote':999999.}
            c.nash_solver.metering_marginal_price={'remote':999999.}
            role='off_entry' if mode=='freeway_only' else 'ramp_arrival'
            for row in y['obs']['merged']['obs150_derived']['boundaries'].values():
                if row['role']==role:
                    row['cross']=999999.;row['lanes']=[{'cross':999999.}]
            y['kwargs']['worker_bootstrap']['state_json']['raw']={'remote':999999.}
            y['kwargs']['worker_bootstrap']['detector_mapping']['projection_proof']={'remote':999999.}
            with patch.dict(adapter._FW_SEG_CTX_STATE,{'forbidden_remote':{'state':[999999.]}}):
                changed=inputs(prepare(y),y)
                self.assertEqual(before,token(changed.view),mode)
                self.assertEqual(
                    baseline.callbacks['command_evidence'](baseline.seed,baseline.context)['owner_physical_sha256'],
                    changed.callbacks['command_evidence'](changed.seed,changed.context)['owner_physical_sha256'])

    def test_actual_price_path_joins_local_prepared_context(self):
        for mode in MODES:
            x=load(mode,CAPTURE);local=prepare(x);policy=local['controller'].cfg.network.sdmpc_options
            mask=active_resources(mode);inactive=0 if mode=='freeway_only' else 1
            with tempfile.TemporaryDirectory(prefix='regional-context-price-') as directory:
                path=Path(directory)/'offline.json';csv=path.with_suffix('.csv')
                csv.write_text('explicit offline application-receipt fixture',encoding='utf-8')
                Path(str(path)+'.applied').write_text('750\n'+str(csv)+'\n'+str(csv.stat().st_size)+'\n',encoding='utf-16')
                saved=dict(schema=sdmpc.SCHEMA,sim_sec=750.,policy_sha256=sdmpc.policy_token(policy),
                    regional_mode=mode,active_resources=mask,next_prices_scaled=[7.,11.])
                x['kwargs']['previous_path']=path
                def view():
                    path.write_text(json.dumps({'metadata':{'sdmpc_state':saved}}),encoding='utf-8')
                    return inputs(prepare(x),x).view
                base=view();saved['next_prices_scaled'][inactive]={'opposite':999999.}
                self.assertEqual(token(base),token(view()))
                saved['next_prices_scaled'][1-inactive]+=3.
                self.assertNotEqual(token(base),token(view()))
                saved['regional_mode']='urban_only' if mode=='freeway_only' else 'freeway_only'
                with self.assertRaisesRegex(ValueError,'information scope'):view()

    def test_inactive_history_is_rejected_and_active_history_retained(self):
        for mode in MODES:
            x=load(mode,CAPTURE);c,s,f,h,m=x['args'];local=prepare(x)
            self.assertEqual(local['historical'].vsl,h.vsl)
            self.assertEqual(local['historical'].green_times,h.green_times)
            self.assertEqual(local['historical'].ramp_metering,h.ramp_metering)
            if mode=='freeway_only':h.green_times[next(iter(h.green_times))]+=1.
            else:h.diagnostics['rw_meter_green_'+c.cfg.network.ramps[0]]=8.
            with self.assertRaisesRegex(ValueError,'Inactive'):prepare(x)

    def test_startup_legal_native_command_scope_and_no_closed_window(self):
        from src.models.state import ControlAction
        for mode in MODES:
            x=load(mode,CAPTURE);cfg=x['args'][0].cfg
            tuning=json.loads(Path('diagnostics/solo355_local_20261013/'+mode+'_config.json').read_text(encoding='utf-8'))
            adapter.install_config_switches(tuning)
            control=adapter._make_no_control(ControlAction,cfg)
            sdmpc_actuator_scope.check(control,cfg.network.sdmpc_options,cfg)
            from evaluation.controllers import area_meter_finalization,signal_actuation_contract
            area_meter_finalization.assert_writer(control,cfg,require_scored=True)
            signal_actuation_contract.validate_writer(control,cfg,adapter.load_signal_group_actuation_plan(),'experiment')
            for now in (0,1):
                raw={'sim_sec':now,'obs150':{'sim_sec':now,'k':None,'window':None}}
                self.assertTrue(runtime_setup.native_startup_without_prediction(tuning,raw,'wu-link'))
                raw['obs150']['window']={'start_s':0,'end_s':now}
                self.assertFalse(runtime_setup.native_startup_without_prediction(tuning,raw,'wu-link'))
            self.assertFalse(runtime_setup.native_startup_without_prediction(
                tuning,{'sim_sec':150,'obs150':{'sim_sec':150}},'wu-link'))

if __name__=='__main__':unittest.main()
