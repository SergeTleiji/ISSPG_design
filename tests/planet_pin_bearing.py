"""
Standalone tests for src/planet_pin_bearing.py

Run from project root:

    python -m tests.planet_pin_bearing

No bearing or material catalogue is required.
Synthetic entries are instantiated directly.
"""

from src.planet_pin_bearing import (
    PinMaterial,
    NeedleBearingSpec,
    PlanetPinBearingInput,
    PlanetPinBearingConfig,
    evaluate_planet_pin_bearing,
)


# ============================================================
# TEST MATERIAL
# ============================================================

TEST_STEEL = PinMaterial(
    name="Synthetic Test Steel",

    Sy_MPa=700.0,
    E_GPa=205.0,
)


# ============================================================
# TEST BEARING
# ============================================================

TEST_BEARING = NeedleBearingSpec(
    designation="TEST-NKI-10",

    bore_mm=10.0,
    outer_diameter_mm=20.0,
    width_mm=10.0,

    C_N=6000.0,
    C0_N=5000.0,

    limiting_speed_rpm=10000.0,

    mass_kg=0.020,
)


# ============================================================
# BASE CONFIG
# ============================================================

BASE_CONFIG = PlanetPinBearingConfig(

    pin_safety_factor=2.0,

    max_pin_deflection_mm=0.05,

    max_pin_tilt_deg=0.10,

    carrier_planet_clearance_mm=1.0,

    axial_bearing_clearance_mm=0.5,

    min_planet_root_ligament_mm=2.0,

    required_bearing_life_h=5000.0,

    min_static_safety_factor=1.5,
)


# ============================================================
# BASE INPUT
# ============================================================

BASE_INPUT = PlanetPinBearingInput(

    F_pin_N=300.0,

    n_p_rpm=-135.0,
    n_c_rpm=90.0,

    z_p=40,
    module_mm=1.0,

    face_width_mm=12.0,
)


def print_result(title, result):

    print("\n" + "=" * 76)
    print(title)
    print("=" * 76)

    print(f"Feasible:                     {result.feasible}")
    print(f"Rejection reason:             {result.rejection_reason}")

    print(f"Material:                     {result.material_name}")
    print(f"Bearing:                      {result.bearing_designation}")

    print("\nPIN GEOMETRY")

    print(
        f"Pin diameter:                 "
        f"{result.pin_diameter_mm:.3f} mm"
    )

    print(
        f"Load lever arm:               "
        f"{result.load_lever_arm_mm:.3f} mm"
    )

    print("\nPIN STRESS")

    print(
        f"Bending moment:               "
        f"{result.bending_moment_Nmm:.3f} N.mm"
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
        f"Pin safety factor:            "
        f"{result.pin_safety_factor:.3f}"
    )

    print("\nPIN STIFFNESS")

    print(
        f"Pin deflection:               "
        f"{result.pin_deflection_mm:.6f} mm"
    )

    print(
        f"Pin tilt:                     "
        f"{result.pin_tilt_deg:.6f} deg"
    )

    print("\nBEARING")

    print(
        f"Relative bearing speed:       "
        f"{result.bearing_relative_speed_rpm:.3f} rpm"
    )

    print(
        f"Bearing speed utilization:    "
        f"{result.bearing_speed_ratio:.5f}"
    )

    print(
        f"L10h:                         "
        f"{result.L10h:.3e} h"
    )

    print(
        f"Static safety factor:         "
        f"{result.static_safety_factor:.3f}"
    )

    print("\nPLANET PACKAGING")

    print(
        f"Planet root diameter:         "
        f"{result.planet_root_diameter_mm:.3f} mm"
    )

    print(
        f"Available radial ligament:    "
        f"{result.available_radial_ligament_mm:.3f} mm"
    )

    print(
        f"Required axial bearing space: "
        f"{result.required_axial_space_mm:.3f} mm"
    )


# ============================================================
# TEST 1 — FEASIBLE PIN + BEARING
# ============================================================

