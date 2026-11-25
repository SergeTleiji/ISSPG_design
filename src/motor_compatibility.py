"""
MOTOR–PLANETARY COMPATIBILITY

Purpose:
    Check whether a selected frameless motor can drive and physically contain
    one planetary candidate.

INPUTS
------
From planetary.py:
    ratio                       Planetary reduction ratio [-]
    n_s_rpm                     Required sun / motor speed [rpm]
    T_s_design_nm               Required sun / motor torque including
                                preliminary gearbox efficiency [N.m]
    z_r                         Ring gear tooth count [-]
    module_mm                   Gear module [mm]

From motor catalogue:
    name                        Motor designation
    rated_voltage_V             Rated voltage [V]
    outer_diameter_mm           Motor outer diameter [mm]
    axial_length_mm             Motor axial length [mm]
    stator_id_min_mm            Worst-case usable stator inner diameter [mm]
    rated_torque_nm             Rated motor torque [N.m]
    peak_torque_nm              Peak motor torque [N.m]
    rated_speed_rpm             Rated motor speed [rpm]
    no_load_speed_rpm           No-load motor speed [rpm]
    Kt_nm_per_A                 Torque constant [N.m/A]
    rated_current_A             Rated current [A]
    peak_current_A              Peak current [A]
    rotor_inertia_kgm2          Rotor inertia [kg.m^2]
    mass_kg                     Motor mass [kg]

Configuration parameters:
    min_ring_backup_ratio       Minimum ring backup ratio m_B [-]
    ring_radial_clearance_mm    Required radial clearance between
                                ring OD and usable stator ID [mm]

OUTPUTS
-------
Motor requirements:
    required_speed_rpm          Required motor speed [rpm]
    required_torque_nm          Required motor torque [N.m]
    required_current_A          Required motor current [A]

Utilization:
    peak_torque_utilization     T_req / T_peak [-]
    peak_current_utilization    I_req / I_peak [-]
    speed_utilization           n_req / n_0 [-]
    rated_torque_utilization    T_req / T_rated [-]
    rated_current_utilization   I_req / I_rated [-]
    rated_speed_utilization     n_req / n_rated [-]

QDD metric:
    reflected_motor_inertia_kgm2 = J_m * i^2

Preliminary ring packaging:
    ring_root_diameter_mm
    min_ring_rim_thickness_mm
    min_ring_outer_diameter_mm
    available_radial_clearance_mm

Constraint results:
    feasible
    rejection_reason

HARD REJECTION CHECKS
---------------------
    1. Required speed <= motor no-load speed
    2. Required torque <= motor peak torque
    3. Required current <= motor peak current
    4. Minimum structurally acceptable ring fits inside usable stator ID

NOT HARD-REJECTED HERE
----------------------
    Exceeding rated torque/current/speed:
        These are reported as utilization values but are not rejected because
        the present Phase-1 model defines a peak requirement rather than a
        complete RMS duty cycle.

    Thermal limits
    Detailed torque-speed curve
    Gear strength
    Final ring FEA
"""

from dataclasses import dataclass, asdict
from typing import Optional


# ============================================================
# MOTOR CATALOGUE ENTRY
# ============================================================

@dataclass(frozen=True)
class MotorSpec:
    name: str

    rated_voltage_V: float
    outer_diameter_mm: float
    axial_length_mm: float
    stator_id_min_mm: float

    rated_torque_nm: float
    peak_torque_nm: float

    rated_speed_rpm: float
    no_load_speed_rpm: float

    Kt_nm_per_A: float

    rated_current_A: float
    peak_current_A: float

    rotor_inertia_kgm2: float
    mass_kg: float


# ============================================================
# INPUT FROM PLANETARY MODULE
# ============================================================

@dataclass(frozen=True)
class MotorCompatibilityInput:
    ratio: float
    n_s_rpm: float
    T_s_design_nm: float

    z_r: int
    module_mm: float


# ============================================================
# CONFIGURATION / CONSTRAINTS
# ============================================================

@dataclass(frozen=True)
class MotorCompatibilityConstraints:
    min_ring_backup_ratio: float
    ring_radial_clearance_mm: float


# ============================================================
# OUTPUT
# ============================================================

@dataclass
class MotorCompatibilityResult:
    feasible: bool
    rejection_reason: Optional[str]

    motor_name: str

    # Required operating point
    required_speed_rpm: float
    required_torque_nm: float
    required_current_A: float

    # Utilization
    peak_torque_utilization: float
    peak_current_utilization: float
    speed_utilization: float

    rated_torque_utilization: float
    rated_current_utilization: float
    rated_speed_utilization: float

    # QDD metric
    reflected_motor_inertia_kgm2: float

    # Ring packaging
    ring_root_diameter_mm: float
    min_ring_rim_thickness_mm: float
    min_ring_outer_diameter_mm: float
    available_radial_clearance_mm: float

    # Motor data useful downstream
    motor_mass_kg: float
    motor_outer_diameter_mm: float
    motor_axial_length_mm: float
    stator_id_min_mm: float


# ============================================================
# MAIN CALCULATION
# ============================================================

