"""
CATALOGUE -> ENGINEERING MODEL ADAPTERS

Purpose:
    Convert generic catalogue entries into the specialized
    dataclasses expected by individual engineering modules.

Example:

    MotorCatalogueEntry
        -> MotorSpec

    MaterialCatalogueEntry
        -> GearMaterial
        -> ShaftMaterial
        -> CarrierMaterial
        -> ...

    BearingCatalogueEntry
        -> BallBearingSpec
        -> NeedleBearingSpec
        -> OutputBearingSpec

No engineering calculations are performed here.

IMPORTANT:
    Missing material properties required by a target component
    are rejected immediately.
"""

from __future__ import annotations

from dataclasses import (
    MISSING,
    fields,
    is_dataclass,
)
from typing import Any, Type

from src.catalogue_loader import (
    BearingCatalogueEntry,
    MaterialCatalogueEntry,
    MotorCatalogueEntry,
)


# ============================================================
# EXCEPTION
# ============================================================

class AdapterError(ValueError):
    """Raised when a catalogue entry cannot populate a model."""


# ============================================================
# GENERIC DATACLASS BUILDER
# ============================================================

def _build_dataclass(
    target_class: Type,
    values: dict[str, Any],
):
    """
    Construct a target dataclass using matching field names.

    values may include aliases for the same physical quantity.

    Required target fields that cannot be populated cause an
    AdapterError.
    """

    if not is_dataclass(
        target_class
    ):
        raise AdapterError(
            f"{target_class} is not a dataclass."
        )

    kwargs = {}

    for field_info in fields(
        target_class
    ):

        if not field_info.init:
            continue

        field_name = (
            field_info.name
        )

        if field_name in values:

            value = values[
                field_name
            ]

            if value is None:

                if (
                    field_info.default
                    is MISSING
                    and
                    field_info.default_factory
                    is MISSING
                ):
                    raise AdapterError(
                        f"Cannot construct "
                        f"{target_class.__name__}: "
                        f"required field "
                        f"'{field_name}' is unavailable."
                    )

                continue

            kwargs[field_name] = (
                value
            )

            continue

        # Required target field not mapped.
        if (
            field_info.default
            is MISSING
            and
            field_info.default_factory
            is MISSING
        ):
            raise AdapterError(
                f"Cannot construct "
                f"{target_class.__name__}: "
                f"no adapter value for required "
                f"field '{field_name}'."
            )

    return target_class(
        **kwargs
    )


# ============================================================
# MOTOR VALUES
# ============================================================

def _motor_values(
    motor: MotorCatalogueEntry,
) -> dict:

    return {

        "name":
            motor.name,

        "rated_voltage_V":
            motor.rated_voltage_V,

        "outer_diameter_mm":
            motor.outer_diameter_mm,

        "axial_length_mm":
            motor.axial_length_mm,

        "stator_id_min_mm":
            motor.stator_id_min_mm,

        "rated_torque_nm":
            motor.rated_torque_nm,

        "peak_torque_nm":
            motor.peak_torque_nm,

        "rated_speed_rpm":
            motor.rated_speed_rpm,

        "no_load_speed_rpm":
            motor.no_load_speed_rpm,

        "Kt_nm_per_A":
            motor.Kt_nm_per_A,

        "Kv_rpm_per_V":
            motor.Kv_rpm_per_V,

        "rated_current_A":
            motor.rated_current_A,

        "peak_current_A":
            motor.peak_current_A,

        "phase_to_phase_resistance_ohm":
            motor.phase_to_phase_resistance_ohm,

        "rotor_inertia_kgm2":
            motor.rotor_inertia_kgm2,

        "mass_kg":
            motor.mass_kg,
    }


# ============================================================
# MATERIAL VALUES
# ============================================================

def _material_values(
    material: MaterialCatalogueEntry,
) -> dict:

    return {

        "name":
            material.name,

        # Strength
        "Sy_MPa":
            material.Sy_MPa,

        "Sut_MPa":
            material.Sut_MPa,

        "Se_prime_MPa":
            material.Se_prime_MPa,

        # Elastic properties
        "elastic_modulus_GPa":
            material.E_GPa,

        "E_GPa":
            material.E_GPa,

        "shear_modulus_GPa":
            material.G_GPa,

        "G_GPa":
            material.G_GPa,

        "poisson_ratio":
            material.poisson_ratio,

        # Density
        "density_kg_m3":
            material.density_kg_m3,

        # AGMA
        "St_MPa":
            material.St_MPa,

        "Sc_MPa":
            material.Sc_MPa,

        # Bearing / pin-hole allowable
        "S_br_allow_MPa":
            material.S_br_allow_MPa,

        "hardness_HB":
            material.hardness_HB,
    }


# ============================================================
# BEARING VALUES
# ============================================================

def _bearing_values(
    bearing: BearingCatalogueEntry,
) -> dict:

    return {

        "designation":
            bearing.designation,

        "bore_mm":
            bearing.bore_mm,

        # OD aliases
        "outer_diameter_mm":
            bearing.outer_diameter_mm,

        "OD_mm":
            bearing.outer_diameter_mm,

        # Width
        "width_mm":
            bearing.width_mm,

        # Dynamic rating aliases
        "C_N":
            bearing.C_N,

        "C":
            bearing.C_N,

        "dynamic_load_rating_N":
            bearing.C_N,

        "dynamic_rating_N":
            bearing.C_N,

        # Static rating aliases
        "C0_N":
            bearing.C0_N,

        "C0":
            bearing.C0_N,

        "static_load_rating_N":
            bearing.C0_N,

        "static_rating_N":
            bearing.C0_N,

        # Speed
        "limiting_speed_rpm":
            bearing.limiting_speed_rpm,

        "limit_speed_rpm":
            bearing.limiting_speed_rpm,

        # Mass
        "mass_kg":
            bearing.mass_kg,
    }


