# Documentation Sync Rules

After every change to source code or data files, check whether any of the
following docs need updating and apply the changes in the same response.

## Which doc covers what

| Changed file(s) | Check these docs |
|---|---|
| `src/nullpud/*.py` — new module, renamed module, removed module | `README.md` project layout section; `docs/architecture.md` module list |
| `src/nullpud/player.py` — stat fields, level-up formula, save format | `docs/architecture.md` player section and save format block |
| `src/nullpud/puzzle.py` — new puzzle type, changed attempt() signature | `docs/architecture.md` puzzle section; `docs/dungeon-format.md` puzzle types table |
| `src/nullpud/combatant.py` — damage formula, boss phase fields | `docs/architecture.md` combatant section |
| `src/nullpud/dungeon.py` — scaling formula, DUNGEON_ORDER, new fields | `docs/architecture.md` dungeon section; `docs/dungeon-format.md` top-level fields table |
| `src/nullpud/run_loop.py` — new command, removed command, changed verb | `README.md` commands table; `docs/architecture.md` run_loop section |
| `src/nullpud/item.py` — new item type, changed fields | `docs/dungeon-format.md` item fields table |
| `data/items/*.json` — new item file | `docs/dungeon-format.md` item examples if the new item illustrates a new pattern |
| `data/monsters/*.json` — new monster file | `docs/dungeon-format.md` monster examples if it illustrates a new pattern |
| `data/dungeons/*.json` — new dungeon | `docs/dungeon-format.md` validation checklist; `docs/architecture.md` DUNGEON_ORDER note |
| `pyproject.toml` — new dependency, Python version change | `README.md` stack table and getting-started section |
| `.gitignore` — new ignored paths | No doc update needed unless a directory is mentioned in README layout |

## Rules

1. **Docs are part of every change.** If a code change invalidates something
   written in a doc, update the doc in the same response — not a follow-up.

2. **Scope updates tightly.** Only update the sections affected by the change.
   Do not rewrite whole files for a one-line code change.

3. **Keep examples honest.** Any JSON or code block in the docs that shows
   a field, formula, or command must match the current implementation. If the
   code changes, update the example.

4. **Dependency rules.** If `docs/architecture.md` lists dependency constraints
   between modules and the code change violates or changes them, update the
   constraints section.

5. **New modules get a full entry.** A new `src/nullpud/<module>.py` needs:
   - A row in the `README.md` project layout block
   - A `### <module>.py` section in `docs/architecture.md`

6. **Removed or renamed things get cleaned up.** If a command, field, file, or
   module is removed, remove every reference to it in the docs too.

7. **Dungeon-format additions.** A new puzzle type in `puzzle.py` needs:
   - A new ### section in `docs/dungeon-format.md` with a JSON example
   - A new row in the puzzle type table

8. **If nothing in the docs is affected, say so explicitly** in the response
   so the user knows the check was done.
