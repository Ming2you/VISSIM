# -*- coding: utf-8 -*-
"""fwe_inventory.py - D-K9-106 Declare step inventory (read-only, light).

Reads only: run provenance JSON, small run files (.err, inpx, readback, action CSV), and the
METADATA of existing analysis caches (JSON head fields, npz array shapes).  Never opens an FZP.
FZP sha256 is taken from existing caches (matched by full path), with size / mtime recorded now.
Writes only <SP>/fwe_decomp/out/inventory.json.

Excluded by name before opening (never opened, never hashed): any path containing 'sealed',
seed tokens _s37/_s59/_s61/_s67 in cache file names, v3c3-s47 / s53 caches (nc_s47.json,
nc_s53.json), raw/historical_vsl_s43 (out of scope).
"""
import glob, hashlib, json, os, re, sys, time

SP = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8'
CH = SP + '/codex_handoff'
CW = CH + '/work'
OUT = SP + '/fwe_decomp/out/inventory.json'
H = 'D:/VISSIM_handoff/20261024'

FORBID = re.compile(r'(sealed|_s37|_s59|_s61|_s67|nc_s47|nc_s53|_s47\b|historical_vsl_s43)', re.I)


def norm(p):
    return os.path.normpath(p).replace('\\', '/').lower()


def sha(p, limit=200 * 1024 * 1024):
    if FORBID.search(p):
        raise RuntimeError('forbidden path ' + p)
    if os.path.getsize(p) > limit:
        return None
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def finfo(p, do_sha=True):
    if p is None or not os.path.exists(p):
        return None
    st = os.stat(p)
    return {'path': p.replace('\\', '/'), 'bytes': st.st_size,
            'mtime_kst': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(st.st_mtime)),
            'sha256': sha(p) if do_sha else None}


def one(pattern):
    g = sorted(x for x in glob.glob(pattern) if not FORBID.search(x))
    return g[0] if len(g) == 1 else (g if g else None)


# ------------------------------------------------------------------ arms
def v3c3_runs():
    R = []
    for s in (31, 41, 43):
        b = 'D:/VISSIM_runs/20261001_v3c3/s%d_v3c3nc' % s
        R.append(dict(arm='NC3', net='v3c3', root=b, prov=b + '/run/run.json',
                      fzp=one(b + '/run/vissim_eval/*.fzp'), err=one(b + '/run/*_001.err'),
                      inpx=one(b + '/prepared/network/*.inpx'), readback=b + '/run/readback.csv'))
        b = 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s%d' % s
        R.append(dict(arm='V-A', net='v3c3', root=b, prov=one(b + '/run_provenance_*.json'),
                      fzp=one(b + '/vissim_eval/*.fzp'), err=b + '/vissim_simulation_001.err',
                      inpx=one(b + '/network/*.inpx'), dec=one(b + '/decisions_*'), action=one(b + '/action_*.csv')))
        b = 'D:/VISSIM_runs/20261026_codex_b_v3c3/s%d/sdmpc' % s
        R.append(dict(arm='B', net='v3c3', root=b, prov=one(b + '/run_provenance_*.json'),
                      fzp=one(b + '/vissim_eval/*.fzp'), err=b + '/vissim_simulation_001.err',
                      inpx=one(b + '/network/*.inpx'), dec=one(b + '/decisions_*'), action=one(b + '/action_*.csv')))
        b = 'D:/VISSIM_runs/20261027_vsl_v3c3/s%d' % s
        R.append(dict(arm='VSL', net='v3c3', root=b, prov=b + '/run/run.json',
                      fzp=one(b + '/run/vissim_eval/*.fzp'), err=one(b + '/run/*_001.err'),
                      inpx=one(b + '/prepared/network/*.inpx'), readback=b + '/run/fixed_readback.csv'))
    # J1 reference (caches only; path from OMEGA701 cache table)
    for s, p in ((31, 'D:/VISSIM_runs/20261004_sdmpc31_k8/sdmpc31_v3c3_k8j1r_s31'),
                 (41, 'D:/VISSIM_runs/20261004_sdmpc31_k8/sdmpc31_v3c3_k8j1_s41'),
                 (43, 'D:/VISSIM_runs/20261004_sdmpc31_k8/sdmpc31_v3c3_k8j1_s43')):
        R.append(dict(arm='J1(참고)', net='v3c3', root=p, prov=one(p + '/run_provenance_*.json'),
                      fzp=one(p + '/vissim_eval/*.fzp'), err=p + '/vissim_simulation_001.err',
                      inpx=one(p + '/network/*.inpx'), dec=one(p + '/decisions_*'), action=one(p + '/action_*.csv')))
    return R


