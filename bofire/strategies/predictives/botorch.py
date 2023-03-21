import copy
from abc import abstractmethod
from typing import Callable, Dict, Optional, Tuple

import numpy as np
import pandas as pd
import torch
from botorch.acquisition.acquisition import AcquisitionFunction
from botorch.acquisition.utils import get_infeasible_cost
from botorch.models.gpytorch import GPyTorchModel
from botorch.optim.optimize import optimize_acqf, optimize_acqf_mixed
from pydantic.types import NonNegativeInt
from torch import Tensor

from bofire.data_models.constraints.api import (
    LinearEqualityConstraint,
    LinearInequalityConstraint,
    NChooseKConstraint,
)
from bofire.data_models.enum import CategoricalEncodingEnum, CategoricalMethodEnum
from bofire.data_models.features.api import (
    CategoricalDescriptorInput,
    CategoricalInput,
    DiscreteInput,
    Input,
    TInputTransformSpecs,
)
from bofire.data_models.strategies.api import BotorchStrategy as DataModel
from bofire.data_models.strategies.api import (
    PolytopeSampler as PolytopeSamplerDataModel,
)
from bofire.strategies.predictives.predictive import PredictiveStrategy
from bofire.strategies.samplers.polytope import PolytopeSampler
from bofire.surrogates.botorch_surrogates import BotorchSurrogates
from bofire.utils.torch_tools import get_linear_constraints, tkwargs


def is_power_of_two(n):
    return (n != 0) and (n & (n - 1) == 0)


