"""Static preparation/final validation for saved flat-network LoadNet probes.

This stdlib validator never creates COM or executes a model. Preparation hashes
the completed assets, including the JPG. The associated isolated read-only
native probe is not a normal timing benchmark; the parent schedules its I/O.
"""
import argparse
import csv
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ARMS = ('baseline','lcd10635_2000','upstream1135')
DECISIONS = {'1123','1124','1125','1134','1135','1136','1137','1116','1118','1119','1126','1138','1140'}
V1_SHA = '18322b5ca49afe57b59baf271afdc8a3fc1cd850b711f2027afdedd656846030'
NATIVE_SHA = '6924c384ebdcb53717a31f4ad829e769b0bd557f9140119366e81eb82e0cef81'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def safe_path(value):
    path = Path(value)
    path = (path if path.is_absolute() else ROOT/path).resolve()
    require(path.is_relative_to(ROOT), 'Path escaped worktree: '+str(path))
    return path


def write_json(path, value):
    with path.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2)
        stream.write('\n')


def expected(tree):
    result = {}
    for node in tree.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic'):
        no = node.get('no')
        key = ('decision_index',no,no,'No')
        require(key not in result,'Duplicate XML decision')
        result[key] = (str(int(no)),3)
        if no not in DECISIONS:
            continue
        for com,xml in [('CombineStaRoutDec','combineStaRoutDec'),('AllVehTypes','allVehTypes')]:
            require(node.get(xml) in ('true','false'),'Unknown Boolean')
            result[('decision',no,no,com)] = (str(int(node.get(xml)=='true')),3)
        for route in node.findall('./vehRoutSta/vehicleRouteStatic'):
            raw = route.get('relFlow','')
            require(not raw or raw.startswith('2 0:'),'Unreviewed static interval')
            key = ('route',no,route.get('no'),'RelFlow(1)')
            require(key not in result,'Duplicate XML route')
            result[key] = (str(Fraction(raw[4:] if raw else '1')),5)
    for no in ('10635','10643','10641','10700'):
        node = tree.find(f"./links/link[@no='{no}']")
        for com,xml in [('LnChgDist','lnChgDist'),('LnChgDistIsPerLn','lnChgDistIsPerLn'),('EmergStopDist','emergStopDist')]:
            raw = node.get(xml)
            if xml == 'lnChgDistIsPerLn':
                require(raw in ('true','false'),'Unknown per-lane Boolean')
                result[('connector',no,no,com)] = (str(int(raw=='true')),3)
            else:
                result[('connector',no,no,com)] = (str(Fraction(raw)),5)
    node = tree.find("./drivingBehaviors/drivingBehavior[@no='1']")
    for com,xml in [('VehRoutDecLookAhead','vehRoutDecLookAhead'),('ConsNextTurn','consNextTurn')]:
        require(node.get(xml) in ('true','false'),'Unknown behavior Boolean')
        result[('driving_behavior','1','1',com)] = (str(int(node.get(xml)=='true')),3)
    return [{'key':list(key),'value':value,'vartype':kind} for key,(value,kind) in sorted(result.items())]


