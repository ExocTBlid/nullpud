"""Tests for nullpud.dungeon — loading, scaling, room/puzzle access."""

import json
import pytest

from nullpud.dungeon import (
    DUNGEON_ORDER,
    Dungeon,
    dungeon_choices,
    dungeon_info,
    next_dungeon,
    record_completion,
)
from nullpud.item import load_all_items
from nullpud.puzzle import CombinationPuzzle, LeverPuzzle, LockPuzzle, RiddlePuzzle


# ---------------------------------------------------------------------------
# Dungeon.load — real crypt_1 data
# ---------------------------------------------------------------------------

class TestDungeonLoad:
    @pytest.fixture
    def dungeon(self):
        return Dungeon.load("crypt_1")

    def test_dungeon_id(self, dungeon):
        assert dungeon.id == "crypt_1"

    def test_dungeon_name(self, dungeon):
        assert dungeon.name == "The Weeping Crypt"

    def test_base_level(self, dungeon):
        assert dungeon.base_level == 1

    def test_entry_room_exists(self, dungeon):
        assert dungeon.entry_room_id in dungeon.rooms
        assert dungeon.entry_room.id == dungeon.entry_room_id

    def test_boss_room_exists(self, dungeon):
        assert dungeon.boss_room_id in dungeon.rooms
        assert dungeon.boss_room.id == dungeon.boss_room_id

    def test_all_rooms_loaded(self, dungeon):
        expected = {"entrance", "hall", "puzzle_room", "treasure_room", "boss_chamber"}
        assert set(dungeon.rooms.keys()) == expected

    def test_exit_room_ids_resolve(self, dungeon):
        """Every exit target is a valid room id in the same dungeon."""
        for room in dungeon.rooms.values():
            for dest in room.exits.values():
                assert dest in dungeon.rooms, f"Exit {dest!r} not found in rooms"

    def test_puzzles_loaded(self, dungeon):
        assert "gate_lock" in dungeon.puzzles
        assert "crypt_riddle" in dungeon.puzzles

    def test_lock_puzzle_type(self, dungeon):
        assert isinstance(dungeon.puzzles["gate_lock"], LockPuzzle)

    def test_riddle_puzzle_type(self, dungeon):
        assert isinstance(dungeon.puzzles["crypt_riddle"], RiddlePuzzle)

    def test_entrance_items(self, dungeon):
        assert "rusty_key" in dungeon.rooms["entrance"].items

    def test_monster_data_loaded(self, dungeon):
        assert "skeleton" in dungeon._monster_data
        assert "wight_lord" in dungeon._monster_data

    def test_completed_starts_false(self, dungeon):
        assert dungeon.completed is False

    def test_missing_dungeon_raises(self):
        with pytest.raises(FileNotFoundError, match="no_dungeon"):
            Dungeon.load("no_dungeon")


# ---------------------------------------------------------------------------
# Dungeon.load — from a tmp JSON file (isolated from real data)
# ---------------------------------------------------------------------------

class TestDungeonLoadFromTmp:
    @pytest.fixture
    def minimal_dungeon_json(self, tmp_path):
        data = {
            "id": "tiny",
            "name": "Tiny Dungeon",
            "base_level": 1,
            "entry_room": "start",
            "boss_room": "start",
            "rooms": {
                "start": {
                    "name": "Start",
                    "desc": "A bare room.",
                    "exits": {},
                    "items": [],
                    "monster": None,
                    "puzzle": None,
                }
            },
        }
        path = tmp_path / "tiny.json"
        path.write_text(json.dumps(data))
        return tmp_path

    def test_loads_minimal_dungeon(self, minimal_dungeon_json, monkeypatch):
        import nullpud.dungeon as dm
        monkeypatch.setattr(dm, "DUNGEON_DIR", minimal_dungeon_json)
        d = Dungeon.load("tiny")
        assert d.id == "tiny"
        assert "start" in d.rooms


# ---------------------------------------------------------------------------
# puzzle_for
# ---------------------------------------------------------------------------

class TestPuzzleFor:
    @pytest.fixture
    def dungeon(self):
        return Dungeon.load("crypt_1")

    def test_returns_puzzle_for_room_with_puzzle(self, dungeon):
        entrance = dungeon.rooms["entrance"]
        puzzle = dungeon.puzzle_for(entrance)
        assert puzzle is not None
        assert isinstance(puzzle, LockPuzzle)

    def test_returns_none_for_room_without_puzzle(self, dungeon):
        treasure = dungeon.rooms["treasure_room"]
        assert dungeon.puzzle_for(treasure) is None

    def test_puzzle_is_same_object_as_registry(self, dungeon):
        entrance = dungeon.rooms["entrance"]
        assert dungeon.puzzle_for(entrance) is dungeon.puzzles["gate_lock"]


# ---------------------------------------------------------------------------
# spawn_monster — scaling
# ---------------------------------------------------------------------------

