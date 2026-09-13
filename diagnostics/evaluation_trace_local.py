"""Optional companion for the v1 trace; never replaces a model function.

The profile hook observes selected returns. A second, selective line hook observes
complete costs immediately before the existing candidate evaluation counters.
Outputs are separate, so adding local evidence does not renumber v1 events.
This is a correctness instrument, not an uninstrumented performance benchmark.
"""
from __future__ import annotations

import atexit
import ast
import dis
import hashlib
import inspect
import json
import os
from pathlib import Path
import sys
import threading

from diagnostics import evaluation_trace as base
from diagnostics.evaluation_trace_state import operational, MISSING_DEMAND

ROOT = base.ROOT
VENDOR = 'vendor/NumSim-mine/src/controllers/'
QUERY_NAMES = ('local_green_costs', 'local_metering_costs', 'local_offset_costs',
               'local_green_offset_costs', 'local_vsl_meter_costs', 'local_vsl_costs')
LOCAL_INPUTS = ('signal', 'link', 'coupling', 'arr_movement', 's_eff_frozen',
                'reservoir_drain', 'freeway_congestion', 'lambda_p', 'forecast_arrivals',
                'horizon_h', 'candidates_override', 'vsl_override', 'requests')
PRICE_FIELDS = ('signal_phase_price', 'signal_phase_price_ref', 'signal_phase_price_weight',
                'signal_marginal_price', 'signal_marginal_price_ref', 'signal_marginal_price_weight',
                'metering_marginal_price', 'metering_marginal_price_ref', 'metering_marginal_price_weight',
                'vsl_marginal_price', 'vsl_marginal_price_ref', 'vsl_marginal_price_weight',
                'offset_marginal_price', 'offset_marginal_price_ref', 'offset_marginal_price_weight',
                'green_offset_cross_price', 'green_offset_cross_ref', 'green_offset_cross_weight',
                'vsl_meter_cross_price', 'vsl_meter_cross_ref', 'vsl_meter_cross_weight',
                '_lambda_P', '_lambda_UF', 'metering_budget_penalty_weight', 'ramp_metering_weight')
PRICE_FIELDS += ('signal_marginal_price_trust_sec','metering_marginal_price_trust_frac',
                 'vsl_marginal_price_trust_kmh','offset_marginal_price_trust_sec',
                 'metering_release_certified','metering_price_split','price_smoothness_disabled')
CONTROL_NAMES = ('previous', 'snapshot', 'control', 'leader', 'committed_prev')


def production_specs():
    wu = VENDOR + 'wu_faithful_follower.py'
    priced = VENDOR + 'priced_wu_link_controller.py'
    adapter = 'evaluation/controllers/vissim_stackelberg_adapter.py'
    out = []
    def add(path, suffix, kind, mode='return', **kw):
        out.append(dict(path=path, suffix=suffix, kind=kind, mode=mode, **kw))
    for name, fields, score in (
        ('_solve_urban_agent_local', ['signal', 'p1', 'greens', 'offset_for_green', 'nin'], 'cost'),
        ('_solve_urban_agent_joint', ['signal', 'p1', 'offset', 'nin'], 'cost'),
        ('_solve_offset_local', ['signal', 'green_p1', 'offset'], 'obj'),
        ('_solve_offset_local_ramp', ['signal', 'green_p1', 'offset', 'greens'], 'obj'),
    ):
        add(wu, name, 'urban_candidate', mode='counter', counter='evals', count=1,
            fields=fields, score=score)
    add('evaluation/controllers/link_predictor.py', 'solve_freeway_agent_local',
        'freeway_sequence_candidate', mode='counter', counter='evals', count=1,
        fields=['link', 'sequence', 'first_vec', 'candidate_control'], score='cost')
    # All ten paths include the seed and every scored trial; each counter is
    # after its branch's complete metering price/dual term, before winner update.
    add(wu, '_solve_freeway_agent_metered', 'meter_candidate', mode='counter',
        counter='evals_total', count=10, fields=['link'], score='meter_branch')
    for name in QUERY_NAMES:
        add(wu, name, 'local_price_query')
    add(priced, 'apply_phase_price_refinement', 'phase_search_context', mode='context')
    add(priced, '_solve_urban_agent_local', 'phase_search_context', mode='context')
    add(priced, 'apply_phase_price_refinement.<locals>.scored', 'phase_candidate',
        fields=['signal', 'vec', 'price', 'ref', 'weight'])
    add(priced, '_solve_urban_agent_local.<locals>.scored', 'phase_candidate',
        fields=['signal', 'vec', 'price', 'ref', 'weight'])
    add(adapter, 'install_phased_price_local.<locals>.patched.<locals>.local_cost',
        'phase_price_local_candidate', fields=['signal', 'vec'])
    add(adapter, 'install_phased_price_local.<locals>._joint_refine',
        'phase_joint_context', mode='context')
    add(adapter, 'install_phased_price_local.<locals>._joint_refine.<locals>._J',
        'phase_joint_candidate', fields=['group', 'control', 'prices', 'refs', 'w_j'])
    # The projected request, and its raw caller request, are distinct evidence.
    add(adapter, 'install_freeway_vsl_zones.<locals>._zoned_local_vsl_costs',
        'local_price_query_projected')
    for name in ('rollout_local_tts', 'rollout_local_tts_phased', 'rollout_local_tts_ramp_aware'):
        add(VENDOR+'local_signal_plant.py', name, 'local_physical_component', mode='component')
    add('evaluation/controllers/local_signal_service.py', 'rollout_shared_ramp',
        'local_physical_component', mode='component')
    # These legacy candidate bodies are not the installed link-agent path. If
    # reached, do not call the evidence complete merely because a winner exists.
    for name in ('_solve_freeway_agent_local', '_solve_freeway_segment_agents'):
        add(wu, name, 'unsupported_local_backend', mode='unsupported')
    return out


