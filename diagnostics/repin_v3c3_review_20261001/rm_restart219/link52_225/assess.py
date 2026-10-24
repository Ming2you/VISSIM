"""Reuse saved-pair validation, then compare physical52 head response. No rollout."""
import gzip
import hashlib
import importlib.util
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
I = ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926'

def read(p): return json.loads(p.read_bytes())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    # Use the established command, inventory, native outcome and receipt checks.
    spec = importlib.util.spec_from_file_location('review223_assessment', HERE.parent/'heldout223/assess.py')
    check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(check)
    check.HERE = HERE
    check.main()
    result = read(HERE / 'assessment.json')
    protocol = read(HERE / 'protocol.json')
    init = read(HERE / 'initialization_verification.json')
    assert init['status'] == 'PASS'
    native_path = ROOT / 'diagnostics/repin_v3c3_review_20261001/corrected_s47_neighbors/arrival10681_native_paths.json'
    native = read(native_path)
    result['input_sha256'][str(native_path)] = sha(native_path)
    sources = ('movement:SC1004_E_SC1005_to_W', 'movement:SC1004_E_SC107_to_W')
    response = {}
    for model, item in protocol['models'].items():
        folder = I / ('closedloop_recorded2700_select_check_trace10681_' + item['label'])
        per_case = {}
        for case in ('held_actual','selected'):
            native_case = 'hold' if case == 'held_actual' else 'selected'
            trace = json.loads(gzip.decompress((folder/(case+'_RM_C10681_trace.json.gz')).read_bytes()))
            up = trace['upstream_diagnostics']
            assert set(up['head_resources']['10629']['spec']['members']) == {s[9:] for s in sources}
            assert up['head_resources']['10629']['installed_pool']['service_veh_h'] == 4080.
            windows = []
            for j, start in enumerate((2700,2850,3000)):
                flows = [t for t in up['transfers'] if start <= t['start_sec'] < start+150 and t['source'] in sources]
                assert all(t['target']=='storage:SC1004_W_out' for t in flows)
                by_source = {s:math.fsum(t['vehicles'] for t in flows if t['source']==s) for s in sources}
                actual = sum(native['arms'][native_case][j]['head_counts_all_destinations'].get('52:'+str(l),0) for l in (1,2,3))
                predicted = sum(by_source.values())
                windows.append(dict(start_sec=start, head52_predicted=predicted, head52_native=actual,
                    error=predicted-actual, by_source=by_source,
                    start_queues={s:up['states'][j]['queues'][s[9:]] for s in sources},
                    end_queues={s:up['states'][j+1]['queues'][s[9:]] for s in sources}))
            per_case[case] = windows
        response[model] = dict(cases=per_case,
            model_head_response=[b['head52_predicted']-a['head52_predicted'] for a,b in zip(per_case['held_actual'],per_case['selected'])],
            native_head_response=[b['head52_native']-a['head52_native'] for a,b in zip(per_case['held_actual'],per_case['selected'])])
    result.update(status='COMPLETE_PHYSICAL52_BOUNDED_RESPONSE_NOT_GAIN_QUALIFICATION',
        forecasts=2, reused_predictions=2, total_predictions_compared=4,
        new_prediction_wall_sec=sum(c['wall_sec'] for c in result['models']['candidate']['cases'].values()),
        initialization_verification=init, head52_response=response,
        route_coverage=init['route_coverage'])
    result['limitations'] += [
        'Candidate corrects physical52 current known destinations, existing physical ETA and native1123 primary-origin future prior; SC107 future prior remains unchanged.',
        'Only two new candidate forecasts. Two REVIEW223 native1125 forecasts are reused verbatim.',
        'Initial inventories and physical head capacity are preserved; this is not a receiving-capacity or merge-parameter calibration.',
        'Head52 native comparison uses observed signal heads on lanes1-3; lane4 left-turn is excluded.']
    (HERE/'assessment.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=result['status'],new_prediction_wall_sec=result['new_prediction_wall_sec'],
        head52={m:{c:[round(w['head52_predicted'],4) for w in r['cases'][c]] for c in r['cases']} for m,r in response.items()},
        omega={m:r['delta_omega'] for m,r in result['models'].items()},
        ramp10681={m:{c:r['cases'][c]['ramps']['RM_C10681'] for c in r['cases']} for m,r in result['models'].items()})))

if __name__ == '__main__': main()
