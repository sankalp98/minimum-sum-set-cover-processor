import json
import subprocess
import sys
from pathlib import Path

APP_DIR = Path("/app")
INPUT_PATH = APP_DIR / "cover.json"
SCRIPT_PATH = APP_DIR / "cover_processor.py"
ORDERING_PATH = APP_DIR / "ordering.txt"
SCORE_PATH = APP_DIR / "score.txt"
ERRORS_PATH = APP_DIR / "errors.txt"


def run_processor(payload):
    INPUT_PATH.write_text(json.dumps(payload), encoding="utf-8")

    for path in [ORDERING_PATH, SCORE_PATH, ERRORS_PATH]:
        if path.exists():
            path.unlink()

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        cwd=str(APP_DIR),
        text=True,
        capture_output=True,
        timeout=10,
    )

    assert result.returncode == 0, (
        f"Processor exited with non-zero status.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )

    assert ORDERING_PATH.exists(), "ordering.txt was not created"
    assert SCORE_PATH.exists(), "score.txt was not created"
    assert ERRORS_PATH.exists(), "errors.txt was not created"

    return read_ordering(), read_score(), read_errors()


def read_ordering():
    text = ORDERING_PATH.read_text(encoding="utf-8").strip()
    if not text:
        return []

    parts = [p.strip() for p in text.split(",")]
    return [int(p) for p in parts if p != ""]


def read_score():
    text = SCORE_PATH.read_text(encoding="utf-8").strip()
    assert text != "", "score.txt is empty"
    return int(text)


def read_errors():
    rows = []
    text = ERRORS_PATH.read_text(encoding="utf-8").strip()
    if not text:
        return rows

    for line in text.splitlines():
        parts = [p.strip() for p in line.split(",", 1)]
        assert len(parts) == 2, f"Invalid error line format: {line}"
        rows.append((int(parts[0]), parts[1]))
    return rows


def test_classic_set_cover_trap_full_ordering_required():
    payload = {
        "items": [1, 2, 3, 4],
        "groups": [
            {"id": 1, "items": [1, 2]},
            {"id": 2, "items": [2, 3]},
            {"id": 3, "items": [2, 4]},
        ],
    }

    ordering, score, errors = run_processor(payload)

    assert ordering == [2, 1, 3, 4]
    assert score == 3
    assert errors == []


def test_score_uses_one_based_first_cover_positions():
    payload = {
        "items": [1, 2, 3],
        "groups": [
            {"id": 1, "items": [2]},
            {"id": 2, "items": [3]},
        ],
    }

    ordering, score, errors = run_processor(payload)

    assert ordering == [2, 3, 1]
    assert score == 3
    assert errors == []


def test_greedy_uses_newly_uncovered_groups_only():
    payload = {
        "items": [1, 2, 3],
        "groups": [
            {"id": 1, "items": [1, 2]},
            {"id": 2, "items": [1, 2]},
            {"id": 3, "items": [3]},
        ],
    }

    ordering, score, errors = run_processor(payload)

    assert ordering == [1, 3, 2]
    assert score == 4
    assert errors == []


def test_tie_breaks_by_smaller_item_id_not_input_order():
    payload = {
        "items": [9, 5, 2],
        "groups": [
            {"id": 1, "items": [5]},
            {"id": 2, "items": [2]},
            {"id": 3, "items": [9]},
        ],
    }

    ordering, score, errors = run_processor(payload)

    assert ordering == [2, 5, 9]
    assert score == 6
    assert errors == []


def test_leftover_items_with_no_groups_still_appear():
    payload = {
        "items": [1, 2, 3, 4],
        "groups": [
            {"id": 1, "items": [2]},
        ],
    }

    ordering, score, errors = run_processor(payload)

    assert ordering == [2, 1, 3, 4]
    assert score == 1
    assert errors == []


def test_duplicate_items_inside_group_do_not_inflate_coverage():
    payload = {
        "items": [1, 2, 3],
        "groups": [
            {"id": 1, "items": [1, 1, 1]},
            {"id": 2, "items": [2]},
            {"id": 3, "items": [3]},
        ],
    }

    ordering, score, errors = run_processor(payload)

    assert ordering == [1, 2, 3]
    assert score == 6
    assert errors == []


def test_invalid_groups_are_reported_and_not_used_for_scoring():
    payload = {
        "items": [1, 2, 3],
        "groups": [
            {"id": 1, "items": [1, 2]},
            {"id": 2, "items": []},
            {"id": 3, "items": [4]},
            {"id": 1, "items": [3]},
            "noise",
            123,
            {"not_a_group": True},
        ],
    }

    ordering, score, errors = run_processor(payload)

    assert ordering == [1, 2, 3]
    assert score == 1

    error_ids = {group_id for group_id, _ in errors}
    assert error_ids == {1, 2, 3}


def test_invalid_group_with_no_usable_id_is_ignored():
    payload = {
        "items": [1, 2],
        "groups": [
            {"id": 1, "items": [1]},
            {"items": [2]},
            {"id": "2", "items": [2]},
            {"id": 3},
            None,
            "noise",
        ],
    }

    ordering, score, errors = run_processor(payload)

    assert ordering == [1, 2]
    assert score == 1

    error_ids = {group_id for group_id, _ in errors}
    assert error_ids == {3}


def test_duplicate_group_keeps_first_valid_group_only():
    payload = {
        "items": [1, 2, 3],
        "groups": [
            {"id": 10, "items": [2]},
            {"id": 10, "items": [1, 3]},
            {"id": 20, "items": [3]},
        ],
    }

    ordering, score, errors = run_processor(payload)

    assert ordering == [2, 3, 1]
    assert score == 3

    assert len(errors) == 1
    assert errors[0][0] == 10
    assert "duplicate" in errors[0][1].lower()


def test_items_with_zero_new_coverage_sorted_by_id_after_covered():
    payload = {
        "items": [5, 1, 4, 2, 3],
        "groups": [
            {"id": 1, "items": [4]},
        ],
    }

    ordering, score, errors = run_processor(payload)

    assert ordering == [4, 1, 2, 3, 5]
    assert score == 1
    assert errors == []


def test_non_contiguous_item_ids_and_negative_item_ids():
    payload = {
        "items": [100, -5, 42, 7],
        "groups": [
            {"id": 1, "items": [100, 42]},
            {"id": 2, "items": [-5]},
            {"id": 3, "items": [7, 42]},
        ],
    }

    ordering, score, errors = run_processor(payload)

    assert ordering == [42, -5, 7, 100]
    assert score == 4
    assert errors == []


def test_no_valid_groups_still_orders_items_and_score_zero():
    payload = {
        "items": [3, 1, 2],
        "groups": [
            {"id": 1, "items": []},
            {"id": 2, "items": [99]},
            "noise",
        ],
    }

    ordering, score, errors = run_processor(payload)

    assert ordering == [1, 2, 3]
    assert score == 0

    error_ids = {group_id for group_id, _ in errors}
    assert error_ids == {1, 2}


def test_boolean_values_are_not_valid_integer_ids():
    payload = {
        "items": [1, 2, 3],
        "groups": [
            {"id": 1, "items": [1]},
            {"id": True, "items": [2]},
            {"id": 2, "items": [True]},
            {"id": 3, "items": [3]},
        ],
    }

    ordering, score, errors = run_processor(payload)

    assert ordering == [1, 3, 2]
    assert score == 3

    error_ids = {group_id for group_id, _ in errors}
    assert error_ids == {2}


def test_empty_items_list_with_invalid_groups():
    payload = {
        "items": [],
        "groups": [
            {"id": 1, "items": [1]},
            {"id": 2, "items": []},
            {"id": 3, "items": [2]},
        ],
    }

    ordering, score, errors = run_processor(payload)

    assert ordering == []
    assert score == 0

    error_ids = {group_id for group_id, _ in errors}
    assert error_ids == {1, 2, 3}


def test_complex_greedy_ordering_and_score():
    payload = {
        "items": [1, 2, 3, 4, 5, 6],
        "groups": [
            {"id": 1, "items": [1, 2, 3]},
            {"id": 2, "items": [2, 4]},
            {"id": 3, "items": [2, 5]},
            {"id": 4, "items": [3, 5]},
            {"id": 5, "items": [4, 6]},
            {"id": 6, "items": [6]},
        ],
    }

    ordering, score, errors = run_processor(payload)

    assert ordering == [2, 6, 3, 1, 4, 5]
    assert score == 10
    assert errors == []
