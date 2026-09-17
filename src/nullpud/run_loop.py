"""run_loop — the game loop.

This is the only module that registers adventurelib @when handlers and
calls adventurelib.start(). It owns all Rich output and drives the
combat sub-loop.

Contexts
--------
None          — exploration (default)
'combat'      — inside a fight; only attack / use potion / flee are valid
'hub'         — between dungeons; enter / quit / stats are valid

adventurelib captures free words in UPPERCASE tokens.
  @when('go DIRECTION')   → direction kwarg
  @when('take ITEM')      → item kwarg
  @when('use ITEM')       → item kwarg
  @when('talk NPC')       → npc kwarg
"""

from __future__ import annotations

import sys
from typing import Optional

import adventurelib
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Table
from rich.text import Text

from nullpud.combatant import Combatant
from nullpud.dungeon import DUNGEON_ORDER, Dungeon, next_dungeon
from nullpud.item import get_item, load_all_items
from nullpud.player import Player
from nullpud.puzzle import PuzzleOutcome

console = Console()

# ---------------------------------------------------------------------------
# Mutable game state — module-level so @when handlers can reach it
# ---------------------------------------------------------------------------

_player: Optional[Player] = None
_dungeon: Optional[Dungeon] = None
_current_room_id: Optional[str] = None
_enemy: Optional[Combatant] = None   # active combat opponent


def _room():
    assert _dungeon and _current_room_id
    return _dungeon.rooms[_current_room_id]


def _puzzle():
    assert _dungeon
    return _dungeon.puzzle_for(_room())


# ---------------------------------------------------------------------------
# Rich helpers
# ---------------------------------------------------------------------------

def _hr(char: str = "─", style: str = "dim") -> None:
    console.print(f"[{style}]{char * console.width}[/{style}]")


def _print_hp(combatant: Combatant, label: str = "") -> None:
    pct = combatant.hp / max(1, combatant.max_hp)
    bar_width = 20
    filled = round(pct * bar_width)
    bar = "█" * filled + "░" * (bar_width - filled)
    color = "green" if pct > 0.5 else "yellow" if pct > 0.25 else "red"
    name = label or combatant.name
    console.print(f"  {name}: [{color}]{bar}[/{color}] {combatant.hp}/{combatant.max_hp}")


def _print_combat_status() -> None:
    assert _player and _enemy
    console.print()
    _print_hp(Combatant(
        name=_player.name,
        hp=_player.current_hp,
        max_hp=_player.max_hp,
        attack=0, defense=0,
    ), label=_player.name)
    _print_hp(_enemy)
    console.print()


def _print_inventory() -> None:
    assert _player
    items = _player.inventory
    if not items:
        console.print("[dim]Your pack is empty.[/dim]")
        return
    table = Table(title="Inventory", show_header=True, header_style="bold cyan")
    table.add_column("Item", style="white")
    table.add_column("Type", style="dim")
    table.add_column("Notes", style="dim")
    for item_id in items:
        try:
            item = get_item(item_id)
            equipped = ""
            if _player.equipped.get("weapon") == item_id:
                equipped = "[bold green]equipped (weapon)[/bold green]"
            elif _player.equipped.get("armor") == item_id:
                equipped = "[bold green]equipped (armor)[/bold green]"
            bonus = ", ".join(f"+{v} {k}" for k, v in item.stat_bonus.items())
            table.add_row(item.name, item.type, equipped or bonus or item.desc[:40])
        except (KeyError, FileNotFoundError):
            table.add_row(item_id, "?", "unknown item")
    console.print(table)


def _print_stats() -> None:
    assert _player
    items = load_all_items()
    table = Table(title=f"{_player.name}  —  Level {_player.level}", show_header=False)
    table.add_column("Stat", style="bold cyan")
    table.add_column("Value", style="white")
    table.add_row("HP", f"{_player.current_hp} / {_player.max_hp}")
    table.add_row("Attack", str(_player.attack(items)))
    table.add_row("Defense", str(_player.defense(items)))
    table.add_row("XP", f"{_player.xp} / {_player.level * 100}")
    console.print(table)


