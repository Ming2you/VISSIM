"""One-off: wrap the read-only collector output with run metadata into P1_REPORT.json r2 (no new computation)."""
import hashlib, json, sys
from pathlib import Path
VP = Path(sys.argv[1]); src = Path(sys.argv[2]); out = Path(sys.argv[3])
def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()
d = json.loads(src.read_text(encoding='utf-8'))
meta = {
 'written_kst': sys.argv[4],
 'status': 'all 9 P1 states run; no stop rule hit under PRE_VP_R3 (r3 R1 rule)',
 'r1_preserved': {'P1_REPORT_r1.md': sha(VP/'P1_REPORT_r1.md'), 'P1_REPORT_r1.json': sha(VP/'P1_REPORT_r1.json')},
 'L0': {'SHA256SUMS_VP_r3.txt': sha(VP/'SHA256SUMS_VP_r3.txt'), 'SHA256SUMS_VP_EXT_r3.txt': sha(VP/'SHA256SUMS_VP_EXT_r3.txt'),
        'pins_ok': '54/54 and 14/14 before launch and again after H3', 'treefields_record': sha(VP/'selftest/treefields_L0_p1r3_43144.json'),
        'selftest_record': sha(VP/'selftest/selftest_L0_p1r3_43144.json'), 'selftest': '65/65',
        'L2_outputs_match_r1_record': True, 'H0_rerun_by_this_run': False},
 'launch': {'tag': 'p1h3r3', 'wmi_pid': 30012, 'queue_pid': 11072, 'launched_kst': '2026-10-27 18:24:43',
            'launch_log_sha256': sha(VP/'logs/launch_p1h3r3.txt'),
            'queue_log_before_resume_copy_sha256': sha(VP/'report_p1/r2/queue_plantP_before_r3resume.log')},
 'collector': {'script_sha256': sha(VP/'report_p1/r2/p1_report_r2_json.py'), 'output_sha256': sha(src),
               'wrapper_sha256': sha(VP/'report_p1/r2/p1_report_r2_final.py')},
 'correction': 'r1 P1_REPORT.md and QV3_REPORT.md section 9 cite code_va.tree.json as 67e6681e1c1c...; the file sha is 67e6681e3c1c30595b660660c66e04210b690a4f0099f516b1ae57169c6c86d3 (the r1 JSON files carry the right value)',
 'open': ['C1 direction label: literal PRE_VP_FIXED 5.4 text gives "방향 근거 없음" for C1 -> m2 (FD - VISSIM low = +2.76 km/h) although C1 lowered v_free in the M1 cells; wording choice for the user',
          'VSb stock / speed: no candidate meets the pointing rule -> left to out-of-list terms; X1 >= 1 veh in 0/9 states at every exit',
          'next step of Q-V4 (plant fix design for the cell 18 lane-drop terms) is the user decision',
          'PRE_VP_R3 options O1 (table tool R1 column code) remains; O2 (S-NULL tolerance) not triggered (null bit-equal 9/9)'],
}
rec = {'schema': d['schema'], 'revision': d['revision'], **meta, **{k: v for k, v in d.items() if k not in ('schema', 'revision')}}
out.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding='utf-8')
print('written', out, sha(out))
