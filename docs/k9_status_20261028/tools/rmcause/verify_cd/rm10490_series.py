"""VERIFY_code-data: RM_C10490 block-0 total gradient vs model dNUF/dz and predicted merge, per decision (read-only)."""
import ctypes, glob, json, os, sys
try:
    ctypes.windll.kernel32.SetPriorityClass(ctypes.c_void_p(-1), 0x4000)
except Exception:
    pass
run, tag = sys.argv[1].rstrip('/\\'), sys.argv[2]
name = os.path.basename(run)
dec = os.path.join(run, 'decisions_' + name)
rows = []
for jp in sorted(glob.glob(os.path.join(dec, 'action_*.joint.json'))):
    T = int(os.path.basename(jp)[7:13])
    s = json.load(open(jp, encoding='utf-8-sig'))['selection']
    co = s['coordinates']; n = len(co); gr = s['gradient_rows']
    r0 = [r for r in gr[:n] if r['kind'] == 'meter' and r['key'] == 'RM_C10490' and r['block'] == 0][0]
    rows.append(dict(T=T, total=r0['total'], own=r0['own'], dNUF_dz=r0['resource_derivatives_scaled'][1] * 1000.0,
                     merge=s['budget_initialization']['accepted_rate_veh_h_by_ramp']['RM_C10490']))
json.dump(rows, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', f'rm10490_{tag}.json'), 'w'), indent=1)
big = sorted(rows, key=lambda r: r['total'])[:6]
print(tag, 'most "open" decisions:')
for r in big: print('  T=%d total=%.3f own=%.3f dNUF/dz=%.3f merge=%.1f' % (r['T'], r['total'], r['own'], r['dNUF_dz'], r['merge']))
print('  decisions with dNUF/dz>1:', [(r['T'], round(r['dNUF_dz'], 1), round(r['merge'], 1)) for r in rows if r['dNUF_dz'] > 1])
