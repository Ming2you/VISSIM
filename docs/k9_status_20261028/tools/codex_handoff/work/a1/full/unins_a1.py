# unins_a1.py - A1 copy of vhr_unins.py (fc233013...): same S_int / dU first-observation difference, A1 pairs added.
# If two runs share the same arrival stream A(t) (same network, seed, demand), then
#   U_a(t) - U_b(t) = I_b(t) - I_a(t),  so  dU = sum_b (W - t_first) - sum_a (W - t_first)  over first-seen <= W.
# usage: python -B unins_a1.py [--smoke]     (--smoke: 'a1' = codex joint, read from firstseen_smoke)
import json, re, sys

SMOKE = '--smoke' in sys.argv
W0 = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work'
S_OLD = W0 + '/vhr/scan_out'                                            # VH first-seen outputs (joint, nc_raw), read only
S_NEW = W0 + '/a1/full/' + ('firstseen_smoke' if SMOKE else 'firstseen')  # a1, lnc
F = {t: json.load(open(f'{S_OLD}/first_{t}.json')) for t in ['joint', 'nc_raw']}
F.update({t: json.load(open(f'{S_NEW}/first_{t}.json')) for t in ['a1', 'lnc']})
A1RUN = 'D:/VISSIM_handoff/20261024/raw/joint/sdmpc' if SMOKE else 'D:/VISSIM_runs/20261025_codex_a1_s29/sdmpc'
NATIVE = {}
for c, p in [('joint', 'D:/VISSIM_handoff/20261024/raw/joint/sdmpc/native_network_performance.json'),
             ('nc', 'D:/VISSIM_handoff/20261024/raw/nc/native_network_performance.json'),
             ('a1', A1RUN + '/native_network_performance.json')]:
    d = json.load(open(p)); NATIVE[c] = dict(to=d['to_sec'], delay_latent_veh_h=d['native']['DelayLatent'] / 3600, demand_latent=d['native']['DemandLatent'],
                                            veh_arr=d['native'].get('VehArr'), veh_act=d['native'].get('VehAct'), sha_path=p)
REMAIN = {}
for c, p in [('a1', A1RUN + '/vissim_simulation_001.err'), ('joint', 'D:/VISSIM_handoff/20261024/raw/joint/sdmpc/vissim_simulation_001.err')]:
    REMAIN[c] = {}
    for line in open(p, encoding='latin-1'):
        m = re.search(r'Vehicle input (\d+):.*remain: (\d+) vehicles', line)
        if m:
            REMAIN[c][m.group(1)] = int(m.group(2))


def S_int(tag, W, cat=None):
    tot = 0.0; n = 0
    for c, d in F[tag]['by_cat'].items():
        if cat is not None and c not in cat:
            continue
        for tt, k in d.items():
            t = int(tt) / 10
            if t <= W:
                tot += k * (W - t); n += k
    return tot / 3600, n


def dU(a, b, W, cat=None):  # U_a - U_b
    return S_int(b, W, cat)[0] - S_int(a, W, cat)[0]


R = {'smoke': SMOKE, 'native': NATIVE, 'remain_err': REMAIN}
R['inserted_by_8100'] = {t: S_int(t, 8100)[1] for t in F}
R['inserted_by_8100_link26'] = {t: S_int(t, 8100, {'26'})[1] for t in F}
R['inserted_by_8100_link74'] = {t: S_int(t, 8100, {'74'})[1] for t in F}
R['inserted_by_8100_other'] = {t: S_int(t, 8100, {'other'})[1] for t in F}
R['A1099_8100'] = {c: R['inserted_by_8100_link26'][c] + REMAIN[c].get('1099', 0) for c in ('a1', 'joint')}
R['lnc_equals_nc_raw_firstseen'] = F['lnc']['by_cat'] == F['nc_raw']['by_cat']
for a, b in [('a1', 'lnc'), ('joint', 'nc_raw'), ('a1', 'joint')]:
    R[f'{a}-{b}'] = dict(total=dU(a, b, 8100), l1098_link74=dU(a, b, 8100, {'74'}), l1099_link26=dU(a, b, 8100, {'26'}), other=dU(a, b, 8100, {'other'}))
R['validate_a1-joint'] = dict(first_seen=R['a1-joint']['total'], native=NATIVE['a1']['delay_latent_veh_h'] - NATIVE['joint']['delay_latent_veh_h'])
R['nc_U_0_8100_pathC_from_joint'] = NATIVE['joint']['delay_latent_veh_h'] - R['joint-nc_raw']['total']
R['nc_U_0_8100_pathC_from_a1'] = NATIVE['a1']['delay_latent_veh_h'] - R['a1-lnc']['total']
R['first_link_top'] = {t: F[t]['first_link_top'][:6] for t in F}
R['vehicles'] = {t: F[t]['vehicles'] for t in F}
json.dump(R, open(W0 + '/a1/full/unins_a1' + ('_smoke' if SMOKE else '') + '.json', 'w'), indent=1)
print(json.dumps({k: R[k] for k in ('inserted_by_8100_link74', 'A1099_8100', 'lnc_equals_nc_raw_firstseen', 'a1-lnc', 'joint-nc_raw', 'a1-joint', 'validate_a1-joint')}, indent=0))
