"""Preserve native cohort evidence and characterize the fractional FIFO limit.

Synthetic states diagnose a numerical representation, not a permitted bypass
or a physical capacity improvement. Production code is unchanged.
"""
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path

from evaluation.controllers.physical_urban_transport import UrbanTransport, FIFO, geometry

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
R = HERE.parent


def read(p):
    b = p.read_bytes()
    return json.loads(gzip.decompress(b) if p.suffix == '.gz' else b)


class Program:
    def state_at(self, t, sg, *, controller_offset_sec):
        return 'GREEN' if sg == 2 else 'RED'


def main():
    output = HERE/'prefix_evidence.json'
    assert not output.exists()
    manifest = read(R/'retained10638/candidate_manifest.json')
    protocol = read(ROOT/manifest['sources']['reference_protocol']['path'])
    network = ROOT/manifest['sources']['network']['path']
    assert hashlib.sha256(network.read_bytes()).hexdigest() == manifest['sources']['network']['sha256']
    cases = []
    for mass in (1., .1, .01, .0003622921237829728, 1e-6, 0.):
        m = UrbanTransport(dict(time_s=3100.1, vehicles=[]), network, Program(), 0,
            protocol['urban_free_speed_m_s'], 6., protocol['wave_m_s'],
            lateral_access=True, continuation=True)
        m.prefer_more_receiving_space = protocol['prefer_more_receiving_space']
        last = len(m.edges[71])-2
        m.cells[(71,3,last)] = FIFO([((10635,'blocked'),mass), ((10634,'through'),2.-mass)])
        m.cells[(71,4,last)] = FIFO([((10635,'red_queue'), m.cap[(71,4,last)])])
        m.initial=m.counts();m.check()
        m.step({})
        cases.append(dict(blocked_mass=mass,through_mass=2.-mass,
            green_lane_departed=sum(n for (d,v),n in m.departed.items() if d==10634),
            blocked_mass_retained=m.counts()[(10635,'blocked')],
            total_mass_residual=sum(m.initial.values())-sum(m.counts().values())-sum(m.departed.values())))
    assert all(abs(c['total_mass_residual'])<1e-8 for c in cases)
    assert all(c['green_lane_departed']==0 for c in cases[:-1])
    assert cases[-1]['green_lane_departed']>0
    audit=read(HERE/'assessment_prefix.json')
    prior=read(R/'urban10643_conditional/assessment.json')
    cachepath=R/'lane10643_native/rows.json.gz'
    cache=read(cachepath)
    cohorts=[]
    for vehicle in (12046,21111,23204):
        label=str(vehicle)+':visit1'
        blocked=[x for x in audit['rows'] if x['green'] and x['reason_after_lateral']=='lane_access'
                 and x['prefix_after_lateral'][1]==label]
        native=[x for x in cache['rows'] if x[1]==vehicle]
        changes=[]; previous=None
        for x in native:
            if previous is None or x[2:4]!=previous[2:4]:changes.append(x)
            previous=x
        if native and native[-1] not in changes:changes.append(native[-1])
        overlap=[x for x in native if blocked[0]['time_s']<=x[0]<=blocked[-1]['time_s']]
        cohorts.append(dict(vehicle=vehicle,
            arrival=next(x for x in prior['events'] if x['vehicle']==vehicle),
            blocked_times=[x['time_s'] for x in blocked],
            prefix_mass_min=min(x['prefix_amount_after_lateral'] for x in blocked),
            prefix_mass_max=max(x['prefix_amount_after_lateral'] for x in blocked),
            model_first=blocked[0],model_last=blocked[-1],native_state_changes=changes,
            native_rows_during_model_block=overlap,
            native_head=[x for x in prior['native']['head_events'] if x['vehicle']==vehicle]))
    result=dict(status='completed_fractional_prefix_representation_diagnosis',
        synthetic_one_step_cases=cases,native_cohorts=cohorts,
        source_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in
            (cachepath,HERE/'assessment_prefix.json',R/'urban10643_conditional/assessment.json',network)},
        production_changed=False,new_native=0,new_fzp=0,fit_calls=0,
        conclusions=['The current complete FIFO head gate is discontinuous at zero blocked fractional mass.',
            'Vehicle12046 has0.000362292veh at lane3 stopline while0.999637708veh remains in lane4 upstream; native vehicle is wholly in lane4 during the17 blocked green seconds.',
            'This identifies a model representation sensitivity, not a validated fix or proof that all local discharge error has this cause.'],
        next='Separate fractional cohort transport from individual-vehicle blocking; do not delete fragments, increase numerical EPS, or add capacity/TTT rewards. A conservative alternative requires multi-condition discharge and queue validation before calibration.')
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(synthetic=cases,cohorts=[dict(vehicle=x['vehicle'],blocked_seconds=len(x['blocked_times']),
        min_prefix=x['prefix_mass_min'],native_during_block=len(x['native_rows_during_model_block'])) for x in cohorts]),ensure_ascii=False))


if __name__=='__main__':main()