def _functions(tree, prefix=''):
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            name = prefix + node.name
            if not isinstance(node, ast.ClassDef):
                yield name, node
            inner = name + ('.' if isinstance(node, ast.ClassDef) else '.<locals>.')
            yield from _functions(node, inner)
        else:
            yield from _functions(node, prefix)


def _meter_operands(node):
    """Find each counter's actual preceding _solve_with assignment in its block."""
    found={}
    def visit(owner):
        for _,value in ast.iter_fields(owner):
            if isinstance(value,list):
                last=None
                for stmt in value:
                    if (isinstance(stmt,ast.Assign) and isinstance(stmt.value,ast.Call)
                            and isinstance(stmt.value.func,ast.Name) and stmt.value.func.id=='_solve_with'):
                        lhs=stmt.targets[0]
                        if not isinstance(lhs,ast.Tuple) or len(lhs.elts)!=3 or len(stmt.value.args)!=1:
                            raise ValueError('Meter candidate assignment contract changed')
                        names=[n.id for n in lhs.elts]
                        arg=stmt.value.args[0]
                        if not isinstance(arg,ast.Name):raise ValueError('Meter argument is no longer a named vector')
                        last={'vsl':names[0],'score':names[1],'evaluations':names[2],'meter':arg.id}
                    if (isinstance(stmt,ast.AugAssign) and isinstance(stmt.target,ast.Name)
                            and stmt.target.id=='evals_total'):
                        if last is None or not isinstance(stmt.value,ast.Name) or stmt.value.id!=last['evaluations']:
                            raise ValueError('Meter count is not attached to an explicit completed solve')
                        found[stmt.lineno]=dict(last)
                    if isinstance(stmt,ast.AST) and not isinstance(stmt,(ast.FunctionDef,ast.AsyncFunctionDef)):
                        visit(stmt)
            elif isinstance(value,ast.AST):visit(value)
    visit(node)
    return found


