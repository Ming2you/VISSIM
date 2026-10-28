# Compare B-copy prescan outputs (work/vhr_b/scan_out/<tag>.json) with the original scanner outputs (work/vhr/scan_out/<tag>.json).
# Read-only. Keys compared: all except scan_sec. Prints one line per tag.
import json, sys
CW = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work'
for tag in sys.argv[1:]:
    a = json.load(open(CW + '/vhr_b/scan_out/%s.json' % tag, encoding='utf-8'))
    b = json.load(open(CW + '/vhr/scan_out/%s.json' % tag, encoding='utf-8'))
    diff = sorted(k for k in set(a) | set(b) if k != 'scan_sec' and a.get(k) != b.get(k))
    print(tag, 'same_except_scan_sec=%s' % (not diff), 'diff_keys=%s' % diff, 'lf_sha_le_895_1=%s' % a.get('lf_sha_le_895_1'),
          'rows_le_895_1=%s' % a.get('rows_le_895_1'), 'first_frame_s=%s' % a.get('first_frame_s'), 'has_0p1=%s' % a.get('has_0p1_frame'))
