"""
SUN GEAR + INPUT SHAFT SIZING

Purpose:
    Size the integral sun-gear/input shaft for:
        1. Fatigue under cyclic torsion
        2. Static yielding at peak torque
        3. Torsional stiffness
        4. Sun-root radial packaging

Architecture / assumptions:
    - Sun gear and input shaft are one integral component.
    - Symmetric planet loading -> net transverse sun force cancels.
    - Shaft bending moment is neglected in preliminary sizing.
    - Spur gears -> axial load = 0.
    - Solid circular shaft.
    - Initial sizing neglects geometric stress concentrations:
          K_t = K_ts = K_f = K_fs = 1
    - Stress concentration effects are deferred to final CAD verification.

INPUTS
------
From previous modules:
    T_max_nm                   Maximum transmitted sun torque [N.m]
    T_min_nm                   Minimum transmitted sun torque [N.m]

From planetary.py:
    module_mm                  Gear module [mm]
    z_s                        Sun tooth count [-]

From material catalogue:
    name                       Material designation
    Sy_MPa                     Yield strength [MPa]
    Sut_MPa                    Ultimate tensile strength [MPa]
    Se_prime_MPa               Unmodified endurance limit [MPa]
    shear_modulus_GPa          Shear modulus G [GPa]

Configuration:
    fatigue_safety_factor      Required Goodman fatigue SF [-]
    yield_safety_factor        Required static yield SF [-]

    marin_surface_factor       k_a [-]
    marin_size_factor          k_b [-]
    marin_load_factor          k_c [-]
    marin_temperature_factor   k_d [-]
    marin_reliability_factor   k_e [-]
    marin_misc_factor          k_misc [-]

    effective_torsion_length_mm
                               Effective shaft length subjected to twist [mm]

    max_twist_deg              Maximum allowed torsional twist [deg]

    min_root_ligament_mm       Minimum radial material between shaft OD
                               and sun tooth-root diameter [mm]

OUTPUTS
-------
Torque decomposition:
    T_mean_nm
    T_alt_nm
    T_peak_abs_nm

Fatigue:
    Se_MPa                     Modified endurance limit [MPa]
    d_fatigue_mm               Minimum fatigue diameter [mm]

Static:
    d_yield_mm                 Minimum yield diameter [mm]

Stiffness:
    d_stiffness_mm             Minimum torsional-stiffness diameter [mm]

Final sizing:
    d_required_mm              Maximum of fatigue, yield and stiffness
    governing_requirement      fatigue / yield / stiffness

Sun-root packaging:
    sun_root_diameter_mm
    max_shaft_diameter_mm
    root_ligament_mm

Verification at selected minimum diameter:
    peak_shear_stress_MPa
    peak_von_mises_MPa
    fatigue_safety_achieved
    yield_safety_achieved
    twist_deg

Constraint result:
    feasible
    rejection_reason

MAIN HARD CONSTRAINT
--------------------
    d_required <= d_f,s - 2*t_lig,min

where:
    d_f,s ~= m(Z_s - 2.5)

NOT INCLUDED HERE
-----------------
    Bearing selection
    Bearing-seat shoulders
    Rotor drive plate
    CAD shoulder stress concentrations
    Shaft bending due to bearing/housing misalignment
"""

from dataclasses import dataclass, asdict
from math import pi, sqrt, radians, degrees
from typing import Optional


# ============================================================
# MATERIAL
# ============================================================

@dataclass(frozen=True)
class ShaftMaterial:
    name: str

    Sy_MPa: float
    Sut_MPa: float

    # Unmodified endurance limit S'_e
    Se_prime_MPa: float

    shear_modulus_GPa: float


# ============================================================
# INPUT
# ============================================================

@dataclass(frozen=True)
class SunShaftInput:

    T_max_nm: float
    T_min_nm: float

    module_mm: float
    z_s: int


# ============================================================
# CONFIGURATION
# ============================================================

@dataclass(frozen=True)
class SunShaftConfig:

    fatigue_safety_factor: float
    yield_safety_factor: float

    # Marin factors
    marin_surface_factor: float
    marin_size_factor: float
    marin_load_factor: float
    marin_temperature_factor: float
    marin_reliability_factor: float
    marin_misc_factor: float

    # Torsional stiffness
    effective_torsion_length_mm: float
    max_twist_deg: float

    # Sun-root packaging
    min_root_ligament_mm: float


