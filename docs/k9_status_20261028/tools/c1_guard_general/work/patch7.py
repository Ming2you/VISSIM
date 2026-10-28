p = 'tools/inv_build.py'
s = open(p, encoding='utf-8').read()
old = """    spacing_fzp = None
    if sp_p != '-':
        sp = jl(sp_p)
        spacing_fzp = sp['recommended_spacing_m']"""
new = """    spacing_fzp = None
    spacing_fzp_mean = None
    if sp_p != '-':
        sp = jl(sp_p)
        spacing_fzp = sp['recommended_spacing_m']
        spacing_fzp_mean = sp['all']['mean_d_m']   # added after seeing the scan (data after)"""
assert old in s; s = s.replace(old, new, 1)
old = """        if spacing_fzp:
            r['veh_per_lane_fzp'] = length_m / spacing_fzp
        return r"""
new = """        if spacing_fzp:
            r['veh_per_lane_fzp'] = length_m / spacing_fzp
        if spacing_fzp_mean:
            r['veh_per_lane_fzp_mean'] = length_m / spacing_fzp_mean
        return r"""
assert old in s; s = s.replace(old, new, 1)
s = s.replace("res = dict(tool='inv_build.py', spacing_6m=s6, spacing_fzp=spacing_fzp,", "res = dict(tool='inv_build.py', spacing_6m=s6, spacing_fzp=spacing_fzp, spacing_fzp_mean=spacing_fzp_mean,")
open(p, 'w', encoding='utf-8').write(s)

p = 'tools/inv_occ.py'
s = open(p, encoding='utf-8').read()
old = """Usage: python -B inv_occ.py <inventory.json> <spacing_m_fzp> <out.json>"""
new = """Usage: python -B inv_occ.py <inventory.json> <spacing.json> <out.json>"""
assert old in s; s = s.replace(old, new, 1)
s = s.replace("""per lane; link-level fill = vehicles on all listed lanes / sum of lane capacities. Spacings: 6.0 m and the FZP value.""",
              """per lane; link-level fill = vehicles on all listed lanes / sum of lane capacities. Spacings: 6.0 m, the FZP median
(pre-declared rule) and the FZP mean (added after seeing the scan).""")
old = """    inv_p, sp_fzp, out = sys.argv[1], float(sys.argv[2]), sys.argv[3]
    inv = json.loads(open(inv_p, 'rb').read().decode('utf-8'))
    S = segments(inv)
    spac = {'6m': 6.0, 'fzp': sp_fzp}"""
new = """    inv_p, sp_p, out = sys.argv[1], sys.argv[2], sys.argv[3]
    inv = json.loads(open(inv_p, 'rb').read().decode('utf-8'))
    sp = json.loads(open(sp_p, 'rb').read().decode('utf-8'))
    S = segments(inv)
    spac = {'6m': 6.0, 'fzp': float(sp['recommended_spacing_m']), 'fzp_mean': float(sp['all']['mean_d_m'])}"""
assert old in s; s = s.replace(old, new, 1)
s = s.replace("""    res = dict(tool='inv_occ.py', inventory_sha256=hashlib.sha256(open(inv_p, 'rb').read()).hexdigest(), spacings=spac,""",
              """    res = dict(tool='inv_occ.py', inventory_sha256=hashlib.sha256(open(inv_p, 'rb').read()).hexdigest(),
               spacing_sha256=hashlib.sha256(open(sp_p, 'rb').read()).hexdigest(), spacings=spac,""")
open(p, 'w', encoding='utf-8').write(s)
print('ok')
