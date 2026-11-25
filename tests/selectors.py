"""
Standalone tests for src/selectors.py

Run from project root:

    python -m tests.selectors
"""

from dataclasses import dataclass

from src.catalogue_loader import (
    BearingCatalogueEntry,
)

from src.selectors import (
    ball_bearings,
    needle_bearings,
    sort_bearings,
    prefilter_bearings,
    generate_bearing_pairs,
    select_first_feasible_bearing,
    select_planet_bearing,
    select_output_bearing_pair,
)


# ============================================================
# DUMMY ENGINEERING RESULT
# ============================================================

@dataclass
class DummyResult:

    feasible: bool

    rejection_reason: str | None

    score: float = 0.0


# ============================================================
# TEST BEARING CATALOGUE
# ============================================================

BEARINGS = [

    BearingCatalogueEntry(
        designation="BALL_10_LIGHT",
        type="deep_groove_ball",
        has_inner_ring=False,
        bore_mm=10.0,
        outer_diameter_mm=26.0,
        width_mm=8.0,
        C_N=5000.0,
        C0_N=2500.0,
        limiting_speed_rpm=20000.0,
        mass_kg=0.020,
    ),

    BearingCatalogueEntry(
        designation="BALL_10_HEAVY",
        type="deep_groove_ball",
        has_inner_ring=False,
        bore_mm=10.0,
        outer_diameter_mm=30.0,
        width_mm=9.0,
        C_N=8000.0,
        C0_N=4000.0,
        limiting_speed_rpm=18000.0,
        mass_kg=0.030,
    ),

    BearingCatalogueEntry(
        designation="BALL_12",
        type="deep_groove_ball",
        has_inner_ring=False,
        bore_mm=12.0,
        outer_diameter_mm=32.0,
        width_mm=10.0,
        C_N=9000.0,
        C0_N=5000.0,
        limiting_speed_rpm=16000.0,
        mass_kg=0.040,
    ),

    BearingCatalogueEntry(
        designation="NEEDLE_06",
        type="needle_with_inner_ring",
        has_inner_ring=True,
        bore_mm=6.0,
        outer_diameter_mm=16.0,
        width_mm=10.0,
        C_N=4000.0,
        C0_N=5000.0,
        limiting_speed_rpm=20000.0,
        mass_kg=0.012,
    ),

    BearingCatalogueEntry(
        designation="NEEDLE_08",
        type="needle_with_inner_ring",
        has_inner_ring=True,
        bore_mm=8.0,
        outer_diameter_mm=18.0,
        width_mm=12.0,
        C_N=6000.0,
        C0_N=7500.0,
        limiting_speed_rpm=18000.0,
        mass_kg=0.018,
    ),

    BearingCatalogueEntry(
        designation="NEEDLE_10",
        type="needle_with_inner_ring",
        has_inner_ring=True,
        bore_mm=10.0,
        outer_diameter_mm=20.0,
        width_mm=12.0,
        C_N=8000.0,
        C0_N=10000.0,
        limiting_speed_rpm=16000.0,
        mass_kg=0.025,
    ),
]


# ============================================================
# TEST 1 — TYPE FILTERING
# ============================================================

def test_type_filtering():

    balls = ball_bearings(
        BEARINGS
    )

    needles = needle_bearings(
        BEARINGS
    )

    assert len(balls) == 3
    assert len(needles) == 3

    assert all(
        bearing.type
        ==
        "deep_groove_ball"
        for bearing in balls
    )

    assert all(
        bearing.type
        ==
        "needle_with_inner_ring"
        for bearing in needles
    )

    print("\n" + "=" * 76)
    print("TEST 1 — TYPE FILTERING")
    print("=" * 76)

    print(
        f"Ball bearings:   {len(balls)}"
    )

    print(
        f"Needle bearings: {len(needles)}"
    )

    print(
        "\nPASS: bearing types filtered correctly."
    )


# ============================================================
# TEST 2 — SORTING
# ============================================================

def test_sorting():

    ordered = sort_bearings(
        reversed(BEARINGS)
    )

    bores = [
        bearing.bore_mm
        for bearing in ordered
    ]

    assert bores == sorted(
        bores
    )

    print("\n" + "=" * 76)
    print("TEST 2 — SORTING")
    print("=" * 76)

    for bearing in ordered:

        print(
            f"{bearing.designation}: "
            f"{bearing.bore_mm:.1f} mm"
        )

    print(
        "\nPASS: bearings sorted from smallest upward."
    )


# ============================================================
# TEST 3 — PREFILTER
# ============================================================

def test_prefilter():

    result = prefilter_bearings(
        needle_bearings(
            BEARINGS
        ),
        min_bore_mm=8.0,
        max_outer_diameter_mm=19.0,
    )

    assert len(result) == 1

    assert (
        result[0].designation
        ==
        "NEEDLE_08"
    )

    print("\n" + "=" * 76)
    print("TEST 3 — PREFILTER")
    print("=" * 76)

    print(
        f"Remaining bearing: "
        f"{result[0].designation}"
    )

    print(
        "\nPASS: geometric prefilter works."
    )


# ============================================================
# TEST 4 — SINGLE-BEARING SELECTION
# ============================================================

def test_single_selection():

    needles = needle_bearings(
        BEARINGS
    )

    def evaluator(
        bearing,
    ):

        # Synthetic requirement:
        # minimum bore = 8 mm.

        if bearing.bore_mm < 8.0:

            return DummyResult(
                feasible=False,
                rejection_reason="pin_too_small",
            )

        return DummyResult(
            feasible=True,
            rejection_reason=None,
            score=bearing.bore_mm,
        )

    selection = (
        select_first_feasible_bearing(
            needles,
            evaluator,
        )
    )

    assert selection.feasible

    assert (
        selection.bearing.designation
        ==
        "NEEDLE_08"
    )

    assert selection.attempts == 2

    print("\n" + "=" * 76)
    print("TEST 4 — SINGLE SELECTION")
    print("=" * 76)

    print(
        f"Selected: "
        f"{selection.bearing.designation}"
    )

    print(
        f"Attempts: "
        f"{selection.attempts}"
    )

    print(
        "\nPASS: first feasible bearing selected."
    )


