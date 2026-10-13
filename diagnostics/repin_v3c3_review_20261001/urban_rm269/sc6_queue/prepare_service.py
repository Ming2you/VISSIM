"""Reuse the existing four-window causal service observer at SC6 south-left."""
import copy
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
read = lambda p: json.loads(p.read_bytes())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def save(name, value):
    path = HERE / name
    assert not path.exists(), path
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf8')


def main():
    assert read(HERE / 'initialization_verification.json')['status'] == 'passed'
    cfg = read(HERE / 'config.json')
    source = ROOT / cfg['urban']['capacity']['head_resource_contract']
    old = read(source)
    doc = copy.deepcopy(old)
    assert doc['schema'] == 'physical-head-resource-join/v10' and '10206' not in doc['resources']
    lane = read(HERE / 'head_lane_support.json')
    network = ROOT / lane['network']['path']
    assert sha(network) == lane['network']['sha256']
    heads = []
    for h in ET.parse(network).findall('./signalHeads/signalHead'):
        link, ln = h.get('lane').split()
        sc, sg = h.get('sg').split()
        if link == '1210018302' and sg == '3':
            heads.append(dict(head_id=h.get('no'), link=link, lane=int(ln), position_m=float(h.get('pos')), sc=sc, sg=sg))
    assert len(heads) == 1 and heads[0]['lane'] == 4 and heads[0]['sc'] == '6'
    name = 'SC6_S_SC12_to_W_SC5'
    doc['schema'] = 'physical-head-resource-join/v11'
    doc['resources']['10206'] = dict(group='1210018302|p2', heads=heads, mode='regular_unique',
        members={name: lane['movements'][name]['expected_spec']}, receiver='SC6_to_SC5', target_link='1220018404',
        green_exposure_windows=4, proof=dict(path=str((HERE / 'head_lane_support.json').relative_to(ROOT)), sha256=sha(HERE / 'head_lane_support.json')))
    doc['scope'] += ' Add proven SC6 south-left10206 only, with existing4 past green exposure windows and unchanged thresholds.'
    save('head_resources.json', doc)
    cfg['urban']['capacity']['head_resource_contract'] = str((HERE / 'head_resources.json').relative_to(ROOT))
    save('service_config.json', cfg)
    core = ROOT / 'evaluation/controllers/head_service_resources.py'
    backup = HERE / 'head_service_resources.before.py.txt'
    assert not backup.exists()
    backup.write_bytes(core.read_bytes())
    save('service_plan.json', dict(status='prepared', candidate='queue plus scoped past-observation service, no new empirical formula',
        observation_only='Replay existing causal observation history through the current cutoff; no future counts used as input.',
        head='SC6_S_SC12_to_W_SC5', min_green_sec=30, min_crossings=5, past_windows=4,
        fit_coefficients=0, adopted=False, max_forecasts=6, new_full_selections=0, native_runs=0,
        evaluation=['2400 same-native hold/selected: queue-only2 plus queue-service2 fixed450 forecasts',
                    '3300 unchanged applied first150: baseline and queue-service2 forecasts'],
        reason='At2400/3300 the left queue is17/18 but split among turns; prior21-24s green windows fail30s single-window exposure, preserving206.53veh/h despite11-12 observed crossings.',
        source_pins={str(p):sha(p) for p in (source, HERE / 'config.json', HERE / 'head_resources.json', HERE / 'service_config.json', backup)},
        success='Improve physically measured service without falsely qualifying overall control gain or hiding arrival shortage.'))
    print(json.dumps(dict(heads=heads, source_sha256=sha(core), config=str(HERE / 'service_config.json'))))


if __name__ == '__main__':
    main()
