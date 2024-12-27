import math
from typing import Annotated, ClassVar, List, Literal, Optional, Tuple

import numpy as np
import pandas as pd
from pydantic import Field, model_validator

from bofire.data_models.features.feature import Output, TTransform
from bofire.data_models.features.numerical import NumericalInput
from bofire.data_models.objectives.api import AnyObjective, MaximizeObjective
from bofire.data_models.types import Bounds


class ContinuousInput(NumericalInput):
    """Base class for all continuous input features.

    Attributes:
        bounds (Tuple[float, float]): A tuple that stores the lower and upper
            bound of the feature.
        stepsize (float, optional): Float indicating the allowed stepsize between
            lower and upper. Defaults to None.
        local_relative_bounds (Tuple[float, float], optional): A tuple that stores
            the lower and upper bounds relative to a reference value.
            Defaults to None.
    """

    type: Literal["ContinuousInput"] = "ContinuousInput"  # type: ignore
    order_id: ClassVar[int] = 1

    bounds: Bounds
    local_relative_bounds: Optional[
        Tuple[Annotated[float, Field(gt=0)], Annotated[float, Field(gt=0)]]
    ] = None
    stepsize: Optional[float] = None

    @property
    def lower_bound(self) -> float:
        """Returns the lower bound of the feature."""
        return self.bounds[0]

    def local_lower_bound(self, reference_value) -> float:
        """Returns the lower bound of the feature relative to a reference value."""
        local_relative_bounds = self.local_relative_bounds or (math.inf, math.inf)
        return max(
            reference_value - local_relative_bounds[0],
            self.lower_bound,
        )

    @property
    def upper_bound(self) -> float:
        """Returns the upper bound of the feature."""
        return self.bounds[1]

    def local_upper_bound(self, reference_value) -> float:
        """Returns the upper bound of the feature relative to a reference value."""
        local_relative_bounds = self.local_relative_bounds or (math.inf, math.inf)
        return min(
            reference_value + local_relative_bounds[1],
            self.upper_bound,
        )

    @model_validator(mode="after")
    def validate_step_size(self):
        if self.stepsize is None:
            return self
        lower, upper = self.bounds
        if lower == upper and self.stepsize is not None:
            raise ValueError(
                "Stepsize cannot be provided for a fixed continuous input.",
            )
        range = upper - lower
        if np.arange(lower, upper + self.stepsize, self.stepsize)[-1] != upper:
            raise ValueError(
                f"Stepsize of {self.stepsize} does not match the provided interval [{lower},{upper}].",
            )
        if range // self.stepsize == 1:
            raise ValueError("Stepsize is too big, only one value allowed.")
        return self

    def round(self, values: pd.Series) -> pd.Series:
        """Round values to the stepsize of the feature. If no stepsize is provided return the
        provided values.

        Args:
            values (pd.Series): The values that should be rounded.

        Returns:
            pd.Series: The rounded values
        """
        if self.stepsize is None:
            return values
        self.validate_candidental(values=values)
        allowed_values = np.arange(
            self.lower_bound,
            self.upper_bound + self.stepsize,
            self.stepsize,
        )
        idx = abs(values.values.reshape([len(values), 1]) - allowed_values).argmin(  # type: ignore
            axis=1,
        )
        return pd.Series(
            data=self.lower_bound + idx * self.stepsize,
            index=values.index,
        )

    def validate_candidental(self, values: pd.Series) -> pd.Series:
        """Method to validate the suggested candidates

        Args:
            values (pd.Series): A dataFrame with candidates

        Raises:
            ValueError: when non numerical values are passed
            ValueError: when values are larger than the upper bound of the feature
            ValueError: when values are lower than the lower bound of the feature

        Returns:
            pd.Series: The passed dataFrame with candidates

        """
        noise = 10e-6
        values = super().validate_candidental(values)
        if (values < self.lower_bound - noise).any():
            raise ValueError(
                f"not all values of input feature `{self.key}`are larger than lower bound `{self.lower_bound}` ",
            )
        if (values > self.upper_bound + noise).any():
            raise ValueError(
                f"not all values of input feature `{self.key}`are smaller than upper bound `{self.upper_bound}` ",
            )
        return values

    def sample(self, n: int, seed: Optional[int] = None) -> pd.Series:
        """Draw random samples from the feature.

        Args:
            n (int): number of samples.
            seed (int, optional): random seed. Defaults to None.

        Returns:
            pd.Series: drawn samples.

        """
        return pd.Series(
            name=self.key,
            data=np.random.default_rng(seed=seed).uniform(
                self.lower_bound,
                self.upper_bound,
                n,
            ),
        )

    def get_bounds(  # type: ignore
        self,
        transform_type: Optional[TTransform] = None,
        values: Optional[pd.Series] = None,
        reference_value: Optional[float] = None,
    ) -> Tuple[List[float], List[float]]:
        assert transform_type is None
        if reference_value is not None and values is not None:
            raise ValueError("Only one can be used, `local_value` or `values`.")

        if values is None:
            if reference_value is None or self.is_fixed():
                return [self.lower_bound], [self.upper_bound]
            else:
                return (
                    [self.local_lower_bound(reference_value)],
                    [self.local_upper_bound(reference_value)],
                )
        lower = min(self.lower_bound, values.min())
        upper = max(self.upper_bound, values.max())
        return [lower], [upper]

    def __str__(self) -> str:
        """Method to return a string of lower and upper bound

        Returns:
            str: String of a list with lower and upper bound

        """
        return f"[{self.lower_bound},{self.upper_bound}]"


class ContinuousOutput(Output):
    """The base class for a continuous output feature

    Attributes:
        objective (objective, optional): objective of the feature indicating in
        which direction it should be optimized. Defaults to `MaximizeObjective`.
    """

    type: Literal["ContinuousOutput"] = "ContinuousOutput"  # type: ignore
    order_id: ClassVar[int] = 9
    unit: Optional[str] = None

    objective: Optional[AnyObjective] = Field(
        default_factory=lambda: MaximizeObjective(w=1.0),
    )

    def __call__(self, values: pd.Series, values_adapt: pd.Series) -> pd.Series:  # type: ignore
        if self.objective is None:
            return pd.Series(
                data=[np.nan for _ in range(len(values))],
                index=values.index,
                name=values.name,
            )
        return self.objective(values, values_adapt)  # type: ignore

    def validate_experimental(self, values: pd.Series) -> pd.Series:
        try:
            values = pd.to_numeric(values, errors="raise").astype("float64")
        except ValueError:
            raise ValueError(
                f"not all values of input feature `{self.key}` are numerical",
            )
        return values

    def __str__(self) -> str:
        return "ContinuousOutputFeature"
