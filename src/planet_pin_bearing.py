"""
PLANET PIN + NEEDLE BEARING SIZING

Purpose:
    Evaluate one catalogue needle-roller bearing and its corresponding
    fixed cantilever planet pin.

Architecture:
    Carrier plate
        -> fixed cantilever planet pin
        -> needle roller bearing with inner ring
        -> rotating planet gear

Assumptions:
    - Pin is fixed to the carrier.
    - Planet rotates relative to the pin through the needle bearing.
    - Bearing bore defines the pin diameter:
          d_pin = bearing bore
    - Planet load acts approximately at the planet gear center plane.
    - Single-sided carrier -> pin is treated as a cantilever.
    - Pin loading includes bending + direct shear.
    - Spur gears -> no axial gear force.
    - Bearing equivalent radial load:
          P = P0 = F_pin

INPUTS
------
From gear_forces.py:
    F_pin_N                     Design planet-pin radial load [N]

From planetary.py:
    n_p_rpm                     Absolute planet rotational speed [rpm]
    n_c_rpm                     Carrier rotational speed [rpm]
    z_p                         Planet tooth count [-]
    module_mm                   Gear module [mm]

From gear design:
    face_width_mm               Gear face width b [mm]

From material catalogue:
    material name
    Sy_MPa                      Pin material yield strength [MPa]
    E_GPa                       Pin elastic modulus [GPa]

From needle-bearing catalogue:
    designation
    bore_mm                     Bearing bore / pin diameter [mm]
    outer_diameter_mm           Bearing OD [mm]
    width_mm                    Bearing width [mm]
    C_N                         Basic dynamic load rating [N]
    C0_N                        Basic static load rating [N]
    limiting_speed_rpm          Bearing limiting speed [rpm]
    mass_kg                     Bearing mass [kg]

Configuration:
    pin_safety_factor           Required pin static SF [-]
    max_pin_deflection_mm       Maximum allowed cantilever deflection [mm]
    max_pin_tilt_deg            Maximum allowed pin angular tilt [deg]

    carrier_planet_clearance_mm Axial carrier-to-planet clearance delta_c [mm]
    axial_bearing_clearance_mm  Required clearance on EACH side of bearing [mm]

    min_planet_root_ligament_mm Minimum radial material around bearing OD [mm]

    required_bearing_life_h     Required L10 bearing life [h]
    min_static_safety_factor    Required static bearing safety [-]

OUTPUTS
-------
Pin geometry:
    pin_diameter_mm
    load_lever_arm_mm

Pin loading:
    bending_moment_Nmm
    bending_stress_MPa
    shear_stress_MPa
    von_mises_stress_MPa
    pin_safety_factor

Pin stiffness:
    pin_deflection_mm
    pin_tilt_deg

Bearing:
    bearing_relative_speed_rpm
    bearing_speed_ratio
    bearing_dynamic_load_N
    bearing_static_load_N
    L10h
    static_safety_factor

Planet packaging:
    planet_root_diameter_mm
    available_radial_ligament_mm
    required_axial_space_mm

Overall:
    feasible
    rejection_reason

HARD CHECKS
-----------
    1. Bearing width fits inside planet face width
    2. Bearing OD fits inside planet root diameter
    3. Pin von Mises safety factor
    4. Pin deflection
    5. Pin tilt
    6. Bearing dynamic life
    7. Bearing static safety
    8. Bearing limiting speed

NOT INCLUDED HERE
-----------------
    Carrier plate pin-hole stress
    Pin engagement depth in carrier
    Pin retention detail
    Threads / circlips / end retainers
    Local stress concentration at pin root
"""

from dataclasses import dataclass, asdict
from math import pi, sqrt, radians, degrees
from typing import Optional


# ============================================================
# MATERIAL
# ============================================================

@dataclass(frozen=True)
class PinMaterial:
    name: str

    Sy_MPa: float
    E_GPa: float


# ============================================================
# NEEDLE BEARING CATALOGUE ENTRY
# ============================================================

@dataclass(frozen=True)
class NeedleBearingSpec:

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
class PlanetPinBearingInput:

    # Design load
    F_pin_N: float

    # Speeds
    n_p_rpm: float
    n_c_rpm: float

    # Planet geometry
    z_p: int
    module_mm: float
    face_width_mm: float


# ============================================================
# CONFIGURATION
# ============================================================

@dataclass(frozen=True)
class PlanetPinBearingConfig:

    # Pin strength
    pin_safety_factor: float

    # Pin stiffness
    max_pin_deflection_mm: float
    max_pin_tilt_deg: float

    # Axial geometry
    carrier_planet_clearance_mm: float
    axial_bearing_clearance_mm: float

    # Radial planet packaging
    min_planet_root_ligament_mm: float

    # Bearing requirements
    required_bearing_life_h: float
    min_static_safety_factor: float


