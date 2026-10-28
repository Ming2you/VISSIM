p = 'tools/inv_occ.py'
s = open(p, encoding='utf-8').read()
old = """            cnt = [0] * len(S)
            for v in vr['records']:
                lk = str(v['link_no'])
                if lk not in by_link:
                    continue
                ln = int(v['lane_no'])
                p = float(v['position_m'])
                for i in by_link[lk]:
                    s = S[i]
                    if ln in s['lanes'] and s['from_m'] - 1e-9 <= p <= s['to_m'] + 1e-9:
                        cnt[i] += 1
            rows.append((T, cnt))
        res_runs[run] = rows"""
new = """            # lane frame of the same decision (vehicle lengths); sha must match the state's pointer
            fr = st['obs150']['frames']['current']
            fraw = open(os.path.join(d, fr['path']), 'rb').read()
            if hashlib.sha256(fraw).hexdigest() != fr['sha256']:
                raise SystemExit('lane frame sha mismatch ' + fp)
            ftxt = fraw.decode('utf-16') if fraw[:2] in (b'\xff\xfe', b'\xfe\xff') else fraw.decode('utf-8-sig')
            vlen = {int(r[0]): float(r[5]) for r in json.loads(ftxt)['vehicles']}
            cnt = [0] * len(S)
            used = [0.0] * len(S)
            for v in vr['records']:
                lk = str(v['link_no'])
                if lk not in by_link:
                    continue
                ln = int(v['lane_no'])
                p = float(v['position_m'])
                for i in by_link[lk]:
                    s = S[i]
                    if ln in s['lanes'] and s['from_m'] - 1e-9 <= p <= s['to_m'] + 1e-9:
                        cnt[i] += 1
                        used[i] += vlen[int(v['veh_no'])] + GAP
            rows.append((T, cnt))
            lrows.append((T, used))
        res_runs[run] = rows
        len_runs[run] = lrows"""
assert old in s; s = s.replace(old, new, 1)
s = s.replace("""        rows = []
        for fp in files:""", """        rows = []
        lrows = []
        for fp in files:""", 1)
s = s.replace("""    res_runs = {}
    files_meta = {}""", """    res_runs = {}
    len_runs = {}
    files_meta = {}
    GAP = float(sp['all']['gap_pct']['0.5'])""", 1)
# summary per segment: add length-based fill
old = """            per[run] = e
        r['runs'] = per
        seg_out.append(r)"""
new = """            ul = [x[1][i] for x in len_runs[run]]
            if L > 0:
                e['max_fill_len'] = max(ul) / L if ul else 0.0
                e['n_ge_1.0_len'] = sum(1 for x in ul if x / L >= 1.0 - 1e-9)
                e['n_ge_0.9_len'] = sum(1 for x in ul if x / L >= 0.9 - 1e-9)
            per[run] = e
        r['runs'] = per
        seg_out.append(r)"""
assert old in s; s = s.replace(old, new, 1)
# groups: add length based
old = """            per[run] = e
        grp_out[g] = dict("""
new = """            ul = [sum(x[1][i] for i in idx) for x in len_runs[run]]
            Lt = sum(l for l in Ls if l > 0)
            if Lt > 0:
                e['max_fill_len'] = max(ul) / Lt if ul else 0.0
                e['n_ge_1.0_len'] = sum(1 for x in ul if x / Lt >= 1.0 - 1e-9)
            per[run] = e
        grp_out[g] = dict("""
assert old in s; s = s.replace(old, new, 1)
s = s.replace("""               spacing_sha256=hashlib.sha256(open(sp_p, 'rb').read()).hexdigest(), spacings=spac,""",
              """               spacing_sha256=hashlib.sha256(open(sp_p, 'rb').read()).hexdigest(), spacings=spac,
               length_rule=dict(gap_m=GAP, text='fill_len = sum over vehicles in segment of (lane-frame length + FZP median gap) / segment length (added after seeing the scan)'),""")
s = s.replace("""               raw_counts={run: [[T] + c for T, c in rows] for run, rows in res_runs.items()},""",
              """               raw_counts={run: [[T] + c for T, c in rows] for run, rows in res_runs.items()},
               raw_used_m={run: [[T] + [round(x, 3) for x in c] for T, c in rows] for run, rows in len_runs.items()},""")
s = s.replace("""(pre-declared rule) and the FZP mean (added after seeing the scan).""", """(pre-declared rule) and the FZP mean (added after seeing the scan). Also a length rule: sum of the lane-frame
vehicle lengths + FZP median gap over the segment length (added after seeing the scan).""")
open(p, 'w', encoding='utf-8').write(s)
print('ok')
