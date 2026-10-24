"""Keep the future-source cause-separation test isolated from causal forecasts."""
import copy
from types import SimpleNamespace
import pytest
from diagnostics.sdmpc_n31_20260924.integration_20260926.probe_selected_arrival_path import diagnostic_source_forecast


def inputs():
    forecast = [SimpleNamespace(freeway_mainline={'FW_E': 7000., 'FW_W': 4500.},
                               urban_boundary={'gate': 17.}, ramp_arrivals={'r': 800.}) for _ in range(3)]
    document = dict(schema='diagnostic-native-mainline/v1', road='FW_E', start_sec=2250.,
                    interval_sec=150., blocks=3, future_observation_inputs=True,
                    optimizer_allowed=False, mode='common_nc',
                    profiles_veh_h={a:[7560.,7152.,7272.] for a in ('held_actual','rm','vsl','both')})
    return forecast, document


def test_default_is_exact_and_never_aliases_forecast():
    forecast,_ = inputs()
    result = diagnostic_source_forecast(forecast, 'rm', None)
    assert result == forecast
    result[0].urban_boundary['gate'] = 99.
    assert forecast[0].urban_boundary['gate'] == 17.


def test_only_explicit_east_source_changes_and_history_is_unmodified():
    forecast,document = inputs(); before = copy.deepcopy(forecast)
    for case in document['profiles_veh_h']:
        result = diagnostic_source_forecast(forecast, case, document)
        for i, step in enumerate(result):
            assert step.freeway_mainline == {'FW_E':document['profiles_veh_h'][case][i], 'FW_W':4500.}
            assert step.urban_boundary == before[i].urban_boundary
            assert step.ramp_arrivals == before[i].ramp_arrivals
    assert forecast == before


@pytest.mark.parametrize('bad', ['unmarked_future', 'optimizer', 'unequal_common', 'nan', 'negative'])
def test_bad_contract_cannot_masquerade_as_normal_forecast(bad):
    forecast,doc = inputs()
    if bad == 'unmarked_future': doc['future_observation_inputs'] = False
    elif bad == 'optimizer': doc['optimizer_allowed'] = True
    elif bad == 'unequal_common': doc['profiles_veh_h']['rm'][0] += 1
    else:
        doc['mode'] = 'per_arm'
        doc['profiles_veh_h']['rm'][0] = float('nan') if bad == 'nan' else -1
    with pytest.raises(ValueError): diagnostic_source_forecast(forecast, 'rm', doc)
