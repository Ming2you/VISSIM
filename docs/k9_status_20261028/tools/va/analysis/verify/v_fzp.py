# 검증자 자체 FZP 한 번 읽기 (J1 검증 v_fzp.py 꼴): 프레임×링크 대수 행렬, 첫 관측, 국소 지표, DESSPEED 첫 진입.
# 사용: python -B v_fzp.py <tag> --profile va|selftest   (읽기 전용 open, 쓰기는 verify/<out>/<tag>/ 만)
# DESSPEED 첫 진입의 표지 위치는 0.1 m 반올림(J1 검증 v_dess_round.py 와 같은 읽기: 시작 = 반올림 머리, 끝 = 다음 머리 원값).
import bisect, json, os, sys, time
import numpy as np
from v_common import runs, profile, out_dir, parse_inpx, chains, sign_positions, below_normal, jd

below_normal()
tag = sys.argv[1]
prof = profile()
R = runs(prof)[tag]
od = os.path.join(out_dir(prof), tag)
os.makedirs(od, exist_ok=True)
t0 = time.time()
net = parse_inpx(R['inpx'])
ch = chains()
signs = sign_positions(net, ch)
link_ids = sorted(net['links'])
idx = {str(l).encode(): i for i, l in enumerate(link_ids)}
L0 = len(link_ids)
extra = {}
FWE = {str(l).encode(): ch['FW_E']['offs'][l] for l in ch['FW_E']['links']}
FWW = {str(l).encode(): ch['FW_W']['offs'][l] for l in ch['FW_W']['links']}
zheads = {}
for d in ('FW_E', 'FW_W'):
    zheads[d] = sorted((signs[z][0], z) for z in signs if z.startswith(d + '__') and signs[z])
zone_names = {d: [z for _, z in zheads[d]] for d in zheads}
P_raw = [h for h, _ in zheads['FW_E']]
P_E = [round(x, 1) for x in P_raw]
E_E = P_raw[1:] + [ch['FW_E']['length']]
frames_t, counts, n127_12, spW, spE, rows_per_frame = [], [], [], [], [], []
seen, dstate, drec, skipped = {}, {}, [], {}
cur_tb = None
cur = None
rows = 0
D = b'0123456789'
hdr = None
with open(R['fzp'], 'rb', buffering=1 << 22) as f:
    for raw in f:
        if raw[:9] == b'$VEHICLE:':
            hdr = raw[9:].strip().decode('ascii').split(';')
            ix = {n: hdr.index(n) for n in ('SIMSEC', 'NO', 'LANE\\LINK\\NO', 'LANE\\INDEX', 'POS', 'SPEED',
                                             'TMINNETTOT', 'DESSPEED', 'ROUTDECNO', 'ROUTENO')}
            assert [ix[k] for k in ('SIMSEC', 'NO', 'LANE\\LINK\\NO', 'LANE\\INDEX', 'POS', 'SPEED', 'TMINNETTOT',
                                     'DESSPEED', 'ROUTDECNO', 'ROUTENO')] == [0, 1, 2, 3, 4, 6, 7, 9, 11, 12], ix
            continue
        if not raw or raw[0] not in D:
            continue
        p = raw.split(b';', 13)
        tb = p[0]
        if tb != cur_tb:
            tf = float(tb)
            if tf < 5.0:  # 0.10 s 행 제외 (K7 §3.6)
                skipped[tb.decode()] = skipped.get(tb.decode(), 0) + 1
                continue
            if cur is not None:
                frames_t.append(cur_t); counts.append(np.asarray(cur, dtype=np.int32))
                n127_12.append(c127); spW.append(fw); spE.append(fe); rows_per_frame.append(crow)
            cur_tb = tb
            cur_t = tf
            cur = [0] * (L0 + len(extra) + 64)
            c127 = 0; fw = False; fe = False; crow = 0
        rows += 1
        crow += 1
        lk = p[2]
        i = idx.get(lk)
        if i is None:
            if lk not in extra:
                extra[lk] = L0 + len(extra)
            i = extra[lk]
            if i >= len(cur):
                cur.extend([0] * (i + 1 - len(cur)))
        cur[i] += 1
        no = p[1]
        if no not in seen:
            seen[no] = (cur_t, lk, p[7])
        if lk in FWE:
            cp = FWE[lk] + float(p[4]); sp = float(p[6])
            pm = dstate.get(no)
            for zi in range(len(P_E)):
                if P_E[zi] <= cp < E_E[zi]:
                    key = (no, zi)
                    if key not in dstate:
                        dstate[key] = 1
                        drec.append((int(no), zi, cur_t, float(p[9]) if p[9] else -1.0, int(pm is not None and pm < P_E[zi])))
                    break
            if pm is None or cp < pm:
                dstate[no] = cp
            if lk == b'2' and not fe:
                if p[3] == b'1' and 3950 <= float(p[4]) <= 4092.3 and p[11] == b'1131' and p[12] == b'2' and sp < 15:
                    fe = True
        elif lk in FWW:
            sp = float(p[6])
            if lk == b'26' and not fw:
                if p[3] == b'1' and 3550 <= float(p[4]) <= 3651 and p[11] == b'1132' and p[12] == b'2' and sp < 15:
                    fw = True
        elif lk == b'10491':
            if not fw and float(p[4]) <= 30 and float(p[6]) < 15:
                fw = True
        elif lk == b'10481':
            if not fe and float(p[4]) <= 30 and float(p[6]) < 15:
                fe = True
        elif lk == b'127':
            if p[3] == b'1' or p[3] == b'2':
                c127 += 1
    if cur is not None:
        frames_t.append(cur_t); counts.append(np.asarray(cur, dtype=np.int32))
        n127_12.append(c127); spW.append(fw); spE.append(fe); rows_per_frame.append(crow)
L = L0 + len(extra)
M = np.zeros((len(counts), L), dtype=np.int32)
for k, a in enumerate(counts):
    M[k, :] = a[:L]
ids_all = link_ids + [int(k) for k in extra]


def tmf(b):
    try:
        return float(b)
    except ValueError:
        return float('nan')


seen_no = np.array([int(k) for k in seen], dtype=np.int64)
seen_t = np.array([v[0] for v in seen.values()])
seen_lk = np.array([int(v[1]) for v in seen.values()], dtype=np.int64)
seen_tm = np.array([tmf(v[2]) for v in seen.values()])
dr = np.array(drec, dtype=np.float64) if drec else np.zeros((0, 5))
np.savez_compressed(os.path.join(od, 'fzp.npz'), t=np.array(frames_t), M=M, link_ids=np.array(ids_all, dtype=np.int64),
                    n127_12=np.array(n127_12), spW=np.array(spW), spE=np.array(spE),
                    seen_no=seen_no, seen_t=seen_t, seen_lk=seen_lk, seen_tm=seen_tm,
                    rows_per_frame=np.array(rows_per_frame))
np.save(os.path.join(od, 'drec_round.npy'), dr)
meta = dict(tag=tag, profile=prof, fzp=R['fzp'], fzp_bytes=os.path.getsize(R['fzp']), rows=rows, frames=len(frames_t),
            first=frames_t[0], last=frames_t[-1], skipped_rows=skipped, extra_links=[int(k) for k in extra],
            zone_names=zone_names, P_E_round=P_E, E_E=E_E, n_seen=len(seen), header=hdr, sec=time.time() - t0)
jd(meta, os.path.join(od, 'fzp_meta.json'))
print(json.dumps({k: meta[k] for k in ('tag', 'rows', 'frames', 'first', 'last', 'skipped_rows', 'extra_links', 'n_seen', 'sec')}))
