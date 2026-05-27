# Minimum Sum Set Cover Processor

## Instructions

You will be given a `cover.json` file containing a list of items and groups. Your task is to build an ordering of the items and compute the cover score for that ordering.

Implement it in:

`/app/cover_processor.py`

The program should read:

`/app/cover.json`

and write:

- `/app/ordering.txt`
- `/app/score.txt`
- `/app/errors.txt`

Use only the Python standard library.

## Task

Each group contains one or more item IDs.

An item covers a group if the item appears in that group.

A group is first covered at the position where the earliest item from that group appears in the ordering.

The score is the sum of the first-cover positions of all valid groups. Positions are 1-based.

## Input

The input file contains:

- `items`, a list of item IDs
- `groups`, a list of group objects

Each group has:

- `id`, a unique integer identifier
- `items`, a list of item IDs in that group

## Ordering rule

Build the ordering greedily.

At each step, choose the remaining item that covers the most groups that have not been covered yet.

If there is a tie, choose the smaller item ID.

Repeat this process for the remaining items.

## Invalid input

There may be invalid groups or noise in the input.

A group may be invalid if it has a duplicate ID, missing fields, an empty item list, or references an item that is not in the item list.

Invalid groups should not be used for scoring.

Noise entries that are not usable groups should be ignored.

## Output

Return three separate outputs:

- `ordering.txt`
- `score.txt`
- `errors.txt`

The `ordering.txt` file should contain the item ordering on one line:

`item_id, item_id, item_id`

The `score.txt` file should contain one line:

`score`

The `errors.txt` file is for invalid groups.

Each line should contain the group ID and reason.

If there are no invalid groups, create an empty `errors.txt`.
