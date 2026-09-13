"""Re-encode bounded completed legacy files without executing their model.

This migration reader explicitly caps each old whole-JSON document. V3 runtime
and collection never read such large inline process JSON bodies.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from diagnostics import evaluation_trace as base
from diagnostics.evaluation_trace_storage import Store, DiskRows, DiskMap, compact_document, collect
from diagnostics.evaluation_trace_local import collection

ROOT = Path(__file__).resolve().parents[1]


def reencode(source, output, *, max_document_bytes=32*1024*1024):
    source, output = Path(source).resolve(), Path(output).resolve()
    if not output.is_relative_to(ROOT/'diagnostics') or output.exists():
        raise ValueError('Require a fresh diagnostics output directory')
    output.mkdir()
    pins={}
    def read(path):
        if path.stat().st_size > max_document_bytes: raise ValueError('Legacy document exceeds bounded migration limit')
        raw=path.read_bytes(); pins[str(path)]=hashlib.sha256(raw).hexdigest()
        return raw
    for path in sorted(source.glob('evaluation_*.json')):
        if path.name.endswith('.started.json'):
            (output/path.name).write_bytes(read(path)); continue
        doc=json.loads(read(path)); pid=doc['pid']
        if doc.get('storage'): raise ValueError('Legacy source required')
        store=Store(output/f'evaluation_{pid}.sqlite')
        try:
            local_path=source/f'local_evaluation_{pid}.json'
            pairs=[(doc,False,path.name)]
            if local_path.exists(): pairs.append((json.loads(read(local_path)),True,local_path.name))
            compact_docs=[]
            for current,is_local,name in pairs:
                tables={'rows':'local_rows' if is_local else 'base_rows',
                        'contexts':'local_contexts' if is_local else 'base_contexts'}
                if is_local: tables.update(values='local_values',operational='local_operations')
                for field,table in tables.items():
                    original=current[field]
                    if field in ('rows','operational'):
                        view=DiskRows(store,table)
                        stream=(output/name).with_suffix('.jsonl').open('x',encoding='utf-8',newline='\n') if field=='rows' else None
                        try:
                            for row in original:
                                view.append(row)
                                if stream: stream.write(base._dump(view.last_reference)+'\n')
                        finally:
                            if stream: stream.close()
                    else:
                        view=DiskMap(store,table)
                        for key,value in original.items(): view.setdefault(key,value)
                    current[field]=view
                compact=compact_document(current,store,local=is_local)
                with (output/name).with_suffix('.jsonl').open('rb') as stream:
                    compact['jsonl_sha256']=hashlib.file_digest(stream,'sha256').hexdigest()
                compact_docs.append((name,compact,is_local))
            store.close()
            for name,compact,is_local in compact_docs:
                if not is_local: compact['storage'].update(store.descriptor())
                (output/name).write_text(base._dump(compact)+'\n',encoding='utf-8',newline='\n')
        finally: store.close()
    local=any(source.glob('local_evaluation_*.json'))
    # Use the byte-pinned, already completed collection certificate. Do not
    # resurrect the legacy collector's all-process JSON load during migration.
    if local:
        certificate=json.loads(read(source/'summary.json'))
        before={'valid':certificate['valid'],'comparison_sha256':certificate['local_comparison_sha256'],
                'v1_comparison_sha256':certificate['v1_comparison_sha256']}
    else:
        certificate=json.loads(read(source.parent/'manifest.json'))['evaluation_trace_validation']
        before={'valid':certificate['valid'],'comparison_sha256':certificate['comparison_sha256'],
                'v1_comparison_sha256':None}
    after=collect(output,local=local)
    changes=[p for p,h in pins.items() if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h]
    summary={'source':str(source),'output':str(output),'local':local,'input_sha256':pins,
             'before_valid':before['valid'],'after_valid':after['valid'],'after_errors':after['errors'],
             'comparison_sha256':[before['comparison_sha256'],after['comparison_sha256']],
             'v1_sha256':[before.get('v1_comparison_sha256'),after.get('v1_comparison_sha256')],
             'source_changes':changes,'model_executions':0}
    summary['valid']=before['valid'] and after['valid'] and not changes and len(set(summary['comparison_sha256']))==1 and len(set(summary['v1_sha256']))==1
    (output/'reencode_validation.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8',newline='\n')
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('source');parser.add_argument('output');args=parser.parse_args()
    result=reencode(args.source,args.output)
    print(json.dumps({k:v for k,v in result.items() if k!='input_sha256'},indent=2))
    raise SystemExit(0 if result['valid'] else 1)
