"""obs150 capture CLI (WP-B1, CONTRACT.md 4.5): called by the runner VBS at each decision stop.

python -B scripts\\obs150_capture.py --eval-dir <EvalOutDir> --err <network dir\\stem_001.err>
       --out-dir <decisionDir>\\obs150 --sim-sec <T> --detectors <CSV> --detectors-sha256 <sha>

Writes obs150/mer_<T>.jsonl, obs150/err_<T>.jsonl, obs150/mer_index.json and
obs150/capture_<T>.json (the meta the VBS splices into the state). On success
stdout is exactly one line, written as bytes and ended by LF (no CR on Windows):
    OBS150_CAPTURE_OK meta=obs150/capture_<T>.json sha256=<hex>
Any failure prints one OBS150_CAPTURE_FAIL line (at most STDERR_LIMIT bytes) to
stderr, nothing to stdout, and exits 2; the runner then aborts the vehicle
observation (no decision on a partial bundle). Both streams stay far below the
pipe buffer: RunCapture3 (VBS) reads them only after the process has exited.
"""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.controllers import obs150_capture  # noqa: E402
from evaluation.controllers import obs150_contract as oc  # noqa: E402

STDERR_LIMIT = 1000


def parse_args(argv):
    parser = argparse.ArgumentParser(description='obs150 .mer/.err capture at one decision stop')
    parser.add_argument('--eval-dir', required=True)
    parser.add_argument('--err', required=True)
    parser.add_argument('--out-dir', required=True)
    parser.add_argument('--sim-sec', required=True)
    parser.add_argument('--detectors', required=True)
    parser.add_argument('--detectors-sha256', required=True)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        text = args.sim_sec.strip()
        if not (text.isascii() and text.isdigit()):
            raise oc.ObsContractError('--sim-sec must be an integer decision time')
        sim_sec = int(text)
        rows, _ = oc.read_detector_csv(args.detectors, args.detectors_sha256)
        obs150_capture.capture(args.eval_dir, args.err, args.out_dir, sim_sec, rows)
        digest = obs150_capture.capture_file_sha256(args.out_dir, sim_sec)
    except Exception as error:  # the runner needs one line and a nonzero exit, never a traceback on stdout
        detail = ' '.join(('%s: %s' % (type(error).__name__, error)).split())
        # Encode first, then cut bytes: a backslash escape grows one character to up to 10 bytes.
        line = ('OBS150_CAPTURE_FAIL ' + detail).encode('ascii', 'backslashreplace')[:STDERR_LIMIT - 1] + b'\n'
        sys.stderr.buffer.write(line)
        sys.stderr.flush()
        return 2
    line = '%s meta=%s sha256=%s\n' % (oc.CAPTURE_STDOUT_PREFIX, oc.capture_meta_path(sim_sec), digest)
    sys.stdout.buffer.write(line.encode('ascii'))
    sys.stdout.flush()
    return 0


if __name__ == '__main__':
    sys.exit(main())