def prepare(flat, output):
    require(output.parent.is_relative_to(ROOT/'diagnostics') or output.parent==ROOT/'diagnostics', 'Output must be in diagnostics')
    require(output.is_dir() and not any(output.iterdir()),'Preflight output must be an empty fresh directory')
    require(not output.is_relative_to(flat), 'Output must not be inside flat assets')
    manifest_path = flat/'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    require(manifest['schema']=='fixed-command-flat-network-assets/v1','Wrong flat schema')
    require(manifest['preserved_v1_manifest_sha256']==V1_SHA and manifest['original_native_settings_validation_sha256']==NATIVE_SHA,'Wrong upstream provenance')
    require(manifest['data_reference_filesystem_validation'] is True and manifest['original_or_v1_writes'] is False,'Unverified flat asset package')
    pinned = {str(manifest_path):sha(manifest_path)}
    v1_path = ROOT/'diagnostics/fixed_beta300v3_network_arms_v1/manifest.json'
    native_path = ROOT/'diagnostics/native_settings_validation.json'
    require(sha(v1_path)==V1_SHA and sha(native_path)==NATIVE_SHA,'Historical evidence bytes changed')
    pinned[str(v1_path)], pinned[str(native_path)] = V1_SHA, NATIVE_SHA
    v1 = json.loads(v1_path.read_text(encoding='utf-8'))
    sig_names = {row['copied_relative_path'] for row in v1['relative_sig_references']}
    require(len(sig_names)==42 and set(manifest['outputs'])=={arm+'.inpx' for arm in ARMS}|sig_names|{'개포동 Test-bed.jpg'},'Flat output names differ from reviewed v1')
    for arm in ARMS:
        require(manifest['outputs'][arm+'.inpx']['destination_sha256']==v1['arms'][arm]['network_sha256'],'Flat variant differs from reviewed v1')
    for name in sig_names:
        require(manifest['outputs'][name]['destination_sha256']==v1['outputs']['baseline/'+name]['sha256'],'Flat SIG differs from reviewed v1')
    for row in manifest['inputs']:
        path = safe_path(row['path'])
        require(sha(path)==row['sha256'],'Flat input changed: '+str(path))
        pinned[str(path)] = row['sha256']
    for name,row in manifest['outputs'].items():
        require(name not in ('','.','..') and not any(c in name for c in '/\\:'),'Unsafe flat filename')
        path = flat/name
        require(path.stat().st_size==row['size'] and sha(path)==row['destination_sha256'],'Flat asset bytes changed: '+name)
        pinned[str(path)] = row['destination_sha256']
        sources = row.get('sources',[row['source']] if 'source' in row else [])
        for source in sources:
            p = safe_path(source)
            require(sha(p)==row['source_sha256'],'Original/v1 source changed: '+source)
            pinned[str(p)] = row['source_sha256']
    require(len(manifest['outputs'])==46 and manifest['shared_assets']['sig_count']==42 and manifest['shared_assets']['jpg_count']==1,'Unexpected asset set')
    # Pin original SIG files as well as the exact v1 copies/flat assets.
    source_dir = ROOT/'network/real_world_gaepo_modi'
    for name,row in manifest['outputs'].items():
        if name.lower().endswith('.sig'):
            path = source_dir/name
            require(sha(path)==row['source_sha256'],'Original SIG differs: '+name)
            pinned[str(path)] = row['source_sha256']
    for name in ('probe_flat_network_native_settings.vbs','run_flat_network_native_gate.ps1','validate_flat_network_native_gate.py'):
        path = ROOT/'diagnostics'/name
        pinned[str(path)] = sha(path)
    watchdog = ROOT/'scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1'
    pinned[str(watchdog)] = sha(watchdog)
    arms = {}
    for name in ARMS:
        path = flat/(name+'.inpx')
        raw = path.read_bytes()
        tree = ET.fromstring(raw)
        refs = [value[6:] for node in tree.iter() for value in node.attrib.values() if value.startswith('#data#')]
        require(set(refs)=={n for n in manifest['outputs'] if n.lower().endswith('.sig')}|{'개포동 Test-bed.jpg'},'Unreviewed #data# reference set')
        require(all((flat/ref).is_file() for ref in refs),'Missing #data# asset')
        arms[name] = {'network_path':str(path),'network_sha256':hashlib.sha256(raw).hexdigest(),
                      'expected_readback':expected(tree),'data_files_resolve':True}
    result = {'schema':'flat-network-native-preflight/v1','flat_directory':str(flat),
        'flat_manifest_sha256':pinned[str(manifest_path)],'flat_manifest_path':str(manifest_path),
        'pinned_files':pinned,'arms':arms,'native_vehicle_eligibility_verified':False,
        'image_hashing_scope':'Before/after isolated read-only native probe; not a normal timing benchmark'}
    write_json(output/'preflight.json',result)
    print(json.dumps({'prepared':True,'arms':list(arms),'pinned_files':len(pinned)}))