class Targets:
    """Read-only AST discovery plus exact source/qualname/code-start matching."""
    def __init__(self, specs=None, root=ROOT):
        self.root, self.targets, self.sources = Path(root).resolve(), {}, {}
        for spec0 in (production_specs() if specs is None else specs):
            spec = dict(spec0)
            path = (self.root/spec['path']).resolve()
            raw = path.read_bytes()
            self.sources[str(path)] = hashlib.sha256(raw).hexdigest()
            matches = [(q,n) for q,n in _functions(ast.parse(raw, filename=str(path)))
                       if q == spec['suffix'] or q.endswith('.'+spec['suffix'])]
            if len(matches) != 1:
                raise ValueError('Expected one pinned local target: '+spec['suffix'])
            qual,node = matches[0]
            spec.update(qualname=qual, first_line=min([node.lineno]+[d.lineno for d in node.decorator_list]),
                        ast_sha256=base.digest(ast.dump(node, include_attributes=False)))
            counters = [n for n in ast.walk(node) if isinstance(n, ast.AugAssign)
                        and isinstance(n.target, ast.Name) and n.target.id == spec.get('counter')]
            spec['lines'] = {n.lineno: n for n in counters}
            if spec['mode']=='counter' and len(counters)!=spec['count']:
                raise ValueError('Candidate counter count changed: '+qual)
            if spec.get('score')=='meter_branch':
                spec['meter_operands']=_meter_operands(node)
                if set(spec['meter_operands'])!=set(spec['lines']):
                    raise ValueError('Not all metering scores have exact operand bindings')
            self.targets[(str(path),qual,spec['first_line'])] = spec
        self.cache = {}
        self.basenames={Path(p).name for p in self.sources}

    def get(self, code):
        if code not in self.cache:
            self.cache[code] = (self.targets.get((str(Path(code.co_filename).resolve()),
                                                code.co_qualname,code.co_firstlineno))
                                if code.co_filename.replace('\\','/').rsplit('/',1)[-1] in self.basenames else None)
        return self.cache[code]

    def changed(self):
        return [p for p,h in self.sources.items() if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h]