def evaluate_motor_compatibility(
    inp: MotorCompatibilityInput,
    motor: MotorSpec,
    limits: MotorCompatibilityConstraints,
) -> MotorCompatibilityResult:

    # --------------------------------------------------------
    # Input validation
    # --------------------------------------------------------

    if inp.ratio <= 0:
        raise ValueError("Planetary ratio must be > 0.")

    if inp.module_mm <= 0:
        raise ValueError("Gear module must be > 0.")

    if inp.z_r <= 0:
        raise ValueError("Ring tooth count must be > 0.")

    if motor.Kt_nm_per_A <= 0:
        raise ValueError("Motor torque constant must be > 0.")

    if limits.min_ring_backup_ratio <= 0:
        raise ValueError("Minimum ring backup ratio must be > 0.")

    if limits.ring_radial_clearance_mm < 0:
        raise ValueError("Ring radial clearance cannot be negative.")

    # ========================================================
    # 1. REQUIRED MOTOR OPERATING POINT
    #
    # Motor rotor directly drives sun:
    #
    # n_m = |n_s|
    # T_m = T_s,design
    # ========================================================

    required_speed = abs(inp.n_s_rpm)
    required_torque = abs(inp.T_s_design_nm)

    # ========================================================
    # 2. REQUIRED MOTOR CURRENT
    #
    # T = Kt I
    # I = T / Kt
    # ========================================================

    required_current = required_torque / motor.Kt_nm_per_A

    # ========================================================
    # 3. UTILIZATION VALUES
    # ========================================================

    peak_torque_utilization = (
        required_torque / motor.peak_torque_nm
    )

    peak_current_utilization = (
        required_current / motor.peak_current_A
    )

    speed_utilization = (
        required_speed / motor.no_load_speed_rpm
    )

    rated_torque_utilization = (
        required_torque / motor.rated_torque_nm
    )

    rated_current_utilization = (
        required_current / motor.rated_current_A
    )

    rated_speed_utilization = (
        required_speed / motor.rated_speed_rpm
    )

    # ========================================================
    # 4. REFLECTED MOTOR INERTIA
    #
    # J_ref = J_m * i^2
    # ========================================================

    reflected_motor_inertia = (
        motor.rotor_inertia_kgm2 * inp.ratio**2
    )

    # ========================================================
    # 5. PRELIMINARY RING PACKAGING
    #
    # Standard full-depth internal ring:
    #
    # d_f,r = m (Z_r + 2.5)
    #
    # whole tooth depth:
    # h_t = 2.25 m
    #
    # backup ratio:
    # m_B = t_R / h_t
    #
    # therefore minimum acceptable rim:
    # t_R,min = m_B,min * h_t
    # ========================================================

    ring_root_diameter = (
        inp.module_mm * (inp.z_r + 2.5)
    )

    whole_tooth_depth = (
        2.25 * inp.module_mm
    )

    min_ring_rim_thickness = (
        limits.min_ring_backup_ratio
        * whole_tooth_depth
    )

    # ========================================================
    # 6. MINIMUM RING OUTER DIAMETER
    #
    # D_ring,out = d_f,r + 2 t_R
    # ========================================================

    min_ring_outer_diameter = (
        ring_root_diameter
        + 2.0 * min_ring_rim_thickness
    )

    # ========================================================
    # 7. AVAILABLE RADIAL CLEARANCE
    #
    # delta_available
    #   = (D_stator,ID - D_ring,out) / 2
    # ========================================================

    available_radial_clearance = (
        motor.stator_id_min_mm
        - min_ring_outer_diameter
    ) / 2.0

    # ========================================================
    # 8. HARD MOTOR SPEED CHECK
    # ========================================================

    if required_speed > motor.no_load_speed_rpm:
        return _result(
            feasible=False,
            reason="required_speed_exceeds_no_load_speed",
            inp=inp,
            motor=motor,
            required_speed=required_speed,
            required_torque=required_torque,
            required_current=required_current,
            peak_torque_utilization=peak_torque_utilization,
            peak_current_utilization=peak_current_utilization,
            speed_utilization=speed_utilization,
            rated_torque_utilization=rated_torque_utilization,
            rated_current_utilization=rated_current_utilization,
            rated_speed_utilization=rated_speed_utilization,
            reflected_motor_inertia=reflected_motor_inertia,
            ring_root_diameter=ring_root_diameter,
            min_ring_rim_thickness=min_ring_rim_thickness,
            min_ring_outer_diameter=min_ring_outer_diameter,
            available_radial_clearance=available_radial_clearance,
        )

    # ========================================================
    # 9. HARD PEAK TORQUE CHECK
    # ========================================================

    if required_torque > motor.peak_torque_nm:
        return _result(
            feasible=False,
            reason="required_torque_exceeds_peak_torque",
            inp=inp,
            motor=motor,
            required_speed=required_speed,
            required_torque=required_torque,
            required_current=required_current,
            peak_torque_utilization=peak_torque_utilization,
            peak_current_utilization=peak_current_utilization,
            speed_utilization=speed_utilization,
            rated_torque_utilization=rated_torque_utilization,
            rated_current_utilization=rated_current_utilization,
            rated_speed_utilization=rated_speed_utilization,
            reflected_motor_inertia=reflected_motor_inertia,
            ring_root_diameter=ring_root_diameter,
            min_ring_rim_thickness=min_ring_rim_thickness,
            min_ring_outer_diameter=min_ring_outer_diameter,
            available_radial_clearance=available_radial_clearance,
        )

    # ========================================================
    # 10. HARD PEAK CURRENT CHECK
    # ========================================================

    if required_current > motor.peak_current_A:
        return _result(
            feasible=False,
            reason="required_current_exceeds_peak_current",
            inp=inp,
            motor=motor,
            required_speed=required_speed,
            required_torque=required_torque,
            required_current=required_current,
            peak_torque_utilization=peak_torque_utilization,
            peak_current_utilization=peak_current_utilization,
            speed_utilization=speed_utilization,
            rated_torque_utilization=rated_torque_utilization,
            rated_current_utilization=rated_current_utilization,
            rated_speed_utilization=rated_speed_utilization,
            reflected_motor_inertia=reflected_motor_inertia,
            ring_root_diameter=ring_root_diameter,
            min_ring_rim_thickness=min_ring_rim_thickness,
            min_ring_outer_diameter=min_ring_outer_diameter,
            available_radial_clearance=available_radial_clearance,
        )

    # ========================================================
    # 11. STATOR BORE PACKAGING CHECK
    #
    # D_ring,out + 2 delta_r <= D_stator,ID,min
    #
    # Equivalent:
    #
    # delta_available >= delta_required
    # ========================================================

    if (
        available_radial_clearance
        < limits.ring_radial_clearance_mm
    ):
        return _result(
            feasible=False,
            reason="ring_does_not_fit_stator_bore",
            inp=inp,
            motor=motor,
            required_speed=required_speed,
            required_torque=required_torque,
            required_current=required_current,
            peak_torque_utilization=peak_torque_utilization,
            peak_current_utilization=peak_current_utilization,
            speed_utilization=speed_utilization,
            rated_torque_utilization=rated_torque_utilization,
            rated_current_utilization=rated_current_utilization,
            rated_speed_utilization=rated_speed_utilization,
            reflected_motor_inertia=reflected_motor_inertia,
            ring_root_diameter=ring_root_diameter,
            min_ring_rim_thickness=min_ring_rim_thickness,
            min_ring_outer_diameter=min_ring_outer_diameter,
            available_radial_clearance=available_radial_clearance,
        )

    # ========================================================
    # SUCCESS
    # ========================================================

    return _result(
        feasible=True,
        reason=None,
        inp=inp,
        motor=motor,
        required_speed=required_speed,
        required_torque=required_torque,
        required_current=required_current,
        peak_torque_utilization=peak_torque_utilization,
        peak_current_utilization=peak_current_utilization,
        speed_utilization=speed_utilization,
        rated_torque_utilization=rated_torque_utilization,
        rated_current_utilization=rated_current_utilization,
        rated_speed_utilization=rated_speed_utilization,
        reflected_motor_inertia=reflected_motor_inertia,
        ring_root_diameter=ring_root_diameter,
        min_ring_rim_thickness=min_ring_rim_thickness,
        min_ring_outer_diameter=min_ring_outer_diameter,
        available_radial_clearance=available_radial_clearance,
    )


