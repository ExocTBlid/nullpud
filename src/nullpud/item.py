"""Item definitions. Loaded from data/items/<id>.json.

Items are immutable value objects — the same definition can appear in
multiple rooms. Runtime inventory is tracked as lists of item ids on
Player and Room; the item registry maps ids to Item instances.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

# Valid item type literals
ItemType = Literal["weapon", "armor", "key", "consumable", "quest"]

# Global registry populated by load_all_items()
_registry: dict[str, "Item"] = {}

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "items"


@dataclass(frozen=True)
class Item:
    id: str
    name: str
    desc: str
    type: ItemType
    # Flat stat bonuses applied when equipped (weapon/armor only)
    stat_bonus: dict[str, int] = field(default_factory=dict)
    # One-time effect when used (consumable only); e.g. {"heal": 10}
    effect: dict[str, int] = field(default_factory=dict)

    def describe(self) -> str:
        """Return a one-line description suitable for inventory display."""
        bonus_parts = [f"+{v} {k}" for k, v in self.stat_bonus.items()]
        suffix = f"  [{', '.join(bonus_parts)}]" if bonus_parts else ""
        return f"{self.name}{suffix} — {self.desc}"


def _from_dict(data: dict) -> Item:
    return Item(
        id=data["id"],
        name=data["name"],
        desc=data["desc"],
        type=data["type"],
        stat_bonus=data.get("stat_bonus", {}),
        effect=data.get("effect", {}),
    )


def load_item(item_id: str) -> Item:
    """Load a single item by id from data/items/<id>.json.

    Returns a cached instance if already loaded.
    """
    if item_id in _registry:
        return _registry[item_id]
    path = DATA_DIR / f"{item_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Item data not found: {path}")
    with path.open() as f:
        item = _from_dict(json.load(f))
    _registry[item_id] = item
    return item


def load_all_items() -> dict[str, Item]:
    """Load every item json file in the data/items directory.

    Populates and returns the global registry.
    """
    if not DATA_DIR.exists():
        return {}
    for path in DATA_DIR.glob("*.json"):
        item_id = path.stem
        if item_id not in _registry:
            with path.open() as f:
                _registry[item_id] = _from_dict(json.load(f))
    return dict(_registry)


def get_item(item_id: str) -> Item:
    """Look up an already-loaded item. Raises KeyError if not found."""
    if item_id not in _registry:
        # Attempt a lazy load before failing
        load_item(item_id)
    return _registry[item_id]
