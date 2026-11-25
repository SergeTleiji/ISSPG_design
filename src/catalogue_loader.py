"""
CATALOGUE LOADER

Purpose:
    Load and validate the external engineering catalogues used by the
    ISSPG feasibility pipeline.

FILES LOADED
------------
    data/motors.yaml
    data/bearings.csv
    data/materials.yaml

OUTPUTS
-------
    MotorCatalogueEntry objects
    BearingCatalogueEntry objects
    MaterialCatalogueEntry objects

    CatalogueBundle containing:
        motors
        bearings
        materials

DESIGN PRINCIPLES
-----------------
    - Parsing and validation happen once here.
    - Engineering modules do not read YAML/CSV directly.
    - Missing required fields fail immediately.
    - Catalogue keys/designations must be unique.
    - Optional material properties may be null where they are not
      applicable to that material/component.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

import csv
import yaml


# ============================================================
# EXCEPTIONS
# ============================================================

class CatalogueError(ValueError):
    """Raised when catalogue data are missing or invalid."""


# ============================================================
# MOTOR CATALOGUE ENTRY
# ============================================================

@dataclass(frozen=True)
class MotorCatalogueEntry:

    key: str
    name: str

    rated_voltage_V: float

    outer_diameter_mm: float
    axial_length_mm: float

    stator_id_nominal_mm: float
    stator_id_min_mm: float
    stator_id_max_mm: float

    rated_torque_nm: float
    peak_torque_nm: float

    rated_speed_rpm: float
    no_load_speed_rpm: float

    Kt_nm_per_A: float
    Kv_rpm_per_V: float

    rated_current_A: float
    peak_current_A: float

    phase_to_phase_resistance_ohm: float

    rotor_inertia_kgm2: float

    mass_kg: float


# ============================================================
# BEARING CATALOGUE ENTRY
# ============================================================

@dataclass(frozen=True)
class BearingCatalogueEntry:

    designation: str

    type: str
    has_inner_ring: bool

    bore_mm: float
    outer_diameter_mm: float
    width_mm: float

    C_N: float
    C0_N: float

    limiting_speed_rpm: float

    mass_kg: float


# ============================================================
# MATERIAL CATALOGUE ENTRY
# ============================================================

@dataclass(frozen=True)
class MaterialCatalogueEntry:

    key: str
    name: str

    material_type: str

    density_kg_m3: float

    E_GPa: float
    G_GPa: float
    poisson_ratio: float

    Sy_MPa: float
    Sut_MPa: float

    Se_prime_MPa: float

    # Optional because not every material is intended
    # for AGMA gear calculations.
    St_MPa: Optional[float]
    Sc_MPa: Optional[float]

    # Nominal pin-hole / bearing-contact allowable
    S_br_allow_MPa: Optional[float]

    hardness_HB: Optional[float]


# ============================================================
# COMPLETE CATALOGUE BUNDLE
# ============================================================

@dataclass(frozen=True)
class CatalogueBundle:

    motors: Dict[str, MotorCatalogueEntry]

    bearings: Dict[str, BearingCatalogueEntry]

    materials: Dict[str, MaterialCatalogueEntry]


# ============================================================
# GENERAL HELPERS
# ============================================================

def _require_mapping(
    data,
    context: str,
) -> dict:

    if not isinstance(data, dict):
        raise CatalogueError(
            f"{context} must be a mapping/dictionary."
        )

    return data


def _required(
    data: dict,
    field: str,
    context: str,
):

    if field not in data:
        raise CatalogueError(
            f"Missing required field '{field}' in {context}."
        )

    value = data[field]

    if value is None:
        raise CatalogueError(
            f"Required field '{field}' is null in {context}."
        )

    return value


def _positive_float(
    value,
    field: str,
    context: str,
) -> float:

    try:
        result = float(value)

    except (TypeError, ValueError) as exc:
        raise CatalogueError(
            f"Field '{field}' in {context} must be numeric."
        ) from exc

    if result <= 0:
        raise CatalogueError(
            f"Field '{field}' in {context} must be > 0."
        )

    return result


def _nonnegative_float(
    value,
    field: str,
    context: str,
) -> float:

    try:
        result = float(value)

    except (TypeError, ValueError) as exc:
        raise CatalogueError(
            f"Field '{field}' in {context} must be numeric."
        ) from exc

    if result < 0:
        raise CatalogueError(
            f"Field '{field}' in {context} must be >= 0."
        )

    return result


def _optional_float(
    value,
    field: str,
    context: str,
) -> Optional[float]:

    if value is None:
        return None

    # CSV files sometimes represent null as an empty string.
    if isinstance(value, str) and value.strip() == "":
        return None

    try:
        result = float(value)

    except (TypeError, ValueError) as exc:
        raise CatalogueError(
            f"Optional field '{field}' in {context} "
            f"must be numeric or null."
        ) from exc

    return result


def _parse_bool(
    value,
    field: str,
    context: str,
) -> bool:

    if isinstance(value, bool):
        return value

    if isinstance(value, str):

        normalized = value.strip().lower()

        if normalized in ("true", "1", "yes"):
            return True

        if normalized in ("false", "0", "no"):
            return False

    raise CatalogueError(
        f"Field '{field}' in {context} must be boolean."
    )


# ============================================================
# MOTOR LOADER
# ============================================================

def load_motor_catalogue(
    path: str | Path = "data/motors.yaml",
) -> Dict[str, MotorCatalogueEntry]:

    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"Motor catalogue not found: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:

        raw = yaml.safe_load(file)

    root = _require_mapping(
        raw,
        "motor catalogue root",
    )

    motors_raw = _require_mapping(
        _required(
            root,
            "motors",
            "motor catalogue root",
        ),
        "motors",
    )

    motors = {}

    for key, data in motors_raw.items():

        context = f"motor '{key}'"

        data = _require_mapping(
            data,
            context,
        )

        motor = MotorCatalogueEntry(

            key=str(key),

            name=str(
                _required(
                    data,
                    "name",
                    context,
                )
            ),

            rated_voltage_V=_positive_float(
                _required(
                    data,
                    "rated_voltage_V",
                    context,
                ),
                "rated_voltage_V",
                context,
            ),

            outer_diameter_mm=_positive_float(
                _required(
                    data,
                    "outer_diameter_mm",
                    context,
                ),
                "outer_diameter_mm",
                context,
            ),

            axial_length_mm=_positive_float(
                _required(
                    data,
                    "axial_length_mm",
                    context,
                ),
                "axial_length_mm",
                context,
            ),

            stator_id_nominal_mm=_positive_float(
                _required(
                    data,
                    "stator_id_nominal_mm",
                    context,
                ),
                "stator_id_nominal_mm",
                context,
            ),

            stator_id_min_mm=_positive_float(
                _required(
                    data,
                    "stator_id_min_mm",
                    context,
                ),
                "stator_id_min_mm",
                context,
            ),

            stator_id_max_mm=_positive_float(
                _required(
                    data,
                    "stator_id_max_mm",
                    context,
                ),
                "stator_id_max_mm",
                context,
            ),

            rated_torque_nm=_positive_float(
                _required(
                    data,
                    "rated_torque_nm",
                    context,
                ),
                "rated_torque_nm",
                context,
            ),

            peak_torque_nm=_positive_float(
                _required(
                    data,
                    "peak_torque_nm",
                    context,
                ),
                "peak_torque_nm",
                context,
            ),

            rated_speed_rpm=_positive_float(
                _required(
                    data,
                    "rated_speed_rpm",
                    context,
                ),
                "rated_speed_rpm",
                context,
            ),

            no_load_speed_rpm=_positive_float(
                _required(
                    data,
                    "no_load_speed_rpm",
                    context,
                ),
                "no_load_speed_rpm",
                context,
            ),

            Kt_nm_per_A=_positive_float(
                _required(
                    data,
                    "Kt_nm_per_A",
                    context,
                ),
                "Kt_nm_per_A",
                context,
            ),

            Kv_rpm_per_V=_positive_float(
                _required(
                    data,
                    "Kv_rpm_per_V",
                    context,
                ),
                "Kv_rpm_per_V",
                context,
            ),

            rated_current_A=_positive_float(
                _required(
                    data,
                    "rated_current_A",
                    context,
                ),
                "rated_current_A",
                context,
            ),

            peak_current_A=_positive_float(
                _required(
                    data,
                    "peak_current_A",
                    context,
                ),
                "peak_current_A",
                context,
            ),

            phase_to_phase_resistance_ohm=_positive_float(
                _required(
                    data,
                    "phase_to_phase_resistance_ohm",
                    context,
                ),
                "phase_to_phase_resistance_ohm",
                context,
            ),

            rotor_inertia_kgm2=_positive_float(
                _required(
                    data,
                    "rotor_inertia_kgm2",
                    context,
                ),
                "rotor_inertia_kgm2",
                context,
            ),

            mass_kg=_positive_float(
                _required(
                    data,
                    "mass_kg",
                    context,
                ),
                "mass_kg",
                context,
            ),
        )

        # ----------------------------------------------------
        # Motor consistency checks
        # ----------------------------------------------------

        if (
            motor.stator_id_min_mm
            >
            motor.stator_id_nominal_mm
        ):
            raise CatalogueError(
                f"{context}: stator_id_min_mm cannot exceed "
                f"stator_id_nominal_mm."
            )

        if (
            motor.stator_id_nominal_mm
            >
            motor.stator_id_max_mm
        ):
            raise CatalogueError(
                f"{context}: stator_id_nominal_mm cannot exceed "
                f"stator_id_max_mm."
            )

        if (
            motor.rated_torque_nm
            >
            motor.peak_torque_nm
        ):
            raise CatalogueError(
                f"{context}: rated torque exceeds peak torque."
            )

        if (
            motor.rated_current_A
            >
            motor.peak_current_A
        ):
            raise CatalogueError(
                f"{context}: rated current exceeds peak current."
            )

        if (
            motor.rated_speed_rpm
            >
            motor.no_load_speed_rpm
        ):
            raise CatalogueError(
                f"{context}: rated speed exceeds no-load speed."
            )

        motors[key] = motor

    if not motors:
        raise CatalogueError(
            "Motor catalogue contains no motors."
        )

    return motors


# ============================================================
# BEARING LOADER
# ============================================================

def load_bearing_catalogue(
    path: str | Path = "data/bearings.csv",
) -> Dict[str, BearingCatalogueEntry]:

    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"Bearing catalogue not found: {path}"
        )

    bearings = {}

    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:

        reader = csv.DictReader(file)

        required_columns = {
            "designation",
            "type",
            "has_inner_ring",
            "bore_mm",
            "outer_diameter_mm",
            "width_mm",
            "C_N",
            "C0_N",
            "limiting_speed_rpm",
            "mass_kg",
        }

        if reader.fieldnames is None:
            raise CatalogueError(
                "Bearing catalogue has no header row."
            )

        missing_columns = (
            required_columns
            -
            set(reader.fieldnames)
        )

        if missing_columns:
            raise CatalogueError(
                "Bearing catalogue missing columns: "
                + ", ".join(
                    sorted(missing_columns)
                )
            )

        for row_number, row in enumerate(
            reader,
            start=2,
        ):

            designation = (
                row["designation"].strip()
            )

            context = (
                f"bearing row {row_number}"
            )

            if not designation:
                raise CatalogueError(
                    f"{context}: empty designation."
                )

            if designation in bearings:
                raise CatalogueError(
                    f"Duplicate bearing designation "
                    f"'{designation}'."
                )

            bearing_type = (
                row["type"].strip()
            )

            if bearing_type not in (
                "deep_groove_ball",
                "needle_with_inner_ring",
            ):
                raise CatalogueError(
                    f"{context}: unsupported bearing type "
                    f"'{bearing_type}'."
                )

            bearing = BearingCatalogueEntry(

                designation=designation,

                type=bearing_type,

                has_inner_ring=_parse_bool(
                    row["has_inner_ring"],
                    "has_inner_ring",
                    context,
                ),

                bore_mm=_positive_float(
                    row["bore_mm"],
                    "bore_mm",
                    context,
                ),

                outer_diameter_mm=_positive_float(
                    row["outer_diameter_mm"],
                    "outer_diameter_mm",
                    context,
                ),

                width_mm=_positive_float(
                    row["width_mm"],
                    "width_mm",
                    context,
                ),

                C_N=_positive_float(
                    row["C_N"],
                    "C_N",
                    context,
                ),

                C0_N=_positive_float(
                    row["C0_N"],
                    "C0_N",
                    context,
                ),

                limiting_speed_rpm=_positive_float(
                    row["limiting_speed_rpm"],
                    "limiting_speed_rpm",
                    context,
                ),

                mass_kg=_nonnegative_float(
                    row["mass_kg"],
                    "mass_kg",
                    context,
                ),
            )

            if (
                bearing.outer_diameter_mm
                <=
                bearing.bore_mm
            ):
                raise CatalogueError(
                    f"{context}: bearing OD must exceed bore."
                )

            if (
                bearing.type
                ==
                "needle_with_inner_ring"
                and not bearing.has_inner_ring
            ):
                raise CatalogueError(
                    f"{context}: needle_with_inner_ring "
                    f"must have has_inner_ring=true."
                )

            bearings[designation] = (
                bearing
            )

    if not bearings:
        raise CatalogueError(
            "Bearing catalogue contains no bearings."
        )

    return bearings


# ============================================================
# MATERIAL LOADER
# ============================================================

def load_material_catalogue(
    path: str | Path = "data/materials.yaml",
) -> Dict[str, MaterialCatalogueEntry]:

    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"Material catalogue not found: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:

        raw = yaml.safe_load(file)

    root = _require_mapping(
        raw,
        "material catalogue root",
    )

    materials_raw = _require_mapping(
        _required(
            root,
            "materials",
            "material catalogue root",
        ),
        "materials",
    )

    materials = {}

    for key, data in materials_raw.items():

        context = (
            f"material '{key}'"
        )

        data = _require_mapping(
            data,
            context,
        )

        material = MaterialCatalogueEntry(

            key=str(key),

            name=str(
                _required(
                    data,
                    "name",
                    context,
                )
            ),

            material_type=str(
                _required(
                    data,
                    "material_type",
                    context,
                )
            ),

            density_kg_m3=_positive_float(
                _required(
                    data,
                    "density_kg_m3",
                    context,
                ),
                "density_kg_m3",
                context,
            ),

            E_GPa=_positive_float(
                _required(
                    data,
                    "E_GPa",
                    context,
                ),
                "E_GPa",
                context,
            ),

            G_GPa=_positive_float(
                _required(
                    data,
                    "G_GPa",
                    context,
                ),
                "G_GPa",
                context,
            ),

            poisson_ratio=_positive_float(
                _required(
                    data,
                    "poisson_ratio",
                    context,
                ),
                "poisson_ratio",
                context,
            ),

            Sy_MPa=_positive_float(
                _required(
                    data,
                    "Sy_MPa",
                    context,
                ),
                "Sy_MPa",
                context,
            ),

            Sut_MPa=_positive_float(
                _required(
                    data,
                    "Sut_MPa",
                    context,
                ),
                "Sut_MPa",
                context,
            ),

            Se_prime_MPa=_positive_float(
                _required(
                    data,
                    "Se_prime_MPa",
                    context,
                ),
                "Se_prime_MPa",
                context,
            ),

            St_MPa=_optional_float(
                data.get("St_MPa"),
                "St_MPa",
                context,
            ),

            Sc_MPa=_optional_float(
                data.get("Sc_MPa"),
                "Sc_MPa",
                context,
            ),

            S_br_allow_MPa=_optional_float(
                data.get(
                    "S_br_allow_MPa"
                ),
                "S_br_allow_MPa",
                context,
            ),

            hardness_HB=_optional_float(
                data.get("hardness_HB"),
                "hardness_HB",
                context,
            ),
        )

        # ----------------------------------------------------
        # Material consistency checks
        # ----------------------------------------------------

        if (
            material.Sy_MPa
            >
            material.Sut_MPa
        ):
            raise CatalogueError(
                f"{context}: yield strength exceeds "
                f"ultimate tensile strength."
            )

        if not (
            0.0
            <
            material.poisson_ratio
            <
            0.5
        ):
            raise CatalogueError(
                f"{context}: Poisson ratio must lie "
                f"between 0 and 0.5."
            )

        for field_name in (
            "St_MPa",
            "Sc_MPa",
            "S_br_allow_MPa",
            "hardness_HB",
        ):

            value = getattr(
                material,
                field_name,
            )

            if (
                value is not None
                and value <= 0
            ):
                raise CatalogueError(
                    f"{context}: {field_name} "
                    f"must be > 0 when provided."
                )

        materials[key] = material

    if not materials:
        raise CatalogueError(
            "Material catalogue contains no materials."
        )

    return materials


# ============================================================
# COMPLETE BUNDLE LOADER
# ============================================================

def load_catalogues(
    motor_path: str | Path = "data/motors.yaml",
    bearing_path: str | Path = "data/bearings.csv",
    material_path: str | Path = "data/materials.yaml",
) -> CatalogueBundle:

    return CatalogueBundle(

        motors=load_motor_catalogue(
            motor_path
        ),

        bearings=load_bearing_catalogue(
            bearing_path
        ),

        materials=load_material_catalogue(
            material_path
        ),
    )


# ============================================================
# FILTER HELPERS
# ============================================================

def get_ball_bearings(
    bearings: Dict[
        str,
        BearingCatalogueEntry,
    ],
) -> list[BearingCatalogueEntry]:

    return sorted(
        (
            bearing
            for bearing in bearings.values()
            if bearing.type
            ==
            "deep_groove_ball"
        ),
        key=lambda bearing: (
            bearing.bore_mm,
            bearing.outer_diameter_mm,
            bearing.width_mm,
        ),
    )


def get_needle_bearings(
    bearings: Dict[
        str,
        BearingCatalogueEntry,
    ],
) -> list[BearingCatalogueEntry]:

    return sorted(
        (
            bearing
            for bearing in bearings.values()
            if bearing.type
            ==
            "needle_with_inner_ring"
        ),
        key=lambda bearing: (
            bearing.bore_mm,
            bearing.outer_diameter_mm,
            bearing.width_mm,
        ),
    )