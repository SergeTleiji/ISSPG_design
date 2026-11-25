"""
Standalone tests for src/config_loader.py

Run:

    python -m tests.config_loader
"""

from pathlib import Path
from tempfile import TemporaryDirectory

from src.config_loader import (
    ConfigError,
    load_config,
)


TEST_CONFIG = """
requirements:
  output_speed_rpm: 90.0
  output_torque_nm: 7.45

planetary:

  search:

    sun_teeth:
      min: 17
      max: 30
      step: 1

    planet_counts:
      - 3
      - 4

    modules_mm:
      - 0.5
      - 0.6

  ratio:
    min: 4.0
    max: 8.0

  efficiency: null

ring:
  min_backup_ratio: 1.2
"""


def create_config(
    directory: Path,
) -> Path:

    path = (
        directory
        / "config.yaml"
    )

    path.write_text(
        TEST_CONFIG,
        encoding="utf-8",
    )

    return path


# ============================================================
# TEST 1
# ============================================================

def test_basic_load():

    with TemporaryDirectory() as tmp:

        path = create_config(
            Path(tmp)
        )

        config = load_config(
            path
        )

        assert (
            config.require(
                "requirements.output_speed_rpm"
            )
            ==
            90.0
        )

        print("\n" + "=" * 76)
        print("TEST 1 — BASIC LOAD")
        print("=" * 76)

        print(
            "PASS: configuration loaded."
        )


# ============================================================
# TEST 2
# ============================================================

def test_nested_value():

    with TemporaryDirectory() as tmp:

        config = load_config(
            create_config(
                Path(tmp)
            )
        )

        value = (
            config.require_number(
                "planetary.ratio.min",
                positive=True,
            )
        )

        assert value == 4.0

        print("\n" + "=" * 76)
        print("TEST 2 — NESTED VALUE")
        print("=" * 76)

        print(
            f"ratio.min = {value}"
        )

        print(
            "PASS: nested path lookup works."
        )


# ============================================================
# TEST 3
# ============================================================

def test_null_allowed_until_required():

    with TemporaryDirectory() as tmp:

        config = load_config(
            create_config(
                Path(tmp)
            )
        )

        assert not config.has_value(
            "planetary.efficiency"
        )

        assert (
            config.get(
                "planetary.efficiency"
            )
            is None
        )

        try:

            config.require(
                "planetary.efficiency"
            )

        except ConfigError as exc:

            print("\n" + "=" * 76)
            print("TEST 3 — NULL VALUE")
            print("=" * 76)

            print(
                f"Expected error: {exc}"
            )

            print(
                "PASS: null becomes an error "
                "only when required."
            )

            return

        raise AssertionError(
            "Expected ConfigError."
        )


# ============================================================
# TEST 4
# ============================================================

def test_list():

    with TemporaryDirectory() as tmp:

        config = load_config(
            create_config(
                Path(tmp)
            )
        )

        values = config.require_list(
            "planetary.search.modules_mm"
        )

        assert values == [
            0.5,
            0.6,
        ]

        print("\n" + "=" * 76)
        print("TEST 4 — LIST")
        print("=" * 76)

        print(
            f"Modules: {values}"
        )

        print(
            "PASS: list retrieval works."
        )


# ============================================================
# TEST 5
# ============================================================

def test_missing_value():

    with TemporaryDirectory() as tmp:

        config = load_config(
            create_config(
                Path(tmp)
            )
        )

        try:

            config.require(
                "does.not.exist"
            )

        except ConfigError as exc:

            print("\n" + "=" * 76)
            print("TEST 5 — MISSING VALUE")
            print("=" * 76)

            print(
                f"Expected error: {exc}"
            )

            print(
                "PASS: missing value rejected."
            )

            return

        raise AssertionError(
            "Expected ConfigError."
        )


# ============================================================
# TEST 6
# ============================================================

def test_integer_validation():

    with TemporaryDirectory() as tmp:

        config = load_config(
            create_config(
                Path(tmp)
            )
        )

        value = config.require_int(
            "planetary.search.sun_teeth.min",
            positive=True,
        )

        assert value == 17

        print("\n" + "=" * 76)
        print("TEST 6 — INTEGER")
        print("=" * 76)

        print(
            f"Sun minimum teeth: {value}"
        )

        print(
            "PASS: integer validation works."
        )


if __name__ == "__main__":

    test_basic_load()
    test_nested_value()
    test_null_allowed_until_required()
    test_list()
    test_missing_value()
    test_integer_validation()

    print("\n" + "=" * 76)
    print("ALL CONFIG LOADER TESTS PASSED")
    print("=" * 76)