# WoW Forever Quest Finder

A static, offline-capable quest chain and leveling reference. Open `index.html` or visit the GitHub Pages site. Progress is saved only in each browser's local storage; it is not synced to an account.

## Objective information

Each quest displays its community objective text as a compact list where available, or **Steps not available for this quest** otherwise. These are source-provided objective descriptions, not AI-generated walkthroughs; some contain several actions in one entry. Do not assume every objective has step-by-step instructions. This community dataset combines Forever and Classic-era records and its maintainers say it has not been cross-checked against the live Forever client; verify uncertain details in game.

The objective snapshot is derived from [tyler3497/forever-quests](https://github.com/tyler3497/forever-quests), which in turn credits QuestieDB, TrinityCore, and NorgannonDB. Its objective data is provided under GPL-3.0; see [THIRD-PARTY-LICENSE-forever-quests.md](THIRD-PARTY-LICENSE-forever-quests.md). We select `objectivesText` for matching quest IDs, reject mismatched quest names, omit blank text, and normalize WoW player-substitution codes. The exact upstream commit and coverage are embedded in `objectiveSource` in `quest-finder.html`. Blizzard owns the game content.

## Refresh objective data

**On GitHub:** Open **Actions → Update quest objectives → Run workflow → Run workflow**. The same workflow checks weekly. It runs tests, downloads a specific upstream commit, refreshes the page, commits changes, and requests a Pages rebuild. Check the workflow run for errors. This only adds objectives for quests already in the site; it does not add new quests or change prerequisite chains.

**Locally:** With Python 3 and Git installed:

```sh
python -m unittest discover -s tools -p 'test_*.py'
python tools/update_objectives.py
git add quest-finder.html
git commit -m "Update community quest objectives"
git push origin main
```

The updater validates the source, refuses large coverage drops, checks names as well as IDs, safely embeds the data and prints coverage and conflicts. An upstream update can still contain incorrect or incomplete game data. The updater doesn't need API keys and doesn't contact ForeverDB. `--commit <full upstream SHA>` pins a specific upstream version for reproducibility. If the source is unchanged the update is deterministic and produces no diff. Read the workflow log if a run fails; do not force a partial update.