class TestSpawnMonster:
    @pytest.fixture
    def dungeon(self):
        return Dungeon.load("crypt_1")

    def test_base_stats_at_matching_level(self, dungeon):
        # base_level == 1, player_level == 1 → scale factor 1.0
        c = dungeon.spawn_monster("skeleton", player_level=1)
        assert c.hp == 12
        assert c.attack == 4
        assert c.defense == 1

    def test_stats_scale_up_with_level(self, dungeon):
        c1 = dungeon.spawn_monster("skeleton", player_level=1)
        c3 = dungeon.spawn_monster("skeleton", player_level=3)
        assert c3.hp > c1.hp
        assert c3.attack > c1.attack

    def test_stats_scale_linearly(self, dungeon):
        c2 = dungeon.spawn_monster("skeleton", player_level=2)
        assert c2.hp == max(1, round(12 * 2))  # base_hp=12, scale=2/1

    def test_minimum_stat_is_one(self, dungeon):
        # player_level 0 would give scale=0; floor is 1
        c = dungeon.spawn_monster("skeleton", player_level=0)
        assert c.hp >= 1
        assert c.attack >= 1
        assert c.defense >= 1

    def test_boss_phase_present_on_wight_lord(self, dungeon):
        c = dungeon.spawn_monster("wight_lord", player_level=1)
        assert c.boss_phase is not None
        assert c.boss_phase.trigger_hp_pct == 0.5


# ---------------------------------------------------------------------------
# next_dungeon
# ---------------------------------------------------------------------------

class TestNextDungeon:
    def test_crypt_leads_to_cellar(self):
        assert next_dungeon("crypt_1") == "cellar_2"

    def test_none_for_last_dungeon(self):
        assert next_dungeon(DUNGEON_ORDER[-1]) is None

    def test_none_for_unknown_dungeon(self):
        assert next_dungeon("nonexistent") is None


# ---------------------------------------------------------------------------
# Tavern progress: next level, previous dungeons
# ---------------------------------------------------------------------------

class TestDungeonChoices:
    def test_campaign_is_ten_levels(self):
        assert DUNGEON_ORDER == [
            "crypt_1",
            "cellar_2",
            "barrow_3",
            "sewer_4",
            "ossuary_5",
            "mine_6",
            "chapel_7",
            "vault_8",
            "spire_9",
            "throne_10",
        ]

    def test_fresh_character_gets_only_the_first(self):
        choice = dungeon_choices(None)
        assert choice.previous == ()
        assert choice.next_id == "crypt_1"
        assert choice.allowed() == ("crypt_1",)

    def test_unknown_clear_does_not_unlock_the_campaign(self):
        choice = dungeon_choices("missing")
        assert choice.allowed() == ("crypt_1",)

    def test_cleared_dungeons_stay_open_with_the_next(self):
        choice = dungeon_choices("cellar_2")
        assert choice.previous == ("crypt_1", "cellar_2")
        assert choice.next_id == "barrow_3"
        assert choice.allowed() == ("crypt_1", "cellar_2", "barrow_3")

    def test_final_clear_has_no_next_level(self):
        choice = dungeon_choices("throne_10")
        assert choice.next_id is None
        assert choice.previous == tuple(DUNGEON_ORDER)
        assert "crypt_1" in choice.allowed()

    def test_replay_does_not_rewind_progress(self):
        assert record_completion("ossuary_5", "cellar_2") == "ossuary_5"
        assert record_completion("crypt_1", "cellar_2") == "cellar_2"
        assert record_completion(None, "crypt_1") == "crypt_1"

    def test_crypt_title(self):
        name, level = dungeon_info("crypt_1")
        assert name == "The Weeping Crypt"
        assert level == 1


# ---------------------------------------------------------------------------
# Every shipped dungeon loads and can be solved from its own rooms
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("dungeon_id", DUNGEON_ORDER)
def test_campaign_dungeon(dungeon_id):
    dungeon = Dungeon.load(dungeon_id)
    assert dungeon.id == dungeon_id
    assert dungeon.base_level == DUNGEON_ORDER.index(dungeon_id) + 1
    assert dungeon.entry_room_id in dungeon.rooms
    assert dungeon.boss_room_id in dungeon.rooms
    assert dungeon.boss_room.monster_id

    items = load_all_items()
    room_items = {iid for room in dungeon.rooms.values() for iid in room.items}

    for room in dungeon.rooms.values():
        for dest in room.exits.values():
            assert dest in dungeon.rooms, f"{dungeon_id}: exit {dest!r} missing"
        if room.monster_id:
            assert room.monster_id in dungeon._monster_data
        if room.puzzle_id:
            assert room.puzzle_id in dungeon.puzzles
            puzzle = dungeon.puzzles[room.puzzle_id]
            assert puzzle.blocks_exit in room.exits

    for puzzle in dungeon.puzzles.values():
        if isinstance(puzzle, LockPuzzle):
            needed = [puzzle.key_item]
        elif isinstance(puzzle, LeverPuzzle):
            needed = list(puzzle.sequence)
        elif isinstance(puzzle, CombinationPuzzle):
            needed = list(puzzle.items)
        else:
            needed = []
        for iid in needed:
            assert iid in items, f"{dungeon_id}: missing item {iid}"
            assert items[iid].type in ("key", "quest")
            assert iid in room_items, f"{dungeon_id}: {iid} is not placed in a room"

    for iid in room_items:
        assert iid in items
    for data in dungeon._monster_data.values():
        for entry in data.get("loot", []):
            assert entry["item"] in items
