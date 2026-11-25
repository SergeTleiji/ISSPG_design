"""
AGMA GEAR TOOTH STRENGTH

Purpose:
    Evaluate bending and contact/pitting strength of the planetary
    sun, planet, and ring gears.

INPUTS
------
From planetary.py:
    z_s                         Sun tooth count [-]
    z_p                         Planet tooth count [-]
    z_r                         Ring tooth count [-]
    module_mm                   Gear module [mm]

Search variable:
    face_width_mm               Gear face width b [mm]

From gear_forces.py:
    F_t_sp_N                    Sun-planet design tangential force [N]
    F_t_pr_N                    Planet-ring design tangential force [N]
    velocity_sp_mps             Sun-planet relative pitch velocity [m/s]
    velocity_pr_mps             Planet-ring relative pitch velocity [m/s]
    pressure_angle_deg          Pressure angle [deg]

From planetary geometry:
    d_s_mm                      Sun pitch diameter [mm]
    d_p_mm                      Planet pitch diameter [mm]

Candidate-specific AGMA bending geometry factors:
    YJ_sun_sp                   Sun, sun-planet mesh [-]
    YJ_planet_sp                Planet, sun-planet mesh [-]
    YJ_planet_pr                Planet, planet-ring mesh [-]
    YJ_ring_pr                  Ring, planet-ring mesh [-]

From material catalogue:
    E_GPa                       Elastic modulus [GPa]
    poisson                     Poisson ratio [-]
    St_MPa                      AGMA bending strength number [MPa]
    Sc_MPa                      AGMA contact strength number [MPa]

Configuration:
    Q_v                         Gear quality number [-]
    K_o                         Overload factor [-]
    K_s                         Size factor [-]
    K_H                         Load-distribution factor [-]
    Z_R                         Surface-condition factor [-]

    K_B_sun                     Sun rim factor [-]
    K_B_planet                  Planet rim factor [-]
    K_B_ring                    Ring rim factor [-]

    K_T                         Temperature factor [-]
    K_R                         Reliability factor [-]

    Y_N_*                       Bending stress-cycle factors [-]
    Y_I_*                       Reverse-bending factors [-]

    Z_N_*                       Contact stress-cycle factors [-]
    Z_W_*                       Hardness-ratio factors [-]

    min_bending_safety_factor   Required AGMA bending safety [-]
    min_contact_safety_factor   Required AGMA contact safety [-]

OUTPUTS
-------
Dynamic factors:
    K_v_sp
    K_v_pr

Pitting geometry:
    Z_I_sp
    Z_I_pr

Elastic coefficients:
    Z_E_sp
    Z_E_pr

Bending stresses:
    sigma_F_sun_MPa
    sigma_F_planet_sp_MPa
    sigma_F_planet_pr_MPa
    sigma_F_ring_MPa

Allowable bending stresses:
    sigma_F_allow_sun_MPa
    sigma_F_allow_planet_MPa
    sigma_F_allow_ring_MPa

Bending safety factors:
    S_F_sun
    S_F_planet_sp
    S_F_planet_pr
    S_F_ring
    S_F_governing
    governing_bending_location

Contact stresses:
    sigma_H_sp_MPa
    sigma_H_pr_MPa

Contact safety factors:
    S_H_sun_sp
    S_H_planet_sp
    S_H_planet_pr
    S_H_ring_pr
    S_H_governing
    governing_contact_location

Equivalent contact load safety:
    S_H_governing^2

Overall:
    feasible
    rejection_reason

IMPORTANT
---------
    F_t already contains K_gamma from gear_forces.py.

    DO NOT multiply by K_gamma again here.
"""

from dataclasses import dataclass, asdict
from math import cos, sin, radians, sqrt
from typing import Optional


# ============================================================
# MATERIAL
# ============================================================

@dataclass(frozen=True)
class GearMaterial:
    name: str

    elastic_modulus_GPa: float
    poisson_ratio: float

    # AGMA strength numbers, NOT yield/ultimate strengths
    St_MPa: float
    Sc_MPa: float


