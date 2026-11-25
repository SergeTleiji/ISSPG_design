"""
PIPELINE REPORTING

Purpose:
    Collect finished Candidate objects and generate human-readable
    and machine-readable optimization results.

OUTPUT FILES
------------
    output/feasible_candidates.csv

        One row per fully feasible candidate.
        Contains:
            search variables
            all attached module results
            final status

    output/rejected_candidates.csv

        One row per rejected candidate.
        Contains:
            search variables
            all results calculated before rejection
            rejection stage
            rejection reason

    output/summary.csv

        High-level pipeline statistics:
            total candidates
            feasible
            rejected
            pending
            rejection counts by stage
            rejection counts by reason

IMPORTANT
---------
    This module performs:
        - NO engineering calculations
        - NO candidate ranking
        - NO optimization objective evaluation

    Ranking will be added only after the feasible design population
    has been inspected.
"""

from __future__ import annotations

import csv

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from src.models import (
    Candidate,
    CandidateStatus,
    candidate_to_flat_dict,
)


# ============================================================
# SUMMARY MODEL
# ============================================================

@dataclass(frozen=True)
class ReportingSummary:

    total_candidates: int

    feasible_candidates: int

    rejected_candidates: int

    pending_candidates: int

    rejection_by_stage: dict[str, int]

    rejection_by_reason: dict[str, int]


# ============================================================
# SPLIT CANDIDATES
# ============================================================

def split_candidates(
    candidates: Iterable[Candidate],
) -> tuple[
    list[Candidate],
    list[Candidate],
    list[Candidate],
]:
    """
    Split candidates into:

        feasible
        rejected
        pending
    """

    feasible = []
    rejected = []
    pending = []

    for candidate in candidates:

        if candidate.status == CandidateStatus.FEASIBLE:

            feasible.append(
                candidate
            )

        elif candidate.status == CandidateStatus.REJECTED:

            rejected.append(
                candidate
            )

        else:

            pending.append(
                candidate
            )

    return (
        feasible,
        rejected,
        pending,
    )


# ============================================================
# CREATE SUMMARY
# ============================================================

def summarize_candidates(
    candidates: Iterable[Candidate],
) -> ReportingSummary:
    """
    Generate overall pipeline statistics.
    """

    candidates = list(
        candidates
    )

    (
        feasible,
        rejected,
        pending,
    ) = split_candidates(
        candidates
    )

    stage_counter = Counter()

    reason_counter = Counter()

    for candidate in rejected:

        if candidate.rejected_stage is None:

            stage_name = (
                "unknown"
            )

        else:

            stage_name = (
                candidate.rejected_stage.value
            )

        stage_counter[
            stage_name
        ] += 1

        reason = (
            candidate.rejection_reason
            if candidate.rejection_reason
            else "unknown"
        )

        reason_counter[
            reason
        ] += 1

    return ReportingSummary(

        total_candidates=len(
            candidates
        ),

        feasible_candidates=len(
            feasible
        ),

        rejected_candidates=len(
            rejected
        ),

        pending_candidates=len(
            pending
        ),

        rejection_by_stage=dict(
            sorted(
                stage_counter.items()
            )
        ),

        rejection_by_reason=dict(
            sorted(
                reason_counter.items()
            )
        ),
    )


# ============================================================
# COLUMN ORDER
# ============================================================

_PRIORITY_COLUMNS = [

    "candidate_id",

    "status",

    "last_completed_stage",

    "rejected_stage",

    "rejection_reason",

    "seed_motor_key",

    "seed_z_s",

    "seed_z_p",

    "seed_n_planets",

    "seed_module_mm",

    "seed_face_width_mm",
]


def _collect_fieldnames(
    rows: list[dict],
) -> list[str]:
    """
    Build one common CSV header across all rows.

    Important candidate-identification fields are placed first.
    Remaining engineering fields are sorted alphabetically.
    """

    if not rows:

        return list(
            _PRIORITY_COLUMNS
        )

    all_fields = set()

    for row in rows:

        all_fields.update(
            row.keys()
        )

    ordered = [

        column

        for column
        in _PRIORITY_COLUMNS

        if column in all_fields
    ]

    remaining = sorted(

        all_fields
        -
        set(ordered)
    )

    return (
        ordered
        +
        remaining
    )


# ============================================================
# WRITE CANDIDATE CSV
# ============================================================

