"""VERIFY_VP bit-identity check of a re-run plant job against the original job (verifier tool, 2026-10-27 KST).
Read-only.  Does not import producer tools.

    python -B vv_bitcompare.py <original job dir> <re-run job dir> <out.json>

For every evaluation label present in the re-run probe.json: objective_veh_h, the 20 owner costs, action / response /
evaluated-action tokens must be equal (==, bit) to the original; the passive hook of that evaluation (matched by
batch + action token -> request sha) must have equal 'blocks' (per-block 31-cell integrals, exits, origin queue),
'first' (worker-seen parameters + initial state), steps, t_first, t_last.  Plan tokens and VSL views, recorded
fields and the ablation 'applied' records of the labels present are compared too.  Request sha equality is
reported (not required: the job folder differs).  Exit 0 = all bit-equal, 1 = a difference."""
import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True


def load(p):
    with open(p, 'r', encoding='utf-8-sig') as f:
        return json.load(f)


def hooks_of(jd):
    d = {}
    for f in sorted((Path(jd) / 'hooks').glob('vphook_*.json')):
        h = load(f)
        d.setdefault(h['request_sha256'], []).append(h)
    return d


def req_for(pr, label):
    ev = pr['evaluations'][label]
    rs = sorted({r['request_sha256'] for r in pr['runs'] if r['batch'] == ev['batch']
                 and r['action_token'] == ev['action_token']})
    return rs


def main():
    oj, rj, outp = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    po, pn = load(oj / 'probe.json'), load(rj / 'probe.json')
    ho, hn = hooks_of(oj), hooks_of(rj)
    res = {'schema': 'vv-bitcompare/1', 'original': oj.name, 'rerun': rj.name, 'labels': {}, 'diffs': []}
    res['rerun_exit_code'] = pn.get('exit_code')
    res['rerun_errors'] = pn.get('errors')
    for k in pn['plans']:
        if pn['plans'][k] != po['plans'].get(k):
            res['diffs'].append('plan %s' % k)
    if pn.get('recorded') != po.get('recorded'):
        res['diffs'].append('recorded')
    if pn.get('policy_sha256') != po.get('policy_sha256'):
        res['diffs'].append('policy_sha256')
    for k, v in (pn.get('checks') or {}).items():
        if po['checks'].get(k) != v:
            res['diffs'].append('check %s %r vs %r' % (k, po['checks'].get(k), v))
    for lab, ev in pn['evaluations'].items():
        eo = po['evaluations'].get(lab)
        d = {}
        if eo is None:
            res['diffs'].append('label missing in original %s' % lab)
            continue
        d['objective_equal'] = ev['objective_veh_h'] == eo['objective_veh_h']
        d['objective_diff'] = ev['objective_veh_h'] - eo['objective_veh_h']
        d['costs_equal'] = ev['costs'] == eo['costs']
        d['tokens_equal'] = all(ev.get(k) == eo.get(k) for k in ('action_token', 'response_token', 'evaluated_action_token',
                                                                  'prediction_model'))
        if 'applied' in ev:
            d['applied_equal'] = ev['applied'] == eo.get('applied')
        rn, ro = req_for(pn, lab), req_for(po, lab)
        d['request_sha_equal'] = rn == ro
        if len(rn) == 1 and len(ro) == 1 and hn.get(rn[0]) and ho.get(ro[0]):
            a, b = hn[rn[0]][0], ho[ro[0]][0]
            d['hook_blocks_equal'] = a['blocks'] == b['blocks']
            d['hook_first_equal'] = a['first'] == b['first']
            d['hook_steps_equal'] = (a['steps'], a['t_first'], a['t_last']) == (b['steps'], b['t_first'], b['t_last'])
            d['hook_errors'] = a.get('errors')
            d['hook_files_rerun'] = len(hn[rn[0]])
        else:
            d['hook_blocks_equal'] = False
            d['hook_first_equal'] = False
            d['hook_steps_equal'] = False
            d['hook_missing'] = [rn, ro]
        for k in ('objective_equal', 'costs_equal', 'tokens_equal', 'hook_blocks_equal', 'hook_first_equal',
                  'hook_steps_equal'):
            if d.get(k) is not True:
                res['diffs'].append('%s %s' % (lab, k))
        if d.get('applied_equal') is False:
            res['diffs'].append('%s applied' % lab)
        res['labels'][lab] = d
    res['n_labels'] = len(res['labels'])
    res['all_bit_equal'] = not res['diffs']
    tmp = outp.with_name(outp.name + '.tmp%d' % os.getpid())
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    os.replace(tmp, outp)
    print('VV_BITCOMPARE labels=%d all_bit_equal=%s diffs=%d' % (res['n_labels'], res['all_bit_equal'], len(res['diffs'])))
    return 0 if res['all_bit_equal'] else 1


if __name__ == '__main__':
    sys.exit(main())
