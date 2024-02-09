from bofire.data_models.features.api import (
    AnyOutput,
    CategoricalOutput,
    ContinuousOutput,
)


def get_column_names(outputs: AnyOutput):
    pred_cols, sd_cols = [], []
    for featkey in outputs.get_keys(CategoricalOutput):
        pred_cols = pred_cols + [
            f"{featkey}_{cat}_prob"
            for cat in outputs.get_by_key(featkey).categories  # type: ignore
        ]
        sd_cols = sd_cols + [
            f"{featkey}_{cat}_sd"
            for cat in outputs.get_by_key(featkey).categories  # type: ignore
        ]
    for featkey in outputs.get_keys(ContinuousOutput):
        pred_cols = pred_cols + [f"{featkey}_pred"]
        sd_cols = sd_cols + [f"{featkey}_sd"]

    return pred_cols, sd_cols
