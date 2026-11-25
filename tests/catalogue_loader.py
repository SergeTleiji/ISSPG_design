"""
Standalone tests for src/catalogue_loader.py

Run from project root:

    python -m tests.catalogue_loader
"""

from pathlib import Path
from tempfile import TemporaryDirectory

from src.catalogue_loader import (
    CatalogueError,
    load_motor_catalogue,
    load_bearing_catalogue,
    load_material_catalogue,
    load_catalogues,
    get_ball_bearings,
    get_needle_bearings,
)


# ============================================================
# TEMPORARY TEST DATA
# ============================================================

MOTOR_YAML = """
motors:

  TEST_MOTOR:

    name: "Test Motor"

    rated_voltage_V: 48.0

    outer_diameter_mm: 80.0
    axial_length_mm: 25.0

    stator_id_nominal_mm: 50.0
    stator_id_min_mm: 49.9
    stator_id_max_mm: 50.1

    rated_torque_nm: 1.5
    peak_torque_nm: 4.0

    rated_speed_rpm: 3000.0
    no_load_speed_rpm: 4500.0

    Kt_nm_per_A: 0.10
    Kv_rpm_per_V: 100.0

    rated_current_A: 15.0
    peak_current_A: 45.0

    phase_to_phase_resistance_ohm: 0.15

    rotor_inertia_kgm2: 0.0002

    mass_kg: 0.35
"""


BEARING_CSV = """designation,type,has_inner_ring,bore_mm,outer_diameter_mm,width_mm,C_N,C0_N,limiting_speed_rpm,mass_kg
TEST_BALL_10,deep_groove_ball,false,10,26,8,5000,2500,20000,0.02
TEST_BALL_08,deep_groove_ball,false,8,22,7,4000,2000,25000,0.015
TEST_NEEDLE_08,needle_with_inner_ring,true,8,18,12,6000,7000,15000,0.018
"""


MATERIAL_YAML = """
materials:

  TEST_GEAR_STEEL:

    name: "Test Gear Steel"
    material_type: "steel"

    density_kg_m3: 7850.0

    E_GPa: 205.0
    G_GPa: 80.0
    poisson_ratio: 0.29

    Sy_MPa: 900.0
    Sut_MPa: 1050.0

    Se_prime_MPa: 500.0

    St_MPa: 300.0
    Sc_MPa: 1000.0

    S_br_allow_MPa: 500.0

    hardness_HB: 300


  TEST_STRUCTURAL:

    name: "Test Structural Steel"
    material_type: "steel"

    density_kg_m3: 7850.0

    E_GPa: 205.0
    G_GPa: 80.0
    poisson_ratio: 0.29

    Sy_MPa: 500.0
    Sut_MPa: 650.0

    Se_prime_MPa: 300.0

    St_MPa: null
    Sc_MPa: null

    S_br_allow_MPa: 300.0

    hardness_HB: null
"""


# ============================================================
# HELPER
# ============================================================

def create_test_catalogues(
    directory: Path,
):

    motor_path = (
        directory
        / "motors.yaml"
    )

    bearing_path = (
        directory
        / "bearings.csv"
    )

    material_path = (
        directory
        / "materials.yaml"
    )

    motor_path.write_text(
        MOTOR_YAML,
        encoding="utf-8",
    )

    bearing_path.write_text(
        BEARING_CSV,
        encoding="utf-8",
    )

    material_path.write_text(
        MATERIAL_YAML,
        encoding="utf-8",
    )

    return (
        motor_path,
        bearing_path,
        material_path,
    )


# ============================================================
# TEST 1 — MOTOR CATALOGUE
# ============================================================

def test_motor_catalogue():

    with TemporaryDirectory() as tmp:

        paths = create_test_catalogues(
            Path(tmp)
        )

        motors = load_motor_catalogue(
            paths[0]
        )

        assert (
            "TEST_MOTOR"
            in motors
        )

        motor = motors[
            "TEST_MOTOR"
        ]

        assert (
            motor.name
            ==
            "Test Motor"
        )

        assert (
            motor.stator_id_min_mm
            ==
            49.9
        )

        assert (
            motor.peak_torque_nm
            ==
            4.0
        )

        print("\n" + "=" * 76)
        print("TEST 1 — MOTOR CATALOGUE")
        print("=" * 76)

        print(
            f"Loaded motor: {motor.name}"
        )

        print(
            "\nPASS: motor catalogue loaded correctly."
        )


# ============================================================
# TEST 2 — BEARING CATALOGUE
# ============================================================

def test_bearing_catalogue():

    with TemporaryDirectory() as tmp:

        paths = create_test_catalogues(
            Path(tmp)
        )

        bearings = (
            load_bearing_catalogue(
                paths[1]
            )
        )

        assert len(bearings) == 3

        ball = bearings[
            "TEST_BALL_10"
        ]

        needle = bearings[
            "TEST_NEEDLE_08"
        ]

        assert (
            ball.type
            ==
            "deep_groove_ball"
        )

        assert not (
            ball.has_inner_ring
        )

        assert (
            needle.has_inner_ring
        )

        print("\n" + "=" * 76)
        print("TEST 2 — BEARING CATALOGUE")
        print("=" * 76)

        print(
            f"Loaded {len(bearings)} bearings."
        )

        print(
            "\nPASS: bearing catalogue loaded correctly."
        )


