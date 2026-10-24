"""Verify cached cohort joins and aggregates independently of audit.py."""
from collections import Counter, defaultdict
import csv
from pathlib import Path

from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE = Path(__file__).resolve().parent


def main():
    pins = h.read(HERE / 'input_pins.json')
    protocol = h.read(HERE / 'protocol.json')
    rows = h.read(HERE / 'observations.json.gz')
    groups = h.read(HERE / 'cohort_groups.json')
    passages = h.read(HERE / 'passages.json')
    assert all(h.sha(Path(p)) == sha for p, sha in pins.items())
    paths = [Path(p) for p in pins]
    histories = {}
    for case in {r['case'] for r in rows}:
        seed, arm = case.split('_', 1)
        p = next(p for p in paths if p.name == 'port_events.csv'
                 and p.parent.name == arm
                 and ('heldout67' in str(p)) == (seed == '67'))
        history = defaultdict(list)
        with p.open(encoding='utf-8-sig', newline='') as stream:
            for e in csv.DictReader(stream):
                if e['kind'] == 'departure' and e['connector'] in ('10639', '10681', '10490', '10484'):
                    history[e['vehicle']].append((float(e['time_s']), e['connector']))
        histories[case] = history
    observed = defaultdict(list)
    ids = set()
    for r in rows:
        key = (r['case'], r['time'], r['id'])
        assert key not in ids
        ids.add(key)
        past = [e for e in histories[r['case']][r['id']] if e[0] <= r['time']]
        origin = max(past)[1] if past else None
        assert r['cohort'] == ('10490' if origin == '10490' else 'other')
        block = round((r['time'] - 2670.1) / 5) // 30
        observed[r['case'], block, r['cell'], r['lane'], r['cohort']].append(r)
        assert r['slow'] == (r['speed'] < 5)
        assert r['next_region'] == (r['next_seen'] and r['next_cell'] in (21, 22))
    assert len(groups) == 6 * 3 * 2 * 3 * 2
    for g in groups:
        rr = observed[g['case'], g['block'], g['cell'], g['lane'], g['cohort']]
        n = len(rr)
        assert g.get('samples', 0) == n
        assert abs(g['mean_n'] - n / 30) < 1e-12
        assert g['sampled_residence_s'] == 5 * n
        assert abs(g['mean_slow'] - sum(r['slow'] for r in rr) / 30) < 1e-12
        if n:
            assert abs(g['vehicle_sample_mean_speed'] - sum(r['speed'] for r in rr) / n) < 1e-10
        assert g.get('lane_changed_any_followed', 0) == sum(
            r['next_seen'] and r['lane'] != r['next_lane'] for r in rr)
        assert g.get('lane_changed_region_survivors', 0) == sum(
            r['next_region'] and r['lane'] != r['next_lane'] for r in rr)
    counts = Counter()
    for p in passages:
        assert p['entry_lower'] <= p['entry_upper']
        assert p['entry_upper'] - p['entry_lower'] <= 5.000001
        assert all(p['entry_upper'] <= r[0] <= 3120.1 and r[1] in (21, 22) for r in p['samples'])
        assert p['lane1_sampled_seconds'] == 5 * sum(r[2] == 1 for r in p['samples'])
        assert p['outcome'] not in ('unexpected_upstream_position', 'unobserved_after_merge')
        counts[p['case'], p['outcome']] += 1
    for item in h.read(HERE / 'passage_summary.json'):
        actual = {k[1]: n for k, n in counts.items() if k[0] == item['case']}
        assert item['outcomes'] == actual and item['merges'] == sum(actual.values())
    flows = h.read(HERE / 'source_checks.json')
    assert len(flows) == 18 and all(r['merge_events'] == r['native_flow_merges'] for r in flows)
    core = protocol['source_sha256']
    assert all(h.sha(h.ROOT / p) == sha for p, sha in core.items())
    assert h.sha(protocol['STOP']['path']) == protocol['STOP']['sha256']
    result = dict(status='PASS', historical_event_joins=len(rows), aggregate_checks=len(groups),
                  passage_checks=len(passages), native_flow_totals=len(flows),
                  input_hashes=len(pins), core_preserved=len(core), STOP_preserved=True,
                  limitation='Independent joins/aggregation verification; not a new microscopic observation or causal model validation.')
    h.save(HERE / 'verification.json', result)
    print(result)


if __name__ == '__main__':
    main()
