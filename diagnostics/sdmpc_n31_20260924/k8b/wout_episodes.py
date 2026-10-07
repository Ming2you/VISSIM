"""W_out entry class x destination episodes from FZP rows (VISSIM side; diagnostics only, no runtime import).

The rule of K8_PREDECLARATION_AMENDMENT_16 r2 section 2.4.2, written before its first run in the scratch script
k8b_decl/p4b_split.py (sha 53e0b556...); the functions below are that script's token / episodes / seed_rows / split
unchanged (same names, same order of tests), so build_k8b_evidence.py p4 and the harness (sa_vissim_ref.py) count
with one rule:

Tokens per FZP record (5 s frames), in time order per vehicle, consecutive duplicates collapsed:
  S      LINK in {29, 37, 40, 10119, 10121, 10698}    SC1001 approach exits feeding link 31 (signal origin)
  SIDE   LINK in {78, 10703}                          side street landing on 31 @350.7 m
  DUP    LINK == 119                                  OR_D_E collector upstream of the 10483 diverge (392.3 m)
  DC     LINK == 10483                                direct landing connector (119 @392.3 -> 124 @201.15)
  W      LINK in {31, 10774, 124}                     W_out (links 31 + 124)
  E      LINK in {10484, 24}                          R_D_E (31 @412.09 -> 24)
  E2     LINK == 10702                                119 -> 24 (not W_out)
  RW     LINK in {10480, 10491} or (LINK == 26 and 3600 <= POS <= 4200)   R_D_W (124 @321.61 -> 26 @3625.8)
  F      LINK in {10775, 125}                         free exit (124 end -> tail 125)
  X      LINK in {10704, 79}                          side exit (31 @281.2 -> 79)
Episode = a maximal run of {W, DC} tokens, or an empty episode when DUP is directly followed by RW or F.
  class        direct if the run contains DC or the token before it is DUP; else signal if the token before it is S;
               else side if the token before it is SIDE; else unknown_entry.
  destination  token after the run: E -> R_D_E, RW -> R_D_W, F -> free, X -> side_exit; else unknown_dest.
  entry time   SIMSEC of the first token of the run (empty episode: of the token after DUP).
  exit time    SIMSEC of the destination token (dest_t; None for unknown_dest) -- used by the harness only.
Anomalies (counted, excluded): direct with destination R_D_E or side_exit, a run containing DC whose token before it
is not DUP.  split(): s_c[d] = n(c, d) / N_c over d in {R_D_E, R_D_W, free'}, free' = free + side_exit."""
from collections import Counter

DESTS = ('R_D_E', 'R_D_W', 'free', 'side_exit')
DEST_OF = {'E': 'R_D_E', 'RW': 'R_D_W', 'F': 'free', 'X': 'side_exit'}


def token(link, pos):
    if link in (29, 37, 40, 10119, 10121, 10698):
        return 'S'
    if link in (78, 10703):
        return 'SIDE'
    if link == 119:
        return 'DUP'
    if link == 10483:
        return 'DC'
    if link in (31, 10774, 124):
        return 'W'
    if link in (10484, 24):
        return 'E'
    if link == 10702:
        return 'E2'
    if link in (10480, 10491) or (link == 26 and 3600.0 <= pos <= 4200.0):
        return 'RW'
    if link in (10775, 125):
        return 'F'
    if link in (10704, 79):
        return 'X'
    return None


def episodes(seq):
    """seq = [(token, t, link)] collapsed.  Yields (class, dest, entry_t, anomaly, dest_t)."""
    i, n = 0, len(seq)
    while i < n:
        tok = seq[i][0]
        if tok in ('W', 'DC'):
            j = i
            while j < n and seq[j][0] in ('W', 'DC'):
                j += 1
            run = [s[0] for s in seq[i:j]]
            before = seq[i - 1][0] if i > 0 else None
            after = seq[j][0] if j < n else None
            has_dc = 'DC' in run
            anomaly = None
            if has_dc or before == 'DUP':
                cls = 'direct'
                if has_dc and before != 'DUP' and before is not None:
                    anomaly = 'dc_without_dup_before'
            elif before == 'S':
                cls = 'signal'
            elif before == 'SIDE':
                cls = 'side'
            else:
                cls = 'unknown_entry'
            dest = DEST_OF.get(after, 'unknown_dest')
            if cls == 'direct' and dest in ('R_D_E', 'side_exit'):
                anomaly = anomaly or f'direct_to_{dest}'
            yield cls, dest, seq[i][1], anomaly, (seq[j][1] if j < n and dest != 'unknown_dest' else None)
            i = j
            continue
        if tok == 'DUP' and i + 1 < n and seq[i + 1][0] in ('RW', 'F'):
            yield 'direct', DEST_OF[seq[i + 1][0]], seq[i + 1][1], None, seq[i + 1][1]
            i += 1
            continue
        i += 1


def seed_rows(df, seed):
    """Episodes of one seed's W_out extract (columns SIMSEC, NO, LINK, POS): [(seed, no, class, dest, entry_t,
    anomaly, dest_t)] in vehicle order (mergesort on NO, SIMSEC as the scratch script)."""
    df = df.sort_values(['NO', 'SIMSEC'], kind='mergesort')
    rows = []
    for no, g in df.groupby('NO', sort=False):
        seq = []
        for t, link, pos in zip(g['SIMSEC'].to_numpy(), g['LINK'].to_numpy(), g['POS'].to_numpy()):
            tok = token(int(link), float(pos))
            if tok is None:
                continue
            if seq and seq[-1][0] == tok:
                continue
            seq.append((tok, float(t), int(link)))
        for cls, dest, t_in, anomaly, t_dest in episodes(seq):
            rows.append((seed, int(no), cls, dest, t_in, anomaly, t_dest))
    return rows


def split(counter):
    out = {}
    for cls in ('signal', 'direct'):
        n = {d: counter.get((cls, d), 0) for d in DESTS}
        n_free2 = n['free'] + n['side_exit']
        N = n['R_D_E'] + n['R_D_W'] + n_free2
        out[cls] = {'n': n, 'N': N,
                    's': ({'R_D_E': n['R_D_E'] / N, 'R_D_W': n['R_D_W'] / N, 'free': n_free2 / N} if N else None)}
    return out


def pooled_counter(rows, lo=900.0, hi=9000.0):
    """(kept rows in [lo, hi), anomaly counter, pooled (class, dest) counter of the clean kept rows)."""
    kept = [r for r in rows if lo <= r[4] < hi]
    anomalies = Counter(r[5] for r in kept if r[5])
    clean = [r for r in kept if not r[5]]
    return kept, anomalies, clean, Counter((r[2], r[3]) for r in clean)
