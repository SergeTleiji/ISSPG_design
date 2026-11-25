"""
CATALOGUE SELECTION HELPERS

Purpose:
    Select the smallest feasible bearing or bearing pair from the
    loaded bearing catalogue.

This module DOES NOT perform bearing engineering calculations.

Instead:

    catalogue entries
        -> ordered by size
        -> passed to evaluator callback
        -> evaluator returns module result
        -> first feasible choice is selected

The evaluator callback is supplied later by main.py.

Typical use:
    Planet:
        needle bearing
        -> evaluate_planet_pin_bearing(...)

    Rotor support:
        ball-bearing pair
        -> evaluate_rotor_support(...)

    Output:
        same-bore ball-bearing pair
        -> evaluate_output_system(...)

INPUTS
------
    BearingCatalogueEntry objects from catalogue_loader.py

    evaluator callback:
        evaluator(bearing)
        or
        evaluator(bearing_A, bearing_B)

    The returned engineering result must contain:

        result.feasible
        result.rejection_reason

OUTPUTS
-------
    BearingSelectionOutcome
    BearingPairSelectionOutcome

IMPORTANT
---------
    "Smallest" is defined deterministically.

Single bearing priority:
    1. bore
    2. outer diameter
    3. width
    4. mass

Pair priority:
    1. maximum bore
    2. maximum outer diameter
    3. total axial width
    4. total mass

No engineering result is recomputed here.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import (
    Any,
    Callable,
    Iterable,
    Optional,
    Protocol,
)

from src.catalogue_loader import (
    BearingCatalogueEntry,
)


# ============================================================
# ENGINEERING RESULT PROTOCOL
# ============================================================

class FeasibilityResult(Protocol):
    """
    Minimum interface expected from an engineering evaluator.
    """

    feasible: bool

    rejection_reason: Optional[str]


# ============================================================
# SINGLE-BEARING SELECTION RESULT
# ============================================================

@dataclass(frozen=True)
class BearingSelectionOutcome:

    feasible: bool

    bearing: Optional[
        BearingCatalogueEntry
    ]

    engineering_result: Optional[Any]

    attempts: int

    rejection_reason: Optional[str]


# ============================================================
# BEARING PAIR
# ============================================================

@dataclass(frozen=True)
class BearingPair:

    bearing_A: BearingCatalogueEntry

    bearing_B: BearingCatalogueEntry


# ============================================================
# PAIR SELECTION RESULT
# ============================================================

@dataclass(frozen=True)
class BearingPairSelectionOutcome:

    feasible: bool

    pair: Optional[
        BearingPair
    ]

    engineering_result: Optional[Any]

    attempts: int

    rejection_reason: Optional[str]


# ============================================================
# BASIC BEARING FILTERS
# ============================================================

def ball_bearings(
    bearings: Iterable[
        BearingCatalogueEntry
    ],
) -> list[BearingCatalogueEntry]:
    """
    Return deep-groove ball bearings ordered by size.
    """

    selected = [

        bearing

        for bearing in bearings

        if bearing.type
        ==
        "deep_groove_ball"
    ]

    return sort_bearings(
        selected
    )


def needle_bearings(
    bearings: Iterable[
        BearingCatalogueEntry
    ],
) -> list[BearingCatalogueEntry]:
    """
    Return needle bearings with inner rings ordered by size.
    """

    selected = [

        bearing

        for bearing in bearings

        if (
            bearing.type
            ==
            "needle_with_inner_ring"

            and

            bearing.has_inner_ring
        )
    ]

    return sort_bearings(
        selected
    )


# ============================================================
# SINGLE-BEARING SORT
# ============================================================

def sort_bearings(
    bearings: Iterable[
        BearingCatalogueEntry
    ],
) -> list[BearingCatalogueEntry]:
    """
    Sort bearings from smallest to largest.

    Priority:
        bore
        OD
        width
        mass
        designation
    """

    return sorted(

        bearings,

        key=lambda bearing: (

            bearing.bore_mm,

            bearing.outer_diameter_mm,

            bearing.width_mm,

            bearing.mass_kg,

            bearing.designation,
        ),
    )


# ============================================================
# OPTIONAL GEOMETRIC PREFILTER
# ============================================================

def prefilter_bearings(
    bearings: Iterable[
        BearingCatalogueEntry
    ],
    *,
    min_bore_mm: Optional[float] = None,
    max_outer_diameter_mm: Optional[float] = None,
    max_width_mm: Optional[float] = None,
) -> list[BearingCatalogueEntry]:
    """
    Apply simple catalogue/geometric filters before running the
    complete engineering evaluator.

    These are NOT substitutes for engineering checks.

    They only avoid evaluating obviously impossible catalogue
    entries.
    """

    if (
        min_bore_mm is not None
        and min_bore_mm < 0
    ):
        raise ValueError(
            "min_bore_mm cannot be negative."
        )

    if (
        max_outer_diameter_mm is not None
        and max_outer_diameter_mm <= 0
    ):
        raise ValueError(
            "max_outer_diameter_mm must be > 0."
        )

    if (
        max_width_mm is not None
        and max_width_mm <= 0
    ):
        raise ValueError(
            "max_width_mm must be > 0."
        )

    result = []

    for bearing in bearings:

        if (
            min_bore_mm is not None
            and
            bearing.bore_mm
            <
            min_bore_mm
        ):
            continue

        if (
            max_outer_diameter_mm
            is not None
            and
            bearing.outer_diameter_mm
            >
            max_outer_diameter_mm
        ):
            continue

        if (
            max_width_mm is not None
            and
            bearing.width_mm
            >
            max_width_mm
        ):
            continue

        result.append(
            bearing
        )

    return sort_bearings(
        result
    )


# ============================================================
# SINGLE-BEARING SELECTOR
# ============================================================

def select_first_feasible_bearing(
    bearings: Iterable[
        BearingCatalogueEntry
    ],
    evaluator: Callable[
        [BearingCatalogueEntry],
        FeasibilityResult,
    ],
) -> BearingSelectionOutcome:
    """
    Evaluate bearings from smallest to largest and return the
    first feasible choice.

    The engineering evaluator is responsible for checks such as:

        static capacity
        dynamic life
        speed
        pin stress
        pin deflection
        packaging
        etc.
    """

    ordered = sort_bearings(
        bearings
    )

    if not ordered:

        return BearingSelectionOutcome(

            feasible=False,

            bearing=None,

            engineering_result=None,

            attempts=0,

            rejection_reason=(
                "no_candidate_bearings"
            ),
        )

    attempts = 0

    last_reason = None

    for bearing in ordered:

        attempts += 1

        result = evaluator(
            bearing
        )

        if not hasattr(
            result,
            "feasible",
        ):
            raise TypeError(
                "Bearing evaluator result must contain "
                "a 'feasible' attribute."
            )

        if result.feasible:

            return BearingSelectionOutcome(

                feasible=True,

                bearing=bearing,

                engineering_result=result,

                attempts=attempts,

                rejection_reason=None,
            )

        last_reason = getattr(
            result,
            "rejection_reason",
            None,
        )

    return BearingSelectionOutcome(

        feasible=False,

        bearing=None,

        engineering_result=None,

        attempts=attempts,

        rejection_reason=(
            "no_feasible_bearing"
            if last_reason is None
            else
            f"no_feasible_bearing:"
            f"{last_reason}"
        ),
    )


# ============================================================
# GENERATE BEARING PAIRS
# ============================================================

def generate_bearing_pairs(
    bearings: Iterable[
        BearingCatalogueEntry
    ],
    *,
    require_same_bore: bool,
) -> list[BearingPair]:
    """
    Generate ordered bearing pairs.

    Ordered pairs are deliberate.

    Bearing A and bearing B may carry different reactions, so:

        A = X, B = Y

    is not necessarily equivalent to:

        A = Y, B = X

    The same catalogue bearing may be used in both positions.
    """

    ordered = sort_bearings(
        bearings
    )

    pairs = []

    for bearing_A, bearing_B in product(
        ordered,
        repeat=2,
    ):

        if require_same_bore:

            if (
                bearing_A.bore_mm
                !=
                bearing_B.bore_mm
            ):
                continue

        pairs.append(

            BearingPair(

                bearing_A=bearing_A,

                bearing_B=bearing_B,
            )
        )

    return sort_bearing_pairs(
        pairs
    )


# ============================================================
# PAIR SORT
# ============================================================

def sort_bearing_pairs(
    pairs: Iterable[
        BearingPair
    ],
) -> list[BearingPair]:
    """
    Sort bearing pairs from smallest to largest.

    Priority:
        maximum bore
        maximum OD
        total width
        total mass
        designation A
        designation B
    """

    return sorted(

        pairs,

        key=lambda pair: (

            max(
                pair.bearing_A.bore_mm,
                pair.bearing_B.bore_mm,
            ),

            max(
                pair.bearing_A.outer_diameter_mm,
                pair.bearing_B.outer_diameter_mm,
            ),

            (
                pair.bearing_A.width_mm
                +
                pair.bearing_B.width_mm
            ),

            (
                pair.bearing_A.mass_kg
                +
                pair.bearing_B.mass_kg
            ),

            pair.bearing_A.designation,

            pair.bearing_B.designation,
        ),
    )


# ============================================================
# BEARING-PAIR SELECTOR
# ============================================================

def select_first_feasible_bearing_pair(
    bearings: Iterable[
        BearingCatalogueEntry
    ],
    evaluator: Callable[
        [
            BearingCatalogueEntry,
            BearingCatalogueEntry,
        ],
        FeasibilityResult,
    ],
    *,
    require_same_bore: bool,
) -> BearingPairSelectionOutcome:
    """
    Evaluate bearing pairs from smallest to largest and return the
    first feasible pair.

    Example:

        output shaft:
            require_same_bore=True

        rotor support:
            require_same_bore can be chosen later based on the
            shaft architecture.
    """

    pairs = generate_bearing_pairs(

        bearings,

        require_same_bore=(
            require_same_bore
        ),
    )

    if not pairs:

        return BearingPairSelectionOutcome(

            feasible=False,

            pair=None,

            engineering_result=None,

            attempts=0,

            rejection_reason=(
                "no_candidate_bearing_pairs"
            ),
        )

    attempts = 0

    last_reason = None

    for pair in pairs:

        attempts += 1

        result = evaluator(

            pair.bearing_A,

            pair.bearing_B,
        )

        if not hasattr(
            result,
            "feasible",
        ):
            raise TypeError(
                "Bearing-pair evaluator result must contain "
                "a 'feasible' attribute."
            )

        if result.feasible:

            return BearingPairSelectionOutcome(

                feasible=True,

                pair=pair,

                engineering_result=result,

                attempts=attempts,

                rejection_reason=None,
            )

        last_reason = getattr(
            result,
            "rejection_reason",
            None,
        )

    return BearingPairSelectionOutcome(

        feasible=False,

        pair=None,

        engineering_result=None,

        attempts=attempts,

        rejection_reason=(
            "no_feasible_bearing_pair"
            if last_reason is None
            else
            f"no_feasible_bearing_pair:"
            f"{last_reason}"
        ),
    )


# ============================================================
# PLANET NEEDLE-BEARING CONVENIENCE SELECTOR
# ============================================================

def select_planet_bearing(
    bearings: Iterable[
        BearingCatalogueEntry
    ],
    evaluator: Callable[
        [BearingCatalogueEntry],
        FeasibilityResult,
    ],
) -> BearingSelectionOutcome:
    """
    Select the smallest feasible needle bearing with inner ring.
    """

    candidates = needle_bearings(
        bearings
    )

    return select_first_feasible_bearing(

        candidates,

        evaluator,
    )


# ============================================================
# OUTPUT BEARING CONVENIENCE SELECTOR
# ============================================================

def select_output_bearing_pair(
    bearings: Iterable[
        BearingCatalogueEntry
    ],
    evaluator: Callable[
        [
            BearingCatalogueEntry,
            BearingCatalogueEntry,
        ],
        FeasibilityResult,
    ],
) -> BearingPairSelectionOutcome:
    """
    Select the smallest feasible deep-groove ball-bearing pair
    having a common bore.

    This matches the current output-system assumption.
    """

    candidates = ball_bearings(
        bearings
    )

    return select_first_feasible_bearing_pair(

        candidates,

        evaluator,

        require_same_bore=True,
    )


# ============================================================
# ROTOR SUPPORT CONVENIENCE SELECTOR
# ============================================================

def select_rotor_support_bearing_pair(
    bearings: Iterable[
        BearingCatalogueEntry
    ],
    evaluator: Callable[
        [
            BearingCatalogueEntry,
            BearingCatalogueEntry,
        ],
        FeasibilityResult,
    ],
    *,
    require_same_bore: bool = True,
) -> BearingPairSelectionOutcome:
    """
    Select the smallest feasible deep-groove ball-bearing pair
    for the rotor/sun support.

    Default:
        same bore for both bearings.

    This can be relaxed later if the final shaft CAD deliberately
    uses stepped bearing seats.
    """

    candidates = ball_bearings(
        bearings
    )

    return select_first_feasible_bearing_pair(

        candidates,

        evaluator,

        require_same_bore=(
            require_same_bore
        ),
    )