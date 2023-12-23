from typing import Literal

from pydantic import Field, field_validator
from typing_extensions import Annotated

from bofire.data_models.surrogates.trainable_botorch import TrainableBotorchSurrogate


class SaasSingleTaskGPSurrogate(TrainableBotorchSurrogate):
    type: Literal["SaasSingleTaskGPSurrogate"] = "SaasSingleTaskGPSurrogate"
    warmup_steps: Annotated[int, Field(ge=1)] = 256  # type: ignore
    num_samples: Annotated[int, Field(ge=1)] = 128  # type: ignore
    thinning: Annotated[int, Field(ge=1)] = 16  # type: ignore

    @field_validator("thinning")
    @classmethod
    def validate_thinning(cls, value, values):
        if values["num_samples"] / value < 1:
            raise ValueError("`num_samples` has to be larger than `thinning`.")
        return value
