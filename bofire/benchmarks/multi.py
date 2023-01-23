import json
import math
import pathlib
from typing import Optional

import numpy as np
import pandas as pd
from pydantic import validator
from pydantic.types import PositiveInt
from scipy.integrate import solve_ivp
from scipy.special import gamma

from bofire.benchmarks.benchmark import Benchmark
from bofire.domain import Domain
from bofire.domain.features import (
    CategoricalDescriptorInput,
    CategoricalInput,
    ContinuousInput,
    ContinuousOutput,
    InputFeature,
    InputFeatures,
    OutputFeatures,
)
from bofire.domain.objectives import MaximizeObjective, MinimizeObjective
from bofire.utils.enum import CategoricalEncodingEnum


class DTLZ2(Benchmark):
    """Multiobjective bechmark function for testing optimization algorithms.
    Info about the function: https://pymoo.org/problems/many/dtlz.html
    """

    def __init__(self, dim: PositiveInt, num_objectives: PositiveInt = 2):
        """Initiallizes object of Type DTLZ2 which is a benchmark function.

        Args:
            dim (PositiveInt): Dimension of input vector
            num_objectives (PositiveInt, optional): Dimension of output vector. Defaults to 2.
        """
        self.num_objectives = num_objectives
        self.dim = dim

        input_features = []
        for i in range(self.dim):
            input_features.append(
                ContinuousInput(key="x_%i" % (i), lower_bound=0.0, upper_bound=1.0)
            )
        output_features = []
        self.k = self.dim - self.num_objectives + 1
        for i in range(self.num_objectives):
            output_features.append(
                ContinuousOutput(key=f"f_{i}", objective=MinimizeObjective(w=1.0))
            )
        domain = Domain(
            input_features=InputFeatures(features=input_features),
            output_features=OutputFeatures(features=output_features),
        )
        self.ref_point = {
            feat: 1.1 for feat in domain.get_feature_keys(ContinuousOutput)
        }
        self._domain = domain

    @validator("dim")
    def validate_dim(cls, dim, values):
        num_objectives = values["num_objectives"]
        if dim <= values["num_objectives"]:
            raise ValueError(
                f"dim must be > num_objectives, but got {dim} and {num_objectives}."
            )
        return dim

    @property
    def best_possible_hypervolume(self) -> float:
        # hypercube - volume of hypersphere in R^d such that all coordinates are
        # positive
        hypercube_vol = self.ref_point[0] ** self.num_objectives  # type: ignore
        pos_hypersphere_vol = (
            math.pi ** (self.num_objectives / 2)
            / gamma(self.num_objectives / 2 + 1)
            / 2**self.num_objectives
        )
        return hypercube_vol - pos_hypersphere_vol

    def _f(self, candidates: pd.DataFrame) -> pd.DataFrame:
        """Function evaluation of DTLZ2.

        Args:
            candidates (pd.DataFrame): Input vector for x-values. Columns go from x0 to xdim.

        Returns:
            pd.DataFrame: Function values in output vector. Columns are f0 and f1.
        """
        X = candidates[self.domain.get_feature_keys(InputFeature)].values  # type: ignore
        X_m = X[..., -self.k :]  # type: ignore
        g_X = ((X_m - 0.5) ** 2).sum(axis=-1)
        g_X_plus1 = 1 + g_X
        fs = []
        pi_over_2 = math.pi / 2
        for i in range(self.num_objectives):
            idx = self.num_objectives - 1 - i
            f_i = g_X_plus1.copy()
            f_i *= np.cos(X[..., :idx] * pi_over_2).prod(axis=-1)
            if i > 0:
                f_i *= np.sin(X[..., idx] * pi_over_2)
            fs.append(f_i)

        col_names = self.domain.output_features.get_keys_by_objective(excludes=None)  # type: ignore
        y_values = np.stack(fs, axis=-1)
        Y = pd.DataFrame(data=y_values, columns=col_names)
        Y[
            [
                "valid_%s" % feat
                for feat in self.domain.output_features.get_keys_by_objective(  # type: ignore
                    excludes=None
                )
            ]
        ] = 1
        return Y


