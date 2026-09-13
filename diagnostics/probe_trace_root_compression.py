"""Bounded synthetic storage experiment; no actual trace or traffic data read."""
import hashlib
import json
from pathlib import Path
import tempfile
import time

from diagnostics import evaluation_trace as base
from diagnostics import evaluation_trace_storage as legacy
from diagnostics.prepare_trace_root_compression_patch import proposal_module,ROOT,SOURCE


def run():
    output=ROOT/'diagnostics/trace_root_compression_synthetic.json'
    if output.exists():raise ValueError('Preserve completed synthetic report')
    production_before=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    shared={'cfg':{'lanes':list(range(2500)),'fields':{str(i):[i,i/7.,-0.0] for i in range(80)}},
            'state':{'stocks':{str(i):i/3. for i in range(80)}},'text':'관측값'}
    # Identical pre-canonicalized inputs isolate only storage work. Python
    # canonical() recursion is explicitly outside these timings.
    values=[base.canonical({'operational':shared,'iteration':i}) for i in range(40)]
    keys=[base.digest(x) for x in values]
    rows=[]
    with tempfile.TemporaryDirectory(prefix='probe_root_blob_',dir=ROOT/'diagnostics') as tmp:
        for name,module in (('dag',legacy),('root_zlib',proposal_module())):
            path=Path(tmp)/(name+'.sqlite');store=module.Store(path)
            try:
                cpu=time.process_time();wall=time.perf_counter()
                received=[store.put(value) for value in values]
                store.conn.commit()
                write_cpu=time.process_time()-cpu;write_wall=time.perf_counter()-wall
                if received!=keys:raise AssertionError('Snapshot key changed')
                cpu=time.process_time();wall=time.perf_counter()
                for value,key in zip(values,keys):
                    if module.dump(store.get(key))!=legacy.dump(value):raise AssertionError('Expanded value changed')
                read_cpu=time.process_time()-cpu;read_wall=time.perf_counter()-wall
                rows.append({'storage':name,'write_process_cpu_sec':write_cpu,'write_wall_sec':write_wall,
                    'verified_read_process_cpu_sec':read_cpu,'verified_read_wall_sec':read_wall,
                    'sqlite_bytes':path.stat().st_size,'snapshot_count':len(keys),
                    'descriptor_bytes':store.conn.execute('SELECT SUM(length(descriptor)) FROM snapshots').fetchone()[0],
                    'node_payload_bytes':store.conn.execute('SELECT COALESCE(SUM(length(payload)),0) FROM nodes').fetchone()[0],
                    'cache_bytes':store.cache_bytes,'cache_limit_bytes':store.cache_limit,
                    'expanded_bytes_and_keys_exact':True})
            finally:store.close()
    report={'schema':'trace-root-compression-synthetic/v1','rows':rows,
        'values':len(values),'largest_canonical_root_bytes':max(len(legacy.dump(v).encode()) for v in values),
        'key_sequence_sha256':base.digest(keys),'production_before':production_before,
        'production_after':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'limits':['Synthetic storage-only workload; no traffic model or current/large trace database read.',
                  'Canonical object traversal and caller digest costs are excluded; this cannot predict full-trace speedup.',
                  'Another actual trace was active; wall figures are not an isolated normal performance benchmark.',
                  'Cache size is a configured bound, not a measurement of whole-process peak RSS.']}
    if report['production_before']!=report['production_after']:raise AssertionError('Production changed')
    output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


if __name__=='__main__':print(json.dumps(run()))
