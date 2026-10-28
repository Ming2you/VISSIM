p = 'tools/inv_build.py'
s = open(p, encoding='utf-8').read()
old = """                   plant_storage_key=l2o.get(link),
                   plant_storage_cap_veh={k: storage_key_cap.get(k) for k in (l2o.get(link) or [])},"""
new = """                   plant_storage_key=l2o.get(link),
                   plant_storage_cap_veh={k: storage_key_cap.get(k) for k in (l2o.get(link) or [])},
                   plant_movements=[dict(movement=m['movement'], weight=m.get('weight'), source=m.get('source'),
                                         phase=(net['urban_movements'].get(m['movement']) or {}).get('phase'))
                                    for m in (det.get('link_to_movements', {}).get(link) or [])],"""
assert old in s
s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8').write(s)
print('patched5')
