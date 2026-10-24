"""Conservation, persistence and causal cutoff of the past-window estimator."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace as NS

from evaluation.controllers.freeway_fd import VSLExposure
from evaluation.controllers.vsl_exposure_history import cell_fluxes, assimilate, read_commands, initialize, permanent_nominal_counts, constrain_nominal
from evaluation.controllers import obs150_contract as oc

HERE=Path(__file__).resolve().parents[1]
HEADER=b'sim_sec,dsd_no,veh_class_no,requested_kph,readback_distribution_no,ok,stage\n'


class History(unittest.TestCase):
    def test_nominal_floor_roundoff_cannot_borrow_nonexistent_mass(self):
        # Actual NC1350 cell2: all110, observed33, integrated32.99999999999862.
        total=32.99999999999862
        e=VSLExposure([total],dict(sign_cells=[0],initial_command=110,ramp_command=110),110)
        before=copy.deepcopy(e.cohorts)
        self.assertEqual(constrain_nominal(e,[33.],110.),0.)
        self.assertEqual(e.cohorts,before)
        # A tolerable excess cannot create extra stock in a mixed cohort either.
        e.cohorts=[{110.:20.,80.:total-20.}]
        constrain_nominal(e,[33.],110.)
        self.assertEqual(e.cohorts,[{110.:total}])
        with self.assertRaisesRegex(ValueError,'lower bound'):
            constrain_nominal(e,[33.001],110.)

    def test_nominal_geometry_never_erases_past_restriction_after_release(self):
        parts=[]
        for no,pos in ((63,25),(64,35),(71,75)):
            parts.append(f'<desSpeedDecision no="{no}" lane="1 1" pos="{pos}" timeFrom="0" timeTo="99999"><vehClassDesSpeedDistr><vehClassDesSpeedDistribution vehClass="10" desSpeedDistr="110"/></vehClassDesSpeedDistr></desSpeedDecision>')
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'net.inpx';p.write_text('<network><desSpeedDecisions>'+''.join(parts)+'</desSpeedDecisions></network>')
            g=dict(addresses={'1':['FW_E',0.]},bounds={'FW_E':[0.,100.]})
            vehicles=[[i,1,1,x] for i,x in enumerate((20.,30.,50.,60.,80.))]
            groups=[dict(dsds=[63,64]),dict(dsds=[71])]
            old=[dict(dsd_no=str(no),readback_distribution_no=str(cmd)) for cmd in (80,110) for no in (63,64)]
            self.assertEqual(permanent_nominal_counts(p,vehicles,g,'FW_E',groups,old,110.,450),[1.])
            self.assertEqual(permanent_nominal_counts(p,vehicles,g,'FW_E',groups,[],110.,150),[3.])
    def test_nominal_constraint_conserves_mass_and_only_uses_lower_bound(self):
        e=VSLExposure([10.],dict(sign_cells=[0],initial_command=110,ramp_command=110),110)
        e.cohorts=[{110.:2.,90.:6.,80.:2.}];e.tangents=[{c:0. for c in e.cohorts[0]}]
        self.assertEqual(constrain_nominal(e,[6.],110.),4.)
        self.assertEqual(e.cohorts,[{90.:3.,80.:1.,110.:6.}])
        self.assertEqual(constrain_nominal(e,[5.],110.),0.)
        with self.assertRaisesRegex(ValueError,'lower bound'):constrain_nominal(e,[11.],110.)

    def test_closed_native_cell_crossings(self):
        fixture=json.loads((HERE/'integration_20260926/past_flow_fixture.json').read_text(encoding='utf8'))
        for row in fixture['rows']:
            with self.subTest(arm=row['arm'],start=row['start']):
                names=('old','new','entry','merges','exits','removed','terminal')
                got=cell_fluxes(*(row[name] for name in names))
                self.assertEqual(got,row['mainline'])
                spec=dict(sign_cells=[0,3,5,8,14,16,26,28],initial_command=110,ramp_command=110)
                exp=VSLExposure(row['old'],spec,110)
                after=assimilate(exp,*(row[name] for name in names),[110]*31,150,1)
                for cohort,n in zip(after.cohorts,row['new']):
                    self.assertAlmostEqual(sum(cohort.values()),n,places=7)
                    self.assertLessEqual(set(cohort),{110.})
                self.assertEqual(exp.cohorts,VSLExposure(row['old'],spec,110).cohorts)

    def test_restriction_is_carried_after_release(self):
        spec=dict(sign_cells=[0],initial_command=110,ramp_command=110)
        initial=VSLExposure([100.],spec,110)
        args=([100.],[100.],10.,[0.],[0.],[0.],10.)
        lower=assimilate(initial,*args,[80.],150,1)
        self.assertGreater(lower.cohorts[0][80.],9.)
        released=assimilate(lower,*args,[110.],150,1)
        self.assertGreater(released.cohorts[0][80.],8.)
        self.assertLess(released.cohorts[0][80.],lower.cohorts[0][80.])
        self.assertAlmostEqual(sum(released.cohorts[0].values()),100.)
        self.assertEqual(initial.cohorts,[{110.:100.}])

    def test_empty_cell_with_past_through_traffic(self):
        spec=dict(sign_cells=[0],initial_command=110,ramp_command=110)
        result=assimilate(VSLExposure([0.,0.],spec,110),[0.,0.],[0.,10.],20.,[0.,0.],[0.,0.],[0.,0.],10.,[80.,None],150,1)
        self.assertFalse(result.cohorts[0])
        self.assertAlmostEqual(result.cohorts[1][80.],10.)

    def test_missing_mass_and_bad_checkpoint_rejected(self):
        with self.assertRaisesRegex(ValueError,'terminal'):
            cell_fluxes([10.],[10.],5.,[0.],[0.],[0.],4.)
        with self.assertRaisesRegex(ValueError,'Negative'):
            cell_fluxes([0.],[10.],0.,[0.],[0.],[0.],0.)
        exp=VSLExposure([4.],dict(sign_cells=[0],initial_command=110,ramp_command=110),110)
        with self.assertRaisesRegex(ValueError,'previous stock'):
            assimilate(exp,[5.],[5.],0.,[0.],[0.],[0.],0.,[110.],150,1)

    def test_readback_uses_past_and_rejects_unverified_changes(self):
        xml='<network><desSpeedDecisions><desSpeedDecision no="63"><vehClassDesSpeedDistr><vehClassDesSpeedDistribution vehClass="10" desSpeedDistr="110"/></vehClassDesSpeedDistr></desSpeedDecision></desSpeedDecisions></network>'
        groups=[dict(dsds=[63])];allowed=[50,60,70,80,90,100,110]
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'net.inpx';path.write_text(xml,encoding='utf8')
            past=HEADER+b'150,63,10,80,80,1,immediate\n'
            expected=read_commands(path,past,groups,[0],2,150,300,allowed)
            actual=read_commands(path,past+b'300,63,10,50,50,0,immediate\n',groups,[0],2,150,300,allowed)
            self.assertEqual(actual,expected)
            self.assertEqual(expected[0],[80.,None]);self.assertTrue(expected[1])
            with self.assertRaisesRegex(ValueError,'Unverified'):
                read_commands(path,past.replace(b'80,80,1',b'80,90,1'),groups,[0],2,150,300,allowed)
            delayed=read_commands(path,past.replace(b'150,63',b'151,63'),groups,[0],2,150,300,allowed)
            self.assertEqual(delayed[0],[110.,None]);self.assertEqual(delayed[3],{1.:[80.,None]})

    def test_first_second_command_does_not_retag_before_it_is_applied(self):
        spec=dict(sign_cells=[0],initial_command=110,ramp_command=110)
        args=([0.],[20.],20.,[0.],[0.],[0.],0.)
        result=assimilate(VSLExposure([0.],spec,110),*args,[110.],150,5,changes={1.:[80.]})
        self.assertAlmostEqual(result.cohorts[0][110.],20/150)
        self.assertAlmostEqual(result.cohorts[0][80.],20*149/150)

    def test_runtime_posterior_persistence_and_stale_history(self):
        """Three observation decisions, not three copies of one model state."""
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'obs150').mkdir()
            network=root/'network.inpx'
            network.write_text('<network><desSpeedDecisions><desSpeedDecision no="63" lane="1 1" pos="0"><vehClassDesSpeedDistr><vehClassDesSpeedDistribution vehClass="10" desSpeedDistr="110"/></vehClassDesSpeedDistr></desSpeedDecision></desSpeedDecisions></network>',encoding='utf8')
            spec=dict(sign_cells=[0],initial_command=110,ramp_command=110)
            groups=[dict(road='FW_E',parent=0,dsds=[63])]
            geometry=dict(cells=[dict(road='FW_E',length_km=1.)],addresses={'1':['FW_E',0.]},bounds={'FW_E':[0.,1000.]},boundaries=[])
            context=dict(plant_mode='v2',manifest_sha256='a'*64,geometry=geometry,paths={'network':network})
            cfg=NS(network=NS(physical_vsl_sign_binding=True,physical_vsl_groups=groups),freeway_follower=NS(vsl_set=list(range(50,111,10))))
            conf=NS(network=NS(component_vsl_transport={'FW_E':spec}),simulation=NS(T_f_sec=1))
            frames={}
            for t in (0,150,300,450):
                path=root/f'frame_{t:06d}.json'
                doc=dict(schema=oc.FRAME_SCHEMA,complete=True,time_s=t,run_id='test',
                    vehicles=[] if t==0 else [[i+1,1,1,float(i+1),30.,5.]+[None]*9 for i in range(100)])
                path.write_bytes(oc.canonical_json_bytes(doc));frames[t]=dict(path=path.name,sha256=oc.file_sha256(path))
            (root/'vsl_readback.csv').write_bytes(HEADER+b'150,63,10,80,80,1,immediate\n300,63,10,110,110,1,immediate\n')
            def call(end,**kwargs):
                raw={oc.RAW_STATE_KEY:dict(sim_sec=end,directory=str(root),run_id='test',frames={'current':frames[end],'previous':frames[end-150]}),
                    oc.MERGED_DERIVED_KEY:dict(boundaries={'source:FW_E':{'cross':100 if end==150 else 10},'chain_end:FW_E':{'cross':0 if end==150 else 10}},removals={'rows':[]})}
                state=NS(lane_freeway_runtime=NS(configs={'FW_E':conf}),freeway_density={'FW_E':[100.]},freeway_effective_lanes={'FW_E':[1.]})
                receipt=initialize(context,raw,state,cfg,**kwargs)
                return state._component_vsl_exposure['FW_E'],receipt
            first,_=call(150);self.assertEqual(set(first.cohorts[0]),{110.})
            lower,_=call(300);self.assertGreater(lower.cohorts[0][80.],9.)
            released,receipt=call(450);self.assertGreater(released.cohorts[0][80.],8.)
            self.assertLess(released.cohorts[0][80.],lower.cohorts[0][80.])
            self.assertEqual(call(450)[1],receipt)
            # A different model must reconstruct the same observed history in
            # its own cache, without weakening identity checks or overwriting.
            native={p:p.read_bytes() for p in (root/'obs150').glob('*.json')}
            scratch=root/'candidate_history';scratch.mkdir()
            context['manifest_sha256']='b'*64
            with self.assertRaisesRegex(ValueError,'another run'):call(450)
            with self.assertRaisesRegex(ValueError,'Missing prior'):call(450,history_directory=scratch)
            for end,expected in ((150,first),(300,lower),(450,released)):
                rebuilt,_=call(end,history_directory=scratch)
                self.assertEqual(rebuilt.cohorts,expected.cohorts)
            self.assertEqual({p:p.read_bytes() for p in native},native)
            context['manifest_sha256']='a'*64
            with self.assertRaisesRegex(ValueError,'another run'):call(450,history_directory=scratch)
            prior=root/'obs150/vsl_cohorts_000300.json';saved=prior.read_bytes();prior.unlink()
            with self.assertRaisesRegex(ValueError,'Missing prior'):
                call(450)
            bad=json.loads(saved);bad['run_id']='other-run';prior.write_bytes(oc.canonical_json_bytes(bad))
            with self.assertRaisesRegex(ValueError,'another run'):
                call(450)


if __name__=='__main__':unittest.main()
