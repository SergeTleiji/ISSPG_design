"""
CANDIDATE GENERATOR

Purpose:
    Expand the configured design search space into CandidateSeed
    objects.

SEARCH VARIABLES
----------------
    motor
    z_s             sun tooth count
    z_p             planet tooth count
    n_planets       number of planets
    module_mm       gear module
    face_width_mm   gear face width

NO ENGINEERING CHECKS ARE PERFORMED HERE.

In particular, this module does NOT check:
    - ring tooth count
    - planetary ratio
    - assembly condition
    - planet clearance
    - motor compatibility
    - gear strength
    - bearing feasibility

Those checks belong to the downstream engineering modules.

OUTPUT
------
    Iterator[CandidateSeed]

The generator is lazy so large search spaces do not have to be
stored in memory before evaluation.
"""

from __future__ import annotations

from typing import (
    Dict,
    Iterable,
    Iterator,
)

from src.catalogue_loader import (
    MotorCatalogueEntry,
)

from src.config_loader import (
    ProjectConfig,
)

from src.models import (
    CandidateSeed,
)


# ============================================================
# EXCEPTION
# ============================================================

class CandidateGenerationError(
    ValueError
):
    """Raised for an invalid design search space."""


# ============================================================
# INTEGER RANGE HELPER
# ============================================================

def _inclusive_integer_range(
    minimum: int,
    maximum: int,
    step: int,
    name: str,
) -> list[int]:
    """
    Inclusive integer range.

    Example:
        min = 17
        max = 21
        step = 2

    returns:
        [17, 19, 21]
    """

    if minimum <= 0:

        raise CandidateGenerationError(
            f"{name}.min must be > 0."
        )

    if maximum < minimum:

        raise CandidateGenerationError(
            f"{name}.max must be >= "
            f"{name}.min."
        )

    if step <= 0:

        raise CandidateGenerationError(
            f"{name}.step must be > 0."
        )

    return list(
        range(
            minimum,
            maximum + 1,
            step,
        )
    )


# ============================================================
# LIST VALIDATION
# ============================================================

def _validate_positive_list(
    values: Iterable,
    name: str,
) -> list:
    """
    Validate a non-empty list of positive numerical values.

    Duplicate values are rejected because they would generate
    duplicate candidate IDs.
    """

    values = list(
        values
    )

    if not values:

        raise CandidateGenerationError(
            f"{name} cannot be empty."
        )

    for value in values:

        if isinstance(
            value,
            bool,
        ):

            raise CandidateGenerationError(
                f"{name} must contain "
                f"numeric values."
            )

        try:

            numeric = float(
                value
            )

        except (
            TypeError,
            ValueError,
        ) as exc:

            raise CandidateGenerationError(
                f"{name} must contain "
                f"numeric values."
            ) from exc

        if numeric <= 0:

            raise CandidateGenerationError(
                f"All values in {name} "
                f"must be > 0."
            )

    if (
        len(values)
        !=
        len(set(values))
    ):

        raise CandidateGenerationError(
            f"{name} contains duplicate values."
        )

    return values


# ============================================================
# MOTOR KEY SELECTION
# ============================================================

def _select_motor_keys(
    config: ProjectConfig,
    motors: Dict[
        str,
        MotorCatalogueEntry,
    ],
) -> list[str]:
    """
    Determine which motors participate in the search.

    If:
        planetary.search.motor_keys

    is absent, all catalogue motors are used.

    If provided, only those motors are used.
    """

    if not motors:

        raise CandidateGenerationError(
            "Motor catalogue is empty."
        )

    configured = config.get(
        "planetary.search.motor_keys"
    )

    if configured is None:

        # Sort for deterministic generation.
        return sorted(
            motors.keys()
        )

    if not isinstance(
        configured,
        list,
    ):

        raise CandidateGenerationError(
            "planetary.search.motor_keys "
            "must be a list."
        )

    if not configured:

        raise CandidateGenerationError(
            "planetary.search.motor_keys "
            "cannot be empty."
        )

    if (
        len(configured)
        !=
        len(set(configured))
    ):

        raise CandidateGenerationError(
            "planetary.search.motor_keys "
            "contains duplicates."
        )

    for motor_key in configured:

        if motor_key not in motors:

            raise CandidateGenerationError(
                f"Motor '{motor_key}' requested "
                f"in search configuration is "
                f"not present in the catalogue."
            )

    return list(
        configured
    )


# ============================================================
# READ SEARCH SPACE
# ============================================================