# ============================================================
# CANDIDATE-SPECIFIC GEOMETRY FACTORS
# ============================================================

@dataclass(frozen=True)
class GearGeometryFactors:

    # Bending geometry factors
    YJ_sun_sp: float
    YJ_planet_sp: float
    YJ_planet_pr: float
    YJ_ring_pr: float


# ============================================================
# INPUT
# ============================================================

@dataclass(frozen=True)
class GearStrengthInput:

    # Teeth
    z_s: int
    z_p: int
    z_r: int

    # Geometry
    module_mm: float
    face_width_mm: float

    d_s_mm: float
    d_p_mm: float

    pressure_angle_deg: float

    # Design tangential forces
    F_t_sp_N: float
    F_t_pr_N: float

    # Relative mesh velocities
    velocity_sp_mps: float
    velocity_pr_mps: float


# ============================================================
# CONFIGURATION
# ============================================================

@dataclass(frozen=True)
class GearStrengthConfig:

    # Manufacturing / load factors
    Q_v: float
    K_o: float
    K_s: float
    K_H: float
    Z_R: float

    # Rim-thickness factors
    K_B_sun: float
    K_B_planet: float
    K_B_ring: float

    # Allowable-stress modifiers
    K_T: float
    K_R: float

    # Bending stress-cycle factors
    Y_N_sun: float
    Y_N_planet: float
    Y_N_ring: float

    # Reverse-bending factors
    Y_I_sun: float
    Y_I_planet: float
    Y_I_ring: float

    # Contact stress-cycle factors
    Z_N_sun: float
    Z_N_planet: float
    Z_N_ring: float

    # Hardness-ratio factors
    Z_W_sun: float
    Z_W_planet: float
    Z_W_ring: float

    # Required safety factors
    min_bending_safety_factor: float
    min_contact_safety_factor: float


# ============================================================
# OUTPUT
# ============================================================

@dataclass
class GearStrengthResult:

    feasible: bool
    rejection_reason: Optional[str]

    # Dynamic factors
    K_v_sp: float
    K_v_pr: float

    # Contact geometry
    Z_I_sp: float
    Z_I_pr: float

    # Elastic coefficients
    Z_E_sp: float
    Z_E_pr: float

    # Bending stresses
    sigma_F_sun_MPa: float
    sigma_F_planet_sp_MPa: float
    sigma_F_planet_pr_MPa: float
    sigma_F_ring_MPa: float

    # Allowable bending stresses
    sigma_F_allow_sun_MPa: float
    sigma_F_allow_planet_MPa: float
    sigma_F_allow_ring_MPa: float

    # Bending safety factors
    S_F_sun: float
    S_F_planet_sp: float
    S_F_planet_pr: float
    S_F_ring: float

    S_F_governing: float
    governing_bending_location: str

    # Contact stresses
    sigma_H_sp_MPa: float
    sigma_H_pr_MPa: float

    # Contact allowable stresses
    sigma_H_allow_sun_MPa: float
    sigma_H_allow_planet_MPa: float
    sigma_H_allow_ring_MPa: float

    # Contact safety factors
    S_H_sun_sp: float
    S_H_planet_sp: float
    S_H_planet_pr: float
    S_H_ring_pr: float

    S_H_governing: float
    governing_contact_location: str

    # Load-equivalent contact safety
    S_H_squared: float

    # Governing load-style safety
    governing_load_safety: float

    # Material names
    sun_material: str
    planet_material: str
    ring_material: str


# ============================================================
# HELPERS
# ============================================================

def _dynamic_factor(Q_v: float, velocity_mps: float) -> float:
    """
    Shigley / AGMA dynamic-factor relation in SI units.

    B = 0.25(12 - Qv)^(2/3)
    A = 50 + 56(1 - B)

    Kv = [(A + sqrt(200*v))/A]^B
    """

    if not (3.0 <= Q_v <= 12.0):
        raise ValueError(
            "Q_v must lie between 3 and 12 for this dynamic-factor model."
        )

    if velocity_mps < 0:
        raise ValueError("Pitch-line velocity cannot be negative.")

    B = 0.25 * (12.0 - Q_v) ** (2.0 / 3.0)

    A = 50.0 + 56.0 * (1.0 - B)

    return (
        (A + sqrt(200.0 * velocity_mps))
        / A
    ) ** B


