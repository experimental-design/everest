from pytest import fixture

from bofire.domain.constraints import Constraint
from bofire.domain.features import Feature
from bofire.domain.objectives import Objective
from tests.bofire import specs

# objective


@fixture
def objective() -> Objective:
    return specs.objectives.valid().obj()


@fixture(params=specs.objectives.valids)
def valid_objective_spec(request) -> specs.Spec:
    return request.param


@fixture(params=specs.objectives.invalids)
def invalid_objective_spec(request) -> specs.Spec:
    return request.param


# feature


@fixture
def feature() -> Feature:
    return specs.features.valid().obj()


@fixture(params=specs.features.valids)
def valid_feature_spec(request) -> specs.Spec:
    return request.param


@fixture(params=specs.features.invalids)
def invalid_feature_spec(request) -> specs.Spec:
    return request.param


# constraint


@fixture
def constraint() -> Constraint:
    return specs.constraints.valid().obj()


@fixture(params=specs.constraints.valids)
def valid_constraint_spec(request) -> specs.Spec:
    return request.param


@fixture(params=specs.constraints.invalids)
def invalid_constraint_spec(request) -> specs.Spec:
    return request.param
