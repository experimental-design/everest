from abc import ABC, abstractmethod
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from bofire.data_models.domain.domain import is_numeric
from bofire.data_models.surrogates.api import Surrogate as DataModel
from bofire.surrogates.values import PredictedValue

# from bofire.models.diagnostics import CvResult, CvResults


class Surrogate(ABC):
    def __init__(
        self,
        data_model: DataModel,
    ):
        self.input_features = data_model.input_features
        self.output_features = data_model.output_features
        self.input_preprocessing_specs = data_model.input_preprocessing_specs
        self.model = None

    @classmethod
    def from_spec(cls, data_model: DataModel) -> "Surrogate":
        return cls(data_model=data_model)

    @property
    def is_fitted(self) -> bool:
        """Return True if model is fitted, else False."""
        return self.model is not None

    def predict(self, X: pd.DataFrame) -> pd.DataFrame:
        # check if model is fitted
        if not self.is_fitted:
            raise ValueError(
                "Model is not fitted yet. Call 'fit' with appropriate arguments before using this model."
            )
        # validate
        X = self.input_features.validate_experiments(X, strict=False)
        # transform
        Xt = self.input_features.transform(X, self.input_preprocessing_specs)
        # predict
        preds, stds = self._predict(Xt)
        # postprocess
        predictions = pd.DataFrame(
            data=np.hstack((preds, stds)),
            columns=["%s_pred" % featkey for featkey in self.output_features.get_keys()]
            + ["%s_sd" % featkey for featkey in self.output_features.get_keys()],
        )
        # validate
        self.validate_predictions(predictions=predictions)
        # return
        return predictions

    def validate_predictions(self, predictions: pd.DataFrame) -> pd.DataFrame:
        expected_cols = [
            f"{key}_{t}"
            for key in self.output_features.get_keys()
            for t in ["pred", "sd"]
        ]
        if sorted(list(predictions.columns)) != sorted(expected_cols):
            raise ValueError(
                f"Predictions are ill-formatted. Expected: {expected_cols}, got: {list(predictions.columns)}."
            )
        # check that values are numeric
        if not is_numeric(predictions):
            raise ValueError("Not all values in predictions are numeric.")
        return predictions

    def to_predictions(
        self, predictions: pd.DataFrame
    ) -> Dict[str, List[PredictedValue]]:
        outputs = {key: [] for key in self.output_features.get_keys()}
        for _, row in predictions.iterrows():
            for key in self.output_features.get_keys():
                outputs[key].append(
                    PredictedValue(
                        predictedValue=row[f"{key}_pred"],
                        standardDeviation=row[f"{key}_sd"],
                    )
                )
        return outputs

    @abstractmethod
    def _predict(self, transformed_X: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        pass

    def dumps(self) -> str:
        """Dumps the actual model to a string as this is not directly json serializable."""
        if not self.is_fitted:
            raise ValueError("Model has to be fitted before dumping")
        self._prepare_for_dump()
        return self._dumps()

    @abstractmethod
    def _dumps() -> str:
        pass

    def _prepare_for_dump(self):
        """Prepares the model before the dump."""
        pass

    @abstractmethod
    def loads(self, data: str):
        """Loads the actual model from a string and writes it to the `model` attribute."""
        pass
