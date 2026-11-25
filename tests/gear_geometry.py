"""
Standalone tests for src/gear_geometry.py

Run from project root:

    python -m tests.gear_geometry
"""

from src.gear_geometry import (
    lookup_external_yj,
    evaluate_external_mesh_yj,
    evaluate_planetary_yj,
    lookup_internal_yj,
)


# ============================================================
# TEST 1 — EXACT LUT NODE
# ============================================================

def test_exact_lut_node():

    YJ = lookup_external_yj(
        gear_teeth=20,
        mating_teeth=50,
    )

    expected = 0.326

    assert abs(
        YJ - expected
    ) < 1e-12

    print("\n" + "=" * 76)
    print("TEST 1 — EXACT LUT NODE")
    print("=" * 76)

    print(f"Expected YJ: {expected:.6f}")
    print(f"Solver YJ:   {YJ:.6f}")

    print(
        "\nPASS: exact LUT lookup is correct."
    )


# ============================================================
# TEST 2 — INTERPOLATED VALUE
# ============================================================

def test_interpolated_value():

    YJ = lookup_external_yj(
        gear_teeth=22,
        mating_teeth=40,
    )

    print("\n" + "=" * 76)
    print("TEST 2 — INTERPOLATED VALUE")
    print("=" * 76)

    print(
        f"YJ(22, 40) = {YJ:.6f}"
    )

    # Must lie between surrounding chart values.
    assert 0.321 < YJ < 0.346

    print(
        "\nPASS: interpolated YJ lies within expected bounds."
    )


# ============================================================
# TEST 3 — SUN / PLANET VALUES ARE DIFFERENT
# ============================================================

def test_external_mesh_pair():

    result = evaluate_external_mesh_yj(
        gear_1_teeth=20,
        gear_2_teeth=40,
    )

    print("\n" + "=" * 76)
    print("TEST 3 — EXTERNAL MESH PAIR")
    print("=" * 76)

    print(
        f"YJ for 20-tooth gear: "
        f"{result.YJ_gear_1:.6f}"
    )

    print(
        f"YJ for 40-tooth gear: "
        f"{result.YJ_gear_2:.6f}"
    )

    assert (
        result.YJ_gear_1
        !=
        result.YJ_gear_2
    )

    assert abs(
        result.YJ_gear_1
        - 0.3228718919690566
    ) < 1e-10

    assert abs(
        result.YJ_gear_2
        - 0.3793712157668146
    ) < 1e-10

    print(
        "\nPASS: each gear receives its own geometry factor."
    )


# ============================================================
# TEST 4 — BELOW CHART RANGE
# ============================================================

def test_low_range_rejection():

    try:

        lookup_external_yj(
            gear_teeth=16,
            mating_teeth=40,
        )

    except ValueError as exc:

        print("\n" + "=" * 76)
        print("TEST 4 — LOW RANGE REJECTION")
        print("=" * 76)

        print(
            f"Expected error: {exc}"
        )

        print(
            "\nPASS: LUT does not extrapolate below chart range."
        )

        return

    raise AssertionError(
        "Expected ValueError was not raised."
    )


# ============================================================
# TEST 5 — ABOVE MATING-GEAR RANGE
# ============================================================

def test_high_mating_range_rejection():

    try:

        lookup_external_yj(
            gear_teeth=30,
            mating_teeth=1200,
        )

    except ValueError as exc:

        print("\n" + "=" * 76)
        print("TEST 5 — HIGH RANGE REJECTION")
        print("=" * 76)

        print(
            f"Expected error: {exc}"
        )

        print(
            "\nPASS: LUT does not extrapolate above chart range."
        )

        return

    raise AssertionError(
        "Expected ValueError was not raised."
    )


# ============================================================
# TEST 6 — INTERNAL MESH MUST NOT USE THIS LUT
# ============================================================

def test_internal_mesh_guard():

    try:

        lookup_internal_yj(
            gear_teeth=40,
            internal_ring_teeth=100,
        )

    except NotImplementedError as exc:

        print("\n" + "=" * 76)
        print("TEST 6 — INTERNAL MESH GUARD")
        print("=" * 76)

        print(
            f"Expected error: {exc}"
        )

        print(
            "\nPASS: external YJ LUT cannot accidentally "
            "be used for the internal ring mesh."
        )

        return

    raise AssertionError(
        "Expected NotImplementedError was not raised."
    )


# ============================================================
# TEST 7 — 
# ============================================================

def test_complete_planetary_yj():


    result = evaluate_planetary_yj(
        z_s=20,
        z_p=40,
        z_r=100,
    )

    print("\n" + "=" * 76)
    print("TEST 7 — COMPLETE PLANETARY YJ")
    print("=" * 76)

    print(
        f"Sun, sun-planet:     "
        f"{result.YJ_sun_sp:.6f}"
    )

    print(
        f"Planet, sun-planet:  "
        f"{result.YJ_planet_sp:.6f}"
    )

    print(
        f"Planet, planet-ring: "
        f"{result.YJ_planet_pr:.6f}"
    )

    print(
        f"Ring, planet-ring:   "
        f"{result.YJ_ring_pr:.6f}"
    )

    assert result.YJ_sun_sp > 0
    assert result.YJ_planet_sp > 0
    assert result.YJ_planet_pr > 0

    assert (
        result.YJ_ring_pr
        ==
        0.25
    )

    assert (
        result.YJ_planet_pr
        <=
        result.YJ_planet_sp
        + 1e-12
    )

    print(
        "\nPASS: complete preliminary planetary YJ set generated."
    )
# ============================================================
# RUN ALL TESTS
# ============================================================

if __name__ == "__main__":

    test_exact_lut_node()
    test_interpolated_value()
    test_external_mesh_pair()
    test_low_range_rejection()
    test_high_mating_range_rejection()
    test_internal_mesh_guard()
    test_complete_planetary_yj()

    print("\n" + "=" * 76)
    print("ALL GEAR GEOMETRY TESTS PASSED")
    print("=" * 76)