class SnarBenchmark(Benchmark):
    """Nucleophilic aromatic substitution problem as a multiobjective test function for optimization algorithms.
    Solving of a differential equation system with varying intitial values.
    """

    def __init__(self, C_i: Optional[np.ndarray] = np.ndarray((1, 1))):
        """Initializes multiobjective test function object of type SnarBenchmark.

        Args:
            C_i (Optional[np.ndarray]): Input concentrations. Defaults to [1, 1]
        """
        self.C_i = C_i

        # Decision variables
        # "residence time in minutes"
        input_features = [
            ContinuousInput(key="tau", lower_bound=0.5, upper_bound=2.0),
            # "equivalents of pyrrolidine"
            ContinuousInput(key="equiv_pldn", lower_bound=1.0, upper_bound=5.0),
            # "concentration of 2,4 dinitrofluorobenenze at reactor inlet (after mixing) in M"
            ContinuousInput(key="conc_dfnb", lower_bound=0.1, upper_bound=0.5),
            # "Reactor temperature in degress celsius"
            ContinuousInput(key="temperature", lower_bound=30, upper_bound=120.0),
        ]
        # Objectives
        # "space time yield (kg/m^3/h)"
        output_features = [
            ContinuousOutput(key="sty", objective=MaximizeObjective(w=1.0)),
            # "E-factor"
            ContinuousOutput(
                key="e_factor",
                objective=MinimizeObjective(w=1.0),
            ),
        ]
        self.ref_point = {"e_factor": 10.7, "sty": 2957.0}
        self._domain = Domain(
            input_features=InputFeatures(features=input_features),
            output_features=OutputFeatures(features=output_features),
        )

    @property
    def best_possible_hypervolume(self):
        return 10000.0

    def _f(self, candidates: pd.DataFrame) -> pd.DataFrame:
        """Function evaluation. Returns output vector.

        Args:
            candidates (pd.DataFrame): Input vector. Columns: tau, equiv_pldn, conc_dfnb, temperature

        Returns:
            pd.DataFrame: Output vector. Columns: sty, e_factor
        """
        stys = []
        e_factors = []
        for i, candidate in candidates.iterrows():
            tau = float(candidate["tau"])
            equiv_pldn = float(candidate["equiv_pldn"])
            conc_dfnb = float(candidate["conc_dfnb"])
            T = float(candidate["temperature"])
            y, e_factor, res = self._integrate_equations(tau, equiv_pldn, conc_dfnb, T)
            stys.append(y)
            e_factors.append(e_factor)
            # candidates["sty"] = y
            # candidates["e_factor"] = e_factor

        # return only y values instead of appending them to input dataframe
        Y = pd.DataFrame({"sty": stys, "e_factor": e_factors})
        Y[
            [
                "valid_%s" % feat
                for feat in self.domain.output_features.get_keys_by_objective(  # type: ignore
                    excludes=None
                )
            ]
        ] = 1
        return Y

    def _integrate_equations(self, tau, equiv_pldn, conc_dfnb, temperature, **kwargs):
        # Initial Concentrations in mM
        self.C_i = np.zeros(5)
        self.C_i[0] = conc_dfnb
        self.C_i[1] = equiv_pldn * conc_dfnb

        # Flowrate and residence time
        V = 5  # mL
        q_tot = V / tau
        # C1_0 = kwargs.get("C1_0", 2.0)  # reservoir concentration of 1 is 1 M = 1 mM
        # C2_0 = kwargs.get("C2_0", 4.2)  # reservoir concentration of  2 is 2 M = 2 mM
        # q_1 = self.C_i[0] / C1_0 * q_tot  # flowrate of 1 (dfnb)
        # q_2 = self.C_i[1] / C2_0 * q_tot  # flowrate of 2 (pldn)
        # q_eth = q_tot - q_1 - q_2  # flowrate of ethanol

        # Integrate
        res = solve_ivp(self._integrand, [0, tau], self.C_i, args=(temperature,))
        C_final = res.y[:, -1]

        # # Add measurement noise
        # C_final += (
        #     C_final * self.rng.normal(scale=self.noise_level, size=len(C_final)) / 100
        # )
        # C_final[
        #     C_final < 0
        # ] = 0  # prevent negative values of concentration introduced by noise

        # Calculate STY and E-factor
        M = [159.09, 71.12, 210.21, 210.21, 261.33]  # molecular weights (g/mol)
        sty = 6e4 / 1000 * M[2] * C_final[2] * q_tot / V  # convert to kg m^-3 h^-1
        if sty < 1e-6:
            sty = 1e-6
        rho_eth = 0.789  # g/mL (should adjust to temp, but just using @ 25C)
        term_2 = 1e-3 * sum([M[i] * C_final[i] * q_tot for i in range(5) if i != 2])
        if np.isclose(C_final[2], 0.0):
            # Set to a large value if no product formed
            e_factor = 1e3
        else:
            e_factor = (q_tot * rho_eth + term_2) / (1e-3 * M[2] * C_final[2] * q_tot)
        if e_factor > 1e3:
            e_factor = 1e3

        return sty, e_factor, {}

    def _integrand(self, t, C, T):
        # Kinetic Constants
        R = 8.314 / 1000  # kJ/K/mol
        T_ref = 90 + 273.71  # Convert to deg K
        T = T + 273.71  # Convert to deg K
        # Need to convert from 10^-2 M^-1s^-1 to M^-1min^-1
        k = (
            lambda k_ref, E_a, temp: 0.6
            * k_ref
            * np.exp(-E_a / R * (1 / temp - 1 / T_ref))
        )
        k_a = k(57.9, 33.3, T)
        k_b = k(2.70, 35.3, T)
        k_c = k(0.865, 38.9, T)
        k_d = k(1.63, 44.8, T)

        # Reaction Rates
        r = np.zeros(5)
        for i in [0, 1]:  # Set to reactants when close
            C[i] = 0 if C[i] < 1e-6 * self.C_i[i] else C[i]  # type: ignore
        r[0] = -(k_a + k_b) * C[0] * C[1]
        r[1] = -(k_a + k_b) * C[0] * C[1] - k_c * C[1] * C[2] - k_d * C[1] * C[3]
        r[2] = k_a * C[0] * C[1] - k_c * C[1] * C[2]
        r[3] = k_a * C[0] * C[1] - k_d * C[1] * C[3]
        r[4] = k_c * C[1] * C[2] + k_d * C[1] * C[3]

        # Deltas
        dcdtau = r
        return dcdtau


