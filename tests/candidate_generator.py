"""
Standalone tests for src/candidate_generator.py

Run:

    python -m tests.candidate_generator
"""

from pathlib import Path
from tempfile import TemporaryDirectory

from src.catalogue_loader import (
    MotorCatalogueEntry,
)

from src.config_loader import (
    load_config,
)

from src.candidate_generator import (
    CandidateGenerationError,
    get_search_space,
    count_candidate_seeds,
    generate_candidate_seeds,
)


# ============================================================
# TEST MOTORS
# ============================================================

def make_motor(
    key: str,
):

    return MotorCatalogueEntry(

        key=key,

        name=key,

        rated_voltage_V=48.0,

        outer_diameter_mm=80.0,
        axial_length_mm=25.0,

        stator_id_nominal_mm=50.0,
        stator_id_min_mm=49.9,
        stator_id_max_mm=50.1,

        rated_torque_nm=1.0,
        peak_torque_nm=3.0,

        rated_speed_rpm=3000.0,
        no_load_speed_rpm=4000.0,

        Kt_nm_per_A=0.1,
        Kv_rpm_per_V=100.0,

        rated_current_A=10.0,
        peak_current_A=30.0,

        phase_to_phase_resistance_ohm=0.1,

        rotor_inertia_kgm2=0.0002,

        mass_kg=0.3,
    )


MOTORS = {

    "MOTOR_A":
        make_motor(
            "MOTOR_A"
        ),

    "MOTOR_B":
        make_motor(
            "MOTOR_B"
        ),
}


# ============================================================
# TEST CONFIG
# ============================================================

CONFIG_TEXT = """
planetary:

  search:

    sun_teeth:
      min: 18
      max: 20
      step: 1

    planet_teeth:
      min: 30
      max: 34
      step: 2

    planet_counts:
      - 3
      - 4

    modules_mm:
      - 0.5
      - 0.7

    face_widths_mm:
      - 6.0
      - 8.0
"""


def create_config(
    directory: Path,
    text: str = CONFIG_TEXT,
):

    path = (
        directory
        / "config.yaml"
    )

    path.write_text(
        text,
        encoding="utf-8",
    )

    return load_config(
        path
    )


# ============================================================
# TEST 1 — SEARCH SPACE
# ============================================================

def test_search_space():

    with TemporaryDirectory() as tmp:

        config = create_config(
            Path(tmp)
        )

        search = get_search_space(
            config,
            MOTORS,
        )

        assert (
            search["motor_keys"]
            ==
            [
                "MOTOR_A",
                "MOTOR_B",
            ]
        )

        assert (
            search["z_s_values"]
            ==
            [
                18,
                19,
                20,
            ]
        )

        assert (
            search["z_p_values"]
            ==
            [
                30,
                32,
                34,
            ]
        )

        assert (
            search[
                "n_planets_values"
            ]
            ==
            [
                3,
                4,
            ]
        )

        assert (
            search[
                "module_values"
            ]
            ==
            [
                0.5,
                0.7,
            ]
        )

        assert (
            search[
                "face_width_values"
            ]
            ==
            [
                6.0,
                8.0,
            ]
        )

        print("\n" + "=" * 76)
        print("TEST 1 — SEARCH SPACE")
        print("=" * 76)

        print(
            "PASS: search space parsed correctly."
        )


# ============================================================
# TEST 2 — CANDIDATE COUNT
# ============================================================

def test_candidate_count():

    with TemporaryDirectory() as tmp:

        config = create_config(
            Path(tmp)
        )

        count = count_candidate_seeds(
            config,
            MOTORS,
        )

        # 2 motors
        # x 3 sun tooth counts
        # x 3 planet tooth counts
        # x 2 planet counts
        # x 2 modules
        # x 2 face widths

        expected = (
            2
            * 3
            * 3
            * 2
            * 2
            * 2
        )

        assert (
            count
            ==
            expected
        )

        assert (
            count
            ==
            144
        )

        print("\n" + "=" * 76)
        print("TEST 2 — CANDIDATE COUNT")
        print("=" * 76)

        print(
            f"Candidate count: {count}"
        )

        print(
            "PASS: raw Cartesian count is correct."
        )


# ============================================================
# TEST 3 — GENERATION
# ============================================================

