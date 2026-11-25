"""
Standalone tests for src/motor_compatibility.py

Run from project root:

    python -m tests.motor_compatibility

No motor YAML catalogue is required.
Motor specifications are instantiated directly in this test.
"""

from src.motor_compatibility import (
    MotorSpec,
    MotorCompatibilityInput,
    MotorCompatibilityConstraints,
    evaluate_motor_compatibility,
)


# ============================================================
# REAL MOTOR TEST DATA
# ============================================================

RO60 = MotorSpec(
    name="RO60 KV115",

    rated_voltage_V=48.0,
    outer_diameter_mm=73.8,
    axial_length_mm=23.0,
    stator_id_min_mm=32.0,

    rated_torque_nm=0.80,
    peak_torque_nm=2.40,

    rated_speed_rpm=4200.0,
    no_load_speed_rpm=5520.0,

    Kt_nm_per_A=0.094,

    rated_current_A=8.5,
    peak_current_A=40.0,

    rotor_inertia_kgm2=1.161e-4,
    mass_kg=0.248,
)


RO80 = MotorSpec(
    name="RO80 KV105",

    rated_voltage_V=48.0,
    outer_diameter_mm=92.6,
    axial_length_mm=26.4,
    stator_id_min_mm=55.0,

    rated_torque_nm=1.30,
    peak_torque_nm=4.00,

    rated_speed_rpm=3600.0,
    no_load_speed_rpm=5040.0,

    Kt_nm_per_A=0.087,

    rated_current_A=15.0,
    peak_current_A=50.0,

    rotor_inertia_kgm2=2.612e-4,
    mass_kg=0.352,
)


def print_result(title, result):

    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)

    print(f"Motor:                         {result.motor_name}")

    print(f"Feasible:                      {result.feasible}")
    print(f"Rejection reason:              {result.rejection_reason}")

    print(
        f"Required speed:                "
        f"{result.required_speed_rpm:.3f} rpm"
    )

    print(
        f"Required torque:               "
        f"{result.required_torque_nm:.6f} N.m"
    )

    print(
        f"Required current:              "
        f"{result.required_current_A:.3f} A"
    )

    print(
        f"Peak torque utilization:       "
        f"{result.peak_torque_utilization:.3f}"
    )

    print(
        f"Peak current utilization:      "
        f"{result.peak_current_utilization:.3f}"
    )

    print(
        f"No-load speed utilization:     "
        f"{result.speed_utilization:.3f}"
    )

    print(
        f"Rated torque utilization:      "
        f"{result.rated_torque_utilization:.3f}"
    )

    print(
        f"Reflected motor inertia:       "
        f"{result.reflected_motor_inertia_kgm2:.6e} kg.m^2"
    )

    print(
        f"Ring root diameter:            "
        f"{result.ring_root_diameter_mm:.3f} mm"
    )

    print(
        f"Minimum ring rim thickness:    "
        f"{result.min_ring_rim_thickness_mm:.3f} mm"
    )

    print(
        f"Minimum ring OD:               "
        f"{result.min_ring_outer_diameter_mm:.3f} mm"
    )

    print(
        f"Available radial clearance:    "
        f"{result.available_radial_clearance_mm:.3f} mm"
    )


# ============================================================
# TEST 1 — VALID RO80 CANDIDATE
# ============================================================

def test_valid_candidate():

    inp = MotorCompatibilityInput(
        ratio=6.0,
        n_s_rpm=540.0,
        T_s_design_nm=1.3070175438596494,

        z_r=100,
        module_mm=0.5,
    )

    limits = MotorCompatibilityConstraints(
        min_ring_backup_ratio=1.2,

        # Temporary test-only assumption
        ring_radial_clearance_mm=0.25,
    )

    result = evaluate_motor_compatibility(
        inp,
        RO80,
        limits,
    )

    print_result(
        "TEST 1 — VALID RO80 CANDIDATE",
        result
    )

    assert result.feasible

    # Current:
    # I = T / Kt
    expected_current = (
        inp.T_s_design_nm / RO80.Kt_nm_per_A
    )

    assert abs(
        result.required_current_A
        - expected_current
    ) < 1e-12

    # Reflected inertia:
    # J_ref = Jm * i^2
    expected_J_ref = (
        RO80.rotor_inertia_kgm2
        * inp.ratio**2
    )

    assert abs(
        result.reflected_motor_inertia_kgm2
        - expected_J_ref
    ) < 1e-12

    print("\nPASS: valid motor candidate accepted.")


# ============================================================
# TEST 2 — SPEED REJECTION
# ============================================================

