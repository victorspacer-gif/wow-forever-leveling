# NPC quest index

`npc-quest-data.js` is an offline-compatible script; load it before code using it with `<script src="npc-quest-data.js"></script>`. It defines `globalThis.NPC_QUEST_DATA`:

- `npcs`: object keyed by decimal NPC ID; each value has numeric `id`, `name` and `namePtBR` (either can be null), and sorted unique `starts` and `ends` arrays of numeric quest IDs. Each ID refers to the page's `quests` object. A quest can occur in both lists, and may have multiple NPCs for either relation. Do not merge records by name.
- `coverage`: build-time counts. `source`: pinned Git commits and SHA-256 hashes of downloaded files. `schemaVersion` is 1.

The index reverses `startedBy.npcs` and `finishedBy.npcs` from [forever-quests](https://github.com/tyler3497/forever-quests), but only where the site's quest ID and normalized English name both match. Names come from [QuestieDB](https://github.com/Questie/QuestieDB) Forever NPC database and PT-BR lookup. Quest IDs refer to the snapshot of `quest-finder.html` used at build time: rebuild after site quests change. Neither objects nor items are treated as NPCs; absent lists do not prove absence in game. Names can be missing even when NPC IDs and relations are known, and separate NPC IDs can share a name. No attempt is made to infer IDs from the site's free-text start/end fields. Community data combines versions, can omit or misidentify records, and is not verified against the live client.

The rebuild also merges `tools/npc_supplement.json`, a small, sourced list of NPC starts and ends for quest records missing from the pinned community snapshot. IDs must exist in the site being rebuilt, duplicate links are ignored, and the sources are embedded in the output. Pass `--supplement` with a compatible file if rebuilding an older snapshot.

## Rebuild

Run `python tools/build_npc_data.py` from the repository root. By default the script downloads the fixed commits in its source and writes only `npc-quest-data.js`, never the site HTML. Override with `--quest-commit` / `--npc-commit` (full lowercase SHA), `--input`, or `--output`. Run `python -m unittest discover -s tools -p 'test_npc_data.py'`. Source names and relationships are third-party data: see `THIRD-PARTY-LICENSE-forever-quests.md` and `THIRD-PARTY-NOTICE-QuestieDB.md`; the latter warns historic contributor permissions are uncertain. Blizzard owns game content.
