r"""Realised flow per commanded green level -- the test of "partial closure is fictional".

If the meter can only express {closed, open}, then intervals commanded to a low green
will pass far more than the green->flow table says, and the excess will grow as the
commanded green falls. If instead the actuation tracks the command, measured/commanded
stays near a constant across green levels.

Pools the three seeds; each (meter, green) cell aggregates its intervals.
"""
import io
import json
from collections import defaultdict

SRC = r'D:\VISSIM-merge\evidence\meter_realised.json'


def main():
    data = json.load(io.open(SRC, encoding='utf-8'))
    cells = defaultdict(list)
    for arm, meters in data.items():
        for name, row in meters.items():
            for item in row['by_interval']:
                cells[(name, item['green'])].append((item['commanded_vph'], item['measured_vph']))

    names = sorted({n for n, _ in cells})
    greens = sorted({g for _, g in cells}, key=lambda g: (g is None, g))
    print('realised / commanded, pooled over 3 seeds   (n = intervals in the cell)\n')
    header = '%-12s' % 'meter'
    for g in greens:
        header += '%12s' % ('g=%s' % g)
    print(header)
    for name in names:
        line = '%-12s' % name
        for g in greens:
            rows = cells.get((name, g))
            if not rows:
                line += '%12s' % '-'
                continue
            cmd = sum(c for c, _ in rows) / len(rows)
            got = sum(m for _, m in rows) / len(rows)
            line += '%12s' % ('%.2f(%d)' % ((got / cmd) if cmd else float('nan'), len(rows)))
        print(line)

    print('\nabsolute veh/h, pooled   commanded -> measured')
    for name in names:
        parts = []
        for g in greens:
            rows = cells.get((name, g))
            if not rows:
                continue
            cmd = sum(c for c, _ in rows) / len(rows)
            got = sum(m for _, m in rows) / len(rows)
            parts.append('g%s %.0f->%.0f' % (g, cmd, got))
        print('  %-12s %s' % (name, '  |  '.join(parts)))

    print('\nRising ratios as green falls = the command is not being realised.')
    print('Flat ratios = actuation tracks the command and the problem is elsewhere.')


if __name__ == '__main__':
    main()
