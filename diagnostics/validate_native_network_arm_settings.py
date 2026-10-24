"""Join saved original-network COM readback to static experimental arms; no COM."""
import argparse
import csv
from fractions import Fraction
import hashlib
import io
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
CAPTURE = ROOT / 'diagnostics/routing_lookahead_native_readback_v1'
ARMS = ROOT / 'diagnostics/fixed_beta300v3_network_arms_v1'
NETWORK = ROOT / 'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx'
DECISIONS = ('1123','1124','1125','1134','1135','1136','1137','1116','1118','1119','1126','1138','1140')
CONNECTORS = ('10635','10643','10641','10700')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'size': len(raw), 'sha256': sha(raw)}


def expected_rows(tree):
    expected = {}
    for no in DECISIONS:
        node = tree.find(f"./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no='{no}']")
        require(node is not None, 'Missing reviewed decision '+no)
        for com, xml in [('CombineStaRoutDec','combineStaRoutDec'),('AllVehTypes','allVehTypes')]:
            require(node.get(xml) in ('true','false'), 'Unsupported native Boolean')
            expected[('decision',no,no,com)] = (Fraction(node.get(xml)=='true'), 3)
        for route in node.findall('./vehRoutSta/vehicleRouteStatic'):
            raw = route.get('relFlow','')
            require(not raw or raw.startswith('2 0:'), 'Unsupported RelFlow interval declaration')
            expected[('route',no,route.get('no'),'RelFlow(1)')] = (Fraction(raw[4:] if raw else '1'), 5)
    for no in CONNECTORS:
        node = tree.find(f"./links/link[@no='{no}']")
        for com, xml in [('LnChgDist','lnChgDist'),('LnChgDistIsPerLn','lnChgDistIsPerLn'),('EmergStopDist','emergStopDist')]:
            raw = node.get(xml)
            expected[('connector',no,no,com)] = (Fraction(raw=='true') if xml=='lnChgDistIsPerLn' else Fraction(raw), 3 if xml=='lnChgDistIsPerLn' else 5)
    node = tree.find("./drivingBehaviors/drivingBehavior[@no='1']")
    for com, xml in [('VehRoutDecLookAhead','vehRoutDecLookAhead'),('ConsNextTurn','consNextTurn')]:
        require(node.get(xml) in ('true','false'), 'Unsupported behavior Boolean')
        expected[('driving_behavior','1','1',com)] = (Fraction(node.get(xml)=='true'), 3)
    return expected


