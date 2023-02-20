import numpy as np
import pytest
import torch
from sklearn.ensemble import RandomForestRegressor
from sklearn.exceptions import NotFittedError

from bofire.benchmarks.single import Himmelblau
from bofire.domain.feature import CategoricalInput, ContinuousInput, ContinuousOutput
from bofire.domain.features import InputFeatures, OutputFeatures
from bofire.models.random_forest import RandomForest, _RandomForest
from bofire.utils.enum import CategoricalEncodingEnum


def test_random_forest_no_random_forest_regressor():
    with pytest.raises(ValueError):
        _RandomForest(rf=5)


def test_random_forest_not_fitted():
    with pytest.raises(NotFittedError):
        _RandomForest(rf=RandomForestRegressor())


def test_random_forest_forward():
    bench = Himmelblau()
    samples = bench.domain.inputs.sample(10)
    experiments = bench.f(samples, return_complete=True)
    rfr = RandomForestRegressor().fit(
        experiments[["x_1", "x_2"]].values, experiments.y.values.ravel()
    )
    rf = _RandomForest(rf=rfr)
    pred = rf.forward(torch.from_numpy(experiments[["x_1", "x_2"]].values))
    assert np.allclose(
        rfr.predict(experiments[["x_1", "x_2"]].values),
        pred.numpy().mean(axis=-3).ravel(),
    )
    assert np.allclose(
        rfr.predict(experiments[["x_1", "x_2"]].values),
        rf.posterior(torch.from_numpy(experiments[["x_1", "x_2"]].values))
        .mean.numpy()
        .ravel(),
    )
    assert pred.shape == torch.Size((100, 10, 1))
    # test with batches
    batch = torch.from_numpy(experiments[["x_1", "x_2"]].values).unsqueeze(0)
    pred = rf.forward(batch)
    assert pred.shape == torch.Size((1, 100, 10, 1))
    assert rf.num_outputs == 1


def test_random_forest():
    # test only continuous
    bench = Himmelblau()
    samples = bench.domain.inputs.sample(10)
    experiments = bench.f(samples, return_complete=True)
    rf = RandomForest(
        input_features=bench.domain.inputs, output_features=bench.domain.outputs
    )
    rf.fit(experiments=experiments)
    # test with categoricals
    input_features = InputFeatures(
        features=[
            ContinuousInput(key=f"x_{i+1}", lower_bound=-4, upper_bound=4)
            for i in range(2)
        ]
        + [CategoricalInput(key="x_cat", categories=["mama", "papa"])]
    )
    output_features = OutputFeatures(features=[ContinuousOutput(key="y")])
    experiments = input_features.sample(n=10)
    experiments.eval("y=((x_1**2 + x_2 - 11)**2+(x_1 + x_2**2 -7)**2)", inplace=True)
    experiments.loc[experiments.x_cat == "mama", "y"] *= 5.0
    experiments.loc[experiments.x_cat == "papa", "y"] /= 2.0
    experiments["valid_y"] = 1
    rf = RandomForest(input_features=input_features, output_features=output_features)
    assert rf.input_preprocessing_specs["x_cat"] == CategoricalEncodingEnum.ONE_HOT
    rf.fit(experiments=experiments)