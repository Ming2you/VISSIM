import xml.etree.ElementTree as ET, json, collections
V='D:/VISSIM-merge/sim3-n31-k8/diagnostics/sdmpc_n31_20260924/network/baseline_s31_v3c3nc.inpx'
C='D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff/diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'
a=ET.parse(V).getroot(); b=ET.parse(C).getroot()
inv=json.load(open('inv2.json'))
dc={e.get('no'):e for e in b.find('dataCollectionPoints')}
rows=[]
for k in inv['dataCollectionPoints']['only_64cf']:
    e=dc[k]; rows.append((int(k),e.get('lane'),e.get('pos'),e.get('name')))
rows.sort()
for r in rows: print(r)
dm={e.get('no'):e for e in b.find('dataCollectionMeasurements')}
print('--- measurements only 64cf')
for k in inv['dataCollectionMeasurements']['only_64cf'][:70]:
    e=dm[k]; pts=[x.get('key') or x.text or x.attrib for x in e.iter() if x is not e]
    print(k,e.get('name'),str(pts)[:120])
print('v3c3 DCP no range', min(int(e.get('no')) for e in a.find('dataCollectionPoints')), max(int(e.get('no')) for e in a.find('dataCollectionPoints')))
