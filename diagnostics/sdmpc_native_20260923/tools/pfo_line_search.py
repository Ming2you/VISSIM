r"""Which line-search trial actually wins, and what would taping only the full step cost?

PFO evaluates every line-search trial with derivatives=True (sdmpc_pfo.py:74), but a
trial's Jacobian is only read if that trial is ACCEPTED -- the losers' derivatives are
discarded (the archive records unused_ad_predictions). SDMPC already suppresses
derivatives on its last iteration (sdmpc.py:809); PFO's call is unconditional.

Trials are built as z + (0.5**k)*step for k in range(line_search_steps), so trial 0 is
the full step. If the full step nearly always wins, taping only trial 0 and running the
halved ones scalar turns a 3-wide taped batch (135.1 s at 2 reverse workers each) into
one 8-worker taped rollout (113.3 s) with the scalars finishing inside it -- about
-21.8 s per trial batch. When the full step LOSES, the winner has no Jacobian and the
next iteration must re-tape it, roughly +113 s.

This counts the wins from the archives so the expected value is arithmetic, not a guess.
"""
import io
import json
import os
import sys

ARCHIVES = [
    (r'C:\Users\TRLAB\Documents\ChatGPT\VISSIM\.worktrees\sdmpc-tangent-20260921'
     r'\diagnostics\sdmpc_pfo_caps_20260922\decision_v1\result.json'),
    (r'C:\Users\TRLAB\Documents\ChatGPT\VISSIM\.worktrees\sdmpc-tangent-20260921'
     r'\diagnostics\sdmpc_pfo_caps_20260922\decision_mlc3\result.json'),
]
TAPED_1WIDE = 113.253     # one taped rollout, 8 reverse workers
RETAPE = 113.253


def blocks(doc):
    """Yield every (label, metadata) that carries PFO-style trial_rows + iterations."""
    def walk(o, path):
        if isinstance(o, dict):
            if 'trial_rows' in o and 'iterations' in o:
                yield path, o
            for k, v in o.items():
                yield from walk(v, path + '/' + str(k))
        elif isinstance(o, list):
            for i, v in enumerate(o):
                yield from walk(v, path + '[%d]' % i)
    return list(walk(doc, ''))


def main():
    grand = {'iters': 0, 'full_step_won': 0, 'no_step': 0}
    for path in ARCHIVES:
        if not os.path.exists(path):
            print('missing: ' + path)
            continue
        doc = json.load(io.open(path, encoding='utf-8-sig'))
        print('=== ' + os.path.basename(os.path.dirname(path)))
        for label, meta in blocks(doc):
            rows, iters = meta['trial_rows'], meta['iterations']
            algo = str(meta.get('algorithm', ''))[:44]
            if not rows:
                continue
            by_iter = {}
            for r in rows:
                by_iter.setdefault(r['iteration'], []).append(r)
            start = {it['iteration']: it.get('action_token') for it in iters}
            print('  %-46s %s  iters=%d status=%s' %
                  (label[-46:], algo, len(iters), meta.get('status')))
            for i in sorted(by_iter):
                trials = by_iter[i]
                nxt = start.get(i + 1)
                if nxt is None:
                    print('      iter %d: %d trials, no accepted successor (terminal)' % (i, len(trials)))
                    grand['no_step'] += 1
                    continue
                idx = next((j for j, t in enumerate(trials) if t.get('action_token') == nxt), None)
                grand['iters'] += 1
                if idx == 0:
                    grand['full_step_won'] += 1
                print('      iter %d: %d trials, accepted index %s  %s'
                      % (i, len(trials), idx,
                         '(FULL STEP)' if idx == 0 else '(halved)' if idx is not None else '(unmatched)'))
        print()

    n = grand['iters']
    if not n:
        print('no matched iterations')
        return 0
    p = grand['full_step_won'] / n
    print('accepted iterations matched: %d   full step won: %d  (p = %.2f)'
          % (n, grand['full_step_won'], p))
    print('terminal iterations with no successor: %d' % grand['no_step'])
    gain, loss = 21.8, RETAPE
    ev = p * gain - (1 - p) * loss
    print('\nexpected value per trial batch, taping only the full step:')
    print('  win  %.2f x -%.1f s   lose %.2f x +%.1f s   ->  %+.1f s' % (p, gain, 1 - p, loss, -ev))
    print('  break-even needs p > %.3f' % (loss / (gain + loss)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
