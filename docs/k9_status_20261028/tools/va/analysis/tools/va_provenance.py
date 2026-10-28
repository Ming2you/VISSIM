r"""V-A analysis step 0 (amendment 34 sec.8.0): input hashes only (no value of any run is read).
python -B va_provenance.py --profile va|selftest  ->  <out>/va_provenance.json
Files: per run FZP / run-end .err / .inpx (size, sha256), runner logs and provenance (sha256), action JSON count;
J1 / NC3 scan files (sha256 vs amendment 34 sec.8.1 prefixes); stage1 tools; link sets; documents.
BELOW_NORMAL, one file at a time."""
import os
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import va_common as V  # noqa: E402

DOCS = {
    'amendment34': os.path.join(V.SP, 'K8_PREDECLARATION_AMENDMENT_34.md'),
    'amendment34_fixed': os.path.join(V.VA, 'AMENDMENT34_FIXED.md'),
    'decisions_notes': os.path.join(V.SP, 'K9_1_J1_NOTES_20261013.md'),
    'j1_analysis_method': os.path.join(V.SP, 'j1', 'analysis', 'ANALYSIS_METHOD.md'),
    'j1_report': os.path.join(V.SP, 'j1', 'analysis', 'J1_REPORT.md'),
    'j1_validity': os.path.join(V.SP, 'j1', 'analysis', 'VALIDITY.md'),
    'j1_caveat_addendum': os.path.join(V.SP, 'j1', 'J1_CAVEAT_ADDENDUM.md'),
    'link_sets': V.LINK_SETS,
}


def fileinfo(p, with_sha=True):
    if not os.path.isfile(p):
        return {'path': p, 'present': False}
    r = {'path': p, 'present': True, 'bytes': os.path.getsize(p)}
    if with_sha:
        r['sha256'] = V.sha(p)
    return r


def main():
    prof = V.profile_from_argv()
    pin = V.require_pinned(prof, __file__)
    t0 = time.time()
    prio = V.set_below_normal()
    res = {'schema': 'k92-va-provenance/v1', 'profile': prof.name, 'pinned': pin, 'priority': hex(prio),
           'runs': {}, 'scans': {}, 'stage1': {}, 'docs': {}}
    for s in V.SEEDS:
        for arm, info in (('va', prof.va_run(s)), ('j1', V.j1_run(s))):
            tag = '%s_s%d' % (arm, s)
            r = {k: fileinfo(info[k]) for k in ('fzp', 'err', 'err_root', 'inpx', 'runlog', 'launch', 'action_csv',
                                                'provenance')}
            r['name'] = info['name']
            r['action_json_count'] = len(V.action_files(info['dec'])) if os.path.isdir(info['dec']) else None
            r['err_root_same_sha'] = (r['err'].get('sha256') is not None and
                                      r['err'].get('sha256') == r['err_root'].get('sha256'))
            res['runs'][tag] = r
            print(tag, 'fzp', r['fzp'].get('bytes'), 'actions', r['action_json_count'], flush=True)
        nc = V.nc3_run(s)
        res['runs']['nc3_s%d' % s] = {k: fileinfo(nc[k]) for k in ('fzp', 'err')}
    for tag in sorted(V.J1_SCAN_SHA16):
        d, ok = V.j1_scan_dir(prof, tag)
        res['scans'][tag] = {'dir': d, 'sha16_match_amendment34_8_1': ok,
                             'scan': fileinfo(os.path.join(d, 'scan.json')),
                             'uninserted': fileinfo(os.path.join(d, 'uninserted.json'))}
    for n in V.STAGE1_SHA:
        h = V.sha(os.path.join(V.STAGE1, n))
        res['stage1'][n] = {'sha256': h, 'expected': V.STAGE1_SHA[n], 'ok': h == V.STAGE1_SHA[n]}
    for k, p in DOCS.items():
        res['docs'][k] = fileinfo(p)
    res['tools'] = {n: V.sha(os.path.join(V.TOOLS, n)) for n in sorted(os.listdir(V.TOOLS)) if n.endswith('.py')}
    res['elapsed_sec'] = round(time.time() - t0, 1)
    V.jdump(res, os.path.join(prof.out, 'va_provenance.json'))
    print('stage1 ok', all(v['ok'] for v in res['stage1'].values()),
          'scans sha16 ok', {k: v['sha16_match_amendment34_8_1'] for k, v in res['scans'].items()})
    print('elapsed', res['elapsed_sec'])


if __name__ == '__main__':
    main()