# ---------------------------------------------------------------------------
# Exploration commands
# ---------------------------------------------------------------------------

@adventurelib.when("look")
def cmd_look() -> None:
    if adventurelib.get_context() == "combat":
        console.print("[yellow]You're in the middle of a fight![/yellow]")
        _print_combat_status()
        return
    room = _room()
    room.render(load_all_items(), _puzzle())
    room.visited = True


@adventurelib.when("go DIRECTION")
def cmd_go(direction: str) -> None:
    global _current_room_id

    if adventurelib.get_context() == "combat":
        console.print("[red]You can't flee like that — use [bold]flee[/bold].[/red]")
        return

    direction = direction.lower()
    room = _room()
    puzzle = _puzzle()

    if room.monster_blocks():
        console.print(f"[red]The {room.monster_id.replace('_', ' ')} blocks your way![/red]")
        return

    available = room.available_exits(puzzle)
    if direction not in available:
        if puzzle and not puzzle.solved and puzzle.blocks_exit == direction:
            console.print(f"[yellow]{puzzle.desc}[/yellow]")
        else:
            console.print(f"[dim]There's no exit to the {direction}.[/dim]")
        return

    next_id = available[direction]
    assert _dungeon
    next_room = _dungeon.get_room(next_id)
    if not next_room:
        console.print("[red]That exit leads nowhere (bad dungeon data).[/red]")
        return

    _current_room_id = next_id
    next_room.render(load_all_items(), _dungeon.puzzle_for(next_room))
    next_room.visited = True

    # Auto-trigger combat if a monster is in the new room
    if next_room.monster_id:
        _start_combat(next_room.monster_id)


@adventurelib.when("take ITEM")
def cmd_take(item: str) -> None:
    if adventurelib.get_context() == "combat":
        console.print("[yellow]Finish the fight first.[/yellow]")
        return
    room = _room()
    item_lower = item.lower()
    # Match by id or name fragment
    matched_id = _find_item_in_list(item_lower, room.items)
    if not matched_id:
        console.print(f"[dim]There's no '{item}' here.[/dim]")
        return
    room.take_item(matched_id)
    assert _player
    _player.add_item(matched_id)
    try:
        name = get_item(matched_id).name
    except (KeyError, FileNotFoundError):
        name = matched_id
    console.print(f"[green]You pick up the {name}.[/green]")


@adventurelib.when("drop ITEM")
def cmd_drop(item: str) -> None:
    assert _player
    if adventurelib.get_context() == "combat":
        console.print("[yellow]Finish the fight first.[/yellow]")
        return
    item_lower = item.lower()
    matched_id = _find_item_in_list(item_lower, _player.inventory)
    if not matched_id:
        console.print(f"[dim]You don't have a '{item}'.[/dim]")
        return
    _player.remove_item(matched_id)
    _room().drop_item(matched_id)
    try:
        name = get_item(matched_id).name
    except (KeyError, FileNotFoundError):
        name = matched_id
    console.print(f"[dim]You drop the {name}.[/dim]")


