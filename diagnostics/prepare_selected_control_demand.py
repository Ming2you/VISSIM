"""Represent a selected native NC demand table using the existing VBS profile.

No model/COM imports. One multiplier per input must reproduce every selected
interval to absolute error <=1e-10 veh/h. Nonrepresentable timetables fail.
"""
import argparse
import csv
import copy
import hashlib
import json
import math
import sys
from pathlib import Path
from statistics import median
import xml.etree.ElementTree as ET

TOLERANCE = 1e-10
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def recording_artifacts(report, output):
    """Add native state columns to a fresh copy; retain the physical source pins."""
    from evaluation.controllers.network_provenance import prepare_recording_bytes
    from diagnostics.com_execution_equivalence.verify_pair import _plan_groups
    from diagnostics.com_execution_equivalence.command_clock import native_options
    source = Path(report['network'])
    folder = Path(output).resolve()/'native_recording'
    target = folder/source.name
    vbs = ROOT/'scripts/run_real_world_stackelberg_controller.vbs'
    config = Path(report.get('vbs_config') or ROOT/'evaluation/real_world_modi_control_ver2n21_20260907/real_world_modi_control_config_ver2n21.vbs')
    plan = config.with_name(config.stem+'_sgplan.vbs')
    urban, _ = _plan_groups(plan.read_bytes(), True)
    meters = native_options(vbs.read_text(encoding='utf-8-sig'), config.read_text(encoding='utf-8-sig'))
    if set(urban) & set(meters): raise ValueError('Overlapping urban/meter ownership')
    groups = {sc: sorted(map(int, values)) for sc,values in urban.items()}
    groups.update({sc:[1] for sc in meters})
    original = source.read_bytes()
    if hashlib.sha256(original).hexdigest()!=report['network_sha256']:
        raise ValueError('Physical source changed during recording preparation')
    rule_detectors = report.get('rule_detectors')
    recorded = prepare_recording_bytes(original, groups, rule_detectors=rule_detectors)
    proof = {'schema':'native-signal-recording-network/v1',
        'source_network':{'path':str(source),'sha256':report['network_sha256']},
        'recorded_network':{'path':str(target),'sha256':hashlib.sha256(recorded).hexdigest()},
        'groups':groups}
    if rule_detectors is not None:
        proof['rule_detectors'] = rule_detectors
    files = {target:recorded}
    tree = ET.fromstring(original)
    names = {node.get('supplyFile2') for node in tree.findall('./signalControllers/signalController')
             if node.get('supplyFile2')}
    names.update(value for node in tree.iter('backgroundImage') for value in node.attrib.values()
                 if value.startswith('#data#'))
    for name in sorted(names):
        if not name.startswith('#data#'):
            raise ValueError('Unexpected relative native asset reference: '+name)
        basename = name[len('#data#'):]
        if Path(basename).name!=basename or '\\' in basename:
            raise ValueError('Native asset must be a sibling basename')
        old = source.parent/basename
        data = old.read_bytes()
        files[folder/basename] = data
        report['source_sha256'][str(old)] = hashlib.sha256(data).hexdigest()
    for path in (vbs, config, plan): report['source_sha256'][str(path)] = sha(path)
    proof_path = Path(output).resolve()/'network_recording.json'
    files[proof_path] = json_bytes(proof)
    report.update(runtime_network=str(target), runtime_network_sha256=proof['recorded_network']['sha256'],
        network_recording_proof={'path':str(proof_path),'sha256':hashlib.sha256(files[proof_path]).hexdigest()},
        native_signal_record=True)
    report['generated_sha256'].update({str(path):hashlib.sha256(data).hexdigest() for path,data in files.items()})
    return files


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def json_bytes(doc):
    return (json.dumps(doc,indent=2,ensure_ascii=False)+'\n').encode('utf-8')


def path_ref(path):
    path=Path(path).resolve()
    try: return path.relative_to(ROOT).as_posix()
    except ValueError: return str(path)


