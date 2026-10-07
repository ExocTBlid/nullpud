# nullPud

A single-player terminal dungeon crawler. Type commands to explore hand-crafted rooms, solve puzzles, fight monsters, beat a boss, and carry your character into the next dungeon.

## Motivation

nullPud is a text adventure in the style of a classic MUD, cut down to what one player needs: a command loop, rooms with exits and items, turn-based combat, puzzles that gate progress, and a save file so the character grows across dungeons.

It is intentionally small. Each dungeon is a JSON file. Adding a room, an item, or a monster means writing data, not changing the engine. The Python modules stay split by job — player, room, item, combat, puzzle, dungeon, and the command loop — so a new dungeon does not require a new game.

## Quick Start

Requires Python 3.13 or newer. Dependencies are managed with [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run nullpud
```

`uv sync` installs the game and the pytest tools. `uv run nullpud` starts a session.

The first launch asks for a character name and opens the hub, The Wayward Lantern. Type `enter crypt_1` to start The Weeping Crypt. Saves are written to `saves/`, one JSON file per character name. That directory is git-ignored.

Load a character on a later launch by typing the same name at the prompt.

## Usage

A session runs in three contexts. The hub is where you start. Exploration is moving through rooms. Combat replaces exploration until the fight ends.

1. Create a character, or type an existing name to load that save.
2. In the hub, read your stats and the list of open dungeons.
3. Enter a dungeon with `enter DUNGEON`. This build ships `crypt_1` (The Weeping Crypt): an entrance, a fight, a puzzle, a treasure room, and a boss.
4. Explore. `look` describes the room. Take what you need and clear the obstacle on the next door.
5. Fights are turn-based. You act, then the monster does. Defeat the boss to earn XP and loot. The game writes your save and leaves you in the cleared dungeon.
6. `quit` saves and exits. The next launch returns you to the hub.

Dying in a fight ends the run after writing the save.

### Commands

| Command | When | Effect |
| --- | --- | --- |
| `look` | explore | Describe the current room |
| `go DIRECTION` | explore | Move `north`, `south`, `east`, or `west` |
| `take ITEM` | explore | Pick up an item in the room |
| `drop ITEM` | explore | Leave an item in the room |
| `use ITEM` | explore | Drink a consumable, equip a weapon or armor, or apply an item to a puzzle |
| `say TEXT` | explore | Answer a riddle |
| `talk NPC` | explore | Speak to someone, or hear a riddle, in the room |
| `inventory` | any | List carried items. `i` is the short form |
| `stats` | any | Show level, HP, attack, defense, and XP |
| `enter DUNGEON` | hub | Leave the hub and start that dungeon |
| `help` | any | Print the command list in the terminal |
| `attack` | combat | Strike. The monster then acts |
| `use ITEM` | combat | Use a consumable such as `health_potion`. The monster still acts |
| `flee` | combat | Try to escape. About half of attempts succeed. A failure means the monster hits you |
| `quit` | any | Save and exit. `exit` does the same |

`go` does not leave a fight. Use `flee`.

An item can be named by its id or by words in its name. `take rusty_key` and `take rusty key` both pick up the Rusty Key.

### Data files

| Path | What it holds |
| --- | --- |
| `data/dungeons/` | One JSON file per dungeon |
| `data/items/` | Shared item definitions |
| `data/monsters/` | Monster definitions |
| `saves/` | Player saves, written at runtime |

Field-by-field rules for authors are in [docs/dungeon-format.md](docs/dungeon-format.md).

## Contributing

Open a pull request against `main`.

1. `uv sync`, then `uv run pytest`. The suite covers the game objects. `run_loop.py` is left out of coverage because the command loop is played by hand.
2. Put behavior changes in `src/nullpud/`. Follow the layer rules in [docs/architecture.md](docs/architecture.md): lower layers do not import higher ones, and `player` does not import rooms, items, or combat.
3. Add content as data. Create `data/dungeons/<id>.json`, add any new files under `data/items/` and `data/monsters/`, and append the dungeon id to `DUNGEON_ORDER` in `src/nullpud/dungeon.py`. The schema is in [docs/dungeon-format.md](docs/dungeon-format.md). A standard dungeon does not require a change to the command loop.
4. A new puzzle kind (anything other than a lock, riddle, lever, or item combination) needs a handler in `puzzle.py` and tests in `tests/`.

## Project layout

```text
src/nullpud/
    __init__.py        entry point (main)
    player.py          name, level, hp, stats, inventory
    room.py            description, exits, items, monster, puzzle state
    item.py            name, type, stats
    combatant.py       shared fight logic for the player and monsters
    puzzle.py          lock, riddle, lever, item combination
    dungeon.py         room graph, boss room, completion flag
    run_loop.py        input, parse, mutate state, print

data/
    items/             shared item definitions (JSON)
    monsters/          monster definitions (JSON)
    dungeons/          one JSON file per dungeon

saves/                 player save files (JSON, git-ignored)
docs/
    architecture.md    layer design and loop shape
    dungeon-format.md  JSON schema for dungeon authors
```

## Stack

| Piece | Library |
| --- | --- |
| Command parsing | [adventurelib](https://github.com/lordmauve/adventurelib) |
| Terminal output | [rich](https://rich.readthedocs.io/) |
| Data files and saves | stdlib `json` |
