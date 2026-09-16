"""Create this experiment's copy: only input1098's six volumes times0.8."""
import argparse
import hashlib
import json
import re
import sys
from decimal import Decimal
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from fast_nc_prepare import prepare_native_preserve

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--seed',type=int,default=13)
args = parser.parse_args()
assert args.seed > 0
source = HERE/'prepared_v1/network/baseline.inpx'
original = source.read_bytes()
before_sha = hashlib.sha256(original).hexdigest()
assert before_sha == '10e1fd8f005ffe30646233bd15cef0344ab992036f144fe8e6f91638bb051cb5'
root = ET.fromstring(original)
before = root.find("./vehicleInputs/vehicleInput[@no='1098']")
assert before is not None and before.get('link') == '74'
nodes = before.findall('./timeIntVehVols/timeIntervalVehVolume')
assert [n.get('timeInt') for n in nodes] == ['1 0','1 900000','1 1800000','1 2700000','1 3600000','1 4500000']
records = [{'input_no':1098, 'start_sec':int(n.get('timeInt').split()[1])//1000,
            'before_vph':n.get('volume'), 'after_vph':format(Decimal(n.get('volume'))*Decimal('0.8'),'f')} for n in nodes]
pattern = rb'<vehicleInput\b[^>]*\bno="1098"[^>]*>.*?</vehicleInput>'
matches = list(re.finditer(pattern, original, re.S))
assert len(matches) == 1
match = matches[0]
block = match.group(0)
assert len(re.findall(rb'\bvolume="[^"]+"', block)) == 6
changed_block = re.sub(rb'\bvolume="([^"]+)"', lambda m: b'volume="'+format(Decimal(m.group(1).decode())*Decimal('0.8'),'f').encode()+b'"', block)
candidate = original[:match.start()] + changed_block + original[match.end():]
assert root.find('./simulation').get('randSeed') == '13'
if args.seed != 13:
    candidate, seed_changes = re.subn(rb'(<simulation\b[^>]*\brandSeed=")13(")',
        lambda m:m.group(1)+str(args.seed).encode()+m.group(2),candidate,count=1)
    assert seed_changes == 1
after_root = ET.fromstring(candidate)
assert after_root.find('./simulation').get('randSeed') == str(args.seed)
after_root.find('./simulation').set('randSeed','13')
after_nodes = after_root.find("./vehicleInputs/vehicleInput[@no='1098']").findall('./timeIntVehVols/timeIntervalVehVolume')
assert [n.get('volume') for n in after_nodes] == [r['after_vph'] for r in records]
for n, r in zip(after_nodes, records):
    n.set('volume', r['before_vph'])
assert ET.tostring(root) == ET.tostring(after_root), 'Unexpected semantic XML change'
case = HERE/('east080_v1' if args.seed==13 else f'east080_seed{args.seed}_v1')
network_dir = case/'source_network'
network_dir.mkdir(parents=True, exist_ok=False)
network = network_dir/'baseline.inpx'
network.write_bytes(candidate)
asset_names = {value[6:] for node in root.iter() for value in node.attrib.values() if value.startswith('#data#')}
for name in asset_names:
    assert Path(name).name == name and '/' not in name and '\\' not in name
    (network_dir/name).write_bytes((source.parent/name).read_bytes())
manifest = {'baseline_source':str(source), 'baseline_sha256':before_sha,
    'candidate_source':str(network), 'candidate_sha256':hashlib.sha256(candidate).hexdigest(),
    'change':f'Input1098 (east freeway source74) volume times0.8 in all six intervals; saved seed13 to{args.seed}; all other bytes unchanged',
    'changes':records, 'unchanged_semantic_xml_after_reverting_six_volumes':True,
    'seed':args.seed, 'terminal_sec':9000, 'all_other_input_and_routing_demand_preserved':True,
    'baseline_expected_input1098_vehicles':27126, 'candidate_expected_input1098_vehicles':21700.8,
    'tail':'Final rate6336 veh/h retained through9000; no zero-demand cooldown',
    'asset_sha256':{name:hashlib.sha256((network_dir/name).read_bytes()).hexdigest() for name in sorted(asset_names)}}
(case/'demand_change.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
prepare_native_preserve(network, case/'prepared', 9000)
print(json.dumps({'changes':records,'candidate_sha256':manifest['candidate_sha256']}, ensure_ascii=False))
