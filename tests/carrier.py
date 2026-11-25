"""
Standalone tests for src/carrier.py

Run from project root:

    python -m tests.carrier

No material catalogue or other pipeline modules are required.
Synthetic values are instantiated directly.
"""

from math import pi, sqrt

from src.carrier import (
    CarrierMaterial,
    CarrierInput,
    CarrierConfig,
    evaluate_carrier,
)


# ============================================================
# TEST MATERIAL
# ============================================================

TEST_MATERIAL = CarrierMaterial(

    name="Synthetic Test Steel",

    Sy_MPa=500.0,

    # Test-only nominal bearing/contact strength
    S_br_allow_MPa=300.0,
)


# ============================================================
# BASE CONFIG
# ============================================================

BASE_CONFIG = CarrierConfig(

    safety_factor=2.0,

    pin_edge_ligament_mm=3.0,
)


# ============================================================
# BASE INPUT
# ============================================================

BASE_INPUT = CarrierInput(

    F_pin_N=300.0,

    pin_diameter_mm=10.0,

    center_distance_mm=30.0,

    T_c_nm=7.45,

    output_shaft_diameter_mm=10.0,
)


def print_result(title, result):

    print("\n" + "=" * 76)
    print(title)
    print("=" * 76)

    print(
        f"Feasible:                     "
        f"{result.feasible}"
    )

    print(
        f"Rejection reason:             "
        f"{result.rejection_reason}"
    )

    print(
        f"Material:                     "
        f"{result.material_name}"
    )

    print("\nGEOMETRY")

    print(
        f"Carrier radius:               "
        f"{result.carrier_radius_mm:.3f} mm"
    )

    print(
        f"Carrier OD:                   "
        f"{result.carrier_outer_diameter_mm:.3f} mm"
    )

    print("\nTHICKNESS REQUIREMENTS")

    print(
        f"Pin-hole thickness:           "
        f"{result.thickness_pinhole_mm:.6f} mm"
    )

    print(
        f"Torsional thickness:          "
        f"{result.thickness_torsion_mm:.6f} mm"
    )

    print(
        f"Final carrier thickness:      "
        f"{result.carrier_thickness_mm:.6f} mm"
    )

    print(
        f"Governing requirement:        "
        f"{result.governing_requirement}"
    )

    print("\nPIN-HOLE CHECK")

    print(
        f"Bearing stress:               "
        f"{result.pinhole_bearing_stress_MPa:.3f} MPa"
    )

    print(
        f"Safety factor:                "
        f"{result.pinhole_safety_factor:.3f}"
    )

    print("\nTORSION CHECK")

    print(
        f"Shear stress:                 "
        f"{result.torsional_shear_stress_MPa:.3f} MPa"
    )

    print(
        f"Von Mises stress:             "
        f"{result.torsional_von_mises_MPa:.3f} MPa"
    )

    print(
        f"Safety factor:                "
        f"{result.torsional_safety_factor:.3f}"
    )


# ============================================================
# TEST 1 — NORMAL CARRIER SIZING
# ============================================================

def test_normal_carrier():

    result = evaluate_carrier(
        BASE_INPUT,
        TEST_MATERIAL,
        BASE_CONFIG,
    )

    print_result(
        "TEST 1 — NORMAL CARRIER SIZING",
        result,
    )

    assert result.feasible

    assert (
        result.carrier_thickness_mm
        ==
        max(
            result.thickness_pinhole_mm,
            result.thickness_torsion_mm,
        )
    )

    print(
        "\nPASS: carrier thickness correctly selected."
    )


# ============================================================
# TEST 2 — CARRIER OD EQUATION
# ============================================================

def test_carrier_outer_diameter():

    result = evaluate_carrier(
        BASE_INPUT,
        TEST_MATERIAL,
        BASE_CONFIG,
    )

    expected_radius = (
        BASE_INPUT.center_distance_mm
        +
        BASE_INPUT.pin_diameter_mm / 2.0
        +
        BASE_CONFIG.pin_edge_ligament_mm
    )

    expected_diameter = (
        2.0
        * expected_radius
    )

    assert abs(
        result.carrier_radius_mm
        -
        expected_radius
    ) < 1e-12

    assert abs(
        result.carrier_outer_diameter_mm
        -
        expected_diameter
    ) < 1e-12

    print("\n" + "=" * 76)
    print("TEST 2 — CARRIER OUTER DIAMETER")
    print("=" * 76)

    print(
        f"Expected radius:   "
        f"{expected_radius:.6f} mm"
    )

    print(
        f"Solver radius:     "
        f"{result.carrier_radius_mm:.6f} mm"
    )

    print(
        f"Expected diameter: "
        f"{expected_diameter:.6f} mm"
    )

    print(
        f"Solver diameter:   "
        f"{result.carrier_outer_diameter_mm:.6f} mm"
    )

    print(
        "\nPASS: carrier radial geometry is consistent."
    )


# ============================================================
# TEST 3 — PIN-HOLE THICKNESS EQUATION
# ============================================================

def test_pinhole_thickness():

    result = evaluate_carrier(
        BASE_INPUT,
        TEST_MATERIAL,
        BASE_CONFIG,
    )

    expected_thickness = (
        BASE_CONFIG.safety_factor
        * BASE_INPUT.F_pin_N
        /
        (
            TEST_MATERIAL.S_br_allow_MPa
            * BASE_INPUT.pin_diameter_mm
        )
    )

    assert abs(
        result.thickness_pinhole_mm
        -
        expected_thickness
    ) < 1e-12

    print("\n" + "=" * 76)
    print("TEST 3 — PIN-HOLE THICKNESS")
    print("=" * 76)

    print(
        f"Expected: "
        f"{expected_thickness:.8f} mm"
    )

    print(
        f"Solver:   "
        f"{result.thickness_pinhole_mm:.8f} mm"
    )

    print(
        "\nPASS: pin-hole thickness equation is consistent."
    )


