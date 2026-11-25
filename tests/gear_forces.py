"""
Standalone tests for src/gear_forces.py

Run from project root:

    python -m tests.gear_forces

No other pipeline modules are required.
All upstream values are manually supplied.
"""

from math import pi, tan, cos, radians

from src.gear_forces import (
    GearForceInput,
    GearForceConfig,
    evaluate_gear_forces,
)


def print_result(title, result):

    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)

    print(f"Feasible:                      {result.feasible}")
    print(f"Rejection reason:              {result.rejection_reason}")

    print(
        f"Nominal tangential force:      "
        f"{result.F_t_nom_N:.3f} N"
    )

    print(
        f"Design tangential force:       "
        f"{result.F_t_N:.3f} N"
    )

    print(
        f"Radial force:                  "
        f"{result.F_r_N:.3f} N"
    )

    print(
        f"Normal force:                  "
        f"{result.F_n_N:.3f} N"
    )

    print(
        f"Axial force:                   "
        f"{result.F_a_N:.3f} N"
    )

    print(
        f"Ring tangential force:         "
        f"{result.F_t_ring_N:.3f} N"
    )

    print(
        f"Pin force from mesh:           "
        f"{result.F_pin_mesh_N:.3f} N"
    )

    print(
        f"Pin force from carrier:        "
        f"{result.F_pin_carrier_N:.3f} N"
    )

    print(
        f"Design pin force:              "
        f"{result.F_pin_design_N:.3f} N"
    )

    print(
        f"Sun mesh velocity:             "
        f"{result.relative_pitch_velocity_mps:.6f} m/s"
    )

    print(
        f"Ring mesh velocity:            "
        f"{result.ring_pitch_velocity_mps:.6f} m/s"
    )


# ============================================================
# TEST 1 — NORMAL CALCULATION
# Based on previous Zs=20, Zp=40, m=0.5 example
# ============================================================

def test_normal_calculation():

    inp = GearForceInput(

        # Previous planetary outputs
        T_s_nm=1.3070175438596494,
        T_c_nm=7.45,
        T_r_nm=6.208333333333334,

        d_s_mm=10.0,
        d_r_mm=50.0,
        center_distance_mm=15.0,

        n_s_rpm=540.0,
        n_c_rpm=90.0,

        n_planets=4,
    )

    cfg = GearForceConfig(
        pressure_angle_deg=20.0,

        # Temporary test-only value
        K_gamma=1.10,
    )

    result = evaluate_gear_forces(
        inp,
        cfg,
    )

    print_result(
        "TEST 1 — NORMAL GEAR FORCE CALCULATION",
        result,
    )

    assert result.feasible

    # --------------------------------------------------------
    # Check nominal tangential force
    # --------------------------------------------------------

    d_s_m = inp.d_s_mm / 1000.0

    expected_Ft_nom = (
        2.0
        * inp.T_s_nm
        / (inp.n_planets * d_s_m)
    )

    assert abs(
        result.F_t_nom_N
        - expected_Ft_nom
    ) < 1e-10

    # --------------------------------------------------------
    # Check K_gamma
    # --------------------------------------------------------

    expected_Ft = (
        cfg.K_gamma
        * expected_Ft_nom
    )

    assert abs(
        result.F_t_N
        - expected_Ft
    ) < 1e-10

    # --------------------------------------------------------
    # Check radial force
    # --------------------------------------------------------

    phi = radians(
        cfg.pressure_angle_deg
    )

    expected_Fr = (
        expected_Ft
        * tan(phi)
    )

    assert abs(
        result.F_r_N
        - expected_Fr
    ) < 1e-10

    # --------------------------------------------------------
    # Check normal force
    # --------------------------------------------------------

    expected_Fn = (
        expected_Ft
        / cos(phi)
    )

    assert abs(
        result.F_n_N
        - expected_Fn
    ) < 1e-10

    # --------------------------------------------------------
    # Spur gears -> zero axial force
    # --------------------------------------------------------

    assert result.F_a_N == 0.0

    print("\nPASS: gear-force equations are consistent.")


# ============================================================
# TEST 2 — PIN LOAD USES CONSERVATIVE MAXIMUM
# ============================================================

