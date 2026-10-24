"""Prepare a storage-only patch; never write the running canonical tracer.

The temporary module is for isolated synthetic QA only. Public snapshot IDs
remain SHA256(canonical JSON); old DAG descriptors remain readable.
"""
from contextlib import contextmanager
import difflib
import hashlib
import importlib
from pathlib import Path
import sys
from types import ModuleType
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'diagnostics/evaluation_trace_storage.py'
EXPECTED='ef6ce464a378355d617016d8a192320ffb454e42f9e13c1e11c56d22ab2073f7'
PATCH=ROOT/'diagnostics/trace_root_compression_v2.patch'


def transformed():
    raw=SOURCE.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=EXPECTED:raise ValueError('Frozen storage base changed')
    text=raw.decode('utf-8').replace('\r\n','\n')
    replacements=[
        ('import zlib\n','import zlib\n\n_ROOT_JSON_ZLIB = b"\\x00trace-root-json-zlib-v1\\x00"\n'),
        ('''            node = self._pack(value,known_content=(key,len(current_bytes)))
            self.conn.execute('INSERT INTO snapshots VALUES (?,?)', (key, dump(node).encode('utf-8')))
''','''            # Hash/encode the current full value once in this store call. The
            # root key and expanded JSON are unchanged; only transport differs.
            blob = (_ROOT_JSON_ZLIB + len(current_bytes).to_bytes(8, 'big')
                    + zlib.compress(current_bytes, 1))
            self.conn.execute('INSERT INTO snapshots VALUES (?,?)', (key, blob))
'''),
        ('''        value = self._unpack(json.loads(rows[0][0]))
''','''        blob = rows[0][0]
        if blob.startswith(_ROOT_JSON_ZLIB):
            header = len(_ROOT_JSON_ZLIB)
            if len(blob) < header + 8: raise ValueError('Truncated compressed snapshot header')
            length = int.from_bytes(blob[header:header+8], 'big')
            inflater = zlib.decompressobj()
            try:
                raw = inflater.decompress(blob[header+8:], length+1)
            except (zlib.error, OverflowError) as exc:
                raise ValueError('Invalid compressed snapshot') from exc
            if (len(raw) != length or not inflater.eof or inflater.unused_data
                    or inflater.unconsumed_tail):
                raise ValueError('Compressed snapshot length or stream mismatch')
            value = json.loads(raw)
        else:
            # Existing immutable v3 DAG databases remain readable.
            value = self._unpack(json.loads(blob))
'''),
    ]
    for old,new in replacements:
        if text.count(old)!=1:raise ValueError('Storage patch anchor is not unique')
        text=text.replace(old,new)
    return raw,text


def proposal_module():
    _,text=transformed()
    module=ModuleType('diagnostics.evaluation_trace_storage')
    module.__file__=str(SOURCE)
    module.__package__='diagnostics'
    exec(compile(text,str(SOURCE),'exec'),module.__dict__)
    return module


@contextmanager
def installed_proposal():
    """Only this diagnostic process imports the transformed storage module."""
    package=importlib.import_module('diagnostics')
    importlib.import_module('diagnostics.evaluation_trace_storage')
    module=proposal_module()
    with patch.dict(sys.modules,{'diagnostics.evaluation_trace_storage':module}), \
            patch.object(package,'evaluation_trace_storage',module):
        yield module


def prepare():
    raw,text=transformed()
    if PATCH.exists():raise ValueError('Preserve existing proposal patch; use explicit reviewed revision')
    diff=''.join(difflib.unified_diff(raw.decode('utf-8').replace('\r\n','\n').splitlines(True),
        text.splitlines(True),fromfile='a/diagnostics/evaluation_trace_storage.py',
        tofile='b/diagnostics/evaluation_trace_storage.py'))
    PATCH.write_text(diff,encoding='utf-8',newline='\n')
    return {'base_sha256':EXPECTED,'proposed_text_sha256':hashlib.sha256(text.encode()).hexdigest(),
            'patch':str(PATCH),'patch_sha256':hashlib.sha256(PATCH.read_bytes()).hexdigest()}


if __name__=='__main__':
    import json
    print(json.dumps(prepare()))
