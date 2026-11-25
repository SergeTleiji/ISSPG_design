"""
OUTPUT SHAFT + OUTPUT BEARINGS

Purpose:
    Size the output shaft for combined bending and torsion, then evaluate
    the two catalogue ball bearings supporting the output assembly.

Architecture:
    Carrier plate + central hub + output shaft = one integral rotating part.

    Bearing A = inner/non-locating support
    Bearing B = outer/locating support

    Both bearings use the same shaft journal diameter for simple assembly.

    Bearing stack:
        carrier shoulder
            -> Bearing A
            -> inner-ring spacer
            -> Bearing B
            -> removable locknut/end retainer

Assumptions:
    - Output shaft is solid and circular.
    - External joint load is radial only.
    - External joint load acts outboard of Bearing B.
    - Axial load = 0.
    - Bearing reactions are obtained from static beam equilibrium.
    - Initial shaft sizing neglects shoulder stress concentrations:
          K_t = K_ts = 1
    - Exact shoulder stress concentration is deferred to final CAD.
    - Deep-groove ball bearings are used:
          bearing life exponent p = 3
    - Both bearing seats use the same bore diameter.

INPUTS
------
From actuator requirements:
    external_radial_load_N          Joint radial load F_J [N]

From previous modules:
    T_c_nm                          Carrier/output torque [N.m]
    n_c_rpm                         Output/carrier speed [rpm]

From material catalogue:
    name                            Material designation
    Sy_MPa                          Yield strength [MPa]

From bearing catalogue:
    Bearing A and Bearing B:
        designation
        bore_mm
        outer_diameter_mm
        width_mm
        C_N                         Basic dynamic load rating [N]
        C0_N                        Basic static load rating [N]
        limiting_speed_rpm
        mass_kg

Configuration:
    shaft_safety_factor             Required output-shaft static SF [-]
    inner_ring_spacer_mm            Preliminary inner-ring spacer length [mm]
    load_overhang_mm                Distance from Bearing B center to
                                    external joint load [mm]
    required_bearing_life_h         Required L10 life [h]
    min_static_safety_factor        Required bearing static safety [-]

OUTPUTS
-------
Geometry:
    bearing_spacing_mm              L_o [mm]
    load_overhang_mm                e_o [mm]

Bearing reactions:
    reaction_A_N                    Signed reaction at A [N]
    reaction_B_N                    Signed reaction at B [N]

Shaft loading:
    max_bending_moment_Nmm
    torque_Nmm

Shaft sizing:
    theoretical_min_diameter_mm
    actual_shaft_diameter_mm        Selected catalogue bearing bore [mm]

Actual shaft stresses:
    bending_stress_MPa
    shear_stress_MPa
    von_mises_stress_MPa
    achieved_shaft_safety_factor

Bearing loads:
    P_A_N
    P_B_N
    P0_A_N
    P0_B_N

Bearing life:
    L10h_A
    L10h_B

Bearing static safety:
    s0_A
    s0_B

Bearing speed:
    speed_ratio_A
    speed_ratio_B

Overall:
    feasible
    rejection_reason

HARD CHECKS
-----------
    1. Bearing A and B use the same bore diameter
    2. Bearing bore >= theoretical shaft diameter
    3. Actual shaft stress satisfies required safety factor
    4. Bearing A life
    5. Bearing B life
    6. Bearing A static safety
    7. Bearing B static safety
    8. Bearing A limiting speed
    9. Bearing B limiting speed

NOT INCLUDED HERE
-----------------
    Final shoulder dimensions
    K_t and K_ts from shoulders/fillets
    Bearing fits and tolerances
    Housing outer-ring retention
    Locknut/thread design
    Final CAD-derived spacer and overhang dimensions
"""

from dataclasses import dataclass, asdict
from math import pi, sqrt, isclose
from typing import Optional


# ============================================================
# MATERIAL
# ============================================================

@dataclass(frozen=True)
class OutputShaftMaterial:
    name: str
    Sy_MPa: float


# ============================================================
# BALL BEARING CATALOGUE ENTRY
# ============================================================

@dataclass(frozen=True)
class OutputBearingSpec:
    designation: str

    bore_mm: float
    outer_diameter_mm: float
    width_mm: float

    C_N: float
    C0_N: float

    limiting_speed_rpm: float

    mass_kg: float


# ============================================================
# INPUT
# ============================================================

@dataclass(frozen=True)
class OutputSystemInput:

    # Output loading
    T_c_nm: float
    external_radial_load_N: float

    # Output speed
    n_c_rpm: float


# ============================================================
# CONFIGURATION
# ============================================================

