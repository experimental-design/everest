import unittest
import warnings
from typing import Literal, Type

import pandas as pd
import pytest

import bofire.data_models.strategies.api as data_models
import bofire.data_models.surrogates.api as surrogate_data_models
import bofire.strategies.api as strategies
import tests.bofire.data_models.specs.api as specs
from bofire.data_models.constraints.api import (
    Constraint,
    LinearConstraint,
    LinearEqualityConstraint,
    LinearInequalityConstraint,
)
from bofire.data_models.domain.api import Domain
from bofire.data_models.enum import CategoricalEncodingEnum
from bofire.data_models.features.api import (
    CategoricalDescriptorInput,
    CategoricalInput,
    ContinuousInput,
    ContinuousOutput,
    DiscreteInput,
    Feature,
    Output,
)
from bofire.data_models.objectives.api import MaximizeObjective, MinimizeObjective
from tests.bofire.data_models.test_domain_validators import generate_experiments
from tests.bofire.strategies.specs import (
    VALID_ALLOWED_CATEGORICAL_DESCRIPTOR_INPUT_FEATURE_SPEC,
    VALID_CATEGORICAL_DESCRIPTOR_INPUT_FEATURE_SPEC,
    VALID_CATEGORICAL_INPUT_FEATURE_SPEC,
    VALID_CONTINUOUS_INPUT_FEATURE_SPEC,
    VALID_CONTINUOUS_OUTPUT_FEATURE_SPEC,
    VALID_DISCRETE_INPUT_FEATURE_SPEC,
    VALID_FIXED_CATEGORICAL_DESCRIPTOR_INPUT_FEATURE_SPEC,
    VALID_FIXED_CATEGORICAL_INPUT_FEATURE_SPEC,
    VALID_FIXED_CONTINUOUS_INPUT_FEATURE_SPEC,
)

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning, append=True)

with warnings.catch_warnings():
    warnings.simplefilter("ignore")


class DummyFeature(Feature):
    type: Literal["DummyFeature"] = "DummyFeature"

    def is_fixed(self):
        pass

    def fixed_value(self):
        pass


class DummyStrategyDataModel(data_models.BotorchStrategy):
    type: Literal["DummyStrategyDataModel"] = "DummyStrategyDataModel"

    @classmethod
    def is_constraint_implemented(cls, my_type: Type[Constraint]) -> bool:
        return my_type in [
            LinearConstraint,
            LinearEqualityConstraint,
            LinearInequalityConstraint,
        ]

    @classmethod
    def is_feature_implemented(cls, my_type: Type[Feature]) -> bool:
        return my_type in [
            ContinuousInput,
            CategoricalInput,
            DiscreteInput,
            CategoricalDescriptorInput,
            ContinuousOutput,
        ]

    @classmethod
    def is_objective_implemented(cls, my_type: Type[Feature]) -> bool:
        return my_type in [MinimizeObjective, MaximizeObjective]


class DummyStrategy(strategies.BotorchStrategy):
    def _init_acqf(
        self,
    ) -> None:
        pass


if1 = ContinuousInput(
    **{
        **VALID_CONTINUOUS_INPUT_FEATURE_SPEC,
        "key": "if1",
    }
)
if2 = ContinuousInput(
    **{
        **VALID_FIXED_CONTINUOUS_INPUT_FEATURE_SPEC,
        "key": "if2",
    }
)

if3 = CategoricalInput(
    **{
        **VALID_CATEGORICAL_INPUT_FEATURE_SPEC,
        "key": "if3",
    }
)

if4 = CategoricalInput(
    **{
        **VALID_FIXED_CATEGORICAL_INPUT_FEATURE_SPEC,
        "key": "if4",
    }
)

if5 = CategoricalDescriptorInput(
    **{
        **VALID_CATEGORICAL_DESCRIPTOR_INPUT_FEATURE_SPEC,
        "key": "if5",
    }
)

if6 = CategoricalDescriptorInput(
    **{
        **VALID_FIXED_CATEGORICAL_DESCRIPTOR_INPUT_FEATURE_SPEC,
        "key": "if6",
    }
)

if7 = DummyFeature(key="if7")

if8 = CategoricalDescriptorInput(
    **{
        **VALID_ALLOWED_CATEGORICAL_DESCRIPTOR_INPUT_FEATURE_SPEC,
        "key": "if8",
    }
)

if9 = DiscreteInput(
    **{
        **VALID_DISCRETE_INPUT_FEATURE_SPEC,
        "key": "if9",
    }
)

