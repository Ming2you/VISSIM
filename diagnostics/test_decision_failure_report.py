"""A failed decision exits promptly even when nobody drains its stdio pipes.

run_real_world_stackelberg_controller.vbs RunCapture3 reads the adapter's
stdout/stderr only after exit. Decision 7650 of sdmpc31_v3b_s31d hung 2418 s:
its tangent worker failed, and the adapter blocked writing the traceback into
the full stderr pipe. The subprocess tests reproduce that pipe discipline.
"""
import io
import os
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers import decision_failure_report as report  # noqa: E402

# Larger than any anonymous pipe buffer (4 KiB on Windows, 64 KiB on Linux).
LONG = 'x'*200_000


class _WorkerRaises:
    """Unpickling this in the tangent worker raises there with a long message."""
    def __reduce__(self):
        return (exec, (f"raise ValueError('worker root cause ' + 'x'*{len(LONG)})",))


class _WorkerDies:
    """Unpickling this in the tangent worker kills it without a result file."""
    def __reduce__(self):
        return (os._exit, (7,))


class _WorkerDiesWhileWriting:
    """The tangent worker leaves a truncated result file and dies, as if killed mid-write."""
    def __reduce__(self):
        return (exec, ("import os, sys; open(sys.argv[2], 'wb').write(bytes([0x80, 5, 0x95])); os._exit(3)",))


class _WorkerDiesNoisily:
    """The tangent worker writes a long stderr and dies without a result file."""
    def __reduce__(self):
        return (exec, ("import os, sys; sys.stderr.write('HEAD-MARK'+'y'*20000+'TAIL-MARK'); "
                       "sys.stderr.flush(); os._exit(5)",))


def _stderr_capture():
    raw = io.BytesIO()
    return raw, io.TextIOWrapper(raw, encoding='utf-8')


class ReportUnitTests(unittest.TestCase):
    def test_report_path_follows_the_action_json(self):
        self.assertEqual(report.report_path(['--out-action-json', r'D:\d\action_007650.json', '--x']),
                         Path(r'D:\d\action_007650.error.txt'))
        self.assertEqual(report.report_path(['--out-action-json=a/action_000900.json']),
                         Path('a/action_000900.error.txt'))
        self.assertIsNone(report.report_path(['--state-json', 's.json']))

    def test_success_is_untouched(self):
        raw, stream = _stderr_capture()
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(sys, 'stderr', stream):
            out = Path(tmp)/'action_000900.json'
            self.assertEqual(report.run(lambda: 42, ['--out-action-json', str(out)]), 42)
            self.assertEqual(os.listdir(tmp), [])
        stream.flush()
        self.assertEqual(raw.getvalue(), b'')

    def test_system_exit_passes_through(self):
        with tempfile.TemporaryDirectory() as tmp:
            def entry():
                raise SystemExit(2)
            with self.assertRaises(SystemExit) as caught:
                report.run(entry, ['--out-action-json', str(Path(tmp)/'a.json')])
            self.assertEqual(caught.exception.code, 2)
            self.assertEqual(os.listdir(tmp), [])

    def test_failure_writes_full_traceback_and_one_bounded_line(self):
        raw, stream = _stderr_capture()
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(sys, 'stderr', stream):
            out = Path(tmp)/'action_007650.json'
            def entry():
                raise RuntimeError('Tangent prediction failed:\nTraceback ...\n'+LONG+
                                   '\nValueError: ramp:RM_C10681 must be finite and nonnegative')
            with self.assertRaises(SystemExit) as caught:
                report.run(entry, ['--out-action-json', str(out)])
            self.assertEqual(caught.exception.code, 1)
            text = (Path(tmp)/'action_007650.error.txt').read_text(encoding='utf-8')
            self.assertIn(LONG, text)
            self.assertIn('in entry', text)
        stream.flush()
        line = raw.getvalue()
        self.assertLessEqual(len(line), report.SUMMARY_LIMIT_BYTES)
        self.assertEqual(line.count(b'\n'), 1)
        self.assertIn(b'type=RuntimeError message=Tangent prediction failed:', line)
        self.assertIn(b'root_error=ValueError: ramp:RM_C10681 must be finite and nonnegative', line)
        self.assertIn(b'action_007650.error.txt', line)

    def test_unwritable_report_falls_back_to_temp(self):
        raw, stream = _stderr_capture()
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(sys, 'stderr', stream):
            blocker = Path(tmp)/'blocker'
            blocker.write_text('a file, not a folder', encoding='utf-8')
            def entry():
                raise KeyError('k')
            with self.assertRaises(SystemExit):
                report.run(entry, ['--out-action-json', str(blocker/'action.json')])
        stream.flush()
        line = raw.getvalue().decode('utf-8')
        path = Path(line.rsplit('traceback=', 1)[1].strip())
        try:
            self.assertEqual(path.parent, Path(tempfile.gettempdir()))
            self.assertIn("KeyError: 'k'", path.read_text(encoding='utf-8'))
        finally:
            path.unlink()


