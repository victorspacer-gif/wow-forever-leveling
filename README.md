# WoW Forever Quest Finder

A static, offline-capable quest chain and leveling reference. Open `index.html` or visit the GitHub Pages site. Progress is saved only in each browser's local storage; it is not synced to an account.

## Objective information

Each quest displays its community objective text as a compact list where available, or **Steps not available for this quest** otherwise. These are source-provided objective descriptions, not AI-generated walkthroughs; some contain several actions in one entry. Do not assume every objective has step-by-step instructions. This community dataset combines Forever and Classic-era records and its maintainers say it has not been cross-checked against the live Forever client; verify uncertain details in game.

The objective snapshot is derived from [tyler3497/forever-quests](https://github.com/tyler3497/forever-quests), which in turn credits QuestieDB, TrinityCore, and NorgannonDB. Its objective data is provided under GPL-3.0; see [THIRD-PARTY-LICENSE-forever-quests.md](THIRD-PARTY-LICENSE-forever-quests.md). We select `objectivesText` for matching quest IDs, reject mismatched quest names, omit blank text, and normalize WoW player-substitution codes. The exact upstream commit and coverage are embedded in `objectiveSource` in `quest-finder.html`. Blizzard owns the game content.

## Brazilian Portuguese

The language switch and quest progress are saved independently in the browser. QuestieDB's [Forever PT-BR quest lookup](https://github.com/Questie/QuestieDB/tree/master/l10n/Forever/lookupQuests) supplies localized names and objectives when available. For safety, the importer joins only IDs where the site's English name matches the community English record. Unavailable translations fall back to English; other data such as route walkthroughs and NPC locations may remain in English. No automatic translation service is used. Translated quest data may be inaccurate or outdated. The source commit and coverage are embedded in `ptBRSource`.

[QuestieDB's licensing notice](THIRD-PARTY-NOTICE-QuestieDB.md) says the project team allows copying under GPLv3, but also warns that some historic contributors' permissions are uncertain; Blizzard owns game content. This is not a claim that all underlying contributions have clear GPL licensing.

## Item search

The search box accepts an item name or numeric item ID in English or Brazilian Portuguese and links to the matching recorded quests. Results identify rewards (including choices), objectives, quest-starting items, and other required items. This index covers only recorded links for quests already in the site, not all game items; missing results do not prove an item has no associated quest. Data can include Classic-era fallback and may not reflect the current live game. See [item data provenance, coverage and update notes](tools/item_README.md).

## NPC profiles

Search NPCs by name or ID in English or Brazilian Portuguese, then open their recorded starting and ending quests in the Quest Finder. The community index covers only quests already on this site and may be incomplete or outdated; missing entries do not establish that an NPC has no other quests. The NPC data is a separate file, `npc-quest-data.js`, which must remain alongside `quest-finder.html` for offline use. See [NPC sources, coverage and rebuild instructions](tools/npc_README.md). The scheduled objective refresh does not refresh the NPC index.

## Quest follow-ups

The site distinguishes required unlocks from suggested or reported links. In particular, **Hol'anyee's Big Book of Big Lizards** is shown under **Other recorded follow-ups** for Alien Ecology: both quests share a quest giver, but completing Alien Ecology is not a verified requirement. The separate Hyjal series beginning with **The Staff of the Mountain** is not unlocked by the book. Its first entry names earlier prerequisites not yet mapped on the site. Curated objective summaries serve as fallbacks and are preserved by community data refreshes.

## Refresh objective data

**On GitHub:** Open **Actions → Update quest objectives → Run workflow → Run workflow**. The same workflow checks weekly. It runs tests, downloads a specific upstream commit, refreshes the page, commits changes, and requests a Pages rebuild. Check the workflow run for errors. This only adds objectives for quests already in the site; it does not add new quests or change prerequisite chains.

**Locally:** With Python 3 and Git installed:

```sh
python -m unittest discover -s tools -p 'test_*.py'
python tools/update_objectives.py
python tools/update_ptbr.py
python tools/item_update.py --output quest-finder.new.html
python -c "from pathlib import Path; Path('quest-finder.new.html').replace('quest-finder.html')"
python -m unittest discover -s tools -p 'test_*.py'
git add quest-finder.html
git commit -m "Update community quest objectives"
git push origin main
```

The updater validates the source, refuses large coverage drops, checks names as well as IDs, safely embeds the data and prints coverage and conflicts. An upstream update can still contain incorrect or incomplete game data. The updater doesn't need API keys and doesn't contact ForeverDB. `--commit <full upstream SHA>` pins a specific upstream version for reproducibility. If the source is unchanged the update is deterministic and produces no diff. Read the workflow log if a run fails; do not force a partial update.
