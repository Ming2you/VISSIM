"""Three-block timing, causal derivatives and actuator transition contracts."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import copy
import json
import pickle
import subprocess
import sys
import unittest
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers import sdmpc_sequence as seq, sdmpc_dual as ad
from src.models.state import ControlAction


class SequenceTimingTests(unittest.TestCase):
    def test_future_payload_is_json_safe_and_first_command_is_separate(self):
        controls=[ControlAction(vsl={'FW_E':v}) for v in (120.,100.,80.)]
        plan=seq.pack(controls)
        json.dumps(plan.diagnostics)
        self.assertEqual(plan.vsl,{'FW_E':120.})
        self.assertEqual([c.vsl['FW_E'] for c in seq.actions(plan,3)],[120.,100.,80.])
        self.assertNotIn(seq.KEY,seq.first_action(plan).diagnostics)
        plan.N_P_star=123.; plan.N_UF_star=999.
        self.assertTrue(all(c.N_P_star==123. and c.N_UF_star==999. for c in seq.actions(plan,3)))
        controls[1].vsl['FW_E']=0.
        self.assertEqual(seq.actions(plan,3)[1].vsl['FW_E'],100.)

    def exercise(self,fail=False):
        from src.simulation import coupling
        trace=ad.Trace([.1]*3,track_stencils=False)
        plan=seq.pack([ControlAction(vsl={'FW_E':ad.Dual(1.+k,{k:1.},trace)}) for k in range(3)])
        cfg=SimpleNamespace(network=SimpleNamespace(sdmpc_options={'control_blocks':3}),
                            simulation=SimpleNamespace(T_c_sec=150))
        seen=[]
        def original(s,c,d,conf):
            seen.append(c.vsl['FW_E'])
            s.x=2*s.x+c.vsl['FW_E']
            return s.x
        with patch.object(coupling,'run_coupled_interval',original), patch(
                'evaluation.controllers.area_meter_finalization.for_endpoint',side_effect=lambda c,*a:c):
            state=SimpleNamespace(time_sec=900.,x=0.)
            with seq.prediction_scope(plan,cfg,900.,3) as visits:
                for k in range(3):
                    coupling.run_coupled_interval(state,plan,None,cfg)
                    if k==0:
                        self.assertEqual(ad.derivative(state.x),{0:1.})
                    elif k==1:
                        self.assertEqual(ad.derivative(state.x),{0:2.,1:1.})
                    state.time_sec+=150
                    if fail: raise RuntimeError('synthetic model failure')
            self.assertIs(coupling.run_coupled_interval,original)
        self.assertEqual(ad.derivative(state.x),{0:4.,1:2.,2:1.})
        self.assertEqual([ad.primal(x) for x in seen],[1.,2.,3.])
        self.assertEqual(visits,[0,1,2])

    def test_each_control_has_its_own_causal_jacobian(self): self.exercise()

    def test_incomplete_or_misclocked_prediction_fails_and_restores_hook(self):
        from src.simulation import coupling
        original=coupling.run_coupled_interval
        cfg=SimpleNamespace(network=SimpleNamespace(sdmpc_options={'control_blocks':3}),
                            simulation=SimpleNamespace(T_c_sec=150))
        plan=seq.pack([ControlAction() for _ in range(3)])
        with patch('evaluation.controllers.area_meter_finalization.for_endpoint',side_effect=lambda c,*a:c):
            with self.assertRaisesRegex(ValueError,'Incomplete'):
                with seq.prediction_scope(plan,cfg,900.,3): pass
            self.assertIs(coupling.run_coupled_interval,original)
            with self.assertRaisesRegex(ValueError,'clock'):
                with seq.prediction_scope(plan,cfg,900.,3):
                    coupling.run_coupled_interval(SimpleNamespace(time_sec=1050.),plan,None,cfg)
            self.assertIs(coupling.run_coupled_interval,original)
            with self.assertRaisesRegex(RuntimeError,'synthetic'):
                with seq.prediction_scope(plan,cfg,900.,3): raise RuntimeError('synthetic')
            self.assertIs(coupling.run_coupled_interval,original)

    def test_default_is_unmodified_hold_and_sequence_needs_opt_in(self):
        from src.simulation import coupling
        original=coupling.run_coupled_interval
        cfg=SimpleNamespace(network=SimpleNamespace())
        with seq.prediction_scope(ControlAction(),cfg,900.,3):
            self.assertIs(coupling.run_coupled_interval,original)
        with self.assertRaises(ValueError):
            with seq.prediction_scope(seq.pack([ControlAction()]*3),cfg,900.,3): pass


class SavedCoordinateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from evaluation.controllers import vissim_stackelberg_adapter as adapter, area_follower_objective as joint
        from evaluation.controllers.runtime_setup import install_worker_runtime
        path=ROOT/'diagnostics/tangent_900_h3_v3/request.pickle'
        with path.open('rb') as f: req=pickle.load(f)
        follower,state,reference,forecast=req['owned']
        cfg=follower.cfg
        cfg.network.sdmpc_options.update(control_blocks=3,fifo_batch=True)
        bootstrap=req['bootstrap']
        install_worker_runtime(adapter,cfg,bootstrap['state_json'],bootstrap['detector_mapping'])
        for k,v in req['runtime'].items(): setattr(adapter,k,v)
        adapter._PHASE_VECTOR_FOLLOWER['ref']=follower
        tuning=json.loads((ROOT/'diagnostics/tangent_900_h1/config.json').read_text())
        options=adapter.joint_owner_game_settings(tuning,cfg,'wu-link')
        mapping=adapter.load_optional_json(str(ROOT/tuning['mapping_json']))
        with joint.shared_query_runtime_scope():
            callbacks,context,_=joint._joint_runtime_callbacks(follower,state,forecast,reference,reference,
                mapping,bootstrap['runtime_sources'],reference=reference,total_budget=None,directional={},
                tolerance=options['nuf_tolerance_veh_h'],price_probe=False)
        cls.coord=seq.SequenceCoordinates(cfg,reference,callbacks['move_box'],cfg.network.sdmpc_options)
        cls.reference=reference

    def test_hold_roundtrip_231_coordinates(self):
        c=self.coord; z=c.encode(self.reference)
        self.assertEqual(len(z),231)
        self.assertEqual({a['block'] for a in c.axes},{0,1,2})
        self.assertTrue(c.valid(z))
        got=c.decode(z,self.reference)
        np.testing.assert_array_equal(c.encode(got),z)
        self.assertTrue(c.validate(got)['all_actuator_and_step_constraints_checked'])

    def test_real_plan_has_stable_pickle_across_fresh_worker_boundary(self):
        plan=self.coord.decode(self.coord.encode(self.reference),self.reference)
        data=pickle.dumps(plan,protocol=5)
        self.assertEqual(pickle.dumps(pickle.loads(data),protocol=5),data)
        code=("import sys,pickle;sys.path.insert(0,'vendor/NumSim-mine');"
              "b=sys.stdin.buffer.read();a=pickle.loads(b);"
              "sys.stdout.buffer.write(pickle.dumps(a,protocol=5))")
        child=subprocess.run([sys.executable,'-B','-c',code],input=data,
                             stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=ROOT,check=True)
        self.assertEqual(child.stdout,data)

    def test_configuration_requires_explicit_tangent_three_block_mode(self):
        from evaluation.controllers import sdmpc
        cfg=copy.deepcopy(self.coord.cfg)
        base={'adapter':{'sdmpc':'proxlinear-v1'}}
        self.assertNotIn('control_blocks',sdmpc.configure(base,cfg))
        self.assertNotIn('fifo_batch',cfg.network.sdmpc_options)
        base['adapter'].update(sdmpc_control_blocks=3,sdmpc_fifo_batch=True)
        with self.assertRaises(ValueError):sdmpc.configure(base,cfg)
        base['adapter']['sdmpc_derivatives']='tangent-v1'
        self.assertEqual(sdmpc.configure(base,cfg)['control_blocks'],3)
        for bad in (True,2,3.0):
            base['adapter']['sdmpc_control_blocks']=bad
            with self.assertRaises(ValueError):sdmpc.configure(base,cfg)

    def test_meter_can_move_two_seconds_each_block_beyond_first_box(self):
        c=self.coord; z=c.encode(self.reference)
        j=next(j for j,a in enumerate(c.blocks[0].axes) if a['kind']=='meter')
        a=c.axes[j]
        self.assertEqual(self.reference.diagnostics['rw_meter_green_'+a['key']],10.)
        for k in range(3): z[k*c.width+j]=-2*(k+1)/a['scale']
        got=c.decode(z,self.reference)
        self.assertEqual([x.diagnostics['rw_meter_green_'+a['key']] for x in seq.actions(got,3)],[8.,6.,4.])
        c.validate(got)
        z[c.width+j]=-6/a['scale']
        self.assertFalse(c.valid(z))
        with self.assertRaises(ValueError):c.decode(z,self.reference)

    def test_future_offset_does_not_change_first_command(self):
        c=self.coord; z=c.encode(self.reference)
        j=next(j for j,a in enumerate(c.blocks[0].axes) if a['kind']=='offset' and c.upper[j]>0)
        z[2*c.width+j]=min(.001,c.upper[j]/2)
        got=c.decode(z,self.reference)
        blocks=seq.actions(got,3)
        self.assertEqual(blocks[0].offsets,self.reference.offsets)
        self.assertEqual(blocks[1].offsets,self.reference.offsets)
        self.assertNotEqual(blocks[2].offsets,self.reference.offsets)
        c.validate(got)


if __name__=='__main__': unittest.main()
