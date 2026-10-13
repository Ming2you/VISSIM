"""Match cached5s SC10 crossings to later SC6 head entries; no new FZP scan."""
from pathlib import Path
from collections import Counter
import json,hashlib
HERE=Path(__file__).resolve().parent;A=HERE.parent
MODEL=Path('E:/VISSIM_analysis/20261010_sc12_initial306/forecast2400_v2')
PINS={}
def read(p):
    b=Path(p).read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest();return json.loads(b)
def main():
    assert not (HERE/'gate_timing.json').exists()
    cohorts=read(HERE/'cohorts.json');gates=read(A/'gatearrival291/assessment.json')
    initial={r['vehicle'] for r in cohorts['initial_routes']}
    results={}
    for arm in ('hold','city'):
        crossings=gates['arms'][arm]['sampled_pre_to_post_crossings']
        new=[r for r in crossings if r['veh'] not in initial and r['low_sec']>=2400]
        matched=[]
        for row in cohorts['head_events'][arm]:
            earlier=[g for g in new if g['veh']==row['vehicle'] and g['high_sec']<row['time']]
            if not earlier:continue
            g=max(earlier,key=lambda x:x['high_sec'])
            matched.append(dict(vehicle=row['vehicle'],gate_low=g['low_sec'],gate_high=g['high_sec'],
                head_sec=row['time'],delay_low=row['time']-g['high_sec'],delay_high=row['time']-g['low_sec'],
                after_gate_speed=g['after_speed']))
        receipts=read(MODEL/(arm+'.delay_receipts.json'))
        expected=sorted({r['post_gate_delay_sec'] for r in receipts})
        assert expected==[40],expected
        bound=min(expected)
        model=read(MODEL/(arm+'.gate.json'))
        byblock=[]
        for start in (2400,2550,2700):
            rows=[r for r in new if start<=r['high_sec']<start+150]
            history=[r for r in model['history'] if start<=r['step']*10<start+150]
            byblock.append(dict(start=start,native_sampled_new_gate_crossers=len(rows),
                model_new_gate_discharge=sum(r['discharged'] for r in history),
                model_capacity_binding_steps=sum(r['positive_green_capacity_binding'] for r in history)))
        results[arm]=dict(matched_count=len(matched),matched=matched,
            actual_head_passage_earlier_than_model_ready_count=sum(r['delay_high']<bound for r in matched),
            model_post_gate_travel_sec=bound,delay_quantiles_upper=[sorted(r['delay_high'] for r in matched)[int((len(matched)-1)*q)] for q in (0,.25,.5,.75,1)],
            byblock=byblock)
    (HERE/'gate_timing.json').write_text(json.dumps(dict(status='complete_new_gate_head_witnesses',arms=results,source_pins=PINS,
        new_forecasts=0,native=0,fzp_scans=0,fits=0,
        limits=['Sampled gate crossings are lower-bound witnesses, not a census.',
          'Gate-to-head elapsed time includes downstream red waiting; it cannot directly calibrate free travel speed.',
          'An observed head crossing before the model ready time is evidence against that predicted travel delay for the witnessed trajectory.',
          'Future events are diagnostic only. Neither model rate nor travel parameter changed.']),ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print({a:{k:v for k,v in r.items() if k!='matched'} for a,r in results.items()})
if __name__=='__main__':main()
