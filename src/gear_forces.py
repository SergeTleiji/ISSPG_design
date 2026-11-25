"""
PLANETARY GEAR TOOTH FORCES

Purpose:
    Calculate the mesh forces and planet-pin load for a surviving
    planetary + motor-compatible candidate.

INPUTS
------
From previous modules:
    T_s_nm                  Design sun/input torque [N.m]
    T_c_nm                  Carrier/output torque [N.m]
    T_r_nm                  Ideal fixed-ring reaction torque [N.m]

    d_s_mm                  Sun pitch diameter [mm]
    d_r_mm                  Ring pitch diameter [mm]
    center_distance_mm      Planet center radius, a [mm]

    n_s_rpm                 Sun rotational speed [rpm]
    n_c_rpm                 Carrier rotational speed [rpm]

    n_planets               Number of planets [-]

Configuration parameters:
    pressure_angle_deg      Spur gear pressure angle [deg]
    K_gamma                 Planetary mesh load-distribution factor [-]

OUTPUTS
-------
Sun-planet mesh:
    F_t_nom_N               Nominal tangential load per planet [N]
    F_t_N                   Design tangential load including K_gamma [N]
    F_r_N                   Radial/separating force [N]
    F_n_N                   Normal tooth force [N]
    F_a_N                   Axial force [N] = 0 for spur gears

Ring-side check:
    F_t_ring_N              Ring-side tangential force per planet [N]

Planet pin:
    F_pin_mesh_N            Approximation 2*F_t [N]
    F_pin_carrier_N         From carrier torque equilibrium [N]
    F_pin_design_N          Conservative maximum of the two [N]

Mesh velocity:
    relative_pitch_velocity_mps
                             Sun-planet relative pitch-line velocity [m/s]
    ring_pitch_velocity_mps
                             Equivalent ring-side mesh velocity [m/s]

Constraint bookkeeping:
    feasible
    rejection_reason

THIS MODULE CHECKS
------------------
    Input validity only.

There are no structural pass/fail checks here.
The calculated forces are passed downstream to:
    gear_strength.py
    planet_pin_bearing.py
    carrier.py

IMPORTANT
---------
    K_gamma is applied HERE to F_t.

    Therefore downstream AGMA stress equations must NOT multiply
    by K_gamma again.
"""

from dataclasses import dataclass, asdict
from math import pi, radians, tan, cos
from typing import Optional


# ============================================================
# INPUT
# ============================================================

@dataclass(frozen=True)
class GearForceInput:

    # Torques
    T_s_nm: float
    T_c_nm: float
    T_r_nm: float

    # Geometry
    d_s_mm: float
    d_r_mm: float
    center_distance_mm: float

    # Speeds
    n_s_rpm: float
    n_c_rpm: float

    # Planet count
    n_planets: int


# ============================================================
# CONFIGURATION
# ============================================================

@dataclass(frozen=True)
class GearForceConfig:
    pressure_angle_deg: float
    K_gamma: float


# ============================================================
# OUTPUT
# ============================================================

@dataclass
class GearForceResult:

    feasible: bool
    rejection_reason: Optional[str]

    # Mesh forces
    F_t_nom_N: float
    F_t_N: float
    F_r_N: float
    F_n_N: float
    F_a_N: float

    # Ring-side comparison
    F_t_ring_N: float

    # Planet pin loads
    F_pin_mesh_N: float
    F_pin_carrier_N: float
    F_pin_design_N: float

    # Mesh velocities
    relative_pitch_velocity_mps: float
    ring_pitch_velocity_mps: float

    # Useful bookkeeping
    pressure_angle_deg: float
    K_gamma: float


# ============================================================
# MAIN CALCULATION
# ============================================================

