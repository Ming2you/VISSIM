"""Identify SC12-to-SC6 source witnesses using the closed five-second cache."""
from collections import Counter, defaultdict
from pathlib import Path
import gzip
import hashlib
import json
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
A = HERE.parent
H = A.parent
ROOT = HERE.parents[4]
PINS = {}


def data(path):
    path = Path(path)
    b = path.read_bytes()
    PINS[str(path)] = hashlib.sha256(b).hexdigest()
    return b


def read(path):
    return json.loads(data(path))


def main():
    assert not (HERE / 'assessment.json').exists()
    done = read(Path('E:/VISSIM_analysis/20261010_gatearrival291/completion.json'))
    network = ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'
    tree = ET.fromstring(data(network))
    sources = {1220013600: ('east', '10239'), 1210012700: ('south', '10244'),
               1220012103: ('west', '10242')}
    for link, (_, connector) in sources.items():
        node = tree.find("./links/link[@no='%s']" % connector)
        assert node.find('fromLinkEndPt').get('lane').split()[0] == str(link)
        assert node.find('toLinkEndPt').get('lane').split()[0] == '1220015100'
    native = {}
    for arm in ('hold', 'city'):
        cache_path = Path(done['arms'][arm]['cache'])
        blob = data(cache_path)
        assert hashlib.sha256(blob).hexdigest() == done['arms'][arm]['cache_sha256']
        cache = json.loads(gzip.decompress(blob))
        assert cache['sample_sec'] == 5
        seen = set()
        history = defaultdict(list)
        witnesses = []
        for frame in cache['frames']:
            time = frame['sec']
            for row in frame['rows']:
                vehicle, link = row[:2]
                if link == 1220015100 and vehicle not in seen:
                    prior = [(t, r) for t, r in history[vehicle] if r[1] in sources]
                    if time > 2400.1 + 1e-6:
                        p = prior[-1] if prior else None
                        typed = bool(p and p[1][7] == sources[p[1][1]][1])
                        witnesses.append(dict(vehicle=vehicle, first_north_time=time,
                            previous_source_time=p[0] if p else None,
                            previous_source=p[1][1] if p else None,
                            source=sources[p[1][1]][0] if p else 'unknown',
                            current_next_connector_confirmed=typed,
                            bracket_seconds=time-p[0] if p else None))
                    seen.add(vehicle)
                history[vehicle].append((time, row))
        assert len({w['vehicle'] for w in witnesses}) == len(witnesses)
        native[arm] = dict(witnesses=witnesses, total=len(witnesses),
            by_source=dict(Counter(w['source'] for w in witnesses)),
            typed_by_source=dict(Counter(w['source'] for w in witnesses if w['current_next_connector_confirmed'])),
            by150=[dict(start=t, counts=dict(Counter(w['source'] for w in witnesses
                if t <= w['first_north_time'] < t+150))) for t in (2400,2550,2700)],
            max_bracket_seconds=max(w['bracket_seconds'] for w in witnesses if w['bracket_seconds'] is not None),
            unresolved_sources=sum(w['source']=='unknown' for w in witnesses),
            first_frame=cache['frames'][0]['sec'], last_frame=cache['frames'][-1]['sec'])
    model = {}
    for arm in ('hold', 'city'):
        r = json.loads(gzip.decompress(data(A/'gate296/forecast2400'/f'{arm}.response.json.gz')))
        totals = Counter()
        by150 = []
        for time in (2400,2550,2700):
            block = Counter()
            for t in r['transfers']:
                if not (time <= t['start_sec'] < time+150 and t['target']=='storage:SC12_to_SC6'
                        and (t['source'] or '').startswith('movement:SC12_')):
                    continue
                side=t['source'].split(':')[1].split('_')[1]
                block[{'E':'east','S':'south','W':'west'}[side]] += t['vehicles']
            totals.update(block)
            by150.append(dict(start=time, counts=dict(block)))
        model[arm] = dict(total=sum(totals.values()), by_source=dict(totals), by150=by150)
    d = lambda rows: {s: rows['city']['by_source'].get(s,0)-rows['hold']['by_source'].get(s,0)
                      for s in ('east','south','west')}
    prior = read(A/'cityresponse290/assessment.json')
    for name in ('sc12w_service/README.md','sc12w_service/typed_support_v3.json',
                 'sc16_supply/README.md','sc16_supply/comparison.json'):
        data(H/name)
    for name in ('diag_c3_r2/U7.md','impl/STAGE3.md'):
        data(H.parent/'upstream_worklog/02_urban_b2'/name)
    data(Path(__file__))
    report = dict(status='complete_cached_source_balance', previous_goal_turn='progress',
        native=native, model=model, native_source_delta=d(native), model_source_delta=d(model),
        native_domain_boundary_delta=prior['native_boundary']['delta'],
        findings=[
            'All newly observed SC12 north-road vehicles have a retained upstream approach witness within10s; source next-link confirmation is recorded independently.',
            'The west-source reduction is much larger than the model predicts. Short fixed-service support, not only SC10 travel timing, remains relevant.',
            'Past SC12W960 and SC16East1677.27 candidates improved their own discharge without changing ramp laws, but were never composed with the source-path/fixed-gate model.',
            'Testing every local repair against the whole-Omega gain sign in isolation is insufficient to judge a coupled set of independently supported physical corrections.'
        ],
        limits=[
            'Five-second cache witnesses are a lower bound, not an exact head crossing census; initial north-road vehicles are excluded.',
            'Native north-road appearances occur after model connector departure, and the final2850s frame is absent. Do not treat by150 differences as exact same-boundary flow errors.',
            'North-road entry is internal to Omega; multiplying this difference by horizon is not a whole-Omega TTT effect.',
            'Extra native freeway admission and unclassified appearances remain separate; same offered demand does not force identical future admission.',
            'No future observed routes/arrivals become predictor inputs.'
        ], new_predictions=0,new_native=0,new_fzp_reads=0,fits=0,production_changes=0,
        goal_complete=False,source_pins=PINS)
    (HERE/'assessment.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:report[k] for k in ('native_source_delta','model_source_delta')},ensure_ascii=False))
    print(json.dumps({a:dict(native=native[a]['by_source'],typed=native[a]['typed_by_source'],
                           model=model[a]['by_source'],max_gap=native[a]['max_bracket_seconds'])
                      for a in ('hold','city')},ensure_ascii=False))


if __name__ == '__main__':
    main()