def test_feasible_candidate():

    result = evaluate_planet_pin_bearing(
        BASE_INPUT,
        TEST_STEEL,
        TEST_BEARING,
        BASE_CONFIG,
    )

    print_result(
        "TEST 1 — FEASIBLE PLANET PIN + BEARING",
        result,
    )

    assert result.feasible

    assert (
        result.pin_diameter_mm
        ==
        TEST_BEARING.bore_mm
    )

    assert (
        result.pin_safety_factor
        >=
        BASE_CONFIG.pin_safety_factor
    )

    print(
        "\nPASS: feasible pin/bearing combination accepted."
    )


# ============================================================
# TEST 2 — RELATIVE BEARING SPEED
# ============================================================

def test_relative_speed():

    result = evaluate_planet_pin_bearing(
        BASE_INPUT,
        TEST_STEEL,
        TEST_BEARING,
        BASE_CONFIG,
    )

    expected_speed = abs(
        BASE_INPUT.n_p_rpm
        -
        BASE_INPUT.n_c_rpm
    )

    assert abs(
        result.bearing_relative_speed_rpm
        -
        expected_speed
    ) < 1e-12

    print("\n" + "=" * 76)
    print("TEST 2 — RELATIVE BEARING SPEED")
    print("=" * 76)

    print(
        f"Expected: {expected_speed:.3f} rpm"
    )

    print(
        f"Solver:   "
        f"{result.bearing_relative_speed_rpm:.3f} rpm"
    )

    print(
        "\nPASS: planet-to-carrier relative speed is correct."
    )


# ============================================================
# TEST 3 — PIN STRENGTH REJECTION
# ============================================================

def test_pin_strength_rejection():

    small_pin_bearing = NeedleBearingSpec(
        designation="TEST-SMALL-PIN",

        bore_mm=4.0,
        outer_diameter_mm=10.0,
        width_mm=8.0,

        C_N=100000.0,
        C0_N=100000.0,

        limiting_speed_rpm=10000.0,

        mass_kg=0.010,
    )

    inp = PlanetPinBearingInput(
        F_pin_N=1000.0,

        n_p_rpm=-135.0,
        n_c_rpm=90.0,

        z_p=40,
        module_mm=1.0,

        face_width_mm=12.0,
    )

    result = evaluate_planet_pin_bearing(
        inp,
        TEST_STEEL,
        small_pin_bearing,
        BASE_CONFIG,
    )

    print_result(
        "TEST 3 — PIN STRENGTH REJECTION",
        result,
    )

    assert not result.feasible

    assert (
        result.rejection_reason
        ==
        "pin_static_safety_below_requirement"
    )

    print(
        "\nPASS: structurally undersized pin correctly rejected."
    )


# ============================================================
# TEST 4 — RADIAL PACKAGING REJECTION
# ============================================================

def test_radial_packaging_rejection():

    oversized_bearing = NeedleBearingSpec(
        designation="TEST-OVERSIZED",

        bore_mm=10.0,
        outer_diameter_mm=40.0,
        width_mm=10.0,

        C_N=100000.0,
        C0_N=100000.0,

        limiting_speed_rpm=10000.0,

        mass_kg=0.050,
    )

    result = evaluate_planet_pin_bearing(
        BASE_INPUT,
        TEST_STEEL,
        oversized_bearing,
        BASE_CONFIG,
    )

    print_result(
        "TEST 4 — RADIAL PACKAGING REJECTION",
        result,
    )

    assert not result.feasible

    assert (
        result.rejection_reason
        ==
        "bearing_OD_exceeds_planet_root_capacity"
    )

    print(
        "\nPASS: bearing that does not fit inside "
        "planet root correctly rejected."
    )


# ============================================================
# TEST 5 — AXIAL PACKAGING REJECTION
# ============================================================