def finish(output):
    preflight_path = output/'preflight.json'
    pre = json.loads(preflight_path.read_text(encoding='utf-8'))
    source_changes = []
    for path,expected_sha in pre['pinned_files'].items():
        try:
            actual = sha(Path(path))
        except OSError as exc:
            actual = 'unreadable:'+str(exc)
        if actual != expected_sha:
            source_changes.append({'path':path,'before':expected_sha,'after':actual})
    arms, errors = {}, []
    for name in ARMS:
        directory = output/name
        row = {'network_sha256':pre['arms'][name]['network_sha256'],'native_readback_exact':False,
               'loadnet_passed':False,'owned_processes_gone':False,'native_vehicle_eligibility_verified':False}
        arms[name] = row
        try:
            process_path, csv_path = directory/'process.json', directory/'routes.csv'
            process = json.loads(process_path.read_text(encoding='utf-8-sig'))
            row['process_manifest_sha256'] = sha(process_path)
            row['owned_processes_gone'] = process['owned_processes_gone'] is True
            require(process['exit_code']==0 and process['timed_out'] is False and process['owned_processes_gone'] is True
                    and process['requires_cleanup'] is False and process.get('error') is None,'Process/cleanup gate failed')
            require(process['network_sha256']==row['network_sha256'] and process['preflight_sha256']==sha(preflight_path),'Process/input provenance mismatch')
            stdout = (directory/'stdout.txt').read_text(encoding='utf-8-sig')
            require('NETWORK_LOADED_READ_ONLY=1' in stdout.splitlines() and 'ROUTE_PROBE_DONE=1' in stdout.splitlines()
                    and 'ATTRIBUTE_FAILURES=0' in stdout.splitlines(),'Native completion markers missing')
            row['loadnet_passed'] = True
            expected_rows = {tuple(r['key']):r for r in pre['arms'][name]['expected_readback']}
            actual = {}
            with csv_path.open(encoding='utf-16',newline='') as stream:
                reader = csv.DictReader(stream)
                require(reader.fieldnames==['kind','owner_no','item_no','attribute','value','vartype','error_number','error_description'],'CSV schema mismatch')
                for item in reader:
                    key = tuple(item[k] for k in ('kind','owner_no','item_no','attribute'))
                    require(key not in actual and key in expected_rows,'Duplicate/unexpected native key '+str(key))
                    expect = expected_rows[key]
                    require(int(item['error_number'])==0 and not item['error_description'],'COM attribute error '+str(key))
                    require(Fraction(item['value'])==Fraction(expect['value']) and int(item['vartype'])==expect['vartype'],'Native value/type mismatch '+str(key))
                    actual[key] = item
            require(set(actual)==set(expected_rows),'Missing native settings/decision/route IDs')
            row.update(native_readback_exact=True,readback_rows=len(actual),readback_csv_sha256=sha(csv_path),
                       readback_csv_path=str(csv_path),decision_count=sum(k[0]=='decision_index' for k in actual),
                       route_keys=[list(k[1:3]) for k in sorted(actual) if k[0]=='route'],
                       distance_10635=actual[('connector','10635','10635','LnChgDist')]['value'])
        except (OSError,ValueError,KeyError,TypeError) as exc:
            row['error'] = str(exc)
            errors.append(name+': '+str(exc))
    passed = not errors and not source_changes and all(row['native_readback_exact'] for row in arms.values())
    result = {'schema':'flat-network-native-gate/v1','native_load_readback_passed':passed,
        'flat_manifest_sha256':pre['flat_manifest_sha256'],'flat_manifest_path':pre['flat_manifest_path'],
        'preflight_sha256':sha(preflight_path),'arms':arms,'source_changes':source_changes,'errors':errors,
        'native_vehicle_eligibility_verified':False,'simulation_executed':False,'run_ready':False,
        'scope':'LoadNet/setting/ID/source/owned-process gate only. Runtime eligible vehicles, lane-change success, writer and full-run outcome are separate gates.'}
    write_json(output/'native_gate.json',result)
    print(json.dumps({'native_load_readback_passed':passed,'native_gate_sha256':sha(output/'native_gate.json'),'errors':errors}))
    return 0 if passed else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    parser.add_argument('--flat')
    parser.add_argument('--finish',action='store_true')
    args = parser.parse_args()
    output = safe_path(args.output)
    if args.finish:
        raise SystemExit(finish(output))
    require(args.flat is not None,'--flat is required for preparation')
    flat = safe_path(args.flat)
    prepare(flat,output)


if __name__ == '__main__':
    main()