def cf_runs():
    R = []
    b = H + '/raw/nc'
    R.append(dict(arm='codex NC', net='64cf', root=b, prov=one(b + '/run_provenance_*.json'),
                  fzp=one(b + '/vissim_eval/*.fzp'), err=one(b + '/vissim_eval/*.err') or one(b + '/*_001.err')))
    for a in ('joint', 'window', 'off', 'freeway_only', 'urban_only'):
        b = H + '/raw/%s/sdmpc' % a
        R.append(dict(arm='codex ' + a, net='64cf', root=b, prov=one(b + '/run_provenance_*.json'),
                      fzp=one(b + '/vissim_eval/*.fzp'), err=b + '/vissim_simulation_001.err',
                      inpx=one(b + '/network/*.inpx'), dec=one(b + '/decisions_*'), action=one(b + '/action_*.csv')))
    b = 'D:/VISSIM_runs/20261025_codex_a1_s29/sdmpc'
    R.append(dict(arm='A1', net='64cf', root=b, prov=one(b + '/run_provenance_*.json'),
                  fzp=one(b + '/vissim_eval/*.fzp'), err=b + '/vissim_simulation_001.err',
                  inpx=one(b + '/network/*.inpx'), dec=one(b + '/decisions_*'), action=one(b + '/action_*.csv')))
    for a in ('none', 'vsl'):
        b = 'D:/VISSIM_runs/vsl_repro_s29/%s/run' % a
        R.append(dict(arm='LNC' if a == 'none' else 'vsl_repro vsl', net='64cf', root=b, prov=b + '/run.json',
                      fzp=one(b + '/vissim_eval/*.fzp'), err=one(b + '/*_001.err'), readback=b + '/fixed_readback.csv'))
    for grp, arms in (('historical_alinea_s29', ('rm', 'both')), ('historical_vsl_s29', ('none', 'bottleneck90'))):
        for a in arms:
            b = H + '/raw/%s/%s/run' % (grp, a)
            R.append(dict(arm='%s/%s' % (grp, a), net='64cf', root=b, prov=b + '/run.json',
                          fzp=one(b + '/vissim_eval/*.fzp'), err=one(b + '/*_001.err')))
    return R


def read_seed(p):
    if not p or not isinstance(p, str) or not os.path.exists(p):
        return None, None
    d = json.load(open(p, encoding='utf-8-sig'))
    return d.get('seed'), sha(p)


# ------------------------------------------------------------------ caches
def runs_from_py(py):
    """tag -> path from a RUNS = {...} dict literal in an existing tool (regex only, never executed)."""
    m = {}
    if not os.path.exists(py):
        return m
    for t, p in re.findall(r"'([A-Za-z0-9_]+)':\s*'(D:/[^']+\.fzp)'", open(py, encoding='utf-8').read()):
        m[t] = p
    return m


