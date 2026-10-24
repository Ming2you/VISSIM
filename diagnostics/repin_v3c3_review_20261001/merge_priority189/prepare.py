"""Freeze one diagnostic merge-priority candidate; do not edit production physics."""
import ast
import copy
import json
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent


def main():
    assert not (HERE/'protocol.json').exists()
    source_path=h.R/'spatial_context148/forecast/executed_function_sources.json'
    baseline=h.read(source_path);source=copy.deepcopy(baseline)
    cls=source['RouteLaneRegion']
    old="        self.rows = []"
    assert cls.count(old)==1
    cls=cls.replace(old,old+'''
        self.merge_priority = dict(spec.get('merge_priority189', {}))
        if any(r != 'RM_C10490' or not math.isfinite(p) or not 0. <= p <= 1.
               for r,p in self.merge_priority.items()):
            raise ValueError('189 only tests the cell21 merge priority')
        self.priority_rows = []''')
    old='def ramp_supply(self, ramp, cfg):'
    assert cls.count(old)==1
    cls=cls.replace(old,'def ramp_supply(self, ramp, cfg, branch_capacity=None, time_s=None):')
    start=cls.index('    def ramp_supply(');end=cls.index('\n    def ',start+5)
    section=cls[start:end]
    assert section.count('        return supply')==1
    section=section.replace('        return supply','''        if ramp not in self.merge_priority:
            return supply
        if i != 21 or self.ramp_access[ramp] != 0 or self.reciprocal_off != '10483':
            raise ValueError('189 requires the verified20--21 shared right-lane node')
        if branch_capacity is None:
            raise ValueError('Current off-ramp receiving is required before reserving mainline room')
        upstream=i-1; g=self.ramp_access[ramp]
        dt=cfg.simulation.T_f_h
        fraction=min(1.,self.v[upstream][g]*dt/self.lengths[upstream])
        through=0.; exit_request=0.
        for key,n in self.stocks[upstream][g].items():
            if key.rsplit('|',1)[-1] == self.reciprocal_off:
                exit_request += n*fraction/dt
            else:
                through += n*fraction/dt
        off_factor=min(1.,max(0.,branch_capacity[self.reciprocal_off])/exit_request) if exit_request else 1.
        # Off-FIFO is applied before the merge competition. Reserving the raw
        # through demand would waste receiving when the exit is blocked.
        feasible_through=through*off_factor
        priority=self.merge_priority[ramp]
        budget=self._shared_ramp_supply(supply,feasible_through,priority)
        self.priority_rows.append(dict(time_s=time_s,ramp=ramp,receiving_vph=supply,
            mainline_raw_vph=through,exit_request_vph=exit_request,
            exit_capacity_vph=branch_capacity[self.reciprocal_off],off_factor=off_factor,
            mainline_feasible_vph=feasible_through,priority=priority,ramp_budget_vph=budget))
        return budget''')
    cls=cls[:start]+section+cls[end:]
    cls+='''
    @staticmethod
    def _shared_ramp_supply(receiving,mainline,priority):
        # Two-input supply sharing, with unused mainline entitlement returned.
        # The physical ramp buffer subsequently clips this by actual ready
        # demand, canonical receiving and the existing gap bound. plan() gives
        # every unused ramp entitlement back to the FIFO-feasible mainline.
        return min(receiving,max(priority*receiving,receiving-mainline))
'''
    ast.parse(cls);source['RouteLaneRegion']=cls
    old='joint_lanes.ramp_supply(ramp,cfg)'
    assert source['rollout'].count(old)==1
    source['rollout']=source['rollout'].replace(old,'joint_lanes.ramp_supply(ramp,cfg,branch_capacity=caps,time_s=state.time_sec)')
    ast.parse(source['rollout'])
    # Every unrelated class method and frozen physical function stays exact.
    def methods(s):
        return {n.name:ast.dump(n) for n in ast.parse(s).body[0].body if isinstance(n,ast.FunctionDef)}
    a,b=methods(baseline['RouteLaneRegion']),methods(cls)
    assert all(b[k]==v for k,v in a.items() if k not in ('__init__','ramp_supply'))
    spec=h.read(h.R/'queue_dynamics178/spec.json');spec.pop('queue178')
    spec['merge_priority189']={'RM_C10490':.5}
    proto=h.read(h.R/'queue_dynamics178/protocol.json')
    for key in ('train','fit','cells','inputs','limitations'):proto.pop(key,None)
    proto.update(hypothesis='Does ramp-first shared receiving distort merge delay and the upstream exit/recovery response?',
        source='Exact148/132 with171 prehead storage; only10490 receives two-input priority instead of ramp-first.',
        formula='Dr=min(available canonical/gap/ready, max(p R, R-Dm)); Dm=raw lane20 through request * off-capacity FIFO factor. Existing plan returns unused ramp room to mainline and preserves reciprocal off FIFO.',
        literature='Wright et al.2017 On node models for high-dimensional road networks, section3.1 and partial-FIFO discussion; https://arxiv.org/html/1601.01054v3',
        assumptions='p=.5 is one fixed equal-priority structural probe for one ramp lane versus one target mainline lane. It is NOT measured VISSIM priority, nor a fitted parameter or whole-paper replication. Existing gap bound remains.',
        budget=dict(autonomous450_max=13,fit_vectors=0,native=0,FZP=0),
        validation='Same12 historical records29/43/61/67; previously inspected, not blind.1 disabled p=1 parity then12 p=.5 autonomous predictions; stored178 baseline reused.',
        limitations=['Restricted to10490/cell21; does not identify microscale gaps or occupancy time.',
                      'Does not replace upstream head/arrival or METANET velocity dynamics.',
                      'Component31mainline+4ramps+4off cost, not wholeOmega. No all8ramp/controller claim.'],
        gates='Meaningful |actual deltaTTT|>=.5 signs, response error at least10%better, absolute error<=110%baseline, choice regret<=.5vehh. Current RM-hold merges and10681 undermerge are guards. No further p grid if rejected.',
        previous='188 conditional posthead check and154target-lane-gap/173ramp-first trials reviewed;109 changes arrival phase, not priority. Claude03 review checked; no coefficients transplanted.',
        no_future_observations=True)
    pins={str(source_path):h.sha(source_path),str(h.R/'queue_dynamics178/spec.json'):h.sha(h.R/'queue_dynamics178/spec.json'),
          str(h.R/'queue_dynamics178/forecast/rows.json'):h.sha(h.R/'queue_dynamics178/forecast/rows.json'),
          str(h.ROOT/'evaluation/controllers/physical_ramp_boundary.py'):h.sha(h.ROOT/'evaluation/controllers/physical_ramp_boundary.py')}
    for p,d in {**pins,**proto['protected_sha256'],proto['STOP']['path']:proto['STOP']['sha256']}.items():assert h.sha(p)==d,p
    h.save(HERE/'executed_function_sources.json',source)
    h.save(HERE/'coefficients.json',dict(priority=.5,fit=False))
    h.save(HERE/'spec.json',spec);h.save(HERE/'protocol.json',proto);h.save(HERE/'pins.json',pins)
    h.save(HERE/'source_checks.json',dict(unrelated_methods_exact=True,changed_functions=['RouteLaneRegion.__init__','RouteLaneRegion.ramp_supply','rollout keyword call'],production_changed=False))


if __name__=='__main__':main()
