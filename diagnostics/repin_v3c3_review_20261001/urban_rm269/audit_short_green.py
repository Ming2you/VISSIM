"""Bounded native head-service evidence from an already stopped run.

No FZP scan, model fit or forecast. A commanded green is verified against native
LDP before being used as a label. Endpoint stocks do not certify continuous
saturation, so observed throughput is not automatically an identified capacity.
"""
import csv
import gzip
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT))
from evaluation.controllers import obs150_contract as oc

F=Path('D:/VISSIM_runs/20261007_goal8_prevention_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29')
LDP=F.parent/'vissim_eval/sdmpc31_sdmpc8100_s29_9106_001.ldp'
OUT=HERE/'short_green'
TIMES=(1050,1200,1350,1650,1800,2100,2250,2400,2550,2850,3450,3900,4500,5100,5400,5550)
PINS={}
def contents(p):
    b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest();return b

def main():
    assert not OUT.exists(), 'Keep completed evidence; do not repeat'
    assert (F.parent.parent/'STOP').exists(), 'Use the stopped historical run only'
    contents(F.parent.parent/'STOP')
    tr=json.loads(gzip.decompress(contents(HERE/'component10681_v2/selected_trace.json.gz')))
    head=tr['initial_buffer']['head_position_m'];length=tr['initial_buffer']['length_m']
    geometry=tr['initial_buffer'];service=tr['head_service_by_green']
    codes={}
    for line in contents(LDP).decode('cp1252').splitlines():
        # The user stopped this run; its final record is a partial ' 6'. Never
        # reinterpret that tail as an earlier timestamp. Requested windows all
        # end<=5700 and must have every complete native display sample below.
        if len(line)<13: continue
        try:t=float(line[:7])
        except ValueError:continue
        assert t not in codes
        codes[t]=line[12:] # One SG, fixed-width native display column.
    rows=[]
    for start in TIMES:
        end=start+150
        command=contents(F/f'action_{start:06}.csv').decode('utf-8-sig')
        meter=[r for r in csv.DictReader(command.splitlines()) if r['kind']=='ramp_meter' and r['id']=='RM_C10681']
        assert len(meter)==1 and meter[0]['sc_no']=='9106'
        green=int(float(meter[0]['green_sec']));assert green in (2,3,4,6)
        receipt=contents(F/f'action_{start:06}.json.applied').decode('utf16').splitlines()
        assert float(receipt[0])==start and Path(receipt[1])==F/f'action_{start:06}.csv'
        assert int(receipt[2])==len((F/f'action_{start:06}.csv').read_bytes())
        expected={t:('I' if (t-1)%10<green else '.') for t in range(start+1,end+1)}
        assert all(codes[t]==v for t,v in expected.items()), (start,'Native LDP does not implement command')
        raw=json.loads(contents(F/f'state_{end:06}.json'))
        bundle=oc.load_bundle(raw)
        detectors,_=oc.read_detector_csv(bundle.obs['detector_config']['path'],bundle.obs['detector_config']['sha256'])
        window=oc.assign_window(bundle.obs,bundle.mer_rows)
        def stocks(frame):
            return {stage:[sum(v[1]==10681 and v[2]==lane and ((v[3]<head)==(stage=='pre'))
                                for v in frame['vehicles']) for lane in (1,2)] for stage in ('pre','post')}
        events=[];tails=[]
        for det in detectors:
            if det.link!=10681 or det.role!='meter_head':continue
            tails.append(window.tails[det.dcp_no])
            events.extend(dict(veh=r.veh,time=r.t_entry,lane=det.lane) for r in window.entries[det.dcp_no])
        assert len(tails)==2 and all(x==0 for x in tails)
        events.sort(key=lambda e:(e['time'],e['lane']))
        perlane=[]
        for lane in (1,2):
            selected=[e for e in events if e['lane']==lane]
            cycles=[sum(t<=e['time']<t+10 for e in selected) for t in range(start,end,10)]
            headways=[b['time']-a['time'] for a,b in zip(selected,selected[1:])
                if math.floor(a['time']/10)==math.floor(b['time']/10)]
            perlane.append(dict(head=len(selected),cycle_counts=cycles,within_cycle_headways_sec=headways,
                first_event_sec=selected[0]['time'] if selected else None))
        before,after=stocks(bundle.frame_start),stocks(bundle.frame_end)
        rows.append(dict(start_sec=start,end_sec=end,green_sec=green,ldp_samples_verified=150,
            initial=before,final=after,observed=perlane,head_events=events,
            table_cycle_veh_per_lane=service[str(green)]*10/3600/2,
            nominal_posthead_capacity_per_lane=(length-head)/geometry['spacing_m'],
            all_endpoint_prehead_stocks_over10=all(n>=10 for n in before['pre']+after['pre']),
            all_endpoint_posthead_stocks_below_half_storage=all(n<(length-head)/geometry['spacing_m']/2 for n in before['post']+after['post'])))
    OUT.mkdir()
    result=dict(status='native_short_green_evidence_not_capacity_fit',source_pins=PINS,
        input_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        state_windows=16,native_ldp_samples_verified=2400,rows=rows,
        forecast_runs=0,coefficient_fits=0,new_native_runs=0,FZP_scans=0,
        limits=['Same seed29, a different closed-loop policy; not independent-seed causal comparison.',
            'Stopped native LDP has a partial final record after6694s; no tail sample is inferred. All selected windows end<=5700.',
            'Endpoint prehead stock and posthead space do not prove saturation/nonblocking throughout a cycle.',
            'Head is detector passage, not actual freeway merge; output cap must not be calibrated to demand-limited windows.',
            'No performance or TTT inference from this component survey.'])
    (OUT/'evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for r in rows:
        print(r['start_sec'],r['green_sec'],'head',[x['head'] for x in r['observed']],
              'pre',r['initial']['pre'],r['final']['pre'],'post',r['initial']['post'],r['final']['post'])

if __name__=='__main__':main()
