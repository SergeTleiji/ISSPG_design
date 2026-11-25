"""
Standalone tests for src/gear_strength.py

Run from project root:

    python -m tests.gear_strength

No material catalogue is required.
Synthetic material properties and geometry factors are used
ONLY to validate the equations and rejection logic.
"""

from math import sqrt

from src.gear_strength import (
    GearMaterial,
    GearGeometryFactors,
    GearStrengthInput,
    GearStrengthConfig,
    evaluate_gear_strength,
)


# ============================================================
# TEST MATERIAL
# ============================================================

TEST_STEEL = GearMaterial(
    name="Synthetic Test Steel",

    elastic_modulus_GPa=205.0,
    poisson_ratio=0.29,

    # Test-only AGMA strength numbers
    St_MPa=500.0,
    Sc_MPa=1500.0,
)


# ============================================================
# TEST GEOMETRY FACTORS
# ============================================================

TEST_GEOMETRY = GearGeometryFactors(

    # Test-only positive values
    YJ_sun_sp=0.30,
    YJ_planet_sp=0.32,
    YJ_planet_pr=0.34,
    YJ_ring_pr=0.36,
)


# ============================================================
# BASE INPUT
# ============================================================

BASE_INPUT = GearStrengthInput(

    z_s=20,
    z_p=40,
    z_r=100,

    module_mm=0.5,
    face_width_mm=12.0,

    d_s_mm=10.0,
    d_p_mm=20.0,

    pressure_angle_deg=20.0,

    F_t_sp_N=72.0,
    F_t_pr_N=70.0,

    velocity_sp_mps=0.2356,
    velocity_pr_mps=0.2356,
)


# ============================================================
# BASE CONFIG
# ============================================================

BASE_CONFIG = GearStrengthConfig(

    Q_v=8.0,

    K_o=1.0,
    K_s=1.0,
    K_H=1.1,
    Z_R=1.0,

    K_B_sun=1.0,
    K_B_planet=1.0,
    K_B_ring=1.0,

    K_T=1.0,
    K_R=1.0,

    Y_N_sun=1.0,
    Y_N_planet=1.0,
    Y_N_ring=1.0,

    Y_I_sun=1.0,
    Y_I_planet=0.70,
    Y_I_ring=1.0,

    Z_N_sun=1.0,
    Z_N_planet=1.0,
    Z_N_ring=1.0,

    Z_W_sun=1.0,
    Z_W_planet=1.0,
    Z_W_ring=1.0,

    min_bending_safety_factor=1.0,
    min_contact_safety_factor=1.0,
)


def print_result(title, result):

    print("\n" + "=" * 76)
    print(title)
    print("=" * 76)

    print(f"Feasible:                     {result.feasible}")
    print(f"Rejection reason:             {result.rejection_reason}")

    print(f"K_v sun-planet:              {result.K_v_sp:.5f}")
    print(f"K_v planet-ring:             {result.K_v_pr:.5f}")

    print(f"Z_I sun-planet:              {result.Z_I_sp:.5f}")
    print(f"Z_I planet-ring:             {result.Z_I_pr:.5f}")

    print(f"Z_E sun-planet:              {result.Z_E_sp:.3f} sqrt(MPa)")
    print(f"Z_E planet-ring:             {result.Z_E_pr:.3f} sqrt(MPa)")

    print("\nBENDING")

    print(
        f"Sun stress:                   "
        f"{result.sigma_F_sun_MPa:.3f} MPa"
    )

    print(
        f"Planet stress, sun side:      "
        f"{result.sigma_F_planet_sp_MPa:.3f} MPa"
    )

    print(
        f"Planet stress, ring side:     "
        f"{result.sigma_F_planet_pr_MPa:.3f} MPa"
    )

    print(
        f"Ring stress:                  "
        f"{result.sigma_F_ring_MPa:.3f} MPa"
    )

    print(
        f"Governing bending SF:         "
        f"{result.S_F_governing:.3f}"
    )

    print(
        f"Governing bending location:   "
        f"{result.governing_bending_location}"
    )

    print("\nCONTACT")

    print(
        f"Sun-planet contact stress:    "
        f"{result.sigma_H_sp_MPa:.3f} MPa"
    )

    print(
        f"Planet-ring contact stress:   "
        f"{result.sigma_H_pr_MPa:.3f} MPa"
    )

    print(
        f"Governing contact SF:         "
        f"{result.S_H_governing:.3f}"
    )

    print(
        f"Governing contact location:   "
        f"{result.governing_contact_location}"
    )

    print(
        f"Contact load safety SH^2:     "
        f"{result.S_H_squared:.3f}"
    )

    print(
        f"Overall load-style safety:    "
        f"{result.governing_load_safety:.3f}"
    )


# ============================================================
# TEST 1 — NORMAL FEASIBLE CALCULATION
# ============================================================

def test_feasible_candidate():

    result = evaluate_gear_strength(
        BASE_INPUT,
        TEST_GEOMETRY,
        TEST_STEEL,
        TEST_STEEL,
        TEST_STEEL,
        BASE_CONFIG,
    )

    print_result(
        "TEST 1 — FEASIBLE GEAR STRENGTH",
        result,
    )

    assert result.feasible

    assert result.K_v_sp >= 1.0
    assert result.K_v_pr >= 1.0

    assert result.Z_I_sp > 0
    assert result.Z_I_pr > 0

    assert result.Z_E_sp > 0
    assert result.Z_E_pr > 0

    print("\nPASS: feasible strength calculation accepted.")


