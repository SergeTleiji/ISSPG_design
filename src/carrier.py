"""
SINGLE CARRIER PLATE SIZING

Purpose:
    Size the single-sided planetary carrier plate from:
        1. Local pin-hole bearing/contact stress
        2. Global torsional stress around the integral output hub

Architecture:
    - Single flat circular carrier plate.
    - Planet pins are fixed cantilever pins mounted at radius a.
    - Carrier plate, central hub and output shaft are treated as one
      integral rigid component.
    - No key, spline or bolted hub connection is required.
    - Local carrier deformation around the planet pins is deferred to FEA.

INPUTS
------
From gear_forces.py:
    F_pin_N                     Design load acting on each planet pin [N]

From planetary.py:
    center_distance_mm          Planet-pin radial location a [mm]
    T_c_nm                      Carrier/output torque [N.m]

From planet_pin_bearing.py:
    pin_diameter_mm             Selected planet pin diameter [mm]

From output_system.py:
    output_shaft_diameter_mm    Actual catalogue-selected output shaft
                                diameter d_out [mm]

From material catalogue:
    name                        Carrier material designation
    Sy_MPa                      Yield strength [MPa]
    S_br_allow_MPa              Material bearing/contact strength [MPa]

Configuration:
    safety_factor               Required carrier safety factor [-]
    pin_edge_ligament_mm        Minimum radial material from outside of
                                planet-pin hole to carrier outer edge [mm]

OUTPUTS
-------
Carrier geometry:
    carrier_radius_mm
    carrier_outer_diameter_mm

Required plate thickness:
    thickness_pinhole_mm        Required from pin-hole bearing stress [mm]
    thickness_torsion_mm        Required from global carrier torsion [mm]
    carrier_thickness_mm        Governing required thickness [mm]
    governing_requirement       "pinhole" or "torsion"

Verification at final thickness:
    pinhole_bearing_stress_MPa
    pinhole_safety_factor

    torsional_shear_stress_MPa
    torsional_von_mises_MPa
    torsional_safety_factor

Overall:
    feasible
    rejection_reason

HARD CHECKS
-----------
    This module primarily SIZES the carrier rather than filtering it.

    A valid candidate always receives the larger of:
        t_pinhole
        t_torsion

    Invalid/non-physical inputs raise ValueError.

NOT INCLUDED HERE
-----------------
    Local plate bending caused by cantilever pin moment
    Pin-hole edge deformation
    Carrier plate distortion
    Pin press/interference fit
    Output-hub shoulder geometry
    Fillets / stress concentrations
    Final carrier FEA

These are deferred to CAD/FEA verification.
"""

from dataclasses import dataclass, asdict
from math import pi, sqrt
from typing import Optional


# ============================================================
# MATERIAL
# ============================================================

@dataclass(frozen=True)
class CarrierMaterial:

    name: str

    # Yield strength
    Sy_MPa: float

    # Nominal allowable bearing/contact strength
    # for the pin-hole interface
    S_br_allow_MPa: float


# ============================================================
# INPUT
# ============================================================

@dataclass(frozen=True)
class CarrierInput:

    # Load per planet pin
    F_pin_N: float

    # Selected pin diameter
    pin_diameter_mm: float

    # Planet-pin center radius
    center_distance_mm: float

    # Carrier/output torque
    T_c_nm: float

    # Actual output shaft / hub diameter
    output_shaft_diameter_mm: float


# ============================================================
# CONFIGURATION
# ============================================================

@dataclass(frozen=True)
class CarrierConfig:

    # Common design safety factor
    safety_factor: float

    # Minimum material between pin-hole OD and carrier OD
    pin_edge_ligament_mm: float


# ============================================================
# OUTPUT
# ============================================================

@dataclass
class CarrierResult:

    feasible: bool
    rejection_reason: Optional[str]

    material_name: str

    # Geometry
    carrier_radius_mm: float
    carrier_outer_diameter_mm: float

    # Thickness requirements
    thickness_pinhole_mm: float
    thickness_torsion_mm: float

    carrier_thickness_mm: float
    governing_requirement: str

    # Pin-hole verification
    pinhole_bearing_stress_MPa: float
    pinhole_safety_factor: float

    # Global torsional verification
    torsional_shear_stress_MPa: float
    torsional_von_mises_MPa: float
    torsional_safety_factor: float


# ============================================================
# MAIN CALCULATION
# ============================================================

