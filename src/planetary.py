"""
PLANETARY GEARSET GEOMETRY & KINEMATICS

Architecture:
    Sun     = input
    Ring    = fixed
    Carrier = output

INPUTS
-------
Iterated design variables:
    z_s                 Sun gear tooth count [-]
    z_p                 Planet gear tooth count [-]
    n_planets           Number of planets [-]
    module_mm           Gear module [mm]

Actuator requirements:
    output_speed_rpm    Required carrier/output speed [rpm]
    output_torque_nm    Required carrier/output torque [N.m]

Configuration parameters:
    efficiency          Preliminary gearbox efficiency [-]
    ratio_min           Minimum allowed gear ratio [-]
    ratio_max           Maximum allowed gear ratio [-]
    min_planet_clearance_mm
                        Minimum adjacent-planet clearance [mm]

OUTPUTS
-------
Geometry:
    z_r                         Ring gear tooth count [-]
    d_s_mm                      Sun pitch diameter [mm]
    d_p_mm                      Planet pitch diameter [mm]
    d_r_mm                      Ring pitch diameter [mm]
    d_ap_mm                     Planet outside diameter [mm]
    center_distance_mm          Sun-to-planet center distance [mm]
    planet_center_spacing_mm    Adjacent planet-center spacing [mm]
    planet_clearance_mm         Adjacent planet physical clearance [mm]

Kinematics:
    ratio                       Planetary reduction ratio [-]
    n_s_rpm                     Sun/input speed [rpm]
    n_p_rpm                     Planet absolute rotational speed [rpm]
    n_c_rpm                     Carrier/output speed [rpm]

Torques:
    T_s_ideal_nm                Ideal sun/input torque [N.m]
    T_s_design_nm               Input torque including gearbox efficiency [N.m]
    T_c_nm                      Carrier/output torque [N.m]
    T_r_ideal_nm                Ideal fixed-ring reaction torque [N.m]

Constraint results:
    assembly_condition_value    (Z_s + Z_r) / N_planets
    feasible                    True/False
    rejection_reason            Exact reason if rejected

THIS MODULE CHECKS
------------------
    1. Valid input values
    2. Gear-ratio range
    3. Equal planet assembly/phasing condition
    4. Adjacent planet clearance

NOT CHECKED HERE
----------------
    Motor compatibility
    Stator-bore packaging
    Gear tooth strength
    Bearings / shafts / carrier / ring structural strength
"""



from dataclasses import dataclass, asdict
from math import pi, sin
from typing import Optional


# ============================================================
# INPUT / CONFIG DATA
# ============================================================

@dataclass(frozen=True)
class PlanetaryInput:
    # Iterated design variables
    z_s: int
    z_p: int
    n_planets: int
    module_mm: float

    # Fixed actuator requirements
    output_speed_rpm: float
    output_torque_nm: float

    # Preliminary gearbox efficiency
    efficiency: float


@dataclass(frozen=True)
class PlanetaryConstraints:
    ratio_min: float
    ratio_max: float

    # Minimum physical clearance between adjacent planet ODs
    min_planet_clearance_mm: float


# ============================================================
# OUTPUT DATA
# ============================================================

@dataclass
class PlanetaryResult:
    feasible: bool
    rejection_reason: Optional[str]

    # Original design variables
    z_s: int
    z_p: int
    z_r: Optional[int]
    n_planets: int
    module_mm: float

    # Kinematics
    ratio: Optional[float]
    n_s_rpm: Optional[float]
    n_p_rpm: Optional[float]
    n_c_rpm: float

    # Torques
    T_s_ideal_nm: Optional[float]
    T_s_design_nm: Optional[float]
    T_c_nm: float
    T_r_ideal_nm: Optional[float]

    # Geometry
    d_s_mm: Optional[float]
    d_p_mm: Optional[float]
    d_r_mm: Optional[float]
    d_ap_mm: Optional[float]

    center_distance_mm: Optional[float]
    planet_center_spacing_mm: Optional[float]
    planet_clearance_mm: Optional[float]

    # Constraint bookkeeping
    assembly_condition_value: Optional[float]


