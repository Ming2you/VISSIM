"""Bounded offline qualification of the cut dynamics, not a controller receipt."""
import copy
import json
import pickle
import unittest
from pathlib import Path

from evaluation.controllers import vissim_stackelberg_adapter as adapter
from evaluation.controllers import sdmpc_regional_prototype as regional, sdmpc_continuous
from evaluation.controllers.sdmpc_tangent_worker import state_error

CAPTURES = (
    Path('D:/VISSIM_analysis/20261013_solo355_local/projected.pkl'),
    Path('D:/VISSIM_analysis/20261013_solo355_local_4500/projected.pkl'),
)


class RegionalPrototypeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.captures = [pickle.loads(p.read_bytes()) for p in CAPTURES]

    def boundary(self,x,mode):
        c,s,_,_,_=x['args']
        return regional.boundary_requests(x['obs']['merged']['obs150_derived'],mode,
            s.time_sec,c.cfg.network.ramps,s.lane_freeway_runtime.offramps)

    def test_causal_exact_boundary_and_opposite_detector_exclusion(self):
        x=self.captures[0]
        for mode in ('freeway_only','urban_only'):
            original=x['obs']['merged']['obs150_derived']
            derived=copy.deepcopy(original)
            role='ramp_arrival' if mode=='freeway_only' else 'off_entry'
            for key in list(derived['boundaries']):
                if not key.startswith(role+':'):
                    derived['boundaries'][key]={'remote':object()}
            c,s,_,_,_=x['args']
            same=regional.boundary_requests(derived,mode,s.time_sec,c.cfg.network.ramps,s.lane_freeway_runtime.offramps)
            self.assertEqual(same,self.boundary(x,mode))
            self.assertFalse(same['measured_flow_is_capacity'])
            derived['window']['end_s']+=150
            with self.assertRaises(ValueError):
                regional.boundary_requests(derived,mode,s.time_sec,c.cfg.network.ramps,s.lane_freeway_runtime.offramps)

    def test_initial_stock_partition_is_disjoint_and_complete(self):
        for x in self.captures:
            c,s,_,_,_=x['args'];total=0.
            for mode in ('freeway_only','urban_only'):
                local=regional.project_state(s,c.cfg,mode,self.boundary(x,mode))
                for key,row in local._control_area_ledger.stocks.items():
                    if not regional.owns_stock(mode,key):
                        self.assertEqual(sum(row.values()),0.,key)
                total+=sum(row['inside'] for row in local._control_area_ledger.stocks.values())
            self.assertAlmostEqual(total,sum(v['inside'] for v in s._control_area_ledger.stocks.values()),places=8)

    def test_hidden_state_and_forecast_do_not_change_cut_trajectory(self):
        for x in self.captures:
            c,s,f,h,_=x['args'];cfg=c.cfg
            sdmpc_continuous.install(cfg)
            for mode in ('freeway_only','urban_only'):
                boundary=self.boundary(x,mode)
                original=regional.project_state(s,cfg,mode,boundary)
                hidden=copy.deepcopy(s)
                if mode=='freeway_only':
                    for field in regional.URBAN_FIELDS:
                        if hasattr(hidden,field):setattr(hidden,field,{'hidden':1e9})
                    hidden.local_observation_summary={'remote_history':[1e9]*10}
                else:
                    for field in regional.FREEWAY_FIELDS-{'lane_ramp_runtime'}:
                        if hasattr(hidden,field):setattr(hidden,field,{'hidden':1e9})
                    for buffer in hidden.lane_ramp_runtime.buffers.values():
                        for child in [buffer,*getattr(buffer,'_lane_buffers',[])]:
                            child._upstream=[(1e12,1e12)]
                            child._head_ready=1e12
                            child._downstream=[(1e12,1e12)]
                    hidden.local_observation_summary['ramp_spillback']={'hidden':1e12}
                changed=regional.project_state(hidden,cfg,mode,boundary)
                self.assertEqual(state_error(original,changed),0.)
                forecast=copy.deepcopy(f)
                for d in forecast:
                    if mode=='freeway_only':d.urban_boundary=dict.fromkeys(d.urban_boundary,1e12)
                    else:
                        d.freeway_mainline=dict.fromkeys(d.freeway_mainline,1e12)
                        d.incident_capacity_factor=.001;d.freeway_lane_loss={'hidden':{0:100.}}
                    d.ramp_arrival=dict.fromkeys(d.ramp_arrival,1e12)
                a=regional.predict(original,cfg,f,h)
                b=regional.predict(changed,cfg,forecast,h)
                self.assertEqual(a.objective,b.objective)
                self.assertEqual(state_error(a.states,b.states),0.)

    def test_boundary_lane_mix_replaces_stale_urban_offer(self):
        x=self.captures[1];c,s,_,_,_=x['args'];cfg=c.cfg
        boundary=self.boundary(x,'freeway_only')
        ramp=next(r for r,b in s.lane_ramp_runtime.buffers.items() if b.lanes==2 and hasattr(b,'_lane_buffers'))
        boundary['inlets'][ramp]=dict(rate_veh_h=360.,lane_rates_veh_h=[360.,0.])
        other=copy.deepcopy(s)
        other.lane_ramp_runtime.buffers[ramp].lane_arrival_shares=(0.,1.)
        first=regional.project_state(s,cfg,'freeway_only',boundary)
        second=regional.project_state(other,cfg,'freeway_only',boundary)
        self.assertEqual(state_error(first,second),0.)
        buffer=second.lane_ramp_runtime.buffers[ramp]
        self.assertEqual(buffer.lane_arrival_shares,(1.,0.))
        children=buffer._lane_buffers
        self.assertEqual(buffer.current_admission_space(),children[0].current_admission_space())
        old=[b.snapshot()['connector_veh'] for b in children]
        amount=min(.01,buffer.current_admission_space())
        buffer.admit_current(amount)
        self.assertAlmostEqual(children[0].snapshot()['connector_veh'],old[0]+amount)
        self.assertEqual(children[1].snapshot()['connector_veh'],old[1])
        boundary['inlets'][ramp]=dict(rate_veh_h=0.,lane_rates_veh_h=[0.,0.])
        zero=regional.project_state(other,cfg,'freeway_only',boundary)
        self.assertEqual(zero.lane_ramp_runtime.buffers[ramp].lane_arrival_shares,(.5,.5))

    def test_rejected_arrivals_are_retained_with_finite_owned_storage(self):
        x=self.captures[0];c,s,f,h,_=x['args'];cfg=c.cfg
        sdmpc_continuous.install(cfg)
        for mode in ('freeway_only','urban_only'):
            boundary=self.boundary(x,mode)
            for row in boundary['inlets'].values():
                row['rate_veh_h']*=1000
                row['lane_rates_veh_h']=[v*1000 for v in row['lane_rates_veh_h']]
            local=regional.project_state(s,cfg,mode,boundary)
            point=regional.predict(local,cfg,f,h)
            self.assertGreater(sum(point.rejected_arrival_backlog.values()),0.)
            admitted={k:0. for k in boundary['inlets']}
            for row in point.ledger._response['transfers']:
                if row['source'] is None:
                    if mode=='freeway_only' and row['target'].startswith('ramp:'):
                        admitted[row['target'][5:]]+=row['vehicles']
                    elif mode=='urban_only':
                        for off,description in local.lane_offramp_runtime.descriptions.items():
                            if row['target']=='storage:'+description['storage']:
                                admitted[off]+=row['vehicles']
            for key,row in boundary['inlets'].items():
                self.assertAlmostEqual(row['rate_veh_h']*450/3600,
                    admitted[key]+point.rejected_arrival_backlog[key],places=7)

    def test_own_local_queue_changes_prediction(self):
        x=self.captures[0];c,s,f,h,_=x['args'];cfg=c.cfg
        sdmpc_continuous.install(cfg)
        for mode in ('freeway_only','urban_only'):
            local=regional.project_state(s,cfg,mode,self.boundary(x,mode))
            changed=copy.deepcopy(local)
            if mode=='freeway_only':
                ramp=next(r for r,b in changed.lane_ramp_runtime.buffers.items() if b.current_admission_space()>.1)
                changed.lane_ramp_runtime.buffers[ramp].admit_current(.1)
                changed.ramp_queue[ramp]+=.1;key='ramp:'+ramp
            else:
                movement=next(m for m,r in cfg.network.urban_movements.items() if r['signal']=='SC1' and r['kind']=='boundary_in')
                changed.urban_movement_queue[movement]+=.1;key='movement:'+movement
            changed._control_area_ledger.stocks[key]['inside']+=.1
            a=regional.predict(local,cfg,f,h);b=regional.predict(changed,cfg,f,h)
            self.assertGreater(abs(a.objective-b.objective),1e-6)


if __name__=='__main__':unittest.main(verbosity=2)
