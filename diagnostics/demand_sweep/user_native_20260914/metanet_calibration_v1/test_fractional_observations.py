"""Native fractional-clock and refined-grid regression checks; no VISSIM."""
import copy
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

from extract_observations import Observer, PortObserver, native_frames, synthetic_tests, skipped_mainline_between_ports
from boundary_factory import build_window, self_test
from scoring import score_rollout


class FractionalObservations(unittest.TestCase):
    def test_two_port_passage_preserves_mainline_flow_without_sampled_stock(self):
        ramp=dict(id='ramp',kind='ramp',road='FW_W',connector=2,to_link=1,to_pos_m=90.,to_cell=0,from_cell=None)
        off=dict(id='off',kind='offramp',road='FW_W',connector=3,from_link=1,from_pos_m=110.,from_cell=1,to_cell=None)
        g=dict(addresses={1:('FW_W',0)},sources={},bounds={'FW_W':[0,100,200]},
            cells=[dict(road='FW_W',cell=i,lane_km=.1) for i in range(2)],
            chains={'FW_W':[{'link':1}]},boundaries=[ramp,off],direct_connector_pairs=[])
        obs=Observer(g,interval_sec=5,phase_sec=.1)
        for t in range(5,31,5):obs.advance(t+.1,{1:(2 if t==5 else 3,1,10.,50.)})
        self.assertEqual(sum(r['ramp_merges'] for r in obs.flows),1)
        self.assertEqual(sum(r['off_departures'] for r in obs.flows),1)
        self.assertEqual(sum(r['downstream_crossings'] for r in obs.flows),1)
        self.assertEqual(sum(r['conservation_residual_veh'] for r in obs.flows),0)
        self.assertTrue(all(r['n_veh']==0 for r in obs.cells))
        self.assertIsNone(skipped_mainline_between_ports(None,(3,1,10,50),{2:ramp},{3:off}))
        self.assertIsNone(skipped_mainline_between_ports((2,1,10,50),(3,1,10,50),{2:ramp},{3:{**off,'from_pos_m':80}}))
        self.assertIsNone(skipped_mainline_between_ports((2,1,10,50),(3,1,10,50),{2:ramp},{3:{**off,'from_link':4}}))

    def test_fractional_fzp_preserves_phase_and_rejects_missing_frame(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'test.fzp'
            header='$VEHICLE:SIMSEC;NO;LANE\\LINK\\NO;LANE\\INDEX;POS;SPEED\n'
            p.write_text(header+'5.10;1;1;1;1;10\n10.10;1;1;1;2;10\n')
            rows=list(native_frames(p,{},deadline=time.monotonic()+5,interval_sec=5,phase_sec=.1))
            self.assertEqual([r[0] for r in rows],[5.1,10.1])
            p.write_text(header+'5.10;1;1;1;1;10\n15.10;1;1;1;2;10\n')
            with self.assertRaises((ValueError,AssertionError,RuntimeError)):
                list(native_frames(p,{},deadline=time.monotonic()+5,interval_sec=5,phase_sec=.1))

    def test_fractional_connector_skip_and_conservation(self):
        g={'addresses':{1:('FW_E',0)},'sources':{1:'source'},'bounds':{'FW_E':[0,100,200]},
           'cells':[{'road':'FW_E','cell':i,'lane_km':.1} for i in range(2)],
           'chains':{'FW_E':[{'link':1}]},'boundaries':[
           {'id':'source','kind':'source','road':'FW_E','connector':None,'from_cell':None,'to_cell':0},
           {'id':'off','kind':'offramp','road':'FW_E','connector':2,'from_cell':1,'to_cell':None,'from_pos_m':150,'to_pos_m':0}],
           'direct_connector_pairs':[{'from_link':1,'to_link':3,'connectors':[2]}]}
        obs=Observer(g,interval_sec=5,phase_sec=.1)
        port=PortObserver(g,interval_sec=5,phase_sec=.1)
        for t in range(5,61,5):
            frame={1:(1,1,90,40)} if t<15 else {1:(3,1,10,40)}
            obs.advance(t+.1,frame);port.advance(t+.1,frame)
        self.assertEqual([r['time_s'] for r in obs.cells],[0,0,30.1,30.1,60.1,60.1])
        self.assertEqual(sum(r['off_departures'] for r in obs.flows),1)
        self.assertEqual(sum(r['conservation_residual_veh'] for r in obs.flows),0)
        self.assertEqual(port.rows[0]['departures_veh'],1)

    def test_refined_fractional_window_no_future_leak_and_exact_score(self):
        t0=900.1;times=[round(t0+d,6) for d in range(-120,451,30)]
        cells=[{'road':'FW_E','cell':i,'lane_km':.3} for i in range(31)]
        d=SimpleNamespace(phase_sec=.1,geometry={'cells':cells},
            definitions={'src':{'kind':'source','road':'FW_E'}},
            cells={t:[dict(time_s=t,road='FW_E',cell=i,n_veh=10.,v_kmh=90.,rho_veh_per_km_lane=10/.3) for i in range(31)] for t in times},
            boundaries={(t,'src'):{'crossings':30,'cumulative_crossings':1000} for t in times},
            flows={(t,'FW_E',i):dict(downstream_crossings=0,off_departures=0,terminal_exits_inferred=0) for t in times for i in range(31)},
            desired_before=lambda road,t:1000,demand_vph=lambda road,t:3600)
        w=build_window(d,t0,'history_forecast',model_step_sec=5)
        before=copy.deepcopy(w)
        for t in times:
            if t>t0:d.boundaries[t,'src']['crossings']=99999
        self.assertEqual(before,build_window(d,t0,'history_forecast',model_step_sec=5))
        self.assertEqual(len(w['boundary_steps']),90)
        rollout={'cells':[r for t,rs in d.cells.items() if t>t0 for r in rs],
            'flows':[dict(window_end_s=t,road='FW_E',cell=i,downstream_crossings=0,off_departures=0,terminal_exits=0) for t in times if t>t0 for i in range(31)],
            'diagnostics':{'roads':[dict(road='FW_E',density_projection_count=0,jam_density_exceedance_count=0,negative_density_count=0,continuity_residual_max_veh=0)]}}
        score=score_rollout(d,t0,rollout,'FW_E')
        self.assertEqual(score['objective'],0)
        self.assertEqual(score['speed']['count'],465)

    def test_legacy_contracts(self):
        self.assertEqual(synthetic_tests()['status'],'PASS')
        self_test()

    def test_five_second_endpoint_speeds_do_not_reject_verified_path(self):
        g={'addresses':{1:('FW_E',0),2:('FW_E',100),3:('FW_E',120)},
           'sources':{1:'source'},'bounds':{'FW_E':[0,100,200]},
           'cells':[{'road':'FW_E','cell':i,'lane_km':.1} for i in range(2)],
           'chains':{'FW_E':[{'link':i} for i in (1,2,3)]},
           'boundaries':[{'id':'source','kind':'source','road':'FW_E','connector':None,'from_cell':None,'to_cell':0}],
           'direct_connector_pairs':[{'from_link':1,'to_link':3,'connectors':[2]}]}
        obs=Observer(g,interval_sec=5,phase_sec=.1)
        for t in range(5,31,5):
            obs.advance(t+.1,{1:(1,1,90,0)} if t==5 else {1:(3,1,0,0)})
        self.assertEqual(sum(r['downstream_crossings'] for r in obs.flows),1)
        self.assertEqual(sum(r['unexplained_entries'] for r in obs.flows),0)
        self.assertEqual(len(obs.position_verified_transitions),1)
        obs.advance(35.1,{1:(1,1,90,0)})
        self.assertEqual(obs.evidence[-1]['reason'],'nonforward_or_implausible_chain_jump')


if __name__=='__main__': unittest.main()
