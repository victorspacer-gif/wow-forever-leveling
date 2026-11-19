#!/usr/bin/env python3
"""Build the offline NPC quest index from pinned community datasets (GPL-3.0-only)."""
import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from item_update import download, lua_string, norm_name, site_quests

ROOT = Path(__file__).resolve().parent.parent
QUEST_COMMIT = '9f4c5aac2d077854d7f4a2bdc2f8eceb8d7b23af'
NPC_COMMIT = '4f628e8328ed8923ffba169c8b432996e0a7a326'
URLS = {
    'quests': 'https://raw.githubusercontent.com/tyler3497/forever-quests/{}/data/quests.json',
    'npcs': 'https://raw.githubusercontent.com/Questie/QuestieDB/{}/data/Forever/foreverNpcDB.lua',
    'ptBR': 'https://raw.githubusercontent.com/Questie/QuestieDB/{}/l10n/Forever/lookupNpcs/ptBR.lua',
}
ROW = re.compile(r'^\[(\d+)\] = (.*),$')


def parse_names(text, database=False):
    result = {}
    for line in text.splitlines():
        m = ROW.fullmatch(line)
        if not m:
            if re.match(r'^\[\d+\]', line):
                raise ValueError('Malformed NPC row: ' + line[:100])
            continue
        ident, value = int(m[1]), m[2]
        if ident <= 0 or ident in result:
            raise ValueError('Duplicate or invalid NPC ID')
        if not value.startswith('{'):
            raise ValueError('Invalid NPC record')
        value = value[1:]
        if value.startswith('nil,'):
            continue
        name, rest = lua_string(value)
        if not rest.startswith(','):
            raise ValueError('Invalid NPC name record')
        if name.strip():
            result[ident] = name
    if not result:
        raise ValueError('No NPC names')
    return result


def build(site, source, names, pt):
    npcs, stats = {}, Counter(siteQuests=len(site))
    for qid, quest in site.items():
        if not re.fullmatch(r'[1-9]\d*', qid):
            raise ValueError('Invalid quest ID')
        src = source.get(qid)
        if not isinstance(src, dict):
            stats['missingQuest'] += 1
            continue
        if src.get('id') != int(qid) or not quest.get('name') or norm_name(quest['name']) != norm_name(src.get('name', '')):
            stats['questMismatch'] += 1
            continue
        stats['matchedQuest'] += 1
        any_relation = False
        for field, relation in (('startedBy', 'starts'), ('finishedBy', 'ends')):
            group = src.get(field) or {}
            if not isinstance(group, dict) or not isinstance(group.get('npcs', []), list):
                raise ValueError(f'Invalid {field} in quest {qid}')
            ids = group.get('npcs', [])
            if any(type(i) is not int or i <= 0 for i in ids):
                raise ValueError(f'Invalid NPC ID in quest {qid}')
            for ident in sorted(set(ids)):
                # Keep unnamed IDs: loss of a label must not silently discard associations.
                entry = npcs.setdefault(str(ident), {'id': ident, 'name': names.get(ident), 'namePtBR': pt.get(ident), 'starts': [], 'ends': []})
                entry[relation].append(int(qid))
                stats[relation + 'Links'] += 1
                any_relation = True
        stats['questsWithNpc'] += any_relation
    for v in npcs.values():
        v['starts'].sort()
        v['ends'].sort()
    stats['npcs'] = len(npcs)
    stats['unnamedNpcs'] = sum(not n['name'] for n in npcs.values())
    stats['ptBRNpcs'] = sum(bool(n['namePtBR']) for n in npcs.values())
    return dict(sorted(npcs.items(), key=lambda x: int(x[0]))), dict(stats)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, default=ROOT/'quest-finder.html')
    p.add_argument('--output', type=Path, default=ROOT/'npc-quest-data.js')
    p.add_argument('--quest-commit', default=QUEST_COMMIT)
    p.add_argument('--npc-commit', default=NPC_COMMIT)
    args = p.parse_args()
    for commit in (args.quest_commit, args.npc_commit):
        if not re.fullmatch(r'[0-9a-f]{40}', commit):
            raise ValueError('Commit must be a full lowercase SHA')
    if args.input.resolve() == args.output.resolve():
        raise ValueError('Output must not overwrite site')
    site = site_quests(args.input.read_text(encoding='utf-8'))
    raw = {k: download(url.format(args.quest_commit if k == 'quests' else args.npc_commit)) for k, url in URLS.items()}
    npcs, stats = build(site, json.loads(raw['quests']), parse_names(raw['npcs'].decode('utf-8'), True), parse_names(raw['ptBR'].decode('utf-8')))
    if stats.get('matchedQuest', 0) < 1000 or stats.get('npcs', 0) < 100:
        raise ValueError('Refusing unexpectedly low coverage')
    result = {'schemaVersion': 1, 'source': {'questCommit': args.quest_commit, 'npcCommit': args.npc_commit, 'sha256': {k: hashlib.sha256(v).hexdigest() for k, v in raw.items()}}, 'coverage': stats, 'npcs': npcs}
    payload = json.dumps(result, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    args.output.write_text('/* Generated by tools/build_npc_data.py; GPL-3.0-only. */\nglobalThis.NPC_QUEST_DATA = ' + payload + ';\n', encoding='utf-8', newline='\n')
    print(json.dumps(stats, indent=2))


if __name__ == '__main__':
    main()
