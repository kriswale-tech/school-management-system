"""Competition ranking for class assessment positions (ties share rank, next skips)."""

from __future__ import annotations

from decimal import Decimal


def competition_ranks(entries: list[tuple[str, Decimal]]) -> dict[str, int]:
    """
    Rank keys by score descending. Equal scores share a rank; the next rank skips.

    Example: scores 90, 80, 80, 70 → positions 1, 2, 2, 4.
    """
    if not entries:
        return {}

    ordered = sorted(entries, key=lambda item: (-item[1], item[0]))
    ranks: dict[str, int] = {}
    index = 0
    while index < len(ordered):
        score = ordered[index][1]
        end = index + 1
        while end < len(ordered) and ordered[end][1] == score:
            end += 1
        position = index + 1
        for key, _ in ordered[index:end]:
            ranks[key] = position
        index = end
    return ranks


def average_totals(totals: list[Decimal]) -> Decimal | None:
    if not totals:
        return None
    return sum(totals, Decimal('0')) / Decimal(len(totals))
