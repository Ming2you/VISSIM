"""Assess a completed bounded forecast against saved geotime and native evidence."""
import gzip
import json
import sys
from pathlib import Path

O=Path(__file__).resolve().parent;L=O.parent;I=L.parent.parent
stage=sys.argv[1];t=3600 if stage=='3600' else 2250
label='clockdefault' if stage=='default' else 'clockcandidate'

def read(p):
    b=p.read_bytes();return json.loads(gzip.decompress(b) if p.suffix=='.gz' else b)

def held(tag):
    return read(I/f'closedloop_recorded{t}_lever450_RM_C10484_city{t}_ps_all8_{tag}/held_actual.json')

base=read(L/f'city_path/{t}_ps_all8_geotimecandidate/trace.json.gz')
new=read(L/f'city_path/{t}_ps_all8_{label}/trace.json.gz')
h0,h1=held('geotimecandidate'),held(label)
assert h0['commands']==h1['commands']
assert h0['executed_control_blocks']==h1['executed_control_blocks']
assert read(L/f'city_path/{t}_ps_all8_geotimecandidate/ramp_initial.json')==read(L/f'city_path/{t}_ps_all8_{label}/ramp_initial.json')
residual=max(abs(b['conservation_residual_veh']) for s in new['ramp_snapshots'] for b in s['buffers'].values())
assert residual<1e-7
result=dict(stage=stage,wall_sec=h1['wall_sec'],actual_commands_unchanged=True,initial_ramps_exact=True,
    max_all8_mass_residual=residual,ttt_omega=h1['ttt_omega_veh_h'],ttt_omega_baseline=h0['ttt_omega_veh_h'],
    validation=h1['validation'],optimizer_iterations=0)
if stage=='default':
    assert base==new
    assert h0['physical_cell_states']==h1['physical_cell_states']
    assert h0['ttt_omega_veh_h']==h1['ttt_omega_veh_h']
    result['full_trace_default_parity']=True
else:
    native=read(L/'posthead10490_receiving/verification.json')['windows'][str(t)]
    rows={}
    for name,trace in (('baseline',base),('candidate',new)):
        b=trace['ramp_snapshots'][0]['buffers']['RM_C10490']
        rows[name]=dict(arrival=b['cumulative_admitted_veh'],head=b['cumulative_head_service_veh'],
            merge=b['cumulative_merge_veh'],post=b['downstream_travelling_veh']+b['merge_ready_veh'],
            pre=b['upstream_travelling_veh']+b['head_ready_veh'],ttt=b['connector_ttt_veh_h'])
    actual=dict(merge=native['native_merge_from_conservation'],post=native['native_end_post'])
    errors={name:{k:abs(r[k]-actual[k]) for k in actual} for name,r in rows.items()}
    if t==2250:
        passed=all(errors['candidate'][k]<=.8*errors['baseline'][k] for k in actual)
    else:
        passed=all(errors['candidate'][k]<=errors['baseline'][k]+1. for k in actual)
    result.update(rows=rows,native=actual,absolute_errors=errors,physical_screen_passed=passed,
        autonomous=True,future_observations_for_scoring_only=True)
(O/f'assessment_{stage}.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='validation'},ensure_ascii=False))
