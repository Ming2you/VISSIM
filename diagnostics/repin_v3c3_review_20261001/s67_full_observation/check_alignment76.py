"""Reject invalid scope/prefix evidence before the two autonomous forecasts."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
from diagnostics.sdmpc_n31_20260924.integration_20260926.native_pair1200.analyze_pair import verify_recording_start_alignment

HERE = Path(__file__).resolve().parent
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path, data):path.write_text(json.dumps(data, indent=2), encoding='utf-8')

def main():
    alignment_path=HERE/'recording_start_alignment76.json'
    alignment=json.loads(alignment_path.read_bytes())
    # Correct the diagnostic metadata label; hashes/rows/native files unchanged.
    if 'old_raw_prefix_check_preserved' in alignment:
        assert alignment.pop('old_raw_prefix_check_preserved') is False
        alignment.update(original_initial_history_exact=False, original_failure_preserved=True)
        save(alignment_path,alignment)
    original=HERE/'analysis/summary.json'
    scope=verify_recording_start_alignment(original,alignment_path)
    summary=json.loads(original.read_bytes())
    checks={'real_new_pair_and_recording_overlap':True}
    mutations={
        'unequal_pair':lambda s,p:s.update(paired_prefix_exact=False),
        'unequal_initial_state':lambda s,p:s.update(common_start_vehicle_records_exact=False),
        'failed_execution':lambda s,p:s['arms']['release'].update(native_execution_passed=False),
        'different_prefix_hash':lambda s,p:s['prefixes']['release_vsl90'].update(sha256='0'*64),
        'wrong_overlap':lambda s,p:p['overlap'].update(rows=4),
        'missing_extra_record':lambda s,p:p.update(extra_new_start_rows=[]),
        'different_recording_start':lambda s,p:p.update(first_common_record_s=10.1),
        'changed_native_file':lambda s,p:p.update(new_file_size=1),
        'silently_flipped_old_pass':lambda s,p:s.update(original_initial_history_exact=True,counterfactual_valid=True),
    }
    with tempfile.TemporaryDirectory(prefix='vissim_alignment76_') as temporary:
        folder=Path(temporary)
        for name,mutate in mutations.items():
            s,p=copy.deepcopy(summary),copy.deepcopy(alignment)
            mutate(s,p)
            sp,pp=folder/'summary.json',folder/'alignment.json'
            save(sp,s);p.update(analysis_summary=str(sp),analysis_summary_sha256=sha(sp));save(pp,p)
            try:verify_recording_start_alignment(sp,pp)
            except AssertionError:checks[name]=True
            else:raise AssertionError('Invalid evidence accepted: '+name)
    result=dict(checks=checks,passed=all(checks.values()),comparison_scope=scope,
                original_failed_summary_sha256=sha(original),
                calibration_candidates=0,native_reruns=0)
    save(HERE/'alignment_checks76.json',result)
    print(json.dumps(result))

if __name__=='__main__':main()