def test_axial_packaging_rejection():

    wide_bearing = NeedleBearingSpec(
        designation="TEST-WIDE",

        bore_mm=10.0,
        outer_diameter_mm=20.0,

        # 12 + 2*0.5 = 13 mm > 12 mm face width
        width_mm=12.0,

        C_N=100000.0,
        C0_N=100000.0,

        limiting_speed_rpm=10000.0,

        mass_kg=0.020,
    )

    result = evaluate_planet_pin_bearing(
        BASE_INPUT,
        TEST_STEEL,
        wide_bearing,
        BASE_CONFIG,
    )

    print_result(
        "TEST 5 — AXIAL PACKAGING REJECTION",
        result,
    )

    assert not result.feasible

    assert (
        result.rejection_reason
        ==
        "bearing_width_exceeds_planet_face_width"
    )

    print(
        "\nPASS: excessive bearing width correctly rejected."
    )


# ============================================================
# TEST 6 — DEFLECTION REJECTION
# ============================================================

def test_deflection_rejection():

    strict_config = PlanetPinBearingConfig(

        pin_safety_factor=1.0,

        # Deliberately tiny
        max_pin_deflection_mm=1e-6,

        # Make tilt non-governing
        max_pin_tilt_deg=10.0,

        carrier_planet_clearance_mm=1.0,
        axial_bearing_clearance_mm=0.5,

        min_planet_root_ligament_mm=2.0,

        required_bearing_life_h=1.0,
        min_static_safety_factor=1.0,
    )

    result = evaluate_planet_pin_bearing(
        BASE_INPUT,
        TEST_STEEL,
        TEST_BEARING,
        strict_config,
    )

    print_result(
        "TEST 6 — PIN DEFLECTION REJECTION",
        result,
    )

    assert not result.feasible

    assert (
        result.rejection_reason
        ==
        "pin_deflection_exceeds_limit"
    )

    print(
        "\nPASS: excessive pin deflection correctly rejected."
    )


# ============================================================
# TEST 7 — BEARING LIFE REJECTION
# ============================================================

def test_bearing_life_rejection():

    weak_bearing = NeedleBearingSpec(
        designation="TEST-WEAK-LIFE",

        bore_mm=10.0,
        outer_diameter_mm=20.0,
        width_mm=10.0,

        # Deliberately weak
        C_N=50.0,

        # Keep static capacity high
        C0_N=100000.0,

        limiting_speed_rpm=10000.0,

        mass_kg=0.020,
    )

    result = evaluate_planet_pin_bearing(
        BASE_INPUT,
        TEST_STEEL,
        weak_bearing,
        BASE_CONFIG,
    )

    print_result(
        "TEST 7 — NEEDLE BEARING LIFE REJECTION",
        result,
    )

    assert not result.feasible

    assert (
        result.rejection_reason
        ==
        "needle_bearing_life_below_requirement"
    )

    print(
        "\nPASS: inadequate needle-bearing life correctly rejected."
    )


# ============================================================
# TEST 8 — BEARING SPEED REJECTION
# ============================================================

def test_bearing_speed_rejection():

    slow_bearing = NeedleBearingSpec(
        designation="TEST-SLOW",

        bore_mm=10.0,
        outer_diameter_mm=20.0,
        width_mm=10.0,

        C_N=100000.0,
        C0_N=100000.0,

        # Relative speed = |-135 - 90| = 225 rpm
        limiting_speed_rpm=100.0,

        mass_kg=0.020,
    )

    result = evaluate_planet_pin_bearing(
        BASE_INPUT,
        TEST_STEEL,
        slow_bearing,
        BASE_CONFIG,
    )

    print_result(
        "TEST 8 — NEEDLE BEARING SPEED REJECTION",
        result,
    )

    assert not result.feasible

    assert (
        result.rejection_reason
        ==
        "needle_bearing_speed_exceeds_limit"
    )

    print(
        "\nPASS: excessive needle-bearing speed correctly rejected."
    )


# ============================================================
# RUN ALL TESTS
# ============================================================

if __name__ == "__main__":

    test_feasible_candidate()
    test_relative_speed()
    test_pin_strength_rejection()
    test_radial_packaging_rejection()
    test_axial_packaging_rejection()
    test_deflection_rejection()
    test_bearing_life_rejection()
    test_bearing_speed_rejection()

    print("\n" + "=" * 76)
    print("ALL PLANET PIN + BEARING TESTS PASSED")
    print("=" * 76)