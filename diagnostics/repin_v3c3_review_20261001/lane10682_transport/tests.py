"""Conservation and actual exit receipts of the connected local allocator."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OLD=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/baseline_reproduction_20260929/cellwise_calibration/freeway_first/joint_lane_fifo/test_candidate.txt'
text=OLD.read_text(encoding='utf8')
text=text.replace("dict(lane_index=g+1,speed_kph=72.)","dict(lane_no=g+1,speed_kph=72.)")
text=text.replace("cell=3,weights=", "cell=3,route_weights=").replace("input='test',weights=", "input='test',route_weights=")
text=text.replace("    joint=RouteLaneRegion(spec,state,cfg,fw,rows)",
    "    state.offramp_route_inventory_state['lane_cells']={fw:[[{}] for _ in routes]}\n"
    "    for i in spec['cells']:\n"
    "        state.offramp_route_inventory_state['lane_cells'][fw][i]=[{k:n/3 for k,n in routes[i].items()} for _ in range(3)]\n"
    "    joint=RouteLaneRegion(spec,state,cfg,fw,rows)")
namespace={'__name__':'archived_test_reused'}
exec(compile(text,str(OLD),'exec'),namespace)
fixture=namespace['fixture'];Base=namespace['JointRouteLaneTests']
routing=namespace['routing']

class Transfers(Base):
    def test_two_lane_exit_and_merge_use_both_lanes_and_one_shared_budget(self):
        state,cfg,joint=fixture()
        joint.off_access['exit']=(0,1)
        joint.ramp_access['ramp']=(0,1)
        joint.plan(state,cfg,[100.]*5,{'exit':10.},[100.]*4,[1000000.]*5,
                   {'ramp':360.},{'exit':180.})
        self.assertAlmostEqual(sum(joint.off_sent['exit']),.05)
        self.assertAlmostEqual(joint.off_sent['exit'][0],.025)
        self.assertAlmostEqual(joint.off_sent['exit'][1],.025)
        self.assertEqual(joint.off_sent['exit'][2],0.)
        self.assertAlmostEqual(sum(joint.merge[3]),.1)
        self.assertGreater(joint.merge[3][0],0.)
        self.assertGreater(joint.merge[3][1],0.)
        self.assertEqual(joint.merge[3][2],0.)

    def test_existing_effective_lane_loss_is_preserved_without_removing_stock(self):
        state,cfg,joint=fixture()
        old=copy.deepcopy(state.offramp_route_inventory_state)
        joint.plan(state,cfg,[100.]*5,{'exit':10.},[100.]*4,[1000000.,1000000.,100.,1000000.,1000000.],
            {'ramp':0.},{'exit':3600.},effective_lanes=[3.,3.,2.9067194769883766,3.,3.])
        self.assertAlmostEqual(sum(joint.widths[2]),2.9067194769883766)
        self.assertEqual(joint.widths[2][1:],[1.,1.])
        self.assertLessEqual(sum(joint.incoming[2]),100./3600+1e-10)
        self.assertEqual(old,state.offramp_route_inventory_state)

    def test_urban_receipt_equals_debited_route_classes(self):
        state,cfg,joint=fixture(True)
        off=self.advance(state,cfg,joint)
        receipt=state.offramp_route_inventory_state['last_offramp_receipts']['FW_E']
        self.assertAlmostEqual(sum(receipt['ports']['exit'].values()),off['exit']/3600)
        self.assertEqual(receipt['ports']['exit'],joint.off_classes['exit'])

    def test_mismatched_accepted_face_is_rejected(self):
        state,cfg,joint=fixture()
        joint.plan(state,cfg,[100.]*5,{'exit':10.},[100.]*4,[1000000.]*5,{'ramp':0.},{'exit':3600.})
        with self.assertRaisesRegex(ValueError,'face differs'):
            routing.advance_inventory(state,cfg,'FW_E',mainline=[1.]*4,terminal=0,offramps={},
                entry=0,generated=0,merges={'ramp':0},duration_h=1/3600)

if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Transfers)
    path=HERE.parent/'lane10682_feasibility/check_partition.py'
    spec=importlib.util.spec_from_file_location('partition_previous',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(module.Partition))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    target=HERE/'tests.json';assert not target.exists()
    target.write_text(json.dumps(dict(tests=result.testsRun,errors=len(result.errors),failures=len(result.failures),
        passed=result.wasSuccessful(),scope='class transport, receipts, native init and default transport; not physical forecast'),indent=2)+'\n')
    raise SystemExit(not result.wasSuccessful())
