"""
INTERNAL RING GEAR RIM + FINAL STATOR PACKAGING

Purpose:
    Size the structural rim surrounding the fixed internal ring gear and
    perform the final ring-versus-stator packaging check.

Architecture:
    - Internal ring gear and its outer structural rim are treated as one
      integral stationary component.
    - Gear-tooth bending/contact strength has already been checked in
      gear_strength.py.
    - This module sizes only the material OUTSIDE the internal tooth root.
    - Final ring/support-flange deformation is deferred to FEA.

INPUTS
------
From planetary.py:
    z_r                         Ring gear tooth count [-]
    module_mm                   Gear module [mm]
    T_r_nm                      Fixed-ring reaction torque [N.m]

From motor catalogue:
    stator_id_min_mm            Worst-case usable stator inner diameter [mm]

From material catalogue:
    name                        Ring material designation
    Sy_MPa                      Yield strength [MPa]

Configuration:
    safety_factor               Required global ring torsional SF [-]
    min_backup_ratio            Minimum AGMA rim backup ratio m_B [-]
                                Must be >= 1.2 in this simplified model.
    radial_clearance_mm         Required radial clearance between
                                ring OD and stator ID [mm]

OUTPUTS
-------
Ring geometry:
    ring_root_diameter_mm       Internal-ring root diameter d_f,r [mm]
    whole_tooth_depth_mm        Standard whole tooth depth h_t [mm]

Rim sizing:
    thickness_backup_mm         Minimum rim from backup ratio [mm]
    thickness_torsion_mm        Conservative global torsion requirement [mm]
    ring_rim_thickness_mm       Final required rim thickness [mm]
    governing_requirement       "backup_ratio" or "torsion"

Backup ratio:
    actual_backup_ratio
    K_B                         1.0 for m_B >= 1.2

Final envelope:
    ring_outer_diameter_mm
    available_radial_clearance_mm

Global torsional sanity check:
    torsional_shear_stress_MPa
    torsional_von_mises_MPa
    torsional_safety_factor

Overall:
    feasible
    rejection_reason

HARD CHECKS
-----------
    1. Minimum backup ratio >= 1.2
    2. Final ring OD + required clearance fits inside worst-case stator ID

NOT INCLUDED HERE
-----------------
    Gear-tooth bending/contact strength
    Ring-to-housing flange details
    Ring/support fasteners
    Local tooth-root deformation
    Ring ovalization
    Final structural FEA

IMPORTANT
---------
    motor_compatibility.py performs an EARLY packaging rejection using the
    minimum backup-ratio rim.

    ring.py performs the FINAL packaging check after considering whether
    global torsion requires an even thicker rim.
"""

from dataclasses import dataclass, asdict
from math import pi, sqrt
from typing import Optional


# ============================================================
# MATERIAL
# ============================================================

@dataclass(frozen=True)
class RingMaterial:
    name: str
    Sy_MPa: float


# ============================================================
# INPUT
# ============================================================

@dataclass(frozen=True)
class RingInput:

    z_r: int
    module_mm: float

    T_r_nm: float

    stator_id_min_mm: float


# ============================================================
# CONFIGURATION
# ============================================================

@dataclass(frozen=True)
class RingConfig:

    safety_factor: float

    min_backup_ratio: float

    radial_clearance_mm: float


# ============================================================
# OUTPUT
# ============================================================

@dataclass
class RingResult:

    feasible: bool
    rejection_reason: Optional[str]

    material_name: str

    # Basic geometry
    ring_root_diameter_mm: float
    whole_tooth_depth_mm: float

    # Rim thickness requirements
    thickness_backup_mm: float
    thickness_torsion_mm: float

    ring_rim_thickness_mm: float
    governing_requirement: str

    # AGMA rim result
    actual_backup_ratio: float
    K_B: float

    # Final radial envelope
    ring_outer_diameter_mm: float
    available_radial_clearance_mm: float

    # Global torsional check
    torsional_shear_stress_MPa: float
    torsional_von_mises_MPa: float
    torsional_safety_factor: float