# ============================================================
# TEST 4 — TORSIONAL THICKNESS EQUATION
# ============================================================

def test_torsional_thickness():

    result = evaluate_carrier(
        BASE_INPUT,
        TEST_MATERIAL,
        BASE_CONFIG,
    )

    T_Nmm = (
        BASE_INPUT.T_c_nm
        * 1000.0
    )

    expected_thickness = (
        2.0
        * sqrt(3.0)
        * BASE_CONFIG.safety_factor
        * T_Nmm
        /
        (
            pi
            * BASE_INPUT.output_shaft_diameter_mm**2
            * TEST_MATERIAL.Sy_MPa
        )
    )

    assert abs(
        result.thickness_torsion_mm
        -
        expected_thickness
    ) < 1e-12

    print("\n" + "=" * 76)
    print("TEST 4 — TORSIONAL THICKNESS")
    print("=" * 76)

    print(
        f"Expected: "
        f"{expected_thickness:.8f} mm"
    )

    print(
        f"Solver:   "
        f"{result.thickness_torsion_mm:.8f} mm"
    )

    print(
        "\nPASS: carrier torsion equation is consistent."
    )


# ============================================================
# TEST 5 — FORCE PIN-HOLE TO GOVERN
# ============================================================

def test_pinhole_governs():

    inp = CarrierInput(

        # Deliberately high pin load
        F_pin_N=2000.0,

        pin_diameter_mm=10.0,

        center_distance_mm=30.0,

        # Deliberately low torque
        T_c_nm=1.0,

        output_shaft_diameter_mm=10.0,
    )

    result = evaluate_carrier(
        inp,
        TEST_MATERIAL,
        BASE_CONFIG,
    )

    print_result(
        "TEST 5 — PIN-HOLE GOVERNING",
        result,
    )

    assert (
        result.thickness_pinhole_mm
        >
        result.thickness_torsion_mm
    )

    assert (
        result.governing_requirement
        ==
        "pinhole"
    )

    assert (
        result.carrier_thickness_mm
        ==
        result.thickness_pinhole_mm
    )

    print(
        "\nPASS: pin-hole loading correctly governs."
    )


# ============================================================
# TEST 6 — FORCE TORSION TO GOVERN
# ============================================================

def test_torsion_governs():

    inp = CarrierInput(

        # Small pin load
        F_pin_N=50.0,

        pin_diameter_mm=10.0,

        center_distance_mm=30.0,

        # Large output torque
        T_c_nm=10.0,

        output_shaft_diameter_mm=8.0,
    )

    result = evaluate_carrier(
        inp,
        TEST_MATERIAL,
        BASE_CONFIG,
    )

    print_result(
        "TEST 6 — TORSION GOVERNING",
        result,
    )

    assert (
        result.thickness_torsion_mm
        >
        result.thickness_pinhole_mm
    )

    assert (
        result.governing_requirement
        ==
        "torsion"
    )

    assert (
        result.carrier_thickness_mm
        ==
        result.thickness_torsion_mm
    )

    print(
        "\nPASS: global torsion correctly governs."
    )


# ============================================================
# TEST 7 — FINAL THICKNESS SATISFIES BOTH SAFETY FACTORS
# ============================================================

def test_final_safety():

    result = evaluate_carrier(
        BASE_INPUT,
        TEST_MATERIAL,
        BASE_CONFIG,
    )

    tolerance = 1e-12

    assert (
        result.pinhole_safety_factor
        >=
        BASE_CONFIG.safety_factor
        - tolerance
    )

    assert (
        result.torsional_safety_factor
        >=
        BASE_CONFIG.safety_factor
        - tolerance
    )

    print("\n" + "=" * 76)
    print("TEST 7 — FINAL SAFETY FACTORS")
    print("=" * 76)

    print(
        f"Pin-hole SF: "
        f"{result.pinhole_safety_factor:.12f}"
    )

    print(
        f"Torsional SF: "
        f"{result.torsional_safety_factor:.12f}"
    )

    print(
        "\nPASS: final thickness satisfies both checks."
    )


# ============================================================
# TEST 8 — INVALID INPUT
# ============================================================

def test_invalid_edge_ligament():

    bad_config = CarrierConfig(

        safety_factor=2.0,

        # Deliberately impossible
        pin_edge_ligament_mm=-1.0,
    )

    try:

        evaluate_carrier(
            BASE_INPUT,
            TEST_MATERIAL,
            bad_config,
        )

    except ValueError as exc:

        print("\n" + "=" * 76)
        print("TEST 8 — INVALID INPUT")
        print("=" * 76)

        print(
            f"Expected error: {exc}"
        )

        print(
            "\nPASS: invalid edge ligament correctly rejected."
        )

        return

    raise AssertionError(
        "Expected ValueError was not raised."
    )


# ============================================================
# RUN ALL TESTS
# ============================================================

if __name__ == "__main__":

    test_normal_carrier()
    test_carrier_outer_diameter()
    test_pinhole_thickness()
    test_torsional_thickness()
    test_pinhole_governs()
    test_torsion_governs()
    test_final_safety()
    test_invalid_edge_ligament()

    print("\n" + "=" * 76)
    print("ALL CARRIER TESTS PASSED")
    print("=" * 76)