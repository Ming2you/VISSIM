"""Append a UTF-8 text file to rmcause/LOG.md (no other writes)."""
import io
import sys
from pathlib import Path

LOG = Path(__file__).resolve().parents[2] / 'LOG.md'
text = io.open(sys.argv[1], encoding='utf-8').read()
if not text.endswith('\n'):
    text += '\n'
with io.open(LOG, 'a', encoding='utf-8', newline='\n') as f:
    f.write(text)
print('appended', len(text), 'chars to', LOG)