of1 = ContinuousOutput(
    **{
        **VALID_CONTINUOUS_OUTPUT_FEATURE_SPEC,
        "key": "of1",
    }
)

of2 = ContinuousOutput(
    **{
        **VALID_CONTINUOUS_OUTPUT_FEATURE_SPEC,
        "key": "of2",
    }
)

domains = [
    Domain(
        input_features=[if1, if3, if5, if9],  # no fixed features
        output_features=[of1],
        constraints=[],
    ),
    Domain(
        input_features=[
            if1,
            if2,
            if3,
            if4,
            if5,
            if6,
            if9,
        ],  # all feature types incl. with fixed values
        output_features=[of1],
        constraints=[],
    ),
    Domain(
        input_features=[
            if1,
            if2,
            if3,
            if4,
            if5,
            if6,
            if9,
        ],  # all feature types incl. with fixed values + mutli-objective
        output_features=[of1, of2],
        constraints=[],
    ),
    Domain(
        input_features=[if1, if2],  # only continuous features
        output_features=[of1],
        constraints=[],
    ),
    Domain(
        input_features=[if1, if3, if5, if9],  # all feature types + mutli-objective
        output_features=[of1, of2],
        constraints=[],
    ),
    Domain(
        input_features=[if1, if2, if8],
        output_features=[of1],
        constraints=[],
    ),
    Domain(
        input_features=[if1, if2],  # only continuous features
        output_features=[of1, of2],
        constraints=[],
    )
    # Domain(
    #     input_features=[if1, if7], # unknown dummy feature
    #     output_features=[of1],
    #     constraints=[],
    # )
]

data = [
    pd.DataFrame.from_dict(
        {
            "if1": [3, 4, 5, 4.5],
            "if3": ["c1", "c2", "c3", "c1"],
            "if5": ["c1", "c2", "c3", "c1"],
            "if9": [1.0, 2.0, 1.0, 2.0],
            "of1": [10, 11, 12, 13],
            "valid_of1": [1, 0, 1, 0],
        }
    ),
    pd.DataFrame.from_dict(
        {
            "if1": [3, 4, 5, 4.5],
            "if2": [3, 3, 3, 3],
            "if3": ["c1", "c2", "c3", "c1"],
            "if4": ["c1", "c1", "c1", "c1"],
            "if5": ["c1", "c2", "c3", "c1"],
            "if6": ["c1", "c1", "c1", "c1"],
            "if9": [1.0, 2.0, 1.0, 2.0],
            "of1": [10, 11, 12, 13],
            "valid_of1": [1, 0, 1, 0],
        }
    ),
    pd.DataFrame.from_dict(
        {
            "if1": [3, 4, 5, 4.5],
            "if2": [3, 3, 3, 3],
            "if3": ["c1", "c2", "c3", "c1"],
            "if4": ["c1", "c1", "c1", "c1"],
            "if5": ["c1", "c2", "c3", "c1"],
            "if6": ["c1", "c1", "c1", "c1"],
            "if9": [1.0, 2.0, 1.0, 2.0],
            "of1": [10, 11, 12, 13],
            "of2": [100, 103, 105, 110],
            "valid_of1": [1, 0, 1, 0],
            "valid_of2": [0, 1, 1, 0],
        }
    ),
    pd.DataFrame.from_dict(
        {
            "if1": [3, 4, 5, 4.5],
            "if2": [3, 3, 3, 3],
            "of1": [10, 11, 12, 13],
            "valid_of1": [1, 0, 1, 0],
        }
    ),
    pd.DataFrame.from_dict(
        {
            "if1": [3, 4, 5, 4.5],
            "if3": ["c1", "c2", "c3", "c1"],
            "if5": ["c1", "c2", "c3", "c1"],
            "if9": [1.0, 2.0, 1.0, 2.0],
            "of1": [10, 11, 12, 13],
            "of2": [100, 103, 105, 110],
            "valid_of1": [1, 0, 1, 0],
            "valid_of2": [0, 1, 1, 0],
        }
    ),
]


@pytest.mark.parametrize("domain", [(domain) for domain in domains])
def test_base_create(domain: Domain):
    with pytest.raises(ValueError, match="number sobol samples"):
        DummyStrategyDataModel(domain=domain, num_sobol_samples=5)

    with pytest.raises(ValueError, match="number raw samples"):
        DummyStrategyDataModel(domain=domain, num_raw_samples=5)