def write_candidate_csv(
    candidates: Iterable[Candidate],
    path: str | Path,
) -> None:
    """
    Flatten and write candidates to CSV.

    An empty candidate list still produces a valid CSV with a
    basic header.
    """

    path = Path(
        path
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    candidates = list(
        candidates
    )

    rows = [

        candidate_to_flat_dict(
            candidate
        )

        for candidate in candidates
    ]

    fieldnames = (
        _collect_fieldnames(
            rows
        )
    )

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:

        writer = csv.DictWriter(

            file,

            fieldnames=fieldnames,

            extrasaction="ignore",
        )

        writer.writeheader()

        for row in rows:

            writer.writerow(
                row
            )


# ============================================================
# WRITE SUMMARY CSV
# ============================================================

def write_summary_csv(
    summary: ReportingSummary,
    path: str | Path,
) -> None:
    """
    Write pipeline summary in a simple:

        category, item, count

    structure.
    """

    path = Path(
        path
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    rows = [

        {
            "category": "overall",
            "item": "total_candidates",
            "count": (
                summary.total_candidates
            ),
        },

        {
            "category": "overall",
            "item": "feasible_candidates",
            "count": (
                summary.feasible_candidates
            ),
        },

        {
            "category": "overall",
            "item": "rejected_candidates",
            "count": (
                summary.rejected_candidates
            ),
        },

        {
            "category": "overall",
            "item": "pending_candidates",
            "count": (
                summary.pending_candidates
            ),
        },
    ]

    # --------------------------------------------------------
    # Rejection stage counts
    # --------------------------------------------------------

    for stage, count in (
        summary.rejection_by_stage.items()
    ):

        rows.append(
            {
                "category":
                    "rejection_stage",

                "item":
                    stage,

                "count":
                    count,
            }
        )

    # --------------------------------------------------------
    # Rejection reason counts
    # --------------------------------------------------------

    for reason, count in (
        summary.rejection_by_reason.items()
    ):

        rows.append(
            {
                "category":
                    "rejection_reason",

                "item":
                    reason,

                "count":
                    count,
            }
        )

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:

        writer = csv.DictWriter(

            file,

            fieldnames=[
                "category",
                "item",
                "count",
            ],
        )

        writer.writeheader()

        writer.writerows(
            rows
        )


# ============================================================
# TERMINAL SUMMARY
# ============================================================

def print_summary(
    summary: ReportingSummary,
) -> None:
    """
    Print compact pipeline statistics.
    """

    print(
        "\n"
        + "=" * 76
    )

    print(
        "ISSPG FEASIBILITY PIPELINE SUMMARY"
    )

    print(
        "=" * 76
    )

    print(
        f"Total candidates:     "
        f"{summary.total_candidates}"
    )

    print(
        f"Feasible candidates:  "
        f"{summary.feasible_candidates}"
    )

    print(
        f"Rejected candidates:  "
        f"{summary.rejected_candidates}"
    )

    print(
        f"Pending candidates:   "
        f"{summary.pending_candidates}"
    )

    # --------------------------------------------------------
    # Percentages
    # --------------------------------------------------------

    if (
        summary.total_candidates
        >
        0
    ):

        feasible_percent = (

            100.0
            *
            summary.feasible_candidates
            /
            summary.total_candidates
        )

        rejected_percent = (

            100.0
            *
            summary.rejected_candidates
            /
            summary.total_candidates
        )

        print()

        print(
            f"Feasible fraction:    "
            f"{feasible_percent:.2f} %"
        )

        print(
            f"Rejected fraction:    "
            f"{rejected_percent:.2f} %"
        )

    # --------------------------------------------------------
    # Rejection funnel
    # --------------------------------------------------------

    if (
        summary.rejection_by_stage
    ):

        print()

        print(
            "REJECTIONS BY STAGE"
        )

        print(
            "-" * 76
        )

        for stage, count in (
            summary.rejection_by_stage.items()
        ):

            print(
                f"{stage:<32}"
                f"{count:>10}"
            )

    # --------------------------------------------------------
    # Rejection reasons
    # --------------------------------------------------------

    if (
        summary.rejection_by_reason
    ):

        print()

        print(
            "REJECTIONS BY REASON"
        )

        print(
            "-" * 76
        )

        for reason, count in (
            summary.rejection_by_reason.items()
        ):

            print(
                f"{reason:<52}"
                f"{count:>10}"
            )

    print(
        "=" * 76
    )


# ============================================================
# COMPLETE REPORT WRITER
# ============================================================

def write_reports(
    candidates: Iterable[Candidate],
    output_directory: str | Path = "output",
    *,
    print_terminal_summary: bool = True,
) -> ReportingSummary:
    """
    Generate all standard pipeline reports.

    Outputs:
        feasible_candidates.csv
        rejected_candidates.csv
        summary.csv

    Returns:
        ReportingSummary
    """

    candidates = list(
        candidates
    )

    output_directory = Path(
        output_directory
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    (
        feasible,
        rejected,
        pending,
    ) = split_candidates(
        candidates
    )

    summary = summarize_candidates(
        candidates
    )

    # --------------------------------------------------------
    # Candidate-level reports
    # --------------------------------------------------------

    write_candidate_csv(

        feasible,

        output_directory
        /
        "feasible_candidates.csv",
    )

    write_candidate_csv(

        rejected,

        output_directory
        /
        "rejected_candidates.csv",
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    write_summary_csv(

        summary,

        output_directory
        /
        "summary.csv",
    )

    # --------------------------------------------------------
    # Terminal
    # --------------------------------------------------------

    if print_terminal_summary:

        print_summary(
            summary
        )

    return summary