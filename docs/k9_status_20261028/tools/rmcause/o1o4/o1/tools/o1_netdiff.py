r"""O1 provenance: compare RM vs NC3 .inpx per top-level section (read only). Also input volumes 1098/1099.
python -B o1_netdiff.py -> o1o4/o1/out/netdiff.json"""
import hashlib, json, os, sys
import xml.etree.ElementTree as ET
sys.dont_write_bytecode = True
ROOT = r'D:\VISSIM_runs\20261001_v3c3'
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'out')
os.makedirs(OUT, exist_ok=True)

def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()

def secs(p):
    r = ET.parse(p).getroot()
    out = {}
    for ch in r:
        out[ch.tag] = hashlib.sha256(ET.tostring(ch)).hexdigest()
    return r, out

res = {}
for s in (31, 41):
    rm = os.path.join(ROOT, 's%d_v3c3rm' % s, 'prepared', 'network', 'baseline_s%d_v3c3rm.inpx' % s)
    nc = os.path.join(ROOT, 's%d_v3c3nc' % s, 'prepared', 'network', 'baseline_s%d_v3c3nc.inpx' % s)
    r1, a = secs(rm)
    r2, b = secs(nc)
    diff = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
    vi = {}
    for r, tag in ((r1, 'rm'), (r2, 'nc')):
        for v in r.findall('./vehicleInputs/vehicleInput'):
            if v.get('no') in ('1098', '1099'):
                vols = [(tv.get('timeInt'), tv.get('volume'), tv.get('vehComp')) for tv in v.findall('./timeIntVehVols/timeIntervalVehVolume')]
                vi.setdefault(v.get('no'), {})[tag] = {'link': v.get('link'), 'vols': vols}
        sim = r.find('./simulation')
        vi.setdefault('simulation', {})[tag] = {k: sim.get(k) for k in ('randSeed', 'simRes', 'simPeriod')}
    res['s%d' % s] = {'rm': rm, 'nc': nc, 'rm_sha256': sha(rm), 'nc_sha256': sha(nc),
                      'sections_differing': diff, 'n_sections': [len(a), len(b)], 'inputs_1098_1099_and_sim': vi}
with open(os.path.join(OUT, 'netdiff.json'), 'w', encoding='utf-8') as f:
    json.dump(res, f, indent=1, ensure_ascii=False)
for k, v in res.items():
    print(k, v['rm_sha256'][:8], v['nc_sha256'][:8], v['sections_differing'], v['n_sections'])
    print(json.dumps(v['inputs_1098_1099_and_sim'])[:1500])