def selected_signal_config(tuning):
    """Bind an optional native clock plan to the existing runner's sibling VBS."""
    base = ROOT/'evaluation/real_world_modi_control_ver2n21_20260907/real_world_modi_control_config_ver2n21.vbs'
    plan_ref = tuning.get('urban', {}).get('plan', {}).get('actuation_plan_json')
    config_ref = tuning.get('execution', {}).get('signal_vbs_config')
    if not plan_ref and not config_ref:
        return base, {}
    if not isinstance(plan_ref, str) or not isinstance(config_ref, str):
        raise ValueError('Native clock activation requires both JSON and generated sibling VBS configuration')
    plan_path = (ROOT/plan_ref).resolve(strict=True)
    config_path = (ROOT/config_ref).resolve(strict=True)
    sibling = config_path.with_name(config_path.stem+'_sgplan.vbs')
    from scripts.derive_signal_group_actuation_plan_mainline_20260825 import render_vbs
    table = json.loads(plan_path.read_text(encoding='utf-8-sig'))
    if (not table.get('controllers') or
            not all(node.get('native_clock_basis') for node in table['controllers'].values())):
        raise ValueError('Selected native plan must cover every controlled signal')
    if config_path.read_bytes() != base.read_bytes():
        raise ValueError('Native clock activation must preserve the base VBS control configuration')
    if sibling.read_text(encoding='utf-8-sig') != render_vbs(table, sha(plan_path)):
        raise ValueError('Native clock VBS sibling differs from the selected JSON renderer')
    sources = (base, config_path, sibling, plan_path,
        ROOT/'scripts/derive_signal_group_actuation_plan_mainline_20260825.py')
    return config_path, {str(path): sha(path) for path in sources}


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def finite(value):
    result=float(value)
    if not math.isfinite(result) or result<0: raise ValueError('Invalid demand value')
    return result


def convert(selected_prepared):
    folder=Path(selected_prepared).resolve(strict=True)
    meta=json.loads((folder/'prepared.json').read_text(encoding='utf-8-sig'))
    if meta.get('seed')!=13 or meta.get('terminal_sec')!=5400:
        raise ValueError('Selected NC evidence must use seed13 and terminal5400')
    network=Path(meta['network']).resolve(strict=True)
    digest=hashlib.sha256(network.read_bytes()).hexdigest()
    if meta['inputs'].get(str(network))!=digest: raise ValueError('Selected native network changed')
    tree=ET.parse(network).getroot()
    starts=[float(n.attrib['start']) for n in tree.findall("./timeIntervalSets/timeIntervalSet[@no='VEHICLEINPUT']/timeInts/timeInterval")]
    if starts!=[0,900,1800,2700,3600,4500]: raise ValueError('Expected native six intervals')
    native={}
    for vi in tree.findall('./vehicleInputs/vehicleInput'):
        for row in vi.findall('./timeIntVehVols/timeIntervalVehVolume'):
            set_no,ticks=row.attrib['timeInt'].split(); sec=int(ticks)/1000
            if set_no!='1' or sec not in starts: raise ValueError('Unknown input interval')
            key=(vi.attrib['no'],f'1-{starts.index(sec)+1}')
            if key in native: raise ValueError('Duplicate native interval')
            native[key]=(sec,finite(row.attrib['volume']))
    selected=read_csv(folder/'demand.csv'); targets={}; groups={}
    for row in selected:
        key=(row['input_no'],row['time_int'])
        if key in targets or key not in native: raise ValueError('Duplicate/unknown selected interval')
        sec,before=native[key]; target=finite(row['volume_vph'])
        if finite(row['start_sec'])!=sec or finite(row['before_vph'])!=before:
            raise ValueError('Selected/native source demand differs')
        if before==0 and target!=0: raise ValueError('Multiplier cannot create positive demand from zero')
        targets[key]=target
        if before>0: groups.setdefault(key[0],[]).append(target/before)
        else: groups.setdefault(key[0],[])
    if len(native)!=204 or set(targets)!=set(native) or len(groups)!=34:
        raise ValueError('Expected full selected 34 inputs x six intervals')
    factors={no:median(values) if values else 0.0 for no,values in groups.items()}
    comparison=[]
    for key,(sec,before) in native.items():
        actual=before*factors[key[0]]  # exact VBS scale1 * per-input multiplier contract
        error=abs(actual-targets[key])
        if not math.isfinite(actual) or error>TOLERANCE:
            raise ValueError('Time-varying selected demand cannot use one multiplier: '+str(key))
        comparison.append({'input_no':key[0],'time_int':key[1],'start_sec':sec,
            'before_vph':before,'selected_vph':targets[key],'profile_vph':actual,'abs_error_vph':error})
    profile='role,multiplier\n__default__,1.0\n'+''.join(f'no:{no},{factors[no]!r}\n' for no in sorted(factors,key=int))
    report={'selected_prepared':str(folder),'network':str(network),'network_sha256':digest,
        'selected_demand_sha256':hashlib.sha256((folder/'demand.csv').read_bytes()).hexdigest(),
        'rows':204,'inputs':34,'absolute_tolerance_vph':TOLERANCE,
        'max_abs_error_vph':max(x['abs_error_vph'] for x in comparison),
        'float_exact_rows':sum(x['abs_error_vph']==0 for x in comparison),
        'per_input_multiplier':factors,'demand_scale':1.0,'passed':True,
        'profile_sha256':hashlib.sha256(profile.encode('ascii')).hexdigest(),
        'selected_prepared_sha256':sha(folder/'prepared.json')}
    return profile,comparison,report


