r"""Prepare an isolated input for replaying one native SDMPC decision offline.

    make_replay_state.py <decisions_dir> <sim_sec> <out_dir>

A decision reads its lane-plant frames through lane_observations/observer_checkpoint.json,
an acceleration cache that is rejected when it is ahead of the decision time
(lane_plant_observation.load_causal_snapshot: "invalid/future cutoff"). Once a later
decision has run in that folder, earlier decisions can no longer be replayed there, and
replaying in a live run's folder would write that run's checkpoint.

So this hard-links frames 0..sim_sec into <out_dir>/lane_observations (no checkpoint:
the observer rebuilds from frame 0, which also checks that the cache was only a cache),
and writes <out_dir>/state_<sec>.json equal to the original except
lane_plant_observation.directory. Frames are write-once files, so hard links are safe.
"""
import io
import json
import os
import sys


def main():
    dec, sec, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    src_state = os.path.join(dec, 'state_%06d.json' % sec)
    raw = json.load(io.open(src_state, encoding='utf-8-sig'))
    meta = raw['lane_plant_observation']
    if meta['time_s'] != sec:
        raise SystemExit('state time mismatch')
    frames_src = meta['directory']
    frames_dst = os.path.join(out, 'lane_observations')
    os.makedirs(frames_dst, exist_ok=False)
    for t in range(0, sec + 1):
        name = 'frame_%06d.json' % t
        os.link(os.path.join(frames_src, name), os.path.join(frames_dst, name))
    raw['lane_plant_observation'] = dict(meta, directory=os.path.abspath(frames_dst))
    with io.open(os.path.join(out, 'state_%06d.json' % sec), 'w', encoding='utf-8') as f:
        json.dump(raw, f, ensure_ascii=False)
    print('linked %d frames from %s; state -> %s' % (sec + 1, frames_src, out))


if __name__ == '__main__':
    main()
