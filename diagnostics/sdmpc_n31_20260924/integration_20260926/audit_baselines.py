"""Read-only comparison of local gain data, upstream v2, and upstream v3b.

Only writes the small audit receipt next to this script. No native launch.
"""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
LOCAL = ROOT.parent / 'sd31'
N31 = Path('diagnostics/sdmpc_n31_20260924')


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def flatten(element, prefix=''):
    """Preserve child order where there is no explicit VISSIM object number."""
    name = element.tag + (f"[{element.get('no')}]" if 'no' in element.attrib else '')
    path = prefix + '/' + name
    out = {path + '/@' + k: v for k, v in element.attrib.items()}
    if element.text and element.text.strip():
        out[path + '/text()'] = element.text.strip()
    seen = Counter()
    for child in element:
        seen[child.tag] += 1
        suffix = '' if 'no' in child.attrib else f'/{child.tag}#{seen[child.tag]}'
        out.update(flatten(child, path + suffix))
    return out


def compare(left, right):
    a, b = flatten(left), flatten(right)
    rows = [{'path': k, 'before': a.get(k), 'after': b.get(k)}
            for k in sorted(a.keys() | b.keys()) if a.get(k) != b.get(k)]
    counts = Counter(row['path'].split('/')[2].split('#')[0] for row in rows)
    return {'attribute_differences': len(rows), 'by_section': dict(counts), 'rows': rows}


def pinned(base):
    manifest = read_json(base / N31 / 'plant_n31_v2.json')
    checks = {}
    for name, item in dict(manifest['sources'], membership=manifest['membership'],
                           detectors=manifest['observation']['detectors']).items():
        p = base / item['path']
        actual = sha(p.read_bytes()) if p.is_file() else None
        checks[name] = {'path': str(p), 'expected': item['sha256'], 'actual': actual,
                        'matches': actual == item['sha256']}
    return manifest, checks


def speed_summary(net):
    curves = {}
    for element in net.findall('desSpeedDistributions/desSpeedDistribution'):
        if element.get('no') not in {'50','60','70','80','90','100','110'}:
            continue
        points = [(float(p.get('fx')), float(p.get('x')))
                  for p in element.findall('speedDistrDatPts/speedDistributionDataPoint')]
        mean = sum((f1-f0)*(v0+v1)/2 for (f0,v0),(f1,v1) in zip(points,points[1:]))
        curves[element.get('no')] = {'points': points, 'mean_kmh': mean}
    inputs = []
    for element in net.findall('vehicleInputs/vehicleInput'):
        if element.get('no') in {'1098','1099'}:
            inputs.append({'input':element.attrib,'intervals':[p.attrib for p in element.iter('timeIntervalVehVolume')]})
    entries = [flatten(e) for e in net.findall('desSpeedDecisions/desSpeedDecision')
               if e.get('lane','').split(' ')[0] in {'26','74'} and float(e.get('pos')) <= 50]
    return {'curves':curves,'mainline_inputs':inputs,'entry_dsds':entries}


def main():
    old_m, old_pins = pinned(LOCAL)
    new_m, new_pins = pinned(ROOT)
    old = (LOCAL / old_m['sources']['network']['path']).read_bytes()
    new = (ROOT / new_m['sources']['network']['path']).read_bytes()
    v2 = subprocess.check_output(['git','show','3af123f:diagnostics/sdmpc_n31_20260924/network/baseline_s31_v2nc.inpx'],cwd=ROOT)
    nets = {name:ET.fromstring(data) for name,data in [('local_gain',old),('upstream_v2',v2),('upstream_v3b',new)]}
    old_g = read_json(LOCAL / old_m['sources']['geometry']['path'])
    new_g = read_json(ROOT / new_m['sources']['geometry']['path'])
    differences = {name:compare(nets[a],nets[b]) for name,a,b in [
        ('local_to_v2','local_gain','upstream_v2'),('v2_to_v3b','upstream_v2','upstream_v3b'),
        ('local_to_v3b','local_gain','upstream_v3b')]}
    result = {'created_utc':datetime.now(timezone.utc).isoformat(),'native_launched':False,
              'network_sha256':dict(local_gain=sha(old),upstream_v2=sha(v2),upstream_v3b=sha(new)),
              'manifest_checks':{'local':old_pins,'upstream':new_pins},'network_differences':differences,
              'geometry_equal_by_key':{k:old_g.get(k)==new_g.get(k) for k in old_g.keys()|new_g.keys()},
              'cell_count':{'local':len(old_g['cells']),'upstream':len(new_g['cells'])},
              'speed_and_inputs':{k:speed_summary(v) for k,v in nets.items()},
              'membership_equal':read_json(LOCAL/old_m['membership']['path'])==read_json(ROOT/new_m['membership']['path'])}
    (HERE/'baseline_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'sha256':result['network_sha256'],
        'diff_sections':{k:v['by_section'] for k,v in differences.items()},
        'geometry_equal_by_key':result['geometry_equal_by_key'],
        'pin_failures':{k:[n for n,r in x.items() if not r['matches']] for k,x in result['manifest_checks'].items()},
        'means':{k:{i:round(v['mean_kmh'],3) for i,v in x['curves'].items()} for k,x in result['speed_and_inputs'].items()}},ensure_ascii=False))


if __name__ == '__main__':
    main()
