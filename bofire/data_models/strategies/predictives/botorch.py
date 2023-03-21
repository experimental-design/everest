from typing import Optional

from pydantic import PositiveInt, root_validator, validator

from bofire.data_models.domain.api import Domain, Outputs
from bofire.data_models.enum import CategoricalEncodingEnum, CategoricalMethodEnum
from bofire.data_models.features.api import CategoricalDescriptorInput, CategoricalInput
from bofire.data_models.strategies.predictives.predictive import PredictiveStrategy
from bofire.data_models.surrogates.api import (
    BotorchSurrogates,
    MixedSingleTaskGPSurrogate,
    SingleTaskGPSurrogate,
)


def is_power_of_two(n):
    return (n != 0) and (n & (n - 1) == 0)


class BotorchStrategy(PredictiveStrategy):
    """
    This is a class for a Botorch strategy that extends from the PredictiveStrategy class. This class is used for optimizing problems using Bayesian optimization.

    Attributes:
    num_sobol_samples (PositiveInt): The number of Sobol samples to be used for generating initial candidates.
    num_restarts (PositiveInt): The number of restarts for generating candidates using optimization.
    num_raw_samples (PositiveInt): The number of raw samples to be used for generating initial candidates.
    descriptor_method (CategoricalMethodEnum): The method to be used for encoding categorical descriptor inputs.
    categorical_method (CategoricalMethodEnum): The method to be used for encoding categorical inputs.
    discrete_method (CategoricalMethodEnum): The method to be used for encoding discrete inputs.
    surrogate_specs (Optional[BotorchSurrogates]): The specifications for the Botorch surrogates used for modeling the problem.

    Methods:
    validate_num_sobol_samples(cls, v): A validator method that ensures the number of Sobol samples is a power of 2.
    validate_num_raw_samples(cls, v): A validator method that ensures the number of raw samples is a power of 2.
    update_surrogate_specs_for_domain(cls, values): A root validator method that ensures that a prediction model is specified for each output feature and that the categorical method is compatible with the chosen models.
    _generate_surrogate_specs(domain: Domain, surrogate_specs: Optional[BotorchSurrogates] = None) -> BotorchSurrogates: A static method that generates the specifications for the Botorch surrogates used for modeling the problem when no specifications are passed. The default specification used is a 5/2 Matern kernel with automated relevance detection and normalization of input features.

    Raises:
    ValueError: If the number of Sobol samples or raw samples is not a power of 2.
    ValueError: If the categorical method is not compatible with the chosen models.
    KeyError: If there is a model specification for an unknown output feature or an unknown input feature.

    Returns:
    None
    """

    num_sobol_samples: PositiveInt = 512
    num_restarts: PositiveInt = 8
    num_raw_samples: PositiveInt = 1024
    descriptor_method: CategoricalMethodEnum = CategoricalMethodEnum.EXHAUSTIVE
    categorical_method: CategoricalMethodEnum = CategoricalMethodEnum.EXHAUSTIVE
    discrete_method: CategoricalMethodEnum = CategoricalMethodEnum.EXHAUSTIVE
    surrogate_specs: Optional[BotorchSurrogates] = None

    @validator("num_sobol_samples")
    def validate_num_sobol_samples(cls, v):
        if is_power_of_two(v) is False:
            raise ValueError(
                "number sobol samples have to be of the power of 2 to increase performance"
            )
        return v

    @validator("num_raw_samples")
    def validate_num_raw_samples(cls, v):
        if is_power_of_two(v) is False:
            raise ValueError(
                "number raw samples have to be of the power of 2 to increase performance"
            )
        return v

    @root_validator(pre=False, skip_on_failure=True)
    def update_surrogate_specs_for_domain(cls, values):
        """Ensures that a prediction model is specified for each output feature"""
        values["surrogate_specs"] = BotorchStrategy._generate_surrogate_specs(
            values["domain"],
            values["surrogate_specs"],
        )
        # we also have to checke here that the categorical method is compatible with the chosen models
        if values["categorical_method"] == CategoricalMethodEnum.FREE:
            for m in values["surrogate_specs"].surrogates:
                if isinstance(m, MixedSingleTaskGPSurrogate):
                    raise ValueError(
                        "Categorical method FREE not compatible with a a MixedSingleTaskGPModel."
                    )
        #  we also check that if a categorical with descriptor method is used as one hot encoded the same method is
        # used for the descriptor as for the categoricals
        for m in values["surrogate_specs"].surrogates:
            keys = m.input_features.get_keys(CategoricalDescriptorInput)
            for k in keys:
                if m.input_preprocessing_specs[k] == CategoricalEncodingEnum.ONE_HOT:
                    if values["categorical_method"] != values["descriptor_method"]:
                        print(values["categorical_method"], values["descriptor_method"])
                        raise ValueError(
                            "One-hot encoded CategoricalDescriptorInput features has to be treated with the same method as categoricals."
                        )
        return values

    @staticmethod
    def _generate_surrogate_specs(
        domain: Domain,
        surrogate_specs: Optional[BotorchSurrogates] = None,
    ) -> BotorchSurrogates:
        """Method to generate model specifications when no model specs are passed
        As default specification, a 5/2 matern kernel with automated relevance detection and normalization of the input features is used.
        Args:
            domain (Domain): The domain defining the problem to be optimized with the strategy
            surrogate_specs (List[ModelSpec], optional): List of model specification classes specifying the models to be used in the strategy. Defaults to None.
        Raises:
            KeyError: if there is a model spec for an unknown output feature
            KeyError: if a model spec has an unknown input feature
        Returns:
            List[ModelSpec]: List of model specification classes
        """
        existing_keys = (
            surrogate_specs.output_features.get_keys()
            if surrogate_specs is not None
            else []
        )
        non_exisiting_keys = list(set(domain.outputs.get_keys()) - set(existing_keys))
        _surrogate_specs = (
            surrogate_specs.surrogates if surrogate_specs is not None else []
        )
        for output_feature in non_exisiting_keys:
            if len(domain.inputs.get(CategoricalInput, exact=True)):
                _surrogate_specs.append(
                    MixedSingleTaskGPSurrogate(
                        input_features=domain.inputs,
                        output_features=Outputs(features=[domain.outputs.get_by_key(output_feature)]),  # type: ignore
                    )
                )
            else:
                _surrogate_specs.append(
                    SingleTaskGPSurrogate(
                        input_features=domain.inputs,
                        output_features=Outputs(features=[domain.outputs.get_by_key(output_feature)]),  # type: ignore
                    )
                )
        surrogate_specs = BotorchSurrogates(surrogates=_surrogate_specs)
        surrogate_specs._check_compability(
            input_features=domain.inputs, output_features=domain.outputs
        )
        return surrogate_specs