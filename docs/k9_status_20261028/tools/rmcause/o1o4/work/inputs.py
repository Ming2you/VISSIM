# -*- coding: utf-8 -*-
"""Read vehicle inputs (1098, 1099 and totals) from an inpx (read-only)."""
import sys, re, xml.etree.ElementTree as ET
p = sys.argv[1]
root = ET.parse(p).getroot()
vi = root.find('vehicleInputs')
out = {}
for v in vi.findall('vehicleInput'):
    no = v.get('no'); link = v.get('link')
    vols = []
    for tv in v.iter('timeIntervalVehVolume'):
        vols.append((tv.get('timeInt'), tv.get('volume'), tv.get('vehComp'), tv.get('volType')))
    out[no] = (link, v.get('name'), vols)
tot = 0.0
for no in sorted(out, key=lambda x: int(x)):
    link, name, vols = out[no]
    if no in ('1098', '1099') or sys.argv[2:] == ['all']:
        print(no, link, name, vols)
    tot += sum(float(x[1]) for x in vols[:1])
print('n_inputs', len(out), 'sum_first_interval_vph', round(tot, 1))
ti = root.find('timeIntervalSets')
for s in ti.findall('timeIntervalSet'):
    print('TIS', s.get('no'), [(t.get('start')) for t in s.iter('timeInterval')][:12])
