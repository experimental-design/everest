import numpy as np
import pandas as pd
import pytest

from bofire.domain import Domain
from bofire.domain.features import ContinuousInput, ContinuousOutput
from bofire.domain.objectives import (
    MaximizeObjective,
    MaximizeSigmoidObjective,
    MinimizeObjective,
)
from bofire.utils.multiobjective import (
    compute_hypervolume,
    get_pareto_front,
    get_ref_point_mask,
    infer_ref_point,
)
from tests.bofire.domain.test_features import VALID_CONTINUOUS_INPUT_FEATURE_SPEC

if1 = ContinuousInput(
    **{
        **VALID_CONTINUOUS_INPUT_FEATURE_SPEC,
        "key": "if1",
    }
)

if2 = ContinuousInput(
    **{
        **VALID_CONTINUOUS_INPUT_FEATURE_SPEC,
        "key": "if2",
    }
)


of1 = ContinuousOutput(
    objective=MaximizeObjective(w=1),
    key="of1",
)

of2 = ContinuousOutput(
    objective=MinimizeObjective(w=1),
    key="of2",
)

of3 = ContinuousOutput(
    objective=MaximizeObjective(w=1),
    key="of3",
)

of4 = ContinuousOutput(
    objective=MinimizeObjective(w=1),
    key="of4",
)
of5 = ContinuousOutput(
    objective=MaximizeSigmoidObjective(w=1, tp=1, steepness=1),
    key="of5",
)
of6 = ContinuousOutput(
    objective=MinimizeObjective(w=0.5),
    key="of6",
)


valid_domains = [
    Domain(input_features=[if1, if2], output_features=[of1, of2]),
    Domain(input_features=[if1, if2], output_features=[of1, of3]),
    Domain(input_features=[if1, if2], output_features=[of1, of2, of3, of4]),
    Domain(input_features=[if1, if2], output_features=[of2, of4]),
    Domain(input_features=[if1, if2], output_features=[of2, of1, of3, of4]),
]

invalid_domains = [
    Domain(input_features=[if1, if2], output_features=[of1]),
    Domain(input_features=[if1, if2], output_features=[of1, of5]),
    Domain(input_features=[if1, if2], output_features=[of1, of5, of6]),
]

dfs = [
    pd.DataFrame.from_dict(
        {
            "if1": [3.0, 4.0, 5.0, 6.0],
            "if2": [10.0, 7.0, 8.0, 12.0],
            "of1": [
                1.0,
                10.0,
                4.0,
                5.0,
            ],
            "of2": [
                5.0,
                3.0,
                2.0,
                5.0,
            ],
            "valid_of1": [
                1,
                1,
                1,
                1,
            ],
            "valid_of2": [
                1,
                1,
                1,
                1,
            ],
        }
    ),
    pd.DataFrame.from_dict(
        {
            "if1": [3.0, 4.0, 5.0, 6.0],
            "if2": [10.0, 7.0, 8.0, 12.0],
            "of1": [
                1.0,
                10.0,
                4.0,
                5.0,
            ],
            "of3": [
                5.0,
                3.0,
                2.0,
                5.0,
            ],
            "valid_of1": [
                1,
                1,
                1,
                1,
            ],
            "valid_of3": [
                1,
                1,
                1,
                1,
            ],
        }
    ),
]


@pytest.mark.parametrize(
    "domain, expected",
    [
        (valid_domains[0], np.array([1.0, -1.0])),
        (valid_domains[1], np.array([1.0, 1.0])),
        (valid_domains[2], np.array([1.0, -1.0, 1.0, -1.0])),
        (valid_domains[3], np.array([-1.0, -1.0])),
        (valid_domains[4], np.array([1.0, -1.0, 1.0, -1.0])),
    ],
)
def test_get_ref_point_mask(domain, expected):
    assert np.allclose(get_ref_point_mask(domain), expected)


@pytest.mark.parametrize(
    "domain, subset, expected",
    [
        (valid_domains[2], ["of1", "of2"], np.array([1.0, -1.0])),
        (valid_domains[2], ["of1", "of2", "of3"], np.array([1.0, -1.0, 1.0])),
        (valid_domains[2], ["of1", "of3"], np.array([1.0, 1.0])),
    ],
)
def test_get_ref_point_mask_subset(domain, subset, expected):
    assert np.allclose(get_ref_point_mask(domain, output_feature_keys=subset), expected)


@pytest.mark.parametrize("domain", invalid_domains[:-1])
def test_invalid_get_ref_point_mask(domain):
    with pytest.raises(ValueError):
        get_ref_point_mask(domain)


@pytest.mark.parametrize(
    "domain, experiments, expected_indices",
    [
        (valid_domains[0], dfs[0], np.array([1, 2], dtype="int64")),
        (valid_domains[1], dfs[1], np.array([1, 3], dtype="int64")),
    ],
)
def test_get_pareto_front(domain, experiments, expected_indices):
    df_pareto = get_pareto_front(domain, experiments)
    assert np.allclose(df_pareto.index.values, expected_indices)


@pytest.mark.parametrize(
    "domain, experiments, ref_point",
    [
        (valid_domains[0], dfs[0], {"of1": 0.0, "of2": 20.0}),
        (valid_domains[1], dfs[1], {"of1": 0.0, "of3": 0.0}),
    ],
)
def test_compute_hypervolume(domain, experiments, ref_point):
    df_pareto = get_pareto_front(domain, experiments)
    hv = compute_hypervolume(domain, df_pareto, ref_point)
    assert hv > 0


@pytest.mark.parametrize(
    "domain, experiments, return_masked, expected",
    [
        (valid_domains[0], dfs[0], True, {"of1": 1.0, "of2": -5.0}),
        (valid_domains[0], dfs[0], False, {"of1": 1.0, "of2": 5.0}),
        (valid_domains[1], dfs[1], True, {"of1": 1.0, "of3": 2.0}),
        (valid_domains[1], dfs[1], False, {"of1": 1.0, "of3": 2.0}),
    ],
)
def test_infer_ref_point(domain, experiments, return_masked, expected):
    ref_point = infer_ref_point(domain, experiments, return_masked)
    assert np.allclose(
        np.array(
            [
                ref_point[feat]
                for feat in domain.output_features.get_keys_by_objective(excludes=None)
            ]
        ),
        np.array(
            [
                expected[feat]
                for feat in domain.output_features.get_keys_by_objective(excludes=None)
            ]
        ),
    )
