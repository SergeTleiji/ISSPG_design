"""
Standalone tests for src/adapters.py

Run:

    python -m tests.adapters
"""

from src.catalogue_loader import (
    BearingCatalogueEntry,
    MaterialCatalogueEntry,
    MotorCatalogueEntry,
)

from src.adapters import (
    AdapterError,
    motor_to_spec,
    material_to_gear_material,
    material_to_shaft_material,
    material_to_rotor_support_material,
    material_to_pin_material,
    material_to_output_shaft_material,
    material_to_carrier_material,
    material_to_ring_material,
    bearing_to_rotor_support_spec,
    bearing_to_needle_spec,
    bearing_to_output_spec,
)


# ============================================================
# TEST DATA
# ============================================================

MOTOR = MotorCatalogueEntry(

    key="TEST_MOTOR",
    name="Test Motor",

    rated_voltage_V=48.0,

    outer_diameter_mm=80.0,
    axial_length_mm=25.0,

    stator_id_nominal_mm=50.0,
    stator_id_min_mm=49.9,
    stator_id_max_mm=50.1,

    rated_torque_nm=1.5,
    peak_torque_nm=4.0,

    rated_speed_rpm=3000.0,
    no_load_speed_rpm=4500.0,

    Kt_nm_per_A=0.10,
    Kv_rpm_per_V=100.0,

    rated_current_A=15.0,
    peak_current_A=45.0,

    phase_to_phase_resistance_ohm=0.15,

    rotor_inertia_kgm2=2e-4,

    mass_kg=0.35,
)


MATERIAL = MaterialCatalogueEntry(

    key="TEST_STEEL",

    name="Test Steel",

    material_type="steel",

    density_kg_m3=7850.0,

    E_GPa=205.0,
    G_GPa=80.0,

    poisson_ratio=0.29,

    Sy_MPa=900.0,
    Sut_MPa=1050.0,

    Se_prime_MPa=500.0,

    St_MPa=300.0,
    Sc_MPa=1000.0,

    S_br_allow_MPa=500.0,

    hardness_HB=300.0,
)


BALL = BearingCatalogueEntry(

    designation="TEST_BALL",

    type="deep_groove_ball",

    has_inner_ring=False,

    bore_mm=10.0,
    outer_diameter_mm=26.0,
    width_mm=8.0,

    C_N=5000.0,
    C0_N=2500.0,

    limiting_speed_rpm=20000.0,

    mass_kg=0.020,
)


NEEDLE = BearingCatalogueEntry(

    designation="TEST_NEEDLE",

    type="needle_with_inner_ring",

    has_inner_ring=True,

    bore_mm=8.0,
    outer_diameter_mm=18.0,
    width_mm=12.0,

    C_N=6000.0,
    C0_N=7500.0,

    limiting_speed_rpm=18000.0,

    mass_kg=0.018,
)


# ============================================================
# TEST 1 — MOTOR
# ============================================================

def test_motor_adapter():

    result = motor_to_spec(
        MOTOR
    )

    assert (
        result.name
        ==
        "Test Motor"
    )

    assert (
        result.peak_torque_nm
        ==
        4.0
    )

    assert (
        result.stator_id_min_mm
        ==
        49.9
    )

    print("\n" + "=" * 76)
    print("TEST 1 — MOTOR ADAPTER")
    print("=" * 76)

    print(
        f"Motor: {result.name}"
    )

    print(
        "PASS: motor adapter works."
    )


# ============================================================
# TEST 2 — GEAR MATERIAL
# ============================================================

def test_gear_material():

    result = (
        material_to_gear_material(
            MATERIAL
        )
    )

    assert (
        result.St_MPa
        ==
        300.0
    )

    assert (
        result.Sc_MPa
        ==
        1000.0
    )

    print("\n" + "=" * 76)
    print("TEST 2 — GEAR MATERIAL")
    print("=" * 76)

    print(
        "PASS: gear material adapter works."
    )


# ============================================================
# TEST 3 — ALL STRUCTURAL MATERIAL ADAPTERS
# ============================================================

