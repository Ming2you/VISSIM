"""Qualify a representation-only change without claiming a new AD rollout.

The numeric run remains pinned to its original source. The only permitted AST
change recreates equal ASCII payload keys; all value and prediction expressions
must remain identical. Native prediction uses and pins the current source.
"""
from pathlib import Path
import ast
import hashlib
import pickle


def qualify(source, request, expected_hash):
    from evaluation.controllers import sdmpc_sequence as seq, sdmpc_dual as ad
    old_path=Path(source)/'sources/sdmpc_sequence.py'
    new_path=Path(seq.__file__)
    before,after=old_path.read_bytes(),new_path.read_bytes()
    if hashlib.sha256(before).hexdigest()!=expected_hash:
        raise ValueError('Transport baseline is not the derivative source')
    old_tree,new_tree=ast.parse(before),ast.parse(after)
    pack=next(n for n in new_tree.body if isinstance(n,ast.FunctionDef) and n.name=='pack')
    rows=[n for n in ast.walk(pack) if isinstance(n,ast.DictComp)]
    if len(rows)!=1:raise ValueError('Unexpected pack structure')
    expected=ast.parse("name.encode('utf-8').decode('utf-8')",mode='eval').body
    if ast.dump(rows[0].key)!=ast.dump(expected):
        raise ValueError('Not the qualified dictionary-key identity repair')
    rows[0].key=ast.Name(id='name',ctx=ast.Load())
    if ast.dump(old_tree)!=ast.dump(new_tree):
        raise ValueError('Transport change also alters non-key expressions')
    if not all(k.isascii() and k.encode('utf-8').decode('utf-8')==k for k in seq.FIELDS):
        raise ValueError('Payload key values changed')
    previous={}
    exec(compile(before,str(old_path),'exec'),previous)
    reference=request['owned'][2]
    checks=[]
    for tangent in (False,True):
        controls=[seq.first_action(reference) for _ in range(3)]
        if tangent:
            trace=ad.Trace([.1]*3,track_stencils=False)
            for k,c in enumerate(controls):
                key=next(iter(c.vsl))
                c.vsl[key]=ad.Dual(c.vsl[key],{k:1.},trace)
        old_plan,new_plan=previous['pack'](controls),seq.pack(controls)
        old_controls,new_controls=seq.actions(old_plan,3),seq.actions(new_plan,3)
        equal=pickle.dumps(old_controls,protocol=5)==pickle.dumps(new_controls,protocol=5)
        if not equal:raise ValueError('Decoded control values/tangents changed')
        checks.append(dict(tangent=tangent,decoded_controls_identical=True))
    data=pickle.dumps(seq.pack([reference]*3),protocol=5)
    if pickle.dumps(pickle.loads(data),protocol=5)!=data:
        raise ValueError('Transport still changes across pickle roundtrip')
    return dict(schema='sdmpc-transport-equivalence/v1',passed=True,
        derivative_source_sha256=expected_hash,
        native_source_sha256=hashlib.sha256(after).hexdigest(),
        only_change='Equal ASCII dictionary-key identity; all value expressions unchanged',
        decoded_control_checks=checks,repeat_derivative_rollout=False)