def test_base_invalid_descriptor_method():
    with pytest.raises(ValueError):
        DummyStrategyDataModel(
            domain=domains[0],
            surrogate_specs=[
                surrogate_data_models.SingleTaskGPSurrogate(
                    input_features=domains[0].input_features,
                    output_features=domains[0].output_features,
                    input_preprocessing_specs={"if5": CategoricalEncodingEnum.ONE_HOT},
                )
            ],
            descriptor_method="FREE",
            categorical_method="EXHAUSTIVE",
        )


@pytest.mark.parametrize(
    # "domain, descriptor_encoding, categorical_encoding, categorical_method, expected",
    "domain, surrogate_specs, categorical_method, descriptor_method, expected",
    [
        (domains[0], None, "EXHAUSTIVE", "EXHAUSTIVE", {}),
        (
            domains[1],
            None,
            "EXHAUSTIVE",
            "EXHAUSTIVE",
            {1: 3, 5: 1, 6: 2, 10: 1, 11: 0, 12: 0},
        ),
        (
            domains[1],
            surrogate_data_models.BotorchSurrogates(
                surrogates=[
                    surrogate_data_models.SingleTaskGPSurrogate(
                        input_features=domains[1].input_features,
                        output_features=domains[1].output_features,
                        input_preprocessing_specs={
                            "if5": CategoricalEncodingEnum.ONE_HOT,
                            "if6": CategoricalEncodingEnum.ONE_HOT,
                        },
                    )
                ]
            ),
            "EXHAUSTIVE",
            "EXHAUSTIVE",
            {1: 3, 6: 1, 7: 0, 8: 0, 12: 1, 13: 0, 14: 0},
        ),
        (
            domains[1],
            surrogate_data_models.BotorchSurrogates(
                surrogates=[
                    surrogate_data_models.SingleTaskGPSurrogate(
                        input_features=domains[1].input_features,
                        output_features=domains[1].output_features,
                    )
                ]
            ),
            "FREE",
            "EXHAUSTIVE",
            {1: 3, 5: 1, 6: 2, 10: 1, 11: 0, 12: 0},
        ),
        (  #
            domains[1],
            surrogate_data_models.BotorchSurrogates(
                surrogates=[
                    surrogate_data_models.SingleTaskGPSurrogate(
                        input_features=domains[1].input_features,
                        output_features=domains[1].output_features,
                        input_preprocessing_specs={
                            "if5": CategoricalEncodingEnum.ONE_HOT,
                            "if6": CategoricalEncodingEnum.ONE_HOT,
                        },
                    )
                ]
            ),
            "FREE",
            "FREE",
            {1: 3, 6: 1, 7: 0, 8: 0, 12: 1, 13: 0, 14: 0},
        ),
        (domains[5], None, "EXHAUSTIVE", "EXHAUSTIVE", {1: 3.0}),
        (
            domains[5],
            surrogate_data_models.BotorchSurrogates(
                surrogates=[
                    surrogate_data_models.SingleTaskGPSurrogate(
                        input_features=domains[5].input_features,
                        output_features=domains[5].output_features,
                        input_preprocessing_specs={
                            "if8": CategoricalEncodingEnum.ONE_HOT,
                        },
                    )
                ]
            ),
            "FREE",
            "FREE",
            {1: 3.0, 2: 0},
        ),
        (domains[5], None, "FREE", "EXHAUSTIVE", {1: 3.0}),
        (domains[5], None, "FREE", "FREE", {1: 3.0, 2: 3.0}),
    ],
)
def test_base_get_fixed_features(
    domain, surrogate_specs, categorical_method, descriptor_method, expected
):
    data_model = DummyStrategyDataModel(
        domain=domain,
        surrogate_specs=surrogate_specs,
        categorical_method=categorical_method,
        descriptor_method=descriptor_method,
    )
    myStrategy = DummyStrategy(data_model=data_model)

    experiments = generate_experiments(domain, 100, tol=1.0)
    myStrategy.set_experiments(experiments)

    fixed_features = myStrategy.get_fixed_features()

    assert fixed_features == expected


