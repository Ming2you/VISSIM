"""Observed merge-speed mismatch, separate from accepted-flow/momentum audits.

Read-only cached native labels. Neither a forecast nor a fitted speed law.
"""
import csv
import ctypes
import math
import time
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE = Path(__file__).resolve().parent/'verified'
START, END = 2670.1, 3120.1
CELLS = {'10490':21, '10484':23}
ARMS = ('hold', 'release', 'hold_vsl90', 'release_vsl90')


def load_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def main():
    HERE.mkdir(exist_ok=True)
    assert not (HERE/'protocol.json').exists(), 'Never overwrite a finished/failed analysis'
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    kernel.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    assert kernel.SetPriorityClass(kernel.GetCurrentProcess(), 0x4000)
    began = time.perf_counter()
    protected = {str(p):h.sha(p) for p in (h.ROOT/'evaluation/controllers').glob('*.py')}
    stop = h.read(h.R/'vsl_response243/protocol.json')['STOP']
    protocol = dict(
        previous_turn='PROGRESS251: published in/out lateral-friction fit rejected after25forecasts.',
        question='Does positive native mainline-minus-merging speed mismatch decrease when VSL helps? Distinguish from old virtual-upstream speed mixing and simply changing delta.',
        sources='Existing67fourarm5s mainline/ramp caches and verified native port event tables; no FZP/COM/native process access.',
        region='10490->cell21/lane1 and10484->cell23/lane1, all three150s blocks of2670.1--3120.1.',
        quantities='Per event: observed receiving-lane mean at interval start, last ramp speed at same start, first observed mainline speed at end. Compare v_main and max(v_main-v_ramp,0). Divide sums by current N_lane+kappa*L only as a dimensioned diagnostic, coefficient1.',
        limitation='Actual merge outcomes in following5s select events; last/first speeds are censored observations, not boundary-speed bounds. Mainline lane may be empty. This is descriptive future-conditioned information, NOT autonomous input, causal attribution, calibrated mechanism or proof that positive mismatch is the correct law.',
        predeclared_comparisons='Report all4arms/2ramps/3blocks. HoldVSLharm and releaseVSLbenefit together. No arbitrary pass percentage or posthoc coefficient fit; first establish whether this mechanism has the proposed direction.',
        prior_attempt='Initial audit wrongly equated old current_target_lane_mean with physical merge lane1. Old source explicitly uses first-postsample endpoint lane as a label; native physics unchanged. Failure source/log preserved. Reconstruct that label for parity and retain physical lane1 for new quantities.',
        preservation='Objective, commands, vehicle conservation and all model/source settings unchanged.',
        budget=dict(fits=0, forecasts=0, native=0, FZP=0), protected_sha256=protected, STOP=stop)
    h.save(HERE/'protocol.json', protocol)
    pins = {str(Path(__file__)):h.sha(__file__)}
    def read(path):
        pins[str(path)] = h.sha(path)
        return h.read(path)
    contract = read(h.F/'route_inventory/contract.json')
    network_path = h.ROOT/contract['network']['path']
    assert h.sha(network_path) == contract['network']['sha256']
    pins[str(network_path)] = contract['network']['sha256']
    network = ET.parse(network_path).getroot()
    for con, link in (('10490',119),('10484',24)):
        endpoint = network.find('.//link[@no="'+con+'"]/toLinkEndPt')
        assert tuple(map(int,endpoint.get('lane').split())) == (link,1)
    from diagnostics.repin_v3c3_review_20261001.jin_macro111 import run as common
    context, _, _ = common.setup()
    cfg = context['component']._config('FW_E', context['parameters']['by_direction']['FW_E'])
    spec = {con:cfg.network.freeway_segment_params['FW_E'][i] for con, i in CELLS.items()}
    old = read(h.F/'merge_speed_audit/events.json')
    previous = {(r['arm'],str(r['vehicle']),r['connector'],round(r['hi'],1)):r for r in old}
    rows = []; states = []; checks = defaultdict(int); maximum = 0.
    initial = None
    for arm in ARMS:
        main = read(h.R/f'blocking176/{arm}_frames.json.gz')
        ramp = read(h.R/f'ramp_motion187/s67_late_{arm}_ramps.json.gz')
        ix = {name:i for i,name in enumerate(main['fields'])}
        mainframes = {round(float(t),1):r for t,r in main['frames'].items()}
        rampframes = {round(float(t),1):r for t,r in ramp['frames'].items()}
        assert sorted(mainframes) == sorted(rampframes)
        first = {k:[v[ix[f]] for f in ('cell','speed','x','lane')] for k,v in mainframes[START].items()}
        if initial is None:initial = first
        else:assert first == initial
        truth = h.I/f'heldout67_freeway_20260930/observations/{arm}'
        event_path = truth/'port_events.csv'; flow_path = truth/'flows_30s.csv'
        for p in (event_path,flow_path):pins[str(p)] = h.sha(p)
        events = [r for r in load_csv(event_path) if r['kind']=='departure' and r['connector'] in CELLS and START<float(r['time_s'])<=END]
        assert len({(r['vehicle'],r['connector'],r['time_s']) for r in events}) == len(events)
        by_time = defaultdict(list)
        for r in events:by_time[round(float(r['lower_time_s']),1),r['connector']].append(r)
        for step in range(90):
            lo = round(START+step*5,1); hi = round(lo+5,1)
            for con, cell in CELLS.items():
                lane = [v for v in mainframes[lo].values() if v[ix['cell']]==cell and v[ix['lane']]==1]
                n = len(lane); speed = math.fsum(v[ix['speed']] for v in lane)/n if n else None
                acc = math.fsum(v[ix['accel']]*3.6 for v in lane)/n if n else None
                slow = sum(v[ix['speed']]<5 for v in lane)
                length = spec[con]['segment_length_km']; kappa = spec[con]['metanet_kappa_veh_km_lane']
                denominator = n+kappa*length
                states.append(dict(arm=arm,connector=con,cell=cell,lo=lo,hi=hi,block=step//30,n=n,speed=speed,
                                   current_acceleration_kmh_per_s=acc,slow=slow,merges=len(by_time[lo,con])))
                for event in by_time[lo,con]:
                    assert round(float(event['upper_time_s']),1)==hi
                    vid = event['vehicle']; raw = rampframes[lo][vid]
                    assert raw[0]==con and vid not in rampframes[hi]
                    assert abs(raw[2]-float(event['speed_kmh']))<1e-9
                    first_main = mainframes[hi].get(vid)
                    after = first_main[ix['speed']] if first_main is not None else None
                    before = raw[2]
                    # Use the same pre-event mainline lane for both speed proxies.
                    gap = None if speed is None else max(0.,speed-before)
                    gap_after = None if speed is None or after is None else max(0.,speed-after)
                    row = dict(arm=arm,connector=con,cell=cell,vehicle=vid,lo=lo,hi=hi,block=step//30,
                               n_lane=n,v_lane=speed,v_ramp_before=before,v_main_after=after,
                               positive_gap_before=gap,positive_gap_after=gap_after,
                               denominator=denominator,
                               unit_original=None if speed is None else speed/denominator,
                               unit_gap_before=None if gap is None else gap/denominator,
                               unit_gap_after=None if gap_after is None else gap_after/denominator)
                    rows.append(row); checks['events']+=1
                    past = previous[(arm,vid,con,hi)]
                    assert past['last_ramp_speed_kmh']==before
                    checks['old_ramp_speed_matches']+=1
                    if past['current_target_lane_mean'] is not None:
                        endpoint_lane = first_main[ix['lane']]
                        endpoint_speeds = [v[ix['speed']] for v in mainframes[lo].values()
                                           if v[ix['cell']]==cell and v[ix['lane']]==endpoint_lane]
                        expected_old = math.fsum(endpoint_speeds)/len(endpoint_speeds)
                        error = abs(past['current_target_lane_mean']-expected_old)
                        maximum = max(maximum,error); assert error<1e-9
                        assert past['first_mainline_speed_kmh']==after
                        checks['old_target_lane_matches']+=1
                        checks['endpoint_lane_not_physical_merge_lane']+=endpoint_lane!=1
        for con,cell in CELLS.items():
            flows = [r for r in load_csv(flow_path) if r['road']=='FW_E' and int(r['cell'])==cell and START<float(r['window_end_s'])<=END]
            assert len(flows)==15
            for r in flows:
                lower,upper = float(r['window_start_s']),float(r['window_end_s'])
                count = sum(lower<float(e['time_s'])<=upper and e['connector']==con for e in events)
                assert count==float(r['ramp_merges']), (arm,con,lower,count,r['ramp_merges'])
                checks['native_flow_windows']+=1
    summaries=[]
    for arm in ARMS:
        for con in CELLS:
            for block in (None,0,1,2):
                group=[r for r in rows if r['arm']==arm and r['connector']==con and (block is None or r['block']==block)]
                native=[r for r in states if r['arm']==arm and r['connector']==con and (block is None or r['block']==block)]
                valid=[r for r in group if r['v_lane'] is not None]
                both=[r for r in valid if r['positive_gap_after'] is not None]
                summaries.append(dict(arm=arm,connector=con,block=block,events=len(group),
                    current_lane_known=len(valid),both_speeds_known=len(both),
                    mainline_slower_than_ramp=sum(r['v_lane']<=r['v_ramp_before'] for r in valid),
                    mean_lane_n=sum(r['n'] for r in native)/len(native),mean_slow=sum(r['slow'] for r in native)/len(native),
                    mean_merge_speed_before=sum(r['v_ramp_before'] for r in group)/len(group) if group else None,
                    unit_original=sum(r['unit_original'] for r in valid),unit_gap_before=sum(r['unit_gap_before'] for r in valid),
                    matched_unit_original=sum(r['unit_original'] for r in both),unit_gap_after=sum(r['unit_gap_after'] for r in both)))
    contrasts=[]
    for con in CELLS:
        for block in (None,0,1,2):
            by={r['arm']:r for r in summaries if r['connector']==con and r['block']==block}
            for left,right in (('hold','release'),('hold','hold_vsl90'),('release','release_vsl90')):
                keys=('events','mean_lane_n','mean_slow','unit_original','unit_gap_before','unit_gap_after')
                contrasts.append(dict(connector=con,block=block,change=right+'-'+left,
                                      delta={k:by[right][k]-by[left][k] for k in keys},
                                      missing_before={left:by[left]['events']-by[left]['current_lane_known'],right:by[right]['events']-by[right]['current_lane_known']}))
    h.save(HERE/'events.json',rows);h.save(HERE/'states.json',states)
    h.save(HERE/'summary.json',summaries);h.save(HERE/'contrasts.json',contrasts);h.save(HERE/'pins.json',pins)
    assert checks['native_flow_windows']==120 and len(states)==720 and len(rows)==sum(r['merges'] for r in states)
    assert all(h.sha(p)==digest for p,digest in {**pins,**protected,stop['path']:stop['sha256']}.items())
    result=dict(status='complete',checks=dict(checks),old_lane_mean_max_error=maximum,seconds=time.perf_counter()-began,
                sources_and_STOP_preserved=True,fits=0,forecasts=0,native=0,FZP=0,adopted=False,goal='ACTIVE_NOT_QUALIFIED')
    h.save(HERE/'completion.json',result);print(result,flush=True)


if __name__=='__main__':main()