def evaluate_carrier(
    inp: CarrierInput,
    material: CarrierMaterial,
    cfg: CarrierConfig,
) -> CarrierResult:

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    if inp.F_pin_N < 0:
        raise ValueError(
            "Planet-pin load cannot be negative."
        )

    if inp.pin_diameter_mm <= 0:
        raise ValueError(
            "Planet-pin diameter must be > 0."
        )

    if inp.center_distance_mm <= 0:
        raise ValueError(
            "Planet center distance must be > 0."
        )

    if inp.output_shaft_diameter_mm <= 0:
        raise ValueError(
            "Output shaft diameter must be > 0."
        )

    if material.Sy_MPa <= 0:
        raise ValueError(
            "Carrier material yield strength must be > 0."
        )

    if material.S_br_allow_MPa <= 0:
        raise ValueError(
            "Carrier bearing/contact strength must be > 0."
        )

    if cfg.safety_factor <= 0:
        raise ValueError(
            "Carrier safety factor must be > 0."
        )

    if cfg.pin_edge_ligament_mm < 0:
        raise ValueError(
            "Pin edge ligament cannot be negative."
        )

    # ========================================================
    # 1. CARRIER RADIUS
    #
    # R_c =
    # a + d_pin/2 + c_e
    # ========================================================

    carrier_radius_mm = (
        inp.center_distance_mm
        +
        inp.pin_diameter_mm / 2.0
        +
        cfg.pin_edge_ligament_mm
    )

    # ========================================================
    # 2. CARRIER OUTER DIAMETER
    #
    # D_c = 2*R_c
    # ========================================================

    carrier_outer_diameter_mm = (
        2.0
        * carrier_radius_mm
    )

    # ========================================================
    # 3. PIN-HOLE BEARING / CONTACT THICKNESS
    #
    # sigma_br =
    # F_pin / (t_c * d_pin)
    #
    # Require:
    #
    # sigma_br <= S_br_allow / n_c
    #
    # therefore:
    #
    # t_c,pinhole >=
    # n_c * F_pin
    # /
    # (S_br_allow * d_pin)
    # ========================================================

    if inp.F_pin_N == 0:

        thickness_pinhole_mm = 0.0

    else:

        thickness_pinhole_mm = (
            cfg.safety_factor
            * inp.F_pin_N
            /
            (
                material.S_br_allow_MPa
                * inp.pin_diameter_mm
            )
        )

    # ========================================================
    # 4. GLOBAL CARRIER TORSIONAL THICKNESS
    #
    # tau_c =
    # 2*T_c
    # /
    # (pi*d_out^2*t_c)
    #
    # sigma_VM =
    # sqrt(3)*tau_c
    #
    # Require:
    #
    # sigma_VM <= Sy/n_c
    #
    # therefore:
    #
    # t_c,torsion >=
    #
    # 2*sqrt(3)*n_c*T_c
    # /
    # (pi*d_out^2*Sy)
    # ========================================================

    T_c_Nmm = (
        abs(inp.T_c_nm)
        * 1000.0
    )

    if T_c_Nmm == 0:

        thickness_torsion_mm = 0.0

    else:

        thickness_torsion_mm = (
            2.0
            * sqrt(3.0)
            * cfg.safety_factor
            * T_c_Nmm
            /
            (
                pi
                * inp.output_shaft_diameter_mm**2
                * material.Sy_MPa
            )
        )

    # ========================================================
    # 5. FINAL CARRIER THICKNESS
    #
    # t_c =
    # max(t_pinhole, t_torsion)
    # ========================================================

    thickness_requirements = {
        "pinhole": thickness_pinhole_mm,
        "torsion": thickness_torsion_mm,
    }

    governing_requirement = max(
        thickness_requirements,
        key=thickness_requirements.get,
    )

    carrier_thickness_mm = (
        thickness_requirements[
            governing_requirement
        ]
    )

    # ========================================================
    # 6. PIN-HOLE STRESS VERIFICATION
    # ========================================================

    if carrier_thickness_mm > 0:

        pinhole_bearing_stress_MPa = (
            inp.F_pin_N
            /
            (
                carrier_thickness_mm
                * inp.pin_diameter_mm
            )
        )

    else:

        pinhole_bearing_stress_MPa = 0.0

    # ========================================================
    # 7. PIN-HOLE SAFETY FACTOR
    # ========================================================

    if pinhole_bearing_stress_MPa > 0:

        pinhole_safety_factor = (
            material.S_br_allow_MPa
            /
            pinhole_bearing_stress_MPa
        )

    else:

        pinhole_safety_factor = (
            float("inf")
        )

    # ========================================================
    # 8. GLOBAL CARRIER TORSIONAL SHEAR STRESS
    # ========================================================

    if carrier_thickness_mm > 0:

        torsional_shear_stress_MPa = (
            2.0
            * T_c_Nmm
            /
            (
                pi
                * inp.output_shaft_diameter_mm**2
                * carrier_thickness_mm
            )
        )

    else:

        torsional_shear_stress_MPa = 0.0

    # ========================================================
    # 9. GLOBAL CARRIER VON MISES STRESS
    # ========================================================

    torsional_von_mises_MPa = (
        sqrt(3.0)
        * torsional_shear_stress_MPa
    )

    # ========================================================
    # 10. GLOBAL TORSIONAL SAFETY FACTOR
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
    # SUCCESS
    # ========================================================

    return CarrierResult(
        feasible=True,
        rejection_reason=None,

        material_name=material.name,

        carrier_radius_mm=carrier_radius_mm,
        carrier_outer_diameter_mm=(
            carrier_outer_diameter_mm
        ),

        thickness_pinhole_mm=(
            thickness_pinhole_mm
        ),

        thickness_torsion_mm=(
            thickness_torsion_mm
        ),

        carrier_thickness_mm=(
            carrier_thickness_mm
        ),

        governing_requirement=(
            governing_requirement
        ),

        pinhole_bearing_stress_MPa=(
            pinhole_bearing_stress_MPa
        ),

        pinhole_safety_factor=(
            pinhole_safety_factor
        ),

        torsional_shear_stress_MPa=(
            torsional_shear_stress_MPa
        ),

        torsional_von_mises_MPa=(
            torsional_von_mises_MPa
        ),

        torsional_safety_factor=(
            torsional_safety_factor
        ),
    )


# ============================================================
# OPTIONAL DICTIONARY CONVERSION
# ============================================================

def result_to_dict(
    result: CarrierResult
) -> dict:

    return asdict(result)