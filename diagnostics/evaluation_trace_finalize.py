"""Shared trace writer with an explicit owner for profile or monitoring hooks."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys


def finish(recorder, *, backend=None):
    if recorder.finished:return
    recorder.finished=True
    if backend is None:
        if sys.getprofile()==recorder.profile:sys.setprofile(None)
        else:recorder.errors.append({'event':'profile_hook_replaced'})
    else:
        # The backend validates its real registered callbacks/events and removes
        # them. It must never install another hook just to satisfy a writer test.
        backend.close_for_writer()
    recorder.stream.close()
    from diagnostics import evaluation_trace as base
    from diagnostics.decision_profile import memory_counters
    changed=[p for p,h in recorder.provenance['source_files'].items()
             if not Path(p).is_file() or hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h]
    input_changes=[p for p,h in recorder.provenance['input_files'].items()
                   if not Path(p).is_file() or hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h]
    document={**recorder.provenance,'completed':True,
              'valid':not recorder.errors and not recorder.frames and not changed and not input_changes,
              'errors':recorder.errors,'unmatched_calls':len(recorder.frames),'source_changes':changed,
              'input_changes':input_changes,'contexts':recorder.contexts,'rows':recorder.rows,
              'memory':memory_counters(),
              'timing_scope':'Trace-overhead-inclusive selected main-thread stages; process CPU includes all threads; nested/process wall times are not additive.',
              'coverage':{'leader_proxy_full_pfo':True,'logical_follower_returns':True,
                          'price_tasks_and_leaves':True,'executed_endpoint_interval_controls':True,
                          'all_agent_local_candidates':False}}
    if recorder.storage is not None:
        from diagnostics.evaluation_trace_storage import compact_document, NormalizedRows, streaming_hash
        recorder.storage.conn.commit()
        document['comparison'] = NormalizedRows(recorder.storage.path,'base_rows')
        document['comparison_sha256'] = streaming_hash(document['comparison'])
        compact = compact_document(document,recorder.storage)
        recorder.storage.close()
        compact['storage'].update(recorder.storage.descriptor())
        with recorder.stem.with_suffix('.jsonl').open('rb') as stream:
            compact['jsonl_sha256'] = hashlib.file_digest(stream,'sha256').hexdigest()
        recorder.stem.with_suffix('.json').write_text(base._dump(compact)+'\n',encoding='utf-8')
    else:
        document['comparison'] = base.normalized_process(recorder.rows)
        document['comparison_sha256']=base.digest(document['comparison'])
        recorder.stem.with_suffix('.json').write_text(base._dump(document)+'\n',encoding='utf-8')
    return document
