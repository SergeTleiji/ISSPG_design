"""
Standalone tests for src/planetary.py

Run from the project root with:

    python -m tests.test_planetary

This test does not require:
    - motor catalogue
    - bearing catalogue
    - material catalogue
    - main pipeline
"""

from src.planetary import (
    PlanetaryInput,
    PlanetaryConstraints,
    evaluate_planetary,
)


def print_result(title, result):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)

    print(f"Feasible:               {result.feasible}")
    print(f"Rejection reason:       {result.rejection_reason}")

    print(f"Zs:                     {result.z_s}")
    print(f"Zp:                     {result.z_p}")
    print(f"Zr:                     {result.z_r}")
    print(f"Number of planets:      {result.n_planets}")
    print(f"Module:                 {result.module_mm} mm")

    print(f"Ratio:                  {result.ratio}")

    print(f"Sun speed:              {result.n_s_rpm} rpm")
    print(f"Planet speed:           {result.n_p_rpm} rpm")
    print(f"Carrier speed:          {result.n_c_rpm} rpm")

    print(f"Ideal sun torque:       {result.T_s_ideal_nm} N.m")
    print(f"Design sun torque:      {result.T_s_design_nm} N.m")
    print(f"Carrier torque:         {result.T_c_nm} N.m")
    print(f"Ideal ring torque:      {result.T_r_ideal_nm} N.m")

    print(f"Sun pitch diameter:     {result.d_s_mm} mm")
    print(f"Planet pitch diameter:  {result.d_p_mm} mm")
    print(f"Ring pitch diameter:    {result.d_r_mm} mm")

    print(
        f"Planet clearance:       "
        f"{result.planet_clearance_mm} mm"
    )

    print(
        f"Assembly condition:     "
        f"{result.assembly_condition_value}"
    )


def test_valid_candidate():

    # --------------------------------------------------------
    # A deliberately selected example candidate.
    # Change these values freely when validating the equations.
    # --------------------------------------------------------

    inp = PlanetaryInput(
        z_s=20,
        z_p=40,
        n_planets=4,
        module_mm=0.5,

        output_speed_rpm=90.0,
        output_torque_nm=7.45,

        efficiency=0.95,
    )

    limits = PlanetaryConstraints(
        ratio_min=4.0,
        ratio_max=8.0,

        # Temporary test-only value
        min_planet_clearance_mm=0.0,
    )

    result = evaluate_planetary(inp, limits)

    print_result("TEST 1 — VALID CANDIDATE", result)

    assert result.feasible

    # Zr = Zs + 2 Zp
    assert result.z_r == 100

    # i = 1 + Zr/Zs
    assert abs(result.ratio - 6.0) < 1e-12

    # ns = i nc
    assert abs(result.n_s_rpm - 540.0) < 1e-12

    print("\nPASS: valid candidate calculations are consistent.")


def test_ratio_rejection():

    inp = PlanetaryInput(
        z_s=40,
        z_p=10,
        n_planets=3,
        module_mm=0.5,

        output_speed_rpm=90.0,
        output_torque_nm=7.45,

        efficiency=0.95,
    )

    limits = PlanetaryConstraints(
        ratio_min=4.0,
        ratio_max=8.0,
        min_planet_clearance_mm=0.0,
    )

    result = evaluate_planetary(inp, limits)

    print_result("TEST 2 — RATIO REJECTION", result)

    assert not result.feasible
    assert result.rejection_reason == "ratio_below_minimum"

    print("\nPASS: invalid ratio correctly rejected.")


def test_assembly_rejection():

    inp = PlanetaryInput(
        z_s=20,
        z_p=38,
        n_planets=4,
        module_mm=0.5,

        output_speed_rpm=90.0,
        output_torque_nm=7.45,

        efficiency=0.95,
    )

    limits = PlanetaryConstraints(
        ratio_min=4.0,
        ratio_max=8.0,
        min_planet_clearance_mm=0.0,
    )

    result = evaluate_planetary(inp, limits)

    print_result(
        "TEST 3 — PLANET ASSEMBLY REJECTION",
        result
    )

    assert not result.feasible
    assert (
        result.rejection_reason
        == "planet_assembly_condition_failed"
    )

    print("\nPASS: assembly condition correctly rejected.")


def test_clearance_rejection():

    inp = PlanetaryInput(
        z_s=20,
        z_p=40,
        n_planets=4,
        module_mm=0.5,

        output_speed_rpm=90.0,
        output_torque_nm=7.45,

        efficiency=0.95,
    )

    # Artificially huge clearance requirement,
    # deliberately forcing rejection.
    limits = PlanetaryConstraints(
        ratio_min=4.0,
        ratio_max=8.0,
        min_planet_clearance_mm=100.0,
    )

    result = evaluate_planetary(inp, limits)

    print_result(
        "TEST 4 — PLANET CLEARANCE REJECTION",
        result
    )

    assert not result.feasible
    assert (
        result.rejection_reason
        == "planet_clearance_below_minimum"
    )

    print("\nPASS: clearance constraint correctly rejected.")


if __name__ == "__main__":

    test_valid_candidate()
    test_ratio_rejection()
    test_assembly_rejection()
    test_clearance_rejection()

    print("\n" + "=" * 70)
    print("ALL PLANETARY MODULE TESTS PASSED")
    print("=" * 70)