# ============================================================
# TEST 2 — DYNAMIC FACTOR EQUATION
# ============================================================

def test_dynamic_factor():

    result = evaluate_gear_strength(
        BASE_INPUT,
        TEST_GEOMETRY,
        TEST_STEEL,
        TEST_STEEL,
        TEST_STEEL,
        BASE_CONFIG,
    )

    Q_v = BASE_CONFIG.Q_v
    v = BASE_INPUT.velocity_sp_mps

    B = 0.25 * (12.0 - Q_v) ** (2.0 / 3.0)

    A = 50.0 + 56.0 * (1.0 - B)

    expected_Kv = (
        (
            A + sqrt(200.0 * v)
        )
        / A
    ) ** B

    assert abs(
        result.K_v_sp
        - expected_Kv
    ) < 1e-12

    print("\n" + "=" * 76)
    print("TEST 2 — DYNAMIC FACTOR")
    print("=" * 76)

    print(f"Expected Kv: {expected_Kv:.8f}")
    print(f"Solver Kv:   {result.K_v_sp:.8f}")

    print("\nPASS: dynamic-factor equation is consistent.")


# ============================================================
# TEST 3 — REVERSE BENDING REDUCES PLANET ALLOWABLE
# ============================================================

def test_reverse_bending():

    result = evaluate_gear_strength(
        BASE_INPUT,
        TEST_GEOMETRY,
        TEST_STEEL,
        TEST_STEEL,
        TEST_STEEL,
        BASE_CONFIG,
    )

    expected_planet_allowable = (
        TEST_STEEL.St_MPa
        * BASE_CONFIG.Y_N_planet
        * BASE_CONFIG.Y_I_planet
        / (
            BASE_CONFIG.K_T
            * BASE_CONFIG.K_R
        )
    )

    assert abs(
        result.sigma_F_allow_planet_MPa
        - expected_planet_allowable
    ) < 1e-12

    assert (
        result.sigma_F_allow_planet_MPa
        <
        result.sigma_F_allow_sun_MPa
    )

    print("\n" + "=" * 76)
    print("TEST 3 — PLANET REVERSE BENDING")
    print("=" * 76)

    print(
        f"Sun allowable:    "
        f"{result.sigma_F_allow_sun_MPa:.3f} MPa"
    )

    print(
        f"Planet allowable: "
        f"{result.sigma_F_allow_planet_MPa:.3f} MPa"
    )

    print(
        "\nPASS: reverse-bending factor correctly "
        "reduces planet allowable stress."
    )


# ============================================================
# TEST 4 — BENDING REJECTION
# ============================================================

def test_bending_rejection():

    weak_bending_material = GearMaterial(
        name="Weak Bending Test Material",

        elastic_modulus_GPa=205.0,
        poisson_ratio=0.29,

        # Deliberately very low bending strength
        St_MPa=20.0,

        # Keep contact strength high
        Sc_MPa=5000.0,
    )

    result = evaluate_gear_strength(
        BASE_INPUT,
        TEST_GEOMETRY,
        weak_bending_material,
        weak_bending_material,
        weak_bending_material,
        BASE_CONFIG,
    )

    print_result(
        "TEST 4 — BENDING REJECTION",
        result,
    )

    assert not result.feasible

    assert result.rejection_reason.startswith(
        "bending_safety_below_minimum_"
    )

    print("\nPASS: inadequate bending strength correctly rejected.")


# ============================================================
# TEST 5 — CONTACT REJECTION
# ============================================================

def test_contact_rejection():

    weak_contact_material = GearMaterial(
        name="Weak Contact Test Material",

        elastic_modulus_GPa=205.0,
        poisson_ratio=0.29,

        # Keep bending strength high
        St_MPa=5000.0,

        # Deliberately low contact strength
        Sc_MPa=100.0,
    )

    result = evaluate_gear_strength(
        BASE_INPUT,
        TEST_GEOMETRY,
        weak_contact_material,
        weak_contact_material,
        weak_contact_material,
        BASE_CONFIG,
    )

    print_result(
        "TEST 5 — CONTACT REJECTION",
        result,
    )

    assert not result.feasible

    assert result.rejection_reason.startswith(
        "contact_safety_below_minimum_"
    )

    print("\nPASS: inadequate contact strength correctly rejected.")


# ============================================================
# TEST 6 — INVALID GEOMETRY FACTOR
# ============================================================

def test_invalid_YJ():

    bad_geometry = GearGeometryFactors(
        YJ_sun_sp=0.0,
        YJ_planet_sp=0.32,
        YJ_planet_pr=0.34,
        YJ_ring_pr=0.36,
    )

    try:

        evaluate_gear_strength(
            BASE_INPUT,
            bad_geometry,
            TEST_STEEL,
            TEST_STEEL,
            TEST_STEEL,
            BASE_CONFIG,
        )

    except ValueError as exc:

        print("\n" + "=" * 76)
        print("TEST 6 — INVALID YJ")
        print("=" * 76)

        print(f"Expected error: {exc}")

        print(
            "\nPASS: invalid geometry factor "
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

    test_feasible_candidate()
    test_dynamic_factor()
    test_reverse_bending()
    test_bending_rejection()
    test_contact_rejection()
    test_invalid_YJ()

    print("\n" + "=" * 76)
    print("ALL GEAR STRENGTH TESTS PASSED")
    print("=" * 76)