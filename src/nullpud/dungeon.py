"""Dungeon — the room graph for one dungeon run.

Loaded from data/dungeons/<id>.json. After loading, dungeon.py:
  - instantiates Room objects
  - wires exit strings (resolves to room ids — run_loop resolves to objects)
  - instantiates Puzzle objects and attaches them to rooms
  - loads monster JSON and scales stats to player level
  - tracks completion

Monster stat scaling
--------------------
A monster's base stats are defined at the dungeon's base_level.
When the player's level differs, stats scale linearly:

    scaled = max(1, round(base * (player_level / base_level)))

This keeps early dungeons easy for a high-level player and makes
returning to old content trivially winnable — as intended.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from nullpud.combatant import Combatant
from nullpud.puzzle import Puzzle, puzzle_from_dict
from nullpud.room import Room

DUNGEON_DIR = Path(__file__).parent.parent.parent / "data" / "dungeons"
MONSTER_DIR = Path(__file__).parent.parent.parent / "data" / "monsters"

# Ids of available dungeons in progression order (add new ones here)
DUNGEON_ORDER: list[str] = ["crypt_1"]


@dataclass
class Dungeon:
    id: str
    name: str
    base_level: int
    entry_room_id: str
    boss_room_id: str
    rooms: dict[str, Room]
    # puzzle id → Puzzle (shared reference; Room.puzzle_id points here)
    puzzles: dict[str, Puzzle]
    # monster id → raw JSON dict (scaled at spawn time)
    _monster_data: dict[str, dict] = field(default_factory=dict, repr=False)
    completed: bool = False

    # ------------------------------------------------------------------
    # Room helpers
    # ------------------------------------------------------------------

    @property
    def entry_room(self) -> Room:
        return self.rooms[self.entry_room_id]

    @property
    def boss_room(self) -> Room:
        return self.rooms[self.boss_room_id]

    def get_room(self, room_id: str) -> Optional[Room]:
        return self.rooms.get(room_id)

    def puzzle_for(self, room: Room) -> Optional[Puzzle]:
        """Return the Puzzle attached to this room, or None."""
        if room.puzzle_id:
            return self.puzzles.get(room.puzzle_id)
        return None

    # ------------------------------------------------------------------
    # Monster spawning
    # ------------------------------------------------------------------

    def spawn_monster(self, monster_id: str, player_level: int) -> Combatant:
        """Return a scaled Combatant for monster_id."""
        data = self._monster_data[monster_id]
        scale = player_level / max(1, self.base_level)
        hp = max(1, round(data["base_hp"] * scale))
        atk = max(1, round(data["base_attack"] * scale))
        dfn = max(1, round(data["base_defense"] * scale))
        return Combatant.from_monster_dict(data, hp, atk, dfn)

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def load(cls, dungeon_id: str) -> "Dungeon":
        """Load a dungeon from data/dungeons/<dungeon_id>.json."""
        path = DUNGEON_DIR / f"{dungeon_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Dungeon data not found: {path}")
        with path.open() as f:
            data = json.load(f)

        # Build puzzles first (rooms reference them by id)
        puzzles: dict[str, Puzzle] = {}
        for pid, pdata in data.get("puzzles", {}).items():
            puzzles[pid] = puzzle_from_dict(pid, pdata)

        # Build rooms
        rooms: dict[str, Room] = {}
        for room_id, rdata in data["rooms"].items():
            rooms[room_id] = Room(
                id=room_id,
                name=rdata["name"],
                desc=rdata["desc"],
                exits=dict(rdata.get("exits", {})),
                items=list(rdata.get("items", [])),
                monster_id=rdata.get("monster"),
                puzzle_id=rdata.get("puzzle"),
            )

        # Load monster data for every monster referenced in the dungeon
        monster_data: dict[str, dict] = {}
        for room in rooms.values():
            if room.monster_id and room.monster_id not in monster_data:
                monster_data[room.monster_id] = _load_monster_json(room.monster_id)

        return cls(
            id=data["id"],
            name=data["name"],
            base_level=data["base_level"],
            entry_room_id=data["entry_room"],
            boss_room_id=data["boss_room"],
            rooms=rooms,
            puzzles=puzzles,
            _monster_data=monster_data,
        )


def _load_monster_json(monster_id: str) -> dict:
    path = MONSTER_DIR / f"{monster_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Monster data not found: {path}")
    with path.open() as f:
        return json.load(f)


def next_dungeon(current_id: str) -> Optional[str]:
    """Return the id of the next dungeon after current_id, or None if it's the last."""
    try:
        idx = DUNGEON_ORDER.index(current_id)
        return DUNGEON_ORDER[idx + 1]
    except (ValueError, IndexError):
        return None