def test_structural_material_adapters():

    shaft = (
        material_to_shaft_material(
            MATERIAL
        )
    )

    rotor = (
        material_to_rotor_support_material(
            MATERIAL
        )
    )

    pin = (
        material_to_pin_material(
            MATERIAL
        )
    )

    output = (
        material_to_output_shaft_material(
            MATERIAL
        )
    )

    carrier = (
        material_to_carrier_material(
            MATERIAL
        )
    )

    ring = (
        material_to_ring_material(
            MATERIAL
        )
    )

    assert shaft.name == "Test Steel"
    assert rotor.name == "Test Steel"
    assert pin.name == "Test Steel"
    assert output.name == "Test Steel"
    assert carrier.name == "Test Steel"
    assert ring.name == "Test Steel"

    print("\n" + "=" * 76)
    print("TEST 3 — MATERIAL ADAPTERS")
    print("=" * 76)

    print(
        "PASS: all structural material adapters work."
    )


# ============================================================
# TEST 4 — BALL BEARING ADAPTERS
# ============================================================

def test_ball_bearing_adapters():

    rotor = (
        bearing_to_rotor_support_spec(
            BALL
        )
    )

    output = (
        bearing_to_output_spec(
            BALL
        )
    )

    assert (
        rotor.designation
        ==
        "TEST_BALL"
    )

    assert (
        output.designation
        ==
        "TEST_BALL"
    )

    print("\n" + "=" * 76)
    print("TEST 4 — BALL BEARINGS")
    print("=" * 76)

    print(
        "PASS: ball-bearing adapters work."
    )


# ============================================================
# TEST 5 — NEEDLE BEARING
# ============================================================

def test_needle_bearing():

    result = (
        bearing_to_needle_spec(
            NEEDLE
        )
    )

    assert (
        result.designation
        ==
        "TEST_NEEDLE"
    )

    print("\n" + "=" * 76)
    print("TEST 5 — NEEDLE BEARING")
    print("=" * 76)

    print(
        "PASS: needle-bearing adapter works."
    )


# ============================================================
# TEST 6 — WRONG BEARING TYPE
# ============================================================

def test_wrong_bearing_type():

    try:

        bearing_to_needle_spec(
            BALL
        )

    except AdapterError as exc:

        print("\n" + "=" * 76)
        print("TEST 6 — WRONG BEARING TYPE")
        print("=" * 76)

        print(
            f"Expected error: {exc}"
        )

        print(
            "PASS: incompatible bearing rejected."
        )

        return

    raise AssertionError(
        "Expected AdapterError."
    )


# ============================================================
# TEST 7 — MISSING AGMA MATERIAL DATA
# ============================================================

def test_missing_gear_data():

    material = (
        MaterialCatalogueEntry(

            key="NON_GEAR",

            name="Non Gear Material",

            material_type="steel",

            density_kg_m3=7850.0,

            E_GPa=205.0,
            G_GPa=80.0,

            poisson_ratio=0.29,

            Sy_MPa=500.0,
            Sut_MPa=650.0,

            Se_prime_MPa=300.0,

            St_MPa=None,
            Sc_MPa=None,

            S_br_allow_MPa=300.0,

            hardness_HB=None,
        )
    )

    try:

        material_to_gear_material(
            material
        )

    except AdapterError as exc:

        print("\n" + "=" * 76)
        print("TEST 7 — MISSING AGMA DATA")
        print("=" * 76)

        print(
            f"Expected error: {exc}"
        )

        print(
            "PASS: non-gear material rejected "
            "for gear calculations."
        )

        return

    raise AssertionError(
        "Expected AdapterError."
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    test_motor_adapter()
    test_gear_material()
    test_structural_material_adapters()
    test_ball_bearing_adapters()
    test_needle_bearing()
    test_wrong_bearing_type()
    test_missing_gear_data()

    print("\n" + "=" * 76)
    print("ALL ADAPTER TESTS PASSED")
    print("=" * 76)