def test_pin_force_selection():

    inp = GearForceInput(
        T_s_nm=1.3070175438596494,
        T_c_nm=7.45,
        T_r_nm=6.208333333333334,

        d_s_mm=10.0,
        d_r_mm=50.0,
        center_distance_mm=15.0,

        n_s_rpm=540.0,
        n_c_rpm=90.0,

        n_planets=4,
    )

    cfg = GearForceConfig(
        pressure_angle_deg=20.0,
        K_gamma=1.10,
    )

    result = evaluate_gear_forces(
        inp,
        cfg,
    )

    expected_design_force = max(
        result.F_pin_mesh_N,
        result.F_pin_carrier_N,
    )

    assert abs(
        result.F_pin_design_N
        - expected_design_force
    ) < 1e-12

    print_result(
        "TEST 2 — CONSERVATIVE PIN LOAD SELECTION",
        result,
    )

    print(
        "\nPASS: larger pin-load estimate "
        "correctly selected."
    )


# ============================================================
# TEST 3 — K_GAMMA SCALING
# ============================================================

def test_K_gamma_scaling():

    inp = GearForceInput(
        T_s_nm=1.0,
        T_c_nm=6.0,
        T_r_nm=5.0,

        d_s_mm=10.0,
        d_r_mm=50.0,
        center_distance_mm=15.0,

        n_s_rpm=500.0,
        n_c_rpm=100.0,

        n_planets=4,
    )

    result_1 = evaluate_gear_forces(
        inp,
        GearForceConfig(
            pressure_angle_deg=20.0,
            K_gamma=1.0,
        ),
    )

    result_2 = evaluate_gear_forces(
        inp,
        GearForceConfig(
            pressure_angle_deg=20.0,
            K_gamma=1.2,
        ),
    )

    # All directly load-scaled forces should increase 20%
    assert abs(
        result_2.F_t_N
        / result_1.F_t_N
        - 1.2
    ) < 1e-12

    assert abs(
        result_2.F_r_N
        / result_1.F_r_N
        - 1.2
    ) < 1e-12

    assert abs(
        result_2.F_n_N
        / result_1.F_n_N
        - 1.2
    ) < 1e-12

    print("\n" + "=" * 72)
    print("TEST 3 — K_GAMMA SCALING")
    print("=" * 72)

    print("PASS: mesh forces scale correctly with K_gamma.")


# ============================================================
# TEST 4 — RELATIVE PITCH VELOCITY
# ============================================================

def test_pitch_velocity():

    inp = GearForceInput(
        T_s_nm=1.0,
        T_c_nm=6.0,
        T_r_nm=5.0,

        d_s_mm=20.0,
        d_r_mm=80.0,
        center_distance_mm=25.0,

        n_s_rpm=600.0,
        n_c_rpm=100.0,

        n_planets=3,
    )

    cfg = GearForceConfig(
        pressure_angle_deg=20.0,
        K_gamma=1.0,
    )

    result = evaluate_gear_forces(
        inp,
        cfg,
    )

    d_s_m = (
        inp.d_s_mm / 1000.0
    )

    expected_velocity = (
        pi
        * d_s_m
        * abs(
            inp.n_s_rpm
            - inp.n_c_rpm
        )
        / 60.0
    )

    assert abs(
        result.relative_pitch_velocity_mps
        - expected_velocity
    ) < 1e-12

    print_result(
        "TEST 4 — PITCH-LINE VELOCITY",
        result,
    )

    print(
        "\nPASS: relative pitch velocity "
        "correctly calculated."
    )


# ============================================================
# TEST 5 — INVALID INPUT
# ============================================================

def test_invalid_planet_count():

    inp = GearForceInput(
        T_s_nm=1.0,
        T_c_nm=6.0,
        T_r_nm=5.0,

        d_s_mm=10.0,
        d_r_mm=50.0,
        center_distance_mm=15.0,

        n_s_rpm=500.0,
        n_c_rpm=100.0,

        n_planets=0,
    )

    cfg = GearForceConfig(
        pressure_angle_deg=20.0,
        K_gamma=1.1,
    )

    try:

        evaluate_gear_forces(
            inp,
            cfg,
        )

    except ValueError as exc:

        print("\n" + "=" * 72)
        print("TEST 5 — INVALID INPUT")
        print("=" * 72)

        print(f"Expected error: {exc}")

        print(
            "\nPASS: invalid planet count "
            "correctly rejected."
        )

        return

    raise AssertionError(
        "Expected ValueError was not raised."
    )


# ============================================================
# RUN ALL TESTS
# ============================================================

if __name__ == "__main__":

    test_normal_calculation()
    test_pin_force_selection()
    test_K_gamma_scaling()
    test_pitch_velocity()
    test_invalid_planet_count()

    print("\n" + "=" * 72)
    print("ALL GEAR FORCE TESTS PASSED")
    print("=" * 72)