def package(selected_prepared, tuning, output):
    """Construct new future-demand declaration; all original physical fields survive."""
    profile,comparison,report=convert(selected_prepared)
    output=Path(output).resolve(); tuning=Path(tuning).resolve(strict=True)
    original=json.loads(tuning.read_text(encoding='utf-8-sig'))
    if 'extends' in original: raise ValueError('Expected a flattened base tuning')
    source=(ROOT/original['urban']['native_internal_inputs']).resolve(strict=True)
    declaration=json.loads(source.read_text(encoding='utf-8-sig'))
    if declaration.get('schema')!='native-internal-inputs/v1': raise ValueError('Unknown native schedule declaration')
    if declaration['network']['sha256']!=report['network_sha256']:
        raise ValueError('Selected network differs from existing native physical declaration; rebinding is forbidden')
    # These are the same input-role and gate pins the production validator checks.
    for key in ('network','input_roles','gate_map','demand_profile'):
        if sha(ROOT/declaration[key]['path'])!=declaration[key]['sha256']:
            raise ValueError('Original declaration source changed: '+key)
    revised=copy.deepcopy(declaration)
    revised['demand_profile']={'path':path_ref(output/'profile.csv'),'sha256':report['profile_sha256']}
    revised['selected_demand_derivation']={
        'source_declaration':{'path':path_ref(source),'sha256':sha(source)},
        'selected_prepared':{'path':report['selected_prepared'],'sha256':report['selected_prepared_sha256']},
        'selected_demand_sha256':report['selected_demand_sha256'],
        'comparison_path':path_ref(output/'comparison.csv'),
        'rows':204,'absolute_tolerance_vph':TOLERANCE,'max_abs_error_vph':report['max_abs_error_vph'],
        'scope':'Future native demand schedule only; original physical definitions and empirical calibration pins unchanged'}
    rest=copy.deepcopy(revised); rest.pop('selected_demand_derivation'); rest['demand_profile']=declaration['demand_profile']
    if 'selected_demand_derivation' in declaration:
        rest['selected_demand_derivation']=declaration['selected_demand_derivation']
    if rest!=declaration: raise AssertionError('Unexpected native declaration change')
    shared_source=(ROOT/original['urban']['shared_approach']).resolve(strict=True)
    shared_original=json.loads(shared_source.read_text(encoding='utf-8-sig'))
    if shared_original.get('schema')!='shared-approach/v1': raise ValueError('Unknown shared approach declaration')
    if shared_original['network']['sha256']!=report['network_sha256']:
        raise ValueError('Selected network differs from shared physical declaration; rebinding is forbidden')
    for key in ('network','gate_map','jam_source','demand_profile'):
        if sha(ROOT/shared_original[key]['path'])!=shared_original[key]['sha256']:
            raise ValueError('Original shared approach source changed: '+key)
    shared=copy.deepcopy(shared_original)
    shared['demand_profile']=copy.deepcopy(revised['demand_profile'])
    shared['selected_demand_derivation']=copy.deepcopy(revised['selected_demand_derivation'])
    shared['selected_demand_derivation']['source_declaration']={'path':path_ref(shared_source),'sha256':sha(shared_source)}
    shared_rest=copy.deepcopy(shared); shared_rest.pop('selected_demand_derivation')
    if 'selected_demand_derivation' in shared_original:
        shared_rest['selected_demand_derivation']=shared_original['selected_demand_derivation']
    shared_rest['demand_profile']=shared_original['demand_profile']
    if shared_rest!=shared_original: raise AssertionError('Unexpected shared physical declaration change')
    config=copy.deepcopy(original)
    config['urban']['native_internal_inputs']=path_ref(output/'native_internal_inputs.json')
    config['urban']['shared_approach']=path_ref(output/'shared_approach.json')
    restored=copy.deepcopy(config); restored['urban']['native_internal_inputs']=original['urban']['native_internal_inputs']
    restored['urban']['shared_approach']=original['urban']['shared_approach']
    if restored!=original: raise AssertionError('Unexpected controller tuning change')
    report.update({'base_tuning':str(tuning),'base_tuning_sha256':sha(tuning),
        'source_declaration':str(source),'source_declaration_sha256':sha(source),
        'config_changed_paths':['urban.native_internal_inputs','urban.shared_approach'],
        'declaration_changed_paths':['demand_profile','selected_demand_derivation'],
        'controller_tuning':str(output/'config.json'),'declaration_path':str(output/'native_internal_inputs.json')})
    report['shared_source_declaration']={'path':str(shared_source),'sha256':sha(shared_source)}
    report['shared_declaration_path']=str(output/'shared_approach.json')
    report['source_sha256']={str(tuning):sha(tuning),str(source):sha(source),str(shared_source):sha(shared_source),
        str(Path(report['selected_prepared'])/'prepared.json'):report['selected_prepared_sha256'],
        str(Path(report['selected_prepared'])/'demand.csv'):report['selected_demand_sha256'],
        report['network']:report['network_sha256']}
    signal_config, signal_sources = selected_signal_config(config)
    if signal_sources:
        report['vbs_config'] = str(signal_config)
    report['source_sha256'].update(signal_sources)
    frozen=original.get('diagnostic',{}).get('signal_profile')
    if frozen:
        pins=[('green_action_json','green_action_sha256')]
        if 'source_action_csv' in frozen:
            pins.append(('source_action_csv','source_action_csv_sha256'))
        for path_key,hash_key in pins:
            artifact=(ROOT/frozen[path_key]).resolve(strict=True)
            digest=sha(artifact)
            if digest!=frozen[hash_key]:
                raise ValueError('Frozen signal source changed: '+path_key)
            report['source_sha256'][str(artifact)]=digest
    report['generated_sha256']={str(output/'profile.csv'):report['profile_sha256'],
        str(output/'config.json'):hashlib.sha256(json_bytes(config)).hexdigest(),
        str(output/'native_internal_inputs.json'):hashlib.sha256(json_bytes(revised)).hexdigest(),
        str(output/'shared_approach.json'):hashlib.sha256(json_bytes(shared)).hexdigest()}
    enabled = config.get('execution',{}).get('native_signal_record',False)
    if not isinstance(enabled,bool): raise ValueError('execution.native_signal_record must be boolean')
    rule = config.get('diagnostic', {}).get('rule_profile', {})
    if rule.get('enabled'):
        if not enabled: raise ValueError('Rule baseline requires native recording')
        detector_path = (ROOT / rule['detector_mapping_json']).resolve(strict=True)
        if sha(detector_path) != rule['detector_mapping_sha256']:
            raise ValueError('Rule detector declaration changed')
        report['rule_detectors'] = json.loads(detector_path.read_text(encoding='utf-8-sig'))
        report['source_sha256'][str(detector_path)] = sha(detector_path)
    if enabled: recording_artifacts(report, output)
    return profile,comparison,report,revised,config,shared


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--selected-prepared',type=Path,required=True)
    p.add_argument('--output',type=Path)
    p.add_argument('--tuning',type=Path)
    p.add_argument('--plan',action='store_true',help='Compute all artifacts and hashes without writing')
    a=p.parse_args()
    if a.tuning:
        if not a.output: p.error('--tuning requires the intended --output directory')
        profile,comparison,report,declaration,config,shared=package(a.selected_prepared,a.tuning,a.output)
    else: profile,comparison,report=convert(a.selected_prepared)
    if a.output and not a.plan:
        recording_files = {}
        if report.get('native_signal_record'):
            planned = copy.deepcopy(report)
            recording_files = recording_artifacts(report, a.output)
            if report != planned: raise ValueError('Recording preparation changed before writing')
        a.output.mkdir(parents=True,exist_ok=False)
        (a.output/'profile.csv').write_text(profile,encoding='ascii',newline='')
        with (a.output/'comparison.csv').open('x',encoding='ascii',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(comparison[0]));writer.writeheader();writer.writerows(comparison)
        if a.tuning:
            for name,doc in [('native_internal_inputs.json',declaration),('shared_approach.json',shared),('config.json',config)]:
                (a.output/name).write_bytes(json_bytes(doc))
        for path,data in recording_files.items():
            path.parent.mkdir(parents=True,exist_ok=True)
            with path.open('xb') as handle: handle.write(data)
        (a.output/'checks.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__': main()
