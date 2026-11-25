"""
Standalone tests for src/rotor_support.py

Run from project root:

    python -m tests.rotor_support

No bearing or material catalogue is required.
Synthetic catalogue entries are instantiated directly.
"""

from src.rotor_support import (
    RotorSupportMaterial,
    BallBearingSpec,
    RotorSupportInput,
    RotorSupportConfig,
    evaluate_rotor_support,
)


# ============================================================
# TEST MATERIAL
# ============================================================

TEST_MATERIAL = RotorSupportMaterial(
    name="Synthetic Test Steel",

    Sy_MPa=900.0,
    density_kg_m3=7850.0,
)


# ============================================================
# TEST BEARING
# ============================================================

TEST_BEARING = BallBearingSpec(
    designation="TEST-10",

    bore_mm=10.0,
    outer_diameter_mm=26.0,
    width_mm=8.0,

    C_N=5000.0,
    C0_N=2500.0,

    limiting_speed_rpm=20000.0,

    mass_kg=0.020,
)


# ============================================================
# BASE CONFIG
# ============================================================

BASE_CONFIG = RotorSupportConfig(

    plate_safety_factor=1.5,

    required_bearing_life_h=5000.0,

    min_static_safety_factor=1.5,

    gravity_m_s2=9.81,
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

    print("\nDRIVE PLATE")

    print(
        f"Hub diameter:                 "
        f"{result.hub_diameter_mm:.3f} mm"
    )

    print(
        f"Plate OD:                     "
        f"{result.plate_outer_diameter_mm:.3f} mm"
    )

    print(
        f"Plate thickness:              "
        f"{result.plate_thickness_mm:.6f} mm"
    )

    print(
        f"Plate mass:                   "
        f"{result.plate_mass_kg:.6f} kg"
    )

    print("\nHUB")

    print(
        f"Hub shear stress:             "
        f"{result.hub_shear_stress_MPa:.3f} MPa"
    )

    print(
        f"Hub von Mises stress:         "
        f"{result.hub_von_mises_MPa:.3f} MPa"
    )

    print(
        f"Hub yield safety factor:      "
        f"{result.hub_yield_safety_factor:.3f}"
    )

    print("\nBEARING REACTIONS")

    print(
        f"Total supported weight:       "
        f"{result.total_weight_N:.3f} N"
    )

    print(
        f"Reaction A:                   "
        f"{result.reaction_A_N:.3f} N"
    )

    print(
        f"Reaction B:                   "
        f"{result.reaction_B_N:.3f} N"
    )

    print("\nBEARING LIFE")

    print(
        f"L10h Bearing A:               "
        f"{result.L10h_A:.3e} h"
    )

    print(
        f"L10h Bearing B:               "
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
        f"{result.speed_ratio_A:.4f}"
    )

    print(
        f"Speed utilization B:          "
        f"{result.speed_ratio_B:.4f}"
    )


# ============================================================
# TEST 1 — NORMAL FEASIBLE CASE
# ============================================================

def test_feasible_support():

    inp = RotorSupportInput(

        T_s_nm=1.30,

        d_shaft_mm=8.0,

        n_s_rpm=600.0,

        rotor_outer_diameter_mm=80.0,

        supported_rotating_mass_kg=0.50,

        bearing_spacing_mm=40.0,

        # Midpoint CG
        cg_position_mm=20.0,
    )

    result = evaluate_rotor_support(
        inp,
        TEST_MATERIAL,
        TEST_BEARING,
        TEST_BEARING,
        BASE_CONFIG,
    )

    print_result(
        "TEST 1 — FEASIBLE ROTOR SUPPORT",
        result,
    )

    assert result.feasible

    print(
        "\nPASS: feasible rotor support correctly accepted."
    )


# ============================================================
# TEST 2 — MIDPOINT CG GIVES EQUAL REACTIONS
# ============================================================

def test_midpoint_reactions():

    inp = RotorSupportInput(
        T_s_nm=1.0,
        d_shaft_mm=8.0,
        n_s_rpm=500.0,
        rotor_outer_diameter_mm=80.0,

        supported_rotating_mass_kg=1.0,

        bearing_spacing_mm=50.0,
        cg_position_mm=25.0,
    )

    result = evaluate_rotor_support(
        inp,
        TEST_MATERIAL,
        TEST_BEARING,
        TEST_BEARING,
        BASE_CONFIG,
    )

    assert abs(
        result.reaction_A_N
        -
        result.reaction_B_N
    ) < 1e-12

    expected_reaction = (
        1.0
        * 9.81
        / 2.0
    )

    assert abs(
        result.reaction_A_N
        -
        expected_reaction
    ) < 1e-12

    print("\n" + "=" * 76)
    print("TEST 2 — MIDPOINT CG")
    print("=" * 76)

    print(
        f"R_A = {result.reaction_A_N:.4f} N"
    )

    print(
        f"R_B = {result.reaction_B_N:.4f} N"
    )

    print(
        "\nPASS: midpoint CG gives equal reactions."
    )


# ============================================================
# TEST 3 — BEARING BORE REJECTION
# ============================================================

def test_bore_rejection():

    small_bearing = BallBearingSpec(
        designation="TEST-SMALL",

        bore_mm=6.0,
        outer_diameter_mm=19.0,
        width_mm=6.0,

        C_N=5000.0,
        C0_N=2500.0,

        limiting_speed_rpm=20000.0,

        mass_kg=0.010,
    )

    inp = RotorSupportInput(
        T_s_nm=1.0,

        # Requires > 6 mm
        d_shaft_mm=8.0,

        n_s_rpm=500.0,

        rotor_outer_diameter_mm=80.0,

        supported_rotating_mass_kg=0.5,

        bearing_spacing_mm=40.0,
        cg_position_mm=20.0,
    )

    result = evaluate_rotor_support(
        inp,
        TEST_MATERIAL,
        small_bearing,
        TEST_BEARING,
        BASE_CONFIG,
    )

    print_result(
        "TEST 3 — BEARING BORE REJECTION",
        result,
    )

    assert not result.feasible

    assert (
        result.rejection_reason
        ==
        "bearing_A_bore_below_required_shaft_diameter"
    )

    print(
        "\nPASS: undersized bearing bore correctly rejected."
    )


# ============================================================
# TEST 4 — BEARING LIFE REJECTION
# ============================================================

def test_life_rejection():

    weak_bearing = BallBearingSpec(
        designation="TEST-WEAK",

        bore_mm=10.0,
        outer_diameter_mm=26.0,
        width_mm=8.0,

        # Deliberately tiny dynamic capacity
        C_N=10.0,

        C0_N=1000.0,

        limiting_speed_rpm=20000.0,

        mass_kg=0.020,
    )

    inp = RotorSupportInput(
        T_s_nm=1.0,
        d_shaft_mm=8.0,

        n_s_rpm=1000.0,

        rotor_outer_diameter_mm=80.0,

        supported_rotating_mass_kg=10.0,

        bearing_spacing_mm=40.0,
        cg_position_mm=20.0,
    )

    result = evaluate_rotor_support(
        inp,
        TEST_MATERIAL,
        weak_bearing,
        weak_bearing,
        BASE_CONFIG,
    )

    print_result(
        "TEST 4 — BEARING LIFE REJECTION",
        result,
    )

    assert not result.feasible

    assert result.rejection_reason in (
        "bearing_A_life_below_requirement",
        "bearing_B_life_below_requirement",
    )

    print(
        "\nPASS: inadequate bearing life correctly rejected."
    )


# ============================================================
# TEST 5 — STATIC SAFETY REJECTION
# ============================================================

def test_static_rejection():

    weak_static_bearing = BallBearingSpec(
        designation="TEST-STATIC-WEAK",

        bore_mm=10.0,
        outer_diameter_mm=26.0,
        width_mm=8.0,

        # Very large C -> dynamic life passes
        C_N=100000.0,

        # Very small static rating
        C0_N=5.0,

        limiting_speed_rpm=20000.0,

        mass_kg=0.020,
    )

    inp = RotorSupportInput(
        T_s_nm=1.0,
        d_shaft_mm=8.0,
        n_s_rpm=500.0,

        rotor_outer_diameter_mm=80.0,

        supported_rotating_mass_kg=2.0,

        bearing_spacing_mm=40.0,
        cg_position_mm=20.0,
    )

    result = evaluate_rotor_support(
        inp,
        TEST_MATERIAL,
        weak_static_bearing,
        weak_static_bearing,
        BASE_CONFIG,
    )

    print_result(
        "TEST 5 — STATIC SAFETY REJECTION",
        result,
    )

    assert not result.feasible

    assert result.rejection_reason in (
        "bearing_A_static_safety_below_requirement",
        "bearing_B_static_safety_below_requirement",
    )

    print(
        "\nPASS: inadequate static capacity correctly rejected."
    )


# ============================================================
# TEST 6 — BEARING SPEED REJECTION
# ============================================================

def test_speed_rejection():

    slow_bearing = BallBearingSpec(
        designation="TEST-SLOW",

        bore_mm=10.0,
        outer_diameter_mm=26.0,
        width_mm=8.0,

        C_N=100000.0,
        C0_N=100000.0,

        # Deliberately low speed limit
        limiting_speed_rpm=400.0,

        mass_kg=0.020,
    )

    inp = RotorSupportInput(
        T_s_nm=1.0,
        d_shaft_mm=8.0,

        # Above bearing speed limit
        n_s_rpm=600.0,

        rotor_outer_diameter_mm=80.0,

        supported_rotating_mass_kg=0.5,

        bearing_spacing_mm=40.0,
        cg_position_mm=20.0,
    )

    result = evaluate_rotor_support(
        inp,
        TEST_MATERIAL,
        slow_bearing,
        slow_bearing,
        BASE_CONFIG,
    )

    print_result(
        "TEST 6 — BEARING SPEED REJECTION",
        result,
    )

    assert not result.feasible

    assert result.rejection_reason in (
        "bearing_A_speed_exceeds_limit",
        "bearing_B_speed_exceeds_limit",
    )

    print(
        "\nPASS: excessive bearing speed correctly rejected."
    )


# ============================================================
# RUN ALL TESTS
# ============================================================

if __name__ == "__main__":

    test_feasible_support()
    test_midpoint_reactions()
    test_bore_rejection()
    test_life_rejection()
    test_static_rejection()
    test_speed_rejection()

    print("\n" + "=" * 76)
    print("ALL ROTOR SUPPORT TESTS PASSED")
    print("=" * 76)