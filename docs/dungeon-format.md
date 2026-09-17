# nullPud — Dungeon Format Reference

Dungeons, items, and monsters are defined as JSON files under `data/`. The engine loads them at runtime — adding content means writing files, not touching Python.

---

## Directory layout

```
data/
    dungeons/
        crypt_1.json
        crypt_2.json
        ...
    items/
        iron_sword.json
        rusty_key.json
        health_potion.json
        ...
    monsters/
        skeleton.json
        wight_lord.json
        ...
```

---

## Dungeon file (`data/dungeons/<id>.json`)

A dungeon is a graph of rooms with a designated boss room. The engine wires room exits and attaches puzzles after loading.

```json
{
  "id": "crypt_1",
  "name": "The Weeping Crypt",
  "base_level": 1,
  "entry_room": "entrance",
  "boss_room": "boss_chamber",
  "rooms": { ... },
  "puzzles": { ... }
}
```

### Top-level fields

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | yes | Unique identifier. Must match the filename. |
| `name` | string | yes | Display name shown to the player. |
| `base_level` | int | yes | Recommended player level. Used to scale monster stats. |
| `entry_room` | string | yes | Room id where the player starts. |
| `boss_room` | string | yes | Room id of the boss encounter. |
| `rooms` | object | yes | Map of room id → room object (see below). |
| `puzzles` | object | no | Map of puzzle id → puzzle object (see below). Omit if the dungeon has no puzzles. |

---

## Room object

