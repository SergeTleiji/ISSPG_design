"""
Standalone tests for src/output_system.py

Run from project root:

    python -m tests.output_system

No bearing or material catalogue is required.
Synthetic entries are instantiated directly.
"""

from math import pi, sqrt

from src.output_system import (
    OutputShaftMaterial,
    OutputBearingSpec,
    OutputSystemInput,
    OutputSystemConfig,
    evaluate_output_system,
)


# ============================================================
# TEST MATERIAL
# ============================================================

TEST_STEEL = OutputShaftMaterial(
    name="Synthetic Test Steel",
    Sy_MPa=500.0,
)


# ============================================================
# TEST BEARING
# ============================================================

TEST_BEARING = OutputBearingSpec(
    designation="TEST-6000",

    bore_mm=10.0,
    outer_diameter_mm=26.0,
    width_mm=9.0,

    C_N=5000.0,
    C0_N=2500.0,

    limiting_speed_rpm=20000.0,

    mass_kg=0.020,
)


# ============================================================
# BASE CONFIG
# ============================================================

BASE_CONFIG = OutputSystemConfig(

    shaft_safety_factor=2.0,

    inner_ring_spacer_mm=20.0,

    load_overhang_mm=20.0,

    required_bearing_life_h=5000.0,

    min_static_safety_factor=1.5,
)


# ============================================================
# BASE INPUT
# ============================================================

BASE_INPUT = OutputSystemInput(

    T_c_nm=7.45,

    external_radial_load_N=490.5,

    n_c_rpm=90.0,
)


def print_result(title, result):

    print("\n" + "=" * 76)
    print(title)
    print("=" * 76)

    print(f"Feasible:                     {result.feasible}")
    print(f"Rejection reason:             {result.rejection_reason}")

    print(f"Material:                     {result.material_name}")

    print(
        f"Bearing A:                    "
        f"{result.bearing_A_designation}"
    )

    print(
        f"Bearing B:                    "
        f"{result.bearing_B_designation}"
    )

    print("\nGEOMETRY")

    print(
        f"Bearing spacing:              "
        f"{result.bearing_spacing_mm:.3f} mm"
    )

    print(
        f"Load overhang:                "
        f"{result.load_overhang_mm:.3f} mm"
    )

    print("\nREACTIONS")

    print(
        f"Reaction A:                   "
        f"{result.reaction_A_N:.3f} N"
    )

    print(
        f"Reaction B:                   "
        f"{result.reaction_B_N:.3f} N"
    )

    print("\nSHAFT")

    print(
        f"Maximum bending moment:       "
        f"{result.max_bending_moment_Nmm:.3f} N.mm"
    )

    print(
        f"Theoretical minimum diameter: "
        f"{result.theoretical_min_diameter_mm:.3f} mm"
    )

    print(
        f"Actual shaft diameter:        "
        f"{result.actual_shaft_diameter_mm:.3f} mm"
    )

    print(
        f"Bending stress:               "
        f"{result.bending_stress_MPa:.3f} MPa"
    )

    print(
        f"Shear stress:                 "
        f"{result.shear_stress_MPa:.3f} MPa"
    )

    print(
        f"Von Mises stress:             "
        f"{result.von_mises_stress_MPa:.3f} MPa"
    )

    print(
        f"Achieved shaft SF:            "
        f"{result.achieved_shaft_safety_factor:.3f}"
    )

    print("\nBEARINGS")

    print(
        f"P_A:                          "
        f"{result.P_A_N:.3f} N"
    )

    print(
        f"P_B:                          "
        f"{result.P_B_N:.3f} N"
    )

    print(
        f"L10h A:                       "
        f"{result.L10h_A:.3e} h"
    )

    print(
        f"L10h B:                       "
        f"{result.L10h_B:.3e} h"
    )

    print(
        f"Static safety A:              "
        f"{result.s0_A:.3f}"
    )

    print(
        f"Static safety B:              "
        f"{result.s0_B:.3f}"
    )

    print(
        f"Speed utilization A:          "
        f"{result.speed_ratio_A:.5f}"
    )

    print(
        f"Speed utilization B:          "
        f"{result.speed_ratio_B:.5f}"
    )