class LocalRecorder:
    def __init__(self, parent, targets=None):
        self.parent = parent
        self.targets = targets or Targets()
        self.frames, self.rows, self.contexts, self.values, self.errors = {}, [], {}, {}, []
        self.operational_rows=[]
        self.identity_rows=[]
        self.storage = getattr(parent, 'storage', None)
        if self.storage is not None:
            from diagnostics.evaluation_trace_storage import DiskRows, DiskMap, BoundedErrors
            self.errors = BoundedErrors()
            self.rows = DiskRows(self.storage, 'local_rows')
            self.operational_rows = DiskRows(self.storage, 'local_operations')
            self.identity_rows = DiskRows(self.storage, 'local_identity_provenance')
            self.contexts = DiskMap(self.storage, 'local_contexts')
            self.values = DiskMap(self.storage, 'local_values')
        self.finished = False
        self.counts = {'profile_events':0, 'global_trace_calls':0, 'selected_line_events':0}
        self.stem = parent.directory/('local_evaluation_'+str(os.getpid()))
        self.stream = self.stem.with_suffix('.jsonl').open('x',encoding='utf-8',newline='\n')

    def emit(self, item):
        item['ordinal']=len(self.rows)
        self.rows.append(item)
        self.stream.write(base._dump(self.rows.last_reference if self.storage else item)+'\n'); self.stream.flush()

    def value_ref(self, value):
        snapshot=base.canonical(value); key=base.digest(snapshot)
        self.values.setdefault(key,snapshot)
        return key

    def operational_snapshot(self, obj, values, origin):
        demand=values.get('demand',values.get('forecast',MISSING_DEMAND))
        def identity_sink(row):
            self.identity_rows.append({'local_ordinal':len(self.rows),'base_ordinal':len(self.parent.rows),
                                       'origin':origin,**row})
        return operational(obj,current_demand=demand,identity_sink=identity_sink)

    def ancestors(self, frame):
        local, outer = None, None
        current=frame.f_back
        while current is not None:
            if local is None:
                local=self.frames.get(id(current))
            if outer is None:
                outer=self.parent.frames.get(id(current))
            if local is not None and outer is not None: break
            current=current.f_back
        return local,outer

    def enter(self, frame, spec):
        if spec['mode']=='unsupported':
            self.errors.append({'kind':'unsupported_local_backend','function':spec['qualname']})
            return
        values=base._locals(frame)
        local,outer=self.ancestors(frame)
        entry={'call':len(self.rows),'parent_call':local['call'] if local else None,
               'base_call':outer['call'] if outer else None,'kind':spec['kind'],
               'source':{'path':frame.f_code.co_filename,'qualname':frame.f_code.co_qualname,
                         'line':frame.f_code.co_firstlineno},'timing':base._timing()}
        # A full input/config snapshot belongs to the search, never to every
        # scored phase closure. Nested physical component arguments use refs.
        if local is not None and spec['mode'] in ('return','component'):
            entry['context']=local['context']
        else:
            obj=values.get('self')
            state=values.get('state')
            raw={'state':base.canonical(state),'forecast':base.canonical(values.get('demand')),
                 'cfg':base.canonical(getattr(obj,'cfg',None)),
                 'prices':base.canonical({k:getattr(obj,k) for k in PRICE_FIELDS if hasattr(obj,k)}),
                 'operational':self.operational_snapshot(obj,values,'local_enter'),
                 'operands':base.canonical({k:values[k] for k in LOCAL_INPUTS if k in values}),
                 'controls':{k:base.control(values[k]) for k in CONTROL_NAMES if k in values}}
            entry['context']=base.digest(raw); self.contexts.setdefault(entry['context'],raw)
        if spec['mode']=='component':
            args=inspect.getargvalues(frame)
            payload={k:values[k] for k in args.args}
            model=payload.pop('model',None)
            # cfg is retained by the enclosing search. Actual derived cap/spec
            # fields, including installed shared-resource/ready operands, remain.
            payload['model_fields']={k:v for k,v in vars(model).items() if k!='cfg'} if model else None
            entry['input_ref']=self.value_ref(payload)
        else:
            entry['input_ref']=self.value_ref({k:values[k] for k in spec.get('fields',LOCAL_INPUTS)
                                                if k in values})
        if spec['kind'].startswith('local_price_query'):
            entry['requests_ref']=self.value_ref(list(values['requests'].items()))
        entry['candidate_count']=0
        entry['nested_evaluations']=0
        self.frames[id(frame)]=entry
        self.emit({**entry,'event':'enter'})

    def candidate(self, frame, spec):
        entry=self.frames[id(frame)]; values=frame.f_locals
        data={k:values[k] for k in spec.get('fields',()) if k in values}
        if spec['score']=='meter_branch':
            operands=spec['meter_operands'][frame.f_lineno]
            score=values[operands['score']]
            data.update(meter=values[operands['meter']],vsl=values[operands['vsl']],
                        nested_vsl_evaluations=values[operands['evaluations']])
            entry['nested_evaluations']+=int(values[operands['evaluations']])
        else:
            score=values[spec['score']]
        profiles={k:values[k] for k in ('gf_by_substep','greens','arr_by_substep') if k in values}
        entry['candidate_count']+=1
        self.emit({'event':'candidate','kind':entry['kind'],'call':entry['call'],
                   'parent_call':entry['parent_call'],'base_call':entry['base_call'],
                   'context':entry['context'],'index':entry['candidate_count']-1,
                   'input_ref':self.value_ref(data),'profiles_ref':self.value_ref(profiles),
                   'score':base.canonical(float(score)), 'timing':base._timing(),
                   'source':{'line':frame.f_lineno}})

    def leave(self, frame, result, spec):
        entry=self.frames.pop(id(frame))
        opcode=frame.f_code.co_code[frame.f_lasti] if frame.f_lasti>=0 else 0
        normal=dis.opname[opcode].startswith('RETURN')
        if not normal:self.errors.append({'kind':spec['kind'],'event':'unwind'})
        values=frame.f_locals
        if normal and spec.get('counter')=='evals' and entry['candidate_count']!=values.get('evals',0):
            self.errors.append({'kind':spec['kind'],'event':'candidate_counter_mismatch'})
        if normal and spec.get('counter')=='evals_total' and entry['nested_evaluations']!=values.get('evals_total',0):
            self.errors.append({'kind':spec['kind'],'event':'nested_vsl_counter_mismatch'})
        if normal and spec['kind'].startswith('local_price_query'):
            requests=values['requests']
            if not isinstance(result,dict) or set(result)!=set(requests) or any(
                    len(result[key])!=len(requests[key]) for key in requests):
                self.errors.append({'kind':spec['kind'],'event':'query_result_cardinality_mismatch'})
        now=base._timing()
        self.emit({'event':'return','kind':entry['kind'],'call':entry['call'],
                   'parent_call':entry['parent_call'],'base_call':entry['base_call'],
                   'context':entry['context'],'result':base.result(result),
                   'candidate_count':entry['candidate_count'],'exit':'return' if normal else 'unwind',
                   'nested_evaluations':entry['nested_evaluations'],
                   'components':base.canonical({k:values[k] for k in ('local','ext','weight') if k in values}),
                   'operational_after':self.operational_snapshot(values.get('self'),values,'local_return'),
                   'timing':{**now,'inclusive_wall_ns':now['perf_ns']-entry['timing']['perf_ns']}})

    def profile(self, frame, event, arg):
        before=self.parent.frames.get(id(frame))
        self.parent.profile(frame,event,arg)
        observed=self.parent.frames.get(id(frame)) if event=='call' else before
        if observed is not None and event in ('call','return') and observed['kind'] in (
                'follower','leader_full','leader_proxy','leader_pfo','price_task',
                'price_batch','price_refresh','phase_refresh','decision'):
            try:
                obj=frame.f_locals.get('self')
                state_values=base._locals(frame)
                if observed['kind']=='price_task':
                    state_values=frame.f_globals.get('_PRICE_WORKER_CTX',{})
                    obj=state_values.get('ctrl')
                self.operational_rows.append({'base_call':observed['call'],
                                               'event':'before' if event=='call' else 'after',
                                               'kind':observed['kind'],'state':self.operational_snapshot(obj,state_values,'base_'+event)})
            except Exception as exc:
                self.errors.append({'event':'operational_snapshot','type':type(exc).__name__,'message':str(exc)})
        self.counts['profile_events']+=1
        if event not in ('call','return'):return
        spec=self.targets.get(frame.f_code)
        if spec is None:return
        try:
            if event=='call':self.enter(frame,spec)
            elif id(frame) in self.frames:self.leave(frame,arg,spec)
        except Exception as exc:
            self.errors.append({'event':event,'function':spec['qualname'],
                                'type':type(exc).__name__,'message':str(exc)})

    def trace(self, frame, event, arg):
        self.counts['global_trace_calls']+=1
        spec=self.targets.get(frame.f_code)
        if spec is not None and spec['mode']=='counter':
            frame.f_trace_opcodes=False
            return self.line
        return None

    def line(self, frame, event, arg):
        if event=='line':
            self.counts['selected_line_events']+=1
            spec=self.targets.get(frame.f_code)
            if frame.f_lineno in spec['lines']:
                try:self.candidate(frame,spec)
                except Exception as exc:self.errors.append({'event':'line','function':spec['qualname'],
                                                           'type':type(exc).__name__,'message':str(exc)})
        return self.line

    def finish(self, *, monitoring_stopped=False):
        if self.finished:return
        self.finished=True
        if not monitoring_stopped:
            if sys.gettrace()==self.trace:sys.settrace(None)
            else:self.errors.append({'event':'local_trace_hook_replaced'})
            if sys.getprofile()==self.profile:sys.setprofile(self.parent.profile)
            else:self.errors.append({'event':'local_profile_hook_replaced'})
        self.stream.close()
        changed=self.targets.changed()
        from diagnostics.decision_profile import memory_counters
        document={'schema':'local-evaluation-trace/v1','pid':os.getpid(),'parent_pid':os.getppid(),
                  'valid':not self.errors and not self.frames and not changed,
                  'errors':self.errors,'unmatched_calls':len(self.frames),'source_changes':changed,
                  'source_sha256':self.targets.sources,'rows':self.rows,'contexts':self.contexts,
                  'operational':self.operational_rows,
                  'identity_provenance':self.identity_rows,
                  'identity_contract':'Only proven phase signature id(demand) becomes its context/current identity relation plus complete demand values; raw addresses retained as provenance.',
                  'values':self.values,'observer_counts':self.counts,'memory':memory_counters(),
                  'scope':'Selected canonical link-agent backend; component, complete candidate, and query-result layers are not additive.',
                  'timing_scope':'Both profile and selective line tracing overhead included; no normal benchmark claim.'}
        if self.storage is not None:
            from diagnostics.evaluation_trace_storage import compact_document
            compact = compact_document(document, self.storage, local=True)
            with self.stem.with_suffix('.jsonl').open('rb') as stream:
                compact['jsonl_sha256'] = hashlib.file_digest(stream, 'sha256').hexdigest()
            self.stem.with_suffix('.json').write_text(base._dump(compact)+'\n',encoding='utf-8')
        else:
            self.stem.with_suffix('.json').write_text(base._dump(document)+'\n',encoding='utf-8')
        return document


