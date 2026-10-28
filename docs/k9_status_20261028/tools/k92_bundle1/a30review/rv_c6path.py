"""ReviewDeclare A30: check30 C6 pin-string membership when the driver runs from KI/launch.ps1 (KI/../a30decl)."""
import hashlib
from pathlib import Path

BS = chr(92)
KB = Path(__file__).resolve().parent.parent
p = Path(str(KB / 'impl') + BS + '..' + BS + 'a30decl' + BS + 'k92t30.py').resolve()
j = p.parent / 'k92t30_judge.py'
txt = (KB / 'a30decl' / 'a30_pins.expected.sha256').read_text(encoding='utf-8')
for q in (p, j):
    m = '%s *%s' % (hashlib.sha256(q.read_bytes()).hexdigest(), str(q).replace(BS, '/'))
    print(m in txt, q.name, str(q)[:3])