@dataclass(frozen=True)
class OutputSystemConfig:

    # Shaft
    shaft_safety_factor: float

    # Preliminary CAD / packaging dimensions
    inner_ring_spacer_mm: float
    load_overhang_mm: float

    # Bearings
    required_bearing_life_h: float
    min_static_safety_factor: float


# ============================================================
# OUTPUT
# ============================================================

@dataclass
class OutputSystemResult:

    feasible: bool
    rejection_reason: Optional[str]

    material_name: str

    bearing_A_designation: str
    bearing_B_designation: str

    # Geometry
    bearing_spacing_mm: float
    load_overhang_mm: float

    # Reactions
    reaction_A_N: float
    reaction_B_N: float

    # Loads
    max_bending_moment_Nmm: float
    torque_Nmm: float

    # Shaft sizing
    theoretical_min_diameter_mm: float
    actual_shaft_diameter_mm: float

    # Actual shaft stresses
    bending_stress_MPa: float
    shear_stress_MPa: float
    von_mises_stress_MPa: float
    achieved_shaft_safety_factor: float

    # Bearing loads
    P_A_N: float
    P_B_N: float

    P0_A_N: float
    P0_B_N: float

    # Life
    L10h_A: float
    L10h_B: float

    # Static safety
    s0_A: float
    s0_B: float

    # Speed
    speed_ratio_A: float
    speed_ratio_B: float

    # Catalogue bore
    bearing_bore_mm: float


# ============================================================
# BALL-BEARING LIFE
# ============================================================

def _ball_bearing_life_hours(
    C_N: float,
    P_N: float,
    speed_rpm: float,
) -> float:

    if P_N <= 0:
        return float("inf")

    if speed_rpm <= 0:
        return float("inf")

    return (
        1.0e6
        / (60.0 * speed_rpm)
        * (C_N / P_N) ** 3
    )


# ============================================================
# STATIC SAFETY
# ============================================================

def _static_safety(
    C0_N: float,
    P0_N: float,
) -> float:

    if P0_N <= 0:
        return float("inf")

    return C0_N / P0_N


# ============================================================
# MAIN CALCULATION
# ============================================================

