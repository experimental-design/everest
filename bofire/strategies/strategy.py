from abc import ABC, abstractmethod
from typing import List, Optional

import numpy as np
import pandas as pd
from pydantic import PositiveInt

from bofire.data_models.strategies.api import Strategy as DataModel
from bofire.strategies.data_models.candidate import Candidate
from bofire.strategies.data_models.values import InputValue


class Strategy(ABC):
    """Base class for all strategies

    Attributes:
    """

    def __init__(
        self,
        data_model: DataModel,
    ):
        self.domain = data_model.domain
        self.seed = data_model.seed
        self.rng = np.random.default_rng(self.seed)
        self._experiments = None
        self._candidates = None

    @classmethod
    def from_spec(cls, data_model: DataModel) -> "Strategy":
        """Used by the mapper to map from data model to functional strategy."""
        return cls(data_model=data_model)

    @property
    def experiments(self) -> pd.DataFrame:
        """Returns the experiments of the strategy.

        Returns:
            pd.DataFrame: Current experiments.
        """
        return self._experiments  # type: ignore

    @property
    def candidates(self) -> pd.DataFrame:
        """Returns the (pending) candidates of the strategy.

        Returns:
            pd.DataFrame: Pending experiments.
        """
        return self._candidates  # type: ignore

    def tell(
        self,
        experiments: pd.DataFrame,
        replace: bool = False,
    ) -> None:
        """This function passes new experimental data to the optimizer

        Args:
            experiments (pd.DataFrame): DataFrame with experimental data
            replace (bool, optional): Boolean to decide if the experimental data should replace the former DataFrame or if the new experiments should be attached. Defaults to False.
        """
        if len(experiments) == 0:
            return
        if replace:
            self.set_experiments(experiments=experiments)
        else:
            self.add_experiments(experiments=experiments)
        self._tell()

    def _tell(self) -> None:
        """Method to allow for customized tell functions in addition to self.tell()"""
        pass

    def ask(
        self,
        candidate_count: Optional[PositiveInt] = None,
        add_pending: bool = False,
        candidate_pool: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """Function to generate new candidates.

        Args:
            candidate_count (PositiveInt, optional): Number of candidates to be generated. If not provided, the number
                of candidates is determined automatically. Defaults to None.
            add_pending (bool, optional): If true the proposed candidates are added to the set of pending experiments. Defaults to False.
            candidate_pool (pd.DataFrame, optional): Pool of candidates from which a final set of candidates should be chosen. If not provided,
                pool independent candidates are provided. Defaults to None.

        Raises:
            ValueError: if candidate count is smaller than 1
            ValueError: if not enough experiments are available to execute the strategy
            ValueError: if the number of generated candidates does not match the requested number

        Returns:
            pd.DataFrame: DataFrame with candidates (proposed experiments)
        """
        if candidate_count is not None and candidate_count < 1:
            raise ValueError(
                f"Candidate_count has to be at least 1 but got {candidate_count}."
            )
        if not self.has_sufficient_experiments():
            raise ValueError(
                "Not enough experiments available to execute the strategy."
            )

        if candidate_pool is None:
            candidates = self._ask(candidate_count=candidate_count)
        else:
            self.domain.validate_candidates(candidate_pool, only_inputs=True)
            if candidate_count is not None:
                assert candidate_count <= len(
                    candidate_pool
                ), "Number of requested candidates is larger than the pool from which they should be chosen."
            candidates = self._choose_from_pool(candidate_pool, candidate_count)

        self.domain.validate_candidates(candidates=candidates, only_inputs=True)

        if candidate_count is not None:
            if len(candidates) != candidate_count:
                raise ValueError(
                    f"expected {candidate_count} candidates, got {len(candidates)}"
                )

        if add_pending:
            self.add_candidates(candidates)

        return candidates

    def _choose_from_pool(
        self,
        candidate_pool: pd.DataFrame,
        candidate_count: Optional[PositiveInt] = None,
    ) -> pd.DataFrame:
        """Abstract method to implement how a strategy chooses a set of candidates from a candidate pool.

        Args:
            candidate_pool (pd.DataFrame): The pool of candidates from which the candidates should be chosen.
            candidate_count (Optional[PositiveInt], optional): Number of candidates to choose. Defaults to None.

        Returns:
            pd.DataFrame: The chosen set of candidates.
        """
        # TODO: change inheritence hierarchy to make this an optional feature of a strategy provided by inheritence
        raise NotImplementedError

    @abstractmethod
    def has_sufficient_experiments(
        self,
    ) -> bool:
        """Abstract method to check if sufficient experiments are available.

        Returns:
            bool: True if number of passed experiments is sufficient, False otherwise
        """
        pass

    @abstractmethod
    def _ask(
        self,
        candidate_count: Optional[PositiveInt] = None,
    ) -> pd.DataFrame:
        """Abstract method to implement how a strategy generates candidates.

        Args:
            candidate_count (PositiveInt, optional): Number of candidates to be generated. Defaults to None.

        Returns:
            pd.DataFrame: DataFrame with candidates (proposed experiments).
        """
        pass

    def to_candidates(self, candidates: pd.DataFrame) -> List[Candidate]:
        """Transform candiadtes dataframe to a list of `Candidate` objects.
        Args:
            candidates (pd.DataFrame): candidates formatted as dataframe
        Returns:
            List[Candidate]: candidates formatted as list of `Candidate` objects.
        """
        return [
            Candidate(
                inputValues={
                    key: InputValue(value=row[key])
                    for key in self.domain.inputs.get_keys()
                },
            )
            for _, row in candidates.iterrows()
        ]

    def set_candidates(self, candidates: pd.DataFrame):
        """Set candidates of the strategy. Overwrites existing ones.

        Args:
            experiments (pd.DataFrame): Dataframe with candidates.
        """
        candidates = self.domain.validate_candidates(candidates)
        self._candidates = candidates

    def add_candidates(self, candidates: pd.DataFrame):
        """Add candidates to the strategy. Appends to existing ones.

        Args:
            experiments (pd.DataFrame): Dataframe with candidates.
        """
        candidates = self.domain.validate_candidates(candidates)
        if self.candidates is None:
            self._candidates = candidates
        else:
            self._candidates = pd.concat(
                (self.candidates, candidates), ignore_index=True
            )

    @property
    def num_candidates(self) -> int:
        """Returns number of (pending) candidates"""
        if self.candidates is None:
            return 0
        return len(self.candidates)

    def set_experiments(self, experiments: pd.DataFrame):
        """Set experiments of the strategy. Overwrites existing ones.

        Args:
            experiments (pd.DataFrame): Dataframe with experiments.
        """
        experiments = self.domain.validate_experiments(experiments)
        self._experiments = experiments

    def add_experiments(self, experiments: pd.DataFrame):
        """Add experiments to the strategy. Appends to existing ones.

        Args:
            experiments (pd.DataFrame): Dataframe with experiments.
        """
        experiments = self.domain.validate_experiments(experiments)
        if self.experiments is None:
            self._experiments = experiments
        else:
            self._experiments = pd.concat(
                (self.experiments, experiments), ignore_index=True
            )

    @property
    def num_experiments(self) -> int:
        """Returns number of experiments"""
        if self.experiments is None:
            return 0
        return len(self.experiments)
