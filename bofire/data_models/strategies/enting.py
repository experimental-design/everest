from typing import Literal, Type

from bofire.data_models.constraints.api import (
    Constraint,
    LinearEqualityConstraint,
    LinearInequalityConstraint,
)
from bofire.data_models.features.api import (
    CategoricalDescriptorInput,
    CategoricalInput,
    ContinuousInput,
    ContinuousOutput,
    DiscreteInput,
    Feature,
)
from bofire.data_models.objectives.api import MinimizeObjective, Objective
from bofire.data_models.strategies.strategy import Strategy


class EntingStrategy(Strategy):
    type: Literal["EntingStrategy"] = "EntingStrategy"

    @classmethod
    def is_constraint_implemented(cls, my_type: Type[Constraint]) -> bool:
        return my_type in [LinearEqualityConstraint, LinearInequalityConstraint]

    @classmethod
    def is_feature_implemented(cls, my_type: Type[Feature]) -> bool:
        return my_type in [
            CategoricalInput,
            DiscreteInput,
            CategoricalDescriptorInput,
            ContinuousInput,
            ContinuousOutput,
        ]

    @classmethod
    def is_objective_implemented(cls, my_type: Type[Objective]) -> bool:
        return my_type in [MinimizeObjective]
