r"""Commanded meter flow versus what actually crossed the connector.

The seed sweep showed RM moving Omega TTT by +-300..400 veh*h with a random sign,
and the command audit showed four of eight meters pinned wide open. This asks the
remaining question for the four that DO restrict: does the commanded green->flow
table value match the flow that actually passed?

METHOD. One FZP pass per arm. A vehicle is counted as an ENTRY to a connector in the
frame where it first appears on that link, so each vehicle is counted once regardless
of how long it sits there. Entries are binned into the 150 s control intervals and
converted to veh/h.

KNOWN BIAS. The FZP samples every 5 s, so a vehicle that crosses a short connector in
under 5 s can be missed entirely. That biases measured flow DOWN, and it biases the
wide-open meters most (they are the fast ones). The four never-restricted meters are
therefore the control: their commanded value is the table ceiling, so measured/commanded
there estimates the sampling loss, and the restricted meters' ratios should be read
against that, not against 1.0.
"""
import io
import json
import os
import re
import sys
from collections import Counter, defaultdict

BASE = r'D:\VISSIM_runs\20260922_seedvar'
POLICY = r'D:\VISSIM_runs\20260922_fw080_urban090_controls\rules\prepared_rm\rule_policy.json'
INTERVAL = 150.0


def commands(arm, meters):
    """{(meter, interval_start_sec): commanded_vph} from the decision receipts."""
    run = os.path.join(BASE, arm, 'run')
    out = {}
    for fname in os.listdir(run):
        m = re.match(r'decision_(\d+)\.json$', fname)
        if not m:
            continue
        sec = int(m.group(1))
        doc = json.load(io.open(os.path.join(run, fname), encoding='utf-8-sig'))
        for name, row in doc.get('meters', {}).items():
            g = row.get('green_sec')
            table = meters[name]['table']
            vph = table.get(str(g), table.get(str(int(g)) if g is not None else None))
            out[(name, sec)] = (g, vph)
    return out


def entries(arm, links):
    """{(link, interval_start_sec): entry count} -- first frame a vehicle appears on the link."""
    base = os.path.join(BASE, arm, 'run', 'vissim_eval')
    path = os.path.join(base, [f for f in os.listdir(base) if f.endswith('.fzp')][0])
    where = {}
    counts = Counter()
    frame_t = None
    seen_this_frame = {}
    with io.open(path, 'rb') as stream:
        for raw in stream:
            if not raw[:1].isdigit():
                continue
            parts = raw.split(b';', 3)
            t = float(parts[0])
            veh = int(parts[1])
            link = int(parts[2])
            if t != frame_t:
                # vehicles absent from the new frame leave; forget them
                for v in list(where):
                    if v not in seen_this_frame:
                        del where[v]
                seen_this_frame = {}
                frame_t = t
            seen_this_frame[veh] = True
            previous = where.get(veh)
            if link in links and previous != link:
                counts[(link, int(t // INTERVAL) * int(INTERVAL))] += 1
            where[veh] = link
    return counts, path


def main():
    arms = sys.argv[1:] or ['s31_rm', 's37_rm', 's41_rm']
    policy = json.load(io.open(POLICY, encoding='utf-8-sig'))
    meters = policy['meters']
    link_of = {m['connector']: name for name, m in meters.items()}
    links = set(link_of)

    report = {}
    for arm in arms:
        cmd = commands(arm, meters)
        counted, path = entries(arm, links)
        print('=== %s   (%s)' % (arm, os.path.basename(path)))
        print('%-12s %8s %10s %12s %12s %8s' %
              ('meter', 'restr.', 'mean green', 'commanded', 'measured', 'meas/cmd'))
        rows = {}
        for link, name in sorted(link_of.items(), key=lambda kv: kv[1]):
            pairs = []
            for (mname, sec), (g, vph) in cmd.items():
                if mname != name or vph is None:
                    continue
                got = counted.get((link, sec), 0) * 3600.0 / INTERVAL
                pairs.append((sec, g, vph, got))
            if not pairs:
                continue
            restricted = sum(1 for _, g, _, _ in pairs if g != 10)
            mean_g = sum(g for _, g, _, _ in pairs) / len(pairs)
            mean_cmd = sum(v for _, _, v, _ in pairs) / len(pairs)
            mean_got = sum(x for _, _, _, x in pairs) / len(pairs)
            rows[name] = {'intervals': len(pairs), 'restricted': restricted,
                          'mean_green_sec': mean_g, 'mean_commanded_vph': mean_cmd,
                          'mean_measured_vph': mean_got,
                          'ratio': (mean_got / mean_cmd) if mean_cmd else None,
                          'by_interval': [{'sec': s, 'green': g, 'commanded_vph': v,
                                           'measured_vph': x} for s, g, v, x in sorted(pairs)]}
            print('%-12s %5d/%-3d %10.1f %12.1f %12.1f %8.2f' %
                  (name, restricted, len(pairs), mean_g, mean_cmd, mean_got,
                   mean_got / mean_cmd if mean_cmd else float('nan')))
        report[arm] = rows
        print()

    dest = r'D:\VISSIM-merge\evidence\meter_realised.json'
    io.open(dest, 'w', encoding='utf-8').write(json.dumps(report, ensure_ascii=False, indent=2))
    print('-> ' + dest)


if __name__ == '__main__':
    main()