def test_speed_rejection():

    inp = MotorCompatibilityInput(
        ratio=6.0,
        n_s_rpm=6000.0,
        T_s_design_nm=1.0,

        z_r=100,
        module_mm=0.5,
    )

    limits = MotorCompatibilityConstraints(
        min_ring_backup_ratio=1.2,
        ring_radial_clearance_mm=0.25,
    )

    result = evaluate_motor_compatibility(
        inp,
        RO80,
        limits,
    )

    print_result(
        "TEST 2 — SPEED REJECTION",
        result
    )

    assert not result.feasible
    assert (
        result.rejection_reason
        == "required_speed_exceeds_no_load_speed"
    )

    print("\nPASS: excessive motor speed correctly rejected.")


# ============================================================
# TEST 3 — PEAK TORQUE REJECTION
# ============================================================

def test_torque_rejection():

    inp = MotorCompatibilityInput(
        ratio=6.0,
        n_s_rpm=500.0,

        # RO80 peak torque = 4.0 N.m
        T_s_design_nm=4.5,

        z_r=100,
        module_mm=0.5,
    )

    limits = MotorCompatibilityConstraints(
        min_ring_backup_ratio=1.2,
        ring_radial_clearance_mm=0.25,
    )

    result = evaluate_motor_compatibility(
        inp,
        RO80,
        limits,
    )

    print_result(
        "TEST 3 — PEAK TORQUE REJECTION",
        result
    )

    assert not result.feasible
    assert (
        result.rejection_reason
        == "required_torque_exceeds_peak_torque"
    )

    print("\nPASS: excessive peak torque correctly rejected.")


# ============================================================
# TEST 4 — CURRENT REJECTION
# Uses deliberately synthetic motor data so current can fail
# independently of torque.
# ============================================================

def test_current_rejection():

    synthetic_motor = MotorSpec(
        name="Synthetic Current-Limited Motor",

        rated_voltage_V=48.0,
        outer_diameter_mm=100.0,
        axial_length_mm=30.0,
        stator_id_min_mm=80.0,

        rated_torque_nm=5.0,
        peak_torque_nm=10.0,

        rated_speed_rpm=3000.0,
        no_load_speed_rpm=5000.0,

        Kt_nm_per_A=1.0,

        rated_current_A=3.0,
        peak_current_A=5.0,

        rotor_inertia_kgm2=1e-4,
        mass_kg=0.5,
    )

    inp = MotorCompatibilityInput(
        ratio=6.0,
        n_s_rpm=500.0,

        # 6 N.m < synthetic peak torque of 10 N.m,
        # but I = 6/1 = 6 A > 5 A peak current.
        T_s_design_nm=6.0,

        z_r=100,
        module_mm=0.5,
    )

    limits = MotorCompatibilityConstraints(
        min_ring_backup_ratio=1.2,
        ring_radial_clearance_mm=0.25,
    )

    result = evaluate_motor_compatibility(
        inp,
        synthetic_motor,
        limits,
    )

    print_result(
        "TEST 4 — CURRENT REJECTION",
        result
    )

    assert not result.feasible
    assert (
        result.rejection_reason
        == "required_current_exceeds_peak_current"
    )

    print("\nPASS: excessive current correctly rejected.")


# ============================================================
# TEST 5 — STATOR PACKAGING REJECTION
# Same planetary candidate that fits RO80 but is too large
# for the RO60 usable stator bore.
# ============================================================

def test_packaging_rejection():

    inp = MotorCompatibilityInput(
        ratio=6.0,
        n_s_rpm=540.0,
        T_s_design_nm=1.3070175438596494,

        z_r=100,
        module_mm=0.5,
    )

    limits = MotorCompatibilityConstraints(
        min_ring_backup_ratio=1.2,
        ring_radial_clearance_mm=0.25,
    )

    result = evaluate_motor_compatibility(
        inp,
        RO60,
        limits,
    )

    print_result(
        "TEST 5 — STATOR PACKAGING REJECTION",
        result
    )

    assert not result.feasible
    assert (
        result.rejection_reason
        == "ring_does_not_fit_stator_bore"
    )

    print("\nPASS: oversized ring correctly rejected.")


# ============================================================
# RUN ALL TESTS
# ============================================================

if __name__ == "__main__":

    test_valid_candidate()
    test_speed_rejection()
    test_torque_rejection()
    test_current_rejection()
    test_packaging_rejection()

    print("\n" + "=" * 72)
    print("ALL MOTOR COMPATIBILITY TESTS PASSED")
    print("=" * 72)