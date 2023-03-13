import math
from itertools import chain

import pytest
import torch

import bofire.data_models.strategies.api as data_models
import tests.bofire.data_models.specs.api as specs
from bofire.benchmarks.multi import DTLZ2
from bofire.data_models.acquisition_functions.api import qUCB
from bofire.data_models.samplers.api import PolytopeSampler
from bofire.strategies.api import SoboStrategy
from tests.bofire.strategies.test_base import domains

# from tests.bofire.strategies.botorch.test_model_spec import VALID_MODEL_SPEC_LIST

VALID_BOTORCH_SOBO_STRATEGY_SPEC = {
    "domain": domains[2],
    "acquisition_function": specs.acquisition_functions.valid().obj(),
    # "num_sobol_samples": 1024,
    # "num_restarts": 8,
    # "num_raw_samples": 1024,
    "descriptor_method": "EXHAUSTIVE",
    "categorical_method": "EXHAUSTIVE",
}

BOTORCH_SOBO_STRATEGY_SPECS = {
    "valids": [
        VALID_BOTORCH_SOBO_STRATEGY_SPEC,
        {**VALID_BOTORCH_SOBO_STRATEGY_SPEC, "seed": 1},
        # {**VALID_BOTORCH_SOBO_STRATEGY_SPEC, "surrogate_specs": VALID_MODEL_SPEC_LIST},
    ],
    "invalids": [
        {**VALID_BOTORCH_SOBO_STRATEGY_SPEC, "acquisition_function": None},
        {**VALID_BOTORCH_SOBO_STRATEGY_SPEC, "descriptor_method": None},
        {**VALID_BOTORCH_SOBO_STRATEGY_SPEC, "categorical_method": None},
        # {**VALID_BOTORCH_SOBO_STRATEGY_SPEC, "seed": -1},
    ],
}


@pytest.mark.parametrize(
    "domain, acqf",
    [(domains[0], VALID_BOTORCH_SOBO_STRATEGY_SPEC["acquisition_function"])],
)
def test_SOBO_not_fitted(domain, acqf):
    data_model = data_models.SoboStrategy(domain=domain, acquisition_function=acqf)
    strategy = SoboStrategy(data_model=data_model)

    msg = "Model not trained."
    with pytest.raises(AssertionError, match=msg):
        strategy._init_acqf()


# TODO: can this tests be removed as acqfs are not initialized via str / enum anymore
# @pytest.mark.parametrize(
#     "acqf, expected, num_test_candidates",
#     [
#         (acqf_inp[0], acqf_inp[1], num_test_candidates)
#         for acqf_inp in [
#             ("QEI", qExpectedImprovement),
#             ("QNEI", qNoisyExpectedImprovement),
#             ("QPI", qProbabilityOfImprovement),
#             ("QUCB", qUpperConfidenceBound),
#             ("QSR", qSimpleRegret),
#             (qEI(), qExpectedImprovement),
#             (qNEI(), qNoisyExpectedImprovement),
#             (qPI(), qProbabilityOfImprovement),
#             (qUCB(), qUpperConfidenceBound),
#             (qSR(), qSimpleRegret),
#         ]
#         for num_test_candidates in range(1, 3)
#     ],
# )
# def test_SOBO_init_acqf(acqf, expected, num_test_candidates):
#     # generate data
#     benchmark = DTLZ2(dim=6)
#     random_strategy = PolytopeSampler(domain=benchmark.domain)
#     experiments = benchmark.f(random_strategy._sample(n=20), return_complete=True)
#     experiments_test = benchmark.f(
#         random_strategy._sample(n=num_test_candidates), return_complete=True
#     )

#     data_model = data_models.SoboStrategy(
#         domain=benchmark.domain, acquisition_function=acqf
#     )
#     strategy = SoboStrategy(data_model=data_model)

#     strategy.tell(experiments)
#     assert isinstance(strategy.acqf, expected)
#     # test acqf calc
#     acqf_vals = strategy._choose_from_pool(experiments_test, num_test_candidates)
#     assert acqf_vals.shape[0] == num_test_candidates


def test_SOBO_init_qUCB():
    beta = 0.5
    acqf = qUCB(beta=beta)

    # generate data
    benchmark = DTLZ2(dim=6)
    random_strategy = PolytopeSampler(domain=benchmark.domain)
    experiments = benchmark.f(random_strategy._sample(n=20), return_complete=True)

    data_model = data_models.SoboStrategy(
        domain=benchmark.domain, acquisition_function=acqf
    )
    strategy = SoboStrategy(data_model=data_model)
    strategy.tell(experiments)
    assert strategy.acqf.beta_prime == math.sqrt(beta * math.pi / 2)


@pytest.mark.parametrize(
    "acqf, num_experiments, num_candidates",
    [
        (acqf.obj(), num_experiments, num_candidates)
        for acqf in specs.acquisition_functions.valids
        for num_experiments in range(8, 10)
        for num_candidates in range(1, 3)
    ],
)
@pytest.mark.slow
def test_get_acqf_input(acqf, num_experiments, num_candidates):
    # generate data
    benchmark = DTLZ2(dim=6)
    random_strategy = PolytopeSampler(domain=benchmark.domain)
    experiments = benchmark.f(
        random_strategy._sample(n=num_experiments), return_complete=True
    )

    data_model = data_models.SoboStrategy(
        domain=benchmark.domain, acquisition_function=acqf
    )
    strategy = SoboStrategy(data_model=data_model)

    strategy.tell(experiments)
    strategy.ask(candidate_count=num_candidates, add_pending=True)

    X_train, X_pending = strategy.get_acqf_input_tensors()

    _, names = strategy.domain.input_features._get_transform_info(
        specs=strategy.surrogate_specs.input_preprocessing_specs
    )

    assert torch.is_tensor(X_train)
    assert torch.is_tensor(X_pending)
    assert X_train.shape == (
        num_experiments,
        len(set(chain(*names.values()))),
    )
    assert X_pending.shape == (
        num_candidates,
        len(set(chain(*names.values()))),
    )
