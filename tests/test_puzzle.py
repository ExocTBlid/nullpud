"""Tests for nullpud.puzzle — all 4 types, outcomes, edge cases."""

import pytest

from nullpud.puzzle import (
    CombinationPuzzle,
    LeverPuzzle,
    LockPuzzle,
    PuzzleOutcome,
    RiddlePuzzle,
    puzzle_from_dict,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_lock(key="gold_key", hint="") -> LockPuzzle:
    return LockPuzzle(
        id="test_lock", type="lock", desc="A locked door.",
        blocks_exit="north", success_msg="Open!", fail_msg="Locked.",
        hint=hint, key_item=key,
    )


def make_riddle(answer="fire", hint="") -> RiddlePuzzle:
    return RiddlePuzzle(
        id="test_riddle", type="riddle", desc="A riddle.",
        blocks_exit="east", success_msg="Correct!", fail_msg="Wrong.",
        hint=hint, answer=answer,
    )


def make_lever(sequence=None) -> LeverPuzzle:
    if sequence is None:
        sequence = ["a", "b", "c"]
    return LeverPuzzle(
        id="test_lever", type="lever", desc="Levers.",
        blocks_exit="west", success_msg="Done!", fail_msg="Reset.",
        hint="Try in order.", sequence=sequence,
    )


def make_combo(items=None, consume=False) -> CombinationPuzzle:
    if items is None:
        items = ["sword", "shield"]
    return CombinationPuzzle(
        id="test_combo", type="combination", desc="Two slots.",
        blocks_exit="south", success_msg="Solved!", fail_msg="Wrong item.",
        consume=consume, items=items,
    )


# ---------------------------------------------------------------------------
# LockPuzzle
# ---------------------------------------------------------------------------

class TestLockPuzzle:
    def test_solved_with_key(self):
        p = make_lock()
        result = p.attempt(inventory=["gold_key"])
        assert result.outcome == PuzzleOutcome.SOLVED

    def test_fail_without_key(self):
        p = make_lock()
        result = p.attempt(inventory=["rusty_key"])
        assert result.outcome == PuzzleOutcome.FAIL

    def test_hint_when_no_key_and_hint_set(self):
        p = make_lock(hint="You need a key.")
        result = p.attempt(inventory=[])
        assert result.outcome == PuzzleOutcome.HINT
        assert "key" in result.message.lower()

    def test_already_solved_after_first_success(self):
        p = make_lock()
        p.attempt(inventory=["gold_key"])
        result = p.attempt(inventory=["gold_key"])
        assert result.outcome == PuzzleOutcome.ALREADY_SOLVED

    def test_solved_flag_set(self):
        p = make_lock()
        p.attempt(inventory=["gold_key"])
        assert p.solved is True

    def test_success_message_returned(self):
        p = make_lock()
        result = p.attempt(inventory=["gold_key"])
        assert result.message == "Open!"


# ---------------------------------------------------------------------------
# RiddlePuzzle
# ---------------------------------------------------------------------------

class TestRiddlePuzzle:
    def test_correct_answer_solves(self):
        p = make_riddle()
        result = p.attempt(player_answer="fire")
        assert result.outcome == PuzzleOutcome.SOLVED

    def test_case_insensitive(self):
        p = make_riddle()
        result = p.attempt(player_answer="FIRE")
        assert result.outcome == PuzzleOutcome.SOLVED

    def test_leading_trailing_whitespace_stripped(self):
        p = make_riddle()
        result = p.attempt(player_answer="  fire  ")
        assert result.outcome == PuzzleOutcome.SOLVED

    def test_wrong_answer_fails(self):
        p = make_riddle()
        result = p.attempt(player_answer="water")
        assert result.outcome == PuzzleOutcome.FAIL

    def test_empty_answer_returns_hint_when_set(self):
        p = make_riddle(hint="Think warm.")
        result = p.attempt(player_answer="")
        assert result.outcome == PuzzleOutcome.HINT

    def test_empty_answer_fails_when_no_hint(self):
        p = make_riddle()
        result = p.attempt(player_answer="")
        assert result.outcome == PuzzleOutcome.FAIL

    def test_already_solved(self):
        p = make_riddle()
        p.attempt(player_answer="fire")
        result = p.attempt(player_answer="fire")
        assert result.outcome == PuzzleOutcome.ALREADY_SOLVED


# ---------------------------------------------------------------------------
# LeverPuzzle
# ---------------------------------------------------------------------------

class TestLeverPuzzle:
    def test_correct_sequence_solves(self):
        p = make_lever(["a", "b", "c"])
        p.attempt(item_used="a")
        p.attempt(item_used="b")
        result = p.attempt(item_used="c")
        assert result.outcome == PuzzleOutcome.SOLVED

    def test_wrong_step_resets_progress(self):
        p = make_lever(["a", "b", "c"])
        p.attempt(item_used="a")
        p.attempt(item_used="x")   # wrong — resets
        result = p.attempt(item_used="b")  # now at position 0, expects "a"
        assert result.outcome == PuzzleOutcome.FAIL

    def test_mid_sequence_returns_hint(self):
        p = make_lever(["a", "b", "c"])
        result = p.attempt(item_used="a")
        assert result.outcome == PuzzleOutcome.HINT
        assert "2" in result.message  # "2 step(s) remaining"

    def test_empty_item_returns_hint_when_set(self):
        p = make_lever()
        result = p.attempt(item_used="")
        assert result.outcome == PuzzleOutcome.HINT

    def test_single_step_sequence(self):
        p = make_lever(["only"])
        result = p.attempt(item_used="only")
        assert result.outcome == PuzzleOutcome.SOLVED

    def test_already_solved(self):
        p = make_lever(["a"])
        p.attempt(item_used="a")
        result = p.attempt(item_used="a")
        assert result.outcome == PuzzleOutcome.ALREADY_SOLVED


# ---------------------------------------------------------------------------
# CombinationPuzzle
# ---------------------------------------------------------------------------

class TestCombinationPuzzle:
    def test_both_items_solve(self):
        p = make_combo(["sword", "shield"])
        p.attempt(item_used="sword", inventory=["sword", "shield"])
        result = p.attempt(item_used="shield", inventory=["sword", "shield"])
        assert result.outcome == PuzzleOutcome.SOLVED

    def test_order_independent(self):
        p = make_combo(["sword", "shield"])
        p.attempt(item_used="shield", inventory=["sword", "shield"])
        result = p.attempt(item_used="sword", inventory=["sword", "shield"])
        assert result.outcome == PuzzleOutcome.SOLVED

    def test_wrong_item_fails(self):
        p = make_combo(["sword", "shield"])
        result = p.attempt(item_used="potion", inventory=["potion"])
        assert result.outcome == PuzzleOutcome.FAIL

    def test_partial_returns_hint(self):
        p = make_combo(["sword", "shield"])
        result = p.attempt(item_used="sword", inventory=["sword", "shield"])
        assert result.outcome == PuzzleOutcome.HINT
        assert "shield" in result.message

    def test_consume_flag_in_message(self):
        p = make_combo(consume=True)
        p.attempt(item_used="sword", inventory=["sword", "shield"])
        result = p.attempt(item_used="shield", inventory=["sword", "shield"])
        assert result.outcome == PuzzleOutcome.SOLVED
        assert "__consume__" in result.message

    def test_no_consume_no_tag(self):
        p = make_combo(consume=False)
        p.attempt(item_used="sword", inventory=["sword", "shield"])
        result = p.attempt(item_used="shield", inventory=["sword", "shield"])
        assert "__consume__" not in result.message

    def test_already_solved(self):
        p = make_combo(["sword", "shield"])
        p.attempt(item_used="sword", inventory=["sword", "shield"])
        p.attempt(item_used="shield", inventory=["sword", "shield"])
        result = p.attempt(item_used="sword", inventory=["sword", "shield"])
        assert result.outcome == PuzzleOutcome.ALREADY_SOLVED


# ---------------------------------------------------------------------------
# puzzle_from_dict factory
# ---------------------------------------------------------------------------

class TestPuzzleFromDict:
    def test_creates_lock(self):
        data = {
            "type": "lock", "desc": "d", "blocks_exit": "north",
            "success_msg": "ok", "fail_msg": "no", "key_item": "big_key",
        }
        p = puzzle_from_dict("p1", data)
        assert isinstance(p, LockPuzzle)
        assert p.key_item == "big_key"

    def test_creates_riddle(self):
        data = {
            "type": "riddle", "desc": "d", "blocks_exit": "east",
            "success_msg": "ok", "fail_msg": "no", "answer": "sky",
        }
        p = puzzle_from_dict("p2", data)
        assert isinstance(p, RiddlePuzzle)
        assert p.answer == "sky"

    def test_creates_lever(self):
        data = {
            "type": "lever", "desc": "d", "blocks_exit": "west",
            "success_msg": "ok", "fail_msg": "no", "sequence": ["x", "y"],
        }
        p = puzzle_from_dict("p3", data)
        assert isinstance(p, LeverPuzzle)
        assert p.sequence == ["x", "y"]

    def test_creates_combination(self):
        data = {
            "type": "combination", "desc": "d", "blocks_exit": "south",
            "success_msg": "ok", "fail_msg": "no", "items": ["a", "b"],
        }
        p = puzzle_from_dict("p4", data)
        assert isinstance(p, CombinationPuzzle)
        assert p.items == ["a", "b"]

    def test_unknown_type_raises(self):
        data = {
            "type": "teleport", "desc": "d", "blocks_exit": "north",
            "success_msg": "ok", "fail_msg": "no",
        }
        with pytest.raises(ValueError, match="teleport"):
            puzzle_from_dict("p5", data)
