"""
CENTRAL PIPELINE DATA MODELS

Purpose:
    Define the shared candidate/state structures used by main.py.

A Candidate represents ONE complete design attempt:

    motor
    + Z_s
    + Z_p
    + N_planets
    + module
    + face width

The candidate is passed sequentially through:

    planetary
    -> motor compatibility
    -> gear forces
    -> gear geometry
    -> gear strength
    -> sun shaft
    -> rotor support
    -> planet pin/bearing
    -> output system
    -> carrier
    -> ring

This module performs NO engineering calculations.

RESPONSIBILITIES
----------------
    - Store fundamental search variables.
    - Generate deterministic candidate IDs.
    - Store each module result.
    - Track pipeline status:
          pending
          rejected
          feasible
    - Store exact rejection stage and reason.
    - Prevent accidental double rejection.
    - Provide flattened dictionaries for later CSV reporting.

IMPORTANT
---------
    Result classes are imported only for type checking.

    This avoids coupling the engineering modules back to models.py
    and prevents unnecessary circular imports.
"""

from __future__ import annotations

from dataclasses import (
    dataclass,
    field,
    fields,
    is_dataclass,
)
from enum import Enum
from typing import (
    Any,
    Optional,
    TYPE_CHECKING,
)


# ============================================================
# TYPE-ONLY IMPORTS
# ============================================================

if TYPE_CHECKING:

    from src.planetary import PlanetaryResult

    from src.motor_compatibility import (
        MotorCompatibilityResult,
    )

    from src.gear_forces import GearForceResult

    from src.gear_geometry import (
        PlanetaryYJResult,
    )

    from src.gear_strength import (
        GearStrengthResult,
    )

    from src.sun_shaft import (
        SunShaftResult,
    )

    from src.rotor_support import (
        RotorSupportResult,
    )

    from src.planet_pin_bearing import (
        PlanetPinBearingResult,
    )

    from src.output_system import (
        OutputSystemResult,
    )

    from src.carrier import (
        CarrierResult,
    )

    from src.ring import (
        RingResult,
    )


# ============================================================
# CANDIDATE STATUS
# ============================================================

class CandidateStatus(str, Enum):

    PENDING = "pending"

    REJECTED = "rejected"

    FEASIBLE = "feasible"


# ============================================================
# PIPELINE STAGES
# ============================================================

class PipelineStage(str, Enum):

    CANDIDATE_GENERATION = (
        "candidate_generation"
    )

    PLANETARY = (
        "planetary"
    )

    MOTOR_COMPATIBILITY = (
        "motor_compatibility"
    )

    GEAR_FORCES = (
        "gear_forces"
    )

    GEAR_GEOMETRY = (
        "gear_geometry"
    )

    GEAR_STRENGTH = (
        "gear_strength"
    )

    SUN_SHAFT = (
        "sun_shaft"
    )

    ROTOR_SUPPORT = (
        "rotor_support"
    )

    PLANET_PIN_BEARING = (
        "planet_pin_bearing"
    )

    OUTPUT_SYSTEM = (
        "output_system"
    )

    CARRIER = (
        "carrier"
    )

    RING = (
        "ring"
    )

    COMPLETE = (
        "complete"
    )


# ============================================================
# FUNDAMENTAL SEARCH VARIABLES
# ============================================================

@dataclass(frozen=True)
class CandidateSeed:
    """
    Fundamental variables that define one optimizer candidate.

    These are the variables explicitly iterated by the search.

    All other dimensions should be:
        - analytically derived, or
        - selected from a catalogue.
    """

    motor_key: str

    z_s: int
    z_p: int

    n_planets: int

    module_mm: float
    face_width_mm: float

    def __post_init__(self):

        if not self.motor_key.strip():
            raise ValueError(
                "motor_key cannot be empty."
            )

        if self.z_s <= 0:
            raise ValueError(
                "z_s must be > 0."
            )

        if self.z_p <= 0:
            raise ValueError(
                "z_p must be > 0."
            )

        if self.n_planets <= 0:
            raise ValueError(
                "n_planets must be > 0."
            )

        if self.module_mm <= 0:
            raise ValueError(
                "module_mm must be > 0."
            )

        if self.face_width_mm <= 0:
            raise ValueError(
                "face_width_mm must be > 0."
            )


