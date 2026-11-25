"""
ROTOR DRIVE PLATE + SUN/ROTOR SUPPORT BEARINGS

Purpose:
    Size the integral rotor drive plate and evaluate the two bearings
    supporting the rotor/sun-shaft rotating assembly.

Architecture:
    Rotor
      -> annular rotor drive plate
      -> integral hub
      -> integral sun shaft

    Bearing A = rear / rotor-side support
                non-locating bearing

    Bearing B = sun-side support
                locating bearing

Assumptions:
    - Drive plate, hub and sun shaft are treated as one rigid component.
    - Hub diameter equals the previously sized sun-shaft diameter:
          d_h = d_shaft
    - Drive plate OD equals motor rotor OD.
    - OEM rotor bolt pattern is fixed and is NOT designed here.
    - Bearing loads are radial only.
    - Gravity loading is used for the preliminary bearing reaction model.
    - Bearing spacing and CG location are preliminary packaging values.
      They are replaced later using final CAD geometry.

INPUTS
------
From previous modules / motor data:
    T_s_nm                       Sun/input torque [N.m]
    d_shaft_mm                   Required sun-shaft diameter [mm]
    n_s_rpm                      Sun/rotor speed [rpm]
    rotor_outer_diameter_mm      Rotor/drive-plate OD [mm]

Preliminary supported mass model:
    supported_rotating_mass_kg   Rotating mass supported by bearings [kg]
    bearing_spacing_mm           Bearing center spacing L_B [mm]
    cg_position_mm               CG distance from Bearing A, x_G [mm]

Material:
    name                         Material designation
    Sy_MPa                       Yield strength [MPa]
    density_kg_m3                Density [kg/m^3]

Bearing A and B catalogue data:
    designation
    bore_mm
    outer_diameter_mm
    width_mm
    C_N                          Basic dynamic load rating [N]
    C0_N                         Basic static load rating [N]
    limiting_speed_rpm
    mass_kg

Configuration:
    plate_safety_factor          Required plate stress safety factor [-]
    required_bearing_life_h      Required L10 bearing life [h]
    min_static_safety_factor     Minimum bearing static safety s0 [-]
    gravity_m_s2                 Gravity [m/s^2]

OUTPUTS
-------
Drive plate:
    hub_diameter_mm
    plate_outer_diameter_mm
    plate_thickness_mm
    plate_mass_kg

Hub sanity check:
    hub_shear_stress_MPa
    hub_von_mises_MPa
    hub_yield_safety_factor

Bearing reactions:
    total_weight_N
    reaction_A_N
    reaction_B_N

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

Constraint result:
    feasible
    rejection_reason

HARD CHECKS
-----------
    1. Bearing bore >= required structural shaft diameter
    2. Bearing A dynamic life
    3. Bearing B dynamic life
    4. Bearing A static safety
    5. Bearing B static safety
    6. Bearing A limiting speed
    7. Bearing B limiting speed

NOT INCLUDED HERE
-----------------
    OEM rotor-bolt design
    Exact bearing fits
    Axial retention shoulders
    Final bearing spacing from CAD
    Final CG calculation
    Shoulder stress concentrations
"""

from dataclasses import dataclass, asdict
from math import pi, sqrt
from typing import Optional


# ============================================================
# MATERIAL
# ============================================================

@dataclass(frozen=True)
class RotorSupportMaterial:
    name: str
    Sy_MPa: float
    density_kg_m3: float


# ============================================================
# BALL BEARING CATALOGUE ENTRY
# ============================================================

@dataclass(frozen=True)
class BallBearingSpec:
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
class RotorSupportInput:

    # Torque / shaft
    T_s_nm: float
    d_shaft_mm: float

    # Speed
    n_s_rpm: float

    # Rotor / drive plate geometry
    rotor_outer_diameter_mm: float

    # Preliminary supported rotating mass
    supported_rotating_mass_kg: float

    # Preliminary bearing geometry
    bearing_spacing_mm: float
    cg_position_mm: float


# ============================================================
# CONFIGURATION
# ============================================================

@dataclass(frozen=True)
class RotorSupportConfig:

    plate_safety_factor: float

    required_bearing_life_h: float
    min_static_safety_factor: float

    gravity_m_s2: float = 9.81


# ============================================================
# OUTPUT
# ============================================================

@dataclass
class RotorSupportResult:

    feasible: bool
    rejection_reason: Optional[str]

    material_name: str

    bearing_A_designation: str
    bearing_B_designation: str

    # Plate
    hub_diameter_mm: float
    plate_outer_diameter_mm: float
    plate_thickness_mm: float
    plate_mass_kg: float

    # Hub sanity check
    hub_shear_stress_MPa: float
    hub_von_mises_MPa: float
    hub_yield_safety_factor: float

    # Bearing loads
    total_weight_N: float
    reaction_A_N: float
    reaction_B_N: float

    P_A_N: float
    P_B_N: float

    P0_A_N: float
    P0_B_N: float

    # Bearing life
    L10h_A: float
    L10h_B: float

    # Static safety
    s0_A: float
    s0_B: float

    # Speed
    speed_ratio_A: float
    speed_ratio_B: float

    # Actual bearing seat diameters
    bearing_A_bore_mm: float
    bearing_B_bore_mm: float


