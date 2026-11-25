"""
Standalone tests for src/models.py

Run from project root:

    python -m tests.models
"""

from dataclasses import dataclass

from src.models import (
    CandidateSeed,
    Candidate,
    CandidateStatus,
    PipelineStage,
    candidate_to_flat_dict,
)


# ============================================================
# SIMPLE DUMMY RESULT
#
# Allows us to test generic result storage without depending
# on any engineering module.
# ============================================================

@dataclass
class DummyResult:

    feasible: bool

    test_value: float

    rejection_reason: str | None = None


# ============================================================
# BASE SEED
# ============================================================

BASE_SEED = CandidateSeed(

    motor_key="RO80_KV105",

    z_s=20,
    z_p=40,

    n_planets=4,

    module_mm=0.5,

    face_width_mm=10.0,
)


# ============================================================
# TEST 1 — CANDIDATE CREATION
# ============================================================

def test_candidate_creation():

    candidate = Candidate(
        BASE_SEED
    )

    print("\n" + "=" * 76)
    print("TEST 1 — CANDIDATE CREATION")
    print("=" * 76)

    print(
        f"ID:     {candidate.candidate_id}"
    )

    print(
        f"Status: {candidate.status.value}"
    )

    assert (
        candidate.status
        ==
        CandidateStatus.PENDING
    )

    assert (
        candidate.candidate_id
        ==
        "RO80_KV105"
        "__Zs20"
        "__Zp40"
        "__Np4"
        "__m0p5"
        "__b10"
    )

    assert (
        candidate.rejected_stage
        is None
    )

    assert (
        candidate.rejection_reason
        is None
    )

    print(
        "\nPASS: candidate initialized correctly."
    )


# ============================================================
# TEST 2 — ATTACH RESULT
# ============================================================

def test_attach_result():

    candidate = Candidate(
        BASE_SEED
    )

    dummy = DummyResult(
        feasible=True,
        test_value=123.456,
    )

    candidate.attach_result(
        PipelineStage.PLANETARY,
        dummy,
    )

    assert (
        candidate.planetary
        is dummy
    )

    assert (
        candidate.last_completed_stage
        ==
        PipelineStage.PLANETARY
    )

    print("\n" + "=" * 76)
    print("TEST 2 — ATTACH RESULT")
    print("=" * 76)

    print(
        f"Last stage: "
        f"{candidate.last_completed_stage.value}"
    )

    print(
        "\nPASS: module result attached correctly."
    )


# ============================================================
# TEST 3 — REJECT CANDIDATE
# ============================================================

def test_reject_candidate():

    candidate = Candidate(
        BASE_SEED
    )

    candidate.reject(
        PipelineStage.PLANETARY,
        "planet_clearance_failed",
    )

    assert (
        candidate.status
        ==
        CandidateStatus.REJECTED
    )

    assert (
        candidate.rejected_stage
        ==
        PipelineStage.PLANETARY
    )

    assert (
        candidate.rejection_reason
        ==
        "planet_clearance_failed"
    )

    print("\n" + "=" * 76)
    print("TEST 3 — REJECTION")
    print("=" * 76)

    print(
        f"Stage:  "
        f"{candidate.rejected_stage.value}"
    )

    print(
        f"Reason: "
        f"{candidate.rejection_reason}"
    )

    print(
        "\nPASS: rejection state recorded correctly."
    )


# ============================================================
# TEST 4 — DOUBLE REJECTION MUST FAIL
# ============================================================

def test_double_rejection():

    candidate = Candidate(
        BASE_SEED
    )

    candidate.reject(
        PipelineStage.PLANETARY,
        "first_failure",
    )

    try:

        candidate.reject(
            PipelineStage.MOTOR_COMPATIBILITY,
            "second_failure",
        )

    except RuntimeError as exc:

        print("\n" + "=" * 76)
        print("TEST 4 — DOUBLE REJECTION")
        print("=" * 76)

        print(
            f"Expected error: {exc}"
        )

        print(
            "\nPASS: first rejection cannot be overwritten."
        )

        return

    raise AssertionError(
        "Expected RuntimeError was not raised."
    )


