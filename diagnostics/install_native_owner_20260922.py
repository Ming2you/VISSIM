"""Remove the superseded per-step bridge after preserving its qualified source."""
import ast
from pathlib import Path
root=Path(__file__).resolve().parents[1]
path=root/'evaluation/controllers/sdmpc_tangent_urban.py'
lines=path.read_text().splitlines(keepends=True)
tree=ast.parse(''.join(lines))
owner=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Owner')
step=next(n for n in owner.body if isinstance(n,ast.FunctionDef) and n.name=='step')
assert step.end_lineno-step.lineno>80
replacement='''    def step(self,u,external,exit_receiving,indexed_lateral):
        from evaluation.controllers.sdmpc_tangent_urban_store import advance
        return advance(self,u,external,exit_receiving,indexed_lateral)
'''
path.write_text(''.join(lines[:step.lineno-1])+replacement+''.join(lines[step.end_lineno:]),encoding='utf-8')
