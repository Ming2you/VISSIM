import csv,collections,sys
fn=r'D:/VISSIM-runs-window264-s29-9000-recovery-20261007/sdmpc/action_sdmpc31_sdmpc9000_s29.csv'
rows=[r for r in csv.DictReader(open(fn,encoding='utf-8',errors='replace'))]
kinds=collections.Counter(r['kind'] for r in rows)
print('kinds',kinds)
m=[r for r in rows if r['kind'] not in ('vsl',) and r['green_sec']]
ids=collections.Counter(r['id'] for r in m)
print('meter-ish ids',ids)
by=collections.defaultdict(dict)
for r in m:
    by[r['id']][int(r['sim_sec'])]=float(r['green_sec'])
for k,d in sorted(by.items()):
    ts=sorted(d)
    lt=[t for t in ts if d[t]<10]
    vals=[d[t] for t in lt]
    print(k,'n_dec',len(ts),'lt10',len(lt), 'range', (min(vals),max(vals)) if vals else None, 'first<10', lt[:1], 'rate example', [r['rate_vph'] for r in m if r['id']==k][:1])
print('decision times', len(set(int(r['sim_sec']) for r in m)), min(int(r['sim_sec']) for r in m), max(int(r['sim_sec']) for r in m))
