"""
Standalone tests for src/sun_shaft.py

Run from project root:

    python -m tests.sun_shaft

No material catalogue is required.
A synthetic steel is instantiated directly for testing.
"""

from math import pi, sqrt, radians

from src.sun_shaft import (
    ShaftMaterial,
    SunShaftInput,
    SunShaftConfig,
    evaluate_sun_shaft,
)


# ============================================================
# TEST MATERIAL
# ============================================================

TEST_STEEL = ShaftMaterial(
    name="Synthetic Test Steel",

    Sy_MPa=1000.0,
    Sut_MPa=1100.0,

    # Test-only endurance limit
    Se_prime_MPa=550.0,

    shear_modulus_GPa=80.0,
)


# ============================================================
# BASE CONFIG
# ============================================================

BASE_CONFIG = SunShaftConfig(

    fatigue_safety_factor=1.5,
    yield_safety_factor=1.5,

    marin_surface_factor=0.85,
    marin_size_factor=0.90,

    # Keep = 1 because torsion is already handled through DE
    marin_load_factor=1.0,

    marin_temperature_factor=1.0,
    marin_reliability_factor=0.90,
    marin_misc_factor=1.0,

    effective_torsion_length_mm=20.0,

    max_twist_deg=0.5,

    min_root_ligament_mm=1.0,
)


def print_result(title, result):

    print("\n" + "=" * 76)
    print(title)
    print("=" * 76)

    print(f"Feasible:                     {result.feasible}")
    print(f"Rejection reason:             {result.rejection_reason}")

    print(f"Material:                     {result.material_name}")

    print(
        f"Mean torque:                  "
        f"{result.T_mean_nm:.4f} N.m"
    )

    print(
        f"Alternating torque:           "
        f"{result.T_alt_nm:.4f} N.m"
    )

    print(
        f"Peak absolute torque:         "
        f"{result.T_peak_abs_nm:.4f} N.m"
    )

    print(
        f"Modified endurance limit:     "
        f"{result.Se_MPa:.3f} MPa"
    )

    print("\nREQUIRED DIAMETERS")

    print(
        f"Fatigue diameter:             "
        f"{result.d_fatigue_mm:.3f} mm"
    )

    print(
        f"Yield diameter:               "
        f"{result.d_yield_mm:.3f} mm"
    )

    print(
        f"Stiffness diameter:           "
        f"{result.d_stiffness_mm:.3f} mm"
    )

    print(
        f"Required shaft diameter:      "
        f"{result.d_required_mm:.3f} mm"
    )

    print(
        f"Governing requirement:        "
        f"{result.governing_requirement}"
    )

    print("\nSUN ROOT")

    print(
        f"Sun root diameter:            "
        f"{result.sun_root_diameter_mm:.3f} mm"
    )

    print(
        f"Max shaft diameter:           "
        f"{result.max_shaft_diameter_mm:.3f} mm"
    )

    print(
        f"Resulting root ligament:      "
        f"{result.root_ligament_mm:.3f} mm"
    )

    print("\nVERIFICATION")

    print(
        f"Peak shear stress:            "
        f"{result.peak_shear_stress_MPa:.3f} MPa"
    )

    print(
        f"Peak von Mises stress:        "
        f"{result.peak_von_mises_MPa:.3f} MPa"
    )

    print(
        f"Achieved fatigue SF:          "
        f"{result.fatigue_safety_achieved:.3f}"
    )

    print(
        f"Achieved yield SF:            "
        f"{result.yield_safety_achieved:.3f}"
    )

    print(
        f"Shaft twist:                  "
        f"{result.twist_deg:.6f} deg"
    )


# ============================================================
# TEST 1 — NORMAL FEASIBLE SHAFT
# ============================================================

def test_feasible_shaft():

    inp = SunShaftInput(

        # Example torque cycle
        T_max_nm=1.30,
        T_min_nm=0.20,

        # Larger test sun so packaging is feasible
        module_mm=1.0,
        z_s=20,
    )

    result = evaluate_sun_shaft(
        inp,
        TEST_STEEL,
        BASE_CONFIG,
    )

    print_result(
        "TEST 1 — FEASIBLE SUN SHAFT",
        result,
    )

    assert result.feasible

    assert (
        result.d_required_mm
        <=
        result.max_shaft_diameter_mm
    )

    print("\nPASS: feasible shaft correctly accepted.")


# ============================================================
# TEST 2 — MEAN / ALTERNATING TORQUE
# ============================================================

def test_torque_decomposition():

    inp = SunShaftInput(
        T_max_nm=2.0,
        T_min_nm=0.0,

        module_mm=1.0,
        z_s=20,
    )

    result = evaluate_sun_shaft(
        inp,
        TEST_STEEL,
        BASE_CONFIG,
    )

    assert abs(
        result.T_mean_nm - 1.0
    ) < 1e-12

    assert abs(
        result.T_alt_nm - 1.0
    ) < 1e-12

    assert abs(
        result.T_peak_abs_nm - 2.0
    ) < 1e-12

    print("\n" + "=" * 76)
    print("TEST 2 — TORQUE DECOMPOSITION")
    print("=" * 76)

    print("PASS: mean and alternating torque are correct.")


