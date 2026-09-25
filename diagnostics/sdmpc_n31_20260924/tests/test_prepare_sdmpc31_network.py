r"""WP-E network copy tool D:\VISSIM-merge\tools\prepare_sdmpc31_network.py (plan section 5, V5 step 3).

Synthetic folders first, then the real pinned copy into a temporary run folder, checked by the WP-D
launch plan (launch_plan.verify_network) exactly as run_sdmpc_n31.ps1 does. Nothing is written into the tree.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
N31D = HERE.parent
ROOT = N31D.parents[1]
TOOL = Path(r'D:\VISSIM-merge\tools\prepare_sdmpc31_network.py')
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pytestmark = pytest.mark.skipif(not TOOL.is_file(), reason='network copy tool absent')
tool = _load('prepare_sdmpc31_network', TOOL) if TOOL.is_file() else None


def sha(data):
    return hashlib.sha256(data).hexdigest()


INPX = b'''<?xml version="1.0" encoding="UTF-8"?><network>
<signalControllers>
<signalController no="1" progNo="1" supplyFile2="#data#\xea\xb0\x9c a.sig"/>
<signalController no="2" progNo="1" supplyFile2="#data#b.sig"/>
<signalController no="9101" progNo="1" supplyFile2=""/>
</signalControllers></network>'''


def make_source(folder, inpx=INPX, sigs=None, manifest_edit=None):
    folder.mkdir(parents=True)
    sigs = sigs if sigs is not None else {'\uac1c a.sig': b'sig-a', 'b.sig': b'sig-b'}
    (folder / 'net.inpx').write_bytes(inpx)
    for name, data in sigs.items():
        (folder / name).write_bytes(data)
    (folder / 'net.err').write_bytes(b'old run output')
    (folder / 'background.jpg').write_bytes(b'jpg')
    manifest = {'schema': tool.MANIFEST_SCHEMA, 'network': {'name': 'net.inpx', 'sha256': sha(inpx)},
                'files': [{'name': n, 'sha256': sha(d)} for n, d in sorted(sigs.items())]}
    if manifest_edit:
        manifest_edit(manifest)
    (folder / tool.MANIFEST_NAME).write_text(json.dumps(manifest, ensure_ascii=False), encoding='utf-8')
    return folder


def test_copy_is_byte_exact_renamed_and_nothing_else(tmp_path):
    source = make_source(tmp_path / 'src')
    out = tmp_path / 'run' / 'network'
    inpx, digest, count = tool.copy_network('sdmpc31_g1', out, source, expected_sig_count=2)
    assert inpx == out / 'sdmpc31_sdmpc31_g1.inpx' and digest == sha(INPX) and count == 2
    assert sorted(p.name for p in out.iterdir()) == sorted(['sdmpc31_sdmpc31_g1.inpx', '\uac1c a.sig', 'b.sig', tool.RECEIPT_NAME])
    assert inpx.read_bytes() == INPX and (out / 'b.sig').read_bytes() == b'sig-b'
    receipt_bytes = (out / tool.RECEIPT_NAME).read_bytes()
    assert b'\r\n' not in receipt_bytes                                  # LF on Windows too
    receipt = json.loads(receipt_bytes.decode('utf-8'))
    assert receipt['schema'] == tool.RECEIPT_SCHEMA and receipt['inpx']['sha256'] == sha(INPX) and len(receipt['sig']) == 2
    assert receipt['tool_sha256'] == sha(TOOL.read_bytes())               # the tool is outside git and FRZ
    assert receipt['source']['sig_manifest'] == str((source / tool.MANIFEST_NAME).resolve())
    assert tool.verify_network('sdmpc31_g1', out, source, expected_sig_count=2)[1] == sha(INPX)


def test_manifest_option_checks_a_source_without_its_own_manifest(tmp_path, capsys):
    """NET has no sig_manifest.json: --source NET --manifest <N31D manifest> (the old docstring promised this)."""
    pinned = make_source(tmp_path / 'pinned')
    net = tmp_path / 'net'
    net.mkdir()
    for p in pinned.iterdir():
        if p.name != tool.MANIFEST_NAME:
            (net / p.name).write_bytes(p.read_bytes())
    with pytest.raises(tool.CopyError, match='sig manifest missing'):
        tool.copy_network('g1', tmp_path / 'n0', net, expected_sig_count=2)
    tool.copy_network('g1', tmp_path / 'n1', net, expected_sig_count=2, manifest_path=pinned / tool.MANIFEST_NAME)
    assert tool.verify_network('g1', tmp_path / 'n1', net, expected_sig_count=2,
                               manifest_path=pinned / tool.MANIFEST_NAME)[2] == 2
    (net / 'b.sig').write_bytes(b'drifted')
    with pytest.raises(tool.CopyError, match='b.sig missing or differs'):
        tool.copy_network('g1', tmp_path / 'n2', net, expected_sig_count=2, manifest_path=pinned / tool.MANIFEST_NAME)
    assert tool.main(['--name', 'g1', '--out-dir', str(tmp_path / 'n3'), '--source', str(pinned),
                      '--manifest', str(pinned / tool.MANIFEST_NAME)]) == 1          # 42 expected by the CLI
    assert 'expected 42' in capsys.readouterr().out


@pytest.mark.parametrize('edit', [
    lambda m: m['network'].update(name='..\\net.inpx'),
    lambda m: m['network'].update(name='sub/net.inpx'),
    lambda m: m['network'].update(name='C:net.inpx'),
    lambda m: m['files'][0].update(name='C:b.sig'),
    lambda m: m['files'][0].update(name='.sig'),
])
def test_refuses_manifest_names_that_leave_the_folder(tmp_path, edit):
    source = make_source(tmp_path / 'src', manifest_edit=edit)
    with pytest.raises(tool.CopyError, match='sig manifest (network entry|row name)'):
        tool.copy_network('g1', tmp_path / 'n', source, expected_sig_count=2)


def test_refuses_a_used_folder_a_bad_name_and_a_wrong_count(tmp_path):
    source = make_source(tmp_path / 'src')
    out = tmp_path / 'network'
    out.mkdir()
    (out / 'stale.err').write_bytes(b'x')
    with pytest.raises(tool.CopyError, match='not empty'):
        tool.copy_network('g1', out, source, expected_sig_count=2)
    with pytest.raises(tool.CopyError, match='run name'):
        tool.copy_network('bad name', tmp_path / 'n2', source, expected_sig_count=2)
    with pytest.raises(tool.CopyError, match='expected 42'):
        tool.copy_network('g1', tmp_path / 'n3', source)


def test_refuses_bytes_that_differ_from_the_manifest(tmp_path):
    source = make_source(tmp_path / 'src')
    (source / 'b.sig').write_bytes(b'tampered')
    with pytest.raises(tool.CopyError, match='b.sig missing or differs'):
        tool.copy_network('g1', tmp_path / 'n', source, expected_sig_count=2)
    source = make_source(tmp_path / 'src2', manifest_edit=lambda m: m['network'].update(sha256='0' * 64))
    with pytest.raises(tool.CopyError, match='differs from sig_manifest'):
        tool.copy_network('g1', tmp_path / 'n2', source, expected_sig_count=2)


def test_refuses_a_manifest_that_disagrees_with_the_inpx_references(tmp_path):
    source = make_source(tmp_path / 'src', sigs={'\uac1c a.sig': b'a', 'b.sig': b'b', 'c.sig': b'c'})
    with pytest.raises(tool.CopyError, match='does not use'):
        tool.copy_network('g1', tmp_path / 'n', source, expected_sig_count=3)
    source = make_source(tmp_path / 'src2', sigs={'b.sig': b'b'})
    with pytest.raises(tool.CopyError, match='beyond the manifest'):
        tool.copy_network('g1', tmp_path / 'n2', source, expected_sig_count=1)


def test_verify_only_catches_later_tampering(tmp_path):
    source = make_source(tmp_path / 'src')
    out = tmp_path / 'network'
    tool.copy_network('g1', out, source, expected_sig_count=2)
    (out / 'extra.err').write_bytes(b'x')
    with pytest.raises(tool.CopyError, match='unexpected'):
        tool.verify_network('g1', out, source, expected_sig_count=2)
    (out / 'extra.err').unlink()
    (out / 'b.sig').write_bytes(b'changed')
    with pytest.raises(tool.CopyError, match='b.sig differs'):
        tool.verify_network('g1', out, source, expected_sig_count=2)


def test_cli_prints_one_line_and_exit_codes(tmp_path, capsys):
    assert tool.main(['--name', 'g1', '--out-dir', str(tmp_path / 'n'), '--root', str(tmp_path / 'nowhere')]) == 1
    line = capsys.readouterr().out.strip().splitlines()
    assert len(line) == 1 and line[0].startswith('NETWORK_COPY_ERROR ')


@pytest.mark.parametrize('edit, reason', [
    (lambda m: m['files'].append('c.sig'), 'row is not an object'),
    (lambda m: m.update(files={'b.sig': '0' * 64}), 'files is not a list'),
    (lambda m: m.update(network='net.inpx'), 'network entry is not an object'),
])
def test_malformed_manifest_is_one_error_line_not_a_traceback(tmp_path, capsys, edit, reason):
    """The stdout contract (one line, exit 1) holds for a manifest of the wrong shape too."""
    source = make_source(tmp_path / 'src', manifest_edit=edit)
    assert tool.main(['--name', 'g1', '--out-dir', str(tmp_path / 'n'), '--source', str(source)]) == 1
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 1 and lines[0].startswith('NETWORK_COPY_ERROR ') and reason in lines[0]
    (tmp_path / 'list.json').write_text('[]', encoding='utf-8')
    assert tool.main(['--name', 'g1', '--out-dir', str(tmp_path / 'n'), '--source', str(source),
                      '--manifest', str(tmp_path / 'list.json')]) == 1
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 1 and 'not a JSON object' in lines[0]


REAL_SOURCE = ROOT / 'diagnostics' / 'sdmpc_n31_20260924' / 'network'


@pytest.mark.skipif(not (REAL_SOURCE / 'sig_manifest.json').is_file(), reason='repin network copy not built')
def test_real_copy_passes_the_launch_plan_network_check(tmp_path, capsys):
    """The exact call run_sdmpc_n31.ps1 makes (cwd = tree root), then launch_plan.verify_network."""
    out = tmp_path / 'sdmpc31_g1' / 'network'
    assert tool.main(['--name', 'sdmpc31_g1', '--out-dir', str(out), '--root', str(ROOT)]) == 0
    line = capsys.readouterr().out.strip()
    assert line.startswith('NETWORK_COPY_OK ') and 'sig=42' in line
    lp = _load('launch_plan_for_test', N31D / 'tools' / 'launch_plan.py')
    manifest = json.loads((REAL_SOURCE / 'sig_manifest.json').read_text(encoding='utf-8'))
    plan = {'network_dir': str(out), 'network_file': str(out / 'sdmpc31_sdmpc31_g1.inpx'),
            'sources': {'network': {'sha256': manifest['network']['sha256']}}, 'sig_files': lp.sig_table(manifest)}
    lp.verify_network(plan)
    assert 'NETWORK_OK' in capsys.readouterr().out
    assert manifest['network']['sha256'].startswith('be0075bf')   # network v3b (2026-09-25; was f475ce42)
    receipt = json.loads((out / tool.RECEIPT_NAME).read_text(encoding='utf-8'))
    assert receipt['tool_sha256'] == sha(TOOL.read_bytes())


NET = Path(r'D:\VISSIM_runs\20260925_v3b\s31_v3bnc\prepared\network')


@pytest.mark.skipif(not (REAL_SOURCE / 'sig_manifest.json').is_file() or not (NET / 'baseline_s31_v3bnc.inpx').is_file(),
                    reason='repin network copy or NET absent')
def test_real_copy_from_net_with_the_pinned_manifest(tmp_path, capsys):
    """NET (read only) holds run outputs and no manifest; only the .inpx and the 42 .sig are copied."""
    out = tmp_path / 'net_copy' / 'network'
    assert tool.main(['--name', 'g1', '--out-dir', str(out), '--source', str(NET),
                      '--manifest', str(REAL_SOURCE / 'sig_manifest.json')]) == 0
    assert capsys.readouterr().out.startswith('NETWORK_COPY_OK ')
    sigs = [p.name for p in REAL_SOURCE.iterdir() if p.suffix == '.sig']
    assert len(sigs) == 42
    assert sorted(p.name for p in out.iterdir()) == sorted(sigs + [tool.RECEIPT_NAME, 'sdmpc31_g1.inpx'])
