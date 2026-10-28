# Item 10: does the original evaluator's partition code reproduce the 8.09 % split?
# (a) exact partition loop copied from analysis/original_scripts/solo355_compare_20261014.py:49-67 (render), run on the cached
#     analysis/comparison/{arm}/area_metrics.json -> compare with summary.json reporting_partition.parts
# (b) cached per-link residence vs our own FZP per-link residence (link level)
import json, hashlib
B = "D:/VISSIM_handoff/20261024"
src = open(f"{B}/analysis/original_scripts/solo355_compare_20261014.py", encoding="utf-8").read().splitlines()
print("lines 49-67 of the original script used verbatim (logic):")
for i in range(48, 67): print(f"  {i+1}: {src[i]}")
geo = json.load(open(f"{B}/code/diagnostics/sdmpc_n31_20260924/integration_20260926/selected/port_gain/geometry.json", encoding="utf-8"))
on = {str(b['connector']): b['road'] for b in geo['boundaries'] if b['kind'] == 'ramp'}
off = {str(b['connector']) for b in geo['boundaries'] if b['kind'] == 'offramp'}
chain = {str(b['link']): r for r, rows in geo['chains'].items() for b in rows}
assert len(on) == 8 and not set(on) & off and not set(on) & set(chain)
summ = json.load(open(f"{B}/analysis/comparison/summary.json", encoding="utf-8"))
cached_parts = summ["reporting_partition"]["parts"]
own = json.load(open("scan/../metrics_out.json"))
parts = {}
maxd = 0.0; linkd = {}
for arm in ["nc", "joint", "freeway_only", "urban_only"]:
    metrics = json.load(open(f"{B}/analysis/comparison/{arm}/area_metrics.json", encoding="utf-8"))
    part = {k: 0. for k in ('FW_E','FW_W','onramps_E','onramps_W','urban_roads','offramps','outside')}
    for link, row in metrics['physical_link_residence'].items():
        group = 'outside' if not row['inside'] else chain.get(link)
        if group is None:
            group = ('onramps_E' if on[link]=='FW_E' else 'onramps_W') if link in on else 'offramps' if link in off else 'urban_roads'
        part[group] += row['ttt_veh_h']
    part.update(urban=part['urban_roads']+part['offramps'], east_with_onramps=part['FW_E']+part['onramps_E'],
                west_with_onramps=part['FW_W']+part['onramps_W'])
    part['freeway'] = part['east_with_onramps']+part['west_with_onramps']
    part['omega'] = part['freeway']+part['urban']
    assert abs(part['omega']-metrics['ttt_veh_h']) < 1e-7
    parts[arm] = part
    for k, v in part.items():
        maxd = max(maxd, abs(v - cached_parts[arm][k]))
    # link level vs own scan
    mine = json.load(open(f"scan/{arm}.json"))["link_residence_veh_h"]
    d = [abs(row['ttt_veh_h'] - mine.get(l, 0.0)) for l, row in metrics['physical_link_residence'].items()]
    extra = set(mine) - set(metrics['physical_link_residence'])
    linkd[arm] = (len(d), max(d), len(extra), sum(mine[l] for l in extra))
print("max |re-run partition - cached summary parts| =", maxd)
print("link-level cached vs own FZP scan (links, max abs diff veh.h, own-only links, their residence):", linkd)
for arm in ["joint", "freeway_only", "urban_only"]:
    p, n = parts[arm], parts["nc"]
    print(arm, "urban_roads %.6f -> %.6f : %.6f %%" % (n['urban_roads'], p['urban_roads'], 100 * (1 - p['urban_roads'] / n['urban_roads'])))
print("sha256 solo355_compare:", hashlib.sha256(open(f"{B}/analysis/original_scripts/solo355_compare_20261014.py", 'rb').read()).hexdigest())
print("sha256 analyze.py:", hashlib.sha256(open(f"{B}/analysis/original_scripts/analyze.py", 'rb').read()).hexdigest())