```json
"entrance": {
  "name": "Crypt Entrance",
  "desc": "Damp stone walls close in around you. A rusted gate to the north is chained shut.",
  "exits": {
    "north": "hall"
  },
  "items": ["rusty_key"],
  "monster": null,
  "puzzle": null
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | yes | Short room title shown in the header. |
| `desc` | string | yes | Full description printed on `look` or first entry. |
| `exits` | object | yes | Direction → room id. Valid directions: `north`, `south`, `east`, `west`. Omit directions that don't exist. |
| `items` | array of strings | no | Item ids present in the room at the start. Defaults to `[]`. |
| `monster` | string or null | no | Monster id. `null` means no monster. The monster blocks all exits until defeated. |
| `puzzle` | string or null | no | Puzzle id from the dungeon's `puzzles` map. `null` means no puzzle. |

Exits can be conditionally blocked by a puzzle. See puzzle `blocks_exit` below.

---

## Puzzle object

Puzzles live in the dungeon file's `puzzles` map and are referenced by room.

### Lock puzzle (requires a key item)

```json
"gate_lock": {
  "type": "lock",
  "desc": "The gate is secured with a heavy padlock.",
  "key_item": "rusty_key",
  "blocks_exit": "north",
  "success_msg": "The lock clicks open. The gate swings wide.",
  "fail_msg": "You don't have anything to open this with."
}
```

### Riddle puzzle (correct answer string)

```json
"crypt_riddle": {
  "type": "riddle",
  "desc": "A carved face on the wall speaks: 'I have cities but no houses. I have mountains but no trees. What am I?'",
  "answer": "a map",
  "blocks_exit": "east",
  "success_msg": "The carved face smiles. A hidden door grinds open.",
  "fail_msg": "The face is silent. Nothing happens.",
  "hint": "Think about what shows places without being a place itself."
}
```

Answer matching is case-insensitive and trims whitespace.

### Lever puzzle (sequence of `use` calls)

```json
"brazier_sequence": {
  "type": "lever",
  "desc": "Four unlit braziers stand in a row, numbered left to right.",
  "sequence": ["brazier_1", "brazier_3", "brazier_2", "brazier_4"],
  "blocks_exit": "north",
  "success_msg": "The braziers roar. A portcullis rises.",
  "fail_msg": "The braziers gutter out. The sequence resets.",
  "hint": "An inscription reads: first and third, then second and last."
}
```

The player must `use` the listed items in the given order. Any wrong step resets progress.

### Combination puzzle (two items used together)

```json
"sealed_door": {
  "type": "combination",
  "desc": "Two stone slots flank the door, shaped like a sword and a shield.",
  "items": ["stone_sword", "stone_shield"],
  "consume": true,
  "blocks_exit": "south",
  "success_msg": "Both slots fill. The door sinks into the floor.",
  "fail_msg": "Only one slot is filled. The door holds."
}
```

| Field | Type | Description |
|---|---|---|
| `type` | string | `lock`, `riddle`, `lever`, or `combination` |
| `desc` | string | Printed when the player enters the room or examines the obstacle |
| `blocks_exit` | string | Direction this puzzle locks until solved |
| `success_msg` | string | Printed on solve |
| `fail_msg` | string | Printed on failed attempt |
| `hint` | string | (optional) Printed when the player `use`s the obstacle without the right item/answer |
| `consume` | bool | (combination only) Whether items are removed from inventory on solve. Defaults to `false`. |

---

## Item file (`data/items/<id>.json`)

Items are global — any dungeon or monster can reference them by id.

```json
{
  "id": "rusty_key",
  "name": "Rusty Key",
  "desc": "A small iron key, spotted with rust. It might still turn.",
  "type": "key"
}
```

```json
{
  "id": "iron_sword",
  "name": "Iron Sword",
  "desc": "A straight blade, nothing fancy. Adds 3 attack.",
  "type": "weapon",
  "stat_bonus": { "attack": 3 }
}
```

```json
{
  "id": "health_potion",
  "name": "Health Potion",
  "desc": "A vial of red liquid. Restores 10 HP.",
  "type": "consumable",
  "effect": { "heal": 10 }
}
```

### Item fields

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | yes | Unique identifier. Must match the filename. |
| `name` | string | yes | Display name. |
| `desc` | string | yes | Description shown on `look` or `inventory`. |
| `type` | string | yes | `weapon`, `armor`, `key`, `consumable`, or `quest` |
| `stat_bonus` | object | no | Flat bonuses applied when equipped. Keys: `attack`, `defense`, `max_hp`. |
| `effect` | object | no | One-time effect when `use`d. Keys: `heal` (int). Only valid for `consumable`. |

`key` and `quest` items have no `stat_bonus` or `effect` — they exist to satisfy puzzles or trigger story events.

---

## Monster file (`data/monsters/<id>.json`)

```json
{
  "id": "skeleton",
  "name": "Skeleton",
  "desc": "Bleached bones clatter as it lurches toward you.",
  "base_hp": 12,
  "base_attack": 4,
  "base_defense": 1,
  "xp": 30,
  "loot": [
    { "item": "bone_shard", "chance": 0.8 },
    { "item": "health_potion", "chance": 0.3 }
  ]
}
```

Stats are scaled at runtime by `dungeon.py` using `player.level` and the dungeon's `base_level`. The formula is applied to `base_hp`, `base_attack`, and `base_defense` — the JSON always stores base values at level 1.

### Monster fields

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | yes | Unique identifier. Must match the filename. |
| `name` | string | yes | Display name. |
| `desc` | string | yes | Printed when the player enters the room. |
| `base_hp` | int | yes | HP at level 1. |
| `base_attack` | int | yes | Attack at level 1. |
| `base_defense` | int | yes | Defense at level 1. |
| `xp` | int | yes | XP awarded on defeat (unscaled). |
| `loot` | array | no | Each entry: `item` (item id) and `chance` (0.0–1.0). Rolled independently on defeat. |

### Boss monsters

A boss is a regular monster file. To make it feel distinct:

- Give it higher `base_hp` and `base_attack` than trash mobs in the same dungeon.
- Add a `boss_phase` object (optional) for a mid-fight mechanic:

```json
{
  "id": "wight_lord",
  "name": "Wight Lord",
  "desc": "A towering figure in black plate. Its eyes are cold fire.",
  "base_hp": 60,
  "base_attack": 9,
  "base_defense": 4,
  "xp": 200,
  "loot": [
    { "item": "wight_crown", "chance": 1.0 },
    { "item": "health_potion", "chance": 0.5 }
  ],
  "boss_phase": {
    "trigger_hp_pct": 0.5,
    "message": "The Wight Lord tears off its helmet. 'You cannot kill what has already died!'",
    "attack_bonus": 3
  }
}
```

`boss_phase.trigger_hp_pct` fires when the boss drops below that fraction of its max HP. `attack_bonus` is added permanently from that point. This is handled by `combatant.py`.

---

## Full dungeon example

`data/dungeons/crypt_1.json`

```json
{
  "id": "crypt_1",
  "name": "The Weeping Crypt",
  "base_level": 1,
  "entry_room": "entrance",
  "boss_room": "boss_chamber",
  "rooms": {
    "entrance": {
      "name": "Crypt Entrance",
      "desc": "Damp stone walls. A rusted gate to the north is chained shut.",
      "exits": { "north": "hall" },
      "items": ["rusty_key"],
      "monster": null,
      "puzzle": "gate_lock"
    },
    "hall": {
      "name": "Dark Hall",
      "desc": "A long corridor. Torches sputter in iron sconces. Doors east and north.",
      "exits": { "south": "entrance", "east": "puzzle_room", "north": "treasure_room" },
      "items": [],
      "monster": "skeleton",
      "puzzle": null
    },
    "puzzle_room": {
      "name": "The Whispering Alcove",
      "desc": "A carved face stares from the far wall. The passage north is sealed.",
      "exits": { "west": "hall", "north": "treasure_room" },
      "items": [],
      "monster": null,
      "puzzle": "crypt_riddle"
    },
    "treasure_room": {
      "name": "Ossuary",
      "desc": "Shelves of skulls line the walls. A chest sits in the centre.",
      "exits": { "south": "hall", "north": "boss_chamber" },
      "items": ["iron_sword", "health_potion"],
      "monster": null,
      "puzzle": null
    },
    "boss_chamber": {
      "name": "The Throne of Dust",
      "desc": "A vaulted chamber. On a throne of bones sits the Wight Lord.",
      "exits": { "south": "treasure_room" },
      "items": [],
      "monster": "wight_lord",
      "puzzle": null
    }
  },
  "puzzles": {
    "gate_lock": {
      "type": "lock",
      "desc": "The gate is secured with a heavy padlock.",
      "key_item": "rusty_key",
      "blocks_exit": "north",
      "success_msg": "The lock clicks open. The gate swings wide.",
      "fail_msg": "You don't have anything to open this with."
    },
    "crypt_riddle": {
      "type": "riddle",
      "desc": "A carved face speaks: 'I have cities but no houses. Mountains but no trees. What am I?'",
      "answer": "a map",
      "blocks_exit": "north",
      "success_msg": "The face smiles. A hidden door grinds open.",
      "fail_msg": "The face is silent.",
      "hint": "Think about what shows places without being a place itself."
    }
  }
}
```

---

## Validation checklist

Before adding a dungeon file, confirm:

- [ ] Every `exits` value is a room id defined in the same `rooms` object
- [ ] Every `items` entry has a matching file in `data/items/`
- [ ] Every `monster` value has a matching file in `data/monsters/`
- [ ] Every `puzzle` value is a key in the dungeon's `puzzles` map
- [ ] Every `blocks_exit` direction exists in the room's `exits`
- [ ] `entry_room` and `boss_room` are both defined in `rooms`
- [ ] The dungeon `id` matches the filename (without `.json`)