def _elastic_coefficient(
    material_1: GearMaterial,
    material_2: GearMaterial,
) -> float:
    """
    Elastic coefficient Z_E [sqrt(MPa)].

    E must be converted from GPa -> MPa.
    """

    E1 = material_1.elastic_modulus_GPa * 1000.0
    E2 = material_2.elastic_modulus_GPa * 1000.0

    nu1 = material_1.poisson_ratio
    nu2 = material_2.poisson_ratio

    denominator = (
        3.141592653589793
        * (
            (1.0 - nu1**2) / E1
            + (1.0 - nu2**2) / E2
        )
    )

    return sqrt(1.0 / denominator)


def _ZI_external_spur(
    z_1: int,
    z_2: int,
    pressure_angle_deg: float,
) -> float:
    """
    Pitting geometry factor for an external spur mesh.

    The smaller gear is treated as the pinion.

    Z_I =
        cos(phi)*sin(phi)/2
        *
        m_G/(m_G + 1)
    """

    z_small = min(z_1, z_2)
    z_large = max(z_1, z_2)

    m_G = z_large / z_small

    phi = radians(pressure_angle_deg)

    return (
        cos(phi)
        * sin(phi)
        / 2.0
        * m_G
        / (m_G + 1.0)
    )


def _ZI_internal_spur(
    z_pinion: int,
    z_internal: int,
    pressure_angle_deg: float,
) -> float:
    """
    Pitting geometry factor for an internal spur mesh.

    Z_I =
        cos(phi)*sin(phi)/2
        *
        m_G/(m_G - 1)
    """

    if z_internal <= z_pinion:
        raise ValueError(
            "Internal ring gear must have more teeth than the mating pinion."
        )

    m_G = z_internal / z_pinion

    phi = radians(pressure_angle_deg)

    return (
        cos(phi)
        * sin(phi)
        / 2.0
        * m_G
        / (m_G - 1.0)
    )


def _bending_allowable(
    material: GearMaterial,
    Y_N: float,
    Y_I: float,
    K_T: float,
    K_R: float,
) -> float:

    return (
        material.St_MPa
        * Y_N
        * Y_I
        / (K_T * K_R)
    )


def _contact_allowable(
    material: GearMaterial,
    Z_N: float,
    Z_W: float,
    K_T: float,
    K_R: float,
) -> float:

    return (
        material.Sc_MPa
        * Z_N
        * Z_W
        / (K_T * K_R)
    )


# ============================================================
# MAIN CALCULATION
# ============================================================