# ============================================================
# TEST 5 — MARK FEASIBLE
# ============================================================

def test_mark_feasible():

    candidate = Candidate(
        BASE_SEED
    )

    candidate.mark_feasible()

    assert (
        candidate.status
        ==
        CandidateStatus.FEASIBLE
    )

    assert candidate.is_feasible

    assert (
        candidate.last_completed_stage
        ==
        PipelineStage.COMPLETE
    )

    print("\n" + "=" * 76)
    print("TEST 5 — FEASIBLE CANDIDATE")
    print("=" * 76)

    print(
        f"Status: "
        f"{candidate.status.value}"
    )

    print(
        "\nPASS: feasible state recorded correctly."
    )


# ============================================================
# TEST 6 — FLATTEN FOR REPORTING
# ============================================================

def test_flatten_candidate():

    candidate = Candidate(
        BASE_SEED
    )

    dummy = DummyResult(
        feasible=True,
        test_value=42.5,
    )

    candidate.attach_result(
        PipelineStage.PLANETARY,
        dummy,
    )

    flattened = (
        candidate_to_flat_dict(
            candidate
        )
    )

    print("\n" + "=" * 76)
    print("TEST 6 — FLATTEN CANDIDATE")
    print("=" * 76)

    print(
        f"candidate_id: "
        f"{flattened['candidate_id']}"
    )

    print(
        f"motor:        "
        f"{flattened['seed_motor_key']}"
    )

    print(
        f"Zs:           "
        f"{flattened['seed_z_s']}"
    )

    print(
        f"dummy value:  "
        f"{flattened['planetary_test_value']}"
    )

    assert (
        flattened[
            "seed_motor_key"
        ]
        ==
        "RO80_KV105"
    )

    assert (
        flattened[
            "seed_z_s"
        ]
        ==
        20
    )

    assert (
        flattened[
            "planetary_test_value"
        ]
        ==
        42.5
    )

    assert (
        flattened[
            "status"
        ]
        ==
        "pending"
    )

    print(
        "\nPASS: candidate flattened correctly."
    )


# ============================================================
# TEST 7 — INVALID SEED
# ============================================================

def test_invalid_seed():

    try:

        CandidateSeed(
            motor_key="RO80_KV105",

            z_s=0,
            z_p=40,

            n_planets=4,

            module_mm=0.5,

            face_width_mm=10.0,
        )

    except ValueError as exc:

        print("\n" + "=" * 76)
        print("TEST 7 — INVALID SEED")
        print("=" * 76)

        print(
            f"Expected error: {exc}"
        )

        print(
            "\nPASS: invalid candidate seed rejected."
        )

        return

    raise AssertionError(
        "Expected ValueError was not raised."
    )


# ============================================================
# TEST 8 — CANNOT ATTACH RESULT AFTER REJECTION
# ============================================================

def test_no_processing_after_rejection():

    candidate = Candidate(
        BASE_SEED
    )

    candidate.reject(
        PipelineStage.PLANETARY,
        "failed",
    )

    dummy = DummyResult(
        feasible=True,
        test_value=1.0,
    )

    try:

        candidate.attach_result(
            PipelineStage.GEAR_FORCES,
            dummy,
        )

    except RuntimeError as exc:

        print("\n" + "=" * 76)
        print("TEST 8 — STOP AFTER REJECTION")
        print("=" * 76)

        print(
            f"Expected error: {exc}"
        )

        print(
            "\nPASS: rejected candidate cannot continue."
        )

        return

    raise AssertionError(
        "Expected RuntimeError was not raised."
    )


# ============================================================
# RUN ALL TESTS
# ============================================================

if __name__ == "__main__":

    test_candidate_creation()
    test_attach_result()
    test_reject_candidate()
    test_double_rejection()
    test_mark_feasible()
    test_flatten_candidate()
    test_invalid_seed()
    test_no_processing_after_rejection()

    print("\n" + "=" * 76)
    print("ALL MODELS TESTS PASSED")
    print("=" * 76)