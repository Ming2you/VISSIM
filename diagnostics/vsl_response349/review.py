"""Reuse completed three-arm records; no FZP, COM, fitting or live writes."""
from pathlib import Path
import hashlib
import json
import statistics
import argparse
import re

ARMS = ('window', 'optimized', 'off')
ROOT = Path('E:/VISSIM_runs')

def folder(arm):
    return ROOT / f'20261008_coupling268_{arm}_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29'

def read(path):
    with path.open(encoding='utf-8-sig') as handle:return json.load(handle)

def file_sha(path):
    with path.open('rb') as handle:return hashlib.file_digest(handle,'sha256').hexdigest()

def small_action(path):
    """Read verified root-level fields at file ends, skipping large optimizer traces."""
    size=path.stat().st_size
    with path.open('rb') as handle:
        head=handle.read(65536)
        handle.seek(max(0,size-262144));tail=handle.read()
    if size<=262144:
        return json.loads(tail),dict(file_bytes=size,sha256=hashlib.sha256(tail).hexdigest(),hash_scope='whole small file')
    cut=head.find(b'\n  "diagnostics":')
    start=tail.rfind(b'\n  "prediction":')
    assert cut>0 and start>=0,('Unsupported action serialization',str(path))
    result=json.loads(head[:cut].rstrip().rstrip(b',')+b'\n}')
    last=json.loads(b'{'+tail[start:])
    assert 'prediction' in last and set(last)<={'prediction','prediction_error'}
    diag=head[cut:].split(b'"_control_area_written_meter_context"',1)[0]
    result['diagnostics']={k.decode():float(value) for k,value in
        re.findall(rb'"(rw_meter_green_[^"]+)"\s*:\s*([0-9.eE+-]+)',diag)}
    assert len(result['diagnostics'])==8
    result.update(last)
    receipt=dict(file_bytes=size,selected_head_sha256=hashlib.sha256(head).hexdigest(),
                 selected_tail_sha256=hashlib.sha256(tail).hexdigest(),hash_scope='selected ranges, not whole file')
    return result,receipt

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def controls(action):
    return dict(green=action['green_times'], offset=action['offsets'],
                meter={k:v for k,v in action['diagnostics'].items() if k.startswith('rw_meter_green_')})

def period(t):
    return 'before1800' if t < 1800 else 'active1800_5700' if t < 5700 else 'after5700'

def main():
    p=argparse.ArgumentParser();p.add_argument('--out', type=Path, required=True);args=p.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    actions={};rows=[];pins={};control_rows=[]
    for arm in ARMS:
        actions[arm]={}
        for t in range(900, 8100, 150):
            path=folder(arm)/f'action_{t:06}.json'
            full,pins[str(path)]=small_action(path)
            # Joint audit payloads may be large: retain only fields needed by this review.
            action={key:full[key] for key in ('green_times','offsets','vsl')}
            action['diagnostics']={k:v for k,v in full['diagnostics'].items() if k.startswith('rw_meter_green_')}
            action['prediction']={k:full.get('prediction',{}).get(k) for k in ('status','target_sim_sec','state_summary')}
            action['prediction_error']=full.get('prediction_error',{})
            del full
            applied=Path(str(path)+'.applied').exists()
            actions[arm][t]=action
            control_rows.append(dict(arm=arm, at=t, applied=applied,
                vsl={k:v for k,v in action['vsl'].items() if '__seg' in k and v<110},
                non_vsl_digest=digest(controls(action))))
            error=action.get('prediction_error', {})
            if error.get('status')!='ok':continue
            start=error['predicted_from_sim_sec']
            if start<900 or start not in actions[arm]:continue
            previous=actions[arm][start]
            prediction=previous['prediction']
            if prediction.get('status')!='ok' or prediction['target_sim_sec']!=t:continue
            observed=error['scalar_errors']
            for key in ('freeway_total_veh','freeway_mean_speed_kph','off_ramp_storage_veh','ramp_queue_total_veh'):
                if key not in observed:continue
                # Use raw summary, not calibrated display corrections, and align target exactly.
                predicted=prediction['state_summary'][key];target=observed[key]['observed']
                rows.append(dict(arm=arm, start=start, end=t, period=period(start), metric=key,
                    predicted=predicted, observed=target, error=predicted-target,
                    prediction_source='stored_raw_postdecision_150s_summary',
                    summary_kind_used_by_old_error=error.get('prediction_summary_kind')))
        (args.out/'progress.json').write_text(json.dumps(dict(last_completed_arm=arm,rows=len(rows)))+'\n')
    aggregate=[]
    for arm in ARMS:
        for part in ('before1800','active1800_5700','after5700'):
            for key in sorted({r['metric'] for r in rows}):
                rr=[r for r in rows if r['arm']==arm and r['period']==part and r['metric']==key]
                if rr:aggregate.append(dict(arm=arm,period=part,metric=key,n=len(rr),
                    bias=statistics.mean(r['error'] for r in rr),mae=statistics.mean(abs(r['error']) for r in rr)))
    pairs=[]
    for arm in ('window','optimized'):
        diffs=[]
        for t in range(900,8100,150):
            a,b=actions[arm][t],actions['off'][t]
            ca,cb=controls(a),controls(b)
            diffs.append(dict(at=t, different_fields=[k for k in ca if ca[k]!=cb[k]],
                              same_vsl=a['vsl']==b['vsl']))
        first_action=next((r['at'] for r in diffs if r['different_fields']),None)
        first_state=None;equal=[]
        for t in range(900,8101,150):
            a=read(folder(arm)/f'state_{t:06}.json')['vehicle_records']['records']
            b=read(folder('off')/f'state_{t:06}.json')['vehicle_records']['records']
            if a!=b:first_state=t;break
            equal.append(t)
        pairs.append(dict(arm=arm,reference='off',first_non_vsl_command_difference=first_action,
            first_vehicle_state_difference=first_state,equal_initial_snapshot_times=equal,command_differences=diffs))
    result=dict(status='completed_record_review',new_native_runs=0,new_predictions=0,new_fits=0,
        scope='Closed-loop arm comparison is descriptive. Stored one-step prediction is not an optimizer450s forecast or current native348 forecast.',
        error_sign='prediction minus observation',aggregate=aggregate,pairs=pairs,source_pins=pins)
    for name,obj in [('review.json',result),('errors150.json',rows),('commands.json',control_rows)]:
        (args.out/name).write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    print(json.dumps(dict(status=result['status'],pairs=[{k:v for k,v in r.items() if k!='command_differences'} for r in pairs],aggregate=aggregate),ensure_ascii=False))

if __name__=='__main__':main()
