"""Clock-only timing/equality batch; no optimizer, endpoint or model rollout."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import pickle
import statistics
import struct
import time

from diagnostics.test_signal_clock_cache import ROOT, fixture, actual, proposal, reference, CONFIG, CONTRACT, input_path


def run():
    runtime, base = fixture(); cfg = runtime[0]
    paths = list((ROOT/'evaluation/controllers').glob('*.py')) + [
             CONFIG, ROOT/CONTRACT, input_path('state_000900.json'),
             input_path('action_000750.json'), input_path('action_000900.json'),
             ROOT/'diagnostics/test_signal_clock_cache.py',
             ROOT/'diagnostics/test_head_service_resources.py',
             ROOT/'diagnostics/fixtures/signal_clock_dd13e08.py',
             ROOT/'evaluation/controllers/signal_actuation_contract.py',
             ROOT/'evaluation/controllers/offset_promotion.py',
             ROOT/'diagnostics/signal_clock_cache_proposal.py', Path(__file__)]
    before_hash = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    queries = []
    for offset in (0., 10., -10.):
        action = base.copy(); action.offsets = dict.fromkeys(cfg.network.signals, offset)
        for signal in cfg.network.signals:
            for phase in actual.PHASES:
                for step in range(180,210):
                    queries.append((action,cfg,{'phase':signal+'_'+phase},step))
    original_inputs = pickle.dumps(queries)
    reference_values = tuple(reference.phase_fraction(*query) for query in queries)
    expected_hash = hashlib.sha256(b''.join(struct.pack('!d',v) for v in reference_values)).hexdigest()
    rows = {}
    methods = {'original': actual.phase_fraction, 'finite_only': proposal.finite_only,
               'validated_clock_full_check': proposal.validated_clock_full_check,
               'validated_clock_and_finite': proposal.validated_clock}
    # Rotate order across samples to reduce a consistent first/last timing bias.
    names = list(methods)
    for sample in range(len(methods)):
        for name in names[sample:]+names[:sample]:
            function = methods[name]
            proposal.clear(); actual._phase_windows.cache_clear()
            started = time.perf_counter()
            cold = tuple(function(*query) for query in queries)
            cold_sec = time.perf_counter()-started
            started = time.perf_counter()
            for _ in range(3):
                warm = tuple(function(*query) for query in queries)
            warm_sec = time.perf_counter()-started
            assert pickle.dumps(cold)==pickle.dumps(reference_values)
            assert pickle.dumps(warm)==pickle.dumps(reference_values)
            rows.setdefault(name,[]).append({'cold_sec':cold_sec,'warm_3passes_sec':warm_sec,
                'clock_cache':proposal.stats(),'phase_windows':actual._phase_windows.cache_info()._asdict()})
    unchanged = original_inputs == pickle.dumps(queries)
    assert unchanged
    report = {'schema':'selected-signal-clock-cache-benchmark/v1',
        'scope':'Isolated selected-clock calls on current actual 900 configuration/action with offset-only copies. Repeated query workload; not parent/worker or full-MPC wall speedup.',
        'queries_per_pass':len(queries),'signals':len(cfg.network.signals),'green_vectors':'actual action held',
        'offsets':[0.,10.,-10.],'absolute_steps':[180,209],'samples':rows,
        'exact_output_sha256':expected_hash,'input_pickle_sha256':hashlib.sha256(original_inputs).hexdigest(),
        'input_pickle_unchanged':unchanged,
        'source_sha256':before_hash,'source_changes':[str(p.relative_to(ROOT)) for p in paths if hashlib.sha256(p.read_bytes()).hexdigest()!=before_hash[str(p.relative_to(ROOT))]]}
    report['median'] = {name:{'cold_sec':statistics.median(v['cold_sec'] for v in values),
        'warm_3passes_sec':statistics.median(v['warm_3passes_sec'] for v in values)} for name,values in rows.items()}
    for name,row in report['median'].items():
        row['warm_speed_ratio_vs_original']=report['median']['original']['warm_3passes_sec']/row['warm_3passes_sec']
    (ROOT/'diagnostics/signal_clock_cache_benchmark.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'queries':len(queries),'median':report['median'],'source_changes':report['source_changes']},indent=2))
    return report


if __name__=='__main__':
    run()
