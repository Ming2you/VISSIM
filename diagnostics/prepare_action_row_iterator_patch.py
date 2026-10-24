"""Prepare an unapplied extraction of the canonical CSV row expressions.

No adapter or traffic-model imports. The output contains a diff, not an adapter
copy. Runtime callbacks remain in the existing writer; the iterator accepts
their already resolved values and performs no allocation or file operations.
"""
from __future__ import annotations

import ast
import difflib
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'evaluation/controllers/vissim_stackelberg_adapter.py'
OUT = ROOT / 'diagnostics/action_row_iterator_preparation_v1'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def prepare(source: str) -> tuple[str, str, str]:
    tree = ast.parse(source)
    if any(isinstance(n, ast.FunctionDef) and n.name == 'iter_action_csv_rows' for n in tree.body):
        raise ValueError('Row iterator already exists; do not stack this proposal')
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'write_action_csv')
    lines = source.splitlines(keepends=True)
    original = ''.join(lines[node.lineno - 1:node.end_lineno])
    signature = original[:original.index(') -> None:') + len(') -> None:')]
    loop = original[original.index('        for seg in mapping["segments"]:'):]
    loop = ''.join(line[4:] if line.startswith('    ') else line for line in loop.splitlines(keepends=True))
    loop = loop.replace('for seg in mapping["segments"]:', 'for segment_index, seg in enumerate(mapping["segments"]):', 1)
    old_vsl = ('        model_link, idx = _segment_model_coordinates(str(segment_id), seg)\n'
               '        value = nearest(segment_vsl_func(control, model_link, idx, cfg), vsl_set)')
    if old_vsl not in loop:
        raise ValueError('Canonical VSL row expression changed')
    loop = loop.replace(old_vsl, '        value = nearest(segment_vsl_values[segment_index], vsl_set)', 1)
    for old in ('real_world_ramp_meter_actions(control, cfg, actuation, mapping)',
                'physical_ramp_actions(control, cfg, actuation)'):
        if loop.count(old) != 1:
            raise ValueError('Canonical meter branch changed')
        loop = loop.replace(old, 'ramp_actions', 1)
    if loop.count('writer.writerow(') != 5:
        raise ValueError('Unexpected canonical row call count')
    loop = loop.replace('writer.writerow(', 'yield (')
    iterator = '''def iter_action_csv_rows(
    control,
    cfg,
    mapping: dict[str, Any],
    segment_vsl_values: Sequence[float],
    ramp_actions: Mapping[str, Mapping[str, Any]],
    metadata: dict[str, Any],
    actuation: Mapping[str, Any],
    signal_group_plan_table: Mapping[str, Any] | None = None,
    offset_writer: str = offset_promotion.WRITER_INTENT_ONLY,
):
    """Yield canonical rows from resolved physical values, without allocation/IO.

    segment_vsl_values follows mapping['segments'] exactly. ramp_actions is the
    result of the existing real-world (or legacy) meter conversion on the same
    finalized action/context. Callers own that preparation and its side effects.
    Every column except metadata is physical CSV content; metadata retains the
    existing provenance serialization and is not a physical-command identity.
    Inputs must remain fixed for the lifetime of this synchronous iterator.
    """
    signal_actuation_contract.validate_writer(control, cfg, signal_group_plan_table, offset_writer)
    if len(segment_vsl_values) != len(mapping["segments"]):
        raise ValueError("Resolved VSL values must cover the ordered segment mapping")
    if isinstance(mapping.get("ramp_meters"), list) and mapping.get("ramp_meters"):
        expected_ramps = tuple(dict.fromkeys(
            str(meter.get("id", meter.get("control_id", "")))
            for meter in mapping["ramp_meters"] if isinstance(meter, Mapping)
            and str(meter.get("id", meter.get("control_id", "")))
        ))
    else:
        expected_ramps = ("D", "F")
    if tuple(ramp_actions) != expected_ramps:
        raise ValueError("Resolved meters must cover the ordered physical meter mapping")
    vsl_set = [float(v) for v in cfg.freeway_follower.vsl_set]
    if 120.0 not in vsl_set:
        vsl_set = sorted(set(vsl_set + [120.0]))
    csv_metadata = _action_csv_metadata(metadata)
'''+loop
    writer = signature + '''
    # Keep runtime callback effects at the existing writer boundary. The row
    # iterator itself never invokes the global VSL hook or meter allocator.
    signal_actuation_contract.validate_writer(control, cfg, signal_group_plan_table, offset_writer)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        _action_csv_metadata(metadata)  # Preserve metadata rejection before callbacks.
        fields = list(action_csv_schema.ACTION_CSV_FIELDS)
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        segment_vsl_values = []
        for seg in mapping["segments"]:
            model_link, idx = _segment_model_coordinates(str(seg["segment_id"]), seg)
            segment_vsl_values.append(segment_vsl_func(control, model_link, idx, cfg))
        if isinstance(mapping.get("ramp_meters"), list) and mapping.get("ramp_meters"):
            ramp_actions = real_world_ramp_meter_actions(control, cfg, actuation, mapping)
        else:
            ramp_actions = physical_ramp_actions(control, cfg, actuation)
        for row in iter_action_csv_rows(
            control, cfg, mapping, segment_vsl_values, ramp_actions, metadata,
            actuation, signal_group_plan_table, offset_writer,
        ):
            writer.writerow(row)
'''
    after = ''.join(lines[:node.lineno - 1]) + iterator + '\n\n' + writer + ''.join(lines[node.end_lineno:])
    ast.parse(after)
    return after, original, iterator + '\n\n' + writer


def main():
    raw = SOURCE.read_bytes()
    source = raw.decode('utf-8-sig').replace('\r\n', '\n')
    after, original, methods = prepare(source)
    OUT.mkdir(parents=True, exist_ok=True)
    patch = ''.join(difflib.unified_diff(source.splitlines(keepends=True), after.splitlines(keepends=True),
                                       fromfile='a/evaluation/controllers/vissim_stackelberg_adapter.py',
                                       tofile='b/evaluation/controllers/vissim_stackelberg_adapter.py'))
    (OUT/'action_row_iterator.patch').write_bytes(patch.encode('utf-8'))
    # Exact original method only, with no imports/bootstrap or adapter copy.
    (OUT/'original_write_action_csv.py').write_bytes(original.encode('utf-8'))
    (OUT/'proposed_writer_methods.py').write_bytes(methods.encode('utf-8'))
    manifest = {'schema':'action-row-iterator-proposal/v1', 'applied':False,
                'source_path':SOURCE.relative_to(ROOT).as_posix(), 'source_sha256':sha(raw),
                'expected_after_lf_sha256':sha(after.encode('utf-8')),
                'files_sha256':{p.name:sha(p.read_bytes()) for p in OUT.iterdir() if p.suffix in ('.patch','.py')},
                'clock_source_is_not_a_patch_or_test_target':True,
                'scope':'Pure resolved-value row iterator; runtime preparation remains in canonical writer'}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    if SOURCE.read_bytes() != raw:
        raise RuntimeError('Production source changed while preparing proposal')
    print(json.dumps(manifest,indent=2))


if __name__ == '__main__':
    main()
