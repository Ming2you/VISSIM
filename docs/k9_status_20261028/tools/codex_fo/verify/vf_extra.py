# vf_extra.py - VERIFY_FO extra raw-file counts (2026-10-28 KST). Written AFTER reading FO_REPORT (to cover cells it cites);
# reads only raw run files (decision CSVs, signal_readback.csv, run logs, VISSIM .err). Light (no FZP). New code.
# usage: python -B vf_extra.py <out_json>
import sys, os, json, csv, glob, re, statistics
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vf_runfiles import states_per_second

SEEDS = [31, 41, 43]
RUNS = {
    'FO': ('D:/VISSIM_runs/20261028_codex_fo_v3c3/s{s}/sdmpc', 'sdmpc31_sdmpc9000_s{s}'),
    'B': ('D:/VISSIM_runs/20261026_codex_b_v3c3/s{s}/sdmpc', 'sdmpc31_sdmpc9000_s{s}'),
}
NC_ERR = 'D:/VISSIM_runs/20261001_v3c3/s{s}_v3c3nc/run/baseline_s{s}_v3c3nc_001.err'
METER_SC = list(range(9101, 9109))
ERR_RE = re.compile(r'Vehicle input (\d+):.*?could not be finished completely \(remain: (\d+) vehicles\)')


def err_remain(path):
    out = {}
    with open(path, encoding='latin-1') as fh:
        for line in fh:
            m = ERR_RE.search(line)
            if m:
                out[m.group(1)] = out.get(m.group(1), 0) + int(m.group(2))
    return out


def main():
    out = sys.argv[1]
    res = {}
    for arm, (base_t, name_t) in RUNS.items():
        for s in SEEDS:
            base = base_t.format(s=s)
            name = name_t.format(s=s)
            dec = base + '/decisions_' + name
            R = {}
            cmd = {}
            ids = {}
            for f in sorted(glob.glob(dec + '/action_[0-9][0-9][0-9][0-9][0-9][0-9].csv')):
                T = int(os.path.basename(f)[7:13])
                with open(f, encoding='utf-8-sig', newline='') as fh:
                    for row in csv.DictReader(fh):
                        if row['kind'] == 'ramp_meter':
                            cmd[(T, int(row['sc_no']))] = float(row['green_sec'])
                            ids[int(row['sc_no'])] = row['id']
            dist = {}
            for sc in METER_SC:
                g = [cmd[(T, sc)] for T in range(900, 8851, 150)]
                dist[ids[sc]] = {'n': len(g), 'n_green10': sum(1 for x in g if x == 10.0), 'n_green2': sum(1 for x in g if x == 2.0),
                                 'min': min(g), 'max': max(g), 'hist': {str(k): v for k, v in sorted(Counter(g).items())}}
            R['meter_cmd_54'] = dist
            imm = defaultdict(list)
            with open(dec + '/signal_readback.csv', encoding='utf-8-sig', newline='') as fh:
                for row in csv.DictReader(fh):
                    sc = int(row['sc_no'])
                    if sc in METER_SC and row['stage'] == 'immediate':
                        imm[sc].append((int(row['sim_sec']), row['requested_state']))
            rb = {}
            for sc in METER_SC:
                st = states_per_second(imm[sc], 900, 9000)
                greens = [sum(1 for x in st[10 * k:10 * k + 10] if x == 'GREEN') for k in range(810)]
                mism = sum(1 for k, gk in enumerate(greens) if gk != cmd[(900 + 150 * ((10 * k) // 150), sc)])
                lt10 = [900 + 10 * k for k, gk in enumerate(greens) if gk < 10]
                le6 = [900 + 10 * k for k, gk in enumerate(greens) if gk <= 6]
                rb[ids[sc]] = {'n_green_lt10': len(lt10), 'T_tight10': lt10[0] if lt10 else None, 'T_tight6': le6[0] if le6 else None,
                               'mean_green': sum(greens) / 810.0, 'hist': {str(k): v for k, v in sorted(Counter(greens).items())},
                               'mismatch_vs_cmd': mism}
            R['meter_readback'] = rb
            lines = open(base + '/runlog_' + name + '.txt', encoding='utf-8', errors='replace').read().splitlines()
            w = []
            for l in lines:
                if l.startswith('CONTROLLER_DECISION '):
                    m = re.search(r'sim_sec=(\d+) wall_sec=([0-9.]+)', l)
                    if int(m.group(1)) >= 900:
                        w.append(float(m.group(2)))
            R['wall_ge900'] = {'n': len(w), 'mean': statistics.mean(w), 'median': statistics.median(w), 'min': min(w), 'max': max(w),
                               'n_gt360': sum(1 for x in w if x > 360), 'n_gt1800': sum(1 for x in w if x > 1800)}
            R['err_remain'] = err_remain(base + '/vissim_simulation_001.err')
            res['%s%d' % (arm, s)] = R
    for s in SEEDS:
        res['NC3%d' % s] = {'err_remain': err_remain(NC_ERR.format(s=s))}
        va = 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s%d/decisions_sdmpc31_v3c3_k92va_s%d/signal_readback.csv' % (s, s)
        n = 0
        bad = 0
        nongreen = 0
        with open(va, encoding='utf-8-sig', newline='') as fh:
            for row in csv.DictReader(fh):
                if int(row['sc_no']) in METER_SC:
                    n += 1
                    if row['requested_state'] != row['readback_state'] or row['ok'] != '1':
                        bad += 1
                    if row['requested_state'] != 'GREEN' or row['readback_state'] != 'GREEN':
                        nongreen += 1
        res['VA%d' % s] = {'meter_readback_rows': n, 'bad': bad, 'non_green_rows': nongreen}
    tmp = out + '.tmp' + str(os.getpid())
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(res, fh, indent=1)
    os.replace(tmp, out)
    print('VF_EXTRA_DONE', flush=True)


if __name__ == '__main__':
    main()
