"""Make the closed leaf list of K8_PREDECLARATION_AMENDMENT_32 section 2.2 (D-K9-62) from the V-B precheck evidence.
Diagnostics only, never committed.  Standard library only.  Reads two files (paths, rule names, counts only):

  VerifyVB independent recount  KB/k92_vb/verify/out/vvb_a_01.json   (sha256 618b9592..., all 10 chained decisions)
  dev probe classification      KB/k92_vb/dev/classify_out.json        (sha256 eda96865..., 5 decisions of v3c3-s41)

and writes AD32/vb_closed_leaves.json (schema k92vb-closed-leaves/v1):
  types.NN  no-control <- no-control   (VB-41w T=150, 300, 450, 600, 750)
  types.SN  first SDMPC <- no-control  (VB-41w T=900)
  types.SS  SDMPC <- SDMPC             (VB-31 / VB-43 / VB-41 T=3,150, VB-41w T=1,050)
  each: leaves = the generalized leaf paths (k92_compare.gen form) that MUST differ in a chained decision
        (VB_PRECHECK_STOP r2 section 2.2 'differs yes'), with HARD group, previous file and how the value refers to it;
        csv_sha_equal_if_same = the D2 CSV sha leaves (not in the list: equal when the chained CSV equals the record).
Checks (SystemExit otherwise): the input shas; every decision of one type gives the same leaf set and instance count;
the counts are 3/3/1 (NN), 21/12/1 (SN), 25/16/3 (SS) as section 2.2 of the report; for the 5 decisions in both files
the classify_out.json 'differs_by_construction' set equals the vvb_a_01.json 'yes' set."""
import collections
import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
KB = Path(r'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/'
          r'491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/k92/bundle1')
VVB_A = KB / 'k92_vb' / 'verify' / 'out' / 'vvb_a_01.json'
VVB_A_SHA = '618b9592e7753147cbc3cf139d4140cc1a099bc636acf2e151f8c8aeb8323741'
CLASSIFY = KB / 'k92_vb' / 'dev' / 'classify_out.json'
CLASSIFY_SHA = 'eda96865db22fb67165c5fa4a3569954962934405e9e17af389eeba78e9c1ea6'
OUT = Path(__file__).resolve().parent / 'vb_closed_leaves.json'
EXPECT = {'NN': (3, 3, 1), 'SN': (21, 12, 1), 'SS': (25, 16, 3)}
NAMES = {'NN': '무제어 ← 무제어', 'SN': '첫 SDMPC ← 무제어', 'SS': 'SDMPC ← SDMPC'}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def dtype(T, prev_T):
    if T < 900 and prev_T < 900:
        return 'NN'
    if T == 900 and prev_T < 900:
        return 'SN'
    if T > 900 and prev_T >= 900:
        return 'SS'
    raise SystemExit('unknown decision type T=%s prev=%s' % (T, prev_T))


def main():
    for p, want in ((VVB_A, VVB_A_SHA), (CLASSIFY, CLASSIFY_SHA)):
        if sha(p) != want:
            raise SystemExit('input sha differs: %s' % p)
    a = json.loads(VVB_A.read_text(encoding='utf-8'))
    c = json.loads(CLASSIFY.read_text(encoding='utf-8'))
    per_type, decisions = {}, []
    for d in a['A']['decisions']:
        t = dtype(int(d['T']), int(d['prev_T']))
        must = [r for r in d['rows'] if str(r['differs']).startswith('yes')]
        csv_eq = sorted({r['path'] for r in d['rows'] if not str(r['differs']).startswith('yes')})
        if (d['n_leaves'], d['n_must_differ'], d['n_must_differ_hard']) != EXPECT[t]:
            raise SystemExit('counts differ from section 2.2 for %s T=%s' % (d['chain'], d['T']))
        if len(d['rows']) != d['n_leaves'] or len(must) != d['n_must_differ']:
            raise SystemExit('row counts inconsistent for %s T=%s' % (d['chain'], d['T']))
        inst = collections.Counter((r['path'], r.get('hard'), r['file'], r['via'], r['outcome']) for r in must)
        key = (tuple(sorted(inst.items())), tuple(csv_eq))
        if t in per_type and per_type[t]['key'] != key:
            raise SystemExit('decisions of type %s give different leaf sets' % t)
        per_type.setdefault(t, {'key': key, 'inst': inst, 'csv_eq': csv_eq})
        decisions.append({'chain': d['chain'], 'T': int(d['T']), 'prev_T': int(d['prev_T']), 'type': t})
        if d['chain'] == 'VB-41w' or (d['chain'] == 'VB-41' and int(d['T']) == 3150):
            rows = c.get(str(int(d['T'])))
            if rows is not None:
                cset = collections.Counter(r['path'] for r in rows if r['differs_by_construction'])
                aset = collections.Counter(r['path'] for r in must)
                if cset != aset:
                    raise SystemExit('classify_out and vvb_a disagree at T=%s' % d['T'])
    if sorted(per_type) != ['NN', 'SN', 'SS']:
        raise SystemExit('missing decision types: %s' % sorted(per_type))
    types = {}
    for t, v in sorted(per_type.items()):
        leaves = {}
        for (path, hard, f, via, outcome), n in v['inst'].items():
            row = leaves.setdefault(path, {'path': path, 'hard': hard, 'previous_file': f, 'via': via,
                                           'outcome_in_report': outcome, 'record_instances': 0})
            if (row['hard'], row['previous_file'], row['via'], row['outcome_in_report']) != (hard, f, via, outcome):
                raise SystemExit('one path with two descriptions: %s' % path)
            row['record_instances'] += n
        rows = sorted(leaves.values(), key=lambda r: (r['hard'] is None, r['path']))
        types[t] = {'name': NAMES[t], 'leaves': rows, 'n_paths': len(rows),
                    'n_instances': sum(r['record_instances'] for r in rows),
                    'n_hard_paths': sum(1 for r in rows if r['hard']), 'csv_sha_equal_if_same': v['csv_eq']}
    decisions.sort(key=lambda d: ({'VB-31': 0, 'VB-43': 1, 'VB-41': 2, 'VB-41w': 3}[d['chain']], d['T']))
    doc = {'schema': 'k92vb-closed-leaves/v1',
           'source': {'report': 'KB/k92_vb/VB_PRECHECK_STOP.md r2 section 2.2 (b96637d9...)',
                      'vvb_a_01.json': VVB_A_SHA, 'classify_out.json': CLASSIFY_SHA,
                      'maker': 'AD32/make_closed32.py'},
           'types': types, 'decisions': decisions}
    data = (json.dumps(doc, indent=1, ensure_ascii=False, sort_keys=True) + '\n').encode('utf-8')
    OUT.write_bytes(data)
    print('CLOSED32 %s NN=%d/%d SN=%d/%d SS=%d/%d decisions=%d' % (
        hashlib.sha256(data).hexdigest(), types['NN']['n_paths'], types['NN']['n_instances'], types['SN']['n_paths'],
        types['SN']['n_instances'], types['SS']['n_paths'], types['SS']['n_instances'], len(decisions)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