@adventurelib.when("use ITEM")
def cmd_use(item: str) -> None:
    assert _player
    item_lower = item.lower()

    if adventurelib.get_context() == "combat":
        _use_in_combat(item_lower)
        return

    # Outside combat: consumables heal, weapons/armor equip, keys/quest → puzzle
    matched_id = _find_item_in_list(item_lower, _player.inventory)
    if not matched_id:
        console.print(f"[dim]You don't have a '{item}'.[/dim]")
        return

    try:
        item_obj = get_item(matched_id)
    except (KeyError, FileNotFoundError):
        console.print(f"[dim]Unknown item: {matched_id}[/dim]")
        return

    if item_obj.type == "consumable":
        heal = item_obj.effect.get("heal", 0)
        if heal:
            recovered = _player.heal(heal)
            _player.remove_item(matched_id)
            console.print(f"[green]You drink the {item_obj.name} and recover {recovered} HP.[/green]")
        else:
            console.print(f"[dim]Nothing happens.[/dim]")
        return

    if item_obj.type in ("weapon", "armor"):
        slot = "weapon" if item_obj.type == "weapon" else "armor"
        _player.equip(matched_id, slot)
        console.print(f"[green]You equip the {item_obj.name}.[/green]")
        return

    # Try applying to the current room's puzzle
    puzzle = _puzzle()
    if puzzle and not puzzle.solved:
        result = puzzle.attempt(item_used=matched_id, inventory=_player.inventory)
        _handle_puzzle_result(result, puzzle, matched_id)
        return

    console.print(f"[dim]You can't use the {item_obj.name} here.[/dim]")


@adventurelib.when("talk NPC")
def cmd_talk(npc: str) -> None:
    if adventurelib.get_context() == "combat":
        console.print("[yellow]This isn't the time for conversation.[/yellow]")
        return
    puzzle = _puzzle()
    if puzzle and not puzzle.solved and puzzle.type == "riddle":
        console.print(f"[cyan]{puzzle.desc}[/cyan]")
        console.print("[dim](Type 'say <answer>' to respond.)[/dim]")
    else:
        console.print(f"[dim]There's no one here to talk to.[/dim]")


@adventurelib.when("say TEXT")
def cmd_say(text: str) -> None:
    puzzle = _puzzle()
    if puzzle and not puzzle.solved and puzzle.type == "riddle":
        result = puzzle.attempt(player_answer=text)
        _handle_puzzle_result(result, puzzle)
    else:
        console.print(f"[dim]Your words echo in the silence.[/dim]")


@adventurelib.when("inventory")
@adventurelib.when("i")
def cmd_inventory() -> None:
    _print_inventory()


@adventurelib.when("stats")
def cmd_stats() -> None:
    _print_stats()


@adventurelib.when("help")
def cmd_help() -> None:
    lines = [
        ("look", "Describe the current room"),
        ("go <direction>", "Move north / south / east / west"),
        ("take <item>", "Pick up an item"),
        ("drop <item>", "Leave an item in the room"),
        ("use <item>", "Use or equip an item; or apply it to a puzzle"),
        ("say <text>", "Answer a riddle"),
        ("talk <npc>", "Speak to someone in the room"),
        ("inventory / i", "List your items"),
        ("stats", "Show your stats"),
        ("attack", "Strike in combat"),
        ("flee", "Attempt to escape a fight"),
        ("quit", "Save and exit"),
    ]
    table = Table(title="Commands", show_header=False, box=None)
    table.add_column("cmd", style="bold cyan", min_width=18)
    table.add_column("desc", style="white")
    for cmd, desc in lines:
        table.add_row(cmd, desc)
    console.print(table)


@adventurelib.when("quit")
@adventurelib.when("exit")
def cmd_quit() -> None:
    if _player:
        path = _player.save()
        console.print(f"[dim]Game saved to {path}. Farewell, {_player.name}.[/dim]")
    sys.exit(0)


# ---------------------------------------------------------------------------
# Combat commands
# ---------------------------------------------------------------------------

