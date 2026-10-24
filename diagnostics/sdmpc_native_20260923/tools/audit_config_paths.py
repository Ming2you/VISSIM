r"""Which files does the SDMPC tuning reference, and are they in the merged tree?

The merge snapshot of the controller worktree committed tracked modifications;
anything untracked (a generated scenario directory, say) never reached sim3 and
only shows up when a run dies on the first file it needs. This lists all of them
at once instead.
"""
import json
import io
import os
import re
import shutil
import sys

SIM = r'D:\VISSIM-merge\sim3'
CTRL = r'C:\Users\TRLAB\Documents\ChatGPT\VISSIM\.worktrees\sdmpc-tangent-20260921'
CONFIG = os.path.join(SIM, 'diagnostics', 'sdmpc_pfo_caps_20260922', 'config_candidate.json')
PATTERN = re.compile(r'"([A-Za-z0-9_./\\-]+\.(?:json|csv|vbs|py|inpx|sig))"')


def main():
    copy = '--copy' in sys.argv
    blob = json.dumps(json.load(io.open(CONFIG, encoding='utf-8-sig')), ensure_ascii=False)
    referenced = sorted(set(PATTERN.findall(blob)))
    only_ctrl, neither = [], []
    for ref in referenced:
        rel = ref.replace('/', os.sep)
        if os.path.exists(os.path.join(SIM, rel)):
            continue
        (only_ctrl if os.path.exists(os.path.join(CTRL, rel)) else neither).append(ref)

    print('config references %d files' % len(referenced))
    print('\n== missing from sim3, present in the controller worktree: %d ==' % len(only_ctrl))
    for ref in only_ctrl:
        print('   ', ref)
    print('\n== missing from both: %d ==' % len(neither))
    for ref in neither:
        print('   ', ref)

    if copy and only_ctrl:
        print('\ncopying...')
        for ref in only_ctrl:
            rel = ref.replace('/', os.sep)
            dst = os.path.join(SIM, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(os.path.join(CTRL, rel), dst)
        print('copied %d' % len(only_ctrl))
    return 1 if neither else 0


if __name__ == '__main__':
    raise SystemExit(main())
