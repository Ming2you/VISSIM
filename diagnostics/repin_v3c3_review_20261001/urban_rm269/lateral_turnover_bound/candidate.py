from diagnostics.repin_v3c3_review_20261001.urban_rm269.lateral_turnover.candidate import install as install_turnover
from diagnostics.repin_v3c3_review_20261001.urban_rm269.lane_transfer_binding.probe import install as bind

def install():
    install_turnover()
    return bind()
