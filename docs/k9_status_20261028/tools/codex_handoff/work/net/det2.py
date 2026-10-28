import xml.etree.ElementTree as ET, json, copy, difflib
V='D:/VISSIM-merge/sim3-n31-k8/diagnostics/sdmpc_n31_20260924/network/baseline_s31_v3c3nc.inpx'
C='D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff/diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'
def norm(e):
    e=copy.deepcopy(e)
    for x in e.iter():
        x.text=(x.text or '').strip() or None; x.tail=None
    return ET.tostring(e,encoding='unicode')
a=ET.parse(V).getroot(); b=ET.parse(C).getroot()
ea=list(a.find('evaluation')); eb=list(b.find('evaluation'))
for i,(x,y) in enumerate(zip(ea,eb)):
    nx,ny=norm(x),norm(y)
    if nx!=ny:
        print('== eval child',i,x.tag)
        print('  V',x.attrib); print('  C',y.attrib)
        sx=[ET.tostring(c,encoding='unicode').strip() for c in x.iter() if c is not x]; sy=[ET.tostring(c,encoding='unicode').strip() for c in y.iter() if c is not y]
        if len(sx)<60:
            for l in difflib.unified_diff([s[:200] for s in sx],[s[:200] for s in sy],lineterm='',n=0): print('   ',l)
        else: print('   children',len(sx),len(sy))