def test_generation():

    with TemporaryDirectory() as tmp:

        config = create_config(
            Path(tmp)
        )

        seeds = list(
            generate_candidate_seeds(
                config,
                MOTORS,
            )
        )

        assert len(
            seeds
        ) == 144

        first = seeds[0]

        assert (
            first.motor_key
            ==
            "MOTOR_A"
        )

        assert first.z_s == 18
        assert first.z_p == 30

        assert (
            first.n_planets
            ==
            3
        )

        assert (
            first.module_mm
            ==
            0.5
        )

        assert (
            first.face_width_mm
            ==
            6.0
        )

        print("\n" + "=" * 76)
        print("TEST 3 — GENERATION")
        print("=" * 76)

        print(
            f"First candidate:"
        )

        print(
            f"  Motor: {first.motor_key}"
        )

        print(
            f"  Zs:    {first.z_s}"
        )

        print(
            f"  Zp:    {first.z_p}"
        )

        print(
            f"  Np:    {first.n_planets}"
        )

        print(
            f"  m:     {first.module_mm}"
        )

        print(
            f"  b:     {first.face_width_mm}"
        )

        print(
            "\nPASS: candidates generated correctly."
        )


# ============================================================
# TEST 4 — DETERMINISTIC ORDER
# ============================================================

def test_deterministic_order():

    with TemporaryDirectory() as tmp:

        config = create_config(
            Path(tmp)
        )

        run_1 = list(
            generate_candidate_seeds(
                config,
                MOTORS,
            )
        )

        run_2 = list(
            generate_candidate_seeds(
                config,
                MOTORS,
            )
        )

        assert (
            run_1
            ==
            run_2
        )

        print("\n" + "=" * 76)
        print("TEST 4 — DETERMINISTIC ORDER")
        print("=" * 76)

        print(
            "PASS: repeated generation "
            "produces identical order."
        )


# ============================================================
# TEST 5 — OPTIONAL MOTOR FILTER
# ============================================================

def test_motor_filter():

    text = """
planetary:

  search:

    motor_keys:
      - MOTOR_B

    sun_teeth:
      min: 20
      max: 20
      step: 1

    planet_teeth:
      min: 40
      max: 40
      step: 1

    planet_counts:
      - 4

    modules_mm:
      - 0.5

    face_widths_mm:
      - 8.0
"""

    with TemporaryDirectory() as tmp:

        config = create_config(
            Path(tmp),
            text,
        )

        seeds = list(
            generate_candidate_seeds(
                config,
                MOTORS,
            )
        )

        assert len(
            seeds
        ) == 1

        assert (
            seeds[0].motor_key
            ==
            "MOTOR_B"
        )

        print("\n" + "=" * 76)
        print("TEST 5 — MOTOR FILTER")
        print("=" * 76)

        print(
            "PASS: optional motor filter works."
        )


# ============================================================
# TEST 6 — UNKNOWN MOTOR
# ============================================================

def test_unknown_motor():

    text = """
planetary:

  search:

    motor_keys:
      - MOTOR_DOES_NOT_EXIST

    sun_teeth:
      min: 20
      max: 20
      step: 1

    planet_teeth:
      min: 40
      max: 40
      step: 1

    planet_counts:
      - 4

    modules_mm:
      - 0.5

    face_widths_mm:
      - 8.0
"""

    with TemporaryDirectory() as tmp:

        config = create_config(
            Path(tmp),
            text,
        )

        try:

            list(
                generate_candidate_seeds(
                    config,
                    MOTORS,
                )
            )

        except CandidateGenerationError as exc:

            print("\n" + "=" * 76)
            print("TEST 6 — UNKNOWN MOTOR")
            print("=" * 76)

            print(
                f"Expected error: {exc}"
            )

            print(
                "PASS: unknown motor rejected."
            )

            return

        raise AssertionError(
            "Expected CandidateGenerationError."
        )


# ============================================================
# TEST 7 — INVALID RANGE
# ============================================================

def test_invalid_range():

    text = """
planetary:

  search:

    sun_teeth:
      min: 30
      max: 20
      step: 1

    planet_teeth:
      min: 40
      max: 50
      step: 1

    planet_counts:
      - 4

    modules_mm:
      - 0.5

    face_widths_mm:
      - 8.0
"""

    with TemporaryDirectory() as tmp:

        config = create_config(
            Path(tmp),
            text,
        )

        try:

            list(
                generate_candidate_seeds(
                    config,
                    MOTORS,
                )
            )

        except CandidateGenerationError as exc:

            print("\n" + "=" * 76)
            print("TEST 7 — INVALID RANGE")
            print("=" * 76)

            print(
                f"Expected error: {exc}"
            )

            print(
                "PASS: invalid range rejected."
            )

            return

        raise AssertionError(
            "Expected CandidateGenerationError."
        )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    test_search_space()
    test_candidate_count()
    test_generation()
    test_deterministic_order()
    test_motor_filter()
    test_unknown_motor()
    test_invalid_range()

    print("\n" + "=" * 76)
    print("ALL CANDIDATE GENERATOR TESTS PASSED")
    print("=" * 76)