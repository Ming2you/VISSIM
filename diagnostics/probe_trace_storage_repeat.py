"""Bounded storage-only repeated-current-value experiment; no model execution."""
from __future__ import annotations
import argparse
import gc
import hashlib
import json
from pathlib import Path
import tempfile
import time
import tracemalloc
from diagnostics.evaluation_trace_storage import Store,DiskRows

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'diagnostics/evaluation_trace_actual_local_20260910T042546182386Z/local_evaluation_50060.json'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('output');parser.add_argument('--count',type=int,default=12)
    parser.add_argument('--memory',action='store_true');args=parser.parse_args()
    output=(ROOT/args.output).resolve()
    if not output.is_relative_to(ROOT/'diagnostics') or output.exists():raise ValueError('Fresh diagnostics result required')
    raw=SOURCE.read_bytes();state=json.loads(raw)['operational'][1]['state']
    memory=[]
    if args.memory:tracemalloc.start()
    with tempfile.TemporaryDirectory(prefix='storage_repeat_',dir=ROOT/'diagnostics') as temporary:
        store=Store(Path(temporary)/'trace.sqlite');rows=DiskRows(store,'local_rows')
        start=time.perf_counter()
        for i in range(args.count):
            rows.append({'ordinal':i,'call':0,'parent_call':None,'base_call':0,'event':'candidate',
                         'kind':'storage_only','score':{'float_hex':float(i).hex()},'operational_after':state})
            if args.memory and i in (0,args.count//2,args.count-1):
                gc.collect();memory.append({'rows':i+1,'current_peak':tracemalloc.get_traced_memory()})
        elapsed=time.perf_counter()-start;store.conn.commit()
        snapshots=store.conn.execute('SELECT COUNT(*) FROM snapshots').fetchone()[0]
        nodes=store.conn.execute('SELECT COUNT(*) FROM nodes').fetchone()[0]
        cache=store.cache_bytes;bytes_on_disk=store.path.stat().st_size
        store.close()
    if args.memory:tracemalloc.stop()
    result={'scope':'Same already canonical actual-local snapshot, changing synthetic score; storage only.',
            'iterations':args.count,'elapsed_sec':elapsed,'memory_instrumented':args.memory,'python_memory':memory,
            'node_count':nodes,'snapshot_count':snapshots,'cache_bytes':cache,'database_bytes':bytes_on_disk,
            'input_sha256':hashlib.sha256(raw).hexdigest(),
            'storage_source_sha256':hashlib.sha256((ROOT/'diagnostics/evaluation_trace_storage.py').read_bytes()).hexdigest(),
            'producer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'model_executions':0}
    output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps(result))


if __name__=='__main__':main()