def evaluate_gear_forces(
    inp: GearForceInput,
    cfg: GearForceConfig,
) -> GearForceResult:

    # --------------------------------------------------------
    # Input validation
    # --------------------------------------------------------

    if inp.n_planets <= 0:
        raise ValueError("Number of planets must be > 0.")

    if inp.d_s_mm <= 0:
        raise ValueError("Sun pitch diameter must be > 0.")

    if inp.d_r_mm <= 0:
        raise ValueError("Ring pitch diameter must be > 0.")

    if inp.center_distance_mm <= 0:
        raise ValueError("Planet center distance must be > 0.")

    if cfg.K_gamma < 1.0:
        raise ValueError(
            "K_gamma should be >= 1.0 for planetary load distribution."
        )

    if not (0.0 < cfg.pressure_angle_deg < 90.0):
        raise ValueError(
            "Pressure angle must be between 0 and 90 degrees."
        )

    # --------------------------------------------------------
    # Unit conversion: mm -> m
    # --------------------------------------------------------

    d_s_m = inp.d_s_mm / 1000.0
    d_r_m = inp.d_r_mm / 1000.0
    a_m = inp.center_distance_mm / 1000.0

    phi = radians(cfg.pressure_angle_deg)

    # ========================================================
    # 1. NOMINAL SUN-PLANET TANGENTIAL FORCE
    #
    # F_t,nom = 2*T_s / (N_pl * d_s)
    # ========================================================

    F_t_nom = (
        2.0
        * abs(inp.T_s_nm)
        / (inp.n_planets * d_s_m)
    )

    # ========================================================
    # 2. DESIGN TANGENTIAL FORCE
    #
    # F_t = K_gamma * F_t,nom
    # ========================================================

    F_t = (
        cfg.K_gamma
        * F_t_nom
    )

    # ========================================================
    # 3. RADIAL / SEPARATING FORCE
    #
    # F_r = F_t * tan(phi)
    # ========================================================

    F_r = (
        F_t
        * tan(phi)
    )

    # ========================================================
    # 4. NORMAL TOOTH FORCE
    #
    # F_n = F_t / cos(phi)
    # ========================================================

    F_n = (
        F_t
        / cos(phi)
    )

    # ========================================================
    # 5. AXIAL FORCE
    #
    # Spur gears:
    # F_a = 0
    # ========================================================

    F_a = 0.0

    # ========================================================
    # 6. RING-SIDE TANGENTIAL FORCE CHECK
    #
    # F_t,r = K_gamma * 2*T_r / (N_pl*d_r)
    # ========================================================

    F_t_ring = (
        cfg.K_gamma
        * 2.0
        * abs(inp.T_r_nm)
        / (inp.n_planets * d_r_m)
    )

    # ========================================================
    # 7. PLANET PIN LOAD FROM MESH FORCE
    #
    # F_pin ~= 2*F_t
    # ========================================================

    F_pin_mesh = (
        2.0
        * F_t
    )

    # ========================================================
    # 8. PLANET PIN LOAD FROM CARRIER TORQUE
    #
    # F_pin = K_gamma*T_c / (N_pl*a)
    # ========================================================

    F_pin_carrier = (
        cfg.K_gamma
        * abs(inp.T_c_nm)
        / (inp.n_planets * a_m)
    )

    # ========================================================
    # 9. DESIGN PLANET PIN LOAD
    #
    # Because the preliminary lumped efficiency model causes
    # small inconsistency between sun-side and carrier-side
    # equilibrium, use the conservative larger value.
    # ========================================================

    F_pin_design = max(
        F_pin_mesh,
        F_pin_carrier,
    )

    # ========================================================
    # 10. SUN-PLANET RELATIVE PITCH-LINE VELOCITY
    #
    # v = pi*d_s*|n_s - n_c| / 60
    # ========================================================

    relative_pitch_velocity = (
        pi
        * d_s_m
        * abs(inp.n_s_rpm - inp.n_c_rpm)
        / 60.0
    )

    # ========================================================
    # 11. EQUIVALENT RING-SIDE PITCH VELOCITY
    #
    # Ring is stationary:
    #
    # v_r = pi*d_r*|n_c| / 60
    # ========================================================

    ring_pitch_velocity = (
        pi
        * d_r_m
        * abs(inp.n_c_rpm)
        / 60.0
    )

    # ========================================================
    # SUCCESS
    # ========================================================

    return GearForceResult(
        feasible=True,
        rejection_reason=None,

        F_t_nom_N=F_t_nom,
        F_t_N=F_t,
        F_r_N=F_r,
        F_n_N=F_n,
        F_a_N=F_a,

        F_t_ring_N=F_t_ring,

        F_pin_mesh_N=F_pin_mesh,
        F_pin_carrier_N=F_pin_carrier,
        F_pin_design_N=F_pin_design,

        relative_pitch_velocity_mps=relative_pitch_velocity,
        ring_pitch_velocity_mps=ring_pitch_velocity,

        pressure_angle_deg=cfg.pressure_angle_deg,
        K_gamma=cfg.K_gamma,
    )


# ============================================================
# OPTIONAL DICTIONARY CONVERSION FOR CSV / JSON
# ============================================================

def result_to_dict(
    result: GearForceResult
) -> dict:

    return asdict(result)