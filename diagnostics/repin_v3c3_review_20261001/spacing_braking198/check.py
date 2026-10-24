"""Test the density-to-interaction closure behind196's recovery overbraking.

Current front spacing and closing speed are paired before aggregation. This
conditional point-spacing probe is not the original GKT or an autonomous model.
No native data read, rollout, production edit, command reward, or future input.
"""
from collections import defaultdict
from pathlib import Path
import gzip
import hashlib
import json
import math
import time
import numpy as np

from diagnostics.repin_v3c3_review_20261001.braking_balance196.check import fit, V0, T

HERE = Path(__file__).resolve().parent
R = HERE.parent


def read(path):
    data = path.read_bytes()
    return json.loads(gzip.decompress(data) if path.suffix == '.gz' else data)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    data = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False).encode('utf-8')
    path.write_bytes(gzip.compress(data, mtime=0) if path.suffix == '.gz' else data)


def score(groups):
    rows = []
    for case in sorted({g['case'] for g in groups}):
        for subset in ('all', 'high_density', 'other'):
            gg = [g for g in groups if g['case'] == case and
                  (subset == 'all' or (g['rho_a'] >= .1) == (subset == 'high_density'))]
            if not gg:
                continue
            row = dict(case=case, subset=subset, groups=len(gg), pairs=sum(g['n'] for g in gg),
                       actual_mean_acceleration=float(np.mean([g['acceleration_5s'] for g in gg])))
            for name in ('persistence', 'paired', 'independent', 'joint_gap', 'factor_gap'):
                predicted = np.array([g.get(name+'_prediction', 0.) for g in gg])
                truth = np.array([g['acceleration_5s'] for g in gg])
                row[name] = dict(rmse=float(np.sqrt(np.mean((predicted-truth)**2))),
                                 bias=float(np.mean(predicted-truth)),
                                 mean=float(np.mean(predicted)),
                                 nonphysical_5s=sum(not 0 <= g['v']+5*p <= 160/3.6
                                                   for g, p in zip(gg, predicted)))
            rows.append(row)
    return rows


