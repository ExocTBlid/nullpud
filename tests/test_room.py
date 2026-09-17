"""Tests for nullpud.room — exits, item mutation, monster state."""

import pytest

from nullpud.puzzle import LockPuzzle
from nullpud.room import Room


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_room(exits=None, items=None, monster_id=None, puzzle_id=None) -> Room:
    return Room(
        id="test_room",
        name="Test Room",
        desc="A plain room.",
        exits=exits or {"north": "room_b", "south": "room_a"},
        items=list(items or []),
        monster_id=monster_id,
        puzzle_id=puzzle_id,
    )


def make_lock(blocks: str = "north", solved: bool = False) -> LockPuzzle:
    return LockPuzzle(
        id="p", type="lock", desc="Locked.", blocks_exit=blocks,
        success_msg="Open!", fail_msg="Nope.", key_item="key",
        solved=solved,
    )


# ---------------------------------------------------------------------------
# available_exits
# ---------------------------------------------------------------------------

class TestAvailableExits:
    def test_all_exits_when_no_puzzle(self):
        room = make_room(exits={"north": "n", "south": "s"})
        assert room.available_exits() == {"north": "n", "south": "s"}

    def test_blocked_exit_hidden_when_unsolved(self):
        room = make_room(exits={"north": "n", "south": "s"})
        puzzle = make_lock(blocks="north", solved=False)
        exits = room.available_exits(puzzle)
        assert "north" not in exits
        assert "south" in exits

    def test_blocked_exit_visible_when_solved(self):
        room = make_room(exits={"north": "n", "south": "s"})
        puzzle = make_lock(blocks="north", solved=True)
        exits = room.available_exits(puzzle)
        assert "north" in exits

    def test_puzzle_only_blocks_its_own_direction(self):
        room = make_room(exits={"north": "n", "south": "s", "east": "e"})
        puzzle = make_lock(blocks="north", solved=False)
        exits = room.available_exits(puzzle)
        assert "south" in exits
        assert "east" in exits

    def test_no_exits_returns_empty(self):
        room = Room(id="r", name="R", desc=".", exits={})
        assert room.available_exits() == {}


# ---------------------------------------------------------------------------
# take_item / drop_item
# ---------------------------------------------------------------------------

class TestItemMutation:
    def test_take_existing_item_returns_true(self):
        room = make_room(items=["rusty_key"])
        assert room.take_item("rusty_key") is True
        assert "rusty_key" not in room.items

    def test_take_missing_item_returns_false(self):
        room = make_room()
        assert room.take_item("ghost") is False

    def test_take_only_removes_one_copy(self):
        room = make_room(items=["potion", "potion"])
        room.take_item("potion")
        assert room.items.count("potion") == 1

    def test_drop_item_adds_to_room(self):
        room = make_room()
        room.drop_item("iron_sword")
        assert "iron_sword" in room.items

    def test_drop_allows_duplicates(self):
        room = make_room(items=["key"])
        room.drop_item("key")
        assert room.items.count("key") == 2


# ---------------------------------------------------------------------------
# monster_blocks / clear_monster
# ---------------------------------------------------------------------------

class TestMonsterState:
    def test_monster_blocks_when_present(self):
        room = make_room(monster_id="skeleton")
        assert room.monster_blocks() is True

    def test_monster_not_blocking_when_none(self):
        room = make_room()
        assert room.monster_blocks() is False

    def test_clear_monster_removes_id(self):
        room = make_room(monster_id="skeleton")
        room.clear_monster()
        assert room.monster_id is None
        assert room.monster_blocks() is False


# ---------------------------------------------------------------------------
# visited flag
# ---------------------------------------------------------------------------

class TestVisited:
    def test_unvisited_by_default(self):
        room = make_room()
        assert room.visited is False

    def test_can_set_visited(self):
        room = make_room()
        room.visited = True
        assert room.visited is True