@pytest.mark.parametrize(
    "domain, descriptor_method, categorical_method, discrete_method, surrogate_specs, expected",
    [
        (
            domains[0],
            "EXHAUSTIVE",
            "EXHAUSTIVE",
            "EXHAUSTIVE",
            None,
            [
                {4: 1.0, 5: 0.0, 6: 0.0, 2: 1.0, 3: 2.0, 1: 1},
                {4: 1.0, 5: 0.0, 6: 0.0, 2: 3.0, 3: 7.0, 1: 1},
                {4: 1.0, 5: 0.0, 6: 0.0, 2: 5.0, 3: 1.0, 1: 1},
                {4: 0.0, 5: 1.0, 6: 0.0, 2: 1.0, 3: 2.0, 1: 1},
                {4: 0.0, 5: 1.0, 6: 0.0, 2: 3.0, 3: 7.0, 1: 1},
                {4: 0.0, 5: 1.0, 6: 0.0, 2: 5.0, 3: 1.0, 1: 1},
                {4: 0.0, 5: 0.0, 6: 1.0, 2: 1.0, 3: 2.0, 1: 1},
                {4: 0.0, 5: 0.0, 6: 1.0, 2: 3.0, 3: 7.0, 1: 1},
                {4: 0.0, 5: 0.0, 6: 1.0, 2: 5.0, 3: 1.0, 1: 1},
                {4: 1.0, 5: 0.0, 6: 0.0, 2: 1.0, 3: 2.0, 1: 2},
                {4: 1.0, 5: 0.0, 6: 0.0, 2: 3.0, 3: 7.0, 1: 2},
                {4: 1.0, 5: 0.0, 6: 0.0, 2: 5.0, 3: 1.0, 1: 2},
                {4: 0.0, 5: 1.0, 6: 0.0, 2: 1.0, 3: 2.0, 1: 2},
                {4: 0.0, 5: 1.0, 6: 0.0, 2: 3.0, 3: 7.0, 1: 2},
                {4: 0.0, 5: 1.0, 6: 0.0, 2: 5.0, 3: 1.0, 1: 2},
                {4: 0.0, 5: 0.0, 6: 1.0, 2: 1.0, 3: 2.0, 1: 2},
                {4: 0.0, 5: 0.0, 6: 1.0, 2: 3.0, 3: 7.0, 1: 2},
                {4: 0.0, 5: 0.0, 6: 1.0, 2: 5.0, 3: 1.0, 1: 2},
            ],
        ),
        (
            domains[0],
            "EXHAUSTIVE",
            "EXHAUSTIVE",
            "FREE",
            None,
            [
                {4: 1.0, 5: 0.0, 6: 0.0, 2: 1.0, 3: 2.0},
                {4: 1.0, 5: 0.0, 6: 0.0, 2: 3.0, 3: 7.0},
                {4: 1.0, 5: 0.0, 6: 0.0, 2: 5.0, 3: 1.0},
                {4: 0.0, 5: 1.0, 6: 0.0, 2: 1.0, 3: 2.0},
                {4: 0.0, 5: 1.0, 6: 0.0, 2: 3.0, 3: 7.0},
                {4: 0.0, 5: 1.0, 6: 0.0, 2: 5.0, 3: 1.0},
                {4: 0.0, 5: 0.0, 6: 1.0, 2: 1.0, 3: 2.0},
                {4: 0.0, 5: 0.0, 6: 1.0, 2: 3.0, 3: 7.0},
                {4: 0.0, 5: 0.0, 6: 1.0, 2: 5.0, 3: 1.0},
            ],
        ),
        (
            domains[0],
            "EXHAUSTIVE",
            "EXHAUSTIVE",
            "EXHAUSTIVE",
            surrogate_data_models.BotorchSurrogates(
                surrogates=[
                    surrogate_data_models.SingleTaskGPSurrogate(
                        input_features=domains[0].input_features,
                        output_features=domains[0].output_features,
                        input_preprocessing_specs={
                            "if5": CategoricalEncodingEnum.ONE_HOT,
                        },
                    )
                ]
            ),
            [
                {2: 1.0, 3: 0.0, 4: 0.0, 5: 1.0, 6: 0.0, 7: 0.0, 1: 1},
                {2: 1.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 1.0, 7: 0.0, 1: 1},
                {2: 1.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 1.0, 1: 1},
                {2: 0.0, 3: 1.0, 4: 0.0, 5: 1.0, 6: 0.0, 7: 0.0, 1: 1},
                {2: 0.0, 3: 1.0, 4: 0.0, 5: 0.0, 6: 1.0, 7: 0.0, 1: 1},
                {2: 0.0, 3: 1.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 1.0, 1: 1},
                {2: 0.0, 3: 0.0, 4: 1.0, 5: 1.0, 6: 0.0, 7: 0.0, 1: 1},
                {2: 0.0, 3: 0.0, 4: 1.0, 5: 0.0, 6: 1.0, 7: 0.0, 1: 1},
                {2: 0.0, 3: 0.0, 4: 1.0, 5: 0.0, 6: 0.0, 7: 1.0, 1: 1},
                {2: 1.0, 3: 0.0, 4: 0.0, 5: 1.0, 6: 0.0, 7: 0.0, 1: 2},
                {2: 1.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 1.0, 7: 0.0, 1: 2},
                {2: 1.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 1.0, 1: 2},
                {2: 0.0, 3: 1.0, 4: 0.0, 5: 1.0, 6: 0.0, 7: 0.0, 1: 2},
                {2: 0.0, 3: 1.0, 4: 0.0, 5: 0.0, 6: 1.0, 7: 0.0, 1: 2},
                {2: 0.0, 3: 1.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 1.0, 1: 2},
                {2: 0.0, 3: 0.0, 4: 1.0, 5: 1.0, 6: 0.0, 7: 0.0, 1: 2},
                {2: 0.0, 3: 0.0, 4: 1.0, 5: 0.0, 6: 1.0, 7: 0.0, 1: 2},
                {2: 0.0, 3: 0.0, 4: 1.0, 5: 0.0, 6: 0.0, 7: 1.0, 1: 2},
            ],
        ),
        (
            domains[0],
            "EXHAUSTIVE",
            "EXHAUSTIVE",
            "FREE",
            surrogate_data_models.BotorchSurrogates(
                surrogates=[
                    surrogate_data_models.SingleTaskGPSurrogate(
                        input_features=domains[0].input_features,
                        output_features=domains[0].output_features,
                        input_preprocessing_specs={
                            "if5": CategoricalEncodingEnum.ONE_HOT,
                        },
                    )
                ]
            ),
            [
                {2: 1.0, 3: 0.0, 4: 0.0, 5: 1.0, 6: 0.0, 7: 0.0},
                {2: 1.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 1.0, 7: 0.0},
                {2: 1.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 1.0},
                {2: 0.0, 3: 1.0, 4: 0.0, 5: 1.0, 6: 0.0, 7: 0.0},
                {2: 0.0, 3: 1.0, 4: 0.0, 5: 0.0, 6: 1.0, 7: 0.0},
                {2: 0.0, 3: 1.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 1.0},
                {2: 0.0, 3: 0.0, 4: 1.0, 5: 1.0, 6: 0.0, 7: 0.0},
                {2: 0.0, 3: 0.0, 4: 1.0, 5: 0.0, 6: 1.0, 7: 0.0},
                {2: 0.0, 3: 0.0, 4: 1.0, 5: 0.0, 6: 0.0, 7: 1.0},
            ],
        ),
        (
            domains[0],
            "EXHAUSTIVE",
            "FREE",
            "FREE",
            surrogate_data_models.BotorchSurrogates(
                surrogates=[
                    surrogate_data_models.SingleTaskGPSurrogate(
                        input_features=domains[0].input_features,
                        output_features=domains[0].output_features,
                    )
                ]
            ),
            [{2: 1.0, 3: 2.0}, {2: 3.0, 3: 7.0}, {2: 5.0, 3: 1.0}],
        ),
        (
            domains[0],
            "FREE",
            "FREE",
            "EXHAUSTIVE",
            surrogate_data_models.BotorchSurrogates(
                surrogates=[
                    surrogate_data_models.SingleTaskGPSurrogate(
                        input_features=domains[0].input_features,
                        output_features=domains[0].output_features,
                    )
                ]
            ),
            [{1: 1.0}, {1: 2.0}],
        ),
        (
            domains[0],
            "EXHAUSTIVE",
            "FREE",
            "EXHAUSTIVE",
            surrogate_data_models.BotorchSurrogates(
                surrogates=[
                    surrogate_data_models.SingleTaskGPSurrogate(
                        input_features=domains[0].input_features,
                        output_features=domains[0].output_features,
                    )
                ]
            ),
            [
                {2: 1.0, 3: 2.0, 1: 1.0},
                {2: 3.0, 3: 7.0, 1: 1.0},
                {2: 5.0, 3: 1.0, 1: 1.0},
                {2: 1.0, 3: 2.0, 1: 2.0},
                {2: 3.0, 3: 7.0, 1: 2.0},
                {2: 5.0, 3: 1.0, 1: 2.0},
            ],
        ),
        (
            domains[0],
            "FREE",
            "FREE",
            "FREE",
            surrogate_data_models.BotorchSurrogates(
                surrogates=[
                    surrogate_data_models.SingleTaskGPSurrogate(
                        input_features=domains[0].input_features,
                        output_features=domains[0].output_features,
                        input_preprocessing_specs={
                            "if5": CategoricalEncodingEnum.ONE_HOT
                        },
                    )
                ]
            ),
            [{}],
        ),
        (
            domains[0],
            "FREE",
            "EXHAUSTIVE",
            "FREE",
            None,
            [
                {4: 1.0, 5: 0.0, 6: 0.0},
                {4: 0.0, 5: 1.0, 6: 0.0},
                {4: 0.0, 5: 0.0, 6: 1.0},
            ],
        ),
        (
            domains[3],
            "EXHAUSTIVE",
            "EXHAUSTIVE",
            "EXHAUSTIVE",
            None,
            [
                {1: 3.0},
            ],
        ),
    ],
)
def test_base_get_categorical_combinations(
    domain,
    descriptor_method,
    categorical_method,
    discrete_method,
    surrogate_specs,
    expected,
):
    data_model = DummyStrategyDataModel(
        domain=domain,
        surrogate_specs=surrogate_specs,
        descriptor_method=descriptor_method,
        categorical_method=categorical_method,
        discrete_method=discrete_method,
    )
    myStrategy = DummyStrategy(data_model=data_model)
    c = unittest.TestCase()
    combo = myStrategy.get_categorical_combinations()
    c.assertCountEqual(combo, expected)