def attach(parent, targets=None):
    if (sys.getprofile()!=parent.profile or sys.gettrace() is not None
            or threading.getprofile() is not None or threading.gettrace() is not None):
        raise RuntimeError('Local companion requires sole ownership of the v1 evaluation trace hooks')
    recorder=LocalRecorder(parent,targets)
    sys.setprofile(recorder.profile)
    sys.settrace(recorder.trace)
    # Registered after base.finish: restores its profile first at process exit.
    atexit.register(recorder.finish)
    return recorder


def _normalized(rows, base_rows, operational_rows=()):
    base_ids={}
    for row in base_rows:base_ids.setdefault(row['call'],len(base_ids))
    ids={}
    for row in rows:ids.setdefault(row['call'],len(ids))
    result=[]
    for row in rows:
        item={k:v for k,v in row.items() if k not in ('source','ordinal','timing')}
        item['call']=ids[row['call']]
        parent=row.get('parent_call')
        item['parent_call']=None if parent is None else ids[parent]
        anchor=row.get('base_call')
        item['base_call']=None if anchor is None else base_ids[anchor]
        result.append(item)
    operations=[{**row,'base_call':base_ids[row['base_call']]} for row in operational_rows]
    return {'rows':result,'operational':operations}


def collection(directory, *, root_pid=None, expected_child_pids=()):
    """Preserve v1 hash separately; local worker rows match the same task keys."""
    from diagnostics.evaluation_trace_storage import has_disk_storage, collect
    if has_disk_storage(directory):
        return collect(directory, root_pid=root_pid, expected_child_pids=expected_child_pids, local=True)
    legacy=base.collection(directory,root_pid=root_pid,expected_child_pids=expected_child_pids)
    root_pid=legacy['root_pid']
    docs={}
    for path in Path(directory).glob('local_evaluation_*.json'):
        doc=json.loads(path.read_text(encoding='utf-8'));docs[doc['pid']]=doc
    base_docs={}
    for path in Path(directory).glob('evaluation_*.json'):
        if path.name.endswith('.started.json'):continue
        doc=json.loads(path.read_text(encoding='utf-8'));base_docs[doc['pid']]=doc
    errors=list(legacy['errors'])
    if set(docs)!=set(base_docs):errors.append('missing_local_process_sidecar')
    tasks=[];parent={}
    for pid,doc in docs.items():
        if not doc['valid']:errors.append('invalid_local_process')
        for table in ('values','contexts'):
            if any(base.digest(value)!=key for key,value in doc[table].items()):
                errors.append('local_snapshot_hash_mismatch')
        for row in doc['rows']:
            if row.get('context') not in doc['contexts']:
                errors.append('missing_local_context')
            for key in ('input_ref','profiles_ref','requests_ref'):
                if key in row and row[key] not in doc['values']:
                    errors.append('missing_local_value_snapshot')
        original=base_docs.get(pid)
        if original is None:continue
        rows=doc['rows']
        if pid==root_pid:
            parent=_normalized(rows,original['rows'],doc['operational']);continue
        assigned=set()
        for task in (r for r in original['rows'] if r['event']=='enter' and r['kind']=='price_task'):
            ids={task['call']};base_rows=[]
            for row in original['rows']:
                if row['call'] in ids or row.get('parent_call') in ids:
                    ids.add(row['call']);base_rows.append(row)
            local_rows=[row for row in rows if row.get('base_call') in ids]
            assigned.update(r['ordinal'] for r in local_rows)
            tasks.append({'task_key':base.digest({'context':task['context'],'input':task['input']}),
                          'trace':_normalized(local_rows,base_rows,[r for r in doc['operational'] if r['base_call'] in ids])})
        if len(assigned)!=len(rows):errors.append('unassigned_local_worker_record')
    compare={'parent':parent,'worker_tasks':sorted(tasks,key=lambda x:(x['task_key'],base.digest(x['trace'])))}
    return {'valid':not errors,'errors':errors,'process_count':len(docs),
            'v1_comparison_sha256':legacy['comparison_sha256'],
            'comparison':compare,'comparison_sha256':base.digest(compare),
            'worker_task_count':len(tasks),
            'coverage':'All evaluated candidates in the selected canonical link-agent bodies; query results/components are separate nested evidence. Unsupported legacy bodies fail closed.'}