class BotorchStrategy(PredictiveStrategy):
    def __init__(
        self,
        data_model: DataModel,
        **kwargs,
    ):
        super().__init__(data_model=data_model, **kwargs)
        self.num_sobol_samples = data_model.num_sobol_samples
        self.num_restarts = data_model.num_restarts
        self.num_raw_samples = data_model.num_raw_samples
        self.descriptor_method = data_model.descriptor_method
        self.categorical_method = data_model.categorical_method
        self.discrete_method = data_model.discrete_method
        self.surrogate_specs = BotorchSurrogates(data_model=data_model.surrogate_specs)  # type: ignore
        torch.manual_seed(self.seed)

    acqf: Optional[AcquisitionFunction] = None
    model: Optional[GPyTorchModel] = None

    @property
    def input_preprocessing_specs(self) -> TInputTransformSpecs:
        return self.surrogate_specs.input_preprocessing_specs  # type: ignore

    @property
    def _features2idx(self) -> Dict[str, Tuple[int]]:
        features2idx, _ = self.domain.inputs._get_transform_info(
            self.input_preprocessing_specs
        )
        return features2idx

    @property
    def _features2names(self) -> Dict[str, Tuple[str]]:
        _, features2names = self.domain.inputs._get_transform_info(
            self.input_preprocessing_specs
        )
        return features2names

    def _fit(self, experiments: pd.DataFrame):
        """[summary]

        Args:
            transformed (pd.DataFrame): [description]
        """
        self.surrogate_specs.fit(experiments)  # type: ignore
        self.model = self.surrogate_specs.compatibilize(  # type: ignore
            input_features=self.domain.input_features,  # type: ignore
            output_features=self.domain.output_features,  # type: ignore
        )

    def _predict(self, transformed: pd.DataFrame):
        # we are using self.model here for this purpose we have to take the transformed
        # input and further transform it to a torch tensor
        X = torch.from_numpy(transformed.values).to(**tkwargs)
        with torch.no_grad():
            preds = self.model.posterior(X=X).mean.cpu().detach().numpy()  # type: ignore
            # TODO: add a option to return the real uncertainty including the data uncertainty
            stds = np.sqrt(self.model.posterior(X=X).variance.cpu().detach().numpy())  # type: ignore
        return preds, stds

    # TODO: test this
    def calc_acquisition(
        self, candidates: pd.DataFrame, combined: bool = False
    ) -> np.ndarray:
        """Calculate the acqusition value for a set of experiments.

        Args:
            candidates (pd.DataFrame): Dataframe with experimentes for which the acqf value should be calculated.
            combined (bool, optional): If combined an acquisition value for the whole batch is calculated, else individual ones.
                Defaults to False.

        Returns:
            np.ndarray: Dataframe with the acquisition values.
        """
        transformed = self.domain.inputs.transform(
            candidates, self.input_preprocessing_specs
        )
        X = torch.from_numpy(transformed.values).to(**tkwargs)
        if combined is False:
            X = X.unsqueeze(-2)
        return self.acqf.forward(X).cpu().detach().numpy()  # type: ignore

    # TODO: test this
    def _choose_from_pool(
        self,
        candidate_pool: pd.DataFrame,
        candidate_count: Optional[NonNegativeInt] = None,
    ) -> pd.DataFrame:
        """Method to choose a set of candidates from a candidate pool.

        Args:
            candidate_pool (pd.DataFrame): The pool of candidates from which the candidates should be chosen.
            candidate_count (Optional[NonNegativeInt], optional): Number of candidates to choose. Defaults to None.

        Returns:
            pd.DataFrame: The chosen set of candidates.
        """

        acqf_values = self.calc_acquisition(candidate_pool)

        return candidate_pool.iloc[
            np.argpartition(acqf_values, -1 * candidate_count)[-candidate_count:]  # type: ignore
        ]

    def _ask(self, candidate_count: int) -> pd.DataFrame:
        """[summary]

        Args:
            candidate_count (int, optional): [description]. Defaults to 1.

        Returns:
            pd.DataFrame: [description]
        """

        assert candidate_count > 0, "candidate_count has to be larger than zero."

        # optimize
        # we have to distuinguish the following scenarios
        # - no categoricals - check
        # - categoricals with one hot and free variables
        # - categoricals with one hot and exhaustive screening, could be in combination with garrido merchan - check
        # - categoricals with one hot and OEN, could be in combination with garrido merchan - OEN not implemented
        # - descriptized categoricals not yet implemented
        num_categorical_features = len(
            self.domain.get_features([CategoricalInput, DiscreteInput])
        )
        num_categorical_combinations = len(
            self.domain.inputs.get_categorical_combinations()
        )
        assert self.acqf is not None

        lower, upper = self.domain.inputs.get_bounds(
            specs=self.input_preprocessing_specs
        )
        bounds = torch.tensor([lower, upper]).to(**tkwargs)

        if (
            (num_categorical_features == 0)
            or (num_categorical_combinations == 1)
            or (
                all(
                    enc == CategoricalMethodEnum.FREE
                    for enc in [
                        self.categorical_method,
                        self.descriptor_method,
                        self.discrete_method,
                    ]
                )
            )
        ) and len(self.domain.cnstrs.get(NChooseKConstraint)) == 0:
            candidates = optimize_acqf(
                acq_function=self.acqf,
                bounds=bounds,
                q=candidate_count,
                num_restarts=self.num_restarts,
                raw_samples=self.num_raw_samples,
                equality_constraints=get_linear_constraints(
                    domain=self.domain, constraint=LinearEqualityConstraint  # type: ignore
                ),
                inequality_constraints=get_linear_constraints(
                    domain=self.domain, constraint=LinearInequalityConstraint  # type: ignore
                ),
                fixed_features=self.get_fixed_features(),
                return_best_only=True,
            )

        elif (
            CategoricalMethodEnum.EXHAUSTIVE
            in [self.categorical_method, self.descriptor_method, self.discrete_method]
        ) and len(self.domain.cnstrs.get(NChooseKConstraint)) == 0:
            candidates = optimize_acqf_mixed(
                acq_function=self.acqf,
                bounds=bounds,
                q=candidate_count,
                num_restarts=self.num_restarts,
                raw_samples=self.num_raw_samples,
                equality_constraints=get_linear_constraints(
                    domain=self.domain, constraint=LinearEqualityConstraint  # type: ignore
                ),
                inequality_constraints=get_linear_constraints(
                    domain=self.domain, constraint=LinearInequalityConstraint  # type: ignore
                ),
                fixed_features_list=self.get_categorical_combinations(),
            )

        elif len(self.domain.cnstrs.get(NChooseKConstraint)) > 0:
            candidates = optimize_acqf_mixed(
                acq_function=self.acqf,
                bounds=bounds,
                q=candidate_count,
                num_restarts=self.num_restarts,
                raw_samples=self.num_raw_samples,
                equality_constraints=get_linear_constraints(
                    domain=self.domain, constraint=LinearEqualityConstraint  # type: ignore
                ),
                inequality_constraints=get_linear_constraints(
                    domain=self.domain, constraint=LinearInequalityConstraint  # type: ignore
                ),
                fixed_features_list=self.get_fixed_values_list(),
            )

        else:
            raise IOError()

        # postprocess the results
        # TODO: in case of free we have to transform back the candidates first and then compute the metrics
        # otherwise the prediction holds only for the infeasible solution, this solution should then also be
        # applicable for >1d descriptors
        preds = self.model.posterior(X=candidates[0]).mean.detach().numpy()  # type: ignore
        stds = np.sqrt(self.model.posterior(X=candidates[0]).variance.detach().numpy())  # type: ignore

        input_feature_keys = [
            item
            for key in self.domain.inputs.get_keys()
            for item in self._features2names[key]
        ]

        df_candidates = pd.DataFrame(
            data=candidates[0].detach().numpy(), columns=input_feature_keys
        )

        df_candidates = self.domain.inputs.inverse_transform(
            df_candidates, self.input_preprocessing_specs
        )

        for i, feat in enumerate(self.domain.outputs.get_by_objective(excludes=None)):
            df_candidates[feat.key + "_pred"] = preds[:, i]
            df_candidates[feat.key + "_sd"] = stds[:, i]
            df_candidates[feat.key + "_des"] = feat.objective(preds[:, i])  # type: ignore

        return df_candidates

    def _tell(self) -> None:
        self.init_acqf()

    def init_acqf(self) -> None:
        self._init_acqf()
        return

    @abstractmethod
    def _init_acqf(
        self,
    ) -> None:
        pass

    def get_fixed_features(self):
        """provides the values of all fixed features

        Raises:
            NotImplementedError: [description]

        Returns:
            fixed_features (dict): Dictionary of fixed features, keys are the feature indices, values the transformed feature values
        """
        fixed_features = {}
        features2idx = self._features2idx

        for _, feat in enumerate(self.domain.get_features(Input)):
            if feat.fixed_value() is not None:  # type: ignore
                fixed_values = feat.fixed_value(transform_type=self.input_preprocessing_specs.get(feat.key))  # type: ignore
                for j, idx in enumerate(features2idx[feat.key]):
                    fixed_features[idx] = fixed_values[j]  # type: ignore

        # in case the optimization method is free and not allowed categories are present
        # one has to fix also them, this is abit of double work as it should be also reflected
        # in the bounds but helps to make it safer

        if (
            self.categorical_method == CategoricalMethodEnum.FREE
            and CategoricalEncodingEnum.ONE_HOT
            in list(self.input_preprocessing_specs.values())
        ):
            # for feat in self.get_true_categorical_features():
            for feat in [
                self.domain.inputs.get_by_key(featkey)
                for featkey in self.domain.inputs.get_keys(CategoricalInput)
                if self.input_preprocessing_specs[featkey]
                == CategoricalEncodingEnum.ONE_HOT
            ]:
                assert isinstance(feat, CategoricalInput)
                if feat.is_fixed() is False:
                    for cat in feat.get_forbidden_categories():
                        transformed = feat.to_onehot_encoding(pd.Series([cat]))
                        # we fix those indices to zero where one has a 1 as response from the transformer
                        for j, idx in enumerate(features2idx[feat.key]):
                            if transformed.values[0, j] == 1.0:
                                fixed_features[idx] = 0
        # for the descriptor ones
        if (
            self.descriptor_method == CategoricalMethodEnum.FREE
            and CategoricalEncodingEnum.DESCRIPTOR
            in list(self.input_preprocessing_specs.values())
        ):
            # for feat in self.get_true_categorical_features():
            for feat in [
                self.domain.inputs.get_by_key(featkey)
                for featkey in self.domain.inputs.get_keys(CategoricalDescriptorInput)
                if self.input_preprocessing_specs[featkey]
                == CategoricalEncodingEnum.DESCRIPTOR
            ]:
                assert isinstance(feat, CategoricalDescriptorInput)
                if feat.is_fixed() is False:
                    lower, upper = feat.get_bounds(CategoricalEncodingEnum.DESCRIPTOR)
                    for j, idx in enumerate(features2idx[feat.key]):
                        if lower[j] == upper[j]:
                            fixed_features[idx] = lower[j]
        return fixed_features

    def get_categorical_combinations(self):
        """provides all possible combinations of fixed values

        Returns:
            list_of_fixed_features List[dict]: Each dict contains a combination of fixed values
        """
        fixed_basis = self.get_fixed_features()

        methods = [
            self.descriptor_method,
            self.discrete_method,
            self.categorical_method,
        ]

        if all(m == CategoricalMethodEnum.FREE for m in methods):
            return [{}]
        else:
            include = []
            exclude = None

            if self.discrete_method == CategoricalMethodEnum.EXHAUSTIVE:
                include.append(DiscreteInput)

            if self.categorical_method == CategoricalMethodEnum.EXHAUSTIVE:
                include.append(CategoricalInput)
                exclude = CategoricalDescriptorInput

            if self.descriptor_method == CategoricalMethodEnum.EXHAUSTIVE:
                include.append(CategoricalDescriptorInput)
                exclude = None

        if not include:
            include = None

        combos = self.domain.inputs.get_categorical_combinations(
            include=(include if include else Input), exclude=exclude
        )
        # now build up the fixed feature list
        if len(combos) == 1:
            return [fixed_basis]
        else:
            features2idx = self._features2idx
            list_of_fixed_features = []

            for combo in combos:
                fixed_features = copy.deepcopy(fixed_basis)

                for pair in combo:
                    feat, val = pair
                    feature = self.domain.get_feature(feat)
                    if (
                        isinstance(feature, CategoricalDescriptorInput)
                        and self.input_preprocessing_specs[feat]
                        == CategoricalEncodingEnum.DESCRIPTOR
                    ):
                        index = feature.categories.index(val)

                        for j, idx in enumerate(features2idx[feat]):
                            fixed_features[idx] = feature.values[index][j]

                    elif isinstance(feature, CategoricalInput):
                        # it has to be onehot in this case
                        transformed = feature.to_onehot_encoding(pd.Series([val]))
                        for j, idx in enumerate(features2idx[feat]):
                            fixed_features[idx] = transformed.values[0, j]

                    elif isinstance(feature, DiscreteInput):
                        fixed_features[features2idx[feat][0]] = val

                list_of_fixed_features.append(fixed_features)
        return list_of_fixed_features

    def get_nchoosek_combinations(self):
        """
        generate a list of fixed values dictionaries from n-choose-k constraints
        """

        # generate botorch-friendly fixed values
        features2idx = self._features2idx
        used_features, unused_features = self.domain.get_nchoosek_combinations(
            exhaustive=True
        )
        fixed_values_list_cc = []
        for used, unused in zip(used_features, unused_features):
            fixed_values = {}

            # sets unused features to zero
            for f_key in unused:
                fixed_values[features2idx[f_key][0]] = 0.0

            fixed_values_list_cc.append(fixed_values)

        if len(fixed_values_list_cc) == 0:
            fixed_values_list_cc.append({})  # any better alternative here?

        return fixed_values_list_cc

    def get_fixed_values_list(self):
        # CARTESIAN PRODUCTS: fixed values from categorical combinations X fixed values from nchoosek constraints
        fixed_values_full = []

        for ff1 in self.get_categorical_combinations():
            for ff2 in self.get_nchoosek_combinations():
                ff = ff1.copy()
                ff.update(ff2)
                fixed_values_full.append(ff)

        return fixed_values_full

    def has_sufficient_experiments(
        self,
    ) -> bool:
        if self.experiments is None:
            return False
        degrees_of_freedom = len(self.domain.get_features(Input)) - len(
            self.get_fixed_features()
        )
        # degrees_of_freedom = len(self.domain.get_features(Input)) + 1
        if self.experiments.shape[0] > degrees_of_freedom + 1:
            return True
        return False

    def get_acqf_input_tensors(self):
        experiments = self.domain.outputs.preprocess_experiments_all_valid_outputs(
            self.experiments
        )

        # TODO: should this be selectable?
        clean_experiments = experiments.drop_duplicates(
            subset=[var.key for var in self.domain.get_features(Input)],
            keep="first",
            inplace=False,
        )

        transformed = self.domain.inputs.transform(
            clean_experiments, self.input_preprocessing_specs
        )
        X_train = torch.from_numpy(transformed.values).to(**tkwargs)

        if self.candidates is not None:
            transformed_candidates = self.domain.inputs.transform(
                self.candidates, self.input_preprocessing_specs
            )
            X_pending = torch.from_numpy(transformed_candidates.values).to(**tkwargs)
        else:
            X_pending = None

        return X_train, X_pending

    def get_infeasible_cost(
        self, objective: Callable[[Tensor, Tensor], Tensor], n_samples=128
    ) -> Tensor:
        X_train, X_pending = self.get_acqf_input_tensors()
        sampler = PolytopeSampler(
            data_model=PolytopeSamplerDataModel(domain=self.domain)
        )
        samples = torch.from_numpy(
            sampler.ask(n=n_samples, return_all=False).values
        ).to(**tkwargs)
        X = (
            torch.cat((X_train, X_pending, samples))
            if X_pending is not None
            else torch.cat((X_train, samples))
        )
        return get_infeasible_cost(
            X=X, model=self.model, objective=objective  # type: ignore
        )