@adventurelib.when("attack")
def cmd_attack() -> None:
    if adventurelib.get_context() != "combat":
        console.print("[dim]There's nothing to attack.[/dim]")
        return
    assert _player and _enemy
    items = load_all_items()
    # Player turn
    p_combatant = Combatant(
        name=_player.name,
        hp=_player.current_hp,
        max_hp=_player.max_hp,
        attack=_player.attack(items),
        defense=_player.defense(items),
    )
    _, p_msg = p_combatant.resolve_attack(_enemy)
    console.print(f"[bold white]{p_msg}[/bold white]")

    if not _enemy.is_alive:
        _end_combat(victory=True)
        return

    # Enemy turn
    e_combatant = Combatant(
        name=_enemy.name,
        hp=_enemy.hp,
        max_hp=_enemy.max_hp,
        attack=_enemy.attack,
        defense=_enemy.defense,
    )
    # Create a proxy combatant representing the player for damage resolution
    player_proxy = Combatant(
        name=_player.name,
        hp=_player.current_hp,
        max_hp=_player.max_hp,
        attack=_player.attack(items),
        defense=_player.defense(items),
    )
    _, e_msg = _enemy.resolve_attack(player_proxy)
    _player.take_damage(player_proxy.max_hp - player_proxy.hp)
    console.print(f"[red]{e_msg}[/red]")

    _print_combat_status()

    if not _player.is_alive:
        _end_combat(victory=False)


@adventurelib.when("flee")
def cmd_flee() -> None:
    global _enemy
    import random
    if adventurelib.get_context() != "combat":
        console.print("[dim]You're not in a fight.[/dim]")
        return
    assert _enemy
    if random.random() < 0.5:
        console.print("[yellow]You manage to slip away![/yellow]")
        adventurelib.set_context(None)
        _enemy = None
        _room().render_brief()
    else:
        assert _player
        items = load_all_items()
        player_proxy = Combatant(
            name=_player.name,
            hp=_player.current_hp,
            max_hp=_player.max_hp,
            attack=_player.attack(items),
            defense=_player.defense(items),
        )
        _, e_msg = _enemy.resolve_attack(player_proxy)
        _player.take_damage(player_proxy.max_hp - player_proxy.hp)
        console.print(f"[red]You fail to escape! {e_msg}[/red]")
        _print_combat_status()
        if not _player.is_alive:
            _end_combat(victory=False)


# ---------------------------------------------------------------------------
# Combat helpers
# ---------------------------------------------------------------------------

def _use_in_combat(item_lower: str) -> None:
    assert _player
    matched_id = _find_item_in_list(item_lower, _player.inventory)
    if not matched_id:
        console.print(f"[dim]You don't have that.[/dim]")
        return
    try:
        item_obj = get_item(matched_id)
    except (KeyError, FileNotFoundError):
        console.print(f"[dim]Unknown item.[/dim]")
        return
    if item_obj.type != "consumable":
        console.print(f"[dim]You can't use the {item_obj.name} in combat.[/dim]")
        return
    heal = item_obj.effect.get("heal", 0)
    if heal:
        recovered = _player.heal(heal)
        _player.remove_item(matched_id)
        console.print(f"[green]You drink the {item_obj.name} and recover {recovered} HP.[/green]")
        _print_combat_status()
        # Enemy still gets a turn
        assert _enemy
        items = load_all_items()
        player_proxy = Combatant(
            name=_player.name,
            hp=_player.current_hp,
            max_hp=_player.max_hp,
            attack=_player.attack(items),
            defense=_player.defense(items),
        )
        _, e_msg = _enemy.resolve_attack(player_proxy)
        _player.take_damage(player_proxy.max_hp - player_proxy.hp)
        console.print(f"[red]{e_msg}[/red]")
        _print_combat_status()
        if not _player.is_alive:
            _end_combat(victory=False)
    else:
        console.print(f"[dim]Nothing happens.[/dim]")


def _start_combat(monster_id: str) -> None:
    global _enemy
    assert _player and _dungeon
    _enemy = _dungeon.spawn_monster(monster_id, _player.level)
    adventurelib.set_context("combat")
    console.print()
    console.print(Panel(
        f"[bold red]⚔  {_enemy.name} attacks![/bold red]\n{_dungeon._monster_data[monster_id]['desc']}",
        border_style="red",
    ))
    _print_combat_status()
    console.print("[dim]Commands: attack  |  use <item>  |  flee[/dim]")