# ============================================================
# TEST 3 — FATIGUE DIAMETER EQUATION
# ============================================================

def test_fatigue_diameter():

    inp = SunShaftInput(
        T_max_nm=1.5,
        T_min_nm=0.5,

        module_mm=1.0,
        z_s=20,
    )

    result = evaluate_sun_shaft(
        inp,
        TEST_STEEL,
        BASE_CONFIG,
    )

    T_m = (
        inp.T_max_nm
        + inp.T_min_nm
    ) / 2.0

    T_a = (
        inp.T_max_nm
        - inp.T_min_nm
    ) / 2.0

    T_m_Nmm = T_m * 1000.0
    T_a_Nmm = T_a * 1000.0

    Se = (
        BASE_CONFIG.marin_surface_factor
        * BASE_CONFIG.marin_size_factor
        * BASE_CONFIG.marin_load_factor
        * BASE_CONFIG.marin_temperature_factor
        * BASE_CONFIG.marin_reliability_factor
        * BASE_CONFIG.marin_misc_factor
        * TEST_STEEL.Se_prime_MPa
    )

    expected_d = (
        (
            16.0
            * sqrt(3.0)
            * BASE_CONFIG.fatigue_safety_factor
            / pi
        )
        * (
            T_a_Nmm / Se
            +
            T_m_Nmm / TEST_STEEL.Sut_MPa
        )
    ) ** (1.0 / 3.0)

    assert abs(
        result.d_fatigue_mm
        - expected_d
    ) < 1e-12

    print("\n" + "=" * 76)
    print("TEST 3 — FATIGUE DIAMETER")
    print("=" * 76)

    print(f"Expected: {expected_d:.8f} mm")
    print(f"Solver:   {result.d_fatigue_mm:.8f} mm")

    print("\nPASS: Goodman fatigue sizing is consistent.")


# ============================================================
# TEST 4 — STIFFNESS DIAMETER EQUATION
# ============================================================

def test_stiffness_diameter():

    inp = SunShaftInput(
        T_max_nm=2.0,
        T_min_nm=0.0,

        module_mm=1.0,
        z_s=20,
    )

    result = evaluate_sun_shaft(
        inp,
        TEST_STEEL,
        BASE_CONFIG,
    )

    T_Nmm = 2.0 * 1000.0

    G_MPa = (
        TEST_STEEL.shear_modulus_GPa
        * 1000.0
    )

    theta_allow = radians(
        BASE_CONFIG.max_twist_deg
    )

    expected_d = (
        (
            32.0
            * T_Nmm
            * BASE_CONFIG.effective_torsion_length_mm
        )
        /
        (
            pi
            * G_MPa
            * theta_allow
        )
    ) ** 0.25

    assert abs(
        result.d_stiffness_mm
        - expected_d
    ) < 1e-12

    print("\n" + "=" * 76)
    print("TEST 4 — TORSIONAL STIFFNESS")
    print("=" * 76)

    print(f"Expected: {expected_d:.8f} mm")
    print(f"Solver:   {result.d_stiffness_mm:.8f} mm")

    print("\nPASS: torsional stiffness sizing is consistent.")


# ============================================================
# TEST 5 — SUN ROOT PACKAGING REJECTION
# ============================================================

def test_root_packaging_rejection():

    inp = SunShaftInput(

        # High torque
        T_max_nm=5.0,
        T_min_nm=0.0,

        # Deliberately tiny sun root
        module_mm=0.4,
        z_s=12,
    )

    result = evaluate_sun_shaft(
        inp,
        TEST_STEEL,
        BASE_CONFIG,
    )

    print_result(
        "TEST 5 — SUN ROOT PACKAGING REJECTION",
        result,
    )

    assert not result.feasible

    assert result.rejection_reason in (
        "required_shaft_diameter_exceeds_sun_root_capacity",
        "insufficient_sun_root_for_minimum_ligament",
    )

    print(
        "\nPASS: shaft that cannot fit inside "
        "the sun root correctly rejected."
    )


# ============================================================
# TEST 6 — INVALID TORQUE RANGE
# ============================================================

def test_invalid_torque_range():

    inp = SunShaftInput(

        # Deliberately invalid
        T_max_nm=1.0,
        T_min_nm=2.0,

        module_mm=1.0,
        z_s=20,
    )

    try:

        evaluate_sun_shaft(
            inp,
            TEST_STEEL,
            BASE_CONFIG,
        )

    except ValueError as exc:

        print("\n" + "=" * 76)
        print("TEST 6 — INVALID TORQUE RANGE")
        print("=" * 76)

        print(f"Expected error: {exc}")

        print(
            "\nPASS: invalid torque range "
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

    test_feasible_shaft()
    test_torque_decomposition()
    test_fatigue_diameter()
    test_stiffness_diameter()
    test_root_packaging_rejection()
    test_invalid_torque_range()

    print("\n" + "=" * 76)
    print("ALL SUN SHAFT TESTS PASSED")
    print("=" * 76)