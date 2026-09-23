r"""Check a relaunched run's lane frames against a reference run, as they are written.

    compare_frames.py <new_run_dir> <ref_run_dir> [last_sec=900]

Frames are written to a temp name and moved into place, so a frame_NNNNNN.json that
exists is complete. Each frame embeds its run_id; that one value is replaced before the
byte comparison, everything else must match. Prints one line per 100 frames with the
wall time per simulated second, and a MISMATCH line at the first difference.
"""
import glob
import os
import re
import sys
import time


def frames_dir(run):
    hits = glob.glob(os.path.join(run, 'decisions_*', 'lane_observations'))
    return hits[0] if hits else None


def body(path):
    raw = open(path, 'rb').read()
    text = raw.decode('utf-16') if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else raw.decode('utf-8-sig')
    return re.sub(r'"run_id":"[^"]*"', '"run_id":""', text, count=1)


def main():
    new, ref = sys.argv[1], sys.argv[2]
    last = int(sys.argv[3]) if len(sys.argv) > 3 else 900
    sec, block_start, block_t0, idle = 0, 0, None, time.time()
    while sec <= last:
        nd = frames_dir(new)
        path = os.path.join(nd, 'frame_%06d.json' % sec) if nd else None
        if not path or not os.path.exists(path):
            if time.time() - idle > 1200:
                print('STALL no new frame for 20 min at sec=%d' % sec, flush=True)
                idle = time.time()
            time.sleep(2)
            continue
        idle = time.time()
        rp = os.path.join(frames_dir(ref), 'frame_%06d.json' % sec)
        if body(path) != body(rp):
            print('FRAME MISMATCH sec=%d  new=%s' % (sec, path), flush=True)
            return 1
        mtime = os.path.getmtime(path)
        if block_t0 is None:
            block_t0 = mtime
        if sec % 100 == 99 or sec == last:
            span = max(1, sec - block_start)
            print('FRAMES OK %d..%d  wall/sim-s %.2f' % (block_start, sec, (mtime - block_t0) / span), flush=True)
            block_start, block_t0 = sec + 1, None
        sec += 1
    print('ALL FRAMES 0..%d IDENTICAL (run_id aside)' % last, flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
