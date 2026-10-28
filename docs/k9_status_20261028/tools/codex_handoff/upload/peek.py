import csv, io, os
root = 'Y:/99_임시휴지통/20261024'
p = os.path.join(root, 'FILE_MANIFEST.csv')
with io.open(p, encoding='utf-8-sig', newline='') as f:
    rows = list(csv.reader(f))
print('header', rows[0])
print('rows', len(rows) - 1)
for r in rows[1:4]:
    print(r)
