"""Fit follower speed-loss sensitivity using NC23 only, never paired TTT."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2 import evaluate_response as e
import numpy as np
import csv

HERE=Path(__file__).resolve().parent


def rows(seed,arm):
    result=[]
    with (HERE/f'lateral_v1/s{seed}_{arm}_events.csv').open(encoding='utf-8',newline='') as stream:
        for r in csv.DictReader(stream):
            if not r['matched_dv_kmh']:continue
            x=max(0.,float(r['follower_old_speed'])-float(r['changer_old_speed']))
            y=float(r['matched_dv_kmh'])-float(r['dv_kmh'])
            result.append((int(r['time_s']),x,y))
    return result


def fit(data):
    x=np.array([r[1] for r in data]);y=np.array([r[2] for r in data])
    assert len(x)>50 and x@x>0
    return max(0.,float(x@y/(x@x)))


def score(data,gamma):
    x=np.array([r[1] for r in data]);y=np.array([r[2] for r in data])
    return {'samples':len(data),'rmse_zero':float(np.sqrt(np.mean(y*y))),
        'rmse_model':float(np.sqrt(np.mean((y-gamma*x)**2))),
        'mean_observed_excess_loss_kmh':float(np.mean(y)),
        'mean_predicted_excess_loss_kmh':float(np.mean(gamma*x))}


def main():
    out=HERE/'interruption_fit_v1';out.mkdir(exist_ok=False)
    nc=rows(23,'none');training=[r for r in nc if r[0]<=2400]
    gamma=fit(training)
    blocks=sorted({(r[0]-900)//150 for r in training})
    loo=[fit([r for r in training if (r[0]-900)//150!=block]) for block in blocks]
    validation={'nc23_late':score([r for r in nc if r[0]>2400],gamma),
        'vsl23_after_control':score([r for r in rows(23,'vsl') if r[0]>2400],gamma),
        'nc33_all':score(rows(33,'none'),gamma),
        'spread33_after_control':score([r for r in rows(33,'spread_only') if r[0]>2400],gamma)}
    result={'schema':'lane-entry-follower-speed-loss/v1','gamma':gamma,
        'formula':'loss_kmh = gamma * max(follower_speed_before - entering_vehicle_speed_before, 0)',
        'training_scope':'Matched NCseed23 events900..2400 only; no cost or treatment-label fitting',
        'training':score(training,gamma),'leave_one_150s_block_out_range':[min(loo),max(loo)],
        'validation':validation,'status':'LOCAL_OBSERVATIONAL_FIT_NOT_ROLLOUT_QUALIFICATION',
        'limits':'Only a small matched subset of events; destination/gap choice and anticipatory braking confound identification. No constant capacity drop is inferred.',
        'mechanism_reference':'https://its.berkeley.edu/node/4685',
        'reference_scope':'Laval and Daganzo2006 motivates lane-change disturbances; this linear loss is a local diagnostic approximation, not their equation, and their original scope is away from diverges.'}
    e.save(out/'fit.json',result);print(result,flush=True)


if __name__=='__main__':main()