def _end_combat(victory: bool) -> None:
    global _enemy
    assert _player and _dungeon

    if victory:
        assert _enemy
        console.print(f"\n[bold green]✓ {_enemy.name} defeated![/bold green]")

        # Award XP
        level_msgs = _player.award_xp(_enemy.xp)
        if level_msgs:
            for msg in level_msgs:
                console.print(f"[bold yellow]⬆  LEVEL UP — {msg}[/bold yellow]")

        # Roll loot
        loot = _enemy.roll_loot()
        if loot:
            for item_id in loot:
                _player.add_item(item_id)
                try:
                    name = get_item(item_id).name
                except (KeyError, FileNotFoundError):
                    name = item_id
                console.print(f"[green]  + {name}[/green]")

        room = _room()
        room.clear_monster()

        # Check for dungeon completion
        if room.id == _dungeon.boss_room_id:
            _dungeon.completed = True
            _on_dungeon_complete()
            return

    else:
        console.print(f"\n[bold red]You have fallen...[/bold red]")
        console.print(f"[dim]{_player.name} collapses in the darkness. Game over.[/dim]")
        _player.save()
        sys.exit(0)

    adventurelib.set_context(None)
    _enemy = None
    _room().render_brief()


def _on_dungeon_complete() -> None:
    global _enemy
    assert _player and _dungeon
    adventurelib.set_context(None)
    _enemy = None

    console.print()
    console.print(Panel(
        f"[bold yellow]★ {_dungeon.name} complete![/bold yellow]\n\nYou fought your way through every shadow.",
        border_style="yellow",
    ))

    _player.last_dungeon = _dungeon.id
    path = _player.save()
    console.print(f"[dim]Progress saved to {path}.[/dim]")

    nxt = next_dungeon(_dungeon.id)
    if nxt:
        console.print(f"\n[cyan]The next dungeon awaits: [bold]{nxt}[/bold][/cyan]")
    else:
        console.print("\n[bold green]You have conquered all dungeons. The realm is safe... for now.[/bold green]")

    console.print("\n[dim]Type [bold]quit[/bold] to exit, or explore the cleared dungeon.[/dim]")


# ---------------------------------------------------------------------------
# Puzzle result handler
# ---------------------------------------------------------------------------

def _handle_puzzle_result(result, puzzle, item_used: str = "") -> None:
    assert _player
    if result.outcome == PuzzleOutcome.SOLVED:
        # Strip the internal consume tag before printing
        msg = result.message
        consume_ids: list[str] = []
        if "__consume__:" in msg:
            msg, tag = msg.split("__consume__:", 1)
            consume_ids = tag.strip().split(",")

        console.print(f"[bold green]{msg.strip()}[/bold green]")
        for cid in consume_ids:
            _player.remove_item(cid.strip())

        # Auto-remove a key after using it on a lock
        if puzzle.type == "lock" and item_used:
            _player.remove_item(item_used)

        _room().render_brief()

    elif result.outcome == PuzzleOutcome.HINT:
        console.print(f"[cyan]{result.message}[/cyan]")
    elif result.outcome == PuzzleOutcome.ALREADY_SOLVED:
        console.print(f"[dim]{result.message}[/dim]")
    else:
        console.print(f"[yellow]{result.message}[/yellow]")


# ---------------------------------------------------------------------------
# Item lookup helper
# ---------------------------------------------------------------------------

def _find_item_in_list(query: str, item_ids: list[str]) -> Optional[str]:
    """Find the first item id in the list whose id or name matches query.

    Matching order: exact id, id prefix, name (case-insensitive substring).
    """
    query = query.lower()
    # Exact id match
    for iid in item_ids:
        if iid.lower() == query:
            return iid
    # Id prefix
    for iid in item_ids:
        if iid.lower().startswith(query):
            return iid
    # Name match via registry
    for iid in item_ids:
        try:
            name = get_item(iid).name.lower()
            if query in name:
                return iid
        except (KeyError, FileNotFoundError):
            pass
    return None