class ZDT1(Benchmark):
    """ZDT1 function for testing optimization algorithms.
    Explanation of the function: https://datacrayon.com/posts/search-and-optimisation/practical-evolutionary-algorithms/synthetic-objective-functions-and-zdt1/
    """

    def __init__(self, n_inputs=30):
        """Initializes class of type ZDT1 which is a benchmark function for optimization problems.

        Args:
            n_inputs (int, optional): Number of inputs. Defaults to 30.
        """
        self.n_inputs = n_inputs
        input_features = [
            ContinuousInput(key=f"x{i+1}", lower_bound=0, upper_bound=1)
            for i in range(n_inputs)
        ]
        inputs = InputFeatures(features=input_features)
        output_features = [
            ContinuousOutput(key=f"y{i+1}", objective=MinimizeObjective(w=1))
            for i in range(2)
        ]
        outputs = OutputFeatures(features=output_features)
        self._domain = Domain(input_features=inputs, output_features=outputs)

    def _f(self, X: pd.DataFrame) -> pd.DataFrame:
        """Function evaluation.

        Args:
            X (pd.DataFrame): Input values

        Returns:
            pd.DataFrame: Function values. Columns are y1, y2, valid_y1 and valid_y2.
        """
        x = X[self._domain.inputs.get_keys()[1:]].to_numpy()
        g = 1 + 9 / (self.n_inputs - 1) * np.sum(x, axis=1)
        y1 = X["x1"].to_numpy()
        y2 = g * (1 - (y1 / g) ** 0.5)
        return pd.DataFrame(
            {"y1": y1, "y2": y2, "valid_y1": 1, "valid_y2": 1}, index=X.index
        )

    def get_optima(self, points=100) -> pd.DataFrame:
        """Pareto front of the output variables.

        Args:
            points (int, optional): Number of points of the pareto front. Defaults to 100.

        Returns:
            pd.DataFrame: 2D pareto front with x and y values.
        """
        x = np.linspace(0, 1, points)
        y = np.stack([x, 1 - np.sqrt(x)], axis=1)
        return pd.DataFrame(y, columns=self.domain.outputs.get_keys())


