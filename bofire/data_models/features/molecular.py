import warnings
from typing import ClassVar, List, Literal, Optional, Sequence, Tuple, Union

import pandas as pd
from pydantic import validator

from bofire.data_models.enum import CategoricalEncodingEnum
from bofire.data_models.features.categorical import _CAT_SEP, CategoricalInput
from bofire.data_models.features.feature import Input
from bofire.data_models.molfeatures.api import (
    AnyMolFeatures,
    Fingerprints,
    FingerprintsFragments,
    Fragments,
    MordredDescriptors,
)
from bofire.utils.cheminformatics import smiles2mol


class MolecularInput(Input):
    type: Literal["MolecularInput"] = "MolecularInput"
    order: ClassVar[int] = 6

    @staticmethod
    def valid_transform_types() -> List[AnyMolFeatures]:
        return [Fingerprints, FingerprintsFragments, Fragments, MordredDescriptors]

    def validate_experimental(
        self, values: pd.Series, strict: bool = False
    ) -> pd.Series:
        for smi in values:
            smiles2mol(smi)

        return values

    def validate_candidental(self, values: pd.Series) -> pd.Series:
        for smi in values:
            smiles2mol(smi)
        return values

    def is_fixed(self) -> bool:
        return False

    def fixed_value(self, transform_type: Optional[AnyMolFeatures] = None) -> None:
        return None

    def sample(self, n: int) -> pd.Series:
        raise ValueError("Sampling not supported for `MolecularInput`")

    def get_bounds(
        self, transform_type: AnyMolFeatures, values: pd.Series
    ) -> Tuple[List[float], List[float]]:
        if values is None:
            raise NotImplementedError(
                "`values` is currently required for `MolecularInput`"
            )
        else:
            data = self.to_descriptor_encoding(transform_type, values)

        lower = data.min(axis=0).values.tolist()
        upper = data.max(axis=0).values.tolist()

        return lower, upper

    def to_descriptor_encoding(
        self, transform_type: AnyMolFeatures, values: pd.Series
    ) -> pd.DataFrame:
        """Converts values to descriptor encoding.

        Args:
            values (pd.Series): Values to transform.

        Returns:
            pd.DataFrame: Descriptor encoded dataframe.
        """
        descriptor_values = transform_type.get_descriptor_values(values)

        descriptor_values.columns = [
            f"{self.key}{_CAT_SEP}{d}" for d in transform_type.get_descriptor_names()
        ]
        descriptor_values.index = values.index

        return descriptor_values


class CategoricalMolecularInput(CategoricalInput, MolecularInput):
    type: Literal["CategoricalMolecularInput"] = "CategoricalMolecularInput"
    order: ClassVar[int] = 7

    @validator("categories")
    def validate_categories_unique(cls, categories: Sequence[str]):
        """validates that categories are valid smiles. Note that this check can only
        be executed when rdkit is available.

        Args:
            categories (List[str]): List of smiles

        Raises:
            ValueError: when string is not a smiles

        Returns:
            List[str]: List of the smiles
        """
        # check on rdkit availability:
        try:
            smiles2mol(categories[0])
        except NameError:
            warnings.warn("rdkit not installed, categories cannot be validated.")
            return categories

        for cat in categories:
            smiles2mol(cat)
        return categories

    @staticmethod
    def valid_transform_types() -> List[Union[AnyMolFeatures, CategoricalEncodingEnum]]:
        return CategoricalInput.valid_transform_types() + [
            Fingerprints,
            FingerprintsFragments,
            Fragments,
            MordredDescriptors,
        ]

    def get_bounds(
        self,
        transform_type: Union[CategoricalEncodingEnum, AnyMolFeatures],
        values: Optional[pd.Series] = None,
    ) -> Tuple[List[float], List[float]]:
        if isinstance(transform_type, CategoricalEncodingEnum):
            # we are just using the standard categorical transformations
            return super().get_bounds(transform_type=transform_type, values=values)
        else:
            # in case that values is None, we return the optimization bounds
            # else we return the complete bounds
            data = self.to_descriptor_encoding(
                transform_type=transform_type,
                values=values if values is not None else self.get_allowed_categories(),
            )

        lower = data.min(axis=0).values.tolist()
        upper = data.max(axis=0).values.tolist()

        return lower, upper
