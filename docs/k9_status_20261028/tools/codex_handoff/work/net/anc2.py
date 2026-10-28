import xml.etree.ElementTree as ET
P={'v2':'v2nc.inpx','v3b':'v3bnc.inpx','v3c1':'v3c1nc.inpx','v3c2':'D:/VISSIM_runs/20260930_v3c2/s31_v3c2nc/prepared/network/baseline_s31_v3c2nc.inpx','v3c3':'D:/VISSIM-merge/sim3-n31-k8/diagnostics/sdmpc_n31_20260924/network/baseline_s31_v3c3nc.inpx','64cf':'D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff/diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'}
for k,p in P.items():
    r=ET.parse(p).getroot()
    vi={e.get('no'):e for e in r.find('vehicleInputs')}
    def s(no): 
        e=vi[no]; return [(t.get('vehComp'),t.get('volume')) for t in e.iter('timeIntervalVehVolume')]
    d110=[(x.get('x'),x.get('fx')) for e in r.find('desSpeedDistributions') if e.get('no')=='110' for x in e.iter('speedDistributionDataPoint')]
    dsd={e.get('no'):e for e in r.find('desSpeedDecisions')}
    pos63=dsd['63'].get('pos'); 
    comps=sorted(e.get('no') for e in r.find('vehicleCompositions'))
    ndcp=len(list(r.find('dataCollectionPoints')))
    dsds=sorted(int(e.get('no')) for e in r.find('desSpeedDistributions'))
    print(k,'1098',s('1098')[:2],'1099',s('1099')[:3]); print('   DSD110',d110,'| DSD63 pos',pos63[:9],'| comps',comps[-3:],'| nDCP',ndcp,'| DSD nos >=80',[x for x in dsds if x>=80])
