"""Bounded arithmetic microbenchmark; no simulation or optimizer invocation."""
import builtins
import ctypes
import gc
import hashlib
import json
from pathlib import Path
import statistics
import time

from evaluation.controllers import sdmpc_tangent_reverse as ad
from evaluation.controllers import sdmpc_tangent_summary as summary
from stock_sum_candidate import stock_sum


def one(fn, size, repeat):
    trace = ad.Trace([1., 1.])
    a = ad.Dual(1., {0: 1.}, trace)
    b = ad.Dual(1e-200, {1: 1.}, trace)
    items = ([0., a, b, 0.025] * ((size+3)//4))[:size]
    started = time.perf_counter()
    for _ in range(repeat):
        result = fn(items)
    elapsed = time.perf_counter()-started
    witness = dict(value=ad.primal(result), node=result.node, support=result.support,
                   arrays=[hashlib.sha256(x.tobytes()).hexdigest()
                           for x in (trace.p1, trace.p2, trace.w1, trace.w2)],
                   counts=dict(trace.counts))
    return elapsed, witness


def main():
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
    summary.install_fused_operations()
    ad.Trace.operation = summary.checked_operation
    out = Path(__file__).with_name('stock_microbenchmark.json')
    assert not out.exists(), 'Preserve prior evidence'
    started = time.perf_counter()
    one(stock_sum, 64, 1)  # Separate JIT warm-up from steady measurements.
    warmup = time.perf_counter()-started
    rows = []
    for size in (64, 512, 4096, 16384):
        repeat = max(8, 65536//size)
        samples = dict(original=[], candidate=[])
        for trial in range(3):
            results = {}
            for name, fn in ((('original', builtins.sum), ('candidate', stock_sum))
                             if trial % 2 == 0 else
                             (('candidate', stock_sum), ('original', builtins.sum))):
                gc.collect()
                elapsed, witness = one(fn, size, repeat)
                samples[name].append(elapsed)
                results[name] = witness
            assert results['original'] == results['candidate']
        medians = {k: statistics.median(v) for k, v in samples.items()}
        rows.append(dict(terms=size, repetitions=repeat, samples_sec=samples,
                         median_sec=medians, speedup=medians['original']/medians['candidate'],
                         identical_value_and_tape=True))
    out.write_text(json.dumps(dict(scope='arithmetic only; not full decision timing',
        compiled_warmup_sec=warmup, rows=rows, native_runs=0, optimizer_runs=0),
        indent=2)+'\n', encoding='utf8')
    print(out.read_text(encoding='utf8'))


if __name__ == '__main__':
    main()
