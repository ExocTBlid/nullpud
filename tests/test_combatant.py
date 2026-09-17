"""Tests for nullpud.combatant — attacks, boss phase, loot, factories."""

import pytest

from nullpud.combatant import BossPhase, Combatant


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_attacker(attack=10, defense=0, hp=50) -> Combatant:
    return Combatant(name="Attacker", hp=hp, max_hp=hp, attack=attack, defense=defense)


def make_defender(defense=2, hp=30) -> Combatant:
    return Combatant(name="Defender", hp=hp, max_hp=hp, attack=5, defense=defense)


# ---------------------------------------------------------------------------
# is_alive / take_damage
# ---------------------------------------------------------------------------

class TestState:
    def test_alive_when_hp_positive(self):
        c = make_attacker(hp=1)
        assert c.is_alive is True

    def test_dead_at_zero_hp(self):
        c = make_attacker(hp=0)
        assert c.is_alive is False

    def test_take_damage_reduces_hp(self):
        c = make_defender(hp=20)
        c.take_damage(7)
        assert c.hp == 13

    def test_take_damage_floors_at_zero(self):
        c = make_defender(hp=5)
        c.take_damage(100)
        assert c.hp == 0


# ---------------------------------------------------------------------------
# resolve_attack — damage formula
# ---------------------------------------------------------------------------

class TestResolveAttack:
    def test_damage_is_positive(self):
        atk = make_attacker(attack=10, defense=0)
        dfn = make_defender(defense=2)
        damage, _ = atk.resolve_attack(dfn)
        assert damage >= 1

    def test_minimum_damage_is_one(self):
        # attacker weaker than defender: max(1, 0) + rand(0,2) → at least 1
        atk = make_attacker(attack=1, defense=0)
        dfn = make_defender(defense=50)
        damage, _ = atk.resolve_attack(dfn)
        assert damage >= 1

    def test_defender_hp_reduced(self):
        atk = make_attacker(attack=10)
        dfn = make_defender(defense=2, hp=30)
        damage, _ = atk.resolve_attack(dfn)
        assert dfn.hp == 30 - damage

    def test_narrative_mentions_names(self):
        atk = make_attacker(attack=10)
        dfn = make_defender()
        _, msg = atk.resolve_attack(dfn)
        assert "Attacker" in msg
        assert "Defender" in msg

    def test_damage_within_expected_range(self):
        # attack=10, defense=2 → raw = max(1, 8) + randint(0,2) → 8–10
        atk = make_attacker(attack=10)
        dfn = make_defender(defense=2, hp=100)
        for _ in range(50):
            damage, _ = atk.resolve_attack(dfn)
            assert 8 <= damage <= 10
            dfn.hp = 100  # reset between checks


# ---------------------------------------------------------------------------
# Boss phase
# ---------------------------------------------------------------------------

class TestBossPhase:
    def _boss_with_phase(self, trigger=0.5, bonus=3) -> Combatant:
        return Combatant(
            name="Boss", hp=100, max_hp=100, attack=10, defense=2,
            boss_phase=BossPhase(
                trigger_hp_pct=trigger,
                message="PHASE TWO!",
                attack_bonus=bonus,
            ),
        )

    def test_phase_fires_below_threshold(self):
        boss = self._boss_with_phase(trigger=0.5)
        boss.hp = 49  # below 50%
        msg = boss._check_boss_phase()
        assert msg == "PHASE TWO!"

    def test_phase_adds_attack_bonus(self):
        boss = self._boss_with_phase(trigger=0.5, bonus=5)
        boss.hp = 49
        boss._check_boss_phase()
        assert boss.attack == 15  # 10 + 5

    def test_phase_fires_only_once(self):
        boss = self._boss_with_phase()
        boss.hp = 49
        boss._check_boss_phase()
        boss.hp = 10  # still below threshold
        msg = boss._check_boss_phase()
        assert msg == ""  # already triggered

    def test_phase_not_fired_above_threshold(self):
        boss = self._boss_with_phase(trigger=0.5)
        boss.hp = 60  # above 50%
        msg = boss._check_boss_phase()
        assert msg == ""
        assert boss.boss_phase.triggered is False

    def test_phase_message_in_attack_narrative(self):
        # Phase fires mid-attack when defender is the boss
        atk = make_attacker(attack=100)
        boss = self._boss_with_phase(trigger=0.5)
        # Arrange: boss HP is just above threshold, attack will push below
        boss.hp = 51
        boss.max_hp = 100
        _, msg = atk.resolve_attack(boss)
        if boss.hp <= 50:
            assert "PHASE TWO!" in msg

    def test_no_phase_when_none(self):
        c = make_defender()
        msg = c._check_boss_phase()
        assert msg == ""


# ---------------------------------------------------------------------------
# roll_loot
# ---------------------------------------------------------------------------

class TestRollLoot:
    def test_always_drops_at_1_0(self):
        c = Combatant(
            name="C", hp=1, max_hp=1, attack=1, defense=0,
            loot_table=[{"item": "gold_coin", "chance": 1.0}],
        )
        for _ in range(20):
            assert "gold_coin" in c.roll_loot()

    def test_never_drops_at_0_0(self):
        c = Combatant(
            name="C", hp=1, max_hp=1, attack=1, defense=0,
            loot_table=[{"item": "diamond", "chance": 0.0}],
        )
        for _ in range(20):
            assert "diamond" not in c.roll_loot()

    def test_empty_table_returns_empty(self):
        c = make_attacker()
        assert c.roll_loot() == []

    def test_multiple_items_rolled_independently(self):
        c = Combatant(
            name="C", hp=1, max_hp=1, attack=1, defense=0,
            loot_table=[
                {"item": "a", "chance": 1.0},
                {"item": "b", "chance": 1.0},
            ],
        )
        loot = c.roll_loot()
        assert "a" in loot
        assert "b" in loot


# ---------------------------------------------------------------------------
# from_monster_dict factory
# ---------------------------------------------------------------------------

class TestFromMonsterDict:
    _DATA = {
        "name": "Goblin",
        "base_hp": 10,
        "base_attack": 3,
        "base_defense": 1,
        "xp": 15,
        "loot": [{"item": "copper_coin", "chance": 0.9}],
    }

    def test_basic_fields(self):
        c = Combatant.from_monster_dict(self._DATA, 20, 6, 2)
        assert c.name == "Goblin"
        assert c.hp == 20
        assert c.max_hp == 20
        assert c.attack == 6
        assert c.defense == 2
        assert c.xp == 15

    def test_loot_table_copied(self):
        c = Combatant.from_monster_dict(self._DATA, 10, 3, 1)
        assert c.loot_table[0]["item"] == "copper_coin"

    def test_boss_phase_parsed(self):
        data = {**self._DATA, "boss_phase": {
            "trigger_hp_pct": 0.4,
            "message": "Enrage!",
            "attack_bonus": 2,
        }}
        c = Combatant.from_monster_dict(data, 100, 10, 3)
        assert c.boss_phase is not None
        assert c.boss_phase.trigger_hp_pct == 0.4
        assert c.boss_phase.attack_bonus == 2

    def test_no_boss_phase_when_absent(self):
        c = Combatant.from_monster_dict(self._DATA, 10, 3, 1)
        assert c.boss_phase is None
