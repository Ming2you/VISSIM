"""Preserve pre-edit unchanged line endings; verify AST identity of formatting."""
import ast
import difflib
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
rows={}
for name in ('shared_approach','sc2001_corridor','route_choice_corridor'):
    path=Path('evaluation/controllers')/(name+'.py')
    old=(HERE/'before'/(name+'.py.before_distance.txt')).read_bytes()
    current=path.read_bytes()
    archive=HERE/'before'/(name+'.py.direct_executed.txt')
    if archive.exists():
        raise FileExistsError(archive)
    archive.write_bytes(current)
    a=old.decode('utf-8').splitlines(keepends=True)
    b=current.decode('utf-8').splitlines(keepends=True)
    diff=difflib.SequenceMatcher(a=[s.rstrip('\r\n') for s in a],b=[s.rstrip('\r\n') for s in b],autojunk=False)
    result=[]
    for tag,i,j,k,l in diff.get_opcodes():
        if tag=='equal':
            result.extend(a[i:j])
        elif tag!='delete':
            ending='\r\n' if a[min(i,len(a)-1)].endswith('\r\n') else '\n'
            result.extend(s.rstrip('\r\n')+ending for s in b[k:l])
    normalized=''.join(result)
    assert ast.dump(ast.parse(normalized))==ast.dump(ast.parse(current.decode('utf-8')))
    path.write_bytes(normalized.encode('utf-8'))
    rows[name]=dict(executed_sha256=hashlib.sha256(current).hexdigest(),
        current_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        archive=str(archive),ast_identical=True)
(HERE/'source_newlines.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print(json.dumps(rows,indent=2))
