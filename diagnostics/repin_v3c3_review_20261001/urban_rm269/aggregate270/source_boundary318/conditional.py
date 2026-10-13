"""Offline oracle boundary substitution. Never install in an optimizer or native run."""
import copy
import math
import pickle


def substitute(forecast, counts_by_road):
    if len(forecast) != 3 or set(counts_by_road) != {'FW_E', 'FW_W'}:
        raise ValueError('Require one450s forecast and both observed source boundaries')
    for counts in counts_by_road.values():
        if len(counts) != 3 or any(isinstance(n, bool) or not math.isfinite(n) or n < 0 for n in counts):
            raise ValueError('Require three finite nonnegative150s admission counts')
    before = pickle.dumps(forecast, protocol=5)
    result = copy.deepcopy(forecast)
    for block, original in enumerate(forecast):
        result[block].freeway_mainline = {r: counts[block] * 3600 / 150 for r, counts in counts_by_road.items()}
        restored = copy.deepcopy(result[block])
        restored.freeway_mainline = copy.deepcopy(original.freeway_mainline)
        assert vars(restored) == vars(original), 'Changed a non-source demand field'
    assert pickle.dumps(forecast, protocol=5) == before
    return result
