# probe: read FZP header + first 3000 data rows only (format check for the verify parser). Read-only.
import sys
import pandas as pd
p = sys.argv[1]
n = 0
with open(p, 'rb') as f:
    for i, line in enumerate(f):
        if line.startswith(b'$VEHICLE:'):
            hdr = line.decode('latin-1').strip(); n = i + 1; break
cols = hdr.split(':', 1)[1].split(';')
print(n, len(cols), cols[:8])
BS = chr(92)
want = ['SIMSEC', 'NO', 'LANE' + BS + 'LINK' + BS + 'NO', 'LANE' + BS + 'INDEX', 'POS', 'SPEED']
idx = {c: cols.index(c) for c in want}
print(idx)
df = pd.read_csv(p, sep=';', header=None, skiprows=n, usecols=list(idx.values()), nrows=3000, engine='c', encoding='latin-1')
print(df.dtypes); print(df.head()); print(df.tail(3))
with open(p, 'rb') as f:
    for i, line in enumerate(f):
        if i in (n, n + 1):
            print(repr(line[:200]))
        if i > n + 1:
            break
