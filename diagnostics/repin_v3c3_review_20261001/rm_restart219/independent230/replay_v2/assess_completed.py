"""Reuse the fixed seed71 assessment after four completed offline replays."""
import hashlib
import importlib.util
import json
from pathlib import Path

D = Path(__file__).resolve().parent
ROOT = D.parents[4]
load = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    protocol = load(D / 'protocol.json')
    output = Path(protocol['output'])
    report = load(output / 'summary.json')
    assert tuple(report['results']) == ('held_actual', 'rm', 'vsl', 'both')
    assert load(D / 'after71.json')['new_forecasts'] == 4
    assert load(output / 'ramp_response_audit.json')['fzp_rescans'] == 0
    pins = {str(ROOT / p): value for p, value in protocol['source_sha256'].items()}
    pins[protocol['driver']] = protocol['helper_sha256']
    for path, expected in pins.items():
        assert sha(Path(path)) == expected, path
    for key in ('native_summary', 'observation_reuse', 'STOP'):
        assert sha(Path(protocol[key]['path'])) == protocol[key]['sha256']
    assert sha(D / 'candidate_config.json') == protocol['config_sha256']
    assert all(load(Path(protocol['native_summary']['path']))['arms'][a]['native_execution_passed']
               for a in ('nc', 'rm', 'vsl', 'both'))
    # The established assessment accepts these manifests; no native data is altered.
    documents = {
        'plan.json': dict(materiality_veh_h=protocol['materiality_veh_h'],
                          old_STOP=protocol['STOP'], model_pins=pins),
        'postprocess_plan.json': dict(source_pins=pins, config_sha256=protocol['config_sha256'],
                                     forecast_output=str(output)),
        'postprocess_status.json': dict(phase='complete_pending_assessment',
                                       four_forecasts_complete=True, cached_ramp_audit_complete=True),
    }
    for name, value in documents.items():
        path = D / name
        assert not path.exists(), path
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    source = ROOT / 'diagnostics/repin_v3c3_review_20261001/independent_s71_84/assess.py'
    spec = importlib.util.spec_from_file_location('seed71_existing_assessment', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.D = D
    module.main()
    result = load(D / 'assessment.json')
    result.update(model='current225', predictions_in_this_experiment=4,
                  previously_viewed_validation_seed=True, blind_validation=False,
                  outcome_calibration_calls=0, assessment_source_sha256=sha(source),
                  diagnostic_config_change=protocol['diagnostic_only_config_change'])
    result['limitations'][0] = ('Previously viewed seed71: four fixed-command forecasts from the same '
        '2250-second state. Not a new blind test, calibration, optimizer choice, or 9000-second validation.')
    (D / 'assessment.json').write_text(json.dumps(result, ensure_ascii=False, indent=2,
                                                allow_nan=False) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