# ============================================================
# TEST 1 — FEASIBLE OUTPUT SYSTEM
# ============================================================

def test_feasible_output_system():

    result = evaluate_output_system(
        BASE_INPUT,
        TEST_STEEL,
        TEST_BEARING,
        TEST_BEARING,
        BASE_CONFIG,
    )

    print_result(
        "TEST 1 — FEASIBLE OUTPUT SYSTEM",
        result,
    )

    assert result.feasible

    assert (
        result.actual_shaft_diameter_mm
        >=
        result.theoretical_min_diameter_mm
    )

    print(
        "\nPASS: feasible output system accepted."
    )


# ============================================================
# TEST 2 — BEARING REACTION EQUILIBRIUM
# ============================================================

def test_reaction_equilibrium():

    result = evaluate_output_system(
        BASE_INPUT,
        TEST_STEEL,
        TEST_BEARING,
        TEST_BEARING,
        BASE_CONFIG,
    )

    # Signed reactions must sum to applied load.
    assert abs(
        (
            result.reaction_A_N
            +
            result.reaction_B_N
        )
        -
        BASE_INPUT.external_radial_load_N
    ) < 1e-10

    print("\n" + "=" * 76)
    print("TEST 2 — REACTION EQUILIBRIUM")
    print("=" * 76)

    print(
        f"R_A + R_B = "
        f"{result.reaction_A_N + result.reaction_B_N:.6f} N"
    )

    print(
        "\nPASS: output bearing reactions satisfy equilibrium."
    )


# ============================================================
# TEST 3 — SHAFT DIAMETER EQUATION
# ============================================================

def test_shaft_diameter_equation():

    result = evaluate_output_system(
        BASE_INPUT,
        TEST_STEEL,
        TEST_BEARING,
        TEST_BEARING,
        BASE_CONFIG,
    )

    F = (
        BASE_INPUT.external_radial_load_N
    )

    e = (
        BASE_CONFIG.load_overhang_mm
    )

    M = F * e

    T = (
        BASE_INPUT.T_c_nm
        * 1000.0
    )

    expected_d = (
        (
            16.0
            * BASE_CONFIG.shaft_safety_factor
            /
            (
                pi
                * TEST_STEEL.Sy_MPa
            )
        )
        *
        sqrt(
            4.0 * M**2
            +
            3.0 * T**2
        )
    ) ** (1.0 / 3.0)

    assert abs(
        result.theoretical_min_diameter_mm
        -
        expected_d
    ) < 1e-12

    print("\n" + "=" * 76)
    print("TEST 3 — SHAFT DIAMETER EQUATION")
    print("=" * 76)

    print(
        f"Expected: {expected_d:.8f} mm"
    )

    print(
        f"Solver:   "
        f"{result.theoretical_min_diameter_mm:.8f} mm"
    )

    print(
        "\nPASS: combined bending/torsion sizing is consistent."
    )


# ============================================================
# TEST 4 — DIFFERENT BEARING BORES REJECTED
# ============================================================

def test_common_bore_rejection():

    different_bearing = OutputBearingSpec(
        designation="TEST-12MM",

        bore_mm=12.0,
        outer_diameter_mm=28.0,
        width_mm=8.0,

        C_N=5000.0,
        C0_N=2500.0,

        limiting_speed_rpm=20000.0,

        mass_kg=0.020,
    )

    result = evaluate_output_system(
        BASE_INPUT,
        TEST_STEEL,
        TEST_BEARING,
        different_bearing,
        BASE_CONFIG,
    )

    print_result(
        "TEST 4 — COMMON BORE REJECTION",
        result,
    )

    assert not result.feasible

    assert (
        result.rejection_reason
        ==
        "output_bearings_do_not_have_common_bore"
    )

    print(
        "\nPASS: unequal output bearing bores correctly rejected."
    )


# ============================================================
# TEST 5 — BEARING BORE TOO SMALL
# ============================================================

