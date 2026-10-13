"""Bind retained Task5 selections to the reviewed I1 source delta without relabeling them."""
import copy
import json
from pathlib import Path
from diagnostics.solo355_local_20261013.summarize_qualification import digest, read, receipt, write

ROOT=Path(__file__).resolve().parents[2]
BASE=Path('D:/VISSIM_analysis/20261013_solo355_local/task5')
FIX=BASE/'fix1'
FACTORY='evaluation/controllers/sdmpc_regional_context.py'


def main():
    old_path=FIX/'executed_validation.json'
    assert digest(old_path)=='4f94aea71f328d57f29816380dd28c7ce6f7d3fa584d0ad2b93a92884c26a032'
    original=read(old_path)
    old_pins=original['source_pins']
    assert digest(old_pins['path'])==old_pins['sha256']
    proof_path=FIX/'qualification/receipt.json'
    proof=read(proof_path)
    assert proof['passed'] and proof['freeway_old_new_graph_identical']
    assert proof['urban_selected_response_jacobian_writer_equal']
    for key in ('old_selected_response','new_selected_response','old_factory','current_factory'):
        assert digest(proof[key]['path'])==proof[key]['sha256']
    deltas=[]
    for row in read(FIX/'source_delta_before.json'):
        assert digest(row['snapshot'])==row['executed_sha256']
        before=Path(row['snapshot']).read_text(encoding='utf-8').rstrip()
        after=(ROOT/row['path']).read_text(encoding='utf-8').rstrip()
        kind='final-blank-line-only'
        if row['path']==FACTORY:
            before=before.replace('head_green_exposure_windows far_ramp_capacity_veh_h boundary_out_ramp_split',
                'head_green_exposure_windows boundary_out_ramp_split').replace(
                "frozenset(('freeway_source_boundary_observed',))",
                "frozenset(('freeway_source_boundary_observed', 'far_ramp_capacity_veh_h'))")
            kind='far-capacity-static-to-freeway-owned-and-final-blank-line'
        assert before==after,row['path']
        deltas.append(dict(row,current_sha256=digest(ROOT/row['path']),classification=kind))
    changed={r['path']:r for r in deltas}
    current=[]
    for row in read(old_pins['path'])['files']:
        path=row['package_relative_path'];sha=digest(row['path'])
        if sha!=row['sha256']:
            assert path==FACTORY
            assert row['sha256']==changed[path]['executed_sha256']
            assert sha==proof['current_factory']['sha256']
        current.append(dict(row,sha256=sha,executed_sha256=row['sha256']))
    known={r['package_relative_path'] for r in current}
    diagnostics=[r['path'] for r in deltas]+[
        'diagnostics/solo355_local_20261013/'+name for name in (
            'regional_far_context_probe.py','finalize_fix1.py','summarize_qualification.py')]
    for path in diagnostics:
        if path not in known:
            current.append(dict(path=str(ROOT/path),package_relative_path=path,sha256=digest(ROOT/path),role='qualification_diagnostic'))
    release_path=FIX/'current_release_package_source_pins.json'
    write(release_path,dict(schema='regional-current-release-pins/v1',root=str(ROOT),
        scope='Current release bytes. Original full selections retain their executed pins; I1 is covered by the explicit source delta and bounded equivalence receipt.',
        executed_source_pins=old_pins,fix_receipt=receipt(proof_path),files=sorted(current,key=lambda r:r['package_relative_path'])))
    delta_path=FIX/'source_delta.json'
    write(delta_path,dict(schema='regional-executed-to-release-delta/v1',passed=True,
        executed_validation=receipt(old_path),executed_source_pins=old_pins,current_release_pins=receipt(release_path),
        source_changes=deltas,qualification=receipt(proof_path),
        numerical_argument='Only regional context ownership changes; FW graph identical. Urban differs solely by removed far-capacity field. Named consumers install the unused legacy far function; regional scalar/AD endpoint directly returns ledger TTT with far_disabled=True. Selected-action full response/Jacobian/writer equality independently checked.',
        full_optimizations_repeated=0))
    result=copy.deepcopy(original)
    result['executed_source_pins']=old_pins
    result['source_pins']=receipt(release_path)
    result['fix1']=dict(passed=True,review_issue='I1',source_delta=receipt(delta_path),qualification=receipt(proof_path),
        focused_regression=dict(command='python -B -m unittest diagnostics.solo355_local_20261013.test_regional_context',tests=5,seconds=12.773,passed=True),
        full_optimizations_repeated=0)
    for mode,row in result['modes'].items():
        full=row['full_selection']
        assert digest(full['evidence_path'])==full['evidence_sha256']
        full['executed_source_binding']='Original Task5 selection bytes (886f82b implementation); not rerun after I1'
        full['current_release_equivalence']=receipt(delta_path)
        row['far_producer_noninterference']=mode=='urban_only'
        row['far_producer_own_sensitivity']=mode=='freeway_only'
    result['limitations'].append('Full selections retain original executed sources. Current release is bound by the explicit I1 ownership delta, FW complete-graph identity and old/new urban selected-action response/Jacobian/writer equivalence; no repeated full optimization.')
    write(ROOT/'diagnostics/solo355_local_20261013/validation.json',result)
    required_path=ROOT/'diagnostics/solo355_local_20261013/required_source_inputs.json'
    required=read(required_path)
    required['executed_canonical_package_pins']=old_pins
    required['canonical_package_pins']=receipt(release_path)
    required['fix1_source_delta']=receipt(delta_path)
    write(required_path,required)
    print(json.dumps(dict(passed=True,current_release_files=len(current),source_delta=str(delta_path),validation_sha256=digest(ROOT/'diagnostics/solo355_local_20261013/validation.json'))))


if __name__=='__main__':
    main()