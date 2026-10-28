# vc_fzp1099.py -- independent FZP scan for the input-1099 / link-26 chain (verify_c V3). Read-only.
# One FZP per call of scan(); main() runs the six runs one after another (one process, one at a time).
import json, sys, time, collections

FR = 5.0
NF = 1801            # frames 5.1 ... 9000.1 -> index round((t-0.1)/5)
NB = 30              # 300 s bins 0..9000

def is_conn(l):
    return 10000 <= l <= 10999

def scan(path, out_path):
    t0 = time.time()
    first = {}                     # vid -> (t, link)
    last_main = {}                 # vid -> last main (non-connector) link
    trans = collections.Counter()  # (from,to,bin300)
    trans_t = collections.defaultdict(list)   # (from,to) -> times (for selected pairs)
    keep_pairs = {(26, 125), (26, 129), (26, 120), (124, 26), (127, 30), (2, 127), (129, 127), (129, 119)}
    zeros = lambda: [0] * NF
    ser = {k: zeros() for k in ('slow127', 'slow129L1_150', 'slow10491', 'slow26L1_3500', 'slow26L1', 'slow120',
                                 'n124', 'slow10480', 'n10480', 'slow10490', 'slow129', 'n26', 'n127')}
    # link 127 0-50 m lanes 1,2 speed sums per 300 s bin
    s127 = [[0.0, 0] for _ in range(NB)]
    # link 26 lane 1 grid: 100 m cells x 300 s bins
    g26 = [[[0.0, 0] for _ in range(40)] for _ in range(NB)]
    nrows = 0; frac = collections.Counter(); bad = 0
    with open(path, 'r', encoding='latin-1') as f:
        for line in f:
            c0 = line[:1]
            if not ('0' <= c0 <= '9'):
                continue
            p = line.split(';', 7)
            try:
                t = float(p[0]); vid = int(p[1]); link = int(p[2]); lane = int(p[3]); pos = float(p[4]); spd = float(p[6])
            except (ValueError, IndexError):
                bad += 1; continue
            nrows += 1
            if vid not in first:
                first[vid] = (t, link)
            if not is_conn(link):
                lm = last_main.get(vid)
                if lm is not None and lm != link:
                    pr = (lm, link)
                    b = min(int(t // 300), NB - 1)
                    trans[(lm, link, b)] += 1
                    if pr in keep_pairs:
                        trans_t[pr].append(t)
                last_main[vid] = link
            fi = int(round((t - 0.1) / FR))
            on_grid = abs(t - (0.1 + fi * FR)) < 1e-6 and 0 <= fi < NF
            frac[on_grid] += 1
            if not on_grid:
                continue
            slow = spd < 10.0
            if link == 127:
                ser['n127'][fi] += 1
                if slow: ser['slow127'][fi] += 1
                if pos < 50.0 and lane in (1, 2):
                    b = min(int(t // 300), NB - 1); s127[b][0] += spd; s127[b][1] += 1
            elif link == 129:
                if slow:
                    ser['slow129'][fi] += 1
                    if lane == 1 and pos >= 150.0: ser['slow129L1_150'][fi] += 1
            elif link == 10491:
                if slow: ser['slow10491'][fi] += 1
            elif link == 26:
                ser['n26'][fi] += 1
                if lane == 1:
                    if slow:
                        ser['slow26L1'][fi] += 1
                        if pos >= 3500.0: ser['slow26L1_3500'][fi] += 1
                    b = min(int(t // 300), NB - 1); cidx = min(int(pos // 100), 39)
                    g26[b][cidx][0] += spd; g26[b][cidx][1] += 1
            elif link == 120:
                if slow: ser['slow120'][fi] += 1
            elif link == 124:
                ser['n124'][fi] += 1
            elif link == 10480:
                ser['n10480'][fi] += 1
                if slow: ser['slow10480'][fi] += 1
            elif link == 10490:
                if slow: ser['slow10490'][fi] += 1
    ins = sorted(t for (t, l) in first.values() if l == 26)
    S = sum(9000.0 - t for t in ins if t <= 9000.0) / 3600.0
    out = {'path': path, 'rows': nrows, 'bad_rows': bad, 'on_grid': {str(k): v for k, v in frac.items()},
           'vehicles': len(first), 'ins1099_times': ins, 'S1099_W9000_vehh': S,
           'first_link_counts_top': collections.Counter(l for (_, l) in first.values()).most_common(12),
           'series': ser, 's127_L12_0_50': s127, 'g26L1': g26,
           'trans_bins': {f'{a}>{b}>{k}': v for (a, b, k), v in trans.items() if (a, b) in keep_pairs},
           'trans_times': {f'{a}>{b}': v for (a, b), v in trans_t.items()},
           'sec': round(time.time() - t0, 1)}
    json.dump(out, open(out_path, 'w', encoding='utf-8'))
    return out['sec'], nrows

RUNS = {
    'b31': 'D:/VISSIM_runs/20261026_codex_b_v3c3/s31/sdmpc/vissim_eval/sdmpc31_sdmpc9000_s31_001.fzp',
    'nc31': 'D:/VISSIM_runs/20261001_v3c3/s31_v3c3nc/run/vissim_eval/baseline_s31_v3c3nc_001.fzp',
    'va31': 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s31/vissim_eval/sdmpc31_sdmpc31_v3c3_k92va_s31_001.fzp',
    'b43': 'D:/VISSIM_runs/20261026_codex_b_v3c3/s43/sdmpc/vissim_eval/sdmpc31_sdmpc9000_s43_001.fzp',
    'nc43': 'D:/VISSIM_runs/20261001_v3c3/s43_v3c3nc/run/vissim_eval/baseline_s43_v3c3nc_001.fzp',
    'va43': 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s43/vissim_eval/sdmpc31_sdmpc31_v3c3_k92va_s43_001.fzp',
}

if __name__ == '__main__':
    outdir = sys.argv[1]
    log = open(outdir + '/fzp_scan.log', 'a', encoding='utf-8')
    for tag, p in RUNS.items():
        log.write(f'{time.strftime("%H:%M:%S")} start {tag}\n'); log.flush()
        sec, n = scan(p, f'{outdir}/fzp_{tag}.json')
        log.write(f'{time.strftime("%H:%M:%S")} done {tag} rows={n} sec={sec}\n'); log.flush()
    log.write('ALL_DONE\n'); log.close()