# ============================================================
# BALL BEARING LIFE HELPER
# ============================================================

def _ball_bearing_life_hours(
    C_N: float,
    P_N: float,
    speed_rpm: float,
) -> float:

    # No load -> effectively infinite calculated life
    if P_N <= 0:
        return float("inf")

    # No rotation -> life in operating hours is not meaningful
    # from the standard revolution-based equation.
    if speed_rpm <= 0:
        return float("inf")

    return (
        1.0e6
        / (60.0 * speed_rpm)
        * (C_N / P_N) ** 3
    )


# ============================================================
# STATIC SAFETY HELPER
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

def evaluate_rotor_support(
    inp: RotorSupportInput,
    material: RotorSupportMaterial,
    bearing_A: BallBearingSpec,
    bearing_B: BallBearingSpec,
    cfg: RotorSupportConfig,
) -> RotorSupportResult:

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    if inp.d_shaft_mm <= 0:
        raise ValueError(
            "Sun-shaft diameter must be > 0."
        )

    if inp.rotor_outer_diameter_mm <= 0:
        raise ValueError(
            "Rotor outer diameter must be > 0."
        )

    if (
        inp.rotor_outer_diameter_mm
        <= inp.d_shaft_mm
    ):
        raise ValueError(
            "Rotor OD must exceed hub/shaft diameter."
        )

    if inp.supported_rotating_mass_kg < 0:
        raise ValueError(
            "Supported rotating mass cannot be negative."
        )

    if inp.bearing_spacing_mm <= 0:
        raise ValueError(
            "Bearing spacing must be > 0."
        )

    if material.Sy_MPa <= 0:
        raise ValueError(
            "Material yield strength must be > 0."
        )

    if material.density_kg_m3 <= 0:
        raise ValueError(
            "Material density must be > 0."
        )

    if cfg.plate_safety_factor <= 0:
        raise ValueError(
            "Plate safety factor must be > 0."
        )

    if cfg.required_bearing_life_h <= 0:
        raise ValueError(
            "Required bearing life must be > 0."
        )

    if cfg.min_static_safety_factor <= 0:
        raise ValueError(
            "Minimum static safety factor must be > 0."
        )

    # ========================================================
    # 1. HUB DIAMETER
    #
    # d_h = d_shaft
    # ========================================================

    hub_diameter_mm = (
        inp.d_shaft_mm
    )

    plate_outer_diameter_mm = (
        inp.rotor_outer_diameter_mm
    )

    # Convert torque N.m -> N.mm
    T_Nmm = (
        abs(inp.T_s_nm)
        * 1000.0
    )

    # ========================================================
    # 2. DRIVE-PLATE THICKNESS
    #
    # tau_p,max =
    # 2*T / (pi*d_h^2*t_p)
    #
    # sigma_VM = sqrt(3)*tau
    #
    # Require:
    #
    # sigma_VM <= Sy/n_p
    #
    # therefore:
    #
    # t_p >=
    # 2*sqrt(3)*n_p*T
    # /
    # (pi*d_h^2*Sy)
    # ========================================================

    if T_Nmm == 0:

        plate_thickness_mm = 0.0

    else:

        plate_thickness_mm = (
            2.0
            * sqrt(3.0)
            * cfg.plate_safety_factor
            * T_Nmm
            /
            (
                pi
                * hub_diameter_mm**2
                * material.Sy_MPa
            )
        )

    # ========================================================
    # 3. DRIVE-PLATE MASS
    #
    # m_p =
    # rho * pi/4 * (D^2 - d_h^2) * t_p
    #
    # Convert mm -> m for volume.
    # ========================================================

    D_m = (
        plate_outer_diameter_mm
        / 1000.0
    )

    d_h_m = (
        hub_diameter_mm
        / 1000.0
    )

    t_p_m = (
        plate_thickness_mm
        / 1000.0
    )

    plate_volume_m3 = (
        pi
        / 4.0
        * (
            D_m**2
            -
            d_h_m**2
        )
        * t_p_m
    )

    plate_mass_kg = (
        material.density_kg_m3
        * plate_volume_m3
    )

    # ========================================================
    # 4. HUB TORSION SANITY CHECK
    #
    # tau_h =
    # 16*T / (pi*d_h^3)
    # ========================================================

    hub_shear_stress_MPa = (
        16.0
        * T_Nmm
        /
        (
            pi
            * hub_diameter_mm**3
        )
    )

    # ========================================================
    # 5. HUB VON MISES STRESS
    #
    # sigma_VM = sqrt(3)*tau
    # ========================================================

    hub_von_mises_MPa = (
        sqrt(3.0)
        * hub_shear_stress_MPa
    )

    if hub_von_mises_MPa > 0:

        hub_yield_safety_factor = (
            material.Sy_MPa
            /
            hub_von_mises_MPa
        )

    else:

        hub_yield_safety_factor = (
            float("inf")
        )

    # ========================================================
    # 6. ROTATING WEIGHT
    #
    # W = M_rot*g
    # ========================================================

    total_weight_N = (
        inp.supported_rotating_mass_kg
        * cfg.gravity_m_s2
    )

    # ========================================================
    # 7. BEARING REACTIONS
    #
    # Bearing A at x = 0
    # Bearing B at x = L_B
    # CG at x = x_G
    #
    # R_A =
    # W*(L_B - x_G)/L_B
    #
    # R_B =
    # W*x_G/L_B
    # ========================================================

    reaction_A_N = (
        total_weight_N
        * (
            inp.bearing_spacing_mm
            -
            inp.cg_position_mm
        )
        /
        inp.bearing_spacing_mm
    )

    reaction_B_N = (
        total_weight_N
        * inp.cg_position_mm
        /
        inp.bearing_spacing_mm
    )

    # ========================================================
    # 8. EQUIVALENT DYNAMIC BEARING LOAD
    #
    # Radial-only preliminary model:
    #
    # P ~= |R|
    # ========================================================

    P_A_N = abs(
        reaction_A_N
    )

    P_B_N = abs(
        reaction_B_N
    )

    # ========================================================
    # 9. EQUIVALENT STATIC LOAD
    #
    # Radial-only:
    #
    # P0 ~= |R|
    # ========================================================

    P0_A_N = (
        P_A_N
    )

    P0_B_N = (
        P_B_N
    )

    # ========================================================
    # 10. BALL-BEARING L10 LIFE
    #
    # p = 3
    #
    # L10h =
    # 10^6 / (60*n)
    # *
    # (C/P)^3
    # ========================================================

    speed_rpm = abs(
        inp.n_s_rpm
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
    # 11. STATIC SAFETY
    #
    # s0 = C0/P0
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
    # 12. SPEED UTILIZATION
    #
    # U_n = n / n_lim
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
    # 13. BEARING BORE CHECK
    #
    # Selected bearing bore must be at least as large as the
    # required structural shaft diameter.
    # ========================================================

    if (
        bearing_A.bore_mm
        <
        inp.d_shaft_mm
    ):

        return _build_result(
            feasible=False,
            rejection_reason=(
                "bearing_A_bore_below_required_shaft_diameter"
            ),
            locals_dict=locals(),
        )

    if (
        bearing_B.bore_mm
        <
        inp.d_shaft_mm
    ):

        return _build_result(
            feasible=False,
            rejection_reason=(
                "bearing_B_bore_below_required_shaft_diameter"
            ),
            locals_dict=locals(),
        )

    # ========================================================
    # 14. BEARING LIFE CHECK
    # ========================================================

    if (
        L10h_A
        <
        cfg.required_bearing_life_h
    ):

        return _build_result(
            feasible=False,
            rejection_reason=(
                "bearing_A_life_below_requirement"
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
                "bearing_B_life_below_requirement"
            ),
            locals_dict=locals(),
        )

    # ========================================================
    # 15. STATIC SAFETY CHECK
    # ========================================================

    if (
        s0_A
        <
        cfg.min_static_safety_factor
    ):

        return _build_result(
            feasible=False,
            rejection_reason=(
                "bearing_A_static_safety_below_requirement"
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
                "bearing_B_static_safety_below_requirement"
            ),
            locals_dict=locals(),
        )

    # ========================================================
    # 16. SPEED CHECK
    # ========================================================

    if (
        speed_rpm
        >
        bearing_A.limiting_speed_rpm
    ):

        return _build_result(
            feasible=False,
            rejection_reason=(
                "bearing_A_speed_exceeds_limit"
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
                "bearing_B_speed_exceeds_limit"
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
) -> RotorSupportResult:

    L = locals_dict

    return RotorSupportResult(
        feasible=feasible,
        rejection_reason=rejection_reason,

        material_name=L["material"].name,

        bearing_A_designation=(
            L["bearing_A"].designation
        ),

        bearing_B_designation=(
            L["bearing_B"].designation
        ),

        hub_diameter_mm=L[
            "hub_diameter_mm"
        ],

        plate_outer_diameter_mm=L[
            "plate_outer_diameter_mm"
        ],

        plate_thickness_mm=L[
            "plate_thickness_mm"
        ],

        plate_mass_kg=L[
            "plate_mass_kg"
        ],

        hub_shear_stress_MPa=L[
            "hub_shear_stress_MPa"
        ],

        hub_von_mises_MPa=L[
            "hub_von_mises_MPa"
        ],

        hub_yield_safety_factor=L[
            "hub_yield_safety_factor"
        ],

        total_weight_N=L[
            "total_weight_N"
        ],

        reaction_A_N=L[
            "reaction_A_N"
        ],

        reaction_B_N=L[
            "reaction_B_N"
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

        bearing_A_bore_mm=(
            L["bearing_A"].bore_mm
        ),

        bearing_B_bore_mm=(
            L["bearing_B"].bore_mm
        ),
    )


def result_to_dict(
    result: RotorSupportResult
) -> dict:

    return asdict(result)