@pytest.mark.parametrize("domain", [(domains[0])])
def test_base_invalid_pair_encoding_method(domain):
    with pytest.raises(ValueError):
        DummyStrategyDataModel(
            domain=domain, categorical_encoding="ORDINAL", categorical_method="FREE"
        )


@pytest.mark.parametrize(
    "domain, data, acquisition_function",
    [
        (
            domains[0],
            generate_experiments(
                domains[0], row_count=5, tol=1.0, force_all_categories=True
            ),
            specs.acquisition_functions.valid().obj().dict(),
        ),
        (
            domains[1],
            generate_experiments(
                domains[1], row_count=5, tol=1.0, force_all_categories=True
            ),
            specs.acquisition_functions.valid().obj().dict(),
        ),
        (
            domains[2],
            generate_experiments(
                domains[2], row_count=5, tol=1.0, force_all_categories=True
            ),
            specs.acquisition_functions.valid().obj().dict(),
        ),
        (
            domains[4],
            generate_experiments(
                domains[4], row_count=5, tol=1.0, force_all_categories=True
            ),
            specs.acquisition_functions.valid().obj().dict(),
        ),
    ],
)
def test_base_fit(domain, data, acquisition_function):
    data_model = DummyStrategyDataModel(
        domain=domain, acquisition_function=acquisition_function
    )
    myStrategy = DummyStrategy(data_model=data_model)
    myStrategy.set_experiments(data)
    myStrategy.fit()


