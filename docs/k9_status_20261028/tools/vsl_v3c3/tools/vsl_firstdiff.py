# -*- coding: utf-8 -*-
"""First differing FZP data row between two runs (read-only). 2026-10-27 KST, vsl_v3c3 (PRE_VSL.md section 7, check V3).

Usage: python -B vsl_firstdiff.py <tag> <fzp_a> <fzp_b> <out_dir>

Compares the data rows (lines after the '$VEHICLE:' header that start with a digit, CR/LF normalised to LF) of the two
files in order and stops at the first row that differs. Writes <out_dir>/firstdiff_<tag>.json with:
- prefix_le_895_1: rows and sha256 of the LF-normalised data rows with time <= 895.1 s for each file and whether equal
  (same definition as vhr_scan.py lf_sha_le_895_1); the 0.1 s runner frame, if any, is included as in vhr_scan.py
- first_diff: time (s) of the first differing row (or of the shorter file's end), its row index, both rows (first 160 bytes)
- frames_equal_before: last frame time whose rows were all equal
Reads only the two FZPs (up to the first difference plus the 895.1 s prefix). Writes only the out file.
"""
import hashlib, json, os, sys, time


def rows(path):
    with open(path, 'rb') as f:
        seen = False
        for line in f:
            if not seen:
                if line.startswith(b'$VEHICLE:'):
                    seen = True
                continue
            if not (b'0' <= line[:1] <= b'9'):
                continue
            if line.endswith(b'\r\n'):
                line = line[:-2] + b'\n'
            elif not line.endswith(b'\n'):
                line = line + b'\n'
            yield line


def tenths(line):
    return int(round(float(line.split(b';', 1)[0]) * 10))


def main():
    tag, pa, pb, out_dir = sys.argv[1:5]
    t0 = time.time()
    ga, gb = rows(pa), rows(pb)
    ha, hb = hashlib.sha256(), hashlib.sha256()
    na = nb = 0
    i = 0
    first = None
    last_equal_frame = None
    cur_frame = None
    frame_clean = True
    while True:
        a = next(ga, None)
        b = next(gb, None)
        if a is None and b is None:
            break
        ta = tenths(a) if a is not None else None
        tb = tenths(b) if b is not None else None
        if a is not None and ta <= 8951:
            ha.update(a); na += 1
        if b is not None and tb <= 8951:
            hb.update(b); nb += 1
        if a != b:
            first = {'row_index': i, 'time_a_s': None if ta is None else ta / 10, 'time_b_s': None if tb is None else tb / 10,
                     'row_a': None if a is None else a[:160].decode('ascii', 'replace'), 'row_b': None if b is None else b[:160].decode('ascii', 'replace')}
            break
        if ta != cur_frame:
            if cur_frame is not None and frame_clean:
                last_equal_frame = cur_frame
            cur_frame = ta
            frame_clean = True
        i += 1
    if first is None and cur_frame is not None:
        last_equal_frame = cur_frame
    # finish the 895.1 s prefix for both files if the difference came earlier
    if first is not None:
        for line in ga:
            if tenths(line) > 8951:
                break
            ha.update(line); na += 1
        for line in gb:
            if tenths(line) > 8951:
                break
            hb.update(line); nb += 1
    res = {'tag': tag, 'a': pa, 'b': pb, 'rows_compared_equal': i,
           'prefix_le_895_1': {'rows_a': na, 'rows_b': nb, 'sha_a': ha.hexdigest(), 'sha_b': hb.hexdigest(),
                               'equal': na == nb and ha.hexdigest() == hb.hexdigest()},
           'first_diff': first, 'frames_equal_before_s': None if last_equal_frame is None else last_equal_frame / 10,
           'identical_files_data_rows': first is None, 'elapsed_s': round(time.time() - t0, 1)}
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, 'firstdiff_' + tag + '.json'), 'w', encoding='utf-8') as g:
        json.dump(res, g, indent=1)
    print(tag, 'prefix_equal', res['prefix_le_895_1']['equal'], 'first_diff', first and (first['time_a_s'], first['time_b_s']), res['elapsed_s'])


if __name__ == '__main__':
    main()