# ============================================================
# OUTPUT
# ============================================================

@dataclass
class SunShaftResult:

    feasible: bool
    rejection_reason: Optional[str]

    material_name: str

    # Torque decomposition
    T_mean_nm: float
    T_alt_nm: float
    T_peak_abs_nm: float

    # Endurance
    Se_MPa: float

    # Required diameters
    d_fatigue_mm: float
    d_yield_mm: float
    d_stiffness_mm: float

    d_required_mm: float
    governing_requirement: str

    # Sun-root packaging
    sun_root_diameter_mm: float
    max_shaft_diameter_mm: float
    root_ligament_mm: float

    # Verification
    peak_shear_stress_MPa: float
    peak_von_mises_MPa: float

    fatigue_safety_achieved: float
    yield_safety_achieved: float

    twist_deg: float


# ============================================================
# MAIN CALCULATION
# ============================================================

def evaluate_sun_shaft(
    inp: SunShaftInput,
    material: ShaftMaterial,
    cfg: SunShaftConfig,
) -> SunShaftResult:

    # --------------------------------------------------------
    # Input validation
    # --------------------------------------------------------

    if inp.T_max_nm < inp.T_min_nm:
        raise ValueError(
            "T_max_nm must be greater than or equal to T_min_nm."
        )

    if inp.module_mm <= 0:
        raise ValueError("Gear module must be > 0.")

    if inp.z_s <= 0:
        raise ValueError("Sun tooth count must be > 0.")

    if material.Sy_MPa <= 0:
        raise ValueError("Yield strength must be > 0.")

    if material.Sut_MPa <= 0:
        raise ValueError("Ultimate strength must be > 0.")

    if material.Se_prime_MPa <= 0:
        raise ValueError("Unmodified endurance limit must be > 0.")

    if material.shear_modulus_GPa <= 0:
        raise ValueError("Shear modulus must be > 0.")

    if cfg.fatigue_safety_factor <= 0:
        raise ValueError("Fatigue safety factor must be > 0.")

    if cfg.yield_safety_factor <= 0:
        raise ValueError("Yield safety factor must be > 0.")

    if cfg.effective_torsion_length_mm <= 0:
        raise ValueError(
            "Effective torsion length must be > 0."
        )

    if cfg.max_twist_deg <= 0:
        raise ValueError("Maximum twist must be > 0.")

    if cfg.min_root_ligament_mm < 0:
        raise ValueError(
            "Minimum root ligament cannot be negative."
        )

    marin_factors = (
        cfg.marin_surface_factor,
        cfg.marin_size_factor,
        cfg.marin_load_factor,
        cfg.marin_temperature_factor,
        cfg.marin_reliability_factor,
        cfg.marin_misc_factor,
    )

    if any(value <= 0 for value in marin_factors):
        raise ValueError(
            "All Marin factors must be > 0."
        )

    # ========================================================
    # 1. TORQUE DECOMPOSITION
    #
    # T_m = (T_max + T_min)/2
    #
    # T_a = (T_max - T_min)/2
    # ========================================================

    T_mean_nm = (
        inp.T_max_nm
        + inp.T_min_nm
    ) / 2.0

    T_alt_nm = (
        inp.T_max_nm
        - inp.T_min_nm
    ) / 2.0

    T_peak_abs_nm = max(
        abs(inp.T_max_nm),
        abs(inp.T_min_nm),
    )

    # Convert N.m -> N.mm
    T_mean_Nmm = abs(T_mean_nm) * 1000.0
    T_alt_Nmm = abs(T_alt_nm) * 1000.0
    T_peak_Nmm = T_peak_abs_nm * 1000.0

    # ========================================================
    # 2. MODIFIED ENDURANCE LIMIT
    #
    # Se =
    # ka * kb * kc * kd * ke * kmisc * Se'
    #
    # NOTE:
    # For the current DE/von-Mises conversion of torsion,
    # kc should remain 1.0 to avoid applying the torsional
    # load correction twice.
    # ========================================================

    Se_MPa = (
        cfg.marin_surface_factor
        * cfg.marin_size_factor
        * cfg.marin_load_factor
        * cfg.marin_temperature_factor
        * cfg.marin_reliability_factor
        * cfg.marin_misc_factor
        * material.Se_prime_MPa
    )

    # ========================================================
    # 3. FATIGUE DIAMETER — MODIFIED GOODMAN
    #
    # sigma'_a = 16*sqrt(3)*T_a / (pi*d^3)
    #
    # sigma'_m = 16*sqrt(3)*T_m / (pi*d^3)
    #
    # sigma'_a/Se + sigma'_m/Sut = 1/n_f
    #
    # Solving for d:
    #
    # d_fatigue =
    # [
    #   16*sqrt(3)*n_f/pi
    #   *
    #   (T_a/Se + T_m/Sut)
    # ]^(1/3)
    # ========================================================

    fatigue_term = (
        T_alt_Nmm / Se_MPa
        +
        T_mean_Nmm / material.Sut_MPa
    )

    if fatigue_term == 0.0:
        d_fatigue_mm = 0.0

    else:
        d_fatigue_mm = (
            (
                16.0
                * sqrt(3.0)
                * cfg.fatigue_safety_factor
                / pi
            )
            * fatigue_term
        ) ** (1.0 / 3.0)

    # ========================================================
    # 4. STATIC YIELD DIAMETER
    #
    # tau = 16*T/(pi*d^3)
    #
    # sigma_VM = sqrt(3)*tau
    #
    # sigma_VM <= Sy/n_y
    #
    # d_yield =
    # [
    #   16*sqrt(3)*n_y*T_peak
    #   /
    #   (pi*Sy)
    # ]^(1/3)
    # ========================================================

    if T_peak_Nmm == 0.0:
        d_yield_mm = 0.0

    else:
        d_yield_mm = (
            (
                16.0
                * sqrt(3.0)
                * cfg.yield_safety_factor
                * T_peak_Nmm
            )
            /
            (
                pi
                * material.Sy_MPa
            )
        ) ** (1.0 / 3.0)

    # ========================================================
    # 5. TORSIONAL STIFFNESS DIAMETER
    #
    # J = pi*d^4/32
    #
    # theta = T*L/(J*G)
    #
    # theta = 32*T*L/(pi*G*d^4)
    #
    # therefore:
    #
    # d_stiffness =
    # [
    #   32*T*L /
    #   (pi*G*theta_allow)
    # ]^(1/4)
    # ========================================================

    G_MPa = (
        material.shear_modulus_GPa
        * 1000.0
    )

    theta_allow_rad = radians(
        cfg.max_twist_deg
    )

    if T_peak_Nmm == 0.0:
        d_stiffness_mm = 0.0

    else:
        d_stiffness_mm = (
            (
                32.0
                * T_peak_Nmm
                * cfg.effective_torsion_length_mm
            )
            /
            (
                pi
                * G_MPa
                * theta_allow_rad
            )
        ) ** 0.25

    # ========================================================
    # 6. REQUIRED SHAFT DIAMETER
    # ========================================================

    diameter_requirements = {
        "fatigue": d_fatigue_mm,
        "yield": d_yield_mm,
        "stiffness": d_stiffness_mm,
    }

    governing_requirement = max(
        diameter_requirements,
        key=diameter_requirements.get,
    )

    d_required_mm = (
        diameter_requirements[
            governing_requirement
        ]
    )

    # ========================================================
    # 7. SUN ROOT DIAMETER
    #
    # Standard full-depth approximation:
    #
    # d_f,s = m(Z_s - 2.5)
    # ========================================================

    sun_root_diameter_mm = (
        inp.module_mm
        * (inp.z_s - 2.5)
    )

    if sun_root_diameter_mm <= 0:
        raise ValueError(
            "Calculated sun root diameter is non-positive."
        )

    # ========================================================
    # 8. MAXIMUM SHAFT DIAMETER ALLOWED BY ROOT LIGAMENT
    #
    # t_lig =
    # (d_f,s - d_shaft)/2
    #
    # Require:
    #
    # t_lig >= t_lig,min
    #
    # therefore:
    #
    # d_shaft <= d_f,s - 2*t_lig,min
    # ========================================================

    max_shaft_diameter_mm = (
        sun_root_diameter_mm
        - 2.0 * cfg.min_root_ligament_mm
    )

    root_ligament_mm = (
        sun_root_diameter_mm
        - d_required_mm
    ) / 2.0

    # ========================================================
    # 9. VERIFICATION AT REQUIRED DIAMETER
    # ========================================================

    if d_required_mm > 0:

        peak_shear_stress_MPa = (
            16.0
            * T_peak_Nmm
            /
            (
                pi
                * d_required_mm**3
            )
        )

        peak_von_mises_MPa = (
            sqrt(3.0)
            * peak_shear_stress_MPa
        )

        sigma_alt_eq_MPa = (
            16.0
            * sqrt(3.0)
            * T_alt_Nmm
            /
            (
                pi
                * d_required_mm**3
            )
        )

        sigma_mean_eq_MPa = (
            16.0
            * sqrt(3.0)
            * T_mean_Nmm
            /
            (
                pi
                * d_required_mm**3
            )
        )

        goodman_usage = (
            sigma_alt_eq_MPa / Se_MPa
            +
            sigma_mean_eq_MPa
            / material.Sut_MPa
        )

        if goodman_usage > 0:
            fatigue_safety_achieved = (
                1.0 / goodman_usage
            )
        else:
            fatigue_safety_achieved = float("inf")

        if peak_von_mises_MPa > 0:
            yield_safety_achieved = (
                material.Sy_MPa
                / peak_von_mises_MPa
            )
        else:
            yield_safety_achieved = float("inf")

        theta_rad = (
            32.0
            * T_peak_Nmm
            * cfg.effective_torsion_length_mm
            /
            (
                pi
                * G_MPa
                * d_required_mm**4
            )
        )

        twist_deg = degrees(
            theta_rad
        )

    else:

        peak_shear_stress_MPa = 0.0
        peak_von_mises_MPa = 0.0

        fatigue_safety_achieved = float("inf")
        yield_safety_achieved = float("inf")

        twist_deg = 0.0

    # ========================================================
    # 10. ROOT PACKAGING CHECK
    # ========================================================

    if max_shaft_diameter_mm <= 0:

        return _build_result(
            feasible=False,
            rejection_reason=(
                "insufficient_sun_root_for_minimum_ligament"
            ),
            locals_dict=locals(),
        )

    if d_required_mm > max_shaft_diameter_mm:

        return _build_result(
            feasible=False,
            rejection_reason=(
                "required_shaft_diameter_exceeds_sun_root_capacity"
            ),
            locals_dict=locals(),
        )

    # ========================================================
    # SUCCESS
    # ========================================================

    return _build_result(
        feasible=True,
        rejection_reason=None,
        locals_dict=locals(),
    )