# ============================================================
# MAIN CALCULATION
# ============================================================

def evaluate_planetary(
    inp: PlanetaryInput,
    limits: PlanetaryConstraints
) -> PlanetaryResult:
    """
    Evaluate one simple planetary candidate.

    Architecture:
        Sun     = input
        Ring    = fixed
        Carrier = output

    This module performs only:
        - planetary geometry
        - speed ratio
        - member speeds
        - preliminary torque mapping
        - equally spaced planet assembly condition
        - adjacent planet clearance

    Motor packaging is intentionally handled later in
    motor_compatibility.py.
    """

    # --------------------------------------------------------
    # Basic input validation
    # --------------------------------------------------------

    if inp.z_s <= 0 or inp.z_p <= 0:
        return _reject(inp, "invalid_tooth_count")

    if inp.n_planets < 2:
        return _reject(inp, "invalid_planet_count")

    if inp.module_mm <= 0:
        return _reject(inp, "invalid_module")

    if not (0 < inp.efficiency <= 1):
        return _reject(inp, "invalid_efficiency")

    # ========================================================
    # 1. RING TOOTH COUNT
    # Zr = Zs + 2 Zp
    # ========================================================

    z_r = inp.z_s + 2 * inp.z_p

    # ========================================================
    # 2. GEAR RATIO
    # fixed ring, sun input, carrier output
    #
    # i = ns / nc
    #   = 1 + Zr/Zs
    # ========================================================

    ratio = 1.0 + z_r / inp.z_s

    if ratio < limits.ratio_min:
        return _reject(
            inp,
            "ratio_below_minimum",
            z_r=z_r,
            ratio=ratio
        )

    if ratio > limits.ratio_max:
        return _reject(
            inp,
            "ratio_above_maximum",
            z_r=z_r,
            ratio=ratio
        )

    # ========================================================
    # 3. MEMBER SPEEDS
    # ========================================================

    n_c = inp.output_speed_rpm

    # ns = i * nc
    n_s = ratio * n_c

    # Planet speed:
    #
    # np = nc - (Zs/Zp)(ns - nc)
    #
    # Signed value is retained because the planet can spin
    # opposite to the sun in the carrier reference frame.
    n_p = (
        n_c
        - (inp.z_s / inp.z_p) * (n_s - n_c)
    )

    # ========================================================
    # 4. TORQUE MAPPING
    # ========================================================

    T_c = inp.output_torque_nm

    # Ideal sun/input torque:
    T_s_ideal = T_c / ratio

    # Design motor/input torque including lumped gearbox loss:
    T_s_design = T_c / (inp.efficiency * ratio)

    # Ideal ring reaction torque:
    #
    # Tr = Tc - Ts
    #    = (i - 1) Ts
    #
    # Keep this explicitly IDEAL because a lumped efficiency
    # model does not uniquely distribute internal loss torques.
    T_r_ideal = T_c - T_s_ideal

    # ========================================================
    # 5. PITCH DIAMETERS
    #
    # d = m Z
    # ========================================================

    d_s = inp.module_mm * inp.z_s
    d_p = inp.module_mm * inp.z_p
    d_r = inp.module_mm * z_r

    # Standard full-depth external planet outside diameter
    d_ap = inp.module_mm * (inp.z_p + 2)

    # ========================================================
    # 6. PLANET CENTER DISTANCE
    #
    # a = (ds + dp)/2
    # ========================================================

    a = (d_s + d_p) / 2.0

    # ========================================================
    # 7. EQUALLY SPACED PLANET ASSEMBLY CONDITION
    #
    # (Zs + Zr) / Nplanets must be integer
    # ========================================================

    assembly_value = (
        (inp.z_s + z_r) / inp.n_planets
    )

    if (inp.z_s + z_r) % inp.n_planets != 0:
        return _reject(
            inp,
            "planet_assembly_condition_failed",
            z_r=z_r,
            ratio=ratio,
            n_s=n_s,
            n_p=n_p,
            T_s_ideal=T_s_ideal,
            T_s_design=T_s_design,
            T_r_ideal=T_r_ideal,
            d_s=d_s,
            d_p=d_p,
            d_r=d_r,
            d_ap=d_ap,
            a=a,
            assembly_value=assembly_value
        )

    # ========================================================
    # 8. ADJACENT PLANET CLEARANCE
    #
    # Lpp = 2 a sin(pi/Nplanets)
    #
    # Cpp = Lpp - da,p
    # ========================================================

    planet_center_spacing = (
        2.0
        * a
        * sin(pi / inp.n_planets)
    )

    planet_clearance = (
        planet_center_spacing
        - d_ap
    )

    if planet_clearance < limits.min_planet_clearance_mm:
        return _reject(
            inp,
            "planet_clearance_below_minimum",
            z_r=z_r,
            ratio=ratio,
            n_s=n_s,
            n_p=n_p,
            T_s_ideal=T_s_ideal,
            T_s_design=T_s_design,
            T_r_ideal=T_r_ideal,
            d_s=d_s,
            d_p=d_p,
            d_r=d_r,
            d_ap=d_ap,
            a=a,
            assembly_value=assembly_value,
            planet_center_spacing=planet_center_spacing,
            planet_clearance=planet_clearance
        )

    # ========================================================
    # SUCCESS
    # ========================================================

    return PlanetaryResult(
        feasible=True,
        rejection_reason=None,

        z_s=inp.z_s,
        z_p=inp.z_p,
        z_r=z_r,
        n_planets=inp.n_planets,
        module_mm=inp.module_mm,

        ratio=ratio,
        n_s_rpm=n_s,
        n_p_rpm=n_p,
        n_c_rpm=n_c,

        T_s_ideal_nm=T_s_ideal,
        T_s_design_nm=T_s_design,
        T_c_nm=T_c,
        T_r_ideal_nm=T_r_ideal,

        d_s_mm=d_s,
        d_p_mm=d_p,
        d_r_mm=d_r,
        d_ap_mm=d_ap,

        center_distance_mm=a,
        planet_center_spacing_mm=planet_center_spacing,
        planet_clearance_mm=planet_clearance,

        assembly_condition_value=assembly_value
    )


