"""
Standalone tests for src/reporting.py

Run:

    python -m tests.reporting
"""

import csv

from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from src.models import (
    Candidate,
    CandidateSeed,
    PipelineStage,
)

from src.reporting import (
    split_candidates,
    summarize_candidates,
    write_candidate_csv,
    write_reports,
)


# ============================================================
# DUMMY RESULT
# ============================================================

@dataclass
class DummyResult:

    feasible: bool

    value: float

    rejection_reason: str | None = None


# ============================================================
# CANDIDATE FACTORY
# ============================================================

def make_candidate(
    number: int,
) -> Candidate:

    return Candidate(

        CandidateSeed(

            motor_key="TEST_MOTOR",

            z_s=20 + number,

            z_p=40,

            n_planets=4,

            module_mm=0.5,

            face_width_mm=8.0,
        )
    )


# ============================================================
# TEST 1 — SPLIT
# ============================================================

def test_split():

    feasible = make_candidate(
        0
    )

    feasible.mark_feasible()

    rejected = make_candidate(
        1
    )

    rejected.reject(

        PipelineStage.PLANETARY,

        "ratio_out_of_range",
    )

    pending = make_candidate(
        2
    )

    result = split_candidates(
        [
            feasible,
            rejected,
            pending,
        ]
    )

    assert len(
        result[0]
    ) == 1

    assert len(
        result[1]
    ) == 1

    assert len(
        result[2]
    ) == 1

    print("\n" + "=" * 76)
    print("TEST 1 — SPLIT")
    print("=" * 76)

    print(
        "PASS: candidates split correctly."
    )


# ============================================================
# TEST 2 — SUMMARY
# ============================================================

def test_summary():

    candidates = []

    # --------------------------------------------------------
    # 2 feasible
    # --------------------------------------------------------

    for i in range(2):

        candidate = (
            make_candidate(
                i
            )
        )

        candidate.mark_feasible()

        candidates.append(
            candidate
        )

    # --------------------------------------------------------
    # 2 planetary rejects
    # --------------------------------------------------------

    for i in range(
        2,
        4,
    ):

        candidate = (
            make_candidate(
                i
            )
        )

        candidate.reject(

            PipelineStage.PLANETARY,

            "ratio_out_of_range",
        )

        candidates.append(
            candidate
        )

    # --------------------------------------------------------
    # 1 gear-strength reject
    # --------------------------------------------------------

    candidate = (
        make_candidate(
            4
        )
    )

    candidate.reject(

        PipelineStage.GEAR_STRENGTH,

        "bending_safety_below_minimum_sun_sp",
    )

    candidates.append(
        candidate
    )

    summary = (
        summarize_candidates(
            candidates
        )
    )

    assert (
        summary.total_candidates
        ==
        5
    )

    assert (
        summary.feasible_candidates
        ==
        2
    )

    assert (
        summary.rejected_candidates
        ==
        3
    )

    assert (
        summary.pending_candidates
        ==
        0
    )

    assert (
        summary.rejection_by_stage[
            "planetary"
        ]
        ==
        2
    )

    assert (
        summary.rejection_by_stage[
            "gear_strength"
        ]
        ==
        1
    )

    assert (
        summary.rejection_by_reason[
            "ratio_out_of_range"
        ]
        ==
        2
    )

    print("\n" + "=" * 76)
    print("TEST 2 — SUMMARY")
    print("=" * 76)

    print(
        f"Total:    "
        f"{summary.total_candidates}"
    )

    print(
        f"Feasible: "
        f"{summary.feasible_candidates}"
    )

    print(
        f"Rejected: "
        f"{summary.rejected_candidates}"
    )

    print(
        "\nPASS: summary statistics correct."
    )


# ============================================================
# TEST 3 — FLATTENED CSV
# ============================================================

def test_candidate_csv():

    candidate = (
        make_candidate(
            0
        )
    )

    dummy = DummyResult(

        feasible=True,

        value=123.45,
    )

    candidate.attach_result(

        PipelineStage.PLANETARY,

        dummy,
    )

    candidate.mark_feasible()

    with TemporaryDirectory() as tmp:

        path = (
            Path(tmp)
            /
            "candidates.csv"
        )

        write_candidate_csv(
            [candidate],
            path,
        )

        assert path.exists()

        with path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as file:

            rows = list(
                csv.DictReader(
                    file
                )
            )

        assert len(
            rows
        ) == 1

        row = rows[0]

        assert (
            row[
                "candidate_id"
            ]
            ==
            candidate.candidate_id
        )

        assert (
            row[
                "status"
            ]
            ==
            "feasible"
        )

        assert (
            row[
                "seed_motor_key"
            ]
            ==
            "TEST_MOTOR"
        )

        assert (
            float(
                row[
                    "planetary_value"
                ]
            )
            ==
            123.45
        )

        print("\n" + "=" * 76)
        print("TEST 3 — CANDIDATE CSV")
        print("=" * 76)

        print(
            f"CSV: {path}"
        )

        print(
            "\nPASS: candidate CSV written correctly."
        )


# ============================================================
# TEST 4 — COMPLETE REPORT SET
# ============================================================

def test_complete_reports():

    feasible = (
        make_candidate(
            0
        )
    )

    feasible.mark_feasible()

    rejected = (
        make_candidate(
            1
        )
    )

    rejected.reject(

        PipelineStage.MOTOR_COMPATIBILITY,

        "motor_peak_torque_exceeded",
    )

    with TemporaryDirectory() as tmp:

        output = Path(
            tmp
        )

        summary = write_reports(

            [
                feasible,
                rejected,
            ],

            output_directory=output,

            print_terminal_summary=False,
        )

        feasible_path = (
            output
            /
            "feasible_candidates.csv"
        )

        rejected_path = (
            output
            /
            "rejected_candidates.csv"
        )

        summary_path = (
            output
            /
            "summary.csv"
        )

        assert feasible_path.exists()
        assert rejected_path.exists()
        assert summary_path.exists()

        assert (
            summary.total_candidates
            ==
            2
        )

        assert (
            summary.feasible_candidates
            ==
            1
        )

        assert (
            summary.rejected_candidates
            ==
            1
        )

        print("\n" + "=" * 76)
        print("TEST 4 — COMPLETE REPORTS")
        print("=" * 76)

        print(
            "PASS: all report files created."
        )


# ============================================================
# TEST 5 — EMPTY FEASIBLE FILE
# ============================================================

def test_empty_feasible_file():

    rejected = (
        make_candidate(
            0
        )
    )

    rejected.reject(

        PipelineStage.PLANETARY,

        "assembly_condition_failed",
    )

    with TemporaryDirectory() as tmp:

        output = Path(
            tmp
        )

        write_reports(

            [rejected],

            output_directory=output,

            print_terminal_summary=False,
        )

        feasible_path = (
            output
            /
            "feasible_candidates.csv"
        )

        assert (
            feasible_path.exists()
        )

        with feasible_path.open(
            "r",
            encoding="utf-8",
        ) as file:

            lines = (
                file.readlines()
            )

        # Header still exists.
        assert len(
            lines
        ) == 1

        print("\n" + "=" * 76)
        print("TEST 5 — EMPTY FEASIBLE SET")
        print("=" * 76)

        print(
            "PASS: empty feasible population "
            "still produces valid CSV."
        )


# ============================================================
# RUN ALL
# ============================================================

if __name__ == "__main__":

    test_split()
    test_summary()
    test_candidate_csv()
    test_complete_reports()
    test_empty_feasible_file()

    print("\n" + "=" * 76)
    print("ALL REPORTING TESTS PASSED")
    print("=" * 76)