"""
ISSPG QDD ACTUATOR — COMPLETE FEASIBILITY PIPELINE

Pipeline:

    load configuration
        ↓
    load catalogues
        ↓
    generate CandidateSeed objects
        ↓
    for each candidate:

        planetary
        ↓
        motor compatibility
        ↓
        gear forces
        ↓
        gear geometry Y_J
        ↓
        gear strength
        ↓
        sun shaft
        ↓
        rotor support + bearing selection
        ↓
        planet pin + needle-bearing selection
        ↓
        output shaft + bearing selection
        ↓
        carrier
        ↓
        ring
        ↓
        feasible

    rejected candidates stop immediately at their first
    failed engineering stage.

No ranking is performed yet.
"""

from __future__ import annotations

from dataclasses import (
    MISSING,
    fields,
)
from typing import Any


# ============================================================
# INFRASTRUCTURE
# ============================================================

from src.config_loader import (
    load_config,
    ProjectConfig,
)

from src.catalogue_loader import (
    load_catalogues,
    CatalogueBundle,
)

from src.candidate_generator import (
    generate_candidate_seeds,
    count_candidate_seeds,
)

from src.models import (
    Candidate,
    PipelineStage,
)

from src.reporting import (
    write_reports,
)

from src.selectors import (
    select_planet_bearing,
    select_rotor_support_bearing_pair,
    select_output_bearing_pair,
)


# ============================================================
# ADAPTERS
# ============================================================