def evaluate_gear_strength(
    inp: GearStrengthInput,
    geometry: GearGeometryFactors,
    sun_material: GearMaterial,
    planet_material: GearMaterial,
    ring_material: GearMaterial,
    cfg: GearStrengthConfig,
) -> GearStrengthResult:

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    if inp.module_mm <= 0:
        raise ValueError("Gear module must be > 0.")

    if inp.face_width_mm <= 0:
        raise ValueError("Gear face width must be > 0.")

    if inp.d_s_mm <= 0 or inp.d_p_mm <= 0:
        raise ValueError("Pitch diameters must be > 0.")

    if inp.F_t_sp_N <= 0 or inp.F_t_pr_N <= 0:
        raise ValueError("Tangential forces must be > 0.")

    if not (0.0 < inp.pressure_angle_deg < 90.0):
        raise ValueError(
            "Pressure angle must lie between 0 and 90 degrees."
        )

    geometry_values = (
        geometry.YJ_sun_sp,
        geometry.YJ_planet_sp,
        geometry.YJ_planet_pr,
        geometry.YJ_ring_pr,
    )

    if any(value <= 0 for value in geometry_values):
        raise ValueError(
            "All Y_J geometry factors must be > 0."
        )

    factor_values = (
        cfg.K_o,
        cfg.K_s,
        cfg.K_H,
        cfg.Z_R,
        cfg.K_B_sun,
        cfg.K_B_planet,
        cfg.K_B_ring,
        cfg.K_T,
        cfg.K_R,
        cfg.Y_N_sun,
        cfg.Y_N_planet,
        cfg.Y_N_ring,
        cfg.Y_I_sun,
        cfg.Y_I_planet,
        cfg.Y_I_ring,
        cfg.Z_N_sun,
        cfg.Z_N_planet,
        cfg.Z_N_ring,
        cfg.Z_W_sun,
        cfg.Z_W_planet,
        cfg.Z_W_ring,
    )

    if any(value <= 0 for value in factor_values):
        raise ValueError(
            "All AGMA strength factors must be > 0."
        )

    # ========================================================
    # 1. DYNAMIC FACTORS
    # ========================================================

    K_v_sp = _dynamic_factor(
        cfg.Q_v,
        inp.velocity_sp_mps,
    )

    K_v_pr = _dynamic_factor(
        cfg.Q_v,
        inp.velocity_pr_mps,
    )

    # ========================================================
    # 2. CONTACT GEOMETRY FACTORS Z_I
    # ========================================================

    Z_I_sp = _ZI_external_spur(
        inp.z_s,
        inp.z_p,
        inp.pressure_angle_deg,
    )

    Z_I_pr = _ZI_internal_spur(
        inp.z_p,
        inp.z_r,
        inp.pressure_angle_deg,
    )

    # ========================================================
    # 3. ELASTIC COEFFICIENTS Z_E
    # ========================================================

    Z_E_sp = _elastic_coefficient(
        sun_material,
        planet_material,
    )

    Z_E_pr = _elastic_coefficient(
        planet_material,
        ring_material,
    )

    # ========================================================
    # 4. SUN-PLANET BENDING COMMON LOAD TERM
    #
    # Ft already includes K_gamma.
    # ========================================================

    load_sp = (
        inp.F_t_sp_N
        * cfg.K_o
        * K_v_sp
        * cfg.K_s
        * cfg.K_H
    )

    # ========================================================
    # 5. SUN BENDING STRESS
    #
    # sigma_F =
    # Ft Ko Kv Ks KH KB / (b m YJ)
    # ========================================================

    sigma_F_sun = (
        load_sp
        * cfg.K_B_sun
        / (
            inp.face_width_mm
            * inp.module_mm
            * geometry.YJ_sun_sp
        )
    )

    # ========================================================
    # 6. PLANET BENDING — SUN SIDE
    # ========================================================

    sigma_F_planet_sp = (
        load_sp
        * cfg.K_B_planet
        / (
            inp.face_width_mm
            * inp.module_mm
            * geometry.YJ_planet_sp
        )
    )

    # ========================================================
    # 7. PLANET-RING BENDING COMMON LOAD TERM
    # ========================================================

    load_pr = (
        inp.F_t_pr_N
        * cfg.K_o
        * K_v_pr
        * cfg.K_s
        * cfg.K_H
    )

    # ========================================================
    # 8. PLANET BENDING — RING SIDE
    # ========================================================

    sigma_F_planet_pr = (
        load_pr
        * cfg.K_B_planet
        / (
            inp.face_width_mm
            * inp.module_mm
            * geometry.YJ_planet_pr
        )
    )

    # ========================================================
    # 9. RING BENDING STRESS
    # ========================================================

    sigma_F_ring = (
        load_pr
        * cfg.K_B_ring
        / (
            inp.face_width_mm
            * inp.module_mm
            * geometry.YJ_ring_pr
        )
    )

    # ========================================================
    # 10. ALLOWABLE BENDING STRESSES
    #
    # sigma_F,allow =
    # St * Y_N * Y_I / (K_T K_R)
    # ========================================================

    sigma_F_allow_sun = _bending_allowable(
        sun_material,
        cfg.Y_N_sun,
        cfg.Y_I_sun,
        cfg.K_T,
        cfg.K_R,
    )

    sigma_F_allow_planet = _bending_allowable(
        planet_material,
        cfg.Y_N_planet,
        cfg.Y_I_planet,
        cfg.K_T,
        cfg.K_R,
    )

    sigma_F_allow_ring = _bending_allowable(
        ring_material,
        cfg.Y_N_ring,
        cfg.Y_I_ring,
        cfg.K_T,
        cfg.K_R,
    )

    # ========================================================
    # 11. BENDING SAFETY FACTORS
    # ========================================================

    S_F_sun = (
        sigma_F_allow_sun
        / sigma_F_sun
    )

    S_F_planet_sp = (
        sigma_F_allow_planet
        / sigma_F_planet_sp
    )

    S_F_planet_pr = (
        sigma_F_allow_planet
        / sigma_F_planet_pr
    )

    S_F_ring = (
        sigma_F_allow_ring
        / sigma_F_ring
    )

    bending_safeties = {
        "sun_sp": S_F_sun,
        "planet_sp": S_F_planet_sp,
        "planet_pr": S_F_planet_pr,
        "ring_pr": S_F_ring,
    }

    governing_bending_location = min(
        bending_safeties,
        key=bending_safeties.get,
    )

    S_F_governing = (
        bending_safeties[
            governing_bending_location
        ]
    )

    # ========================================================
    # 12. CONTACT REFERENCE DIAMETERS
    #
    # External mesh:
    # smaller member = pinion/reference diameter
    #
    # Internal mesh:
    # external planet is the pinion
    # ========================================================

    d_ref_sp = min(
        inp.d_s_mm,
        inp.d_p_mm,
    )

    d_ref_pr = inp.d_p_mm

    # ========================================================
    # 13. SUN-PLANET CONTACT STRESS
    #
    # sigma_H =
    # ZE sqrt[
    #     Ft Ko Kv Ks KH ZR
    #     /
    #     (d b ZI)
    # ]
    # ========================================================

    sigma_H_sp = (
        Z_E_sp
        * sqrt(
            (
                inp.F_t_sp_N
                * cfg.K_o
                * K_v_sp
                * cfg.K_s
                * cfg.K_H
                * cfg.Z_R
            )
            /
            (
                d_ref_sp
                * inp.face_width_mm
                * Z_I_sp
            )
        )
    )

    # ========================================================
    # 14. PLANET-RING CONTACT STRESS
    # ========================================================

    sigma_H_pr = (
        Z_E_pr
        * sqrt(
            (
                inp.F_t_pr_N
                * cfg.K_o
                * K_v_pr
                * cfg.K_s
                * cfg.K_H
                * cfg.Z_R
            )
            /
            (
                d_ref_pr
                * inp.face_width_mm
                * Z_I_pr
            )
        )
    )

    # ========================================================
    # 15. ALLOWABLE CONTACT STRESSES
    #
    # sigma_H,allow =
    # Sc * Z_N * Z_W / (K_T K_R)
    # ========================================================

    sigma_H_allow_sun = _contact_allowable(
        sun_material,
        cfg.Z_N_sun,
        cfg.Z_W_sun,
        cfg.K_T,
        cfg.K_R,
    )

    sigma_H_allow_planet = _contact_allowable(
        planet_material,
        cfg.Z_N_planet,
        cfg.Z_W_planet,
        cfg.K_T,
        cfg.K_R,
    )

    sigma_H_allow_ring = _contact_allowable(
        ring_material,
        cfg.Z_N_ring,
        cfg.Z_W_ring,
        cfg.K_T,
        cfg.K_R,
    )

    # ========================================================
    # 16. CONTACT SAFETY FACTORS
    # ========================================================

    S_H_sun_sp = (
        sigma_H_allow_sun
        / sigma_H_sp
    )

    S_H_planet_sp = (
        sigma_H_allow_planet
        / sigma_H_sp
    )

    S_H_planet_pr = (
        sigma_H_allow_planet
        / sigma_H_pr
    )

    S_H_ring_pr = (
        sigma_H_allow_ring
        / sigma_H_pr
    )

    contact_safeties = {
        "sun_sp": S_H_sun_sp,
        "planet_sp": S_H_planet_sp,
        "planet_pr": S_H_planet_pr,
        "ring_pr": S_H_ring_pr,
    }

    governing_contact_location = min(
        contact_safeties,
        key=contact_safeties.get,
    )

    S_H_governing = (
        contact_safeties[
            governing_contact_location
        ]
    )

    # ========================================================
    # 17. LOAD-EQUIVALENT CONTACT SAFETY
    #
    # Contact stress is proportional to sqrt(load),
    # therefore compare S_F with S_H^2 for load margin.
    # ========================================================

    S_H_squared = (
        S_H_governing**2
    )

    governing_load_safety = min(
        S_F_governing,
        S_H_squared,
    )

    # ========================================================
    # 18. HARD BENDING CHECK
    # ========================================================

    if (
        S_F_governing
        < cfg.min_bending_safety_factor
    ):

        return _build_result(
            feasible=False,
            rejection_reason=(
                "bending_safety_below_minimum_"
                + governing_bending_location
            ),
            locals_dict=locals(),
        )

    # ========================================================
    # 19. HARD CONTACT CHECK
    # ========================================================

    if (
        S_H_governing
        < cfg.min_contact_safety_factor
    ):

        return _build_result(
            feasible=False,
            rejection_reason=(
                "contact_safety_below_minimum_"
                + governing_contact_location
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
) -> GearStrengthResult:

    L = locals_dict

    return GearStrengthResult(
        feasible=feasible,
        rejection_reason=rejection_reason,

        K_v_sp=L["K_v_sp"],
        K_v_pr=L["K_v_pr"],

        Z_I_sp=L["Z_I_sp"],
        Z_I_pr=L["Z_I_pr"],

        Z_E_sp=L["Z_E_sp"],
        Z_E_pr=L["Z_E_pr"],

        sigma_F_sun_MPa=L["sigma_F_sun"],
        sigma_F_planet_sp_MPa=L["sigma_F_planet_sp"],
        sigma_F_planet_pr_MPa=L["sigma_F_planet_pr"],
        sigma_F_ring_MPa=L["sigma_F_ring"],

        sigma_F_allow_sun_MPa=L["sigma_F_allow_sun"],
        sigma_F_allow_planet_MPa=L["sigma_F_allow_planet"],
        sigma_F_allow_ring_MPa=L["sigma_F_allow_ring"],

        S_F_sun=L["S_F_sun"],
        S_F_planet_sp=L["S_F_planet_sp"],
        S_F_planet_pr=L["S_F_planet_pr"],
        S_F_ring=L["S_F_ring"],

        S_F_governing=L["S_F_governing"],
        governing_bending_location=L[
            "governing_bending_location"
        ],

        sigma_H_sp_MPa=L["sigma_H_sp"],
        sigma_H_pr_MPa=L["sigma_H_pr"],

        sigma_H_allow_sun_MPa=L[
            "sigma_H_allow_sun"
        ],
        sigma_H_allow_planet_MPa=L[
            "sigma_H_allow_planet"
        ],
        sigma_H_allow_ring_MPa=L[
            "sigma_H_allow_ring"
        ],

        S_H_sun_sp=L["S_H_sun_sp"],
        S_H_planet_sp=L["S_H_planet_sp"],
        S_H_planet_pr=L["S_H_planet_pr"],
        S_H_ring_pr=L["S_H_ring_pr"],

        S_H_governing=L["S_H_governing"],
        governing_contact_location=L[
            "governing_contact_location"
        ],

        S_H_squared=L["S_H_squared"],

        governing_load_safety=L[
            "governing_load_safety"
        ],

        sun_material=L["sun_material"].name,
        planet_material=L["planet_material"].name,
        ring_material=L["ring_material"].name,
    )


def result_to_dict(
    result: GearStrengthResult
) -> dict:

    return asdict(result)