def main():
    assert not (HERE/'protocol.json').exists(), 'Preserve completed and failed experiments'
    started = time.perf_counter()
    old = read(R/'braking_balance196/protocol.json')
    paths = [R/'neighbor_information194/rows.json.gz', R/'braking_balance196/groups.json.gz',
             R/'braking_balance196/frozen_models.json', R/'braking_balance196/check.py',
             Path(__file__)]
    inputs = {str(p): sha(p) for p in paths}
    protected = {p: sha(p) for p in old['protected_sha256']}
    deliberate_prior_changes = {p: dict(before=d, now=protected[p])
                               for p, d in old['protected_sha256'].items() if d != protected[p]}
    stop = old['STOP']
    assert sha(stop['path']) == stop['sha256']
    protocol = dict(previous_turn='PROGRESS197: fixed VSL runtime/hold path and native launch; separate dynamics remained unqualified.',
        hypothesis='196 multiplies averaged closing-speed square by a cell-density susceptibility. Current recovery platoons may instead require the joint front-spacing/closing-speed moment.',
        equation='a = alpha*(V0-mean(v)) - gamma*V0*T^2*mean((v-v_front)_+^2 / s_front^2)',
        comparator='Same equation with mean((v-v_front)_+^2)*mean(1/s_front^2); equal two-coefficient fit budget.',
        interpretation='Our conditional dilute point-spacing probe of the GKT density closure, NOT the original GKT. s is front-to-front, not bumper gap. No guessed length, jam-spacing subtraction, gap floor, or fitted spatial scale.',
        relation='For uniform point spacing s=1/rho, both features reduce to the rho^2*B dilute factor. The close-packing susceptibility in196 is deliberately absent. Existing196 predictions are reused unchanged.',
        population='Exactly the saved196 cohorts, group weights and four nominal110 arms; t/t+5 same-vehicle labels from194. Endpoint survival and 5s integration limitations remain.',
        train='29_none only, freeze both fits before43_none and67hold/release scoring.',
        bounds=old['bounds'], constants=old['constants'],
        gate='Each heldout seed pooled joint-gap RMSE improves10pct against196 paired-density AND zero acceleration; no arm deteriorates against either. Paired-spacing must not worsen versus factor-gap. No post-result bound/feature search.',
        missing='No uniform per-vehicle desired-speed/VSL exposure across these caches: nominal necessary-condition test only. No autonomous moment closure, RM/VSL causal benefit, conservation/flow, or SDMPC qualification claimed.',
        prior_reviewed=['upstream_worklog/03_codex_review/REVIEW_CHECK.md',
            'cohort_dynamics_20260920/ORDERED_RELATIVE_RESPONSE_GATE.md: old geometry uncalibrated IDM, not this closure',
            'cohort_dynamics_20260920/INTERACTION_MEMORY_AND_TARGET_RESPONSE.md',
            'queue_dynamics178/README.md','neighbor_information194/README.md','braking_balance196/README.md'],
        budget=dict(fits=2,autonomous=0,native=0,FZP=0),input_sha256=inputs,
        protected_sha256=protected,prior197_protected_changes=deliberate_prior_changes,STOP=stop)
    save(HERE/'protocol.json', protocol)
    material = read(paths[0]); groups = read(paths[1]); lookup = defaultdict(list)
    for row in material:
        lookup[row['case'],row['t'],row['cell'],row['lane']].append(row)
    checks = 0
    max_target_error = 0.
    for g in groups:
        rr = lookup[g['case'],g['t'],g['cell'],g['lane']]
        assert len(rr) == g['n']
        spacing = np.array([r['gap_m'] for r in rr])
        assert np.all(np.isfinite(spacing)) and np.all(spacing > 0.)
        closing = np.array([max(0., -r['x'][13]/3.6) for r in rr])
        joint = float(np.mean((closing/spacing)**2))
        factor = float(np.mean(closing**2)*np.mean(1/spacing**2))
        independent_joint = sum(max(0., -r['x'][13]/3.6)**2 / r['gap_m']**2 for r in rr)/len(rr)
        assert abs(joint-independent_joint) < 1e-12
        target = sum(r['y']/18 for r in rr)/len(rr)
        max_target_error = max(max_target_error, abs(target-g['acceleration_5s']))
        assert max_target_error < 1e-12
        g.update(joint_gap_braking_feature=-V0*T*T*joint,
                 factor_gap_braking_feature=-V0*T*T*factor,
                 minimum_front_spacing_m=float(np.min(spacing)), joint_moment=joint,
                 factorized_moment=factor)
        checks += len(rr)
    train = [g for g in groups if g['case'] == '29_none']
    models = {name:fit(train,name) for name in ('joint_gap','factor_gap')}
    save(HERE/'frozen_models.json', models)
    frozen = sha(HERE/'frozen_models.json')
    for g in groups:
        for name, m in models.items():
            g[name+'_prediction'] = m['alpha']*g['relaxation_feature'] + m['gamma']*g[name+'_braking_feature']
    scores = score(groups); gates = {}
    for seed in ('43','67'):
        rows = [s for s in scores if s['subset']=='all' and s['case'].startswith(seed)]
        pooled = {name:math.sqrt(sum(s['groups']*s[name]['rmse']**2 for s in rows)/sum(s['groups'] for s in rows))
                  for name in ('paired','persistence','joint_gap','factor_gap')}
        gates[seed] = dict(rmse=pooled,pass_gate=(pooled['joint_gap']<=.9*pooled['paired']
             and pooled['joint_gap']<=.9*pooled['persistence']
             and pooled['joint_gap']<=pooled['factor_gap']
             and all(s['joint_gap']['rmse']<=min(s['paired']['rmse'],s['persistence']['rmse']) for s in rows)))
    save(HERE/'groups.json.gz', groups)
    save(HERE/'summary.json', dict(models=models,scores=scores,gates=gates,
        gate_pass=all(g['pass_gate'] for g in gates.values()),seconds=time.perf_counter()-started,
        production_adopted=False,autonomous=0,limitations=protocol['missing']))
    # Independent least-squares calculation on the same closed convex polygon.
    checks_fit = {}
    for branch, m in models.items():
        x = np.array([[g['relaxation_feature'],g[branch+'_braking_feature']] for g in train])
        y = np.array([g['acceleration_5s'] for g in train])
        q, r = np.linalg.qr(x, mode='reduced'); b = np.linalg.solve(r,q.T@y)
        def inside(v):
            return 1/120<=v[0]<=1/5 and v[0]/.5<=v[1]<=v[0]/.001
        candidates = [b] if inside(b) else []
        for fixed_tau in (5.,120.):
            a=1/fixed_tau
            z=x[:,1]; g=float(z@(y-a*x[:,0])/(z@z))
            candidates.append(np.array([a,np.clip(g,a/.5,a/.001)]))
        for fixed_A in (.001,.5):
            z=x[:,0]+x[:,1]/fixed_A; a=float(z@y/(z@z)); a=float(np.clip(a,1/120,1/5))
            candidates.append(np.array([a,a/fixed_A]))
        b=min(candidates,key=lambda v:float(np.sum((x@v-y)**2)))
        error=float(max(abs(b-np.array([m['alpha'],m['gamma']]))))
        assert error<1e-9
        checks_fit[branch]=error
    for p,d in {**inputs,**protected,stop['path']:stop['sha256']}.items():
        assert sha(p)==d,p
    assert sha(HERE/'frozen_models.json')==frozen
    save(HERE/'verification.json', dict(status='pass',pairs_recomputed=checks,
        max_material_target_error=max_target_error,independent_fit_error=checks_fit,
        protected_unchanged=True,inputs_unchanged=True))
    save(HERE/'completion.json', dict(status='complete_conditional_probe',fits=2,
         native=0,FZP=0,autonomous=0,production_adopted=False,full_goal='ACTIVE_NOT_QUALIFIED',
         source_sha256=sha(__file__),frozen_models_sha256=frozen))
    print(json.dumps(dict(models=models,gates=gates,checks=checks),ensure_ascii=False))


if __name__ == '__main__':
    main()