def cache_index():
    C = []  # dicts: kind, file, fzp, fzp_sha256, extra

    def add(kind, f, fzp, fsha, extra=None):
        if FORBID.search(f):
            return
        C.append(dict(kind=kind, file=f.replace('\\', '/'), file_sha256=sha(f), fzp=fzp, fzp_key=norm(fzp) if fzp else None,
                      fzp_sha256_cached=fsha, extra=extra or {}))

    # omega npz caches: per link x 5 s frame counts (M)
    import numpy as np
    for d in (CW + '/omega/cache', CW + '/omega_b/cache'):
        for j in sorted(glob.glob(d + '/*.json')):
            if FORBID.search(j) or j.endswith('scan_log.json'):
                continue
            m = json.load(open(j, encoding='utf-8'))
            npz = j[:-5] + '.npz'
            z = np.load(npz)
            add('omega_npz(링크×5s 프레임 재고)', npz, m['fzp'], m.get('fzp_sha256'),
                dict(meta=j.replace('\\', '/'), meta_sha256=sha(j), M_shape=list(z['M'].shape), frames=m.get('frames'),
                     first_sec=m.get('first_sec'), last_sec=m.get('last_sec'), fzp_bytes_at_scan=m.get('fzp_bytes'),
                     scan_started=m.get('started')))
    # vhr link integrals (4 forms) and first-seen
    vmap = {}
    for py in (CW + '/vhr/vhr_firstseen.py', CW + '/vhr/vhr_scan.py', CW + '/vhr_b/vhr_firstseen_b.py', CW + '/vhr_b/vhr_scan_b.py',
               CW + '/a1/full/vhr_firstseen_a1.py'):
        vmap[py] = runs_from_py(py)
    for d, pys in ((CW + '/vhr/scan_out', (CW + '/vhr/vhr_firstseen.py',)), (CW + '/vhr_b/scan_out', (CW + '/vhr_b/vhr_firstseen_b.py',))):
        for j in sorted(glob.glob(d + '/*.json')):
            if FORBID.search(j):
                continue
            b = os.path.basename(j)[:-5]
            m = json.load(open(j, encoding='utf-8'))
            if b.startswith('first_'):
                tag = b[6:]
                fzp = None
                for py in pys:
                    fzp = vmap[py].get(tag) or fzp
                add('first_seen(입력별 첫 관측 누적)', j, fzp, None, dict(tag=tag, map_from=pys[0].replace('\\', '/'), vehicles=m.get('vehicles')))
            else:
                add('vhr_link_integrals(링크별 적분 4꼴)', j, m.get('path'), m.get('file_sha256'), dict(tag=m.get('tag'), n_frames=m.get('n_frames')))
    for j in sorted(glob.glob(CW + '/a1/full/firstseen/first_*.json')):
        tag = os.path.basename(j)[6:-5]
        fzp = {'a1': 'D:/VISSIM_runs/20261025_codex_a1_s29/sdmpc/vissim_eval/sdmpc31_sdmpc8100_s29_001.fzp',
               'lnc': 'D:/VISSIM_runs/vsl_repro_s29/none/run/vissim_eval/vsl_seed29_none_001.fzp'}.get(tag)
        add('first_seen(입력별 첫 관측 누적)', j, fzp, None, dict(tag=tag, map_from='a1/full/vhr_firstseen_a1.py RUNS (a1, lnc)'))
    j = CW + '/a1/full/scan/a1.json'
    m = json.load(open(j, encoding='utf-8'))
    add('a1_link_residence(링크별 0-8100 적분)', j, m['fzp'], None, dict(lf_sha256_le_8100=m.get('full_sha256_lf_le_8100'), bytes=m.get('bytes')))
    # VSL v3c3 caches
    vs = SP + '/vsl_v3c3/out'
    for j in sorted(glob.glob(vs + '/vhr/*.json')):
        b = os.path.basename(j)[:-5]
        m = json.load(open(j, encoding='utf-8'))
        if b.startswith('first_'):
            s = b.split('_s')[-1]
            fzp = 'D:/VISSIM_runs/20261027_vsl_v3c3/s%s/run/vissim_eval/baseline_s%s_v3c3vsl_001.fzp' % (s, s)
            add('first_seen(입력별 첫 관측 누적)', j, fzp, None, dict(tag=m.get('tag'), map_from='vsl_v3c3/tools/vsl_vhr.py (vsl_sNN=경로)'))
        else:
            add('vhr_link_integrals(링크별 적분 4꼴)', j, m.get('path'), m.get('file_sha256'), dict(tag=m.get('tag')))
    for j in sorted(glob.glob(vs + '/phys/*.json')):
        m = json.load(open(j, encoding='utf-8'))
        add('fwe_scan(FW_E 체인 100m×60s·차로·램프 60s)', j, m.get('fzp'), m.get('fzp_sha256'), dict(tag=m.get('tag')))
    for j in sorted(glob.glob(vs + '/cell/*.json')):
        m = json.load(open(j, encoding='utf-8'))
        add('vsl_cell(셀 31칸·차로 60s, 체인 6000-8600)', j, m.get('fzp'), m.get('fzp_sha256'), dict(tag=m.get('tag')))
    # rmcause fwe_scan + o1o4 scans
    for j in sorted(glob.glob(SP + '/rmcause/phys/scan/*.json')):
        if FORBID.search(j) or os.path.basename(j).startswith('st1v'):
            continue
        m = json.load(open(j, encoding='utf-8'))
        add('fwe_scan(FW_E 체인 100m×60s·차로·램프 60s)', j, m.get('fzp'), m.get('fzp_sha256'), dict(tag=m.get('tag')))
    for j in sorted(glob.glob(SP + '/rmcause/o1o4/scan/*.json')):
        m = json.load(open(j, encoding='utf-8'))
        if m.get('schema') == 'w264-linkbin/v1':
            add('linkbin(링크×150s 재고·대기·삽입)', j, m.get('fzp'), m.get('fzp_sha256'), dict(tag=m.get('tag')))
        else:
            add('fwe_scan(FW_E 체인 100m×60s·차로·램프 60s)', j, m.get('fzp'), m.get('fzp_sha256'), dict(tag=m.get('tag')))
    for j in sorted(glob.glob(SP + '/c_port/vsl/out/scan/*.json')):
        m = json.load(open(j, encoding='utf-8'))
        add('fwe_scan(FW_E 체인 100m×60s·차로·램프 60s)', j, m.get('fzp'), m.get('fzp_sha256'), dict(tag=m.get('tag')))
    j = SP + '/c_port/vsl/out/first_vsl.json'
    m = json.load(open(j, encoding='utf-8'))
    add('first_seen(입력별 첫 관측 누적)', j, m.get('fzp'), None, dict(tag=m.get('tag')))
    # readback meter scans + cycles
    rb = SP + '/c_port/readback/out'
    for j in sorted(glob.glob(rb + '/scan_*.json')):
        m = json.load(open(j, encoding='utf-8'))
        tag = os.path.basename(j)[5:-5]
        add('rb_meter_scan(미터 헤드 통과·프레임)', j, m.get('fzp'), m.get('sha256'), dict(tag=tag))
        cyc = rb + '/cycles_%s.csv' % tag
        if os.path.exists(cyc):
            add('rb_cycles(미터별 10s 주기 GREEN 초 readback)', cyc, m.get('fzp'), m.get('sha256'), dict(tag=tag, map_from='scan_%s.json fzp' % tag))
    # w1099
    for j in sorted(glob.glob(SP + '/c_port/w1099/out/*.json')):
        b = os.path.basename(j)
        if not re.match(r'^(nc|va|b)\d\d\.json$', b):
            continue
        m = json.load(open(j, encoding='utf-8'))
        add('w1099(FW_W 입구 26·120·129 칸)', j, m.get('path'), None, dict(name=m.get('name')))
    # O4 merge scans (rmcause/o1o4/fzp)
    for j in sorted(glob.glob(SP + '/rmcause/o1o4/fzp/*.json')):
        if j.endswith('_split.json'):
            continue
        m = json.load(open(j, encoding='utf-8'))
        add('o4_merge(10681 등 합류·연결로 재고)', j, m.get('fzp'), m.get('fzp_sha256'), dict(tag=m.get('tag')))
    return C


