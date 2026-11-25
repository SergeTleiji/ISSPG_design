"""
Standalone tests for src/ring.py

Run from project root:

    python -m tests.ring

No material or motor catalogue is required.
Synthetic values are instantiated directly.
"""

from src.ring import (
    RingMaterial,
    RingInput,
    RingConfig,
    evaluate_ring,
)


# ============================================================
# TEST MATERIAL
# ============================================================

TEST_STEEL = RingMaterial(

    name="Synthetic Test Steel",

    Sy_MPa=500.0,
)


# ============================================================
# BASE CONFIG
# ============================================================

BASE_CONFIG = RingConfig(

    safety_factor=2.0,

    min_backup_ratio=1.2,

    radial_clearance_mm=0.25,
)


# ============================================================
# BASE INPUT
#
# Similar to:
#   Zr = 100
#   m  = 0.5 mm
#   RO80 stator ID = 55 mm
# ============================================================

BASE_INPUT = RingInput(

    z_r=100,

    module_mm=0.5,

    T_r_nm=6.208333333333334,

    stator_id_min_mm=55.0,
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
        f"Ring root diameter:           "
        f"{result.ring_root_diameter_mm:.6f} mm"
    )

    print(
        f"Whole tooth depth:            "
        f"{result.whole_tooth_depth_mm:.6f} mm"
    )

    print("\nRIM THICKNESS")

    print(
        f"Backup-ratio thickness:       "
        f"{result.thickness_backup_mm:.6f} mm"
    )

    print(
        f"Torsional thickness:          "
        f"{result.thickness_torsion_mm:.6f} mm"
    )

    print(
        f"Final rim thickness:          "
        f"{result.ring_rim_thickness_mm:.6f} mm"
    )

    print(
        f"Governing requirement:        "
        f"{result.governing_requirement}"
    )

    print(
        f"Actual backup ratio:          "
        f"{result.actual_backup_ratio:.6f}"
    )

    print(
        f"K_B:                          "
        f"{result.K_B:.3f}"
    )

    print("\nPACKAGING")

    print(
        f"Ring outer diameter:          "
        f"{result.ring_outer_diameter_mm:.6f} mm"
    )

    print(
        f"Available radial clearance:   "
        f"{result.available_radial_clearance_mm:.6f} mm"
    )

    print("\nGLOBAL TORSION")

    print(
        f"Shear stress:                 "
        f"{result.torsional_shear_stress_MPa:.6f} MPa"
    )

    print(
        f"Von Mises stress:             "
        f"{result.torsional_von_mises_MPa:.6f} MPa"
    )

    print(
        f"Torsional safety factor:      "
        f"{result.torsional_safety_factor:.6f}"
    )


# ============================================================
# TEST 1 — NORMAL FEASIBLE RING
# ============================================================

def test_feasible_ring():

    result = evaluate_ring(
        BASE_INPUT,
        TEST_STEEL,
        BASE_CONFIG,
    )

    print_result(
        "TEST 1 — FEASIBLE RING",
        result,
    )

    assert result.feasible

    assert (
        result.available_radial_clearance_mm
        >=
        BASE_CONFIG.radial_clearance_mm
    )

    print(
        "\nPASS: feasible ring correctly accepted."
    )


# ============================================================
# TEST 2 — BACKUP-RATIO THICKNESS
# ============================================================

def test_backup_ratio():

    result = evaluate_ring(
        BASE_INPUT,
        TEST_STEEL,
        BASE_CONFIG,
    )

    expected_h_t = (
        2.25
        * BASE_INPUT.module_mm
    )

    expected_t = (
        BASE_CONFIG.min_backup_ratio
        * expected_h_t
    )

    assert abs(
        result.whole_tooth_depth_mm
        -
        expected_h_t
    ) < 1e-12

    assert abs(
        result.thickness_backup_mm
        -
        expected_t
    ) < 1e-12

    assert (
        result.actual_backup_ratio
        >=
        BASE_CONFIG.min_backup_ratio
        - 1e-12
    )

    print("\n" + "=" * 76)
    print("TEST 2 — BACKUP RATIO")
    print("=" * 76)

    print(
        f"Expected thickness: "
        f"{expected_t:.8f} mm"
    )

    print(
        f"Solver thickness:   "
        f"{result.thickness_backup_mm:.8f} mm"
    )

    print(
        "\nPASS: backup-ratio sizing is consistent."
    )