# ============================================================
# MAIN CANDIDATE MODEL
# ============================================================

@dataclass
class Candidate:
    """
    Complete state of one design candidate.

    Engineering results are filled progressively by main.py.

    Once rejected, the candidate must not proceed through
    additional engineering stages.
    """

    seed: CandidateSeed

    # Automatically generated from the search variables.
    candidate_id: str = field(
        init=False
    )

    # Pipeline state
    status: CandidateStatus = (
        CandidateStatus.PENDING
    )

    last_completed_stage: Optional[
        PipelineStage
    ] = None

    rejected_stage: Optional[
        PipelineStage
    ] = None

    rejection_reason: Optional[str] = None

    # --------------------------------------------------------
    # Module results
    # --------------------------------------------------------

    planetary: Optional[
        PlanetaryResult
    ] = None

    motor_compatibility: Optional[
        MotorCompatibilityResult
    ] = None

    gear_forces: Optional[
        GearForceResult
    ] = None

    gear_geometry: Optional[
        PlanetaryYJResult
    ] = None

    gear_strength: Optional[
        GearStrengthResult
    ] = None

    sun_shaft: Optional[
        SunShaftResult
    ] = None

    rotor_support: Optional[
        RotorSupportResult
    ] = None

    planet_pin_bearing: Optional[
        PlanetPinBearingResult
    ] = None

    output_system: Optional[
        OutputSystemResult
    ] = None

    carrier: Optional[
        CarrierResult
    ] = None

    ring: Optional[
        RingResult
    ] = None

    # ========================================================
    # INITIALIZATION
    # ========================================================

    def __post_init__(self):

        self.candidate_id = (
            _make_candidate_id(
                self.seed
            )
        )

    # ========================================================
    # STATE PROPERTIES
    # ========================================================

    @property
    def is_pending(self) -> bool:

        return (
            self.status
            ==
            CandidateStatus.PENDING
        )

    @property
    def is_rejected(self) -> bool:

        return (
            self.status
            ==
            CandidateStatus.REJECTED
        )

    @property
    def is_feasible(self) -> bool:

        return (
            self.status
            ==
            CandidateStatus.FEASIBLE
        )

    # ========================================================
    # ATTACH MODULE RESULT
    # ========================================================

    def attach_result(
        self,
        stage: PipelineStage,
        result: Any,
    ) -> None:
        """
        Attach one module result to this candidate.

        Example:

            candidate.attach_result(
                PipelineStage.PLANETARY,
                planetary_result,
            )
        """

        if not self.is_pending:

            raise RuntimeError(
                f"Cannot attach result to candidate "
                f"'{self.candidate_id}' because status is "
                f"'{self.status.value}'."
            )

        result_field = (
            _STAGE_RESULT_FIELDS.get(
                stage
            )
        )

        if result_field is None:

            raise ValueError(
                f"Stage '{stage.value}' does not "
                f"have an attachable result field."
            )

        setattr(
            self,
            result_field,
            result,
        )

        self.last_completed_stage = (
            stage
        )

    # ========================================================
    # REJECT CANDIDATE
    # ========================================================

    def reject(
        self,
        stage: PipelineStage,
        reason: str,
    ) -> None:
        """
        Permanently reject a candidate.

        Only the FIRST rejection is retained.

        Calling reject again is treated as a pipeline logic error.
        """

        if not self.is_pending:

            raise RuntimeError(
                f"Candidate '{self.candidate_id}' "
                f"is already finalized with status "
                f"'{self.status.value}'."
            )

        if not reason.strip():

            raise ValueError(
                "Rejection reason cannot be empty."
            )

        self.status = (
            CandidateStatus.REJECTED
        )

        self.rejected_stage = (
            stage
        )

        self.rejection_reason = (
            reason
        )

    # ========================================================
    # MARK CANDIDATE FEASIBLE
    # ========================================================

    def mark_feasible(self) -> None:
        """
        Mark the candidate as having passed the complete pipeline.
        """

        if not self.is_pending:

            raise RuntimeError(
                f"Candidate '{self.candidate_id}' "
                f"is already finalized with status "
                f"'{self.status.value}'."
            )

        self.status = (
            CandidateStatus.FEASIBLE
        )

        self.last_completed_stage = (
            PipelineStage.COMPLETE
        )