# ---------------------------------------------------------------------------
# Hub
# ---------------------------------------------------------------------------

def _show_hub() -> None:
    assert _player
    items = load_all_items()
    console.print()
    console.print(Panel(
        Text.assemble(
            ("The Wayward Lantern\n\n", "bold"),
            ("A dim tavern at the edge of nowhere. The barkeep nods.\n\n", ""),
            (f"Welcome back, {_player.name}.\n", "italic"),
        ),
        title="[bold]Hub[/bold]",
        border_style="dim",
    ))
    _print_stats()
    console.print()

    available = _available_dungeons()
    if available:
        console.print("[cyan]Available dungeons:[/cyan]")
        for did in available:
            console.print(f"  • [bold]{did}[/bold]")
        console.print()
        console.print("[dim]Type [bold]enter <dungeon>[/bold] to descend.[/dim]")
    else:
        console.print("[green]All dungeons cleared![/green]")

    console.print("[dim]Type [bold]stats[/bold], [bold]inventory[/bold], or [bold]quit[/bold].[/dim]")


def _available_dungeons() -> list[str]:
    assert _player
    result = []
    for did in DUNGEON_ORDER:
        if _player.last_dungeon is None or DUNGEON_ORDER.index(did) > DUNGEON_ORDER.index(_player.last_dungeon):
            result.append(did)
        elif did == DUNGEON_ORDER[0] and _player.last_dungeon is None:
            result.append(did)
    # Always include the first dungeon if nothing has been completed
    if not result and _player.last_dungeon is None:
        result = [DUNGEON_ORDER[0]]
    return result


@adventurelib.when("enter DUNGEON")
def cmd_enter(dungeon: str) -> None:
    global _dungeon, _current_room_id, _enemy
    assert _player

    dungeon_id = dungeon.lower()
    if dungeon_id not in DUNGEON_ORDER:
        console.print(f"[dim]Unknown dungeon: {dungeon_id}[/dim]")
        return

    console.print(f"[dim]Loading {dungeon_id}...[/dim]")
    try:
        _dungeon = Dungeon.load(dungeon_id)
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        return

    _current_room_id = _dungeon.entry_room_id
    _enemy = None
    adventurelib.set_context(None)

    console.print()
    console.print(Panel(
        f"[bold]Entering: {_dungeon.name}[/bold]",
        border_style="cyan",
    ))
    load_all_items()
    _room().render(load_all_items(), _puzzle())


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _greet() -> None:
    console.print(Panel(
        Text.assemble(
            ("nullPud\n", "bold magenta"),
            ("A dungeon awaits. Good luck.\n", "dim"),
        ),
        border_style="magenta",
    ))


def _new_player_prompt() -> Player:
    console.print("[cyan]No save found. What is your name, adventurer?[/cyan]")
    while True:
        name = input("> ").strip()
        if name:
            return Player(name=name)
        console.print("[dim]Please enter a name.[/dim]")


def run() -> None:
    """Entry point called from __init__.main()."""
    global _player

    load_all_items()
    _greet()

    saves = Player.list_saves()
    if saves:
        console.print(f"[dim]Existing save(s): {', '.join(saves)}[/dim]")
        console.print("[cyan]Load a save (enter name) or press Enter for a new character:[/cyan]")
        name = input("> ").strip()
        if name:
            _player = Player.load(name)
            if _player:
                console.print(f"[green]Welcome back, {_player.name}![/green]")
            else:
                console.print(f"[yellow]No save for '{name}'. Creating new character.[/yellow]")
                _player = Player(name=name)
        else:
            _player = _new_player_prompt()
    else:
        _player = _new_player_prompt()

    _show_hub()
    adventurelib.start()
