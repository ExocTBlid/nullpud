"""Combatant — shared turn-based fight logic for player and monsters.

Both the player and a loaded monster are wrapped in a Combatant before a
fight starts. run_loop.py drives the turn loop; this module only resolves
individual attacks and tracks HP / phase transitions.

Damage formula
--------------
    raw    = max(1, attacker.attack - defender.defense) + randint(0, 2)
    damage = raw   (no crits or misses for now — easy to add later)

Boss phase
----------
Triggered once when HP drops below trigger_hp_pct * max_hp.
Adds attack_bonus permanently and prints the phase message.
The phase fires at most once per fight.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BossPhase:
    trigger_hp_pct: float
    message: str
    attack_bonus: int
    triggered: bool = False


@dataclass
class Combatant:
    name: str
    hp: int
    max_hp: int
    attack: int
    defense: int
    xp: int = 0
    # Loot entries: [{"item": item_id, "chance": 0.0-1.0}]
    loot_table: list[dict] = field(default_factory=list)
    boss_phase: Optional[BossPhase] = None

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    @property
    def is_alive(self) -> bool:
        return self.hp > 0

    def take_damage(self, amount: int) -> None:
        self.hp = max(0, self.hp - amount)

    # ------------------------------------------------------------------
    # Attack resolution
    # ------------------------------------------------------------------

    def resolve_attack(self, defender: "Combatant") -> tuple[int, str]:
        """Deal damage to defender. Returns (damage_dealt, narrative).

        Also checks and fires boss phase on the *defender* if applicable.
        """
        raw = max(1, self.attack - defender.defense) + random.randint(0, 2)
        defender.take_damage(raw)
        msg = f"{self.name} hits {defender.name} for {raw} damage."

        # Check if this hit triggered the defender's boss phase
        phase_msg = defender._check_boss_phase()
        if phase_msg:
            msg = msg + "\n" + phase_msg

        return raw, msg

    def _check_boss_phase(self) -> str:
        """Fire boss phase if threshold crossed for the first time."""
        if (
            self.boss_phase
            and not self.boss_phase.triggered
            and self.hp <= self.max_hp * self.boss_phase.trigger_hp_pct
        ):
            self.boss_phase.triggered = True
            self.attack += self.boss_phase.attack_bonus
            return self.boss_phase.message
        return ""

    # ------------------------------------------------------------------
    # Loot
    # ------------------------------------------------------------------

    def roll_loot(self) -> list[str]:
        """Roll loot table. Returns list of item ids dropped."""
        dropped: list[str] = []
        for entry in self.loot_table:
            if random.random() < entry["chance"]:
                dropped.append(entry["item"])
        return dropped

    # ------------------------------------------------------------------
    # Factory helpers
    # ------------------------------------------------------------------

    @classmethod
    def from_monster_dict(cls, data: dict, scaled_hp: int, scaled_attack: int, scaled_defense: int) -> "Combatant":
        """Build a Combatant from a monster JSON dict with pre-scaled stats."""
        bp = None
        if "boss_phase" in data:
            bpd = data["boss_phase"]
            bp = BossPhase(
                trigger_hp_pct=bpd["trigger_hp_pct"],
                message=bpd["message"],
                attack_bonus=bpd["attack_bonus"],
            )
        return cls(
            name=data["name"],
            hp=scaled_hp,
            max_hp=scaled_hp,
            attack=scaled_attack,
            defense=scaled_defense,
            xp=data.get("xp", 0),
            loot_table=data.get("loot", []),
            boss_phase=bp,
        )

    @classmethod
    def from_player(cls, player) -> "Combatant":
        """Wrap a Player as a Combatant for the fight loop.

        Imports Player inline to avoid circular dependency.
        """
        from nullpud.item import _registry as item_reg  # lazy import

        return cls(
            name=player.name,
            hp=player.current_hp,
            max_hp=player.max_hp,
            attack=player.attack(item_reg),
            defense=player.defense(item_reg),
        )
