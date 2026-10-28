"""Development generator (run once): append the guard fragment and the two codex functions (CX
evaluation/controllers/urban_storage_guard.py sha256 2c24b570..., constrain CX USG:102-145 and operating_seed CX
USG:148-166, copied by ast span with CR removed) to src_r2/c1_port.py.  Renames only: the function names, the read
attribute 'urban_storage_guard' -> 'c1_storage_capacity_guard', the receipt attribute urban_storage_receipt ->
c1_storage_capacity_receipt (amendment C1-2 section 5.6, G-K1 static (g))."""
import ast
import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CX_USG = Path(r'D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff/evaluation/controllers/urban_storage_guard.py')
CX_USG_SHA = '2c24b570ca5ba6f2a81d47b9eedfde1af863713fefd9a337109e2f78b64173ab'
RENAMES = [('def constrain(coord):', 'def constrain_storage_capacity(coord):'),
           ("getattr(coord.cfg.network, 'urban_storage_guard', None)",
            "getattr(coord.cfg.network, 'c1_storage_capacity_guard', None)"),
           ('coord.urban_storage_receipt', 'coord.c1_storage_capacity_receipt'),
           ('def operating_seed(coord, reference, policy):', 'def storage_capacity_seed(coord, reference, policy):')]


def cx_functions():
    raw = CX_USG.read_bytes()
    if hashlib.sha256(raw).hexdigest() != CX_USG_SHA:
        raise SystemExit('CX USG differs from its pin')
    text = raw.decode('utf-8').replace('\r\n', '\n')
    tree = ast.parse(text)
    out = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in ('constrain', 'operating_seed'):
            out[node.name] = '\n'.join(text.split('\n')[node.lineno - 1:node.end_lineno])
    return out


def main():
    target = HERE / 'src_r2' / 'c1_port.py'
    src = target.read_text(encoding='utf-8')
    if 'def storage_capacity_core' in src:
        raise SystemExit('already generated')
    frag = (HERE / 'src_r2' / '_guard_fragment.py.txt').read_text(encoding='utf-8')
    fx = cx_functions()
    block = '\n\n' + fx['constrain'] + '\n\n\n' + fx['operating_seed'] + '\n'
    for old, new in RENAMES:
        n = block.count(old)
        if n < 1:
            raise SystemExit('rename anchor missing: ' + old)
        block = block.replace(old, new)
    out = src.rstrip('\n') + '\n' + frag.rstrip('\n') + '\n' + block
    compile(out, 'c1_port.py', 'exec')
    target.write_text(out, encoding='utf-8', newline='\n')
    print('C1P_R2 sha256=%s lines=%d' % (hashlib.sha256(out.encode('utf-8')).hexdigest(), out.count('\n')))


if __name__ == '__main__':
    sys.dont_write_bytecode = True
    main()
