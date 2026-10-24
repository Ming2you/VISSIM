r"""How much flow did metering actually remove, measured against the same seed's none arm.

The first attempt compared measured flow to the commanded table value, but for the
four never-restricted meters the "commanded" number is the table CEILING, not the ramp
demand, so a low ratio there could be sampling loss or simply a quiet ramp -- the design
could not separate them.

This compares the SAME meter between the rm and none arms of the SAME seed. Both arms
share the pre-900 state, the demand and the 5 s sampling grid, so the sampling loss
cancels and what remains is what metering did. A meter commanded wide open in every
interval must show no difference; if it does, something other than the command moved it.
"""
import io
import json
import os
import sys
from collections import Counter

BASE = r'D:\VISSIM_runs\20260922_seedvar'
POLICY = r'D:\VISSIM_runs\20260922_fw080_urban090_controls\rules\prepared_rm\rule_policy.json'
INTERVAL = 150.0
CONTROL_START = 900.0


def entries(arm, links):
    base = os.path.join(BASE, arm, 'run', 'vissim_eval')
    path = os.path.join(base, [f for f in os.listdir(base) if f.endswith('.fzp')][0])
    where, counts = {}, Counter()
    frame_t, seen = None, {}
    with io.open(path, 'rb') as stream:
        for raw in stream:
            if not raw[:1].isdigit():
                continue
            parts = raw.split(b';', 3)
            t = float(parts[0]); veh = int(parts[1]); link = int(parts[2])
            if t != frame_t:
                for v in list(where):
                    if v not in seen:
                        del where[v]
                seen, frame_t = {}, t
            seen[veh] = True
            if link in links and where.get(veh) != link:
                counts[(link, int(t // INTERVAL) * int(INTERVAL))] += 1
            where[veh] = link
    return counts


def main():
    seeds = sys.argv[1:] or ['s31', 's37', 's41']
    policy = json.load(io.open(POLICY, encoding='utf-8-sig'))
    link_of = {m['connector']: name for name, m in policy['meters'].items()}
    links = set(link_of)

    out = {}
    for seed in seeds:
        none_c = entries(seed + '_none', links)
        rm_c = entries(seed + '_rm', links)
        run = os.path.join(BASE, seed + '_rm', 'run')
        restricted = Counter()
        for fname in os.listdir(run):
            if not fname.startswith('decision_') or not fname.endswith('.json'):
                continue
            doc = json.load(io.open(os.path.join(run, fname), encoding='utf-8-sig'))
            for name, row in doc.get('meters', {}).items():
                if row.get('green_sec') != 10:
                    restricted[name] += 1

        print('=== seed %s   (control from %d s)' % (seed, CONTROL_START))
        print('%-12s %8s %12s %12s %12s %9s' %
              ('meter', 'restr.', 'none veh/h', 'rm veh/h', 'delta', 'rm/none'))
        rows = {}
        for link, name in sorted(link_of.items(), key=lambda kv: kv[1]):
            secs = sorted({s for (l, s) in list(none_c) + list(rm_c) if l == link and s >= CONTROL_START})
            if not secs:
                continue
            a = sum(none_c.get((link, s), 0) for s in secs) * 3600.0 / (INTERVAL * len(secs))
            b = sum(rm_c.get((link, s), 0) for s in secs) * 3600.0 / (INTERVAL * len(secs))
            rows[name] = {'none_vph': a, 'rm_vph': b, 'delta_vph': b - a,
                          'ratio': (b / a) if a else None,
                          'restricted_intervals': restricted.get(name, 0), 'intervals': len(secs)}
            print('%-12s %5d/%-3d %12.1f %12.1f %+12.1f %9s' %
                  (name, restricted.get(name, 0), len(secs), a, b, b - a,
                   ('%.2f' % (b / a)) if a else 'n/a'))
        out[seed] = rows
        print()

    dest = r'D:\VISSIM-merge\evidence\meter_rm_vs_none.json'
    io.open(dest, 'w', encoding='utf-8').write(json.dumps(out, ensure_ascii=False, indent=2))
    print('-> ' + dest)
    print('\nA meter with restr.=0 should show rm/none ~ 1.00. Anything else there is not')
    print('metering -- it is the network reacting to the meters that DID restrict.')


if __name__ == '__main__':
    main()
