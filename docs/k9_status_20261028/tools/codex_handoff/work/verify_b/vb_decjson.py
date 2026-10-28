# vb_decjson.py — B 결정 JSON(action_<T>.json, T=900..8850)을 새로 읽어 미터 녹색·rate·VSL·상태 요약 (읽기만)
import json, os, collections, sys
V = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(V, 'out')
R = 'D:/VISSIM_runs/20261026_codex_b_v3c3'
MET = ['RM_C10480', 'RM_C10482', 'RM_C10646', 'RM_C10644', 'RM_C10639', 'RM_C10681', 'RM_C10490', 'RM_C10484']


def find_key(o, key, depth=0, path=''):
    out = []
    if depth > 4:
        return out
    if isinstance(o, dict):
        for k, v in o.items():
            p = path + '/' + str(k)
            if k == key:
                out.append((p, v if not isinstance(v, (dict, list)) else str(v)[:80]))
            out += find_key(v, key, depth + 1, p)
    return out


res = {}
for s in ('31', '41', '43'):
    ddir = f'{R}/s{s}/sdmpc/decisions_sdmpc31_sdmpc9000_s{s}'
    g = {m: collections.Counter() for m in MET}
    rt = {m: collections.Counter() for m in MET}
    vsl = collections.Counter()
    cst = collections.Counter(); sst = collections.Counter()
    fc = []
    arr_keys = set()
    n = 0
    for T in range(900, 8851, 150):
        d = json.load(open(f'{ddir}/action_{T:06d}.json', encoding='utf-8'))
        n += 1
        dg = d.get('diagnostics', {})
        for m in MET:
            g[m][dg.get('rw_meter_green_' + m)] += 1
            rt[m][d.get('ramp_metering', {}).get(m)] += 1
        for k, v in d.get('vsl', {}).items():
            vsl[v] += 1
        md = d.get('metadata', {})
        cst[md.get('controller_status')] += 1
        ss = find_key(d, 'selection_status')
        sst[tuple(sorted(set(str(x[1]) for x in ss)))] += 1
        fc.append(md.get('forecast_ramp_arrival_total_vph'))
        for k in md.keys():
            if 'arrival' in k.lower():
                arr_keys.add(k)
        if T == 900:
            sel_paths = [x[0] for x in ss]
    res['s' + s] = dict(n=n,
                        rm_green={m: dict(sorted((str(k), v) for k, v in g[m].items())) for m in MET},
                        rm_rate={m: dict(sorted((str(k), v) for k, v in rt[m].items())) for m in MET},
                        vsl_values={str(k): v for k, v in vsl.items()},
                        controller_status={str(k): v for k, v in cst.items()},
                        selection_status={str(k): v for k, v in sst.items()}, selection_paths_T900=sel_paths,
                        forecast_min_max=[min(x for x in fc if x is not None), max(x for x in fc if x is not None)],
                        forecast_none=sum(1 for x in fc if x is None), metadata_arrival_keys=sorted(arr_keys))
    print('done', s, flush=True)
json.dump(res, open(os.path.join(OUT, 'decjson.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('ALL_DONE', flush=True)
