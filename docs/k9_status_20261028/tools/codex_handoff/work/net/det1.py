import xml.etree.ElementTree as ET, json
V='D:/VISSIM-merge/sim3-n31-k8/diagnostics/sdmpc_n31_20260924/network/baseline_s31_v3c3nc.inpx'
C='D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff/diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'
a=ET.parse(V).getroot(); b=ET.parse(C).getroot()
inv=json.load(open('inv.json'))
def get(r,tag,no):
    for e in r.find(tag):
        if e.get('no')==no: return e
print('SIM v3c3', a.find('simulation').attrib); print('SIM 64cf', b.find('simulation').attrib)
for tag in ['vehicleInputs','vehicleCompositions','desSpeedDistributions','desSpeedDecisions','evaluation']:
    for k in inv[tag]['differ']+inv[tag]['only_v3c3']:
        ea=get(a,tag,k); eb=get(b,tag,k)
        print('=====',tag,k)
        print(' V:',ET.tostring(ea,encoding='unicode')[:1500] if ea is not None else None)
        print(' C:',ET.tostring(eb,encoding='unicode')[:1500] if eb is not None else None)
