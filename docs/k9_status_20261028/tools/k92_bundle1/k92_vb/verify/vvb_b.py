"""VerifyVB 2026-10-22, part B: judge-behaviour probe for VB_PRECHECK_STOP.md V-B-D1 (NOT a V-B run, no adapter, no
replay, no V-B data).  It asks the declared VB-I1 judge itself -- GWT8 K9-2-5 k92_compare.compare (blob 2b2b5523...,
sha256 3e2da987...; amendment 29 section 6.2) -- what it returns when a decision output differs from the RR record
ONLY in the previous-action location / receipt / JSON-bytes leaves that a chain must change.

For each of the 10 chained OFF decisions of VB-I1 (amendment 24 :547) it builds, in a temporary folder under
--work, copies of the RR record action_T.{json,csv,joint.progress.jsonl}:
  ctrl     byte copies (no change)                                        -> expected PASS (harness sanity)
  pathonly strings / keys naming the RR previous action file action_<P>.* re-pointed to an OK2/vb location
  chain    pathonly + leaves equal to sha256(RR action_<P>.json) or sha256(RR action_<P>.json.applied) replaced by a
           different 64-hex value (the chain JSON / receipt bytes differ: state path, wall clock, receipt line 2);
           the CSV sha leaf is kept (chain CSV = record CSV when VB-I1 H1 holds for the previous decision)
  rrsib    like chain, but the location is a hypothetical sibling run folder of RR that N maps to <run>
           (writing there is NOT allowed; amendment 24 :522) -- shows whether a location trick alone would help
then calls compare(RR dir, copy dir, T, new_root=old_root=the run's frozen root, keyed=None) and keeps the verdict,
HARD group flags, generalized HARD diff paths, unclassified paths/rules and allowed counts.  The synthetic JSON is
deleted after each comparison (its sha256 is kept).  BLIND: paths, rule names, counts, sha only.

    python -B vvb_b.py --work <dir> --out <file.json>
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import sys

sys.dont_write_bytecode = True
JUDGE_DIR = 'D:/VISSIM-merge/sim3-n31-k8/diagnostics/sdmpc_n31_20260924/k8_gates/sa'
JUDGE_SHA = '3e2da987ff9e7b54ba2f51ad1b73bfdaf55f868bd6dedbf7937cf1f22fa4caba'
RR = 'D:/VISSIM_runs/20261004_sdmpc31_k8'
FRZ = {'sdmpc31_v3c3_k8j1r_s31': 'D:/VISSIM-merge/frozen/sdmpc31_b9734abe_202610141821',
       'sdmpc31_v3c3_k8j1_s43': 'D:/VISSIM-merge/frozen/sdmpc31_74cd495f_202610131824',
       'sdmpc31_v3c3_k8j1_s41': 'D:/VISSIM-merge/frozen/sdmpc31_74cd495f_202610131824'}
CHAINED = [('VB-31', 'sdmpc31_v3c3_k8j1r_s31', 3150, 3000), ('VB-43', 'sdmpc31_v3c3_k8j1_s43', 3150, 3000),
           ('VB-41', 'sdmpc31_v3c3_k8j1_s41', 3150, 3000)] + [
    ('VB-41w', 'sdmpc31_v3c3_k8j1_s41', t, p) for p, t in
    ((1, 150), (150, 300), (300, 450), (450, 600), (600, 750), (750, 900), (900, 1050))]
OK2_VB = 'D:\\VISSIM_runs\\20261001_v3c3\\reports\\k8\\k92_b1\\vb\\%s_off\\decisions\\'
RR_SIB = 'D:\\VISSIM_runs\\20261004_sdmpc31_k8\\sdmpc31_v3c3_k8j1vb_s41\\decisions_sdmpc31_v3c3_k8j1vb_s41\\'


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


def repoint(x, tag, prefix_rx, new_prefix, sha_map, stats):
    """re-point strings / keys that name tag (action_<P>) under the record folder; replace mapped sha values."""
    def fix(s):
        if tag in s.lower():
            t, n = prefix_rx.subn(lambda _m: new_prefix, s)
            if n:
                stats['repointed'] += 1
                return t
            stats['tag_not_under_record'] += 1
            return s
        if sha_map is not None and s.lower() in sha_map:
            stats['sha_replaced'] += 1
            return sha_map[s.lower()]
        return s
    if isinstance(x, dict):
        return {fix(k): repoint(v, tag, prefix_rx, new_prefix, sha_map, stats) for k, v in x.items()}
    if isinstance(x, list):
        return [repoint(v, tag, prefix_rx, new_prefix, sha_map, stats) for v in x]
    if isinstance(x, str):
        return fix(x)
    return x


def compact(rep):
    out = {k: rep.get(k) for k in ('verdict', 'hard_verdict', 'n_diff_leaves_total', 'unclassified_n',
                                   'allowed_counts', 'h5_declared', 'why')}
    for g in ('H1', 'H2', 'H3', 'H4', 'H5'):
        if g in rep:
            out[g] = {'same': rep[g]['same']} if g == 'H1' else {
                'same': rep[g]['same'], 'n': rep[g]['n_diff_leaves'], 'paths': rep[g]['diff_paths_generalized']}
    out['unclassified'] = rep.get('unclassified')
    out['r3_checks'] = [{'path': r['path'], 'ok': r['new_value_is_file_sha256']} for r in rep.get('r3_checks', [])]
    out['k92_checks'] = rep.get('k92_checks')
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    if os.path.exists(a.out) or os.path.exists(a.work):
        sys.exit('output or work folder exists (never reused)')
    if sha(JUDGE_DIR + '/k92_compare.py') != JUDGE_SHA:
        sys.exit('judge bytes differ from K9-2-5')
    sys.path.insert(0, JUDGE_DIR)
    import k92_compare as kc
    os.makedirs(a.work)
    res = {'schema': 'vvb-b/v1', 'tool_sha256': sha(os.path.abspath(__file__)), 'judge_sha256': JUDGE_SHA,
           'judge_file': os.path.abspath(kc.__file__), 'rows': []}
    for chain, run, t, p in CHAINED:
        d = '%s/%s/decisions_%s' % (RR, run, run)
        s6, tag = '%06d' % t, 'action_%06d' % p
        prefix_rx = re.compile(r'(?i)d:[\\/]+vissim_runs[\\/]+20261004_sdmpc31_k8[\\/]+%s[\\/]+decisions_%s[\\/]+'
                               r'(?=action_%06d)' % (run, run, p))
        prev_json, prev_ack = '%s/%s.json' % (d, tag), '%s/%s.json.applied' % (d, tag)
        sha_map = {sha(prev_json): hashlib.sha256(b'vvb-synthetic-json:' + tag.encode()).hexdigest()}
        if os.path.isfile(prev_ack):
            sha_map[sha(prev_ack)] = hashlib.sha256(b'vvb-synthetic-receipt:' + tag.encode()).hexdigest()
        raw = json.load(open('%s/action_%s.json' % (d, s6), encoding='utf-8-sig'))
        for variant in ('ctrl', 'pathonly', 'chain', 'rrsib'):
            w = os.path.join(a.work, '%s_%s_%s' % (chain, s6, variant))
            os.makedirs(w)
            for suf in ('.csv', '.joint.progress.jsonl'):
                src = '%s/action_%s%s' % (d, s6, suf)
                if os.path.isfile(src):
                    shutil.copyfile(src, os.path.join(w, 'action_%s%s' % (s6, suf)))
            jp = os.path.join(w, 'action_%s.json' % s6)
            stats = {'repointed': 0, 'tag_not_under_record': 0, 'sha_replaced': 0}
            if variant == 'ctrl':
                shutil.copyfile('%s/action_%s.json' % (d, s6), jp)
            else:
                newp = RR_SIB if variant == 'rrsib' else OK2_VB % chain
                doc = repoint(raw, tag, prefix_rx, newp, None if variant == 'pathonly' else sha_map, stats)
                with open(jp, 'w', encoding='utf-8') as f:
                    json.dump(doc, f, ensure_ascii=False)
            js = sha(jp)
            rep = kc.compare(d, w, t, FRZ[run], keyed=None, old_root=FRZ[run], label='vvb_%s_%s' % (chain, variant))
            row = {'chain': chain, 'run': run, 'T': t, 'prev_T': p, 'variant': variant, 'synthetic_json_sha256': js,
                   'stats': stats, 'result': compact(rep)}
            res['rows'].append(row)
            print('B %s T=%d<-%d %-8s verdict=%s hard=%s H=%s uncl=%s stats=%s' % (
                chain, t, p, variant, rep.get('verdict'), rep.get('hard_verdict'),
                {g: rep[g]['same'] for g in ('H1', 'H2', 'H3', 'H4', 'H5') if g in rep}, rep.get('unclassified_n'),
                stats), flush=True)
            os.remove(jp)
    with open(a.out, 'w', encoding='utf-8') as f:
        json.dump(res, f, indent=1, sort_keys=True, default=str)
    print('VVB_B_DONE', flush=True)


if __name__ == '__main__':
    main()