def decision_info(d):
    if not d or not isinstance(d, str) or not os.path.isdir(d):
        return None
    acts = sorted(glob.glob(d + '/action_*.csv'))
    jsons = sorted(x for x in glob.glob(d + '/action_*.json') if re.search(r'action_\d+\.json$', x))
    man = hashlib.sha256()
    for a in acts:
        man.update(('%s\t%d\t%s\n' % (os.path.basename(a), os.path.getsize(a), sha(a))).encode())
    rbk = d + '/signal_readback.csv'
    vrb = d + '/vsl_readback.csv'
    return dict(dir=d.replace('\\', '/'), n_action_csv=len(acts), action_csv_manifest_sha256=man.hexdigest(),
                n_action_json=len(jsons), action_json_bytes=sum(os.path.getsize(x) for x in jsons),
                signal_readback=finfo(rbk), vsl_readback=finfo(vrb))


def main():
    t0 = time.time()
    caches = cache_index()
    runs = v3c3_runs() + cf_runs()
    out = []
    for r in runs:
        rec = dict(arm=r['arm'], net=r['net'], root=r['root'])
        seed, psha = read_seed(r.get('prov'))
        rec['provenance'] = dict(path=r.get('prov'), sha256=psha, seed=seed)
        fz = r.get('fzp')
        if isinstance(fz, list):
            rec['fzp_error'] = 'multiple: %s' % fz
            fz = None
        fi = finfo(fz, do_sha=False)
        rec['fzp'] = fi
        key = norm(fz) if fz else None
        hits = [c for c in caches if c['fzp_key'] == key] if key else []
        shas = sorted(set(c['fzp_sha256_cached'] for c in hits if c['fzp_sha256_cached']))
        rec['fzp_sha256_cached'] = shas
        rec['fzp_sha256_status'] = ('일치(%d 캐시)' % len([c for c in hits if c['fzp_sha256_cached']])) if len(shas) == 1 else ('없음' if not shas else '불일치')
        rec['caches'] = [dict(kind=c['kind'], file=c['file'], file_sha256=c['file_sha256'], extra=c['extra']) for c in hits]
        for k in ('err', 'inpx', 'readback', 'action'):
            p = r.get(k)
            if isinstance(p, list):
                rec[k] = {'error': 'multiple', 'cands': p}
            else:
                rec[k] = finfo(p)
        rec['decisions'] = decision_info(r.get('dec'))
        ev = os.path.dirname(fz) if fz else None
        if ev and os.path.isdir(ev):
            ldps = sorted(glob.glob(ev + '/*_910[1-8]_001.ldp'))
            rec['meter_ldp'] = [finfo(x) for x in ldps]
        out.append(rec)
    unmatched = [dict(kind=c['kind'], file=c['file'], fzp=c['fzp']) for c in caches
                 if c['fzp_key'] not in set(norm(r['fzp']['path']) for r in out if r.get('fzp'))]
    res = dict(tool='fwe_inventory.py', started_kst=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(t0)),
               elapsed_s=round(time.time() - t0, 1), runs=out, caches_not_matched_to_inventory_runs=unmatched,
               excluded_by_name=FORBID.pattern)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    tmp = OUT + '.tmp'
    json.dump(res, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    os.replace(tmp, OUT)
    print('done', len(out), 'runs', len(caches), 'caches', round(time.time() - t0, 1), 's')


if __name__ == '__main__':
    main()