def evaluate_output_system(
    inp: OutputSystemInput,
    material: OutputShaftMaterial,
    bearing_A: OutputBearingSpec,
    bearing_B: OutputBearingSpec,
    cfg: OutputSystemConfig,
) -> OutputSystemResult:

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    if inp.external_radial_load_N < 0:
        raise ValueError(
            "External radial load cannot be negative."
        )

    if material.Sy_MPa <= 0:
        raise ValueError(
            "Output-shaft yield strength must be > 0."
        )

    if cfg.shaft_safety_factor <= 0:
        raise ValueError(
            "Shaft safety factor must be > 0."
        )

    if cfg.inner_ring_spacer_mm < 0:
        raise ValueError(
            "Inner-ring spacer length cannot be negative."
        )

    if cfg.load_overhang_mm < 0:
        raise ValueError(
            "Load overhang cannot be negative."
        )

    if cfg.required_bearing_life_h <= 0:
        raise ValueError(
            "Required bearing life must be > 0."
        )

    if cfg.min_static_safety_factor <= 0:
        raise ValueError(
            "Minimum static safety factor must be > 0."
        )

    for bearing in (bearing_A, bearing_B):

        if bearing.bore_mm <= 0:
            raise ValueError(
                "Bearing bore must be > 0."
            )

        if bearing.width_mm <= 0:
            raise ValueError(
                "Bearing width must be > 0."
            )

        if bearing.C_N <= 0 or bearing.C0_N <= 0:
            raise ValueError(
                "Bearing ratings must be > 0."
            )

        if bearing.limiting_speed_rpm <= 0:
            raise ValueError(
                "Bearing limiting speed must be > 0."
            )

    # ========================================================
    # 1. BEARING CENTER SPACING
    #
    # L_o =
    # B_A/2 + L_s + B_B/2
    # ========================================================

    bearing_spacing_mm = (
        bearing_A.width_mm / 2.0
        +
        cfg.inner_ring_spacer_mm
        +
        bearing_B.width_mm / 2.0
    )

    load_overhang_mm = (
        cfg.load_overhang_mm
    )

    if bearing_spacing_mm <= 0:
        raise ValueError(
            "Calculated bearing spacing must be > 0."
        )

    # ========================================================
    # 2. BEARING REACTIONS
    #
    # Overhung radial load beyond Bearing B:
    #
    # R_A = -F_J * e_o/L_o
    #
    # R_B = F_J * (L_o + e_o)/L_o
    # ========================================================

    F_J = (
        inp.external_radial_load_N
    )

    reaction_A_N = (
        -F_J
        * load_overhang_mm
        / bearing_spacing_mm
    )

    reaction_B_N = (
        F_J
        * (
            bearing_spacing_mm
            +
            load_overhang_mm
        )
        / bearing_spacing_mm
    )

    # ========================================================
    # 3. MAXIMUM SHAFT BENDING MOMENT
    #
    # M_max = F_J * e_o
    # ========================================================

    max_bending_moment_Nmm = (
        F_J
        * load_overhang_mm
    )

    # ========================================================
    # 4. OUTPUT TORQUE
    #
    # Convert N.m -> N.mm
    # ========================================================

    torque_Nmm = (
        abs(inp.T_c_nm)
        * 1000.0
    )

    # ========================================================
    # 5. THEORETICAL MINIMUM SHAFT DIAMETER
    #
    # sigma_b = 32*M/(pi*d^3)
    #
    # tau = 16*T/(pi*d^3)
    #
    # sigma_VM =
    # sqrt(sigma_b^2 + 3*tau^2)
    #
    # resulting:
    #
    # d_min =
    # [
    #   16*n/(pi*Sy)
    #   *
    #   sqrt(4*M^2 + 3*T^2)
    # ]^(1/3)
    # ========================================================

    combined_load_term = sqrt(
        4.0 * max_bending_moment_Nmm**2
        +
        3.0 * torque_Nmm**2
    )

    if combined_load_term == 0:

        theoretical_min_diameter_mm = 0.0

    else:

        theoretical_min_diameter_mm = (
            (
                16.0
                * cfg.shaft_safety_factor
                / (
                    pi
                    * material.Sy_MPa
                )
            )
            * combined_load_term
        ) ** (1.0 / 3.0)

    # ========================================================
    # 6. COMMON BEARING BORE / SHAFT JOURNAL
    #
    # Both seats use the same diameter.
    # ========================================================

    same_bore = isclose(
        bearing_A.bore_mm,
        bearing_B.bore_mm,
        rel_tol=0.0,
        abs_tol=1e-9,
    )

    # Use A only after same-bore check.
    actual_shaft_diameter_mm = (
        bearing_A.bore_mm
    )

    # ========================================================
    # 7. ACTUAL BENDING STRESS
    # ========================================================

    bending_stress_MPa = (
        32.0
        * max_bending_moment_Nmm
        /
        (
            pi
            * actual_shaft_diameter_mm**3
        )
    )

    # ========================================================
    # 8. ACTUAL TORSIONAL SHEAR STRESS
    # ========================================================

    shear_stress_MPa = (
        16.0
        * torque_Nmm
        /
        (
            pi
            * actual_shaft_diameter_mm**3
        )
    )

    # ========================================================
    # 9. ACTUAL VON MISES STRESS
    # ========================================================

    von_mises_stress_MPa = sqrt(
        bending_stress_MPa**2
        +
        3.0 * shear_stress_MPa**2
    )

    # ========================================================
    # 10. ACHIEVED SHAFT SAFETY FACTOR
    # ========================================================

    if von_mises_stress_MPa > 0:

        achieved_shaft_safety_factor = (
            material.Sy_MPa
            /
            von_mises_stress_MPa
        )

    else:

        achieved_shaft_safety_factor = (
            float("inf")
        )

    # ========================================================
    # 11. BEARING EQUIVALENT DYNAMIC LOADS
    #
    # Radial only:
    #
    # P = |R|
    # ========================================================

    P_A_N = abs(
        reaction_A_N
    )

    P_B_N = abs(
        reaction_B_N
    )

    # ========================================================
    # 12. STATIC EQUIVALENT LOAD
    # ========================================================

    P0_A_N = P_A_N
    P0_B_N = P_B_N

    # ========================================================
    # 13. BALL-BEARING L10 LIFE
    #
    # p = 3
    # ========================================================

    speed_rpm = abs(
        inp.n_c_rpm
    )

    L10h_A = (
        _ball_bearing_life_hours(
            bearing_A.C_N,
            P_A_N,
            speed_rpm,
        )
    )

    L10h_B = (
        _ball_bearing_life_hours(
            bearing_B.C_N,
            P_B_N,
            speed_rpm,
        )
    )

    # ========================================================
    # 14. BEARING STATIC SAFETY
    # ========================================================

    s0_A = (
        _static_safety(
            bearing_A.C0_N,
            P0_A_N,
        )
    )

    s0_B = (
        _static_safety(
            bearing_B.C0_N,
            P0_B_N,
        )
    )

    # ========================================================
    # 15. BEARING SPEED UTILIZATION
    # ========================================================

    speed_ratio_A = (
        speed_rpm
        /
        bearing_A.limiting_speed_rpm
    )

    speed_ratio_B = (
        speed_rpm
        /
        bearing_B.limiting_speed_rpm
    )

    # ========================================================
    # 16. COMMON-BORE CHECK
    # ========================================================

    if not same_bore:

        return _build_result(
            feasible=False,
            rejection_reason=(
                "output_bearings_do_not_have_common_bore"
            ),
            locals_dict=locals(),
        )

    # ========================================================
    # 17. BEARING BORE / SHAFT DIAMETER CHECK
    # ========================================================

    if (
        actual_shaft_diameter_mm
        <
        theoretical_min_diameter_mm
    ):

        return _build_result(
            feasible=False,
            rejection_reason=(
                "bearing_bore_below_required_output_shaft_diameter"
            ),
            locals_dict=locals(),
        )

    # ========================================================
    # 18. ACTUAL SHAFT SAFETY CHECK
    # ========================================================

    if (
        achieved_shaft_safety_factor
        <
        cfg.shaft_safety_factor
    ):

        return _build_result(
            feasible=False,
            rejection_reason=(
                "output_shaft_safety_below_requirement"
            ),
            locals_dict=locals(),
        )

    # ========================================================
    # 19. BEARING LIFE CHECK
    # ========================================================

    if (
        L10h_A
        <
        cfg.required_bearing_life_h
    ):

        return _build_result(
            feasible=False,
            rejection_reason=(
                "output_bearing_A_life_below_requirement"
            ),
            locals_dict=locals(),
        )

    if (
        L10h_B
        <
        cfg.required_bearing_life_h
    ):

        return _build_result(
            feasible=False,
            rejection_reason=(
                "output_bearing_B_life_below_requirement"
            ),
            locals_dict=locals(),
        )

    # ========================================================
    # 20. STATIC SAFETY CHECK
    # ========================================================

    if (
        s0_A
        <
        cfg.min_static_safety_factor
    ):

        return _build_result(
            feasible=False,
            rejection_reason=(
                "output_bearing_A_static_safety_below_requirement"
            ),
            locals_dict=locals(),
        )

    if (
        s0_B
        <
        cfg.min_static_safety_factor
    ):

        return _build_result(
            feasible=False,
            rejection_reason=(
                "output_bearing_B_static_safety_below_requirement"
            ),
            locals_dict=locals(),
        )

    # ========================================================
    # 21. SPEED CHECK
    # ========================================================

    if (
        speed_rpm
        >
        bearing_A.limiting_speed_rpm
    ):

        return _build_result(
            feasible=False,
            rejection_reason=(
                "output_bearing_A_speed_exceeds_limit"
            ),
            locals_dict=locals(),
        )

    if (
        speed_rpm
        >
        bearing_B.limiting_speed_rpm
    ):

        return _build_result(
            feasible=False,
            rejection_reason=(
                "output_bearing_B_speed_exceeds_limit"
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
) -> OutputSystemResult:

    L = locals_dict

    return OutputSystemResult(
        feasible=feasible,
        rejection_reason=rejection_reason,

        material_name=L["material"].name,

        bearing_A_designation=(
            L["bearing_A"].designation
        ),

        bearing_B_designation=(
            L["bearing_B"].designation
        ),

        bearing_spacing_mm=L[
            "bearing_spacing_mm"
        ],

        load_overhang_mm=L[
            "load_overhang_mm"
        ],

        reaction_A_N=L[
            "reaction_A_N"
        ],

        reaction_B_N=L[
            "reaction_B_N"
        ],

        max_bending_moment_Nmm=L[
            "max_bending_moment_Nmm"
        ],

        torque_Nmm=L[
            "torque_Nmm"
        ],

        theoretical_min_diameter_mm=L[
            "theoretical_min_diameter_mm"
        ],

        actual_shaft_diameter_mm=L[
            "actual_shaft_diameter_mm"
        ],

        bending_stress_MPa=L[
            "bending_stress_MPa"
        ],

        shear_stress_MPa=L[
            "shear_stress_MPa"
        ],

        von_mises_stress_MPa=L[
            "von_mises_stress_MPa"
        ],

        achieved_shaft_safety_factor=L[
            "achieved_shaft_safety_factor"
        ],

        P_A_N=L["P_A_N"],
        P_B_N=L["P_B_N"],

        P0_A_N=L["P0_A_N"],
        P0_B_N=L["P0_B_N"],

        L10h_A=L["L10h_A"],
        L10h_B=L["L10h_B"],

        s0_A=L["s0_A"],
        s0_B=L["s0_B"],

        speed_ratio_A=L[
            "speed_ratio_A"
        ],

        speed_ratio_B=L[
            "speed_ratio_B"
        ],

        bearing_bore_mm=L[
            "actual_shaft_diameter_mm"
        ],
    )


def result_to_dict(
    result: OutputSystemResult
) -> dict:

    return asdict(result)