"""ReviewDeclare A32 check (read-only, RR recorded files only; no V-B data, no replay, no adapter).
For each of the 10 chained OFF decisions of amendment 32 section 2.2, find every leaf of the RECORDED decision JSON
whose value (a) contains the file name of ANY earlier decision of the same chain (immediate previous and earlier), or
(b) equals the sha256 of any file of any earlier decision of the same chain (json, csv, .json.applied, .joint.json,
.joint.progress.jsonl, .joint_written.json, .decision_budget.json, .json.sdmpc_pending, .stdout.txt, .stderr.txt),
or (c) contains the decision folder name.  Paths are KC-generalized ([*], lower-case keys).  Also the same scan for
the 4 chain-first decisions (earlier files there are RR files the chain also reads, so they cannot differ).
Output: paths, file kinds, T' and counts only -- no value."""
import hashlib
import json
import re
import sys
from pathlib import Path

RR = Path('D:/VISSIM_runs/20261004_sdmpc31_k8')
RUNS = {'VB-31': 'sdmpc31_v3c3_k8j1r_s31', 'VB-43': 'sdmpc31_v3c3_k8j1_s43', 'VB-41': 'sdmpc31_v3c3_k8j1_s41',
        'VB-41w': 'sdmpc31_v3c3_k8j1_s41'}
CHAIN_T = {'VB-31': [3000, 3150], 'VB-43': [3000, 3150], 'VB-41': [3000, 3150],
           'VB-41w': [1, 150, 300, 450, 600, 750, 900, 1050]}
KINDS = ('.json', '.csv', '.json.applied', '.joint.json', '.joint.progress.jsonl', '.joint_written.json',
         '.decision_budget.json', '.json.sdmpc_pending', '.stdout.txt', '.stderr.txt')
HEX = re.compile(r'^[0-9a-f]{64}$')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def leaves(x, p, out):
    if isinstance(x, dict):
        for k, v in x.items():
            leaves(v, p + '/' + str(k).lower(), out)
    elif isinstance(x, list):
        for i, v in enumerate(x):
            leaves(v, p + '[%d]' % i, out)
    else:
        out.append((p, x))


def gen(p):
    return re.sub(r'\[\d+\]', '[*]', p)


def main(dest):
    res = {'schema': 'rv32-nested/v1', 'decisions': []}
    for chain, ts in CHAIN_T.items():
        run = RUNS[chain]
        dec = RR / run / ('decisions_' + run)
        first_T = ts[0]
        for idx, T in enumerate(ts):
            # earlier files of this chain: for the chain-first decision the RR previous (T - 150) is read as is
            earlier = ts[:idx] if idx > 0 else []
            prevs = {}
            for Tp in earlier:
                for k in KINDS:
                    f = dec / ('action_%06d%s' % (Tp, k))
                    if f.is_file():
                        prevs[sha(f)] = (Tp, k)
            doc = json.loads((dec / ('action_%06d.json' % T)).read_text(encoding='utf-8-sig'))
            lv = []
            leaves(doc, '', lv)
            hits, names, dirs, selfn, dirpaths = [], [], 0, [], set()
            for p, v in lv:
                if isinstance(v, str):
                    vl = v.lower().replace('\\', '/')
                    if HEX.match(vl) and vl in prevs:
                        hits.append({'path': gen(p), 'T_prev': prevs[vl][0], 'file': prevs[vl][1],
                                     'immediate': prevs[vl][0] == (earlier[-1] if earlier else None)})
                    for Tp in earlier:
                        if ('action_%06d' % Tp) in vl:
                            names.append({'path': gen(p), 'T_prev': Tp,
                                          'immediate': Tp == earlier[-1]})
                    if ('action_%06d' % T) in vl:
                        selfn.append(gen(p))
                    if ('decisions_' + run).lower() in vl and not any(('action_%06d' % Tp) in vl for Tp in earlier):
                        dirs += 1
                        dirpaths.add(gen(p))
            row = {'chain': chain, 'T': T, 'first': idx == 0, 'earlier_T': earlier, 'n_leaves': len(lv),
                   'sha_hits': hits, 'name_hits': names, 'other_decision_dir_strings': dirs,
                   'other_decision_dir_paths': sorted(dirpaths), 'self_name_paths': sorted(set(selfn))}
            row['nonimmediate_sha_hits'] = [h for h in hits if not h['immediate']]
            row['nonimmediate_name_hits'] = [h for h in names if not h['immediate']]
            res['decisions'].append(row)
    Path(dest).write_text(json.dumps(res, indent=1, sort_keys=True), encoding='utf-8')
    for r in res['decisions']:
        print('RV32N %s T=%d first=%s sha_hits=%d name_hits=%d nonimm_sha=%d nonimm_name=%d dirstr=%d self=%d' % (
            r['chain'], r['T'], r['first'], len(r['sha_hits']), len(r['name_hits']), len(r['nonimmediate_sha_hits']),
            len(r['nonimmediate_name_hits']), r['other_decision_dir_strings'], len(r['self_name_paths'])))


if __name__ == '__main__':
    main(sys.argv[1])