# ============================================================
# TEST 3 — BACKUP RATIO GOVERNS NORMAL DESIGN
# ============================================================

def test_backup_governs():

    result = evaluate_ring(
        BASE_INPUT,
        TEST_STEEL,
        BASE_CONFIG,
    )

    assert (
        result.thickness_backup_mm
        >
        result.thickness_torsion_mm
    )

    assert (
        result.governing_requirement
        ==
        "backup_ratio"
    )

    print_result(
        "TEST 3 — BACKUP RATIO GOVERNING",
        result,
    )

    print(
        "\nPASS: backup ratio correctly governs normal example."
    )


# ============================================================
# TEST 4 — FORCE GLOBAL TORSION TO GOVERN
# ============================================================

def test_torsion_governs():

    low_strength_material = RingMaterial(

        name="Low Strength Test Material",

        Sy_MPa=100.0,
    )

    inp = RingInput(

        z_r=20,

        module_mm=0.5,

        # Deliberately high reaction torque
        T_r_nm=50.0,

        # Very large stator ID so packaging does not interfere
        stator_id_min_mm=100.0,
    )

    result = evaluate_ring(
        inp,
        low_strength_material,
        BASE_CONFIG,
    )

    print_result(
        "TEST 4 — GLOBAL TORSION GOVERNING",
        result,
    )

    assert result.feasible

    assert (
        result.thickness_torsion_mm
        >
        result.thickness_backup_mm
    )

    assert (
        result.governing_requirement
        ==
        "torsion"
    )

    print(
        "\nPASS: global torsional requirement correctly governs."
    )


# ============================================================
# TEST 5 — TORSIONAL SAFETY FACTOR
# ============================================================

def test_torsional_safety():

    result = evaluate_ring(
        BASE_INPUT,
        TEST_STEEL,
        BASE_CONFIG,
    )

    tolerance = 1e-12

    assert (
        result.torsional_safety_factor
        >=
        BASE_CONFIG.safety_factor
        - tolerance
    )

    print("\n" + "=" * 76)
    print("TEST 5 — TORSIONAL SAFETY")
    print("=" * 76)

    print(
        f"Required SF: "
        f"{BASE_CONFIG.safety_factor:.12f}"
    )

    print(
        f"Actual SF:   "
        f"{result.torsional_safety_factor:.12f}"
    )

    print(
        "\nPASS: final rim satisfies global torsional requirement."
    )


# ============================================================
# TEST 6 — STATOR PACKAGING REJECTION
# ============================================================

def test_packaging_rejection():

    inp = RingInput(

        z_r=100,

        module_mm=0.5,

        T_r_nm=6.208333333333334,

        # Deliberately too small
        stator_id_min_mm=32.0,
    )

    result = evaluate_ring(
        inp,
        TEST_STEEL,
        BASE_CONFIG,
    )

    print_result(
        "TEST 6 — STATOR PACKAGING REJECTION",
        result,
    )

    assert not result.feasible

    assert (
        result.rejection_reason
        ==
        "final_ring_does_not_fit_stator_bore"
    )

    print(
        "\nPASS: oversized final ring correctly rejected."
    )


# ============================================================
# TEST 7 — INVALID BACKUP RATIO
# ============================================================

def test_invalid_backup_ratio():

    bad_config = RingConfig(

        safety_factor=2.0,

        # Invalid for our K_B = 1 simplification
        min_backup_ratio=1.0,

        radial_clearance_mm=0.25,
    )

    try:

        evaluate_ring(
            BASE_INPUT,
            TEST_STEEL,
            bad_config,
        )

    except ValueError as exc:

        print("\n" + "=" * 76)
        print("TEST 7 — INVALID BACKUP RATIO")
        print("=" * 76)

        print(
            f"Expected error: {exc}"
        )

        print(
            "\nPASS: thin-rim configuration correctly rejected."
        )

        return

    raise AssertionError(
        "Expected ValueError was not raised."
    )


# ============================================================
# RUN ALL TESTS
# ============================================================

if __name__ == "__main__":

    test_feasible_ring()
    test_backup_ratio()
    test_backup_governs()
    test_torsion_governs()
    test_torsional_safety()
    test_packaging_rejection()
    test_invalid_backup_ratio()

    print("\n" + "=" * 76)
    print("ALL RING TESTS PASSED")
    print("=" * 76)