# ============================================================
# OUTPUT
# ============================================================

@dataclass
class PlanetPinBearingResult:

    feasible: bool
    rejection_reason: Optional[str]

    material_name: str
    bearing_designation: str

    # Pin geometry
    pin_diameter_mm: float
    load_lever_arm_mm: float

    # Pin stress
    bending_moment_Nmm: float
    bending_stress_MPa: float
    shear_stress_MPa: float
    von_mises_stress_MPa: float
    pin_safety_factor: float

    # Pin stiffness
    pin_deflection_mm: float
    pin_tilt_deg: float

    # Bearing
    bearing_relative_speed_rpm: float
    bearing_speed_ratio: float

    bearing_dynamic_load_N: float
    bearing_static_load_N: float

    L10h: float
    static_safety_factor: float

    # Planet packaging
    planet_root_diameter_mm: float
    available_radial_ligament_mm: float

    bearing_width_mm: float
    required_axial_space_mm: float


# ============================================================
# BEARING LIFE HELPER
# ============================================================

def _roller_bearing_life_hours(
    C_N: float,
    P_N: float,
    speed_rpm: float,
) -> float:
    """
    Roller / needle bearing exponent:
        p = 10/3
    """

    if P_N <= 0:
        return float("inf")

    if speed_rpm <= 0:
        return float("inf")

    return (
        1.0e6
        / (60.0 * speed_rpm)
        * (C_N / P_N) ** (10.0 / 3.0)
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

def evaluate_planet_pin_bearing(
    inp: PlanetPinBearingInput,
    material: PinMaterial,
    bearing: NeedleBearingSpec,
    cfg: PlanetPinBearingConfig,
) -> PlanetPinBearingResult:

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    if inp.F_pin_N < 0:
        raise ValueError(
            "Planet-pin load cannot be negative."
        )

    if inp.z_p <= 0:
        raise ValueError(
            "Planet tooth count must be > 0."
        )

    if inp.module_mm <= 0:
        raise ValueError(
            "Gear module must be > 0."
        )

    if inp.face_width_mm <= 0:
        raise ValueError(
            "Gear face width must be > 0."
        )

    if material.Sy_MPa <= 0:
        raise ValueError(
            "Pin material yield strength must be > 0."
        )

    if material.E_GPa <= 0:
        raise ValueError(
            "Pin elastic modulus must be > 0."
        )

    if bearing.bore_mm <= 0:
        raise ValueError(
            "Bearing bore must be > 0."
        )

    if bearing.outer_diameter_mm <= 0:
        raise ValueError(
            "Bearing OD must be > 0."
        )

    if bearing.width_mm <= 0:
        raise ValueError(
            "Bearing width must be > 0."
        )

    if bearing.C_N <= 0 or bearing.C0_N <= 0:
        raise ValueError(
            "Bearing load ratings must be > 0."
        )

    if bearing.limiting_speed_rpm <= 0:
        raise ValueError(
            "Bearing limiting speed must be > 0."
        )

    if cfg.pin_safety_factor <= 0:
        raise ValueError(
            "Required pin safety factor must be > 0."
        )

    if cfg.max_pin_deflection_mm <= 0:
        raise ValueError(
            "Maximum pin deflection must be > 0."
        )

    if cfg.max_pin_tilt_deg <= 0:
        raise ValueError(
            "Maximum pin tilt must be > 0."
        )

    if cfg.carrier_planet_clearance_mm < 0:
        raise ValueError(
            "Carrier-to-planet clearance cannot be negative."
        )

    if cfg.axial_bearing_clearance_mm < 0:
        raise ValueError(
            "Axial bearing clearance cannot be negative."
        )

    if cfg.min_planet_root_ligament_mm < 0:
        raise ValueError(
            "Planet root ligament cannot be negative."
        )

    # ========================================================
    # 1. PIN DIAMETER FROM BEARING BORE
    #
    # d_pin = d_bearing,bore
    # ========================================================

    pin_diameter_mm = (
        bearing.bore_mm
    )

    # ========================================================
    # 2. LOAD LEVER ARM
    #
    # Load acts approximately at center of gear face:
    #
    # e = delta_c + b/2
    # ========================================================

    load_lever_arm_mm = (
        cfg.carrier_planet_clearance_mm
        +
        inp.face_width_mm / 2.0
    )

    # ========================================================
    # 3. CANTILEVER BENDING MOMENT
    #
    # M = F_pin * e
    # ========================================================

    bending_moment_Nmm = (
        inp.F_pin_N
        * load_lever_arm_mm
    )

    # ========================================================
    # 4. PIN BENDING STRESS
    #
    # sigma_b =
    # 32*M / (pi*d_pin^3)
    # ========================================================

    bending_stress_MPa = (
        32.0
        * bending_moment_Nmm
        /
        (
            pi
            * pin_diameter_mm**3
        )
    )

    # ========================================================
    # 5. DIRECT SHEAR STRESS
    #
    # tau =
    # 4*F_pin / (pi*d_pin^2)
    # ========================================================

    shear_stress_MPa = (
        4.0
        * inp.F_pin_N
        /
        (
            pi
            * pin_diameter_mm**2
        )
    )

    # ========================================================
    # 6. COMBINED VON MISES STRESS
    #
    # sigma_VM =
    # sqrt(sigma_b^2 + 3*tau^2)
    # ========================================================

    von_mises_stress_MPa = sqrt(
        bending_stress_MPa**2
        +
        3.0 * shear_stress_MPa**2
    )

    # ========================================================
    # 7. PIN SAFETY FACTOR
    #
    # n_pin = Sy / sigma_VM
    # ========================================================

    if von_mises_stress_MPa > 0:

        pin_safety_factor = (
            material.Sy_MPa
            /
            von_mises_stress_MPa
        )

    else:

        pin_safety_factor = (
            float("inf")
        )

    # ========================================================
    # 8. SECOND MOMENT OF AREA
    #
    # I = pi*d^4 / 64
    # ========================================================

    I_mm4 = (
        pi
        * pin_diameter_mm**4
        / 64.0
    )

    E_MPa = (
        material.E_GPa
        * 1000.0
    )

    # ========================================================
    # 9. CANTILEVER TIP DEFLECTION
    #
    # delta =
    # F*e^3 / (3EI)
    #
    # Equivalent:
    #
    # delta =
    # 64*F*e^3
    # /
    # (3*E*pi*d^4)
    # ========================================================

    pin_deflection_mm = (
        inp.F_pin_N
        * load_lever_arm_mm**3
        /
        (
            3.0
            * E_MPa
            * I_mm4
        )
    )

    # ========================================================
    # 10. CANTILEVER ANGULAR TILT
    #
    # theta =
    # F*e^2 / (2EI)
    #
    # Equivalent:
    #
    # theta =
    # 32*F*e^2
    # /
    # (E*pi*d^4)
    # ========================================================

    pin_tilt_rad = (
        inp.F_pin_N
        * load_lever_arm_mm**2
        /
        (
            2.0
            * E_MPa
            * I_mm4
        )
    )

    pin_tilt_deg = degrees(
        pin_tilt_rad
    )

    # ========================================================
    # 11. BEARING RELATIVE SPEED
    #
    # Pin rotates with carrier.
    #
    # n_B = |n_p - n_c|
    # ========================================================

    bearing_relative_speed_rpm = abs(
        inp.n_p_rpm
        -
        inp.n_c_rpm
    )

    # ========================================================
    # 12. BEARING EQUIVALENT LOADS
    #
    # Radial-only:
    #
    # P = P0 = F_pin
    # ========================================================

    bearing_dynamic_load_N = (
        inp.F_pin_N
    )

    bearing_static_load_N = (
        inp.F_pin_N
    )

    # ========================================================
    # 13. NEEDLE BEARING LIFE
    #
    # Roller bearing exponent:
    #
    # p = 10/3
    #
    # L10h =
    # 10^6/(60*n_B)
    # *
    # (C/P)^(10/3)
    # ========================================================

    L10h = (
        _roller_bearing_life_hours(
            bearing.C_N,
            bearing_dynamic_load_N,
            bearing_relative_speed_rpm,
        )
    )

    # ========================================================
    # 14. STATIC SAFETY
    #
    # s0 = C0/P0
    # ========================================================

    static_safety_factor = (
        _static_safety(
            bearing.C0_N,
            bearing_static_load_N,
        )
    )

    # ========================================================
    # 15. BEARING SPEED UTILIZATION
    #
    # U_n = n_B / n_lim
    # ========================================================

    bearing_speed_ratio = (
        bearing_relative_speed_rpm
        /
        bearing.limiting_speed_rpm
    )

    # ========================================================
    # 16. PLANET ROOT DIAMETER
    #
    # d_f,p ~= m(Z_p - 2.5)
    # ========================================================

    planet_root_diameter_mm = (
        inp.module_mm
        * (inp.z_p - 2.5)
    )

    if planet_root_diameter_mm <= 0:

        raise ValueError(
            "Calculated planet root diameter is non-positive."
        )

    # ========================================================
    # 17. ACTUAL RADIAL LIGAMENT AROUND BEARING
    #
    # t_lig,p =
    # (d_f,p - D_B)/2
    # ========================================================

    available_radial_ligament_mm = (
        planet_root_diameter_mm
        -
        bearing.outer_diameter_mm
    ) / 2.0

    # ========================================================
    # 18. REQUIRED AXIAL SPACE
    #
    # B_B + 2*delta_a <= b
    # ========================================================

    required_axial_space_mm = (
        bearing.width_mm
        +
        2.0
        * cfg.axial_bearing_clearance_mm
    )

    # ========================================================
    # 19. AXIAL PACKAGING CHECK
    # ========================================================

    if (
        required_axial_space_mm
        >
        inp.face_width_mm
    ):

        return _build_result(
            feasible=False,
            rejection_reason=(
                "bearing_width_exceeds_planet_face_width"
            ),
            locals_dict=locals(),
        )

    # ========================================================
    # 20. RADIAL PACKAGING CHECK
    #
    # D_B + 2*t_lig,min <= d_f,p
    # ========================================================

    if (
        available_radial_ligament_mm
        <
        cfg.min_planet_root_ligament_mm
    ):

        return _build_result(
            feasible=False,
            rejection_reason=(
                "bearing_OD_exceeds_planet_root_capacity"
            ),
            locals_dict=locals(),
        )

    # ========================================================
    # 21. PIN STRENGTH CHECK
    # ========================================================

    if (
        pin_safety_factor
        <
        cfg.pin_safety_factor
    ):

        return _build_result(
            feasible=False,
            rejection_reason=(
                "pin_static_safety_below_requirement"
            ),
            locals_dict=locals(),
        )

    # ========================================================
    # 22. PIN DEFLECTION CHECK
    # ========================================================

    if (
        pin_deflection_mm
        >
        cfg.max_pin_deflection_mm
    ):

        return _build_result(
            feasible=False,
            rejection_reason=(
                "pin_deflection_exceeds_limit"
            ),
            locals_dict=locals(),
        )

    # ========================================================
    # 23. PIN TILT CHECK
    # ========================================================

    if (
        pin_tilt_deg
        >
        cfg.max_pin_tilt_deg
    ):

        return _build_result(
            feasible=False,
            rejection_reason=(
                "pin_tilt_exceeds_limit"
            ),
            locals_dict=locals(),
        )

    # ========================================================
    # 24. BEARING LIFE CHECK
    # ========================================================

    if (
        L10h
        <
        cfg.required_bearing_life_h
    ):

        return _build_result(
            feasible=False,
            rejection_reason=(
                "needle_bearing_life_below_requirement"
            ),
            locals_dict=locals(),
        )

    # ========================================================
    # 25. BEARING STATIC CHECK
    # ========================================================

    if (
        static_safety_factor
        <
        cfg.min_static_safety_factor
    ):

        return _build_result(
            feasible=False,
            rejection_reason=(
                "needle_bearing_static_safety_below_requirement"
            ),
            locals_dict=locals(),
        )

    # ========================================================
    # 26. BEARING SPEED CHECK
    # ========================================================

    if (
        bearing_relative_speed_rpm
        >
        bearing.limiting_speed_rpm
    ):

        return _build_result(
            feasible=False,
            rejection_reason=(
                "needle_bearing_speed_exceeds_limit"
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
) -> PlanetPinBearingResult:

    L = locals_dict

    return PlanetPinBearingResult(
        feasible=feasible,
        rejection_reason=rejection_reason,

        material_name=L["material"].name,
        bearing_designation=L["bearing"].designation,

        pin_diameter_mm=L[
            "pin_diameter_mm"
        ],

        load_lever_arm_mm=L[
            "load_lever_arm_mm"
        ],

        bending_moment_Nmm=L[
            "bending_moment_Nmm"
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

        pin_safety_factor=L[
            "pin_safety_factor"
        ],

        pin_deflection_mm=L[
            "pin_deflection_mm"
        ],

        pin_tilt_deg=L[
            "pin_tilt_deg"
        ],

        bearing_relative_speed_rpm=L[
            "bearing_relative_speed_rpm"
        ],

        bearing_speed_ratio=L[
            "bearing_speed_ratio"
        ],

        bearing_dynamic_load_N=L[
            "bearing_dynamic_load_N"
        ],

        bearing_static_load_N=L[
            "bearing_static_load_N"
        ],

        L10h=L[
            "L10h"
        ],

        static_safety_factor=L[
            "static_safety_factor"
        ],

        planet_root_diameter_mm=L[
            "planet_root_diameter_mm"
        ],

        available_radial_ligament_mm=L[
            "available_radial_ligament_mm"
        ],

        bearing_width_mm=L[
            "bearing"
        ].width_mm,

        required_axial_space_mm=L[
            "required_axial_space_mm"
        ],
    )


def result_to_dict(
    result: PlanetPinBearingResult
) -> dict:

    return asdict(result)