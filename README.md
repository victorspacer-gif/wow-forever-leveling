# WoW Forever Quest Finder

A static, offline-capable quest chain and leveling reference. Open `index.html` or visit the GitHub Pages site. Progress is saved only in each browser's local storage; it is not synced to an account.

## Objective information

Each quest displays its community objective text as a compact list where available, or **Steps not available for this quest** otherwise. These are source-provided objective descriptions, not AI-generated walkthroughs; some contain several actions in one entry. Do not assume every objective has step-by-step instructions. This community dataset combines Forever and Classic-era records and its maintainers say it has not been cross-checked against the live Forever client; verify uncertain details in game.

The objective snapshot is derived from [tyler3497/forever-quests](https://github.com/tyler3497/forever-quests), which in turn credits QuestieDB, TrinityCore, and NorgannonDB. Its objective data is provided under GPL-3.0; see [THIRD-PARTY-LICENSE-forever-quests.md](THIRD-PARTY-LICENSE-forever-quests.md). We select `objectivesText` for matching quest IDs, reject mismatched quest names, omit blank text, and normalize WoW player-substitution codes. The exact upstream commit and coverage are embedded in `objectiveSource` in `quest-finder.html`. Blizzard owns the game content.

## Community walkthroughs

Selected quests have reviewed directions in English and PT-BR: landmarks, approximate coordinates with the correct map, what to interact with, and where to turn in. The companion file `quest-walkthrough-data.js` must stay alongside `quest-finder.html`; the weekly objective refresh does not replace it. Only show details that add to the quest log. Paraphrase and cite the player directions, and distinguish older Classic references or superseded routes from current WoW Forever evidence. A missing guide is not evidence that the quest has no special interaction.

For video discovery, start with the **Videos** tab on the exact Wowhead Forever quest ID and search YouTube for the full quest title plus `WoW Forever`. Prefer a dedicated upload; for longer videos use a timestamp only if that segment actually walks through the quest. Check the version, faction/variant, all objective actions, and hand-in using footage, chapters or transcript; the title or channel alone does not prove coverage. Reject old routes when a later hotfix changes the interaction or location. Store the YouTube ID, creator, coverage type and review evidence in the companion file. A specifically recommended, identity-checked clip with unconfirmed coverage may be credited separately as related gameplay, not as the walkthrough. Video links open only on click and never make network requests in the background.

Run `python tools/walkthrough_review.py --output review-queue.json` to generate a local queue covering every quest ID. It prioritizes object contacts, item objectives, and action-plus-landmark text; priority is only a research hint. `--quest 93404` limits the output. To rank a harvested YouTube catalog in the same run, pass `--videos catalog.json`: a JSON array of records with `id`, `title`, and optional `creator`, `description`, `chapters` (text array), or `wowheadQuestId` (only when the exact Forever quest page links that video). The matcher rejects explicit conflicting editions and won't pick between identical quest names without an exact-ID source or a distinguishing NPC/objective. Candidate results are not published or labeled complete automatically. After editing the curated file, run `python tools/walkthrough_review.py --check` and `bash tools/check-quest-finder.sh`.

## Brazilian Portuguese

The language switch and quest progress are saved independently in the browser. QuestieDB's [Forever PT-BR quest lookup](https://github.com/Questie/QuestieDB/tree/master/l10n/Forever/lookupQuests) supplies localized names and objectives when available. For safety, the importer joins only IDs where the site's English name matches the community English record. Unavailable translations fall back to English; other data such as route walkthroughs and NPC locations may remain in English. No automatic translation service is used. Translated quest data may be inaccurate or outdated. The source commit and coverage are embedded in `ptBRSource`.

[QuestieDB's licensing notice](THIRD-PARTY-NOTICE-QuestieDB.md) says the project team allows copying under GPLv3, but also warns that some historic contributors' permissions are uncertain; Blizzard owns game content. This is not a claim that all underlying contributions have clear GPL licensing.

## Item search

The search box accepts an item name or numeric item ID in English or Brazilian Portuguese and links to the matching recorded quests. Results identify rewards (including choices), objectives, quest-starting items, and other required items. This index covers only recorded links for quests already in the site, not all game items; missing results do not prove an item has no associated quest. Data can include Classic-era fallback and may not reflect the current live game. See [item data provenance, coverage and update notes](tools/item_README.md).

## NPC profiles

Search NPCs by name or ID in English or Brazilian Portuguese, then open their recorded starting and ending quests in the Quest Finder. The community index covers only quests already on this site and may be incomplete or outdated; missing entries do not establish that an NPC has no other quests. The NPC data is a separate file, `npc-quest-data.js`, which must remain alongside `quest-finder.html` for offline use. See [NPC sources, coverage and rebuild instructions](tools/npc_README.md). The scheduled objective refresh does not refresh the NPC index.

## Quest pickup and turn-in locations

Some imported coordinates were expressed on a neighboring zone's map (for example, Nesingwary's Expedition was listed under Westfall). The [location correction ledger](tools/npc_location_fixes.json) records the original labels, NPC IDs, corrected zones and supporting sources. `observed` means ForeverDB has confirmed player observations at the corrected location; `reference` means the fix is supported by reference data, not a direct Forever observation. Coordinates are approximate; a patrol may cover more than one point. The corrections change only pickup and turn-in labels, not quest zones or prerequisites. The scheduled objective refresh preserves these labels.

## Quest follow-ups

**Full recorded chain** uses the same numbered timeline for linear and branching chains, with the selected quest highlighted. For branches, numbers show display order, not a mandatory route; prerequisites are shown above quests they unlock even when another branch reaches the follow-up sooner. The rules and source links remain visible, and the copied chain follows the same order.

The site distinguishes required unlocks from suggested or reported links. Direct non-required links are visible by default in **Full recorded chain**, separate from required progression. Completing Alien Ecology is not a verified requirement for **Hol'anyee's Big Book of Big Lizards**. The book does not lead into the separate Mount Hyjal series: **The Staff of the Mountain** has three prerequisites listed by WoW Forever Atlas. For **Admiral Lamora**, ForeverDB observed an offer after **Unchecked Expansion**; this is not treated as a required unlock. The [Explorer’s League curation](tools/forever-explorers-league.json) records two separate branches from **An Acquaintance in Southshore**: **Take Two With Water → Findings for the Explorer's League** and **Magics of the Drowned City → The Web of Magic**. Neither branch is a prerequisite for the other.

## Forever launch zones

Riverglades, Mount Hyjal, Shen'dralas and Zephras Isle use the saved Wowhead Forever quest listings/zone tab for quest IDs, levels and rewards. The pinned [QuestieDB Forever delta-base](https://github.com/Questie/QuestieDB/tree/9cf27d6491dd80f1998aa0a846dbea9a3c5daad9/src/corrections/Forever/generated) supplies objective text, NPC/object contacts, selected coordinates and item roles. WoW Forever Atlas fills gaps, and the curation file records direct game-database sources and player observations. Listing coverage does not guarantee a quest is currently obtainable. Location coordinates are approximate, and chain links are only added where specifically sourced. Missing links do not prove there are no prerequisites.

The import is additive: it preserves existing guide routes, recorded quest IDs and progress, except for explicit documented endpoint or relationship corrections. Rebuild the snapshot with `python tools/import_forever_zones.py --output quest-finder.new.html`, run `node tools/test-quest-graph.mjs quest-finder.new.html`, then replace the HTML, rebuild the NPC index with `python tools/build_npc_data.py`, and run `bash tools/check-quest-finder.sh` before committing. The weekly refresh does not replace the launch-zone objective, quest-item, or translation fields. The checked-in `tools/forever-zone-listings.json`, `tools/forever-atlas-zone-details.json`, and `tools/forever-zone-curations.json` are inputs, not network dependencies for visitors.

## Refresh objective data

**On GitHub:** Open **Actions → Quest Finder checks and Pages → Run workflow**, select `main`, and enable the refresh checkbox to import upstream data. The same workflow imports weekly, and checks pull requests and pushes to `main` without reimporting. An objective refresh may update objective/translation fields and the item index, not the layout, prerequisites, quest IDs, routes, or curated details. The workflow tests the candidate before committing it and publishes only the exact checked site artifact. A failed check leaves the last successful Pages deployment live.

**Locally:** Use Python 3, Node.js 22+, Git, and Chromium (set `CHROMIUM` to the executable path if it isn't `chromium`):

```sh
cp quest-finder.html quest-finder.before.html
python tools/update_objectives.py
python tools/update_ptbr.py
python tools/item_update.py --output quest-finder.new.html
python tools/verify_objective_import.py quest-finder.before.html quest-finder.new.html
python -c "from pathlib import Path; Path('quest-finder.new.html').replace('quest-finder.html')"
bash tools/check-quest-finder.sh
git add quest-finder.html
git commit -m "Update community quest objectives"
git push origin main
```

The updater validates the source, refuses large coverage drops, checks names as well as IDs, safely embeds the data and prints coverage and conflicts. An upstream update can still contain incorrect or incomplete game data. The updater doesn't need API keys and doesn't contact ForeverDB. `--commit <full upstream SHA>` pins a specific upstream version for reproducibility. If the source is unchanged the update is deterministic and produces no diff. Read the workflow log if a run fails; do not force a partial update.

The timeline test checks every quest graph, and Chromium checks representative linear, choice, merged, and reported-only routes in English and PT-BR at 320, 390, 650, 651, and 1440 CSS pixels. It verifies numbering, the selected step, visible non-required links, and text wrapping, including a long imported name. Only changes that pass these checks can reach Pages through the workflow.
