# nullPud

A single-player terminal dungeon crawler built with Python. Type commands to explore hand-crafted rooms, solve puzzles, fight monsters, beat a boss, then carry your character into the next dungeon.

## What it is

nullPud is a text adventure engine in the style of classic MUDs, stripped down to what one player actually needs: a command loop, rooms with exits and items, simple turn-based combat, puzzles that gate progress, and a persistent save so your character grows across dungeons.

It is intentionally small. Each dungeon is a JSON file. Adding new content means writing data, not code.

## Stack

| Piece | Library |
|---|---|
| Command parsing / rooms | [adventurelib](https://github.com/lordmauve/adventurelib) |
| Terminal output | [rich](https://rich.readthedocs.io/) |
| Data files | stdlib `json` |
| Saves | stdlib `json` |

## Getting started

Requires Python 3.13+. Dependencies are managed with [uv](https://docs.astral.sh/uv/).

```bash
# install dependencies
uv sync

# run the game
uv run nullpud
```

## Project layout

```
src/nullpud/
    __init__.py        entry point (main)
    player.py          name, level, hp, stats, inventory
    room.py            description, exits, items, npc/monster, puzzle state
    item.py            name, type, stats
    combatant.py       shared fight logic for player and monsters
    puzzle.py          lock, riddle, lever, item combination
    dungeon.py         room graph, boss room, completion flag
    run_loop.py        input → parse → mutate state → print

data/
    items/             shared item definitions (JSON)
    monsters/          monster definitions (JSON)
    dungeons/          one JSON file per dungeon

saves/                 player save files (JSON, git-ignored)
docs/
    architecture.md    layer design and loop shape
    dungeon-format.md  JSON schema reference for dungeon authors
```

## Gameplay loop

1. **Hub** — rest, spend loot, review stats.
2. **Enter dungeon** — scaled to player level.
3. **Explore** — type commands to move, examine, take, use, talk, and fight.
4. **Puzzles** — small obstacles gate rooms and the boss door.
5. **Boss fight** — turn-based, with a unique mechanic.
6. **Level up** — gain XP and loot, save, return to hub.

## Commands

| Command | Effect |
|---|---|
| `look` | Describe the current room |
| `go north` / `go south` / … | Move through an exit |
| `take <item>` | Pick up an item |
| `drop <item>` | Leave an item in the room |
| `use <item>` | Use an item on yourself or the environment |
| `inventory` | List carried items |
| `stats` | Show player stats |
| `attack` | Strike in combat |
| `use potion` | Heal during combat |
| `flee` | Attempt to escape a fight |
| `talk <npc>` | Speak to an NPC or puzzle NPC |

## First milestone

One dungeon, five rooms:

1. Entrance — flavor text, one item
2. Puzzle room — key or riddle
3. Combat room — one trash mob
4. Treasure room — loot relevant to the boss fight
5. Boss room

Plus a JSON save and a "dungeon 2" stub. That is the complete vertical slice.

## See also

- [docs/architecture.md](docs/architecture.md) — how the layers fit together
- [docs/dungeon-format.md](docs/dungeon-format.md) — how to write a dungeon JSON file
