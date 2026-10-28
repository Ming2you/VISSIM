# make_spec_fo.py (2026-10-27 KST, PRE_FO s8) - build the mkcopy spec for the FO analysis copies.
# Source = the pinned B copies (PINS_B.sha256); destination = FO copies next to them (codex_handoff/work/*_fo/...).
# Only path constants and comments change: the B run root -> the FO run root, the B output folders -> the FO output folders,
# the 'B copy' slot comments -> 'FO copy'. Every changed line is a whole-line replacement (made unique with the line before it
# when the same line occurs twice). rm_exec_b_s* is not copied (no LDP in codex-runner run folders: COMPARE_RULE_B X6, B_RUNS s9).
# usage: python -B make_spec_fo.py <out_spec.json>
import hashlib, json, sys

CW = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work'
PINS_B = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/b/PINS_B.sha256'
PINS_B_SHA = '5e8ffbc5cc192c25a15a07c11dda5036c7005b73c342aa16d1f7d6ed5e67d804'
SUBS = [
    ('[B copy 2026-10-26 KST, COMPARE_RULE_B: path constants only',
     '[FO copy 2026-10-27 KST, COMPARE_RULE_FO: path constants only; the slot that held B now holds FO] [B copy 2026-10-26 KST, COMPARE_RULE_B: path constants only'),
    ('D:/VISSIM_runs/20261026_codex_b_v3c3', 'D:/VISSIM_runs/20261028_codex_fo_v3c3'),
    ('/codex_handoff/work/vhr_b/', '/codex_handoff/work/vhr_fo/'),
    ('/codex_handoff/work/rawcheck_b/', '/codex_handoff/work/rawcheck_fo/'),
    ('# B copy: slot j1 = B', '# FO copy: slot j1 = FO'),
    ('# B copy: slot joint = B v3c3-s', '# FO copy: slot joint = FO v3c3-s'),
    ('# B copy: slot a1 = B v3c3-s', '# FO copy: slot a1 = FO v3c3-s'),
    ('# B copy: codex-runner layout', '# FO copy (of the B copy): codex-runner layout, FO run root'),
]
TARGETS = [s for s, _ in SUBS]
FILES = [('vhr_b/vhr_scan_b.py', 'vhr_fo/vhr_scan_fo.py'), ('vhr_b/vhr_firstseen_b.py', 'vhr_fo/vhr_firstseen_fo.py'),
         ('vhr_b/vhr_v3c3_all_b.py', 'vhr_fo/vhr_v3c3_all_fo.py'), ('omega_b/omega701_recount_b.py', 'omega_fo/omega701_recount_fo.py'),
         ('rawcheck_b/dec_extract_b.py', 'rawcheck_fo/dec_extract_fo.py')]
for s in (31, 41, 43):
    for t in ('scan_fzp', 'metrics', 'walltimes', 'ramp_fc', 'a1_fzp_firstdiff'):
        FILES.append(('rawcheck_b/s%d/%s_b_s%d.py' % (s, t, s), 'rawcheck_fo/s%d/%s_fo_s%d.py' % (s, t, s)))


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def main(out):
    if sha(PINS_B) != PINS_B_SHA:
        raise SystemExit('PINS_B changed')
    pins = {}
    for l in open(PINS_B, encoding='utf-8'):
        h, p = l.strip().split(' *', 1)
        pins[p] = h
    spec = []
    for src, dst in FILES:
        rel = 'work/' + src
        p = CW + '/' + src
        if pins.get(rel) != sha(p):
            raise SystemExit('source not the pinned B copy: ' + rel)
        text = open(p, 'rb').read().decode('utf-8').replace('\r\n', '\n')
        lines = text.split('\n')
        reps = []
        for i, line in enumerate(lines):
            if not any(t in line for t in TARGETS):
                continue
            new = line
            for a, b in SUBS:
                new = new.replace(a, b)
            old, nw = line, new
            if text.count(old) != 1:
                old, nw = lines[i - 1] + '\n' + line, lines[i - 1] + '\n' + new
                if text.count(old) != 1:
                    raise SystemExit('cannot make a unique replacement in %s line %d' % (src, i + 1))
            reps.append([old, nw])
        if not reps:
            raise SystemExit('no replacement in ' + src)
        spec.append({'src': p, 'dst': CW + '/' + dst, 'why': 'FO: slot of B -> FO run root %s; B output folders -> FO output folders' % 'D:/VISSIM_runs/20261028_codex_fo_v3c3',
                     'reps': reps})
    json.dump(spec, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('spec files', len(spec), 'replacements', sum(len(x['reps']) for x in spec))


if __name__ == '__main__':
    main(sys.argv[1])