# ============================================================
# REJECTION HELPER
# ============================================================

def _reject(
    inp: PlanetaryInput,
    reason: str,

    z_r=None,
    ratio=None,
    n_s=None,
    n_p=None,

    T_s_ideal=None,
    T_s_design=None,
    T_r_ideal=None,

    d_s=None,
    d_p=None,
    d_r=None,
    d_ap=None,

    a=None,
    assembly_value=None,

    planet_center_spacing=None,
    planet_clearance=None
) -> PlanetaryResult:

    return PlanetaryResult(
        feasible=False,
        rejection_reason=reason,

        z_s=inp.z_s,
        z_p=inp.z_p,
        z_r=z_r,
        n_planets=inp.n_planets,
        module_mm=inp.module_mm,

        ratio=ratio,
        n_s_rpm=n_s,
        n_p_rpm=n_p,
        n_c_rpm=inp.output_speed_rpm,

        T_s_ideal_nm=T_s_ideal,
        T_s_design_nm=T_s_design,
        T_c_nm=inp.output_torque_nm,
        T_r_ideal_nm=T_r_ideal,

        d_s_mm=d_s,
        d_p_mm=d_p,
        d_r_mm=d_r,
        d_ap_mm=d_ap,

        center_distance_mm=a,
        planet_center_spacing_mm=planet_center_spacing,
        planet_clearance_mm=planet_clearance,

        assembly_condition_value=assembly_value
    )


# ============================================================
# OPTIONAL DICTIONARY CONVERSION FOR CSV / JSON
# ============================================================

def result_to_dict(result: PlanetaryResult) -> dict:
    return asdict(result)