"""
EXTERNAL SPUR-GEAR BENDING GEOMETRY FACTOR Y_J

Purpose:
    Approximate the AGMA bending geometry factor Y_J for an
    EXTERNAL spur-gear mesh using a digitized lookup table from
    Shigley Mechanical Engineering Design, Figure 14-6.

Source basis:
    User-supplied Shigley Figure 14-6:
        "Spur-gear geometry factors Y_J"

IMPORTANT:
    - Values are approximate readings from the chart.
    - Intended for design-space filtering and preliminary sizing.
    - NOT a replacement for a final AGMA 908 geometry calculation.
    - This LUT applies ONLY to EXTERNAL gear meshes.
    - Do NOT use it for the internal planet-ring mesh.

INPUTS
------
    gear_teeth:
        Number of teeth on the gear for which Y_J is desired.

    mating_teeth:
        Number of teeth on the mating EXTERNAL gear.

OUTPUT
------
    Approximate Y_J [-]

INTERPOLATION
-------------
    - Exact LUT node -> exact stored value.
    - Between nodes -> bilinear interpolation.
    - Tooth-count interpolation is performed in log(tooth count)
      because the source chart uses a logarithmic tooth-count axis.
    - No extrapolation is permitted.

VALID RANGE
-----------
    17 <= gear_teeth <= 275
    17 <= mating_teeth <= 1000

EXAMPLE
-------
    Sun:
        YJ_sun = lookup_external_yj(
            gear_teeth=z_s,
            mating_teeth=z_p,
        )

    Planet:
        YJ_planet = lookup_external_yj(
            gear_teeth=z_p,
            mating_teeth=z_s,
        )

    These values are generally NOT equal.
"""

from dataclasses import dataclass
from math import log
from typing import Tuple


@dataclass(frozen=True)
class PlanetaryYJResult:

    YJ_sun_sp: float
    YJ_planet_sp: float

    YJ_planet_pr: float
    YJ_ring_pr: float


# ============================================================
# DIGITIZED CHART AXES
# ============================================================

GEAR_TEETH_AXIS = (
    17,
    20,
    24,
    30,
    35,
    40,
    50,
    60,
    80,
    125,
    275,
)

MATING_TEETH_AXIS = (
    17,
    25,
    35,
    50,
    85,
    170,
    1000,
)


# ============================================================
# APPROXIMATE DIGITIZED Y_J TABLE
#
# Rows:
#     number of teeth in mating gear
#
# Columns:
#     GEAR_TEETH_AXIS
#
# Values are approximate readings from the supplied chart.
# ============================================================

YJ_EXTERNAL_LUT = {

    17: (
        0.294,
        0.311,
        0.329,
        0.351,
        0.364,
        0.376,
        0.396,
        0.411,
        0.430,
        0.451,
        0.474,
    ),

    25: (
        0.298,
        0.316,
        0.335,
        0.358,
        0.371,
        0.384,
        0.404,
        0.420,
        0.440,
        0.462,
        0.486,
    ),

    35: (
        0.302,
        0.321,
        0.341,
        0.364,
        0.378,
        0.391,
        0.412,
        0.428,
        0.448,
        0.472,
        0.497,
    ),

    50: (
        0.306,
        0.326,
        0.346,
        0.371,
        0.385,
        0.398,
        0.420,
        0.436,
        0.457,
        0.482,
        0.509,
    ),

    85: (
        0.309,
        0.331,
        0.352,
        0.377,
        0.392,
        0.405,
        0.427,
        0.444,
        0.466,
        0.493,
        0.521,
    ),

    170: (
        0.313,
        0.336,
        0.358,
        0.384,
        0.400,
        0.413,
        0.436,
        0.453,
        0.476,
        0.504,
        0.533,
    ),

    1000: (
        0.318,
        0.342,
        0.365,
        0.392,
        0.408,
        0.422,
        0.445,
        0.463,
        0.487,
        0.516,
        0.547,
    ),
}