class CrossCoupling(Benchmark):
    """Baumgartner Cross Coupling adapted from Summit (https://github.com/sustainable-processes/summit)

    Virtual experiments representing the Aniline Cross-Coupling reaction
    similar to Baumgartner et al. (2019). Experimental outcomes are based on an
    emulator that is trained on the experimental data published by Baumgartner et al.
    This is a five dimensional optimisation of temperature, residence time, base equivalents,
    catalyst and base.
    The categorical variables (catalyst and base) contain descriptors
    calculated using COSMO-RS. Specifically, the descriptors are the first two sigma moments.
    To use the pretrained version, call get_pretrained_baumgartner_cc_emulator
    Parameters
    ----------
    include_cost : bool, optional
        Include minimization of cost as an extra objective. Cost is calculated
        as a deterministic function of the inputs (i.e., no model is trained).
        Defaults to False.
    use_descriptors : bool, optional
        Use descriptors for the catalyst and base instead of one-hot encoding (defaults to False). T
        The descriptors been pre-calculated using COSMO-RS. To only use descriptors with
        a single feature, pass descriptors_features a list where
        the only item is the name of the desired categorical variable.
    Examples
    --------
    >>> bemul = CrossCoupling()
    Notes
    -----
    This benchmark is based on data from [Baumgartner]_ et al.
    References
    ----------
    .. [Baumgartner] L. M. Baumgartner et al., Org. Process Res. Dev., 2019, 23, 1594–1601
       DOI: `10.1021/acs.oprd.9b00236 <https://`doi.org/10.1021/acs.oprd.9b00236>`_
    """

    def __init__(
        self,
        descriptor_encoding: CategoricalEncodingEnum = CategoricalEncodingEnum.DESCRIPTOR,
        **kwargs,
    ):

        # "residence time in minutes"
        input_features = [
            CategoricalDescriptorInput(
                key="catalyst",
                categories=["tBuXPhos", "tBuBrettPhos", "AlPhos"],
                descriptors=[
                    "area_cat",
                    "M2_cat",
                ],  # , 'M3_cat', 'Macc3_cat', 'Mdon3_cat'] #,'mol_weight', 'sol']
                values=[
                    [
                        460.7543,
                        67.2057,
                    ],  # 30.8413, 2.3043, 0], #, 424.64, 421.25040226],
                    [
                        518.8408,
                        89.8738,
                    ],  # 39.4424, 2.5548, 0], #, 487.7, 781.11247064],
                    [
                        819.933,
                        129.0808,
                    ],  # 83.2017, 4.2959, 0], #, 815.06, 880.74916884],
                ],
            ),
            CategoricalDescriptorInput(
                key="base",
                categories=["TEA", "TMG", "BTMG", "DBU"],
                descriptors=[
                    "area",
                    "M2",
                ],  # , 'M3', 'Macc3', 'Mdon3', 'mol_weight', 'sol'
                values=[
                    [162.2992, 25.8165],  # 40.9469, 3.0278, 0], #101.19, 642.2973283],
                    [
                        165.5447,
                        81.4847,
                    ],  # 107.0287, 10.215, 0.0169], # 115.18, 534.01544123],
                    [
                        227.3523,
                        30.554,
                    ],  # 14.3676, 1.1196, 0.0127], # 171.28, 839.81215],
                    [192.4693, 59.8367],  # 82.0661, 7.42, 0], # 152.24, 1055.82799],
                ],
            ),
            # "base equivalents"
            ContinuousInput(key="base_eq", lower_bound=1.0, upper_bound=2.5),
            # "Reactor temperature in degrees celsius"
            ContinuousInput(key="temperature", lower_bound=30, upper_bound=100.0),
            # "residence time in seconds (s)"
            ContinuousInput(key="t_res", lower_bound=60, upper_bound=1800.0),
        ]

        self.input_preprocessing_specs = {
            "catalyst": descriptor_encoding,
            "base": descriptor_encoding,
        }

        # Objectives: yield and cost
        output_features = [
            ContinuousOutput(
                key="yield", bounds=[0.0, 1.0], objective=MaximizeObjective(w=1.0)
            ),
            ContinuousOutput(
                key="cost", objective=MinimizeObjective(w=1.0), bounds=[0.0, 1.0]
            ),
        ]
        self.ref_point = {"yield": 0.0, "cost": 1.0}

        self._domain = Domain(
            input_features=InputFeatures(features=input_features),
            output_features=OutputFeatures(features=output_features),
        )

    def _f(self, candidates: pd.DataFrame) -> pd.DataFrame:
        """Function evaluation. Returns output vector.

        Args:
            candidates (pd.DataFrame): Input vector. Columns: catalyst, base, base_eq, temperature, t_res

        Returns:
            pd.DataFrame: Output vector. Columns: yield, cost, valid_yield, valid_cost
        """
        Y = pd.DataFrame()
        for _, candidate in candidates.iterrows():
            # TODO hier Modell aufrufen!
            cost_i = self._calculate_costs(candidate)
            yield_i = self._integrate_equations(candidate)

            pd.concat(
                [Y, pd.DataFrame(data=[yield_i, cost_i], columns=["yield", "cost"])],
                axis=0,
            )

        Y[
            [
                "valid_%s" % feat
                for feat in self.domain.output_features.get_keys_by_objective(  # type: ignore
                    excludes=None
                )
            ]
        ] = 1
        return Y

    @classmethod
    def load(cls, save_dir, **kwargs):
        """Load all the essential parameters of the BaumgartnerCrossCouplingEmulator
        from disc
        Parameters
        ----------
        save_dir : str or pathlib.Path
            The directory from which to load emulator files.
        include_cost : bool, optional
            Include minimization of cost as an extra objective. Cost is calculated
            as a deterministic function of the inputs (i.e., no model is trained).
            Defaults to False.
        use_descriptors : bool, optional
            Use descriptors for the catalyst and base instead of one-hot encoding (defaults to False). T
            The descriptors been pre-calculated using COSMO-RS. To only use descriptors with
            a single feature, pass descriptors_features a list where
            the only item is the name of the desired categorical variable.
        """
        if cls.descriptor_encoding == CategoricalEncodingEnum.DESCRIPTOR:
            model_name = "baumgartner_aniline_cn_crosscoupling_descriptors"
        else:
            model_name = "baumgartner_aniline_cn_crosscoupling"
        save_dir = pathlib.Path(save_dir)
        with open(save_dir / f"{model_name}.json", "r") as f:
            d = json.load(f)
        d["experiment_params"]["include_cost"] = include_cost
        exp = ExperimentalEmulator.from_dict(d, **kwargs)
        exp.load_regressor(save_dir)
        return exp

    @classmethod
    def _calculate_costs(cls, conditions):
        catalyst = conditions["catalyst"].values
        base = conditions["base"].values
        base_equiv = conditions["base_equivalents"].values

        # Calculate amounts
        droplet_vol = 40 * 1e-3  # mL
        mmol_triflate = 0.91 * droplet_vol
        mmol_anniline = 1.6 * mmol_triflate
        catalyst_equiv = {
            "tBuXPhos": 0.0095,
            "tBuBrettPhos": 0.0094,
            "AlPhos": 0.0094,
        }
        mmol_catalyst = [catalyst_equiv[c] * mmol_triflate for c in catalyst]
        mmol_base = base_equiv * mmol_triflate

        # Calculate costs
        cost_triflate = mmol_triflate * 5.91  # triflate is $5.91/mmol
        cost_anniline = mmol_anniline * 0.01  # anniline is $0.01/mmol
        cost_catalyst = np.array(
            [cls._get_catalyst_cost(c, m) for c, m in zip(catalyst, mmol_catalyst)]
        )
        cost_base = np.array(
            [cls._get_base_cost(b, m) for b, m in zip(base, mmol_base)]
        )
        tot_cost = cost_triflate + cost_anniline + cost_catalyst + cost_base
        if len(tot_cost) == 1:
            tot_cost = tot_cost[0]
        return tot_cost

    @staticmethod
    def _get_catalyst_cost(catalyst, catalyst_mmol):
        catalyst_prices = {
            "tBuXPhos": 94.08,
            "tBuBrettPhos": 182.85,
            "AlPhos": 594.18,
        }
        return float(catalyst_prices[catalyst] * catalyst_mmol)

    @staticmethod
    def _get_base_cost(base, mmol_base):
        # prices in $/mmol
        base_prices = {
            "DBU": 0.03,
            "BTMG": 1.2,
            "TMG": 0.001,
            "TEA": 0.01,
        }
        return float(base_prices[base] * mmol_base)


