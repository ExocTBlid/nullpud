"""Tests for nullpud.player — stats, inventory, XP, save/load."""

import pytest

from nullpud.item import Item
from nullpud.player import Player, _BASE_ATTACK, _BASE_DEFENSE, _BASE_HP, xp_to_next


# Minimal fake item registry for stat tests
_WEAPON = Item(id="test_sword", name="Test Sword", desc="", type="weapon",
               stat_bonus={"attack": 4}, effect={})
_ARMOR = Item(id="test_shield", name="Test Shield", desc="", type="armor",
              stat_bonus={"defense": 3}, effect={})
_FAKE_REGISTRY = {"test_sword": _WEAPON, "test_shield": _ARMOR}


@pytest.fixture
def player():
    return Player(name="Tester")


# ---------------------------------------------------------------------------
# Base stats
# ---------------------------------------------------------------------------

class TestBaseStats:
    def test_initial_hp(self, player):
        assert player.max_hp == _BASE_HP
        assert player.current_hp == _BASE_HP

    def test_attack_no_equipment(self, player):
        assert player.attack({}) == _BASE_ATTACK

    def test_defense_no_equipment(self, player):
        assert player.defense({}) == _BASE_DEFENSE

    def test_attack_with_weapon(self, player):
        player.equip("test_sword", "weapon")
        assert player.attack(_FAKE_REGISTRY) == _BASE_ATTACK + 4

    def test_defense_with_armor(self, player):
        player.equip("test_shield", "armor")
        assert player.defense(_FAKE_REGISTRY) == _BASE_DEFENSE + 3

    def test_unequip_removes_bonus(self, player):
        player.equip("test_sword", "weapon")
        player.unequip("weapon")
        assert player.attack(_FAKE_REGISTRY) == _BASE_ATTACK


# ---------------------------------------------------------------------------
# HP helpers
# ---------------------------------------------------------------------------

class TestHP:
    def test_take_damage_reduces_hp(self, player):
        player.take_damage(5)
        assert player.current_hp == _BASE_HP - 5

    def test_take_damage_floors_at_zero(self, player):
        player.take_damage(9999)
        assert player.current_hp == 0

    def test_is_alive_true_when_hp_positive(self, player):
        assert player.is_alive is True

    def test_is_alive_false_at_zero_hp(self, player):
        player.take_damage(9999)
        assert player.is_alive is False

    def test_heal_restores_hp(self, player):
        player.take_damage(10)
        recovered = player.heal(5)
        assert recovered == 5
        assert player.current_hp == _BASE_HP - 5

    def test_heal_caps_at_max(self, player):
        player.take_damage(3)
        recovered = player.heal(100)
        assert player.current_hp == player.max_hp
        assert recovered == 3

    def test_heal_returns_zero_when_full(self, player):
        recovered = player.heal(10)
        assert recovered == 0


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------

class TestInventory:
    def test_add_item(self, player):
        player.add_item("rusty_key")
        assert player.has_item("rusty_key")

    def test_remove_item_returns_true(self, player):
        player.add_item("rusty_key")
        assert player.remove_item("rusty_key") is True
        assert not player.has_item("rusty_key")

    def test_remove_missing_returns_false(self, player):
        assert player.remove_item("ghost") is False

    def test_duplicate_items_allowed(self, player):
        player.add_item("health_potion")
        player.add_item("health_potion")
        assert player.inventory.count("health_potion") == 2

    def test_remove_only_one_copy(self, player):
        player.add_item("health_potion")
        player.add_item("health_potion")
        player.remove_item("health_potion")
        assert player.inventory.count("health_potion") == 1


# ---------------------------------------------------------------------------
# XP and levelling
# ---------------------------------------------------------------------------

class TestXPAndLevelUp:
    def test_xp_threshold(self):
        assert xp_to_next(1) == 100
        assert xp_to_next(2) == 200
        assert xp_to_next(5) == 500

    def test_no_level_up_below_threshold(self, player):
        msgs = player.award_xp(50)
        assert msgs == []
        assert player.level == 1

    def test_level_up_at_threshold(self, player):
        msgs = player.award_xp(100)
        assert len(msgs) == 1
        assert player.level == 2

    def test_xp_carries_over(self, player):
        player.award_xp(150)
        # spent 100 to level up, 50 remaining
        assert player.xp == 50

    def test_multiple_level_ups_at_once(self, player):
        # 100 + 200 = 300 XP needed for levels 2 and 3
        msgs = player.award_xp(300)
        assert player.level == 3
        assert len(msgs) == 2

    def test_hp_increases_on_level_up(self, player):
        player.award_xp(100)
        assert player.max_hp == _BASE_HP + 5

    def test_attack_increases_every_even_level(self, player):
        # Level 2: attack +1
        player.award_xp(100)
        assert player.level == 2
        assert player.base_attack == _BASE_ATTACK + 1

    def test_attack_no_increase_on_odd_level(self, player):
        # Level 3 is odd — no attack bonus
        player.award_xp(300)
        assert player.level == 3
        assert player.base_attack == _BASE_ATTACK + 1  # only from level 2

    def test_defense_increases_every_third_level(self, player):
        # Level 3: defense +1
        player.award_xp(300)
        assert player.level == 3
        assert player.base_defense == _BASE_DEFENSE + 1

    def test_partial_heal_on_level_up(self, player):
        player.take_damage(10)
        hp_before = player.current_hp
        player.award_xp(100)
        assert player.current_hp > hp_before


# ---------------------------------------------------------------------------
# Save / load round-trip
# ---------------------------------------------------------------------------

class TestSaveLoad:
    def test_round_trip(self, player, tmp_path, monkeypatch):
        import nullpud.player as pm
        monkeypatch.setattr(pm, "SAVES_DIR", tmp_path)

        player.add_item("iron_sword")
        player.equip("iron_sword", "weapon")
        player.award_xp(150)
        player.last_dungeon = "crypt_1"
        player.save()

        loaded = Player.load("Tester")
        assert loaded is not None
        assert loaded.name == player.name
        assert loaded.level == player.level
        assert loaded.xp == player.xp
        assert loaded.max_hp == player.max_hp
        assert loaded.inventory == player.inventory
        assert loaded.equipped == player.equipped
        assert loaded.last_dungeon == player.last_dungeon

    def test_load_missing_returns_none(self, tmp_path, monkeypatch):
        import nullpud.player as pm
        monkeypatch.setattr(pm, "SAVES_DIR", tmp_path)
        assert Player.load("nobody") is None

    def test_list_saves(self, player, tmp_path, monkeypatch):
        import nullpud.player as pm
        monkeypatch.setattr(pm, "SAVES_DIR", tmp_path)
        player.save()
        saves = Player.list_saves()
        assert "tester" in saves
