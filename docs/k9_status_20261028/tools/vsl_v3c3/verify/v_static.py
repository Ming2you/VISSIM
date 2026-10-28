# v_static.py — VERIFY_VSL (2026-10-27 KST). Fresh script. Read-only on run folders.
# For each seed: VSL prepared/network vs NC3 prepared/network (file sha, inpx line diff hunks),
# fixed_events / fixed_readback rows (non-initial writes, final readback), readback.csv, native_simulation.csv.
import hashlib, json, os, sys, difflib, csv, re

RR = 'D:/VISSIM_runs/20261027_vsl_v3c3'
V3 = 'D:/VISSIM_runs/20261001_v3c3'
OUT = sys.argv[1]


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


res = {}
for s in (31, 41, 43):
    r = {}
    vn = f'{RR}/s{s}/prepared/network'
    nn = f'{V3}/s{s}_v3c3nc/prepared/network'
    # assets: compare every non-inpx, non-err, non-results file present in NC3 folder
    assets = {}
    for fn in sorted(os.listdir(nn)):
        p = os.path.join(nn, fn)
        if os.path.isdir(p) or fn.endswith('.err') or fn.endswith('.inpx'):
            continue
        q = os.path.join(vn, fn)
        assets[fn] = (sha(p) == sha(q)) if os.path.exists(q) else 'missing_in_vsl'
    extra = [fn for fn in os.listdir(vn) if not os.path.isdir(os.path.join(vn, fn)) and not fn.endswith('.err')
             and not fn.endswith('.inpx') and fn not in assets]
    r['assets_equal'] = all(v is True for v in assets.values())
    r['assets_n'] = len(assets)
    r['assets_not_equal'] = [k for k, v in assets.items() if v is not True]
    r['assets_extra_in_vsl'] = extra
    vi = [f for f in os.listdir(vn) if f.endswith('.inpx')][0]
    ni = [f for f in os.listdir(nn) if f.endswith('.inpx')][0]
    vl = open(os.path.join(vn, vi), encoding='utf-8').read().splitlines()
    nl = open(os.path.join(nn, ni), encoding='utf-8').read().splitlines()
    r['inpx'] = dict(vsl=vi, nc3=ni, vsl_sha=sha(os.path.join(vn, vi)), nc3_sha=sha(os.path.join(nn, ni)),
                     vsl_lines=len(vl), nc3_lines=len(nl))
    sm = difflib.SequenceMatcher(None, nl, vl, autojunk=False)
    hunks = []
    removed, added = [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            continue
        hunks.append(dict(tag=tag, nc3=[i1 + 1, i2], vsl=[j1 + 1, j2]))
        removed += nl[i1:i2]
        added += vl[j1:j2]
    r['inpx_hunks_n'] = len(hunks)
    r['inpx_removed_n'] = len(removed)
    r['inpx_added_n'] = len(added)
    # classify changed lines by leading XML tag
    def tagof(line):
        m = re.match(r'\s*<\/?([A-Za-z0-9_]+)', line)
        return m.group(1) if m else ('<blank>' if not line.strip() else '<text>')
    from collections import Counter
    r['removed_tags'] = dict(Counter(tagof(x) for x in removed))
    r['added_tags'] = dict(Counter(tagof(x) for x in added))
    r['removed_lines'] = removed[:40]
    # evaluation / sim lines among added (short)
    r['added_non_detector_lines'] = [x.strip()[:220] for x in added
                                     if tagof(x) not in ('dataCollectionMeasurement', 'dataCollectionPoint', 'dataCollectionPoints',
                                                         'dataCollectionMeasurements', 'dataCollPoint', 'dataCollPoints',
                                                         'dataCollMeasurement', 'dataCollMeasurements', '<blank>')][:60]
    r['hunks'] = hunks[:80]
    # DSD 63-66 and distribution 91 lines in both
    def grab(lines, pat, n=4):
        out = []
        for k, x in enumerate(lines):
            if re.search(pat, x):
                out.append(' | '.join(y.strip() for y in lines[k:k + n]))
        return out
    r['dsd63_66_vsl'] = grab(vl, r'<desSpeedDecision [^>]*no="6[3-6]"', 3)
    r['dsd63_66_nc3'] = grab(nl, r'<desSpeedDecision [^>]*no="6[3-6]"', 3)
    r['dist91_vsl'] = grab(vl, r'<desSpeedDistribution [^>]*no="91"', 4)
    r['sim_line_vsl'] = [x.strip() for x in vl if x.strip().startswith('<simulation ')]
    r['sim_line_nc3'] = [x.strip() for x in nl if x.strip().startswith('<simulation ')]
    # events / readback
    ev = list(csv.DictReader(open(f'{RR}/s{s}/prepared/fixed_events.csv', encoding='utf-8')))
    r['events'] = dict(n=len(ev), kinds=sorted({e['kind'] for e in ev}), times=sorted({e['time_s'] for e in ev}),
                       nos=sorted({int(e['no']) for e in ev}), classes=sorted({e['veh_class'] for e in ev}),
                       values=sorted({e['value'] for e in ev}))
    rb = list(csv.DictReader(open(f'{RR}/s{s}/run/fixed_readback.csv', encoding='utf-8')))
    phases = Counter((x['time_s'], x['phase'], x['kind']) for x in rb)
    r['readback_phase_counts'] = {f'{k[0]}|{k[1]}|{k[2]}': v for k, v in sorted(phases.items())}
    writes = [x for x in rb if x['phase'] not in ('initial', 'final')]
    r['readback_non_initial_final'] = writes[:30]
    r['readback_writes_n'] = len(writes)
    r['readback_writes_all_ok'] = all(x['ok'] == '1' and x['expected'] == x['actual'] for x in writes)
    fin = [x for x in rb if x['phase'] == 'final' and x['kind'] == 'vsl' and int(x['no']) in (63, 64, 65, 66)]
    r['final_dsd63_66'] = sorted({(x['no'], x['veh_class'], x['actual']) for x in fin})
    # initial vs final for all other DSD/SG: identical?
    ini = {(x['kind'], x['no'], x['veh_class']): x['actual'] for x in rb if x['phase'] == 'initial'}
    fn_ = {(x['kind'], x['no'], x['veh_class']): x['actual'] for x in rb if x['phase'] == 'final'}
    diffs = [(k, ini.get(k), fn_.get(k)) for k in sorted(set(ini) | set(fn_)) if ini.get(k) != fn_.get(k)]
    r['initial_vs_final_diffs'] = [list(map(str, d)) for d in diffs]
    r['readback_csv_vsl'] = open(f'{RR}/s{s}/run/readback.csv', encoding='utf-8').read().splitlines()
    r['readback_csv_nc3'] = open(f'{V3}/s{s}_v3c3nc/run/readback.csv', encoding='utf-8').read().splitlines()
    rj = json.load(open(f'{RR}/s{s}/run/run.json', encoding='utf-8-sig'))
    r['run_json_keys'] = {k: rj.get(k) for k in ('completed', 'exit_code', 'fixed_profile_validation_exit_code', 'mode',
                                                   'started', 'finished', 'seed') if k in rj}
    res[str(s)] = r

json.dump(res, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for s, r in res.items():
    print(s, 'assets_equal', r['assets_equal'], r['assets_n'], r['assets_not_equal'], r['assets_extra_in_vsl'])
    print('  inpx', r['inpx']['vsl_lines'], r['inpx']['nc3_lines'], 'hunks', r['inpx_hunks_n'], 'removed', r['inpx_removed_n'],
          'added', r['inpx_added_n'])
    print('  removed_tags', r['removed_tags'])
    print('  added_tags', r['added_tags'])
    print('  removed_lines', r['removed_lines'][:10])
    print('  sim', r['sim_line_vsl'], r['sim_line_nc3'])
    print('  events', r['events'])
    print('  readback phases', r['readback_phase_counts'])
    print('  writes', r['readback_writes_n'], r['readback_writes_all_ok'], 'final63-66', r['final_dsd63_66'])
    print('  init!=final', r['initial_vs_final_diffs'][:20])
    print('  dsd vsl', r['dsd63_66_vsl'][:1], 'equal_to_nc3', r['dsd63_66_vsl'] == r['dsd63_66_nc3'])
    print('  dist91', r['dist91_vsl'][:1])
    print('  run', r['run_json_keys'])
