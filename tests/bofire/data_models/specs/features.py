import math
import random
import uuid

import bofire.data_models.features.api as features
from bofire.data_models.objectives.api import (
    ConstrainedCategoricalObjective,
    MaximizeObjective,
)
from tests.bofire.data_models.specs.objectives import specs as objectives
from tests.bofire.data_models.specs.specs import Specs

# RDKIT_AVAILABLE = importlib.util.find_spec("rdkit") is not None

specs = Specs([])

specs.add_valid(
    features.DiscreteInput,
    lambda: {
        "key": str(uuid.uuid4()),
        "values": [random.random(), random.random() + 3],
        "unit": random.choice(["°C", "mg", "mmol/l", None]),
    },
)

specs.add_invalid(
    features.DiscreteInput,
    lambda: {
        "key": str(uuid.uuid4()),
        "values": [1.0],
        "unit": random.choice(["°C", "mg", "mmol/l", None]),
    },
    error=ValueError,
    message="Fixed discrete inputs are not supported. Please use a fixed continuous input.",
)


specs.add_valid(
    features.ContinuousInput,
    lambda: {
        "key": str(uuid.uuid4()),
        "bounds": (3, 5.3),
        "unit": random.choice(["°C", "mg", "mmol/l", None]),
        "local_relative_bounds": (math.inf, math.inf),
        "stepsize": None,
    },
)
specs.add_valid(
    features.ContinuousDescriptorInput,
    lambda: {
        "key": str(uuid.uuid4()),
        "bounds": (3, 5.3),
        "descriptors": ["d1", "d2"],
        "values": [1.0, 2.0],
        "unit": random.choice(["°C", "mg", "mmol/l", None]),
        "local_relative_bounds": (math.inf, math.inf),
        "stepsize": None,
    },
)
specs.add_valid(
    features.CategoricalInput,
    lambda: {
        "key": str(uuid.uuid4()),
        "categories": ["c1", "c2", "c3"],
        "allowed": [True, True, False],
    },
)

specs.add_invalid(
    features.CategoricalInput,
    lambda: {
        "key": str(uuid.uuid4()),
        "categories": ["c1", "c2", "c2"],
        "allowed": [True, True, False],
    },
    error=ValueError,
    message="categories must be unique",
)

specs.add_invalid(
    features.CategoricalInput,
    lambda: {
        "key": str(uuid.uuid4()),
        "categories": ["c1", "c2", "c3"],
        "allowed": [True, True],
    },
    error=ValueError,
    message="allowed must have same length as categories",
)

specs.add_invalid(
    features.CategoricalInput,
    lambda: {
        "key": str(uuid.uuid4()),
        "categories": ["c1", "c2", "c3"],
        "allowed": [False, False, False],
    },
    error=ValueError,
    message="no category is allowed",
)


specs.add_valid(
    features.CategoricalDescriptorInput,
    lambda: {
        "key": str(uuid.uuid4()),
        "categories": ["c1", "c2", "c3"],
        "allowed": [True, True, False],
        "descriptors": ["d1", "d2"],
        "values": [
            [1.0, 2.0],
            [3.0, 7.0],
            [5.0, 1.0],
        ],
    },
)
specs.add_valid(
    features.ContinuousOutput,
    lambda: {
        "key": str(uuid.uuid4()),
        "objective": objectives.valid(MaximizeObjective).typed_spec(),
        "unit": random.choice(["%", "area %", None]),
    },
)

specs.add_valid(
    features.CategoricalOutput,
    lambda: {
        "key": str(uuid.uuid4()),
        "categories": ["a", "b", "c"],
        "objective": ConstrainedCategoricalObjective(
            categories=["a", "b", "c"], desirability=[True, True, False]
        ).model_dump(),
    },
)
specs.add_valid(
    features.MolecularInput,
    lambda: {
        "key": str(uuid.uuid4()),
    },
)

specs.add_valid(
    features.CategoricalMolecularInput,
    lambda: {
        "key": str(uuid.uuid4()),
        "categories": [
            "CC(=O)Oc1ccccc1C(=O)O",
            "c1ccccc1",
            "[CH3][CH2][OH]",
            "N[C@](C)(F)C(=O)O",
        ],
        "allowed": [True, True, True, True],
    },
)
