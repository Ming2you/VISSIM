"""Reproduce admission into a full pre-signal compartment, without changing it."""
from diagnostics.repin_v3c3_review_20261001.ramp10639_170 import check as c
from evaluation.controllers.physical_ramp_boundary import PhysicalRampBoundary


def main():
    assert not (c.HERE/'prehead_storage.json').exists()
    c.pin(c.Path(__file__))
    c.pin(c.ROOT/'evaluation/controllers/physical_ramp_boundary.py')
    # Ten vehicles occupy all60m before a red signal. The empty40m AFTER it
    # cannot be used to admit another vehicle before that signal.
    b = PhysicalRampBoundary(connector_id='diagnostic', length_m=100,
        head_position_m=60, lanes=1, spacing_m=6, travel_speed_kmh=36,
        time_sec=0, initial_cohorts=[(6*i,0,1) for i in range(10)])
    space = b.current_admission_space()
    b.begin_interval(0,1)
    b.commit_merge(0)
    b.apply_head_service(0,mode='RED',green_sec=0,posthead_capacity_veh=40/6)
    receipt = b.finish_interval(1)
    # This asserts reproduction of the defect, NOT physical acceptance.
    assert receipt['admitted_arrivals_veh']==1 and space>0
    assert receipt['end']['upstream_travelling_veh']+receipt['end']['head_ready_veh']==11
    witnesses=[]
    for arm in ('hold','release','hold_vsl90','release_vsl90'):
        p=c.read(c.R/f'recovery_lateral169/forecast/state/s67_late_{arm}.json.gz')
        for cid in c.RAMPS:
            meta=p['diagnostics']['dynamic_ramp_boundary']['metadata']['RM_C'+cid]
            # Physical lane is the unit of storage; ramp10681 has two lanes.
            pre_cap=meta['head_position_m']/meta['spacing_m']
            violations=[]
            for row in p['ramps']:
                if row['start']['connector_id']!=cid:continue
                for i,lane in enumerate(row['lane_receipts']):
                    pre=lane['end']['upstream_travelling_veh']+lane['end']['head_ready_veh']
                    if pre>pre_cap+1e-7:
                        violations.append(dict(time_s=row['end_sec'],lane=i+1,pre_veh=pre,
                            excess_veh=pre-pre_cap,admitted_veh=lane['admitted_arrivals_veh']))
            witnesses.append(dict(arm=arm,connector=cid,pre_capacity_per_lane_veh=pre_cap,
                violating_lane_steps=len(violations),max_excess_veh=max((x['excess_veh'] for x in violations),default=0),
                first=violations[0] if violations else None,last=violations[-1] if violations else None))
    for p,d in c.PINS.items():assert c.sha(p)==d,p
    c.save('prehead_storage.json',dict(status='defect_reproduced_not_fixed',
        fixture=dict(geometry_length_m=100,head_m=60,spacing_m=6,initial_pre_n=10,
            physical_pre_capacity_veh=10,expected_additional_admission=0,
            current_reported_admission_space=space,receipt=receipt),
        cached_witnesses=witnesses,input_sha256=c.PINS,
        qualification='Compartment geometry inconsistency, not a calibrated jam-spacing estimate. Correcting it can move waiting upstream; Omega and outside costs must remain conserved. No gain claim.',
        forecasts=0,native=0,FZP=0))
    for x in witnesses:
        if x['violating_lane_steps']:print(x)


if __name__=='__main__':main()
