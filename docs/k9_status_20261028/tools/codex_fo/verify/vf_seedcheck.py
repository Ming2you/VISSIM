# vf_seedcheck.py - VERIFY_FO: seed of every run in vf_fzp_list.txt from its provenance / run.json (not from names),
# and the FZP header "File:" line must point into the same run root. Read only. New code.
# usage: python -B vf_seedcheck.py <list_file> <out_json>
import sys, os, json

PROV = {
    'fo': 'D:/VISSIM_runs/20261028_codex_fo_v3c3/s{s}/sdmpc/run_provenance_sdmpc31_sdmpc9000_s{s}.json',
    'b': 'D:/VISSIM_runs/20261026_codex_b_v3c3/s{s}/sdmpc/run_provenance_sdmpc31_sdmpc9000_s{s}.json',
    'nc': 'D:/VISSIM_runs/20261001_v3c3/s{s}_v3c3nc/run/run.json',
    'va': 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s{s}/run_provenance_sdmpc31_v3c3_k92va_s{s}.json',
}
ROOT = {
    'fo': 'D:\\VISSIM_runs\\20261028_codex_fo_v3c3\\s{s}\\',
    'b': 'D:\\VISSIM_runs\\20261026_codex_b_v3c3\\s{s}\\',
    'nc': 'D:\\VISSIM_runs\\20261001_v3c3\\s{s}_v3c3nc\\',
    'va': 'D:\\VISSIM_runs\\20261023_sdmpc31_k92\\sdmpc31_v3c3_k92va_s{s}\\',
}


def main():
    lst, out = sys.argv[1], sys.argv[2]
    res = {}
    ok_all = True
    for line in open(lst, encoding='utf-8'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        label, fzp = line.split('|', 1)
        arm, s = label[:-2], label[-2:]
        with open(PROV[arm].format(s=s), encoding='utf-8-sig') as fh:
            prov = json.load(fh)
        seed = prov.get('seed')
        file_line = None
        with open(fzp, 'rb') as fh:
            for i, raw in enumerate(fh):
                t = raw.decode('latin-1')
                if t.startswith('* File:'):
                    file_line = t.split(':', 1)[1].strip()
                    break
                if i > 50:
                    break
        root = ROOT[arm].format(s=s)
        same_root = file_line is not None and file_line.lower().startswith(root.lower())
        ok = (seed == int(s)) and same_root
        ok_all = ok_all and ok
        res[label] = {'provenance_seed': seed, 'expected_from_list_slot': int(s), 'fzp_header_file': file_line,
                      'fzp_in_same_run_root': same_root, 'ok': ok}
    res['_all_ok'] = ok_all
    with open(out, 'w', encoding='utf-8') as fh:
        json.dump(res, fh, indent=1)
    print('VF_SEEDCHECK', 'ALL_OK' if ok_all else 'MISMATCH', flush=True)
    sys.exit(0 if ok_all else 4)


if __name__ == '__main__':
    main()