def get_pretrained_baumgartner_cc_emulator(include_cost=False, use_descriptors=False):
    """Get a pretrained BaumgartnerCrossCouplingEmulator
    Parameters
    ----------
    include_cost : bool, optional
        Include minimization of cost as an extra objective. Cost is calculated
        as a deterministic function of the inputs (i.e., no model is trained).
        Defaults to False.
    use_descriptors : bool, optional
        Use descriptors for the catalyst and base instead of one-hot encoding (defaults to False). T
        The descriptors been pre-calculated using COSMO-RS. To only use descriptors with
        a single feature, pass descriptors_features a list where
        the only item is the name of the desired categorical variable.
    Examples
    --------
    >>> import matplotlib.pyplot as plt
    >>> from summit.benchmarks import get_pretrained_baumgartner_cc_emulator
    >>> from summit.utils.dataset import DataSet
    >>> import pandas as pd
    >>> b = get_pretrained_baumgartner_cc_emulator(include_cost=True, use_descriptors=False)
    >>> fig, ax = b.parity_plot(include_test=True)
    >>> plt.show()
    >>> columns = [v.name for v in b.domain.variables]
    >>> values = { "catalyst": ["tBuXPhos"], "base": ["DBU"], "t_res": [328.717801570892],"temperature": [30],"base_equivalents": [2.18301549894049]}
    >>> conditions = pd.DataFrame(values)
    >>> conditions = DataSet.from_df(conditions)
    >>> results = b.run_experiments(conditions, return_std=True)
    """
    model_name = "baumgartner_aniline_cn_crosscoupling"
    data_path = get_data_path()
    ds = DataSet.read_csv(data_path / f"{model_name}.csv")
    model_name += "_descriptors" if use_descriptors else ""
    model_path = get_model_path() / model_name
    if not model_path.exists():
        raise NotADirectoryError("Could not initialize from expected path.")
    exp = BaumgartnerCrossCouplingEmulator.load(
        model_path,
        dataset=ds,
        include_cost=include_cost,
        use_descriptors=use_descriptors,
    )
    return exp
