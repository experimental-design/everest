from typing import Dict, List

import numpy as np
import pandas as pd

from bofire.models.diagnostics import metrics
from bofire.models.model import Model
from bofire.utils.enum import RegressionMetricsEnum


def permutation_importance(
    model: Model, X: pd.DataFrame, y: pd.DataFrame, n_repeats: int = 5, seed: int = 42
) -> Dict[str, pd.DataFrame]:
    """Computes permutation feature importance for a model.

    Args:
        model (Model): Model for which the feature importances should be estimated.
        X (pd.DataFrame): X values used to estimate the importances.
        y (pd.DataFrame): Y values used to estimate the importances.
        n_repeats (int, optional): Number of repeats. Defaults to 5.
        seed (int, optional): Seed for the random sampler. Defaults to 42.

    Returns:
        Dict[str, pd.DataFrame]: keys are the metrices for which the model is evluated and value is a dataframe
            with the feature keys as columns and the mean and std of the respective permutation importances as rows.
    """
    assert len(model.output_features) == 1
    assert n_repeats > 1
    output_key = model.output_features[0].key
    rng = np.random.default_rng(seed)
    prelim_results = {
        k.name: {feature.key: [] for feature in model.input_features}
        for k in metrics.keys()
    }
    pred = model.predict(X)
    original_metrics = {
        k.name: metrics[k](y[output_key].values, pred[output_key + "_pred"].values)  # type: ignore
        for k in metrics.keys()
    }

    for feature in model.input_features:
        for _ in range(n_repeats):
            # shuffle
            X_i = X.copy()
            X_i[feature.key] = rng.permutation(X_i[feature.key].values)  # type: ignore
            # predict
            pred = model.predict(X_i)
            # compute scores
            for metricenum, metric in metrics.items():
                prelim_results[metricenum.name][feature.key].append(
                    metric(y[output_key].values, pred[output_key + "_pred"].values)  # type: ignore
                )
    # convert dictionaries to dataframe for easier postprocessing and statistics
    # and return
    results = {}
    for k in metrics.keys():
        results[k.name] = pd.DataFrame(
            data={
                feature.key: [
                    original_metrics[k.name]
                    - np.mean(prelim_results[k.name][feature.key]),
                    np.std(prelim_results[k.name][feature.key]),
                ]
                for feature in model.input_features
            },
            index=["mean", "std"],
        )

    return results


def permutation_importance_hook(
    model: Model,
    X_train: pd.DataFrame,
    y_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_test: pd.DataFrame,
    use_test: bool = True,
    n_repeats: int = 5,
    seed: int = 42,
):
    """Hook that can be used within `model.cross_validate` to compute a cross validated permutation feature importance.

    Args:
        model (Model): Predictive BoFire model.
        X_train (pd.DataFrame):
        y_train (pd.DataFrame): _description_
        X_test (pd.DataFrame): _description_
        y_test (pd.DataFrame): _description_
        use_test (bool, optional): _description_. Defaults to True.
        n_repeats (int, optional): _description_. Defaults to 5.
        seed (int, optional): _description_. Defaults to 42.

    Returns:
        _type_: _description_
    """
    if use_test:
        X = X_test
        y = y_test
    else:
        X = X_train
        y = y_train
    return permutation_importance(model=model, X=X, y=y, n_repeats=n_repeats, seed=seed)


def combine_permutation_importances(
    importances: List[Dict[str, pd.DataFrame]], metric: RegressionMetricsEnum
) -> pd.DataFrame:
    feature_keys = list(importances[0]["MAE"].columns)
    return pd.DataFrame(
        data={
            key: [fold[metric.name].loc["mean", key] for fold in importances]
            for key in feature_keys
        }
    )