def get_search_space(
    config: ProjectConfig,
    motors: Dict[
        str,
        MotorCatalogueEntry,
    ],
) -> dict:
    """
    Read and validate all candidate-generation variables.

    Returns a dictionary containing explicit lists for every
    search dimension.
    """

    # --------------------------------------------------------
    # Motor choices
    # --------------------------------------------------------

    motor_keys = (
        _select_motor_keys(
            config,
            motors,
        )
    )

    # --------------------------------------------------------
    # Sun tooth count
    # --------------------------------------------------------

    z_s_values = (
        _inclusive_integer_range(

            minimum=config.require_int(
                "planetary.search."
                "sun_teeth.min",
                positive=True,
            ),

            maximum=config.require_int(
                "planetary.search."
                "sun_teeth.max",
                positive=True,
            ),

            step=config.require_int(
                "planetary.search."
                "sun_teeth.step",
                positive=True,
            ),

            name=(
                "planetary.search."
                "sun_teeth"
            ),
        )
    )

    # --------------------------------------------------------
    # Planet tooth count
    # --------------------------------------------------------

    z_p_values = (
        _inclusive_integer_range(

            minimum=config.require_int(
                "planetary.search."
                "planet_teeth.min",
                positive=True,
            ),

            maximum=config.require_int(
                "planetary.search."
                "planet_teeth.max",
                positive=True,
            ),

            step=config.require_int(
                "planetary.search."
                "planet_teeth.step",
                positive=True,
            ),

            name=(
                "planetary.search."
                "planet_teeth"
            ),
        )
    )

    # --------------------------------------------------------
    # Number of planets
    # --------------------------------------------------------

    n_planets_values = (
        _validate_positive_list(

            config.require_list(
                "planetary.search."
                "planet_counts"
            ),

            "planetary.search."
            "planet_counts",
        )
    )

    # Planet count must be integer.
    for value in n_planets_values:

        if int(value) != value:

            raise CandidateGenerationError(
                "planetary.search."
                "planet_counts must contain "
                "integers."
            )

    n_planets_values = [
        int(value)
        for value
        in n_planets_values
    ]

    # --------------------------------------------------------
    # Gear modules
    # --------------------------------------------------------

    module_values = (
        _validate_positive_list(

            config.require_list(
                "planetary.search."
                "modules_mm"
            ),

            "planetary.search."
            "modules_mm",
        )
    )

    module_values = [
        float(value)
        for value
        in module_values
    ]

    # --------------------------------------------------------
    # Face widths
    # --------------------------------------------------------

    face_width_values = (
        _validate_positive_list(

            config.require_list(
                "planetary.search."
                "face_widths_mm"
            ),

            "planetary.search."
            "face_widths_mm",
        )
    )

    face_width_values = [
        float(value)
        for value
        in face_width_values
    ]

    return {

        "motor_keys":
            motor_keys,

        "z_s_values":
            z_s_values,

        "z_p_values":
            z_p_values,

        "n_planets_values":
            n_planets_values,

        "module_values":
            module_values,

        "face_width_values":
            face_width_values,
    }


# ============================================================
# COUNT SEARCH SPACE
# ============================================================

def count_candidate_seeds(
    config: ProjectConfig,
    motors: Dict[
        str,
        MotorCatalogueEntry,
    ],
) -> int:
    """
    Return total raw Cartesian-product candidate count.

    This is BEFORE any engineering filtering.
    """

    search = get_search_space(
        config,
        motors,
    )

    return (
        len(search["motor_keys"])
        *
        len(search["z_s_values"])
        *
        len(search["z_p_values"])
        *
        len(search["n_planets_values"])
        *
        len(search["module_values"])
        *
        len(search["face_width_values"])
    )


# ============================================================
# GENERATE CANDIDATE SEEDS
# ============================================================

def generate_candidate_seeds(
    config: ProjectConfig,
    motors: Dict[
        str,
        MotorCatalogueEntry,
    ],
) -> Iterator[CandidateSeed]:
    """
    Lazily generate all CandidateSeed objects.

    Generation order:

        motor
        -> sun teeth
        -> planet teeth
        -> planet count
        -> module
        -> face width
    """

    search = get_search_space(
        config,
        motors,
    )

    for motor_key in (
        search[
            "motor_keys"
        ]
    ):

        for z_s in (
            search[
                "z_s_values"
            ]
        ):

            for z_p in (
                search[
                    "z_p_values"
                ]
            ):

                for n_planets in (
                    search[
                        "n_planets_values"
                    ]
                ):

                    for module_mm in (
                        search[
                            "module_values"
                        ]
                    ):

                        for face_width_mm in (
                            search[
                                "face_width_values"
                            ]
                        ):

                            yield CandidateSeed(

                                motor_key=(
                                    motor_key
                                ),

                                z_s=z_s,

                                z_p=z_p,

                                n_planets=(
                                    n_planets
                                ),

                                module_mm=(
                                    module_mm
                                ),

                                face_width_mm=(
                                    face_width_mm
                                ),
                            )