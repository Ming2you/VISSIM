r"""Did the ramp meters ever actually restrict, and by how much?

The paired seed sweep says RM moved Omega TTT by +-300..400 veh*h with a random sign.
Before blaming actuation, establish what was COMMANDED: if green_sec is pinned at 10
(wide open) for every meter at every interval, the meters never metered and the TTT
swings come from somewhere else entirely.

Reads each rm arm's decision_<sec>.json:
  meters[name].green_sec          what this interval commands
  meters[name].raw_request_vph    what the rule wanted before bounding
  meters[name].bounded_request_vph what the green->flow table can express
"""
import io
import json
import os
import re
from collections import Counter, defaultdict

BASE = r'D:\VISSIM_runs\20260922_seedvar'
POLICY = r'D:\VISSIM_runs\20260922_fw080_urban090_controls\rules\prepared_rm\rule_policy.json'
ARMS = ('s31_rm', 's37_rm', 's41_rm')


def main():
    policy = json.load(io.open(POLICY, encoding='utf-8-sig'))
    tables = {k: {int(g): v for g, v in m['table'].items()} for k, m in policy['meters'].items()}
    print('control_start_sec = %s   minimum_green = %s   max_green_change = %s\n'
          % (policy['rule']['control_start_sec'], policy['minimum_green'], policy['max_green_change']))

    summary = {}
    for arm in ARMS:
        run = os.path.join(BASE, arm, 'run')
        files = sorted((int(re.search(r'decision_(\d+)\.json', f).group(1)), f)
                       for f in os.listdir(run) if re.match(r'decision_\d+\.json$', f))
        greens = defaultdict(Counter)
        clipped = Counter()
        raw_over = defaultdict(list)
        for sec, fname in files:
            doc = json.load(io.open(os.path.join(run, fname), encoding='utf-8-sig'))
            for name, row in doc.get('meters', {}).items():
                g = row.get('green_sec')
                greens[name][g] += 1
                raw, bounded = row.get('raw_request_vph'), row.get('bounded_request_vph')
                if raw is not None and bounded is not None:
                    if raw > bounded + 1e-6:
                        clipped[name] += 1
                    raw_over[name].append(raw / bounded if bounded else float('inf'))
        summary[arm] = {'intervals': len(files), 'first_sec': files[0][0], 'last_sec': files[-1][0],
                        'greens': {k: dict(v) for k, v in greens.items()},
                        'clipped_at_ceiling': dict(clipped)}
        print('=== %s   %d intervals, %d..%d s' % (arm, len(files), files[0][0], files[-1][0]))
        print('%-12s %-34s %10s %10s' % ('meter', 'green_sec distribution', 'restricted', 'raw/bound'))
        for name in sorted(greens):
            dist = greens[name]
            total = sum(dist.values())
            restricted = total - dist.get(10, 0)
            ratios = [r for r in raw_over[name] if r != float('inf')]
            mean_ratio = sum(ratios) / len(ratios) if ratios else float('nan')
            shown = ', '.join('%s:%d' % (g, n) for g, n in sorted(dist.items(), key=lambda x: (x[0] is None, x[0])))
            print('%-12s %-34s %6d/%-4d %9.2fx' % (name, shown, restricted, total, mean_ratio))
        print()

    io.open(r'D:\VISSIM-merge\evidence\meter_commands.json', 'w', encoding='utf-8').write(
        json.dumps(summary, ensure_ascii=False, indent=2))
    print('-> D:\\VISSIM-merge\\evidence\\meter_commands.json')
    print('\nA meter that is 10 in every interval never metered. "restricted" counts the')
    print('intervals whose commanded green was anything other than fully open, and')
    print('"raw/bound" is how far the rule\'s own request exceeded what the table can express.')


if __name__ == '__main__':
    main()