@pytest.mark.parametrize(
    "domain, data, acquisition_function",
    [
        (
            domains[0],
            generate_experiments(
                domains[0], row_count=10, tol=1.0, force_all_categories=True
            ),
            specs.acquisition_functions.valid().obj(),
        ),
        (
            domains[1],
            generate_experiments(
                domains[1], row_count=10, tol=1.0, force_all_categories=True
            ),
            specs.acquisition_functions.valid().obj(),
        ),
        (
            domains[2],
            generate_experiments(
                domains[2], row_count=10, tol=1.0, force_all_categories=True
            ),
            specs.acquisition_functions.valid().obj(),
        ),
        # TODO: this tests randomly fails (All attempts to fit the model have failed.)
        # (
        #     domains[4],
        #     generate_experiments(
        #         domains[4], row_count=10, tol=1.0, force_all_categories=True
        #     ),
        #     specs.acquisition_functions.valid().obj(),
        # ),
    ],
)
def test_base_predict(domain, data, acquisition_function):
    data_model = DummyStrategyDataModel(
        domain=domain, acquisition_function=acquisition_function
    )
    myStrategy = DummyStrategy(data_model=data_model)
    myStrategy.tell(experiments=data)
    predictions = myStrategy.predict(data)
    assert len(predictions.columns.tolist()) == 3 * len(domain.get_feature_keys(Output))
    assert data.index[-1] == predictions.index[-1]