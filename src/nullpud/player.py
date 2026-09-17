"""Player — owns everything that persists across dungeons.

Stat scaling on level-up:
    max_hp   += 5
    attack   += 1 per 2 levels (every even level)
    defense  += 1 per 3 levels (every level divisible by 3)

XP threshold for level N:  N * 100
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

SAVES_DIR = Path(__file__).parent.parent.parent / "saves"

# Base stats at level 1 before any equipment
_BASE_HP = 20
_BASE_ATTACK = 5
_BASE_DEFENSE = 2

# XP needed to reach level N+1
def xp_to_next(level: int) -> int:
    return level * 100


@dataclass
class Player:
    name: str
    level: int = 1
    xp: int = 0
    max_hp: int = _BASE_HP
    current_hp: int = _BASE_HP
    base_attack: int = _BASE_ATTACK
    base_defense: int = _BASE_DEFENSE
    # Item ids in the player's bag
    inventory: list[str] = field(default_factory=list)
    equipped: dict[str, Optional[str]] = field(
        default_factory=lambda: {"weapon": None, "armor": None}
    )
    last_dungeon: Optional[str] = None

    # ------------------------------------------------------------------
    # Derived stats (equipment bonuses applied on top of base)
    # ------------------------------------------------------------------

    def attack(self, item_registry: dict) -> int:
        """Effective attack including equipped weapon bonus."""
        bonus = 0
        weapon_id = self.equipped.get("weapon")
        if weapon_id and weapon_id in item_registry:
            bonus = item_registry[weapon_id].stat_bonus.get("attack", 0)
        return self.base_attack + bonus

    def defense(self, item_registry: dict) -> int:
        """Effective defense including equipped armor bonus."""
        bonus = 0
        armor_id = self.equipped.get("armor")
        if armor_id and armor_id in item_registry:
            bonus = item_registry[armor_id].stat_bonus.get("defense", 0)
        return self.base_defense + bonus

    # ------------------------------------------------------------------
    # HP helpers
    # ------------------------------------------------------------------

    @property
    def is_alive(self) -> bool:
        return self.current_hp > 0

    def heal(self, amount: int) -> int:
        """Restore HP up to max. Returns actual HP recovered."""
        before = self.current_hp
        self.current_hp = min(self.max_hp, self.current_hp + amount)
        return self.current_hp - before

    def take_damage(self, amount: int) -> None:
        self.current_hp = max(0, self.current_hp - amount)

    # ------------------------------------------------------------------
    # Inventory
    # ------------------------------------------------------------------

    def add_item(self, item_id: str) -> None:
        self.inventory.append(item_id)

    def remove_item(self, item_id: str) -> bool:
        """Remove one copy of item_id. Returns True if found."""
        try:
            self.inventory.remove(item_id)
            return True
        except ValueError:
            return False

    def has_item(self, item_id: str) -> bool:
        return item_id in self.inventory

    def equip(self, item_id: str, slot: str) -> None:
        """Equip an item into 'weapon' or 'armor' slot."""
        self.equipped[slot] = item_id

    def unequip(self, slot: str) -> None:
        self.equipped[slot] = None

    # ------------------------------------------------------------------
    # XP and levelling
    # ------------------------------------------------------------------

    def award_xp(self, amount: int) -> list[str]:
        """Add XP and process any level-ups. Returns list of level-up messages."""
        self.xp += amount
        messages: list[str] = []
        while self.xp >= xp_to_next(self.level):
            self.xp -= xp_to_next(self.level)
            self._level_up()
            messages.append(
                f"Level {self.level}! "
                f"HP {self.max_hp}  ATK {self.base_attack}  DEF {self.base_defense}"
            )
        return messages

    def _level_up(self) -> None:
        self.level += 1
        self.max_hp += 5
        self.current_hp = min(self.current_hp + 5, self.max_hp)  # partial heal on level-up
        if self.level % 2 == 0:
            self.base_attack += 1
        if self.level % 3 == 0:
            self.base_defense += 1

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "level": self.level,
            "xp": self.xp,
            "max_hp": self.max_hp,
            "current_hp": self.current_hp,
            "base_attack": self.base_attack,
            "base_defense": self.base_defense,
            "inventory": list(self.inventory),
            "equipped": dict(self.equipped),
            "last_dungeon": self.last_dungeon,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Player":
        p = cls(name=data["name"])
        p.level = data["level"]
        p.xp = data["xp"]
        p.max_hp = data["max_hp"]
        p.current_hp = data["current_hp"]
        p.base_attack = data["base_attack"]
        p.base_defense = data["base_defense"]
        p.inventory = data["inventory"]
        p.equipped = data["equipped"]
        p.last_dungeon = data.get("last_dungeon")
        return p

    def save(self) -> Path:
        """Write save file. Returns the path written."""
        SAVES_DIR.mkdir(parents=True, exist_ok=True)
        path = SAVES_DIR / f"{self.name.lower()}.json"
        with path.open("w") as f:
            json.dump(self.to_dict(), f, indent=2)
        return path

    @classmethod
    def load(cls, name: str) -> Optional["Player"]:
        """Load from saves/<name>.json. Returns None if not found."""
        path = SAVES_DIR / f"{name.lower()}.json"
        if not path.exists():
            return None
        with path.open() as f:
            return cls.from_dict(json.load(f))

    @classmethod
    def list_saves(cls) -> list[str]:
        """Return player names that have existing save files."""
        SAVES_DIR.mkdir(parents=True, exist_ok=True)
        return [p.stem for p in SAVES_DIR.glob("*.json")]