# ============================================================
# RESULT FOR AN EXTERNAL MESH
# ============================================================

@dataclass(frozen=True)
class ExternalMeshYJResult:

    gear_1_teeth: int
    gear_2_teeth: int

    YJ_gear_1: float
    YJ_gear_2: float


# ============================================================
# BRACKETING HELPER
# ============================================================

def _find_bracket(
    value: float,
    axis: Tuple[int, ...],
) -> Tuple[int, int]:

    if value < axis[0] or value > axis[-1]:

        raise ValueError(
            f"Value {value} outside LUT range "
            f"[{axis[0]}, {axis[-1]}]."
        )

    # Exact node
    for i, node in enumerate(axis):

        if value == node:
            return i, i

    # Between nodes
    for i in range(len(axis) - 1):

        if axis[i] < value < axis[i + 1]:
            return i, i + 1

    raise RuntimeError(
        "Unable to bracket LUT value."
    )


def evaluate_planetary_yj(
    z_s: int,
    z_p: int,
    z_r: int,
    ring_yj_assumption: float = 0.25,
) -> PlanetaryYJResult:
    """
    Preliminary Y_J provider for the complete planetary gearset.

    Sun-planet:
        Uses digitized Shigley external spur-gear LUT.

    Planet-ring:
        Planet factor is conservatively approximated using the
        smaller of:
            - planet factor from the sun-planet mesh
            - external LUT value using ring tooth count as the
              approximate large mating gear

    Ring:
        Uses a conservative provisional fixed assumption.

    IMPORTANT:
        YJ_ring_pr is provisional and should later be validated
        using an internal-ring method or FEA.
    """

    if z_s <= 0 or z_p <= 0 or z_r <= 0:
        raise ValueError(
            "All planetary tooth counts must be > 0."
        )

    if z_r <= z_p:
        raise ValueError(
            "Internal ring must have more teeth than the planet."
        )

    if ring_yj_assumption <= 0:
        raise ValueError(
            "ring_yj_assumption must be > 0."
        )

    # ========================================================
    # 1. SUN — SUN/PLANET EXTERNAL MESH
    # ========================================================

    YJ_sun_sp = lookup_external_yj(
        gear_teeth=z_s,
        mating_teeth=z_p,
    )

    # ========================================================
    # 2. PLANET — SUN/PLANET EXTERNAL MESH
    # ========================================================

    YJ_planet_sp = lookup_external_yj(
        gear_teeth=z_p,
        mating_teeth=z_s,
    )

    # ========================================================
    # 3. PLANET — PLANET/RING PRELIMINARY APPROXIMATION
    #
    # Use ring tooth count as a large-mate approximation.
    #
    # Clamp only at upper mating-gear LUT limit.
    # ========================================================

    effective_ring_teeth = min(
        z_r,
        MATING_TEETH_AXIS[-1],
    )

    YJ_planet_large_mate = lookup_external_yj(
        gear_teeth=z_p,
        mating_teeth=effective_ring_teeth,
    )

    # Conservative choice:
    # never allow the ring-side approximation to make the
    # planet tooth appear stronger than its sun-side result.
    YJ_planet_pr = min(
        YJ_planet_sp,
        YJ_planet_large_mate,
    )

    # ========================================================
    # 4. INTERNAL RING — PROVISIONAL ASSUMPTION
    # ========================================================

    YJ_ring_pr = ring_yj_assumption

    return PlanetaryYJResult(
        YJ_sun_sp=YJ_sun_sp,
        YJ_planet_sp=YJ_planet_sp,
        YJ_planet_pr=YJ_planet_pr,
        YJ_ring_pr=YJ_ring_pr,
    )

# ============================================================
# LOG-SPACE INTERPOLATION
# ============================================================

