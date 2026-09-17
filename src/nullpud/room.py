"""Room — a single node in the dungeon graph.

Rooms hold transient state: which items are still present, whether the
monster has been defeated, and whether any attached puzzle is solved.
run_loop.py calls room.render() to print the current state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

# Compass directions recognised by the engine
DIRECTIONS = {"north", "south", "east", "west"}


@dataclass
class Room:
    id: str
    name: str
    desc: str
    # direction → room id (not yet resolved to Room objects)
    exits: dict[str, str] = field(default_factory=dict)
    # Item ids currently present in this room
    items: list[str] = field(default_factory=list)
    # Monster id; None once defeated
    monster_id: Optional[str] = None
    # Puzzle id attached to this room (key into Dungeon.puzzles)
    puzzle_id: Optional[str] = None
    visited: bool = False

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render(self, item_registry: dict, puzzle=None) -> None:
        """Print the full room description using Rich."""
        body = Text()
        body.append(self.desc + "\n")

        # Items on the floor
        if self.items:
            names = [item_registry[i].name if i in item_registry else i for i in self.items]
            body.append("\nYou see: ", style="bold yellow")
            body.append(", ".join(names) + ".")

        # Monster present
        if self.monster_id:
            body.append("\n\n⚔  ", style="bold red")
            body.append(f"A {self.monster_id.replace('_', ' ')} is here!", style="bold red")

        # Puzzle hint
        if puzzle and not puzzle.solved:
            body.append(f"\n\n{puzzle.desc}", style="italic cyan")

        # Exits
        exit_list = ", ".join(sorted(self.exits.keys()))
        body.append(f"\n\nExits: {exit_list}", style="dim")

        console.print(Panel(body, title=f"[bold]{self.name}[/bold]", border_style="blue"))

    def render_brief(self) -> None:
        """Print a one-line reminder (used after combat / puzzle resolve)."""
        exit_list = ", ".join(sorted(self.exits.keys()))
        console.print(f"[dim][ {self.name} | exits: {exit_list} ][/dim]")

    # ------------------------------------------------------------------
    # Mutation helpers
    # ------------------------------------------------------------------

    def take_item(self, item_id: str) -> bool:
        """Remove item_id from the room. Returns True if it was present."""
        if item_id in self.items:
            self.items.remove(item_id)
            return True
        return False

    def drop_item(self, item_id: str) -> None:
        self.items.append(item_id)

    def clear_monster(self) -> None:
        self.monster_id = None

    # ------------------------------------------------------------------
    # Exit queries
    # ------------------------------------------------------------------

    def available_exits(self, puzzle=None) -> dict[str, str]:
        """Return exits dict with puzzle-blocked direction removed if unsolved."""
        exits = dict(self.exits)
        if puzzle and not puzzle.solved and puzzle.blocks_exit in exits:
            exits.pop(puzzle.blocks_exit)
        return exits

    def monster_blocks(self) -> bool:
        """True when a live monster is present (blocks all movement)."""
        return self.monster_id is not None
