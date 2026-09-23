r"""Copy the controller worktree's untracked files into the merged tree.

The merge snapshot committed tracked modifications only, so every untracked file
the controller branch had produced -- generated scenario inputs among them --
never reached sim3. A run then dies on whichever one it needs first, one at a
time. This fills the holes in one pass.

Only paths ABSENT from sim3 are written, so nothing from the plant side can be
overwritten. Pass --apply to actually copy; the default is a dry run.
"""
import io
import os
import shutil
import sys

SIM = r'D:\VISSIM-merge\sim3'
CTRL = r'C:\Users\TRLAB\Documents\ChatGPT\VISSIM\.worktrees\sdmpc-tangent-20260921'
LIST = (r'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----'
        r'\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\untracked.txt')
SKIP_SUFFIX = ('.pstats', '.fzp', '.pyc')


def main():
    apply = '--apply' in sys.argv
    todo, skipped, bytes_total = [], [], 0
    for line in io.open(LIST, encoding='utf-8'):
        rel = line.strip().strip('"')
        if not rel:
            continue
        native = rel.replace('/', os.sep)
        dst = os.path.join(SIM, native)
        src = os.path.join(CTRL, native)
        if os.path.exists(dst) or not os.path.isfile(src):
            continue
        if rel.endswith(SKIP_SUFFIX):
            skipped.append(rel)
            continue
        todo.append((src, dst, rel))
        bytes_total += os.path.getsize(src)

    print('to copy : %d files, %.1f MB' % (len(todo), bytes_total / 1e6))
    print('skipped : %d profiling/trajectory artefacts' % len(skipped))
    if not apply:
        print('(dry run -- pass --apply)')
        return 0
    for src, dst, rel in todo:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
    print('copied %d' % len(todo))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