# ============================================================
# RESULT BUILDER
# ============================================================

def _build_result(
    feasible: bool,
    rejection_reason: Optional[str],
    locals_dict: dict,
) -> SunShaftResult:

    L = locals_dict

    return SunShaftResult(
        feasible=feasible,
        rejection_reason=rejection_reason,

        material_name=L["material"].name,

        T_mean_nm=L["T_mean_nm"],
        T_alt_nm=L["T_alt_nm"],
        T_peak_abs_nm=L["T_peak_abs_nm"],

        Se_MPa=L["Se_MPa"],

        d_fatigue_mm=L["d_fatigue_mm"],
        d_yield_mm=L["d_yield_mm"],
        d_stiffness_mm=L["d_stiffness_mm"],

        d_required_mm=L["d_required_mm"],
        governing_requirement=L[
            "governing_requirement"
        ],

        sun_root_diameter_mm=L[
            "sun_root_diameter_mm"
        ],

        max_shaft_diameter_mm=L[
            "max_shaft_diameter_mm"
        ],

        root_ligament_mm=L[
            "root_ligament_mm"
        ],

        peak_shear_stress_MPa=L[
            "peak_shear_stress_MPa"
        ],

        peak_von_mises_MPa=L[
            "peak_von_mises_MPa"
        ],

        fatigue_safety_achieved=L[
            "fatigue_safety_achieved"
        ],

        yield_safety_achieved=L[
            "yield_safety_achieved"
        ],

        twist_deg=L[
            "twist_deg"
        ],
    )


def result_to_dict(
    result: SunShaftResult
) -> dict:

    return asdict(result)