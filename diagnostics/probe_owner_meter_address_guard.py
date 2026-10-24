"""Bounded address-only fixture, with no model/adapter import or rollout.

Only the actual writer's two pure mapping functions and the written test's
address-fixture setup are compiled from AST. This is not a model integration
test and does not stand in for the later full ControlAction test suite.
"""
import ast
import copy
import csv
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from typing import Any, Mapping
import unittest

ROOT = Path(__file__).resolve().parents[1]


def module(name, text):
    result = ModuleType(name)
    sys.modules[name] = result
    exec(compile(text, name, 'exec'), result.__dict__)
    return result


def run():
    output = ROOT / 'diagnostics/owner_meter_address_guard_validation.json'
    if output.exists(): raise ValueError('Preserve completed fixture result')
    previous = ROOT / 'diagnostics/joint_owner_addresses_before_meter_guard.patch'
    prior_bytes = previous.read_bytes()
    if hashlib.sha256(prior_bytes).hexdigest() != '145ff56a0ed97af6102d8d29ccc2b5b1322118fadca697b3c4a0e48b88f121c8':
        raise ValueError('Prior proposal patch changed')
    old_text = ''.join(line[1:] for line in prior_bytes.decode().splitlines(keepends=True) if line.startswith('+') and not line.startswith('+++'))
    if hashlib.sha256(old_text.encode()).hexdigest() != 'caab877adbf569ed374223a580cab9350b416bbb832fb8e502fb4c85452a4fe2':
        raise ValueError('Prior proposal source reconstruction changed')
    old = module('_owner_address_prior', old_text)
    path = ROOT / 'diagnostics/joint_owner_addresses_candidate.py'
    new = module('_owner_address_current', path.read_text(encoding='utf-8'))
    adapter = ROOT / 'evaluation/controllers/vissim_stackelberg_adapter.py'
    tree = ast.parse(adapter.read_text(encoding='utf-8'))
    pure = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in ('_as_float', '_segment_dsd_controls')]
    if len(pure) != 2: raise ValueError('Actual writer helper boundary changed')
    env = {'Any': Any, 'Mapping': Mapping}
    exec(compile(ast.Module(body=pure, type_ignores=[]), str(adapter), 'exec'), env)
    callback = env['_segment_dsd_controls']
    test_path = ROOT / 'diagnostics/test_joint_owner_addresses.py'
    test_tree = ast.parse(test_path.read_text(encoding='utf-8'))
    fixture = next(node for node in test_tree.body if isinstance(node, ast.ClassDef) and node.name == 'OwnerAddressesTests')
    fixture.body = [node for node in fixture.body if isinstance(node, ast.FunctionDef) and node.name in ('setUp', 'build')]
    if len(fixture.body) != 2: raise ValueError('Written address fixture boundary changed')
    setup = {'ROOT': ROOT, 'SimpleNamespace': SimpleNamespace, 'json': json, 'copy': copy, 'unittest': unittest, 'proposed': new, '_segment_dsd_controls': callback}
    exec(compile(ast.Module(body=[fixture], type_ignores=[]), str(test_path), 'exec'), setup)
    fixture = setup['OwnerAddressesTests'](); fixture.setUp()
    before = copy.deepcopy((fixture.mapping, fixture.plan))
    try:
        old.build_ownership(fixture.cfg, fixture.mapping, fixture.plan, segment_dsd_controls=callback)
        prior_actual_error = None
    except ValueError as exc:
        prior_actual_error = str(exc)
    current = fixture.build()
    if before != (fixture.mapping, fixture.plan): raise AssertionError('Actual mapping/plan mutated')
    actual_csv = ROOT / 'diagnostics/area_production_preflight/wu-link_t900_beta300_20260910T032525335593Z/action.csv'
    with actual_csv.open(encoding='utf-8-sig', newline='') as stream: written = list(csv.DictReader(stream))
    native = []
    for row in written:
        if row['kind'] == 'vsl': key = ('dsd', str(int(row['dsd_no'])))
        elif row['kind'] == 'signal': key = ('signal_sc', str(int(row['sc_no'])))
        elif row['kind'] == 'signal_sg': key = ('signal_sg', f"{int(row['sc_no'])}:{int(row['dsd_no'])}")
        elif row['kind'] == 'ramp_meter': key = ('signal_sg', f"{int(row['sc_no'])}:1")
        else: raise AssertionError('Unknown actual CSV write kind')
        native.append(key)
    if len(native) != len(set(native)) or set(native) != {(w[0], w[1]) for w in current.writes}:
        raise AssertionError('Actual CSV/native owner addresses differ')
    # Isolate the peer meter counterexample from the independently discovered
    # old red_only metadata bug; original files and actual-plan test stay intact.
    fixture.plan = copy.deepcopy(before[1])
    for node in fixture.plan['controllers'].values(): node['red_only_signal_groups'] = []
    rows = []
    for case in ('sg2_only', 'duplicate_sc_sg2', 'duplicate_sc_sg1'):
        fixture.mapping = copy.deepcopy(before[0])
        if case == 'sg2_only': fixture.mapping['ramp_meters'][0]['sg_no'] = 2
        else:
            fixture.mapping['ramp_meters'][1]['sc_no'] = fixture.mapping['ramp_meters'][0]['sc_no']
            fixture.mapping['ramp_meters'][1]['sg_no'] = 2 if case.endswith('sg2') else 1
        outcomes = {}
        for name, helper in (('prior', old), ('current', new)):
            try:
                helper.build_ownership(fixture.cfg, fixture.mapping, fixture.plan, segment_dsd_controls=callback)
                outcomes[name] = {'accepted': True}
            except ValueError as exc:
                outcomes[name] = {'accepted': False, 'error': str(exc)}
        if outcomes['current']['accepted']: raise AssertionError('Invalid meter accepted')
        if case != 'duplicate_sc_sg1' and not outcomes['prior']['accepted']:
            raise AssertionError('Prior counterexample did not reproduce')
        rows.append({'case': case, **outcomes})
    forbidden = [name for name in sys.modules if name == 'src' or name.startswith(('src.', 'evaluation.controllers'))]
    if forbidden: raise AssertionError(f'Model/controller import occurred: {forbidden}')
    result = {'schema': 'owner-meter-address-guard-validation/v1', 'passed': True,
              'actual_mapping_and_plan_unmutated': True, 'actual_csv_native_addresses_exact': True,
              'prior_actual_plan_rejected': prior_actual_error,
              'meter_counterexample_fixture': 'Omit unused red_only metadata in both proposal versions solely to isolate meter-address guard; actual CSV proof above uses full original selected plan.',
              'owners': len(current.owners), 'native_write_addresses': len(current.writes),
              'invalid_cases': rows, 'model_imports': 0, 'model_execution': 0, 'com_execution': 0,
              'scope': 'Only pure owner helper and actual writer mapping functions; actual ControlAction test suite remains unexecuted.',
              'sha256': {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in (path, adapter, previous, test_path, actual_csv)}}
    output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    return result


if __name__ == '__main__': print(json.dumps(run(), indent=2))