def _interp_log(
    x: float,
    x0: float,
    x1: float,
    y0: float,
    y1: float,
) -> float:

    if x0 == x1:
        return y0

    fraction = (
        log(x) - log(x0)
    ) / (
        log(x1) - log(x0)
    )

    return (
        y0
        +
        fraction
        * (y1 - y0)
    )


# ============================================================
# MAIN LUT LOOKUP
# ============================================================

def lookup_external_yj(
    gear_teeth: int,
    mating_teeth: int,
) -> float:
    """
    Return approximate Y_J for one member of an EXTERNAL
    spur-gear mesh.

    gear_teeth:
        Teeth on the gear whose root bending factor is desired.

    mating_teeth:
        Teeth on its external mating gear.
    """

    if gear_teeth <= 0:
        raise ValueError(
            "gear_teeth must be > 0."
        )

    if mating_teeth <= 0:
        raise ValueError(
            "mating_teeth must be > 0."
        )

    # --------------------------------------------------------
    # 1. Locate requested gear tooth count
    # --------------------------------------------------------

    g0_i, g1_i = _find_bracket(
        gear_teeth,
        GEAR_TEETH_AXIS,
    )

    # --------------------------------------------------------
    # 2. Locate mating gear tooth count
    # --------------------------------------------------------

    m0_i, m1_i = _find_bracket(
        mating_teeth,
        MATING_TEETH_AXIS,
    )

    g0 = GEAR_TEETH_AXIS[g0_i]
    g1 = GEAR_TEETH_AXIS[g1_i]

    m0 = MATING_TEETH_AXIS[m0_i]
    m1 = MATING_TEETH_AXIS[m1_i]

    # --------------------------------------------------------
    # 3. Interpolate along desired-gear tooth axis
    #    on lower mating-gear curve
    # --------------------------------------------------------

    y_m0 = _interp_log(
        gear_teeth,
        g0,
        g1,
        YJ_EXTERNAL_LUT[m0][g0_i],
        YJ_EXTERNAL_LUT[m0][g1_i],
    )

    # --------------------------------------------------------
    # 4. Same interpolation on upper mating-gear curve
    # --------------------------------------------------------

    y_m1 = _interp_log(
        gear_teeth,
        g0,
        g1,
        YJ_EXTERNAL_LUT[m1][g0_i],
        YJ_EXTERNAL_LUT[m1][g1_i],
    )

    # --------------------------------------------------------
    # 5. Interpolate between mating-gear curves
    # --------------------------------------------------------

    YJ = _interp_log(
        mating_teeth,
        m0,
        m1,
        y_m0,
        y_m1,
    )

    return YJ


# ============================================================
# EXTERNAL MESH PAIR
# ============================================================

def evaluate_external_mesh_yj(
    gear_1_teeth: int,
    gear_2_teeth: int,
) -> ExternalMeshYJResult:
    """
    Calculate Y_J for BOTH members of one external mesh.

    Important:
        YJ_gear_1 != YJ_gear_2 in general.
    """

    YJ_1 = lookup_external_yj(
        gear_teeth=gear_1_teeth,
        mating_teeth=gear_2_teeth,
    )

    YJ_2 = lookup_external_yj(
        gear_teeth=gear_2_teeth,
        mating_teeth=gear_1_teeth,
    )

    return ExternalMeshYJResult(
        gear_1_teeth=gear_1_teeth,
        gear_2_teeth=gear_2_teeth,

        YJ_gear_1=YJ_1,
        YJ_gear_2=YJ_2,
    )


# ============================================================
# INTERNAL-MESH GUARD
# ============================================================

def lookup_internal_yj(
    gear_teeth: int,
    internal_ring_teeth: int,
) -> float:
    """
    Intentionally unsupported.

    The Shigley Figure 14-6 LUT implemented above is for
    external spur gears and must not be reused for an
    internal ring mesh.
    """

    raise NotImplementedError(
        "Internal planet-ring Y_J is not available from the "
        "external-gear Shigley Figure 14-6 LUT. "
        "Use a validated internal-gear AGMA method."
    )