# ============================================================
# MAIN CALCULATION
# ============================================================

def evaluate_ring(
    inp: RingInput,
    material: RingMaterial,
    cfg: RingConfig,
) -> RingResult:

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    if inp.z_r <= 0:
        raise ValueError(
            "Ring tooth count must be > 0."
        )

    if inp.module_mm <= 0:
        raise ValueError(
            "Gear module must be > 0."
        )

    if inp.stator_id_min_mm <= 0:
        raise ValueError(
            "Usable stator ID must be > 0."
        )

    if material.Sy_MPa <= 0:
        raise ValueError(
            "Ring material yield strength must be > 0."
        )

    if cfg.safety_factor <= 0:
        raise ValueError(
            "Ring safety factor must be > 0."
        )

    # This module assumes K_B = 1.
    if cfg.min_backup_ratio < 1.2:
        raise ValueError(
            "min_backup_ratio must be >= 1.2 "
            "for the simplified K_B = 1 ring model."
        )

    if cfg.radial_clearance_mm < 0:
        raise ValueError(
            "Required radial clearance cannot be negative."
        )

    # ========================================================
    # 1. INTERNAL RING ROOT DIAMETER
    #
    # d_f,r ~= m(Z_r + 2.5)
    # ========================================================

    ring_root_diameter_mm = (
        inp.module_mm
        * (inp.z_r + 2.5)
    )

    # ========================================================
    # 2. STANDARD WHOLE TOOTH DEPTH
    #
    # h_t ~= 2.25*m
    # ========================================================

    whole_tooth_depth_mm = (
        2.25
        * inp.module_mm
    )

    # ========================================================
    # 3. MINIMUM RIM FROM BACKUP RATIO
    #
    # m_B = t_R/h_t
    #
    # t_R,backup = m_B,min * h_t
    # ========================================================

    thickness_backup_mm = (
        cfg.min_backup_ratio
        * whole_tooth_depth_mm
    )

    # ========================================================
    # 4. CONSERVATIVE REFERENCE RADIUS FOR GLOBAL TORSION
    #
    # Use the ring root radius instead of the true rim
    # mean radius:
    #
    # r_ref = d_f,r/2
    #
    # Because the true mean radius is larger, this produces
    # a conservative global torsional thickness.
    # ========================================================

    reference_radius_mm = (
        ring_root_diameter_mm
        / 2.0
    )

    # Convert torque N.m -> N.mm
    T_r_Nmm = (
        abs(inp.T_r_nm)
        * 1000.0
    )

    # ========================================================
    # 5. GLOBAL TORSIONAL RIM THICKNESS
    #
    # Thin closed circular wall approximation:
    #
    # tau =
    # T / (2*pi*r_ref^2*t_R)
    #
    # sigma_VM = sqrt(3)*tau
    #
    # Require:
    #
    # sigma_VM <= Sy/n
    #
    # therefore:
    #
    # t_R,torsion >=
    # sqrt(3)*n*T
    # /
    # (2*pi*r_ref^2*Sy)
    # ========================================================

    if T_r_Nmm == 0:

        thickness_torsion_mm = 0.0

    else:

        thickness_torsion_mm = (
            sqrt(3.0)
            * cfg.safety_factor
            * T_r_Nmm
            /
            (
                2.0
                * pi
                * reference_radius_mm**2
                * material.Sy_MPa
            )
        )

    # ========================================================
    # 6. FINAL RIM THICKNESS
    # ========================================================

    thickness_requirements = {
        "backup_ratio": thickness_backup_mm,
        "torsion": thickness_torsion_mm,
    }

    governing_requirement = max(
        thickness_requirements,
        key=thickness_requirements.get,
    )

    ring_rim_thickness_mm = (
        thickness_requirements[
            governing_requirement
        ]
    )

    # ========================================================
    # 7. ACTUAL BACKUP RATIO
    #
    # m_B = t_R/h_t
    # ========================================================

    actual_backup_ratio = (
        ring_rim_thickness_mm
        /
        whole_tooth_depth_mm
    )

    # Since actual m_B >= configured m_B >= 1.2:
    K_B = 1.0

    # ========================================================
    # 8. FINAL RING OUTER DIAMETER
    #
    # D_ring,out =
    # d_f,r + 2*t_R
    # ========================================================

    ring_outer_diameter_mm = (
        ring_root_diameter_mm
        +
        2.0
        * ring_rim_thickness_mm
    )

    # ========================================================
    # 9. AVAILABLE RADIAL CLEARANCE
    #
    # delta_available =
    # (D_stator,ID,min - D_ring,out)/2
    # ========================================================

    available_radial_clearance_mm = (
        inp.stator_id_min_mm
        -
        ring_outer_diameter_mm
    ) / 2.0

    # ========================================================
    # 10. ACTUAL GLOBAL TORSIONAL SHEAR
    # ========================================================

    if (
        ring_rim_thickness_mm > 0
        and T_r_Nmm > 0
    ):

        torsional_shear_stress_MPa = (
            T_r_Nmm
            /
            (
                2.0
                * pi
                * reference_radius_mm**2
                * ring_rim_thickness_mm
            )
        )

    else:

        torsional_shear_stress_MPa = 0.0

    # ========================================================
    # 11. VON MISES STRESS
    # ========================================================

    torsional_von_mises_MPa = (
        sqrt(3.0)
        * torsional_shear_stress_MPa
    )

    # ========================================================
    # 12. GLOBAL TORSIONAL SAFETY
    # ========================================================

    if torsional_von_mises_MPa > 0:

        torsional_safety_factor = (
            material.Sy_MPa
            /
            torsional_von_mises_MPa
        )

    else:

        torsional_safety_factor = (
            float("inf")
        )

    # ========================================================
    # 13. FINAL STATOR PACKAGING CHECK
    #
    # D_ring,out + 2*delta_req
    # <=
    # D_stator,ID,min
    #
    # Equivalent:
    #
    # delta_available >= delta_req
    # ========================================================

    if (
        available_radial_clearance_mm
        <
        cfg.radial_clearance_mm
    ):

        return _build_result(
            feasible=False,
            rejection_reason=(
                "final_ring_does_not_fit_stator_bore"
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
) -> RingResult:

    L = locals_dict

    return RingResult(
        feasible=feasible,
        rejection_reason=rejection_reason,

        material_name=L["material"].name,

        ring_root_diameter_mm=L[
            "ring_root_diameter_mm"
        ],

        whole_tooth_depth_mm=L[
            "whole_tooth_depth_mm"
        ],

        thickness_backup_mm=L[
            "thickness_backup_mm"
        ],

        thickness_torsion_mm=L[
            "thickness_torsion_mm"
        ],

        ring_rim_thickness_mm=L[
            "ring_rim_thickness_mm"
        ],

        governing_requirement=L[
            "governing_requirement"
        ],

        actual_backup_ratio=L[
            "actual_backup_ratio"
        ],

        K_B=L["K_B"],

        ring_outer_diameter_mm=L[
            "ring_outer_diameter_mm"
        ],

        available_radial_clearance_mm=L[
            "available_radial_clearance_mm"
        ],

        torsional_shear_stress_MPa=L[
            "torsional_shear_stress_MPa"
        ],

        torsional_von_mises_MPa=L[
            "torsional_von_mises_MPa"
        ],

        torsional_safety_factor=L[
            "torsional_safety_factor"
        ],
    )


# ============================================================
# OPTIONAL DICTIONARY CONVERSION
# ============================================================

def result_to_dict(
    result: RingResult
) -> dict:

    return asdict(result)