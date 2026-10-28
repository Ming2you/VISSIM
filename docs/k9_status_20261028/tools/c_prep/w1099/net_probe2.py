# net_probe2.py — 신호 머리·차량 입력·경로 결정·속도 결정을 FW_W 둘레에서 읽기만 함 (탐색용)
import sys, xml.etree.ElementTree as ET, json, re
p = sys.argv[1]
root = ET.parse(p).getroot()
def tag(e): return e.tag.split('}')[-1]
L = json.load(open('out/net_links.json'))
focus = {'26','120','10771','124','125','129','32','121','69','10479','10480','10482','10491','10490','10646','10644','10775','10778','10777','10483','10774','127','31','119'}
# successors of 125,127,129
for k,v in L.items():
    if v['from'] and v['from'].split()[0] in ('125','127','31','119') :
        print('conn', k, 'from', v['from'], v['fromPos'], '->', v['to'], v['toPos'], 'lanes', v['n_lanes'])
for e in root.iter():
    t = tag(e)
    if t == 'signalHead':
        lane = e.get('lane'); 
        if lane and lane.split()[0] in focus:
            print('SH', e.get('no'), e.get('name'), 'lane', lane, 'pos', e.get('pos'), 'sg', e.get('sg'))
    if t == 'vehicleInput' and e.get('no') in ('1099','1098'):
        print('VI', e.get('no'), e.get('name'), 'link', e.get('link'))
        for vol in e.iter():
            if tag(vol) == 'timeIntervalVehVolume':
                print('   ', {k: vol.get(k) for k in ('timeInt','volume','vehComp','volType','cont')})
    if t == 'vehicleRoutingDecisionStatic':
        if e.get('link') in focus:
            print('RD', e.get('no'), e.get('name'), 'link', e.get('link'), 'pos', e.get('pos'), 'allVehTypes', e.get('allVehTypes'))
            for r in e.iter():
                if tag(r) == 'vehicleRouteStatic':
                    print('    route', r.get('no'), 'dest', r.get('destLink'), r.get('destPos'), 'relFlow', r.get('relFlow'))
    if t in ('desiredSpeedDecision','reducedSpeedArea'):
        if e.get('lane') and e.get('lane').split()[0] in focus:
            print(t, e.get('no'), 'lane', e.get('lane'), 'pos', e.get('pos'))
    if t == 'timeInterval':
        pass
for e in root.iter():
    if tag(e) == 'timeIntervalSet':
        print('TIS', e.get('no'), [ (ti.get('no'), ti.get('start')) for ti in e.iter() if tag(ti)=='timeInterval'][:40])