# ============================================================
# RESULT HELPER
# ============================================================

def _result(
    feasible,
    reason,
    inp,
    motor,
    required_speed,
    required_torque,
    required_current,
    peak_torque_utilization,
    peak_current_utilization,
    speed_utilization,
    rated_torque_utilization,
    rated_current_utilization,
    rated_speed_utilization,
    reflected_motor_inertia,
    ring_root_diameter,
    min_ring_rim_thickness,
    min_ring_outer_diameter,
    available_radial_clearance,
):

    return MotorCompatibilityResult(
        feasible=feasible,
        rejection_reason=reason,

        motor_name=motor.name,

        required_speed_rpm=required_speed,
        required_torque_nm=required_torque,
        required_current_A=required_current,

        peak_torque_utilization=peak_torque_utilization,
        peak_current_utilization=peak_current_utilization,
        speed_utilization=speed_utilization,

        rated_torque_utilization=rated_torque_utilization,
        rated_current_utilization=rated_current_utilization,
        rated_speed_utilization=rated_speed_utilization,

        reflected_motor_inertia_kgm2=reflected_motor_inertia,

        ring_root_diameter_mm=ring_root_diameter,
        min_ring_rim_thickness_mm=min_ring_rim_thickness,
        min_ring_outer_diameter_mm=min_ring_outer_diameter,
        available_radial_clearance_mm=available_radial_clearance,

        motor_mass_kg=motor.mass_kg,
        motor_outer_diameter_mm=motor.outer_diameter_mm,
        motor_axial_length_mm=motor.axial_length_mm,
        stator_id_min_mm=motor.stator_id_min_mm,
    )


def result_to_dict(
    result: MotorCompatibilityResult
) -> dict:
    return asdict(result)