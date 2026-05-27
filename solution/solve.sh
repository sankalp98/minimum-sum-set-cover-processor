#!/bin/bash
set -e

cat > /app/cover_processor.py <<'PY'
import json
from pathlib import Path

INPUT_PATH = Path("/app/cover.json")
ORDERING_PATH = Path("/app/ordering.txt")
SCORE_PATH = Path("/app/score.txt")
ERRORS_PATH = Path("/app/errors.txt")


def is_int(value):
    return type(value) is int


def main():
    try:
        data = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    except Exception:
        ORDERING_PATH.write_text("", encoding="utf-8")
        SCORE_PATH.write_text("0\n", encoding="utf-8")
        ERRORS_PATH.write_text("", encoding="utf-8")
        return

    if not isinstance(data, dict):
        ORDERING_PATH.write_text("", encoding="utf-8")
        SCORE_PATH.write_text("0\n", encoding="utf-8")
        ERRORS_PATH.write_text("", encoding="utf-8")
        return

    raw_items = data.get("items", [])
    raw_groups = data.get("groups", [])

    if not isinstance(raw_items, list):
        raw_items = []

    if not isinstance(raw_groups, list):
        raw_groups = []

    # Keep only usable integer item IDs.
    # Sort them so tie-breaking and leftover ordering are deterministic.
    item_set = set()
    for item in raw_items:
        if is_int(item):
            item_set.add(item)

    items = sorted(item_set)

    valid_groups = []
    errors = []
    seen_group_ids = set()

    for group in raw_groups:
        if not isinstance(group, dict):
            continue

        group_id = group.get("id")

        # If there is no usable integer group ID, we cannot report it in errors.txt.
        if not is_int(group_id):
            continue

        if group_id in seen_group_ids:
            errors.append((group_id, "duplicate group id"))
            continue

        seen_group_ids.add(group_id)

        if "items" not in group:
            errors.append((group_id, "missing field"))
            continue

        group_items = group.get("items")

        if not isinstance(group_items, list):
            errors.append((group_id, "invalid items"))
            continue

        if len(group_items) == 0:
            errors.append((group_id, "empty item list"))
            continue

        normalized_group_items = set()

        valid = True
        for item in group_items:
            if not is_int(item):
                valid = False
                break

            if item not in item_set:
                valid = False
                break

            normalized_group_items.add(item)

        if not valid:
            errors.append((group_id, "unknown item"))
            continue

        if len(normalized_group_items) == 0:
            errors.append((group_id, "empty item list"))
            continue

        valid_groups.append({
            "id": group_id,
            "items": normalized_group_items,
        })

    remaining_items = set(items)
    covered_group_ids = set()
    ordering = []

    while remaining_items:
        best_item = None
        best_new_cover_count = None

        for item in sorted(remaining_items):
            newly_covered = 0

            for group in valid_groups:
                if group["id"] in covered_group_ids:
                    continue
                if item in group["items"]:
                    newly_covered += 1

            if best_item is None:
                best_item = item
                best_new_cover_count = newly_covered
            elif newly_covered > best_new_cover_count:
                best_item = item
                best_new_cover_count = newly_covered
            elif newly_covered == best_new_cover_count and item < best_item:
                best_item = item
                best_new_cover_count = newly_covered

        ordering.append(best_item)
        remaining_items.remove(best_item)

        for group in valid_groups:
            if group["id"] in covered_group_ids:
                continue
            if best_item in group["items"]:
                covered_group_ids.add(group["id"])

    position_by_item = {
        item: idx + 1
        for idx, item in enumerate(ordering)
    }

    score = 0
    for group in valid_groups:
        first_position = min(position_by_item[item] for item in group["items"])
        score += first_position

    errors.sort(key=lambda row: row[0])

    ORDERING_PATH.write_text(
        ", ".join(str(item) for item in ordering) + ("\n" if ordering else ""),
        encoding="utf-8",
    )

    SCORE_PATH.write_text(f"{score}\n", encoding="utf-8")

    ERRORS_PATH.write_text(
        "\n".join(f"{group_id}, {reason}" for group_id, reason in errors)
        + ("\n" if errors else ""),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
PY

python3 /app/cover_processor.py