CHILD = textwrap.dedent('''
    import sys
    from pathlib import Path
    sys.path[:0] = [sys.argv[1]]
    from evaluation.controllers import decision_failure_report as report
    from evaluation.controllers.sdmpc_tangent import _evaluate_single
    mode, marker, out, size = sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5])
    class WorkerRaises:
        def __reduce__(self):
            return (exec, (f"raise ValueError('worker root cause ' + 'x'*{size})",))
    def main():
        try:
            _evaluate_single({'payload': WorkerRaises()})
        except BaseException:
            Path(marker).write_text('worker failure reached the decision process', encoding='utf-8')
            raise
    if mode == 'bounded':
        report.run(main, ['--out-action-json', out])
    else:
        main()
''')


class WorkerFailurePromptExitTests(unittest.TestCase):
    """Real tangent worker processes, real undrained pipes, bounded waits."""

    def evaluate_in_thread(self, payload, timeout=90.):
        from evaluation.controllers.sdmpc_tangent import _evaluate_single
        import threading
        box = {}
        def target():
            try:
                box['result'] = _evaluate_single({'payload': payload})
            except BaseException as exc:  # noqa: BLE001
                box['error'] = exc
        started = time.perf_counter()
        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        thread.join(timeout)
        self.assertFalse(thread.is_alive(), 'parent still waiting on a failed tangent worker')
        return box, time.perf_counter()-started

    def test_worker_error_raises_in_parent_with_its_traceback(self):
        box, wall = self.evaluate_in_thread(_WorkerRaises())
        self.assertIsInstance(box.get('error'), RuntimeError)
        message = str(box['error'])
        self.assertTrue(message.startswith('Tangent prediction failed:'))
        self.assertIn('sdmpc_tangent_worker.py', message)
        self.assertIn('ValueError: worker root cause xxx', message)

    def test_worker_death_raises_in_parent(self):
        box, wall = self.evaluate_in_thread(_WorkerDies())
        self.assertIsInstance(box.get('error'), RuntimeError)
        self.assertTrue(str(box['error']).startswith('Tangent worker failed: returncode=7,'))

    def test_worker_killed_while_writing_names_its_exit_status(self):
        import pickle
        box, wall = self.evaluate_in_thread(_WorkerDiesWhileWriting())
        error = box.get('error')
        self.assertIsInstance(error, RuntimeError)
        self.assertTrue(str(error).startswith('Tangent worker failed: unreadable result ('), str(error))
        self.assertIn('returncode=3,', str(error))
        self.assertIsInstance(error.__cause__, (pickle.UnpicklingError, EOFError))

    def test_long_worker_stderr_keeps_its_head_and_tail(self):
        box, wall = self.evaluate_in_thread(_WorkerDiesNoisily())
        self.assertIsInstance(box.get('error'), RuntimeError)
        message = str(box['error'])
        self.assertTrue(message.startswith('Tangent worker failed: returncode=5,'))
        for part in ('HEAD-MARK', 'TAIL-MARK', 'characters omitted'):
            self.assertIn(part, message)
        self.assertLess(len(message), 6200)

    def spawn(self, tmp, mode):
        marker, out = Path(tmp)/f'{mode}.marker', Path(tmp)/'decisions'/'action_007650.json'
        env = dict(os.environ, PYTHONUTF8='1')
        # stdin/stdout/stderr are anonymous pipes that nobody reads before exit,
        # as in VBS RunCapture3 (shell.Exec + Status polling + ReadAll after exit).
        child = subprocess.Popen([sys.executable, '-B', '-c', CHILD, str(ROOT), mode, str(marker),
                                  str(out), str(len(LONG))], cwd=ROOT, env=env, stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.addCleanup(lambda: child.poll() is None and (child.kill(), child.communicate()))
        return child, marker, out

    @staticmethod
    def poll(child, until, timeout):
        deadline = time.monotonic()+timeout
        while time.monotonic() < deadline:
            if until():
                return True
            time.sleep(.05)
        return until()

    def test_failed_worker_ends_the_decision_process_with_undrained_pipes(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Control: the former entry point blocks in the traceback write.
            child, marker, _ = self.spawn(tmp, 'plain')
            self.assertTrue(self.poll(child, marker.is_file, 90.), 'worker failure not reached')
            time.sleep(3.)
            self.assertIsNone(child.poll(), 'control did not block: the pipe mechanism is not exercised')
            _, err = child.communicate(timeout=60)  # draining alone releases it
            self.assertEqual(child.returncode, 1)
            self.assertGreater(len(err), 65536)

            # Fixed entry point: exits by itself with its pipes never read.
            child, marker, out = self.spawn(tmp, 'bounded')
            started = time.monotonic()
            self.assertTrue(self.poll(child, lambda: child.poll() is not None, 90.),
                            'decision process hung after its tangent worker failed')
            self.assertTrue(marker.is_file())
            self.assertEqual(child.returncode, 1)
            _, err = child.communicate(timeout=10)
            self.assertLessEqual(len(err), report.SUMMARY_LIMIT_BYTES)
            self.assertIn(b'type=RuntimeError message=Tangent prediction failed:', err)
            self.assertIn(b'root_error=ValueError: worker root cause xxx', err)
            text = out.with_suffix('.error.txt').read_text(encoding='utf-8')
            self.assertIn('sdmpc_tangent_worker.py', text)
            self.assertIn('worker root cause '+LONG, text)
            self.assertLess(time.monotonic()-started, 90.)


if __name__ == '__main__':
    unittest.main()
