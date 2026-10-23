"""Reconstruct the rejected coupled step from saved trajectories only."""
import collections,gzip,hashlib,json,math
from pathlib import Path
import numpy as np
V=Path(__file__).resolve().parent
O=V/'cellwise_coupled_20261020'
pins={}
def read(p):
    raw=p.read_bytes();pins[str(p)]=hashlib.sha256(raw).hexdigest()
    return json.loads(gzip.decompress(raw) if p.suffix=='.gz' else raw)

def main():
    assert not (O/'step_audit.json').exists()
    protocol=read(O/'protocol.json');selection=read(O/'selection.json');truth=read(O/'training_truth.json')
    evaluations=read(O/'evaluations.json');lookup={r['label']:r for r in evaluations}
    assert not selection['eligible_for_development'] and selection['updates']==1
    def residual(label):
        parts=[]
        for at in protocol['train_starts']:
            result=read(O/f'{label}_{at}.json');q=truth[str(at)]
            dn=np.array([r['n'] for r in result['frames']])-np.array([r['n'] for r in q])
            dv=np.array([r['speed'] for r in result['frames']])-np.array([r['speed'] for r in q])
            parts.extend((dn[:,14:21].ravel()/10,dv[:,14:21].ravel()/20))
        return np.concatenate(parts)/math.sqrt(63)
    base=residual('baseline');actual=residual('fitted1')
    assert abs(float(base@base)-lookup['baseline']['data_loss'])<1e-12
    columns=[]
    for j,(cell,name) in enumerate(protocol['parameters']):
        label=f'probe1_c{cell}_{name}';r=residual(label);step=lookup[label]['relative'][j]
        assert abs(step-.05)<1e-12
        columns.append((r-base)/step)
    J=np.column_stack(columns);step=np.array(lookup['fitted1']['relative']);linear=base+J@step
    predicted_reduction=float(base@base-linear@linear)
    observed_reduction=float(base@base-actual@actual)
    sv=np.linalg.svd(J,compute_uv=False)
    groups=[]
    for j,at in enumerate(protocol['train_starts']):
        sl=slice(j*42,(j+1)*42)
        groups.append(dict(start=at,baseline_loss=float(base[sl]@base[sl]),linear_prediction_loss=float(linear[sl]@linear[sl]),measured_loss=float(actual[sl]@actual[sl])))
    clocks=[]
    for at in protocol['train_starts']:
        pair={}
        for label in ('baseline','fitted1'):
            result=read(O/f'{label}_{at}.json');r=read(Path(result['response_cache']))
            steps=[x for x in r['resource_allocations'] if x['kind']=='freeway_mainline_sending' and x['resource']=='FW_E:cell:18']
            durations=collections.Counter(round(x['end_sec']-x['start_sec'],8) for x in steps)
            pair[label]=dict(event_rows=len(steps),duration_counts=dict(durations))
        clocks.append(dict(start=at,rows=pair))
    report=dict(status='rejected_step_linearization_audited',new_forecasts=0,new_native=0,new_fits=0,
        baseline_data_loss=float(base@base),linear_predicted_loss=float(linear@linear),measured_candidate_loss=float(actual@actual),
        predicted_reduction=predicted_reduction,observed_reduction=observed_reduction,
        reduction_agreement_ratio=observed_reduction/predicted_reduction,
        linearization_error_norm=float(np.linalg.norm(actual-linear)),actual_residual_change_norm=float(np.linalg.norm(actual-base)),
        singular_values=sv.tolist(),data_condition=float(sv[0]/sv[-1]),
        cells=[dict(cell=cell,step=step[j*5:j*5+5].tolist(),names=protocol['parameters'][j*5:j*5+5]) for j,cell in enumerate((16,17,18))],
        window_losses=groups,clock_event_summaries=clocks,
        interpretation='The tested coefficient vector failed measured nonlinear improvement. This does not establish impossibility of per-cell calibration; local linearization trust must be reduced before inferring model failure. Event clocks are a diagnostic, not proof of causal error.',
        next='Reuse the15 saved finite-difference columns. Prepare a smaller measured trust-region step, with no new Jacobian probes or parameter-grid search; preserve previous rejection. Validate the same fixed3OFF trajectories before VSL or independent-case expansion.',
        source_pins=pins,goal_complete=False,candidate_adopted=False)
    (O/'step_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('source_pins','cells','singular_values')},indent=2))
if __name__=='__main__':main()
