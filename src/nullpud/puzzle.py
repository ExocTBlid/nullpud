"""Puzzle state machines for room obstacles.

Each puzzle type is a dataclass with an attempt() method that returns a
PuzzleResult. run_loop.py owns all printing; puzzle.py only returns data.

Puzzle types
------------
lock        — requires a specific key item in the player's inventory
riddle      — correct answer string (case-insensitive, stripped)
lever       — sequence of item ids used in order; wrong step resets progress
combination — set of items used together (order-independent); optionally consumed
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Literal, Optional


class PuzzleOutcome(Enum):
    SOLVED = auto()
    FAIL = auto()
    HINT = auto()
    ALREADY_SOLVED = auto()


@dataclass
class PuzzleResult:
    outcome: PuzzleOutcome
    message: str


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

@dataclass
class Puzzle:
    id: str
    type: str
    desc: str
    blocks_exit: str
    success_msg: str
    fail_msg: str
    hint: str = ""
    solved: bool = False

    def attempt(self, **kwargs) -> PuzzleResult:  # type: ignore[override]
        raise NotImplementedError

    def _already_solved(self) -> PuzzleResult:
        return PuzzleResult(PuzzleOutcome.ALREADY_SOLVED, "That's already been dealt with.")


# ---------------------------------------------------------------------------
# Lock
# ---------------------------------------------------------------------------

@dataclass
class LockPuzzle(Puzzle):
    key_item: str = ""

    def attempt(self, inventory: list[str], **_) -> PuzzleResult:  # type: ignore[override]
        if self.solved:
            return self._already_solved()
        if self.key_item in inventory:
            self.solved = True
            return PuzzleResult(PuzzleOutcome.SOLVED, self.success_msg)
        if self.hint:
            return PuzzleResult(PuzzleOutcome.HINT, self.hint)
        return PuzzleResult(PuzzleOutcome.FAIL, self.fail_msg)


# ---------------------------------------------------------------------------
# Riddle
# ---------------------------------------------------------------------------

@dataclass
class RiddlePuzzle(Puzzle):
    answer: str = ""

    def attempt(self, player_answer: str = "", **_) -> PuzzleResult:  # type: ignore[override]
        if self.solved:
            return self._already_solved()
        if player_answer.strip().lower() == self.answer.strip().lower():
            self.solved = True
            return PuzzleResult(PuzzleOutcome.SOLVED, self.success_msg)
        if self.hint and not player_answer:
            return PuzzleResult(PuzzleOutcome.HINT, self.hint)
        return PuzzleResult(PuzzleOutcome.FAIL, self.fail_msg)


# ---------------------------------------------------------------------------
# Lever (ordered sequence)
# ---------------------------------------------------------------------------

@dataclass
class LeverPuzzle(Puzzle):
    sequence: list[str] = field(default_factory=list)
    _progress: int = field(default=0, init=False, repr=False)

    def attempt(self, item_used: str = "", **_) -> PuzzleResult:  # type: ignore[override]
        if self.solved:
            return self._already_solved()
        if not item_used:
            if self.hint:
                return PuzzleResult(PuzzleOutcome.HINT, self.hint)
            return PuzzleResult(PuzzleOutcome.FAIL, self.fail_msg)

        expected = self.sequence[self._progress]
        if item_used == expected:
            self._progress += 1
            if self._progress == len(self.sequence):
                self.solved = True
                return PuzzleResult(PuzzleOutcome.SOLVED, self.success_msg)
            remaining = len(self.sequence) - self._progress
            return PuzzleResult(
                PuzzleOutcome.HINT,
                f"Something shifts... {remaining} step(s) remaining.",
            )
        else:
            self._progress = 0
            return PuzzleResult(PuzzleOutcome.FAIL, self.fail_msg)


# ---------------------------------------------------------------------------
# Combination (unordered set of items)
# ---------------------------------------------------------------------------

@dataclass
class CombinationPuzzle(Puzzle):
    items: list[str] = field(default_factory=list)
    consume: bool = False
    _used: set[str] = field(default_factory=set, init=False, repr=False)

    def attempt(
        self,
        item_used: str = "",
        inventory: Optional[list[str]] = None,
        **_,
    ) -> PuzzleResult:  # type: ignore[override]
        if self.solved:
            return self._already_solved()
        if inventory is None:
            inventory = []

        if item_used not in self.items:
            return PuzzleResult(PuzzleOutcome.FAIL, self.fail_msg)

        self._used.add(item_used)

        if set(self.items) == self._used:
            self.solved = True
            # Signal to caller which items to consume via the message tag
            return PuzzleResult(
                PuzzleOutcome.SOLVED,
                self.success_msg + (f"\n__consume__:{','.join(self.items)}" if self.consume else ""),
            )

        remaining = [i for i in self.items if i not in self._used]
        return PuzzleResult(
            PuzzleOutcome.HINT,
            f"One slot fills. Still need: {', '.join(remaining)}.",
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def puzzle_from_dict(puzzle_id: str, data: dict) -> Puzzle:
    """Build the right Puzzle subclass from a dungeon JSON puzzle entry."""
    common = dict(
        id=puzzle_id,
        type=data["type"],
        desc=data["desc"],
        blocks_exit=data["blocks_exit"],
        success_msg=data["success_msg"],
        fail_msg=data["fail_msg"],
        hint=data.get("hint", ""),
    )
    ptype: str = data["type"]
    if ptype == "lock":
        return LockPuzzle(**common, key_item=data["key_item"])
    elif ptype == "riddle":
        return RiddlePuzzle(**common, answer=data["answer"])
    elif ptype == "lever":
        return LeverPuzzle(**common, sequence=data["sequence"])
    elif ptype == "combination":
        return CombinationPuzzle(
            **common,
            items=data["items"],
            consume=data.get("consume", False),
        )
    else:
        raise ValueError(f"Unknown puzzle type: {ptype!r}")
