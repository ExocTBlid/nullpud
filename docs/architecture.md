# nullPud — Architecture

## Guiding principle

Think in layers, not one big game file. Each layer owns one concern and exposes a clean interface to the layers above it. New dungeons and content should require writing data, not touching core logic.

---

## Layer diagram

```
┌─────────────────────────────────────────┐
│               run_loop                  │  input → parse → mutate → print
├─────────────────────────────────────────┤
│               dungeon                   │  room graph, boss, completion flag
├──────────────┬──────────────────────────┤
│    player    │  room / item / combatant │  game objects
├──────────────┴──────────────────────────┤
│               puzzle                    │  state machines for obstacles
├─────────────────────────────────────────┤
│         adventurelib + rich             │  command dispatch, terminal output
├─────────────────────────────────────────┤
│           JSON data files               │  rooms, items, monsters, dungeons
└─────────────────────────────────────────┘
```

---

## Modules

### `player.py`

Owns everything that persists across dungeons.

- **Fields:** name, level, max\_hp, current\_hp, attack, defense, xp, inventory (list of item ids), equipped weapon/armor
- **Responsibilities:** level-up logic, stat scaling, inventory add/remove, serialise to / deserialise from a save dict
- **Does not** know about rooms or combat resolution — it just holds the numbers

### `room.py`

A single node in the dungeon graph.

- **Fields:** id, name, description, exits (dict of direction → room id), items present (list of item ids), npc/monster id (optional), puzzle id (optional), visited flag
- **Responsibilities:** render its own description via Rich, report available exits, hold transient state (items picked up, monster defeated, puzzle solved)
- **Does not** wire its own exits — `dungeon.py` does that after loading

### `item.py`

A single item definition.

- **Fields:** id, name, description, type (`weapon` | `armor` | `key` | `consumable` | `quest`), stat modifiers, use effect
- **Responsibilities:** describe itself, apply its effect when used (`consumable` heals, `weapon` equips, etc.)
- Items are loaded from `data/items/` and looked up by id at runtime — they are never mutated, so the same definition can appear in multiple rooms

### `combatant.py`

Shared turn-based fight logic used by both `player` and monsters.

- **Fields:** name, hp, max\_hp, attack, defense, loot table (monsters only)
- **Responsibilities:** resolve one attack (damage formula, miss chance), check alive, apply status if any are added later
- **Combat turn order:** player acts first, then monster. One command per turn: `attack`, `use <consumable>`, `flee`
- **Damage formula (starting point):** `max(1, attacker.attack - defender.defense) + randint(0, 2)`
- Both `Player` and a loaded monster dict produce a `Combatant`; the fight loop in `run_loop` does not care which is which

### `puzzle.py`

State machines for room obstacles.

- **Types:** `lock` (needs a key item), `riddle` (correct answer string), `lever` (sequence of `use` calls), `combination` (two items used together)
- **Responsibilities:** check whether a player action satisfies the puzzle, return a result (`solved`, `fail`, `hint`)
- **Does not** block movement directly — `run_loop` checks puzzle state when the player tries to use an exit or enter a room

### `dungeon.py`

The graph of rooms for one dungeon run.

- **Fields:** id, name, rooms (dict of room id → `Room`), boss room id, completion flag, scaling metadata (base level)
- **Responsibilities:** load from a JSON file, wire room exits, attach puzzle callbacks, scale monster stats to `player.level`, track which rooms have been visited, mark completion when boss is defeated
- **Does not** run the game loop — it is a passive data structure

### `run_loop.py`

The game loop. This is the only module that calls adventurelib decorators.

- Registers `@when` handlers for every verb: `look`, `go DIRECTION`, `take ITEM`, `drop ITEM`, `use ITEM`, `inventory`, `stats`, `attack`, `flee`, `talk NPC`
- Each handler: validates preconditions (in combat? puzzle blocking?), mutates state on `player` / `room` / `dungeon`, then prints feedback via Rich
- **Loop shape:**

```
start
  └─ load save (or create new player)
  └─ show hub
        └─ enter dungeon
              └─ adventurelib.start()   ← blocks on input
                    │
                    ├─ @when handlers mutate state
                    │
                    └─ boss defeated?
                          └─ award XP + loot
                          └─ level up if threshold met
                          └─ write save JSON
                          └─ return to hub
```

- Rich is used here for all output: room descriptions in panels, inventory as a table, HP as a progress bar, combat results in colored text

---

## Data flow: entering a dungeon

```
run_loop           dungeon            room / item / puzzle
   │                  │                      │
   │ load("crypt_1")  │                      │
   │ ────────────────►│                      │
   │                  │ read JSON            │
   │                  │ instantiate Rooms ──►│
   │                  │ wire exits           │
   │                  │ attach puzzles ─────►│
   │◄─────────────────│                      │
   │ set current_room │                      │
   │ print room desc  │                      │
```

---

## Save format

A save is a single JSON file at `saves/<player_name>.json`. It is written after every dungeon completion and on a clean quit from the hub.

```json
{
  "name": "Arden",
  "level": 2,
  "xp": 340,
  "max_hp": 28,
  "attack": 7,
  "defense": 3,
  "inventory": ["iron_sword", "health_potion"],
  "equipped": {
    "weapon": "iron_sword",
    "armor": null
  },
  "last_dungeon": "crypt_1"
}
```

`player.py` owns serialisation. `run_loop.py` decides when to call it.

---

## Adding a new dungeon

1. Write `data/dungeons/<id>.json` (see [dungeon-format.md](dungeon-format.md)).
2. Add any new monsters to `data/monsters/`.
3. Add any new items to `data/items/`.
4. If the dungeon uses a puzzle type not yet implemented, add a handler in `puzzle.py`.
5. Register the dungeon id in the hub's dungeon list so the player can enter it.

No changes to the core loop are needed for standard content.

---

## Dependency rules

- Lower layers must not import from higher layers.
- `run_loop` may import everything.
- `dungeon` may import `room`, `item`, `puzzle`, `combatant`.
- `room`, `item`, `puzzle`, `combatant` must not import each other or `dungeon`.
- `player` must not import any game-object module — it only holds data.