def test_bore_rejection():

    small_bearing = OutputBearingSpec(
        designation="TEST-6MM",

        bore_mm=6.0,
        outer_diameter_mm=19.0,
        width_mm=6.0,

        C_N=100000.0,
        C0_N=100000.0,

        limiting_speed_rpm=20000.0,

        mass_kg=0.010,
    )

    result = evaluate_output_system(
        BASE_INPUT,
        TEST_STEEL,
        small_bearing,
        small_bearing,
        BASE_CONFIG,
    )

    print_result(
        "TEST 5 — OUTPUT SHAFT BORE REJECTION",
        result,
    )

    assert not result.feasible

    assert (
        result.rejection_reason
        ==
        "bearing_bore_below_required_output_shaft_diameter"
    )

    print(
        "\nPASS: undersized catalogue bore correctly rejected."
    )


# ============================================================
# TEST 6 — BEARING LIFE REJECTION
# ============================================================

def test_life_rejection():

    weak_bearing = OutputBearingSpec(
        designation="TEST-WEAK",

        bore_mm=10.0,
        outer_diameter_mm=26.0,
        width_mm=9.0,

        # Deliberately low dynamic rating
        C_N=100.0,

        C0_N=100000.0,

        limiting_speed_rpm=20000.0,

        mass_kg=0.020,
    )

    result = evaluate_output_system(
        BASE_INPUT,
        TEST_STEEL,
        weak_bearing,
        weak_bearing,
        BASE_CONFIG,
    )

    print_result(
        "TEST 6 — OUTPUT BEARING LIFE REJECTION",
        result,
    )

    assert not result.feasible

    assert result.rejection_reason in (
        "output_bearing_A_life_below_requirement",
        "output_bearing_B_life_below_requirement",
    )

    print(
        "\nPASS: inadequate bearing life correctly rejected."
    )


# ============================================================
# TEST 7 — STATIC SAFETY REJECTION
# ============================================================

def test_static_rejection():

    weak_static_bearing = OutputBearingSpec(
        designation="TEST-STATIC-WEAK",

        bore_mm=10.0,
        outer_diameter_mm=26.0,
        width_mm=9.0,

        # Dynamic life easily passes
        C_N=100000.0,

        # Static rating deliberately tiny
        C0_N=100.0,

        limiting_speed_rpm=20000.0,

        mass_kg=0.020,
    )

    result = evaluate_output_system(
        BASE_INPUT,
        TEST_STEEL,
        weak_static_bearing,
        weak_static_bearing,
        BASE_CONFIG,
    )

    print_result(
        "TEST 7 — OUTPUT BEARING STATIC REJECTION",
        result,
    )

    assert not result.feasible

    assert result.rejection_reason in (
        "output_bearing_A_static_safety_below_requirement",
        "output_bearing_B_static_safety_below_requirement",
    )

    print(
        "\nPASS: inadequate static capacity correctly rejected."
    )


# ============================================================
# TEST 8 — BEARING SPEED REJECTION
# ============================================================

def test_speed_rejection():

    slow_bearing = OutputBearingSpec(
        designation="TEST-SLOW",

        bore_mm=10.0,
        outer_diameter_mm=26.0,
        width_mm=9.0,

        C_N=100000.0,
        C0_N=100000.0,

        # Output speed = 90 rpm
        limiting_speed_rpm=50.0,

        mass_kg=0.020,
    )

    result = evaluate_output_system(
        BASE_INPUT,
        TEST_STEEL,
        slow_bearing,
        slow_bearing,
        BASE_CONFIG,
    )

    print_result(
        "TEST 8 — OUTPUT BEARING SPEED REJECTION",
        result,
    )

    assert not result.feasible

    assert result.rejection_reason in (
        "output_bearing_A_speed_exceeds_limit",
        "output_bearing_B_speed_exceeds_limit",
    )

    print(
        "\nPASS: excessive bearing speed correctly rejected."
    )


# ============================================================
# RUN ALL TESTS
# ============================================================

if __name__ == "__main__":

    test_feasible_output_system()
    test_reaction_equilibrium()
    test_shaft_diameter_equation()
    test_common_bore_rejection()
    test_bore_rejection()
    test_life_rejection()
    test_static_rejection()
    test_speed_rejection()

    print("\n" + "=" * 76)
    print("ALL OUTPUT SYSTEM TESTS PASSED")
    print("=" * 76)