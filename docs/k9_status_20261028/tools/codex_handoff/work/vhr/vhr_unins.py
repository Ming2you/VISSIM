# vhr_unins.py - arm-to-arm uninserted-wait differences from first-seen counts (fresh method, no arrival-curve model).
# If two runs share the same arrival stream A(t) (same network, seed, demand), then
#   U_a(t) - U_b(t) = I_b(t) - I_a(t),  so  dU = sum_b (W - t_first) - sum_a (W - t_first)  over first-seen <= W.
# Checked against VISSIM native DelayLatent where both arms have it (joint/window/off, 0-8100).
import json, re

S = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work/vhr/scan_out'
F = {t: json.load(open(f'{S}/first_{t}.json')) for t in ['joint', 'nc_raw', 'window', 'off', 'va_s31', 'nc3_s31', 'j1_s31']}
NATIVE = {}
for c in ['joint', 'window', 'off', 'nc']:
    p = f'D:/VISSIM_handoff/20261024/raw/{c}/sdmpc/native_network_performance.json' if c != 'nc' else 'D:/VISSIM_handoff/20261024/raw/nc/native_network_performance.json'
    d = json.load(open(p)); NATIVE[c] = dict(to=d['to_sec'], delay_latent_veh_h=d['native']['DelayLatent'] / 3600, demand_latent=d['native']['DemandLatent'])


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


R = {'native': NATIVE}
R['inserted_by_8100'] = {t: S_int(t, 8100)[1] for t in F}
R['inserted_by_8100_link26'] = {t: S_int(t, 8100, {'26'})[1] for t in F}
R['inserted_by_8100_link74'] = {t: S_int(t, 8100, {'74'})[1] for t in F}
R['inserted_by_9000'] = {t: S_int(t, 9000)[1] for t in F}
# validation against native (codex arms)
R['validate'] = {f'{a}-joint': dict(first_seen=dU(a, 'joint', 8100), native=NATIVE[a]['delay_latent_veh_h'] - NATIVE['joint']['delay_latent_veh_h']) for a in ['window', 'off']}
# joint - NC (0-8100), totals and by first link
R['joint-nc'] = dict(total=dU('joint', 'nc_raw', 8100), l1098_link74=dU('joint', 'nc_raw', 8100, {'74'}), l1099_link26=dU('joint', 'nc_raw', 8100, {'26'}),
                     other=dU('joint', 'nc_raw', 8100, {'other'}))
R['nc_U_0_8100_pathC'] = NATIVE['joint']['delay_latent_veh_h'] - R['joint-nc']['total']
# 1099 arrivals at 8100: joint inserted(link26) + joint remain 10217 (.err)
R['A1099_8100_joint'] = R['inserted_by_8100_link26']['joint'] + 10217
# v3c3 pairs (codex window [0,W])
for a, b in [('va_s31', 'nc3_s31'), ('j1_s31', 'nc3_s31'), ('va_s31', 'j1_s31')]:
    for W in (8100, 9000):
        R[f'{a}-{b}|{W}'] = dict(total=dU(a, b, W), l74=dU(a, b, W, {'74'}), l26=dU(a, b, W, {'26'}), other=dU(a, b, W, {'other'}))
R['first_link_top'] = {t: F[t]['first_link_top'][:6] for t in F}
R['vehicles'] = {t: F[t]['vehicles'] for t in F}
json.dump(R, open(f'{S}/../unins_out.json', 'w'), indent=1)
print(json.dumps(R, indent=0)[:5000])
