"""Tests for nullpud.item — loading, registry, and Item behaviour."""

import pytest

import nullpud.item as item_module
from nullpud.item import Item, get_item, load_all_items, load_item


@pytest.fixture(autouse=True)
def clear_registry():
    """Isolate each test from cached registry state."""
    item_module._registry.clear()
    yield
    item_module._registry.clear()


# ---------------------------------------------------------------------------
# load_item
# ---------------------------------------------------------------------------

class TestLoadItem:
    def test_loads_known_item(self):
        item = load_item("rusty_key")
        assert item.id == "rusty_key"
        assert item.name == "Rusty Key"
        assert item.type == "key"

    def test_returns_cached_instance(self):
        a = load_item("rusty_key")
        b = load_item("rusty_key")
        assert a is b

    def test_missing_item_raises(self):
        with pytest.raises(FileNotFoundError, match="no_such_item"):
            load_item("no_such_item")

    def test_weapon_has_stat_bonus(self):
        item = load_item("iron_sword")
        assert item.type == "weapon"
        assert item.stat_bonus.get("attack", 0) > 0

    def test_consumable_has_effect(self):
        item = load_item("health_potion")
        assert item.type == "consumable"
        assert item.effect.get("heal", 0) > 0

    def test_key_has_no_bonus_or_effect(self):
        item = load_item("rusty_key")
        assert item.stat_bonus == {}
        assert item.effect == {}


# ---------------------------------------------------------------------------
# load_all_items
# ---------------------------------------------------------------------------

class TestLoadAllItems:
    def test_returns_all_items(self):
        registry = load_all_items()
        assert "rusty_key" in registry
        assert "iron_sword" in registry
        assert "health_potion" in registry
        assert "bone_shard" in registry

    def test_populates_registry(self):
        load_all_items()
        assert "rusty_key" in item_module._registry

    def test_idempotent(self):
        first = load_all_items()
        second = load_all_items()
        assert set(first.keys()) == set(second.keys())


# ---------------------------------------------------------------------------
# get_item
# ---------------------------------------------------------------------------

class TestGetItem:
    def test_lazy_loads_missing(self):
        # registry is empty; get_item should trigger a load
        item = get_item("iron_sword")
        assert item.id == "iron_sword"

    def test_raises_for_unknown(self):
        with pytest.raises(FileNotFoundError):
            get_item("ghost_item")


# ---------------------------------------------------------------------------
# Item.describe
# ---------------------------------------------------------------------------

class TestItemDescribe:
    def test_weapon_includes_bonus(self):
        item = load_item("iron_sword")
        desc = item.describe()
        assert "iron sword" in desc.lower()
        assert "+3 attack" in desc.lower()

    def test_key_no_bonus_suffix(self):
        item = load_item("rusty_key")
        desc = item.describe()
        assert "[" not in desc  # no bonus bracket

    def test_consumable_no_bonus_suffix(self):
        item = load_item("health_potion")
        desc = item.describe()
        assert "[" not in desc
