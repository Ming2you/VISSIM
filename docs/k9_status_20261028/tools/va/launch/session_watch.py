"""Main-session wake-up poller for V-A (not a judging tool; reads only va_monitor.py output booleans/counts).

Runs va_monitor.py every POLL seconds and exits (printing one ALERT line) when something needs the session:
a run printed its EXIT line, a hold / error line / error file appeared, the S-VA-7 stall flag is set, a launch
cmd died without an EXIT line, or s43 reached its T=900 decision (health check due).  Exits with HEARTBEAT after
MAX_SEC so the session re-arms.  Never touches run folders except through va_monitor.py.
"""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'session_watch_last.json')
POLL = int(sys.argv[1]) if len(sys.argv) > 1 else 480
MAX_SEC = int(sys.argv[2]) if len(sys.argv) > 2 else 6 * 3600
seen_exit = set(sys.argv[3].split(',')) if len(sys.argv) > 3 and sys.argv[3] else set()

t0 = time.time()
while True:
    try:
        subprocess.run([sys.executable, '-B', os.path.join(HERE, 'va_monitor.py'), OUT],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600)
        with open(OUT, encoding='utf-8') as f:
            res = json.load(f)
    except Exception as e:  # transient failure: try again next poll
        res = None
        print('WARN monitor failed: %r' % (e,), file=sys.stderr)
    alerts = []
    if res:
        for s, r in sorted(res['runs'].items()):
            if not r.get('run_dir_exists'):
                continue
            if r.get('exit_line') and s not in seen_exit:
                alerts.append('%s EXIT: %s' % (s, r['exit_line']))
            if len(r.get('hold_attempt') or []) or len(r.get('held') or []):
                alerts.append('%s HOLD attempts=%d held=%d' % (s, len(r['hold_attempt']), len(r['held'])))
            if len(r.get('error_lines') or []) or len(r.get('error_files') or []):
                alerts.append('%s ERROR lines=%d files=%d' % (s, len(r['error_lines']), len(r['error_files'])))
            if r.get('stall_S_VA_7'):
                alerts.append('%s STALL S-VA-7 ages=%s' % (s, r.get('age_sec')))
            if r.get('cmd_alive') is False and not r.get('exit_line'):
                alerts.append('%s CMD_DEAD without EXIT' % s)
            if s == 's43' and 900 in (r.get('decision_T') or []) and not os.path.exists(os.path.join(HERE, 'health_s43_T900.json')):
                alerts.append('s43 reached T=900: health check due')
    if alerts:
        print('ALERT %s | %s' % (res.get('checked_at'), ' ; '.join(alerts)))
        sys.exit(0)
    if time.time() - t0 > MAX_SEC:
        brief = []
        if res:
            for s, r in sorted(res['runs'].items()):
                if r.get('run_dir_exists'):
                    brief.append('%s n=%d last_T=%s' % (s, r.get('decisions_count', 0), (r.get('decision_T') or [None])[-1]))
                else:
                    brief.append('%s absent' % s)
        print('HEARTBEAT %s | %s' % (res.get('checked_at') if res else '?', ' ; '.join(brief)))
        sys.exit(0)
    time.sleep(POLL)
