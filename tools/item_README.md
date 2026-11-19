# Quest item dataset

The item index is embedded in `quest-finder.html` as a compact mapping of quest IDs to arrays of `{id,name,namePtBR,relation}`. `namePtBR` is null if unavailable; there is one row per (item ID, relation), so the same item may appear more than once. Relations:

- `reward`: fixed or one-of choice reward (the dataset does not distinguish the two; don't imply all choices are awarded).
- `objective`: item explicitly listed in the quest's item objectives.
- `start`: item that starts the quest, not an item given by its quest giver.
- `required`: `requiredSourceItems`: non-objective item needed for the quest, not necessarily an acceptance prerequisite.

The source's `sourceItemId` is an item *given* by the quest starter, not necessarily required or a reward, so is deliberately excluded. No fuzzy item-name joins or inference from free text. Missing names cause the item relation to be omitted, not fabricated. Quest records are joined by ID **and** normalized English title; mismatches and absent quests are skipped. A missing entry therefore does not prove a quest has no items.

## Rebuild

From repository root, Python 3 standard library and HTTPS are sufficient:

```sh
python tools/item_update.py --output quest-finder-with-items.html
python -m unittest discover -s tools -p 'test_*.py'
# After validation, replace quest-finder.html with the generated copy.
```

The updater never edits its input HTML. If the output already has a correctly marked block it replaces that block; otherwise it inserts one after the existing `quest-data` block. The caller can atomically replace the original with the completed output after successful generation. It writes `tools/item-data.json`; use `--dataset PATH` to choose a separate output. By default the updater uses the same pinned quest and QuestieDB revisions already embedded by the objective and PT-BR updates. To select other revisions, supply `--quest-commit` and `--item-commit` (full lowercase SHA). It prints source SHA-256 hashes and coverage; builds are deterministic for identical input and source bytes. Run the updater after quest data has been refreshed. Coverage guards reject implausible regressions. Network errors fail the process rather than publishing a fabricated dataset.

The page reads the embedded `item-data` block and associates matching names or IDs with quest IDs. JSON is escaped against HTML script termination. The page remains self-contained and `file://` compatible; the JSON is data, not a runtime global.

## Provenance and limits

- Quest relationships and rewards: [`tyler3497/forever-quests`](https://github.com/tyler3497/forever-quests), pinned in script; `data/quests.json` and upstream README describe sourcing (including TDB, NorgannonDB and QuestieDB). GPL-3.0-only; repository includes `THIRD-PARTY-LICENSE-forever-quests.md`.
- English names: QuestieDB `data/Forever/foreverItemDB.lua`. Portuguese names: `l10n/Forever/lookupItems/ptBR.lua`; traces provide fallback only where base lacks a name. Trace entries can include random-enchantment suffixes and should be treated as imperfect aliases. QuestieDB's historical contributions have mixed/uncertain rights: see `THIRD-PARTY-NOTICE-QuestieDB.md` and upstream licensing before redistribution. Do not assume all QuestieDB data has clear GPL coverage.
- These are community Forever snapshots, not an official server export. Corrections outside generated base item-name data, differences between versions, unavailable names, hidden objectives, and absent quest records limit coverage. Source fields represent available data, not guarantees of in-game behavior. Choices and amounts are not preserved.
- The default build produced 3,209 matched quest identities out of 3,580; 358 absent and 13 title/ID conflicts; 1,655 quests with named items; 1,715 reward, 1,677 objective, 82 start and 62 required rows; 3,535 rows with Portuguese names. 287 item-relation pairs lacked English names and were omitted. These counts can change with input or pinned commits.
