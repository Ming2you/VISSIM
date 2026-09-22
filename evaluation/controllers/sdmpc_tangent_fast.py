"""Plain numeric validation kernels in the isolated derivative worker only.

Compile the original source bodies, retaining every field, guard and tolerance.
Their values are already explicitly stripped to validation primals. Arithmetic
that transports vehicles or produces an objective/resource remains AD traced.
"""
import ast
import builtins
import copy
import hashlib
import math
from pathlib import Path


def install(finder, cfg):
    if not cfg.network.sdmpc_options.get('fast_primitives'):
        return
    if (finder.backend != 'reverse-v1'
            or not cfg.network.sdmpc_options.get('primal_audit')):
        raise ValueError('Fast primitives require reverse AD with primal-only audit records')
    from evaluation.controllers import control_area_objective as area
    from evaluation.controllers import sdmpc_tangent_reverse as ad
    path=Path(area.__file__).resolve()
    data=path.read_bytes()
    tree=ast.parse(data,filename=str(path))
    ledger=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='ModelAreaLedger')
    names={'record_resource_allocation','record_state_upper_bound'}
    functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in
               {'_copy_response_tree','_nonnegative'}]
    functions.extend(n for n in ledger.body if isinstance(n,ast.FunctionDef) and n.name in names)
    if len(functions)!=4:
        raise ValueError('Canonical validation kernel source changed')
    namespace=dict(vars(area),__builtins__=builtins.__dict__,math=math,copy=copy)
    # Both AD scalar classes are immutable and deepcopy to themselves.
    # All other objects keep the canonical deepcopy hooks and memo behavior.
    namespace['_COPY_ATOMIC_TYPES']=area._COPY_ATOMIC_TYPES|{ad.Dual,ad.forward.Dual}
    exec(compile(ast.Module(body=functions,type_ignores=[]),str(path),'exec',
                 flags=__import__('__future__').annotations.compiler_flag),namespace)
    area._copy_response_tree=namespace['_copy_response_tree']
    for name in names:
        setattr(area.ModelAreaLedger,name,namespace[name])
    ad.FAST_PRIMITIVES=True
    for source in (path,Path(__file__).resolve()):
        finder.source_hashes[str(source)]=hashlib.sha256(source.read_bytes()).hexdigest()