# ============================================================
# TEST 3 — MATERIAL CATALOGUE
# ============================================================

def test_material_catalogue():

    with TemporaryDirectory() as tmp:

        paths = create_test_catalogues(
            Path(tmp)
        )

        materials = (
            load_material_catalogue(
                paths[2]
            )
        )

        gear = materials[
            "TEST_GEAR_STEEL"
        ]

        structural = materials[
            "TEST_STRUCTURAL"
        ]

        assert gear.St_MPa == 300.0
        assert gear.Sc_MPa == 1000.0

        assert structural.St_MPa is None
        assert structural.Sc_MPa is None

        print("\n" + "=" * 76)
        print("TEST 3 — MATERIAL CATALOGUE")
        print("=" * 76)

        print(
            f"Loaded {len(materials)} materials."
        )

        print(
            "\nPASS: optional material fields handled correctly."
        )


# ============================================================
# TEST 4 — COMPLETE BUNDLE
# ============================================================

def test_complete_bundle():

    with TemporaryDirectory() as tmp:

        paths = create_test_catalogues(
            Path(tmp)
        )

        bundle = load_catalogues(
            motor_path=paths[0],
            bearing_path=paths[1],
            material_path=paths[2],
        )

        assert len(bundle.motors) == 1
        assert len(bundle.bearings) == 3
        assert len(bundle.materials) == 2

        print("\n" + "=" * 76)
        print("TEST 4 — COMPLETE BUNDLE")
        print("=" * 76)

        print(
            f"Motors:    {len(bundle.motors)}"
        )

        print(
            f"Bearings:  {len(bundle.bearings)}"
        )

        print(
            f"Materials: {len(bundle.materials)}"
        )

        print(
            "\nPASS: complete catalogue bundle loaded."
        )


# ============================================================
# TEST 5 — BEARING FILTER / SORT
# ============================================================

def test_bearing_filters():

    with TemporaryDirectory() as tmp:

        paths = create_test_catalogues(
            Path(tmp)
        )

        bearings = (
            load_bearing_catalogue(
                paths[1]
            )
        )

        balls = get_ball_bearings(
            bearings
        )

        needles = (
            get_needle_bearings(
                bearings
            )
        )

        assert len(balls) == 2
        assert len(needles) == 1

        # Must be sorted by bore.
        assert (
            balls[0].bore_mm
            <
            balls[1].bore_mm
        )

        print("\n" + "=" * 76)
        print("TEST 5 — BEARING FILTERS")
        print("=" * 76)

        print(
            "Ball bearing order:"
        )

        for bearing in balls:

            print(
                f"  {bearing.designation}: "
                f"{bearing.bore_mm:.1f} mm"
            )

        print(
            "\nPASS: bearing filtering and sorting work."
        )


# ============================================================
# TEST 6 — INVALID MOTOR DATA
# ============================================================

def test_invalid_motor():

    bad_yaml = """
motors:

  BAD_MOTOR:

    name: "Bad"

    rated_voltage_V: 48

    outer_diameter_mm: 80
    axial_length_mm: 25

    stator_id_nominal_mm: 50
    stator_id_min_mm: 50
    stator_id_max_mm: 50

    rated_torque_nm: 5
    peak_torque_nm: 2

    rated_speed_rpm: 3000
    no_load_speed_rpm: 4000

    Kt_nm_per_A: 0.1
    Kv_rpm_per_V: 100

    rated_current_A: 10
    peak_current_A: 20

    phase_to_phase_resistance_ohm: 0.1

    rotor_inertia_kgm2: 0.0002

    mass_kg: 0.3
"""

    with TemporaryDirectory() as tmp:

        path = (
            Path(tmp)
            / "motors.yaml"
        )

        path.write_text(
            bad_yaml,
            encoding="utf-8",
        )

        try:

            load_motor_catalogue(
                path
            )

        except CatalogueError as exc:

            print("\n" + "=" * 76)
            print("TEST 6 — INVALID MOTOR")
            print("=" * 76)

            print(
                f"Expected error: {exc}"
            )

            print(
                "\nPASS: inconsistent motor data rejected."
            )

            return

        raise AssertionError(
            "Expected CatalogueError was not raised."
        )


# ============================================================
# RUN ALL TESTS
# ============================================================

if __name__ == "__main__":

    test_motor_catalogue()
    test_bearing_catalogue()
    test_material_catalogue()
    test_complete_bundle()
    test_bearing_filters()
    test_invalid_motor()

    print("\n" + "=" * 76)
    print("ALL CATALOGUE LOADER TESTS PASSED")
    print("=" * 76)