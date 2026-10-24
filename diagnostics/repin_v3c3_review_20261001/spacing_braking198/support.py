"""Post-result support audit; never refit, discard failures, or change the gate."""
from collections import defaultdict
import math

from diagnostics.repin_v3c3_review_20261001.spacing_braking198.check import read, save, sha, HERE, R


def main():
    assert not (HERE/'support.json').exists()
    groups=read(HERE/'groups.json.gz'); rows=read(R/'neighbor_information194/rows.json.gz')
    lookup=defaultdict(list)
    for r in rows:lookup[r['case'],r['t'],r['cell'],r['lane']].append(r)
    output=[]; pins={}; witnesses=[]
    for arm in ('hold','release'):
        path=R/'blocking176'/f'{arm}_frames.json.gz'
        pins[str(path)]=sha(path); d=read(path); ix={k:i for i,k in enumerate(d['fields'])}
        categories=defaultdict(list); counts=defaultdict(int)
        for g in groups:
            if g['case']!='67_'+arm:continue
            fr=d['frames'][str(g['t'])]; overlapping=False; mismatch=False
            for r in lookup[g['case'],g['t'],g['cell'],g['lane']]:
                z=fr[r['id']]; front=fr[r['leader']]
                overlap=r['gap_m']<float(front[ix['length']])
                wrong_target=z[ix['target_type']]!='Vehicle' or str(z[ix['target']])!=r['leader']
                counts['pairs']+=1; counts['projected_body_overlap']+=int(overlap)
                counts['geometric_target_mismatch']+=int(wrong_target)
                overlapping |= overlap; mismatch |= wrong_target
                if overlap and len(witnesses)<30:
                    witnesses.append(dict(case=g['case'],t=g['t'],cell=g['cell'],lane=g['lane'],
                        id=r['id'],leader=r['leader'],front_spacing=r['gap_m'],
                        leader_length=front[ix['length']],native_target=z[ix['target']],
                        current_lnchg=z[ix['lnchg']]))
            categories['all'].append(g)
            categories['has_projected_overlap' if overlapping else 'no_projected_overlap'].append(g)
            if not overlapping and not mismatch:categories['all_current_pairs_supported'].append(g)
        scores={}
        for category,gg in categories.items():
            scores[category]=dict(groups=len(gg))
            for name in ('persistence','paired','joint_gap','factor_gap'):
                scores[category][name]=math.sqrt(sum((g.get(name+'_prediction',0)-g['acceleration_5s'])**2 for g in gg)/len(gg))
        output.append(dict(case='67_'+arm,counts=dict(counts),scores=scores))
    for p,d in pins.items():assert sha(p)==d
    save(HERE/'support.json',dict(status='complete_posthoc_support_diagnostic',scores=output,
        witnesses=witnesses,input_sha256=pins,fits=0,forecasts=0,
        limitations='Projected front gap smaller than recorded leader length is an unsupported 1D body configuration, not proof of native collision or lane change. Current target agreement is not a future relation model. Supported subset is posthoc; original failed gate is retained.'))
    print(output)


if __name__=='__main__':main()
