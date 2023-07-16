import warnings
from typing import Annotated, List, Literal, Optional

import pandas as pd
from pydantic import Field, validator

from bofire.data_models.base import BaseModel
from bofire.utils.cheminformatics import (  # smiles2bag_of_characters,
    smiles2fingerprints,
    smiles2fragments,
    smiles2fragments_fingerprints,
    smiles2mordred,
)

try:
    from rdkit.Chem import Descriptors
except ImportError:
    warnings.warn(
        "rdkit not installed, BoFire's cheminformatics utilities cannot be used."
    )

try:
    from mordred import Calculator
    from mordred import descriptors as mordred_descriptors
except ImportError:
    warnings.warn(
        "mordred not installed. Mordred molecular descriptors cannot be used."
    )


class MolFeatures(BaseModel):
    """Base class for all molecular features"""

    type: str


class Fingerprints(MolFeatures):
    type: Literal["Fingerprints"] = "Fingerprints"
    bond_radius: int = 5
    n_bits: int = 2048

    def get_descriptor_names(self) -> List[str]:
        return [f"fingerprint_{i}" for i in range(self.n_bits)]

    def get_descriptor_values(self, values: pd.Series) -> pd.DataFrame:
        return pd.DataFrame(
            data=smiles2fingerprints(
                values.to_list(), bond_radius=self.bond_radius, n_bits=self.n_bits
            ).astype(float),
            columns=self.get_descriptor_names(),
            index=values.index,
        )


class Fragments(MolFeatures):
    type: Literal["Fragments"] = "Fragments"
    fragments: Optional[List[str]] = None

    @validator(
        "fragments",
    )
    def validate_fragments(cls, fragments):
        """validates that fragments have unique names

        Args:
            categories (List[str]): List of fragment names

        Raises:
            ValueError: when fragments have non-unique names

        Returns:
            List[str]: List of the fragments
        """
        if fragments is not None:
            if len(fragments) != len(set(fragments)):
                raise ValueError("Fragments must be unique")

            if not all(
                user_fragment
                in [rdkit_fragment[0] for rdkit_fragment in Descriptors.descList[124:]]
                for user_fragment in fragments
            ):
                raise ValueError(
                    "Not all provided fragments were not found in the RDKit list"
                )

        return fragments

    def get_descriptor_names(self) -> List[str]:
        return (
            self.fragments
            if self.fragments is not None
            else [rdkit_fragment[0] for rdkit_fragment in Descriptors.descList[124:]]
        )

    def get_descriptor_values(self, values: pd.Series) -> pd.DataFrame:
        return pd.DataFrame(
            data=smiles2fragments(values.to_list(), self.get_descriptor_names()),
            columns=self.get_descriptor_names(),
            index=values.index,
        )


class FingerprintsFragments(Fingerprints, Fragments):
    type: Literal["FingerprintsFragments"] = "FingerprintsFragments"

    def get_descriptor_names(self) -> List[str]:
        fingerprints_list = [f"fingerprint_{i}" for i in range(self.n_bits)]
        fragments_list = (
            self.fragments
            if self.fragments is not None
            else [rdkit_fragment[0] for rdkit_fragment in Descriptors.descList[124:]]
        )

        fingerprints_fragment_list = fingerprints_list + fragments_list

        return fingerprints_fragment_list

    def get_descriptor_values(self, values: pd.Series) -> pd.DataFrame:
        fragments_list = (
            self.fragments
            if self.fragments is not None
            else [rdkit_fragment[0] for rdkit_fragment in Descriptors.descList[124:]]
        )

        return pd.DataFrame(
            data=smiles2fragments_fingerprints(
                values.to_list(),
                bond_radius=self.bond_radius,
                n_bits=self.n_bits,
                fragments_list=fragments_list,
            ),
            columns=self.get_descriptor_names(),
            index=values.index,
        )


class MordredDescriptors(MolFeatures):
    type: Literal["MordredDescriptors"] = "MordredDescriptors"
    descriptors: Annotated[List[str], Field(min_items=1)]

    @validator(
        "descriptors",
    )
    def validate_descriptors(cls, descriptors):
        """validates that descriptors have unique names

        Args:
            descriptors (List[str]): List of descriptor names

        Raises:
            ValueError: when descriptors have non-unique names

        Returns:
            List[str]: List of the descriptors
        """
        if len(descriptors) != len(set(descriptors)):
            raise ValueError("descriptors must be unique")

        calc = Calculator(mordred_descriptors, ignore_3D=False)
        if not all(desc in [str(d) for d in calc.descriptors] for desc in descriptors):
            raise ValueError(
                "Not all provided descriptors were not found in the Mordred list"
            )

        return descriptors

    def get_descriptor_names(self) -> List[str]:
        return self.descriptors

    def get_descriptor_values(self, values: pd.Series) -> pd.DataFrame:
        return pd.DataFrame(
            data=smiles2mordred(values.to_list(), self.descriptors),
            columns=self.descriptors,
            index=values.index,
        )
