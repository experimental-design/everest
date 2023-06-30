import warnings
from typing import Literal

import numpy as np
import pandas as pd
from pydantic import root_validator

try:
    from rdkit.Chem import Descriptors
except ImportError:
    warnings.warn(
        "rdkit not installed, BoFire's cheminformatics utilities cannot be used."
    )

from bofire.data_models.features.feature import TDescriptors
from bofire.data_models.molfeatures.molfeatures import MolFeatures
from bofire.utils.cheminformatics import (  # smiles2bag_of_characters,
    smiles2fingerprints,
    smiles2fragments,
    smiles2fragments_fingerprints,
    smiles2mordred,
)


class Fingerprints(MolFeatures):
    type: Literal["Fingerprints"] = "Fingerprints"
    bond_radius: int = 5
    n_bits: int = 2048

    @root_validator
    def generate_descriptor_names(cls, values):
        if values["descriptors"] is None:
            values["descriptors"] = [
                f"fingerprint_{i}" for i in range(values["n_bits"])
            ]
        return values

    def __call__(self, values: pd.Series) -> pd.DataFrame:
        return pd.DataFrame(
            data=smiles2fingerprints(
                values.to_list(), bond_radius=self.bond_radius, n_bits=self.n_bits
            ).astype(float),
            columns=self.descriptors,
            index=values.index,
        )


class Fragments(MolFeatures):
    type: Literal["Fragments"] = "Fragments"

    @root_validator
    def generate_descriptor_names(cls, values):
        if values["descriptors"] is None:
            values["descriptors"] = [
                f"{i}" for i in [fragment[0] for fragment in Descriptors.descList[124:]]
            ]
        return values

    def __call__(self, values: pd.Series) -> pd.DataFrame:
        return pd.DataFrame(
            data=smiles2fragments(values.to_list()),
            columns=self.descriptors,
            index=values.index,
        )


class FingerprintsFragments(MolFeatures):
    type: Literal["FingerprintsFragments"] = "FingerprintsFragments"
    bond_radius: int = 5
    n_bits: int = 2048

    @root_validator
    def generate_descriptor_names(cls, values):
        if values["descriptors"] is None:
            values["descriptors"] = [
                f"fingerprint_{i}" for i in range(values["n_bits"])
            ] + [
                f"{i}" for i in [fragment[0] for fragment in Descriptors.descList[124:]]
            ]
        return values

    def __call__(self, values: pd.Series) -> pd.DataFrame:
        # values is SMILES; not molecule name
        # fingerprints = smiles2fingerprints(
        #     values.to_list(), bond_radius=self.bond_radius, n_bits=self.n_bits
        # )
        # fragments = smiles2fragments(values.to_list())

        return pd.DataFrame(
            data=smiles2fragments_fingerprints(
                values.to_list(), bond_radius=self.bond_radius, n_bits=self.n_bits
            ),
            columns=self.descriptors,
            index=values.index,
        )


# class BagOfCharacters(MolFeatures):
#     type: Literal["BagOfCharacters"] = "BagOfCharacters"
#     max_ngram: int = 5
#
#     def __call__(self, values: pd.Series) -> pd.DataFrame:
#         data = smiles2bag_of_characters(values.to_list(), max_ngram=self.max_ngram)
#         self.descriptors = [f'boc_{i}' for i in range(data.shape[1])]
#
#         return pd.DataFrame(
#             data=data,
#             columns=self.descriptors,
#             index=values.index,
#         )


class MordredDescriptors(MolFeatures):
    type: Literal["MordredDescriptors"] = "MordredDescriptors"
    descriptors: TDescriptors

    def __call__(self, values: pd.Series) -> pd.DataFrame:
        # values is SMILES; not molecule name
        return pd.DataFrame(
            data=smiles2mordred(values.to_list(), self.descriptors),
            columns=self.descriptors,
            index=values.index,
        )