# ============================================================
# TEST 5 — PLANET SELECTOR USES NEEDLE ONLY
# ============================================================

def test_planet_selector():

    def evaluator(
        bearing,
    ):

        return DummyResult(
            feasible=(
                bearing.bore_mm >= 8.0
            ),
            rejection_reason=(
                None
                if bearing.bore_mm >= 8.0
                else "too_small"
            ),
        )

    selection = (
        select_planet_bearing(
            BEARINGS,
            evaluator,
        )
    )

    assert selection.feasible

    assert (
        selection.bearing.type
        ==
        "needle_with_inner_ring"
    )

    assert (
        selection.bearing.designation
        ==
        "NEEDLE_08"
    )

    print("\n" + "=" * 76)
    print("TEST 5 — PLANET SELECTOR")
    print("=" * 76)

    print(
        f"Selected: "
        f"{selection.bearing.designation}"
    )

    print(
        "\nPASS: planet selector searches needle bearings only."
    )


# ============================================================
# TEST 6 — SAME-BORE PAIR GENERATION
# ============================================================

def test_same_bore_pairs():

    balls = ball_bearings(
        BEARINGS
    )

    pairs = generate_bearing_pairs(
        balls,
        require_same_bore=True,
    )

    assert len(pairs) == 5

    for pair in pairs:

        assert (
            pair.bearing_A.bore_mm
            ==
            pair.bearing_B.bore_mm
        )

    print("\n" + "=" * 76)
    print("TEST 6 — SAME-BORE PAIRS")
    print("=" * 76)

    print(
        f"Generated pairs: "
        f"{len(pairs)}"
    )

    print(
        "\nPASS: only common-bore pairs generated."
    )


# ============================================================
# TEST 7 — OUTPUT PAIR SELECTION
# ============================================================

def test_output_pair_selection():

    def evaluator(
        bearing_A,
        bearing_B,
    ):

        # Synthetic example:
        #
        # A needs C >= 4500 N
        # B needs C >= 7000 N

        feasible = (
            bearing_A.C_N >= 4500.0
            and
            bearing_B.C_N >= 7000.0
        )

        return DummyResult(
            feasible=feasible,
            rejection_reason=(
                None
                if feasible
                else "capacity_failure"
            ),
        )

    selection = (
        select_output_bearing_pair(
            BEARINGS,
            evaluator,
        )
    )

    assert selection.feasible

    assert (
        selection.pair.bearing_A.bore_mm
        ==
        selection.pair.bearing_B.bore_mm
    )

    assert (
        selection.pair.bearing_A.designation
        ==
        "BALL_10_LIGHT"
    )

    assert (
        selection.pair.bearing_B.designation
        ==
        "BALL_10_HEAVY"
    )

    print("\n" + "=" * 76)
    print("TEST 7 — OUTPUT PAIR SELECTION")
    print("=" * 76)

    print(
        f"Bearing A: "
        f"{selection.pair.bearing_A.designation}"
    )

    print(
        f"Bearing B: "
        f"{selection.pair.bearing_B.designation}"
    )

    print(
        f"Common bore: "
        f"{selection.pair.bearing_A.bore_mm:.1f} mm"
    )

    print(
        "\nPASS: smallest feasible ordered pair selected."
    )


# ============================================================
# TEST 8 — NO FEASIBLE BEARING
# ============================================================

def test_no_feasible_bearing():

    def evaluator(
        bearing,
    ):

        return DummyResult(
            feasible=False,
            rejection_reason="always_fail",
        )

    selection = (
        select_planet_bearing(
            BEARINGS,
            evaluator,
        )
    )

    assert not selection.feasible

    assert selection.bearing is None

    assert (
        selection.rejection_reason
        ==
        "no_feasible_bearing:always_fail"
    )

    print("\n" + "=" * 76)
    print("TEST 8 — NO FEASIBLE BEARING")
    print("=" * 76)

    print(
        f"Attempts: "
        f"{selection.attempts}"
    )

    print(
        f"Reason: "
        f"{selection.rejection_reason}"
    )

    print(
        "\nPASS: complete catalogue failure handled."
    )


# ============================================================
# TEST 9 — EMPTY CATALOGUE
# ============================================================

def test_empty_catalogue():

    def evaluator(
        bearing,
    ):

        raise AssertionError(
            "Evaluator should not be called."
        )

    selection = (
        select_first_feasible_bearing(
            [],
            evaluator,
        )
    )

    assert not selection.feasible

    assert selection.attempts == 0

    assert (
        selection.rejection_reason
        ==
        "no_candidate_bearings"
    )

    print("\n" + "=" * 76)
    print("TEST 9 — EMPTY CATALOGUE")
    print("=" * 76)

    print(
        "\nPASS: empty catalogue handled correctly."
    )


# ============================================================
# RUN ALL TESTS
# ============================================================

if __name__ == "__main__":

    test_type_filtering()
    test_sorting()
    test_prefilter()
    test_single_selection()
    test_planet_selector()
    test_same_bore_pairs()
    test_output_pair_selection()
    test_no_feasible_bearing()
    test_empty_catalogue()

    print("\n" + "=" * 76)
    print("ALL SELECTOR TESTS PASSED")
    print("=" * 76)