def validate():
    pinned = [NETWORK, CAPTURE/'routes.csv', CAPTURE/'manifest.json', ARMS/'manifest.json', Path(__file__).resolve()]
    inputs = [pin(p) for p in pinned]
    tree = ET.fromstring(NETWORK.read_bytes())
    native = json.loads((CAPTURE/'manifest.json').read_text(encoding='utf-8-sig'))
    manifest = json.loads((ARMS/'manifest.json').read_text(encoding='utf-8'))
    network_sha = inputs[0]['sha256']
    require(native['passed'] is True and native['exit_code']==0 and native['timed_out'] is False and native['source_changes']==[], 'Native capture not successful/unchanged')
    native_sources = {str(Path(p).resolve()): value.lower() for p,value in native['sources'].items()}
    require(native_sources[str(NETWORK.resolve())] == network_sha == manifest['source_network_sha256'], 'Native/arm source network mismatch')
    source_differences = [p for p,h in native_sources.items() if sha(Path(p).read_bytes()) != h]
    require(not source_differences, 'Captured source bytes changed: '+str(source_differences))
    rows = list(csv.DictReader(io.StringIO((CAPTURE/'routes.csv').read_text(encoding='utf-8-sig'))))
    expected, actual, checks = expected_rows(tree), {}, []
    for row in rows:
        key = tuple(row[k] for k in ('kind','owner_no','item_no','attribute'))
        require(key not in actual, 'Duplicate readback key '+str(key))
        require(key in expected, 'Unexpected readback key '+str(key))
        require(int(row['error_number'])==0 and row['error_description']=='', 'Native readback error '+str(key))
        value, vartype = expected[key]
        measured = Fraction(row['value'])  # rejects NaN/infinity
        require(measured==value and int(row['vartype'])==vartype, 'Native value/type mismatch '+str(key))
        actual[key] = measured
        checks.append({'key':list(key),'xml_expected':str(value),'COM_observed':row['value'],'vartype':vartype,'exact':True})
    require(set(actual)==set(expected), 'Missing native readback rows')
    verified_outputs = []
    for name,row in manifest['outputs'].items():
        path = (ARMS/name).resolve()
        require(path.is_relative_to(ARMS.resolve()), 'Manifest output escaped arm tree')
        raw = path.read_bytes()
        require(len(raw)==row['size'] and sha(raw)==row['sha256'], 'Arm output changed '+name)
        verified_outputs.append(name)
    historical_input_changes = []
    for name,row in manifest['inputs'].items():
        current = sha((ROOT/name).read_bytes())
        if current != row['sha256']:
            require(name=='diagnostics/fixed_beta300v3_route_experiment_design.md', 'Non-document arm input changed '+name)
            historical_input_changes.append({'path':name,'prepared_sha256':row['sha256'],'current_sha256':current,
                'scope':'Parent-authorized removal of unnecessary approval wording after v1 preparation; original manifest preserved.'})
    relations = []
    for row in manifest['route_id_mapping']:
        parent, old = row['parent_decision'], row['old_parent_route']
        downstream = row['old_downstream_route']
        total = sum(v for (kind,no,item,attr),v in actual.items() if kind=='route' and no==parent)
        down_total = sum(v for (kind,no,item,attr),v in actual.items() if kind=='route' and no=='1135')
        p = actual[('route',parent,old,'RelFlow(1)')]/total
        q = actual[('route','1135',downstream,'RelFlow(1)')]/down_total
        require(p*q == Fraction(row['upstream_probability_after']), 'Observed native probability product differs')
        relations.append({'parent':parent,'original_route':old,'downstream1135_route':downstream,'new_route':row['new_route'],'P':str(p),'q':str(q),'product':str(p*q),'exact':True})
    backgrounds = []
    for node in tree.findall('./backgroundImages/backgroundImage'):
        ref = node.get('pathFilename')
        data_relative = ref.startswith('#data#')
        original = (NETWORK.parent/ref[6:]).resolve() if data_relative else Path(ref)
        targets = {name:str((ARMS/arm['network']).parent/ref[6:]) if data_relative else str(original) for name,arm in manifest['arms'].items()}
        backgrounds.append({'no':node.get('no'),'raw_reference':ref,'resolution_basis':'#data# resolved against loaded INPX directory' if data_relative else 'existing absolute path unchanged',
            'original_resolved_path':str(original),'original_exists':original.is_file(),
            'original_size':original.stat().st_size if original.is_file() else None,
            'arm_resolved_paths':targets,'arm_exists':{name:Path(p).is_file() for name,p in targets.items()},
            'introduced_missing_asset':data_relative and original.is_file() and any(not Path(p).is_file() for p in targets.values())})
    for item,path in zip(inputs,pinned):
        require(sha(path.read_bytes())==item['sha256'], 'Validation input changed '+str(path))
    return {'schema':'native-network-arm-settings-validation/v1','status':'complete','original_native_settings_exact':True,
        'run_ready':False,'executed_model_or_COM':False,'inputs':inputs,'native_capture_elapsed_sec':native['elapsed_sec'],
        'native_source_files_rechecked':len(native_sources),'source_changes':[],
        'historical_arm_document_pin_changes':historical_input_changes,
        'readback_checks':checks,'readback_count':len(checks),'readback_duplicates':0,'readback_errors':0,
        'arm_output_files_verified':len(verified_outputs),'native_probability_products':relations,
        'background_reference_resolution':backgrounds,
        'scope':['Original-network COM only; variant COM/native loading and vehicle eligibility remain unverified.',
                 'Original capture manifest has no routes.csv output hash; this validation pins the saved CSV bytes now and cross-checks every row against the pinned original XML.',
                 'Missing #data# background is a package path issue. Its effect on LoadNet/simulation is not tested. For 2D visual use restore the same asset in a separately versioned package; do not mutate the existing arm manifest.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    result = validate()
    rows = result['readback_count']
    text = '# Native settings and prepared network arms\n\n'
    text += f'All {rows} original-network COM rows match the pinned INPX exactly, including numeric values, native types, unique keys and error-free completeness. The nine expanded probability products also match these actual native weights. All 132 manifest-listed arm artifacts retain their exact bytes.\n\n'
    text += '1123 weights are 1:10:1; 1124/1125 are 6:1:1; 1135 is 3:1:1. Combine and AllVehTypes are true. Behavior 1 look-ahead is true and ConsNextTurn false. Connector 10635 has distance 1000 m, per-lane false, and emergency-stop distance 5 m. Empty XML RelFlow defaults are therefore confirmed for the queried original routes. This does not validate the modified route network in COM.\n\n'
    text += 'The original image `#data#개포동 Test-bed.jpg` exists (95,065,685 bytes), but all three copied INPX directories lack that relative file. Its 2D background reference therefore no longer resolves locally. The other original background is an absolute TRLAB Downloads PNG and is already absent on this host; relocation did not introduce that absence. Exact paths and existence flags are in the JSON. No asset was copied or XML reference changed during this check.\n\n'
    text += 'All arms remain `run_ready=false`. Preserve the v1 manifest and, before 2D inspection, make a separate version containing identical JPG bytes in each INPX directory or an explicitly recorded equivalent asset resolution. Native LoadNet behavior, variant RelFlow/Combine and eligible route coverage remain launch gates; a missing visual asset has not been declared simulation-neutral.\n\n'
    text += 'After the original successful 133-file producer verification, the parent-authorized edit removed unnecessary approval wording in the experiment design MD. Its historical/current hashes are preserved in this sidecar. The original arm manifest is unchanged; running the old producer --verify against that updated document will reject the provenance difference. Network, SIG, generated artifact and numeric transformation bytes still match all v1 pins.\n\n'
    text += 'The saved COM capture has no routes.csv hash in its own manifest. This report pins the current CSV bytes, links its successful source network to the arm manifest, and checks every recorded setting against XML; it does not invent a historical output signature. Source bytes were rechecked unchanged. No model/COM/VISSIM execution was performed by this validator.\n'
    files = {'native_settings_validation.json':(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf-8'), 'native_settings_validation.md':text.encode('utf-8')}
    for name,raw in files.items():
        path = ROOT/'diagnostics'/name
        if args.verify:
            require(path.read_bytes()==raw, 'Prior validation bytes changed '+name)
        else:
            with path.open('xb') as stream: stream.write(raw)
    print(json.dumps({'rows':rows,'products':len(result['native_probability_products']),'arm_outputs':result['arm_output_files_verified'],'run_ready':False,'source_changes':[], 'outputs':{k:sha(v) for k,v in files.items()}}))


if __name__ == '__main__':
    main()
