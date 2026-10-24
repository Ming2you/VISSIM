"""Lossless, disk-backed trace records; memory does not retain prior candidates.

The public snapshot key is still SHA256 of the v1/v2 canonical JSON. Internal
Merkle nodes only compress storage: expanding them yields those exact bytes.
SQLite owns the index (2 MiB page cache); the Python node cache is size-bounded.
"""
from __future__ import annotations

from collections import OrderedDict
from collections.abc import Mapping, Sequence
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import zlib

_ROOT_JSON_ZLIB = b"\x00trace-root-json-zlib-v1\x00"


def dump(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def hash_json(value):
    # One current-value JSON allocation, never a history-sized allocation. The
    # C encoder avoids a Python callback per scalar in a large config snapshot.
    return hashlib.sha256(dump(value).encode('utf-8')).hexdigest()


class BoundedErrors(list):
    """A broken observer remains invalid without accumulating unlimited errors."""
    def append(self, value):
        if len(self) < 63: super().append(value)
        elif len(self) == 63: super().append({'event':'further_observer_errors','count':1})
        else: self[-1]['count'] += 1


class Store:
    def __init__(self, path, *, readonly=False):
        self.path = Path(path).resolve()
        self.readonly, self.closed = readonly, False
        self.cache, self.cache_bytes = OrderedDict(), 0
        self.cache_limit = 1024 * 1024
        self.conn = self._connect()
        if not readonly:
            self.conn.executescript('''
                CREATE TABLE IF NOT EXISTS nodes (key TEXT PRIMARY KEY, payload BLOB NOT NULL);
                CREATE TABLE IF NOT EXISTS snapshots (key TEXT PRIMARY KEY, descriptor BLOB NOT NULL);
                CREATE TABLE IF NOT EXISTS subtrees (plain_key TEXT PRIMARY KEY, descriptor BLOB NOT NULL);
                CREATE TABLE IF NOT EXISTS maps (name TEXT, key TEXT, snapshot TEXT, PRIMARY KEY(name,key));
                CREATE TABLE IF NOT EXISTS rows (name TEXT, ordinal INTEGER, call_id INTEGER, parent_id INTEGER,
                    base_id INTEGER, event TEXT, kind TEXT, snapshot TEXT, PRIMARY KEY(name,ordinal));
                CREATE INDEX IF NOT EXISTS row_calls ON rows(name,event,call_id);
                CREATE INDEX IF NOT EXISTS row_base ON rows(name,base_id);
            ''')
        self.writes = 0

    def _connect(self):
        if self.readonly or self.closed:
            conn = sqlite3.connect(self.path.as_uri() + '?mode=ro', uri=True)
        else:
            conn = sqlite3.connect(str(self.path))
        conn.execute('PRAGMA cache_size=-2048')
        conn.execute('PRAGMA mmap_size=0')
        conn.execute('PRAGMA temp_store=FILE')
        return conn

    def _query(self, sql, args=()):
        conn = self._connect() if self.closed else self.conn
        try:
            yield from conn.execute(sql, args)
        finally:
            if self.closed: conn.close()

    def _remember(self, key, raw):
        if len(raw) > self.cache_limit: return
        old = self.cache.pop(key, None)
        if old is not None: self.cache_bytes -= len(old)
        self.cache[key] = raw
        self.cache_bytes += len(raw)
        while self.cache_bytes > self.cache_limit:
            _, removed = self.cache.popitem(last=False)
            self.cache_bytes -= len(removed)

    def _pack(self, value, known_content=None):
        content_key = None
        container=isinstance(value,(dict,list,tuple))
        children=value.values() if isinstance(value,dict) else (value if container else ())
        # This only selects WHERE to try the optional shortcut. Every hit still
        # requires a freshly computed full-content hash, never shape equality.
        worth_lookup=container and (len(value)>32 or any(
            isinstance(v,(dict,list,tuple,str)) and len(v)>32 for v in children))
        if known_content is not None or worth_lookup:
            if known_content is None:
                current_bytes = dump(value).encode('utf-8')
                length=len(current_bytes)
            else:
                content_key,length=known_content
            if length >= 4096:
                # Hash current full contents on EVERY visit. No mutable-object
                # identity/shape cache is used. A hit skips child SQL traversal.
                if content_key is None:content_key = hashlib.sha256(current_bytes).hexdigest()
                cached = self.cache.get('content:'+content_key)
                if cached is None:
                    found = self.conn.execute('SELECT descriptor FROM subtrees WHERE plain_key=?',(content_key,)).fetchone()
                    cached = found[0] if found else None
                if cached is not None:
                    self._remember('content:'+content_key,cached)
                    return json.loads(cached)
            else:
                content_key=None
        if isinstance(value, dict):
            node = ['dict', [[k, self._pack(v)] for k, v in sorted(value.items())]]
        elif isinstance(value, (list, tuple)):
            node = ['list', [self._pack(v) for v in value]]
        else:
            return ['atom', value]
        raw = dump(node).encode('utf-8')
        # Inline small containers; large repeated config/state/model subtrees
        # become content references. The tagged grammar cannot collide with data.
        if len(raw) >= 1024:
            key = hashlib.sha256(raw).hexdigest()
            if key not in self.cache:
                self.conn.execute('INSERT OR IGNORE INTO nodes VALUES (?,?)', (key, zlib.compress(raw, 1)))
                self._remember(key, raw)
            node = ['ref', key]
        if content_key is not None:
            encoded = dump(node).encode('utf-8')
            self.conn.execute('INSERT OR IGNORE INTO subtrees VALUES (?,?)',(content_key,encoded))
            self._remember('content:'+content_key,encoded)
        return node

    def _node(self, key):
        raw = self.cache.get(key)
        if raw is None:
            rows = list(self._query('SELECT payload FROM nodes WHERE key=?', (key,)))
            if len(rows) != 1: raise ValueError('Missing trace node: ' + key)
            raw = zlib.decompress(rows[0][0])
            if hashlib.sha256(raw).hexdigest() != key: raise ValueError('Trace node hash mismatch')
            self._remember(key, raw)
        return json.loads(raw)

    def _unpack(self, node):
        kind, payload = node
        if kind == 'atom': return payload
        if kind == 'ref': return self._unpack(self._node(payload))
        if kind == 'list': return [self._unpack(v) for v in payload]
        if kind == 'dict': return {k: self._unpack(v) for k, v in payload}
        raise ValueError('Unknown trace storage tag')

    def put(self, value, *, expected=None):
        current_bytes=dump(value).encode('utf-8')
        key = hashlib.sha256(current_bytes).hexdigest()
        if expected is not None and key != expected: raise ValueError('Snapshot key mismatch')
        if self.conn.execute('SELECT 1 FROM snapshots WHERE key=?', (key,)).fetchone() is None:
            # Hash/encode the current full value once in this store call. The
            # root key and expanded JSON are unchanged; only transport differs.
            blob = (_ROOT_JSON_ZLIB + len(current_bytes).to_bytes(8, 'big')
                    + zlib.compress(current_bytes, 1))
            self.conn.execute('INSERT INTO snapshots VALUES (?,?)', (key, blob))
        self.writes += 1
        if self.writes % 128 == 0: self.conn.commit()
        return key

    def get(self, key):
        rows = list(self._query('SELECT descriptor FROM snapshots WHERE key=?', (key,)))
        if len(rows) != 1: raise ValueError('Missing trace snapshot: ' + key)
        blob = rows[0][0]
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
        if hash_json(value) != key: raise ValueError('Snapshot content hash mismatch')
        return value

    def close(self):
        if self.closed: return
        if not self.readonly: self.conn.commit()
        self.conn.close()
        self.closed = True
        self.cache.clear(); self.cache_bytes = 0

    def descriptor(self):
        if not self.closed: self.conn.commit()
        with self.path.open('rb') as stream:
            key = hashlib.file_digest(stream, 'sha256').hexdigest()
        return {'schema': 'lossless-trace-sqlite/v1', 'database': self.path.name,
                'sha256': key}


class DiskRows(Sequence):
    def __init__(self, store, name):
        self.store, self.name = store, name
        self.count = next(store._query('SELECT COUNT(*) FROM rows WHERE name=?', (name,)))[0]
        self.last_reference = None

    def __len__(self): return self.count

    def append(self, row):
        key = self.store.put(row)
        self.store.conn.execute('INSERT INTO rows VALUES (?,?,?,?,?,?,?,?)',
            (self.name, self.count, row.get('call'), row.get('parent_call'), row.get('base_call'),
             row.get('event'), row.get('kind'), key))
        self.last_reference = {'ordinal': self.count, 'snapshot': key,
                               **{k: row[k] for k in ('call','parent_call','base_call','event','kind') if k in row}}
        self.count += 1

    def __iter__(self):
        reader = Store(self.store.path, readonly=True) if self.store.closed else self.store
        try:
            for (key,) in reader._query('SELECT snapshot FROM rows WHERE name=? ORDER BY ordinal', (self.name,)):
                yield reader.get(key)
        finally:
            if reader is not self.store: reader.close()

    def __getitem__(self, index):
        if isinstance(index, slice): return list(self)[index]  # explicit small-fixture convenience only
        if index < 0: index += self.count
        rows = list(self.store._query('SELECT snapshot FROM rows WHERE name=? AND ordinal=?', (self.name,index)))
        if not rows: raise IndexError(index)
        return self.store.get(rows[0][0])


class DiskMap(Mapping):
    def __init__(self, store, name): self.store, self.name = store, name
    def __len__(self): return next(self.store._query('SELECT COUNT(*) FROM maps WHERE name=?',(self.name,)))[0]
    def __iter__(self):
        for (key,) in self.store._query('SELECT key FROM maps WHERE name=? ORDER BY key',(self.name,)): yield key
    def __getitem__(self, key):
        found = list(self.store._query('SELECT snapshot FROM maps WHERE name=? AND key=?',(self.name,key)))
        if not found: raise KeyError(key)
        return self.store.get(found[0][0])
    def setdefault(self, key, value):
        snapshot = self.store.put(value, expected=key)
        self.store.conn.execute('INSERT OR IGNORE INTO maps VALUES (?,?,?)',(self.name,key,snapshot))
        return value


def _storage_tables(*, local=False, identity=False):
    tables = {'rows':'local_rows' if local else 'base_rows',
              'contexts':'local_contexts' if local else 'base_contexts'}
    if local:
        tables.update(values='local_values', operational='local_operations')
        if identity: tables['identity_provenance']='local_identity_provenance'
    return tables


def compact_document(document, store, *, local=False):
    out = dict(document)
    out['disk_backed'] = True
    tables = _storage_tables(local=local, identity='identity_provenance' in document)
    for key, name in tables.items():
        values = out.pop(key)
        out[key + '_count'] = len(values)
    out.pop('comparison', None)
    out['storage'] = {'schema':'lossless-trace-sqlite/v1', 'database':store.path.name, 'tables':tables}
    return out


def load_document(path, *, expand=False):
    """Small sidecar only by default. Explicit expansion is for bounded fixtures."""
    path = Path(path)
    doc = json.loads(path.read_text(encoding='utf-8'))
    storage = doc.get('storage')
    if not storage: return doc
    store = Store(path.parent / storage['database'], readonly=True)
    store.close()  # views reopen only for their iterator; no leaked Windows handle
    for name, table in storage['tables'].items():
        view = DiskRows(store, table) if name in ('rows','operational','identity_provenance') else DiskMap(store, table)
        doc[name] = list(view) if expand and isinstance(view, DiskRows) else (dict(view) if expand else view)
    return doc


def iter_json(value):
    """Canonical JSON bytes for disk sequences without list()/whole raw loads."""
    if isinstance(value, Mapping):
        yield '{'
        for index, key in enumerate(sorted(value)):
            if index: yield ','
            yield dump(key); yield ':'
            yield from iter_json(value[key])
        yield '}'
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        yield '['
        for index, item in enumerate(value):
            if index: yield ','
            yield from iter_json(item)
        yield ']'
    else:
        yield dump(value)


def streaming_hash(value):
    h = hashlib.sha256()
    for chunk in iter_json(value): h.update(chunk.encode('utf-8'))
    return h.hexdigest()


class NormalizedRows(Sequence):
    """SQL window ranks replace an unbounded Python call-id normalization map."""
    def __init__(self, path, channel, task_range=None):
        self.path, self.channel, self.task_range = Path(path), channel, task_range
        if channel not in ('base_rows','local_rows','local_operations'): raise ValueError(channel)

    def condition(self, channel, alias=''):
        prefix = alias + '.' if alias else ''
        text = f"{prefix}name='{channel}'"
        if self.task_range is not None:
            start, end = map(int, self.task_range)
            column = 'ordinal' if channel == 'base_rows' else 'base_id'
            text += f' AND {prefix}{column} BETWEEN {start} AND {end}'
        return text

    def __len__(self):
        reader = Store(self.path, readonly=True)
        try: return reader.conn.execute('SELECT COUNT(*) FROM rows WHERE '+self.condition(self.channel)).fetchone()[0]
        finally: reader.close()

    def __iter__(self):
        reader = Store(self.path, readonly=True)
        condition = self.condition(self.channel)
        base_condition = self.condition('base_rows')
        query = f'''
          WITH own_calls AS MATERIALIZED (
            SELECT call_id, ROW_NUMBER() OVER (ORDER BY ordinal)-1 AS new_id
              FROM rows WHERE {condition} AND event='enter'),
          base_calls AS MATERIALIZED (
            SELECT call_id, ROW_NUMBER() OVER (ORDER BY ordinal)-1 AS new_id
              FROM rows WHERE {base_condition} AND event='enter')
          SELECT r.snapshot, c.new_id, p.new_id, b.new_id
            FROM rows r
            LEFT JOIN own_calls c ON c.call_id=r.call_id
            LEFT JOIN own_calls p ON p.call_id=r.parent_id
            LEFT JOIN base_calls b ON b.call_id=r.base_id
            WHERE {self.condition(self.channel,'r')} ORDER BY r.ordinal
        '''
        try:
            for key, call, parent, anchor in reader.conn.execute(query):
                raw = reader.get(key)
                if self.channel == 'local_operations':
                    if anchor is None: raise ValueError('Unassigned operational base call')
                    yield {**raw, 'base_call':anchor}
                    continue
                context_table='local_contexts' if self.channel=='local_rows' else 'base_contexts'
                if not reader.conn.execute('SELECT 1 FROM maps WHERE name=? AND key=?',
                                           (context_table,raw.get('context'))).fetchone():
                    raise ValueError('Missing trace context reference')
                if self.channel=='local_rows':
                    for field in ('input_ref','profiles_ref','requests_ref'):
                        if field in raw and not reader.conn.execute(
                                "SELECT 1 FROM maps WHERE name='local_values' AND key=?",(raw[field],)).fetchone():
                            raise ValueError('Missing local value snapshot')
                if call is None or (raw.get('parent_call') is not None and parent is None):
                    raise ValueError('Unmatched trace call/parent')
                item = {k:v for k,v in raw.items() if k not in ('source','ordinal','timing')}
                item['call'], item['parent_call'] = call, parent
                if self.channel == 'local_rows':
                    if raw.get('base_call') is not None and anchor is None:
                        raise ValueError('Unassigned local base call')
                    item['base_call'] = anchor
                yield item
        finally: reader.close()

    def __getitem__(self, index):
        import itertools
        if isinstance(index, slice): return list(self)[index]
        if index < 0: index += len(self)
        try: return next(itertools.islice(iter(self), index, index+1))
        except StopIteration: raise IndexError(index) from None

    def __eq__(self, other):
        import itertools
        if not isinstance(other, Sequence): return False
        sentinel = object()
        return all(a == b for a,b in itertools.zip_longest(self, other, fillvalue=sentinel))


def has_disk_storage(directory):
    for path in Path(directory).glob('evaluation_*.json'):
        if not path.name.endswith('.started.json'):
            # V3 sidecars are small. A legacy directory is handled by its legacy
            # collector; do not read a large legacy JSON just to detect format.
            with path.open('r',encoding='utf-8') as stream:
                prefix = stream.read(4096)
            if re.search(r'"disk_backed"\s*:\s*true',prefix): return True
    return False


def _file_hash(path):
    with Path(path).open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()


def _verify_jsonl(reader, channel, path):
    # The small public row references and backing table must describe the same
    # ordered records, even if a sidecar checksum was independently rewritten.
    cursor=reader.conn.execute('SELECT ordinal,call_id,parent_id,base_id,event,kind,snapshot FROM rows WHERE name=? ORDER BY ordinal',(channel,))
    with Path(path).open('r',encoding='utf-8') as stream:
        for ordinal,call,parent,anchor,event,kind,snapshot in cursor:
            line=stream.readline()
            expected={'ordinal':ordinal,'snapshot':snapshot,'call':call,'parent_call':parent,'event':event,'kind':kind}
            if channel=='local_rows':expected['base_call']=anchor
            if not line or json.loads(line)!=expected:raise ValueError('JSONL/backing row mismatch')
        if stream.readline():raise ValueError('Extra JSONL record')


def collect(directory, *, root_pid=None, expected_child_pids=(), local=False):
    """Same v1/v2 comparison object, with lazy sequences backed by immutable DBs.

    Only process/task descriptors are retained. Candidate rows, normalization
    ranks, and snapshots stay on disk; no full JSONL or process body is loaded.
    """
    directory = Path(directory)
    docs, local_docs, errors = {}, {}, []
    for path in directory.glob('evaluation_*.json'):
        if path.name.endswith('.started.json'): continue
        doc = json.loads(path.read_text(encoding='utf-8'))
        if not doc.get('disk_backed'): raise ValueError('Mixed disk/legacy trace processes')
        if doc['pid'] in docs: errors.append('duplicate_process_identity')
        docs[doc['pid']] = doc
    for path in directory.glob('local_evaluation_*.json'):
        doc = json.loads(path.read_text(encoding='utf-8'))
        local_docs[doc['pid']] = doc
    pids = set(docs)
    roots = [d for d in docs.values() if d['parent_pid'] not in pids]
    if len(roots) != 1: errors.append('expected_one_root_process')
    actual_root = roots[0]['pid'] if len(roots)==1 else None
    if root_pid is not None and actual_root != root_pid: errors.append('root_pid_mismatch')
    missing = sorted(set(expected_child_pids)-pids)
    if missing: errors.append('observed_child_missing_sidecar')
    started = {json.loads(p.read_text(encoding='utf-8'))['pid']
               for p in directory.glob('evaluation_*.started.json')}
    if started != pids: errors.append('started_finished_pid_sets_differ')
    if local and set(local_docs) != pids: errors.append('missing_local_process_sidecar')
    base_parent, local_parent, base_tasks, local_tasks = [], {}, [], []
    for pid, doc in docs.items():
        if not doc['valid']: errors.append('incomplete_or_invalid_process')
        storage = doc['storage']; path = directory/storage['database']
        if not path.is_file() or _file_hash(path) != storage['sha256']:
            errors.append('trace_storage_hash_mismatch'); continue
        if _file_hash(directory/f'evaluation_{pid}.jsonl') != doc['jsonl_sha256']:
            errors.append('trace_jsonl_hash_mismatch')
        ld = local_docs.get(pid)
        if local and ld is not None:
            if not ld['valid']: errors.append('invalid_local_process')
            if ld['storage']['database'] != storage['database']: errors.append('local_storage_mismatch')
            if _file_hash(directory/f'local_evaluation_{pid}.jsonl') != ld['jsonl_sha256']:
                errors.append('local_jsonl_hash_mismatch')
        reader = Store(path, readonly=True)
        try:
            _verify_jsonl(reader,'base_rows',directory/f'evaluation_{pid}.jsonl')
            if local and ld is not None:_verify_jsonl(reader,'local_rows',directory/f'local_evaluation_{pid}.jsonl')
            for metadata in ([doc,ld] if local and ld else [doc]):
                is_local = metadata is ld
                # Old v2 transports have no identity channel. Current sidecars
                # cannot hide it, or required context/value tables, by omission.
                identity = is_local and ('identity_contract' in metadata or 'identity_provenance_count' in metadata
                    or reader.conn.execute("SELECT 1 FROM rows WHERE name='local_identity_provenance' LIMIT 1").fetchone() is not None)
                tables = _storage_tables(local=is_local, identity=identity)
                if metadata['storage']['tables'] != tables:
                    raise ValueError('Trace table declaration mismatch')
                if {key for key in metadata if key.endswith('_count')} != {field+'_count' for field in tables}:
                    raise ValueError('Trace table count declarations mismatch')
                for field,table in tables.items():
                    sql_table = 'rows' if field in ('rows','operational','identity_provenance') else 'maps'
                    count = reader.conn.execute(f'SELECT COUNT(*) FROM {sql_table} WHERE name=?',(table,)).fetchone()[0]
                    recorded = metadata[field+'_count']
                    if type(recorded) is not int or count != recorded: errors.append('trace_table_count_mismatch')
                    if sql_table=='maps':
                        # Preserve v2's snapshot-key integrity check. At most
                        # one expanded current snapshot is alive at a time.
                        for expected,snapshot in reader.conn.execute('SELECT key,snapshot FROM maps WHERE name=?',(table,)):
                            if snapshot != expected:
                                raise ValueError('Snapshot content hash mismatch')
                            reader.get(snapshot)
                    elif field=='identity_provenance':
                        # This evidence is intentionally outside comparison
                        # hashes, but its stored content must still be verified.
                        for (snapshot,) in reader.conn.execute('SELECT snapshot FROM rows WHERE name=? ORDER BY ordinal',(table,)):
                            reader.get(snapshot)
            if pid == actual_root:
                base_parent = NormalizedRows(path,'base_rows')
                local_parent = {'rows':NormalizedRows(path,'local_rows'),
                                'operational':NormalizedRows(path,'local_operations')}
                continue
            ranges = []
            for start, call, snapshot in reader.conn.execute(
                    "SELECT ordinal,call_id,snapshot FROM rows WHERE name='base_rows' AND event='enter' AND kind='price_task' ORDER BY ordinal"):
                ends = reader.conn.execute("SELECT ordinal FROM rows WHERE name='base_rows' AND event='return' AND call_id=?",(call,)).fetchall()
                if len(ends)!=1: errors.append('unmatched_worker_task'); continue
                end = ends[0][0]; ranges.append((start,end))
                task = reader.get(snapshot)
                key = hash_json({'context':task['context'],'input':task['input']})
                trace = NormalizedRows(path,'base_rows',(start,end))
                base_tasks.append({'task_key':key,'trace':trace})
                local_tasks.append({'task_key':key,'trace':{
                    'rows':NormalizedRows(path,'local_rows',(start,end)),
                    'operational':NormalizedRows(path,'local_operations',(start,end))}})
            if any(b[0] <= a[1] for a,b in zip(ranges,ranges[1:])): errors.append('overlapping_worker_tasks')
            clauses = ' OR '.join(f'(ordinal BETWEEN {a} AND {b})' for a,b in ranges) or '0'
            if reader.conn.execute(f"SELECT COUNT(*) FROM rows WHERE name='base_rows' AND NOT ({clauses})").fetchone()[0]:
                errors.append('unassigned_worker_record')
            if local:
                clauses = ' OR '.join(f'(base_id BETWEEN {a} AND {b})' for a,b in ranges) or '0'
                if reader.conn.execute(f"SELECT COUNT(*) FROM rows WHERE name IN ('local_rows','local_operations') AND (base_id IS NULL OR NOT ({clauses}))").fetchone()[0]:
                    errors.append('unassigned_local_worker_record')
        except (ValueError,KeyError,sqlite3.DatabaseError) as exc:
            errors.append('invalid_trace_index:'+str(exc))
        finally: reader.close()
    try:
        base_tasks.sort(key=lambda task:(task['task_key'],streaming_hash(task['trace'])))
        base_compare = {'parent':base_parent,'worker_tasks':base_tasks}
        base_hash = streaming_hash(base_compare)
        if local:
            local_tasks.sort(key=lambda task:(task['task_key'],streaming_hash(task['trace'])))
            compare = {'parent':local_parent,'worker_tasks':local_tasks}
        else: compare = base_compare
        key = streaming_hash(compare) if local else base_hash
    except (ValueError, KeyError, sqlite3.DatabaseError, zlib.error) as exc:
        errors.append('invalid_trace_storage:' + str(exc)); compare = {}; key = None; base_hash = None
    result = {'valid':not errors,'errors':errors,'process_count':len(docs),'process_pids':sorted(pids),
              'root_pid':actual_root,'missing_observed_child_pids':missing,
              'worker_task_count':len(base_tasks),'comparison':compare,'comparison_sha256':key,
              'storage_scope':'Canonical v1/v2 comparison semantics; candidate sequences streamed from lossless disk storage.',
              'coverage':'All selected canonical candidate/query/component layers retained; no candidate or operational field excluded to reduce storage.'}
    if local: result['v1_comparison_sha256'] = base_hash
    if local:
        result['identity_contracts']=sorted({d.get('identity_contract','legacy v2 raw phase demand address') for d in local_docs.values()})
    return result
