"""T6 (plan C4(f), N31 review A5/A6): make the silent index fallbacks raise.

While `strict_index_guards()` is active:
  1. zoned segment_vsl (AD:8599-8606) raises for a cell outside the config's
     zone table instead of passing the raw index through, and for a merge
     index (item 2) of an N-cell state read through a zone table of another
     length: LPR:477 writes the 31-cell to_cell into the full cfg, whose zone
     table stays 21-cell, so metanet.py:285, AFA:60-61 and leader.py:699-707
     would read RM_C10681's refined cell 12 (parent 9, zone 5) as zone 10
     while staying in range;
  2. metanet._ramp_merge_index (metanet.py:150-154) and the Leader /
     FreewayFollower copies (leader.py:667-671, freeway_follower.py:135-139)
     raise for a configured merge index outside the current state length
     instead of clamping (the leader.py:699-707 path), and tag the returned
     index with that state length (MergeIndex, an int) for item 1. A merge
     index that only indexes the state is left alone: it is in the state's
     own namespace;
  3. effective_lane_profile (the AD:8925 lane fallback) raises when a road's
     state is longer than its configured lane table;
  4. joint_owner_neighbors.build_current_freeway_domain (the 21-cell assert at
     :1182) is spied: every call is recorded, so a replay can prove the SDMPC
     path never reaches it.
Every guard error is also appended to record['guard_errors'] before it is
raised, so a caller that swallows exceptions (a decision falling back to a
hold action) cannot hide it from the T6 record.
Everything is restored on exit. For use in V3 replays (T6) and in the unit
tests of the guards themselves.
"""
from __future__ import annotations

import contextlib


class IndexGuardError(IndexError):
    pass


class MergeIndex(int):
    """A ramp merge cell index that remembers the state length it was computed for."""

    def __new__(cls, value, n_segments):
        index = super().__new__(cls, value)
        index.n_segments = int(n_segments)
        return index


def _check_merge(configured, ramp, n_segments, where, fail):
    if isinstance(configured, dict) and ramp in configured:
        index = float(configured[ramp])
        if not 0.0 <= index <= float(n_segments - 1):
            fail('%s: merge index %s of %s outside %d cells' % (where, index, ramp, n_segments))


@contextlib.contextmanager
def strict_index_guards(record=None):
    from src.models import state as st
    from src.models import metanet as mn
    from src.controllers import leader as leader_module
    from src.controllers import freeway_follower as follower_module
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    from evaluation.controllers import joint_owner_neighbors as jon
    record = {} if record is None else record
    record.setdefault('build_current_freeway_domain_calls', 0)
    errors = record.setdefault('guard_errors', [])

    def fail(message):
        errors.append(message)
        raise IndexGuardError(message)
    restore = []

    old_segment_vsl = st.segment_vsl

    def guarded_segment_vsl(control, link, index, cfg_, *args, **kwargs):
        table = (getattr(cfg_.network, 'freeway_vsl_zone_head_of_cell', None) or {}).get(str(link))
        space = getattr(index, 'n_segments', None)
        if table and space is not None and space != len(table):
            fail('segment_vsl: merge cell %d of a %d-cell state read in the %d-cell zone table of %s'
                 % (int(index), space, len(table), link))
        if table and not 0 <= int(index) < len(table):
            fail('segment_vsl: cell %s outside the %d-cell zone table of %s' % (index, len(table), link))
        return old_segment_vsl(control, link, index, cfg_, *args, **kwargs)
    for flag in ('_rw_vsl_zone', '_rw_fw_seg_patch'):
        if getattr(old_segment_vsl, flag, False):
            setattr(guarded_segment_vsl, flag, True)
    adapter._fw_rebind('segment_vsl', old_segment_vsl, guarded_segment_vsl)
    st.segment_vsl = guarded_segment_vsl
    restore.append(lambda: (adapter._fw_rebind('segment_vsl', guarded_segment_vsl, old_segment_vsl),
                            setattr(st, 'segment_vsl', old_segment_vsl)))

    old_merge = mn._ramp_merge_index

    def guarded_merge(cfg, ramp, n_segments):
        _check_merge(getattr(cfg.network, 'ramp_merge_segment_index', {}), ramp, n_segments, 'metanet', fail)
        return MergeIndex(old_merge(cfg, ramp, n_segments), n_segments)
    adapter._fw_rebind('_ramp_merge_index', old_merge, guarded_merge)
    mn._ramp_merge_index = guarded_merge
    restore.append(lambda: (adapter._fw_rebind('_ramp_merge_index', guarded_merge, old_merge),
                            setattr(mn, '_ramp_merge_index', old_merge)))

    for cls, where in ((leader_module.Leader, 'leader'), (follower_module.FreewayFollower, 'freeway_follower')):
        old_method = cls.__dict__['_ramp_merge_index']

        def guarded_method(self, ramp, n_segments, _old=old_method, _where=where):
            _check_merge(getattr(self.cfg.network, 'ramp_merge_segment_index', {}), ramp, n_segments, _where, fail)
            return MergeIndex(_old(self, ramp, n_segments), n_segments)
        cls._ramp_merge_index = guarded_method
        restore.append(lambda cls=cls, old=old_method: setattr(cls, '_ramp_merge_index', old))

    old_profile = mn.effective_lane_profile

    def guarded_profile(state, cfg_, demand=None):
        table = getattr(cfg_.network, 'freeway_segment_lanes', None) or {}
        for link, densities in (getattr(state, 'freeway_density', None) or {}).items():
            lanes = table.get(str(link))
            if lanes and len(densities) > len(lanes):
                fail('lane profile: %d state cells but %d configured lanes on %s'
                     % (len(densities), len(lanes), link))
        return old_profile(state, cfg_, demand)
    for flag in ('_rw_fw_seg_patch',):
        if getattr(old_profile, flag, False):
            setattr(guarded_profile, flag, True)
    adapter._fw_rebind('effective_lane_profile', old_profile, guarded_profile)
    mn.effective_lane_profile = guarded_profile
    restore.append(lambda: (adapter._fw_rebind('effective_lane_profile', guarded_profile, old_profile),
                            setattr(mn, 'effective_lane_profile', old_profile)))

    old_domain = jon.build_current_freeway_domain

    def spied_domain(*args, **kwargs):
        record['build_current_freeway_domain_calls'] += 1
        return old_domain(*args, **kwargs)
    adapter._fw_rebind('build_current_freeway_domain', old_domain, spied_domain)
    jon.build_current_freeway_domain = spied_domain
    restore.append(lambda: (adapter._fw_rebind('build_current_freeway_domain', spied_domain, old_domain),
                            setattr(jon, 'build_current_freeway_domain', old_domain)))
    try:
        yield record
    finally:
        for undo in reversed(restore):
            undo()