from src.adapters import (
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
# ENGINEERING MODULES
# ============================================================

from src.planetary import (
    PlanetaryInput,
    PlanetaryConstraints,
    evaluate_planetary,
)

from src.motor_compatibility import (
    MotorCompatibilityInput,
    MotorCompatibilityConstraints,
    evaluate_motor_compatibility,
)

from src.gear_forces import (
    GearForceInput,
    GearForceConfig,
    evaluate_gear_forces,
)

from src.gear_geometry import (
    evaluate_planetary_yj,
)

from src.gear_strength import (
    GearGeometryFactors,
    GearStrengthInput,
    GearStrengthConfig,
    evaluate_gear_strength,
)

from src.sun_shaft import (
    SunShaftInput,
    SunShaftConfig,
    evaluate_sun_shaft,
)

from src.rotor_support import (
    RotorSupportInput,
    RotorSupportConfig,
    evaluate_rotor_support,
)

from src.planet_pin_bearing import (
    PlanetPinBearingInput,
    PlanetPinBearingConfig,
    evaluate_planet_pin_bearing,
)

from src.output_system import (
    OutputSystemInput,
    OutputSystemConfig,
    evaluate_output_system,
)

from src.carrier import (
    CarrierInput,
    CarrierConfig,
    evaluate_carrier,
)

from src.ring import (
    RingInput,
    RingConfig,
    evaluate_ring,
)


# ============================================================
# SMALL GENERIC HELPERS
# ============================================================

def _get_attr(
    obj,
    *names: str,
):
    """
    Read an attribute while allowing a few legacy aliases.

    This makes main.py tolerant of minor naming changes in older
    module versions.
    """

    for name in names:

        if hasattr(
            obj,
            name,
        ):

            return getattr(
                obj,
                name,
            )

    raise AttributeError(
        f"{type(obj).__name__} has none of the expected "
        f"attributes: {names}"
    )


def _build_dataclass(
    cls,
    values: dict[str, Any],
):
    """
    Construct a dataclass using matching entries from values.

    Extra values are ignored.

    Required target fields that are not supplied raise a clear
    error.
    """

    kwargs = {}

    missing = []

    for field_info in fields(
        cls
    ):

        if not field_info.init:
            continue

        name = field_info.name

        if (
            name in values
            and
            values[name] is not None
        ):

            kwargs[name] = (
                values[name]
            )

            continue

        if (
            field_info.default
            is MISSING
            and
            field_info.default_factory
            is MISSING
        ):

            missing.append(
                name
            )

    if missing:

        raise RuntimeError(
            f"Cannot construct {cls.__name__}. "
            f"Missing fields: {missing}. "
            f"Available values: "
            f"{sorted(values.keys())}"
        )

    return cls(
        **kwargs
    )


def _config_dataclass(
    config: ProjectConfig,
    cls,
    section: str,
):
    """
    Construct a module configuration dataclass directly from a
    YAML section whose keys match the dataclass field names.

    Example:

        gear_strength:
            Q_v: 8
            K_o: 1.25
            ...
    """

    kwargs = {}

    for field_info in fields(
        cls
    ):

        if not field_info.init:
            continue

        path = (
            f"{section}."
            f"{field_info.name}"
        )

        if config.has_value(
            path
        ):

            kwargs[
                field_info.name
            ] = config.require(
                path
            )

            continue

        # Required dataclass fields must exist.
        if (
            field_info.default
            is MISSING
            and
            field_info.default_factory
            is MISSING
        ):

            config.require(
                path
            )

    return cls(
        **kwargs
    )


def _attach_or_reject(
    candidate: Candidate,
    stage: PipelineStage,
    result,
) -> bool:
    """
    Attach a module result.

    Returns:
        True  -> candidate may continue
        False -> candidate was rejected
    """

    candidate.attach_result(
        stage,
        result,
    )

    if not result.feasible:

        candidate.reject(

            stage,

            result.rejection_reason
            or
            "engineering_check_failed",
        )

        return False

    return True


def _material_entry(
    config: ProjectConfig,
    catalogues: CatalogueBundle,
    config_path: str,
):
    """
    Retrieve one configured material catalogue entry.
    """

    key = str(
        config.require(
            config_path
        )
    )

    if key not in catalogues.materials:

        raise KeyError(
            f"Material '{key}' from "
            f"'{config_path}' does not exist "
            f"in materials catalogue."
        )

    return catalogues.materials[
        key
    ]


# ============================================================
# PREPARE FIXED PIPELINE DATA
# ============================================================

def build_pipeline_setup(
    config: ProjectConfig,
    catalogues: CatalogueBundle,
) -> dict:
    """
    Build all fixed configuration/material objects once.

    These objects are reused for every design candidate.
    """

    # ========================================================
    # BASIC REQUIREMENTS
    # ========================================================

    output_speed_rpm = (
        config.require_number(
            "requirements.output_speed_rpm",
            positive=True,
        )
    )

    output_torque_nm = (
        config.require_number(
            "requirements.output_torque_nm",
            positive=True,
        )
    )

    joint_radial_load_N = (
        config.require_number(
            "requirements.joint_radial_load_N",
            positive=True,
        )
    )

    # ========================================================
    # PLANETARY
    # ========================================================

    planetary_constraints = (
        PlanetaryConstraints(

            ratio_min=(
                config.require_number(
                    "planetary.ratio.min",
                    positive=True,
                )
            ),

            ratio_max=(
                config.require_number(
                    "planetary.ratio.max",
                    positive=True,
                )
            ),

            min_planet_clearance_mm=(
                config.require_number(
                    "planetary."
                    "min_planet_clearance_mm",
                    nonnegative=True,
                )
            ),
        )
    )

    planetary_efficiency = (
        config.require_number(
            "planetary.efficiency",
            positive=True,
        )
    )

    # ========================================================
    # MOTOR COMPATIBILITY
    #
    # Ring packaging constraints are shared with ring.py.
    # ========================================================

    motor_constraints = (
        MotorCompatibilityConstraints(

            min_ring_backup_ratio=(
                config.require_number(
                    "ring.min_backup_ratio",
                    positive=True,
                )
            ),

            ring_radial_clearance_mm=(
                config.require_number(
                    "ring.radial_clearance_mm",
                    nonnegative=True,
                )
            ),
        )
    )

    # ========================================================
    # MODULE CONFIGS
    # ========================================================

    gear_force_config = (
        _config_dataclass(
            config,
            GearForceConfig,
            "gear_forces",
        )
    )

    gear_strength_config = (
        _config_dataclass(
            config,
            GearStrengthConfig,
            "gear_strength",
        )
    )

    sun_shaft_config = (
        _config_dataclass(
            config,
            SunShaftConfig,
            "sun_shaft",
        )
    )

    rotor_support_config = (
        _config_dataclass(
            config,
            RotorSupportConfig,
            "rotor_support",
        )
    )

    planet_pin_config = (
        _config_dataclass(
            config,
            PlanetPinBearingConfig,
            "planet_pin_bearing",
        )
    )

    output_system_config = (
        _config_dataclass(
            config,
            OutputSystemConfig,
            "output_system",
        )
    )

    carrier_config = (
        _config_dataclass(
            config,
            CarrierConfig,
            "carrier",
        )
    )

    ring_config = (
        _config_dataclass(
            config,
            RingConfig,
            "ring",
        )
    )

    # ========================================================
    # SUN SHAFT TORQUE-CYCLE ASSUMPTION
    #
    # Tmin = ratio * Tmax
    #
    # Examples:
    #
    #   ratio =  0.0
    #       zero-to-peak pulsating torque
    #
    #   ratio = -1.0
    #       fully reversed torque
    #
    #   ratio =  1.0
    #       steady torque
    # ========================================================

    torque_cycle_ratio = (
        config.require_number(
            "sun_shaft."
            "torque_cycle."
            "min_to_max_ratio"
        )
    )

    if not (
        -1.0
        <=
        torque_cycle_ratio
        <=
        1.0
    ):

        raise ValueError(
            "sun_shaft.torque_cycle."
            "min_to_max_ratio "
            "must lie between -1 and 1."
        )

    # ========================================================
    # ROTOR SUPPORT PRELIMINARY GEOMETRY
    # ========================================================

    supported_rotating_mass_kg = (
        config.require_number(
            "rotor_support."
            "supported_rotating_mass_kg",
            positive=True,
        )
    )

    rotor_bearing_spacing_mm = (
        config.require_number(
            "rotor_support."
            "bearing_spacing_mm",
            positive=True,
        )
    )

    rotor_cg_position_mm = (
        config.require_number(
            "rotor_support."
            "cg_position_mm",
            nonnegative=True,
        )
    )

    # ========================================================
    # MATERIAL ASSIGNMENTS
    # ========================================================

    sun_gear_entry = _material_entry(
        config,
        catalogues,
        "materials.gears.sun",
    )

    planet_gear_entry = _material_entry(
        config,
        catalogues,
        "materials.gears.planet",
    )

    ring_gear_entry = _material_entry(
        config,
        catalogues,
        "materials.gears.ring",
    )

    sun_shaft_entry = _material_entry(
        config,
        catalogues,
        "materials.sun_shaft.material",
    )

    rotor_plate_entry = _material_entry(
        config,
        catalogues,
        "materials.rotor_drive_plate.material",
    )

    pin_entry = _material_entry(
        config,
        catalogues,
        "materials.planet_pin.material",
    )

    output_entry = _material_entry(
        config,
        catalogues,
        "materials.output_shaft.material",
    )

    carrier_entry = _material_entry(
        config,
        catalogues,
        "materials.carrier.material",
    )

    ring_structural_entry = (
        _material_entry(
            config,
            catalogues,
            "materials.ring_structural.material",
        )
    )

    # ========================================================
    # CONVERT MATERIALS INTO MODULE-SPECIFIC OBJECTS
    # ========================================================

    sun_gear_material = (
        material_to_gear_material(
            sun_gear_entry
        )
    )

    planet_gear_material = (
        material_to_gear_material(
            planet_gear_entry
        )
    )

    ring_gear_material = (
        material_to_gear_material(
            ring_gear_entry
        )
    )

    sun_shaft_material = (
        material_to_shaft_material(
            sun_shaft_entry
        )
    )

    rotor_support_material = (
        material_to_rotor_support_material(
            rotor_plate_entry
        )
    )

    pin_material = (
        material_to_pin_material(
            pin_entry
        )
    )

    output_material = (
        material_to_output_shaft_material(
            output_entry
        )
    )

    carrier_material = (
        material_to_carrier_material(
            carrier_entry
        )
    )

    ring_material = (
        material_to_ring_material(
            ring_structural_entry
        )
    )

    # ========================================================
    # RETURN FIXED SETUP
    # ========================================================

    return {

        "output_speed_rpm":
            output_speed_rpm,

        "output_torque_nm":
            output_torque_nm,

        "joint_radial_load_N":
            joint_radial_load_N,

        "planetary_constraints":
            planetary_constraints,

        "planetary_efficiency":
            planetary_efficiency,

        "motor_constraints":
            motor_constraints,

        "gear_force_config":
            gear_force_config,

        "gear_strength_config":
            gear_strength_config,

        "sun_shaft_config":
            sun_shaft_config,

        "rotor_support_config":
            rotor_support_config,

        "planet_pin_config":
            planet_pin_config,

        "output_system_config":
            output_system_config,

        "carrier_config":
            carrier_config,

        "ring_config":
            ring_config,

        "torque_cycle_ratio":
            torque_cycle_ratio,

        "supported_rotating_mass_kg":
            supported_rotating_mass_kg,

        "rotor_bearing_spacing_mm":
            rotor_bearing_spacing_mm,

        "rotor_cg_position_mm":
            rotor_cg_position_mm,

        "sun_gear_material":
            sun_gear_material,

        "planet_gear_material":
            planet_gear_material,

        "ring_gear_material":
            ring_gear_material,

        "sun_shaft_material":
            sun_shaft_material,

        "rotor_support_material":
            rotor_support_material,

        "pin_material":
            pin_material,

        "output_material":
            output_material,

        "carrier_material":
            carrier_material,

        "ring_material":
            ring_material,
    }


# ============================================================
# RUN ONE COMPLETE CANDIDATE
# ============================================================

def run_candidate_pipeline(
    candidate: Candidate,
    setup: dict,
    catalogues: CatalogueBundle,
) -> Candidate:

    seed = candidate.seed

    # ========================================================
    # 1. PLANETARY
    # ========================================================

    planetary_input = (
        PlanetaryInput(

            z_s=seed.z_s,

            z_p=seed.z_p,

            n_planets=(
                seed.n_planets
            ),

            module_mm=(
                seed.module_mm
            ),

            output_speed_rpm=(
                setup[
                    "output_speed_rpm"
                ]
            ),

            output_torque_nm=(
                setup[
                    "output_torque_nm"
                ]
            ),

            efficiency=(
                setup[
                    "planetary_efficiency"
                ]
            ),
        )
    )

    planetary = evaluate_planetary(

        planetary_input,

        setup[
            "planetary_constraints"
        ],
    )

    if not _attach_or_reject(

        candidate,

        PipelineStage.PLANETARY,

        planetary,
    ):
        return candidate

    # Convenient local values
    z_r = _get_attr(
        planetary,
        "z_r",
    )

    ratio = _get_attr(
        planetary,
        "ratio",
    )

    n_s_rpm = _get_attr(
        planetary,
        "n_s_rpm",
        "sun_speed_rpm",
    )

    n_p_rpm = _get_attr(
        planetary,
        "n_p_rpm",
        "planet_speed_rpm",
    )

    n_c_rpm = _get_attr(
        planetary,
        "n_c_rpm",
        "output_speed_rpm",
    )

    T_s_design_nm = _get_attr(
        planetary,
        "T_s_design_nm",
        "sun_design_torque_nm",
    )

    T_r_ideal_nm = _get_attr(
        planetary,
        "T_r_ideal_nm",
        "ring_reaction_torque_nm",
    )

    d_s_mm = _get_attr(
        planetary,
        "d_s_mm",
    )

    d_p_mm = _get_attr(
        planetary,
        "d_p_mm",
    )

    d_r_mm = _get_attr(
        planetary,
        "d_r_mm",
    )

    center_distance_mm = (
        _get_attr(
            planetary,
            "center_distance_mm",
            "a_mm",
        )
    )

    # ========================================================
    # 2. MOTOR COMPATIBILITY
    # ========================================================

    motor_entry = (
        catalogues.motors[
            seed.motor_key
        ]
    )

    motor_spec = (
        motor_to_spec(
            motor_entry
        )
    )

    motor_input = (
        MotorCompatibilityInput(

            ratio=ratio,

            n_s_rpm=n_s_rpm,

            T_s_design_nm=(
                T_s_design_nm
            ),

            z_r=z_r,

            module_mm=(
                seed.module_mm
            ),
        )
    )

    motor_result = (
        evaluate_motor_compatibility(

            motor_input,

            motor_spec,

            setup[
                "motor_constraints"
            ],
        )
    )

    if not _attach_or_reject(

        candidate,

        PipelineStage.MOTOR_COMPATIBILITY,

        motor_result,
    ):
        return candidate

    # ========================================================
    # 3. GEAR FORCES
    # ========================================================

    gear_force_input = (
        GearForceInput(

            T_s_nm=T_s_design_nm,

            T_c_nm=(
                setup[
                    "output_torque_nm"
                ]
            ),

            T_r_nm=T_r_ideal_nm,

            d_s_mm=d_s_mm,

            d_r_mm=d_r_mm,

            center_distance_mm=(
                center_distance_mm
            ),

            n_s_rpm=n_s_rpm,

            n_c_rpm=n_c_rpm,

            n_planets=(
                seed.n_planets
            ),
        )
    )

    gear_forces = (
        evaluate_gear_forces(

            gear_force_input,

            setup[
                "gear_force_config"
            ],
        )
    )

    if not _attach_or_reject(

        candidate,

        PipelineStage.GEAR_FORCES,

        gear_forces,
    ):
        return candidate

    # ========================================================
    # 4. GEAR GEOMETRY Y_J
    # ========================================================

    try:

        YJ = evaluate_planetary_yj(

            z_s=seed.z_s,

            z_p=seed.z_p,

            z_r=z_r,
        )

    except (
        ValueError,
        NotImplementedError,
    ) as exc:

        candidate.reject(

            PipelineStage.GEAR_GEOMETRY,

            "gear_geometry_unavailable:"
            + str(exc),
        )

        return candidate

    candidate.attach_result(

        PipelineStage.GEAR_GEOMETRY,

        YJ,
    )

    geometry = (
        GearGeometryFactors(

            YJ_sun_sp=(
                YJ.YJ_sun_sp
            ),

            YJ_planet_sp=(
                YJ.YJ_planet_sp
            ),

            YJ_planet_pr=(
                YJ.YJ_planet_pr
            ),

            YJ_ring_pr=(
                YJ.YJ_ring_pr
            ),
        )
    )

    # ========================================================
    # 5. GEAR STRENGTH
    # ========================================================

    gear_strength_input = (
        GearStrengthInput(

            z_s=seed.z_s,

            z_p=seed.z_p,

            z_r=z_r,

            module_mm=(
                seed.module_mm
            ),

            face_width_mm=(
                seed.face_width_mm
            ),

            d_s_mm=d_s_mm,

            d_p_mm=d_p_mm,

            pressure_angle_deg=(
                setup[
                    "gear_force_config"
                ].pressure_angle_deg
            ),

            F_t_sp_N=(
                _get_attr(
                    gear_forces,
                    "F_t_N",
                    "F_t_sp_N",
                )
            ),

            F_t_pr_N=(
                _get_attr(
                    gear_forces,
                    "F_t_ring_N",
                    "F_t_pr_N",
                )
            ),

            velocity_sp_mps=(
                _get_attr(
                    gear_forces,
                    "relative_pitch_velocity_mps",
                    "velocity_sp_mps",
                )
            ),

            velocity_pr_mps=(
                _get_attr(
                    gear_forces,
                    "ring_pitch_velocity_mps",
                    "velocity_pr_mps",
                )
            ),
        )
    )

    gear_strength = (
        evaluate_gear_strength(

            gear_strength_input,

            geometry,

            setup[
                "sun_gear_material"
            ],

            setup[
                "planet_gear_material"
            ],

            setup[
                "ring_gear_material"
            ],

            setup[
                "gear_strength_config"
            ],
        )
    )

    if not _attach_or_reject(

        candidate,

        PipelineStage.GEAR_STRENGTH,

        gear_strength,
    ):
        return candidate

    # ========================================================
    # 6. SUN SHAFT
    # ========================================================

    T_max_nm = abs(
        T_s_design_nm
    )

    T_min_nm = (

        setup[
            "torque_cycle_ratio"
        ]

        *
        T_max_nm
    )

    sun_shaft_input = (
        SunShaftInput(

            T_max_nm=T_max_nm,

            T_min_nm=T_min_nm,

            module_mm=(
                seed.module_mm
            ),

            z_s=seed.z_s,
        )
    )

    sun_shaft = (
        evaluate_sun_shaft(

            sun_shaft_input,

            setup[
                "sun_shaft_material"
            ],

            setup[
                "sun_shaft_config"
            ],
        )
    )

    if not _attach_or_reject(

        candidate,

        PipelineStage.SUN_SHAFT,

        sun_shaft,
    ):
        return candidate

    d_sun_shaft_mm = (
        _get_attr(
            sun_shaft,
            "d_required_mm",
        )
    )

    # ========================================================
    # 7. ROTOR SUPPORT + BALL-BEARING SELECTION
    # ========================================================

    def rotor_bearing_evaluator(
        bearing_A_entry,
        bearing_B_entry,
    ):

        bearing_A = (
            bearing_to_rotor_support_spec(
                bearing_A_entry
            )
        )

        bearing_B = (
            bearing_to_rotor_support_spec(
                bearing_B_entry
            )
        )

        rotor_input = (
            RotorSupportInput(

                T_s_nm=(
                    T_s_design_nm
                ),

                d_shaft_mm=(
                    d_sun_shaft_mm
                ),

                n_s_rpm=n_s_rpm,

                rotor_outer_diameter_mm=(
                    motor_entry.outer_diameter_mm
                ),

                supported_rotating_mass_kg=(
                    setup[
                        "supported_rotating_mass_kg"
                    ]
                ),

                bearing_spacing_mm=(
                    setup[
                        "rotor_bearing_spacing_mm"
                    ]
                ),

                cg_position_mm=(
                    setup[
                        "rotor_cg_position_mm"
                    ]
                ),
            )
        )

        return evaluate_rotor_support(

            rotor_input,

            setup[
                "rotor_support_material"
            ],

            bearing_A,

            bearing_B,

            setup[
                "rotor_support_config"
            ],
        )

    rotor_selection = (
        select_rotor_support_bearing_pair(

            catalogues.bearings.values(),

            rotor_bearing_evaluator,

            require_same_bore=True,
        )
    )

    if not rotor_selection.feasible:

        candidate.reject(

            PipelineStage.ROTOR_SUPPORT,

            rotor_selection.rejection_reason
            or
            "no_feasible_rotor_support_bearings",
        )

        return candidate

    candidate.attach_result(

        PipelineStage.ROTOR_SUPPORT,

        rotor_selection.engineering_result,
    )

    # ========================================================
    # 8. PLANET PIN + NEEDLE-BEARING SELECTION
    # ========================================================

    F_pin_design_N = (
        _get_attr(
            gear_forces,
            "F_pin_design_N",
        )
    )

    def planet_bearing_evaluator(
        bearing_entry,
    ):

        bearing = (
            bearing_to_needle_spec(
                bearing_entry
            )
        )

        values = {

            "F_pin_N":
                F_pin_design_N,

            "F_pin_design_N":
                F_pin_design_N,

            "face_width_mm":
                seed.face_width_mm,

            "module_mm":
                seed.module_mm,

            "z_p":
                seed.z_p,

            "n_p_rpm":
                n_p_rpm,

            "n_planet_rpm":
                n_p_rpm,

            "n_c_rpm":
                n_c_rpm,

            "n_carrier_rpm":
                n_c_rpm,
        }

        pin_input = (
            _build_dataclass(
                PlanetPinBearingInput,
                values,
            )
        )

        return (
            evaluate_planet_pin_bearing(

                pin_input,

                setup[
                    "pin_material"
                ],

                bearing,

                setup[
                    "planet_pin_config"
                ],
            )
        )

    planet_selection = (
        select_planet_bearing(

            catalogues.bearings.values(),

            planet_bearing_evaluator,
        )
    )

    if not planet_selection.feasible:

        candidate.reject(

            PipelineStage.PLANET_PIN_BEARING,

            planet_selection.rejection_reason
            or
            "no_feasible_planet_bearing",
        )

        return candidate

    candidate.attach_result(

        PipelineStage.PLANET_PIN_BEARING,

        planet_selection.engineering_result,
    )

    d_pin_mm = (
        planet_selection
        .bearing
        .bore_mm
    )

    # ========================================================
    # 9. OUTPUT SHAFT + BALL-BEARING SELECTION
    # ========================================================

    def output_bearing_evaluator(
        bearing_A_entry,
        bearing_B_entry,
    ):

        bearing_A = (
            bearing_to_output_spec(
                bearing_A_entry
            )
        )

        bearing_B = (
            bearing_to_output_spec(
                bearing_B_entry
            )
        )

        values = {

            "T_c_nm":
                setup[
                    "output_torque_nm"
                ],

            "output_torque_nm":
                setup[
                    "output_torque_nm"
                ],

            "external_radial_load_N":
                setup[
                    "joint_radial_load_N"
                ],

            "n_c_rpm":
                n_c_rpm,

            "output_speed_rpm":
                n_c_rpm,
        }
        output_input = (
            _build_dataclass(
                OutputSystemInput,
                values,
            )
        )

        return evaluate_output_system(

            output_input,

            setup[
                "output_material"
            ],

            bearing_A,

            bearing_B,

            setup[
                "output_system_config"
            ],
        )

    output_selection = (
        select_output_bearing_pair(

            catalogues.bearings.values(),

            output_bearing_evaluator,
        )
    )

    if not output_selection.feasible:

        candidate.reject(

            PipelineStage.OUTPUT_SYSTEM,

            output_selection.rejection_reason
            or
            "no_feasible_output_bearings",
        )

        return candidate

    candidate.attach_result(

        PipelineStage.OUTPUT_SYSTEM,

        output_selection.engineering_result,
    )

    # Current architecture:
    # output shaft bearing seat diameter = selected common bore.

    d_output_mm = (
        output_selection
        .pair
        .bearing_A
        .bore_mm
    )

    # ========================================================
    # 10. CARRIER
    # ========================================================

    carrier_values = {

        "F_pin_N":
            F_pin_design_N,

        "F_pin_design_N":
            F_pin_design_N,

        "pin_diameter_mm":
            d_pin_mm,

        "center_distance_mm":
            center_distance_mm,

        "a_mm":
            center_distance_mm,

        "T_c_nm":
            setup[
                "output_torque_nm"
            ],

        "output_torque_nm":
            setup[
                "output_torque_nm"
            ],

        "output_shaft_diameter_mm":
            d_output_mm,
    }

    carrier_input = (
        _build_dataclass(
            CarrierInput,
            carrier_values,
        )
    )

    carrier = (
        evaluate_carrier(

            carrier_input,

            setup[
                "carrier_material"
            ],

            setup[
                "carrier_config"
            ],
        )
    )

    if not _attach_or_reject(

        candidate,

        PipelineStage.CARRIER,

        carrier,
    ):
        return candidate

    # ========================================================
    # 11. RING
    # ========================================================

    ring_input = (
        RingInput(

            z_r=z_r,

            module_mm=(
                seed.module_mm
            ),

            T_r_nm=T_r_ideal_nm,

            stator_id_min_mm=(
                motor_entry
                .stator_id_min_mm
            ),
        )
    )

    ring = evaluate_ring(

        ring_input,

        setup[
            "ring_material"
        ],

        setup[
            "ring_config"
        ],
    )

    if not _attach_or_reject(

        candidate,

        PipelineStage.RING,

        ring,
    ):
        return candidate

    # ========================================================
    # COMPLETE
    # ========================================================

    candidate.mark_feasible()

    return candidate


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "\n"
        + "=" * 76
    )

    print(
        "ISSPG QDD ACTUATOR FEASIBILITY SWEEP"
    )

    print(
        "=" * 76
    )

    # ========================================================
    # LOAD PROJECT DATA
    # ========================================================

    config = load_config()

    catalogues = (
        load_catalogues()
    )

    setup = build_pipeline_setup(

        config,

        catalogues,
    )

    # ========================================================
    # SEARCH SIZE
    # ========================================================

    raw_candidate_count = (
        count_candidate_seeds(

            config,

            catalogues.motors,
        )
    )

    print(
        f"Raw search-space candidates: "
        f"{raw_candidate_count}"
    )

    print(
        f"Motors in catalogue:         "
        f"{len(catalogues.motors)}"
    )

    print(
        f"Bearings in catalogue:       "
        f"{len(catalogues.bearings)}"
    )

    print(
        f"Materials in catalogue:      "
        f"{len(catalogues.materials)}"
    )

    print(
        "=" * 76
    )

    # ========================================================
    # RUN ALL CANDIDATES
    # ========================================================

    candidates = []

    progress_every = int(
        config.get(
            "runtime.progress_every",
            1000,
        )
    )

    for index, seed in enumerate(

        generate_candidate_seeds(

            config,

            catalogues.motors,
        ),

        start=1,
    ):

        candidate = Candidate(
            seed
        )

        run_candidate_pipeline(

            candidate,

            setup,

            catalogues,
        )

        candidates.append(
            candidate
        )

        if (
            progress_every > 0
            and
            index % progress_every == 0
        ):

            print(
                f"Processed "
                f"{index}/"
                f"{raw_candidate_count}"
                f" candidates..."
            )

    # ========================================================
    # REPORT
    # ========================================================

    write_reports(

        candidates,

        output_directory="output",

        print_terminal_summary=True,
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()