# ============================================================
# STAGE -> CANDIDATE RESULT FIELD
# ============================================================

_STAGE_RESULT_FIELDS = {

    PipelineStage.PLANETARY:
        "planetary",

    PipelineStage.MOTOR_COMPATIBILITY:
        "motor_compatibility",

    PipelineStage.GEAR_FORCES:
        "gear_forces",

    PipelineStage.GEAR_GEOMETRY:
        "gear_geometry",

    PipelineStage.GEAR_STRENGTH:
        "gear_strength",

    PipelineStage.SUN_SHAFT:
        "sun_shaft",

    PipelineStage.ROTOR_SUPPORT:
        "rotor_support",

    PipelineStage.PLANET_PIN_BEARING:
        "planet_pin_bearing",

    PipelineStage.OUTPUT_SYSTEM:
        "output_system",

    PipelineStage.CARRIER:
        "carrier",

    PipelineStage.RING:
        "ring",
}


# ============================================================
# DETERMINISTIC CANDIDATE ID
# ============================================================

def _make_candidate_id(
    seed: CandidateSeed,
) -> str:
    """
    Generate a human-readable deterministic candidate ID.

    Example:

        RO80_KV105__Zs20__Zp40__Np4__m0p5__b10
    """

    module_text = (
        _number_for_id(
            seed.module_mm
        )
    )

    width_text = (
        _number_for_id(
            seed.face_width_mm
        )
    )

    return (
        f"{seed.motor_key}"
        f"__Zs{seed.z_s}"
        f"__Zp{seed.z_p}"
        f"__Np{seed.n_planets}"
        f"__m{module_text}"
        f"__b{width_text}"
    )


def _number_for_id(
    value: float,
) -> str:

    text = (
        f"{value:g}"
    )

    # Avoid decimal points in filenames / IDs.
    return text.replace(
        ".",
        "p",
    )


# ============================================================
# FLATTEN CANDIDATE FOR REPORTING
# ============================================================

def candidate_to_flat_dict(
    candidate: Candidate,
) -> dict:
    """
    Flatten a Candidate and all attached dataclass results into
    one dictionary suitable for later CSV reporting.

    Examples of generated keys:

        candidate_id
        seed_motor_key
        seed_z_s
        seed_module_mm

        planetary_ratio
        planetary_z_r

        gear_strength_S_F_governing

        output_system_actual_shaft_diameter_mm

        rejected_stage
        rejection_reason
    """

    output = {}

    _flatten_value(
        candidate,
        prefix="",
        output=output,
    )

    return output


# ============================================================
# RECURSIVE FLATTENER
# ============================================================

def _flatten_value(
    value: Any,
    prefix: str,
    output: dict,
) -> None:

    # --------------------------------------------------------
    # Dataclass
    # --------------------------------------------------------

    if is_dataclass(value):

        for item in fields(value):

            field_value = getattr(
                value,
                item.name,
            )

            field_prefix = (
                f"{prefix}_{item.name}"
                if prefix
                else item.name
            )

            _flatten_value(
                field_value,
                field_prefix,
                output,
            )

        return

    # --------------------------------------------------------
    # Enum
    # --------------------------------------------------------

    if isinstance(value, Enum):

        output[prefix] = (
            value.value
        )

        return

    # --------------------------------------------------------
    # Dictionaries
    # --------------------------------------------------------

    if isinstance(value, dict):

        for key, child in value.items():

            child_prefix = (
                f"{prefix}_{key}"
                if prefix
                else str(key)
            )

            _flatten_value(
                child,
                child_prefix,
                output,
            )

        return

    # --------------------------------------------------------
    # Lists / tuples
    # --------------------------------------------------------

    if isinstance(
        value,
        (list, tuple),
    ):

        output[prefix] = (
            str(value)
        )

        return

    # --------------------------------------------------------
    # Scalar / None
    # --------------------------------------------------------

    output[prefix] = value