# vf_prefix.py - VERIFY_FO: FZP prefix comparison FO / B / NC3 per seed (2026-10-28 KST). Written after reading FO_REPORT.
# Streams each FZP only until the first frame after 900.1 s. Hashes the raw data lines with 1 <= t <= 895.1 and 1 <= t <= 900.1,
# keeps the t < 1 s lines as text. Read only. New code.
# usage: python -B vf_prefix.py <list_file> <out_json>     (list lines: label|path; labels fo31, b31, nc31, ...)
import sys, json, hashlib


def prefix(path):
    h895 = hashlib.sha256()
    h900 = hashlib.sha256()
    n895 = n900 = 0
    lt1 = []
    in_data = False
    with open(path, 'rb') as fh:
        for raw in fh:
            if not in_data:
                if raw.startswith(b'$VEHICLE:'):
                    in_data = True
                continue
            t = float(raw.split(b';', 1)[0])
            if t > 900.15:
                break
            if t < 1.0:
                lt1.append(raw.decode('latin-1').rstrip('\r\n'))
                continue
            h900.update(raw)
            n900 += 1
            if t <= 895.15:
                h895.update(raw)
                n895 += 1
    return {'sha_1_895': h895.hexdigest(), 'n_1_895': n895, 'sha_1_900': h900.hexdigest(), 'n_1_900': n900, 'rows_lt1': lt1}


def main():
    lst, out = sys.argv[1], sys.argv[2]
    res = {}
    for line in open(lst, encoding='utf-8'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        label, path = line.split('|', 1)
        if label[:-2] not in ('fo', 'b', 'nc'):
            continue
        res[label] = prefix(path)
        print('VF_PREFIX', label, res[label]['n_1_900'], flush=True)
    cmpres = {}
    for s in ('31', '41', '43'):
        f, b, n = res['fo' + s], res['b' + s], res['nc' + s]
        cmpres[s] = {'fo_eq_b_1_895': f['sha_1_895'] == b['sha_1_895'], 'fo_eq_nc_1_895': f['sha_1_895'] == n['sha_1_895'],
                     'fo_eq_b_1_900': f['sha_1_900'] == b['sha_1_900'], 'fo_eq_nc_1_900': f['sha_1_900'] == n['sha_1_900'],
                     'lt1_fo_eq_b': f['rows_lt1'] == b['rows_lt1'], 'lt1_fo_eq_nc': f['rows_lt1'] == n['rows_lt1']}
    res['_compare'] = cmpres
    with open(out, 'w', encoding='utf-8') as fh:
        json.dump(res, fh, indent=1)
    print('VF_PREFIX_DONE', json.dumps(cmpres), flush=True)


if __name__ == '__main__':
    main()