# ============================================================
# MOTOR
# ============================================================

def motor_to_spec(
    motor: MotorCatalogueEntry,
):
    """
    MotorCatalogueEntry -> MotorSpec
    """

    from src.motor_compatibility import (
        MotorSpec,
    )

    return _build_dataclass(
        MotorSpec,
        _motor_values(
            motor
        ),
    )


# ============================================================
# GEAR MATERIAL
# ============================================================

def material_to_gear_material(
    material: MaterialCatalogueEntry,
):
    """
    MaterialCatalogueEntry -> GearMaterial

    Requires:
        E
        nu
        St
        Sc
    """

    if material.St_MPa is None:

        raise AdapterError(
            f"Material '{material.key}' "
            f"has no St_MPa for gear bending."
        )

    if material.Sc_MPa is None:

        raise AdapterError(
            f"Material '{material.key}' "
            f"has no Sc_MPa for gear contact."
        )

    from src.gear_strength import (
        GearMaterial,
    )

    return _build_dataclass(
        GearMaterial,
        _material_values(
            material
        ),
    )


# ============================================================
# SUN SHAFT MATERIAL
# ============================================================

def material_to_shaft_material(
    material: MaterialCatalogueEntry,
):
    """
    MaterialCatalogueEntry -> ShaftMaterial
    """

    from src.sun_shaft import (
        ShaftMaterial,
    )

    return _build_dataclass(
        ShaftMaterial,
        _material_values(
            material
        ),
    )


# ============================================================
# ROTOR SUPPORT MATERIAL
# ============================================================

def material_to_rotor_support_material(
    material: MaterialCatalogueEntry,
):
    """
    MaterialCatalogueEntry -> RotorSupportMaterial
    """

    from src.rotor_support import (
        RotorSupportMaterial,
    )

    return _build_dataclass(
        RotorSupportMaterial,
        _material_values(
            material
        ),
    )


# ============================================================
# PLANET PIN MATERIAL
# ============================================================

def material_to_pin_material(
    material: MaterialCatalogueEntry,
):
    """
    MaterialCatalogueEntry -> PinMaterial
    """

    from src.planet_pin_bearing import (
        PinMaterial,
    )

    return _build_dataclass(
        PinMaterial,
        _material_values(
            material
        ),
    )


# ============================================================
# OUTPUT SHAFT MATERIAL
# ============================================================

def material_to_output_shaft_material(
    material: MaterialCatalogueEntry,
):
    """
    MaterialCatalogueEntry -> OutputShaftMaterial
    """

    from src.output_system import (
        OutputShaftMaterial,
    )

    return _build_dataclass(
        OutputShaftMaterial,
        _material_values(
            material
        ),
    )


# ============================================================
# CARRIER MATERIAL
# ============================================================

def material_to_carrier_material(
    material: MaterialCatalogueEntry,
):
    """
    MaterialCatalogueEntry -> CarrierMaterial
    """

    if (
        material.S_br_allow_MPa
        is None
    ):
        raise AdapterError(
            f"Material '{material.key}' has no "
            f"S_br_allow_MPa for carrier pin-hole sizing."
        )

    from src.carrier import (
        CarrierMaterial,
    )

    return _build_dataclass(
        CarrierMaterial,
        _material_values(
            material
        ),
    )


# ============================================================
# RING MATERIAL
# ============================================================

def material_to_ring_material(
    material: MaterialCatalogueEntry,
):
    """
    MaterialCatalogueEntry -> RingMaterial
    """

    from src.ring import (
        RingMaterial,
    )

    return _build_dataclass(
        RingMaterial,
        _material_values(
            material
        ),
    )


# ============================================================
# ROTOR/SUN BALL BEARING
# ============================================================

def bearing_to_rotor_support_spec(
    bearing: BearingCatalogueEntry,
):
    """
    BearingCatalogueEntry -> BallBearingSpec
    """

    if (
        bearing.type
        !=
        "deep_groove_ball"
    ):
        raise AdapterError(
            f"Bearing '{bearing.designation}' "
            f"is not a deep-groove ball bearing."
        )

    from src.rotor_support import (
        BallBearingSpec,
    )

    return _build_dataclass(
        BallBearingSpec,
        _bearing_values(
            bearing
        ),
    )


# ============================================================
# PLANET NEEDLE BEARING
# ============================================================

def bearing_to_needle_spec(
    bearing: BearingCatalogueEntry,
):
    """
    BearingCatalogueEntry -> NeedleBearingSpec
    """

    if (
        bearing.type
        !=
        "needle_with_inner_ring"
    ):
        raise AdapterError(
            f"Bearing '{bearing.designation}' "
            f"is not a needle bearing with inner ring."
        )

    if not bearing.has_inner_ring:

        raise AdapterError(
            f"Bearing '{bearing.designation}' "
            f"does not include an inner ring."
        )

    from src.planet_pin_bearing import (
        NeedleBearingSpec,
    )

    return _build_dataclass(
        NeedleBearingSpec,
        _bearing_values(
            bearing
        ),
    )


# ============================================================
# OUTPUT BALL BEARING
# ============================================================

def bearing_to_output_spec(
    bearing: BearingCatalogueEntry,
):
    """
    BearingCatalogueEntry -> OutputBearingSpec
    """

    if (
        bearing.type
        !=
        "deep_groove_ball"
    ):
        raise AdapterError(
            f"Bearing '{bearing.designation}' "
            f"is not a deep-groove ball bearing."
        )

    from src.output_system import (
        OutputBearingSpec,
    )

    return _build_dataclass(
        OutputBearingSpec,
        _bearing_values(
            bearing
        ),
    )