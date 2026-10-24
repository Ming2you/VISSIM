"""Verify recursive SHA256SUMS files; does not run a simulation."""
import argparse,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('folder',type=Path);a=p.parse_args();n=0
for manifest in a.folder.rglob('SHA256SUMS.txt'):
 if '.git' in manifest.parts:continue
 for line in manifest.read_text(encoding='utf-8').splitlines():
  if not line or line.startswith('#'):continue
  expected,rel=line.split('  ',1);q=manifest.parent/rel
  h=hashlib.sha256()
  with q.open('rb') as f:
   for chunk in iter(lambda:f.read(8*1024**2),b''):h.update(chunk)
  if h.hexdigest()!=expected:raise SystemExit('MISMATCH '+str(q))
  n+=1
print('PASS',n,'checks')
