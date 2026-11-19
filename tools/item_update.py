#!/usr/bin/env python3
"""Build a pinned Forever quest-item dataset; optionally inject it into an HTML copy.

SPDX-License-Identifier: GPL-3.0-only
"""
import argparse
import hashlib
import json
import re
import sys
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUEST_COMMIT = '9f4c5aac2d077854d7f4a2bdc2f8eceb8d7b23af'
ITEM_COMMIT = '4f628e8328ed8923ffba169c8b432996e0a7a326'
QUEST_URL = 'https://raw.githubusercontent.com/tyler3497/forever-quests/{}/data/quests.json'
ITEM_BASE = 'https://raw.githubusercontent.com/Questie/QuestieDB/{}/'
PATHS = {'items': 'data/Forever/foreverItemDB.lua', 'pt': 'l10n/Forever/lookupItems/ptBR.lua', 'trace': 'l10n/Forever/traces/lookupItems/ptBR.lua'}
MARKER = re.compile(r'(<script id="quest-data" type="application/json">)(.*?)(</script>)', re.S)
ITEM_MARKER = re.compile(r'(<script id="item-data" type="application/json">)(.*?)(</script>)', re.S)
ROW = re.compile(r'^\[(\d+)\] = (.*),$')


def download(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'WoW-Forever-Quest-Finder/1.0'})
    with urllib.request.urlopen(req, timeout=90) as response:
        return response.read()


def lua_string(text):
    """Parse a Lua quoted string without executing downloaded Lua."""
    if not text or text[0] not in "\"'":
        raise ValueError('Expected Lua string')
    quote, out, i = text[0], [], 1
    escapes = {'n':'\n', 'r':'\r', 't':'\t', '\\':'\\', "'":"'", '"':'"'}
    while i < len(text):
        c = text[i]
        if c == quote:
            return ''.join(out), text[i+1:]
        if c == '\\':
            i += 1
            if i >= len(text) or text[i] not in escapes:
                raise ValueError('Unsupported Lua escape')
            c = escapes[text[i]]
        out.append(c)
        i += 1
    raise ValueError('Unterminated Lua string')


def parse_names(text, item_db=False):
    result = {}
    for line in text.splitlines():
        m = ROW.fullmatch(line)
        if not m:
            if re.match(r'^\[\d+\]', line):
                raise ValueError('Unexpected lookup row: ' + line[:100])
            continue
        ident, value = int(m[1]), m[2]
        if ident in result or ident <= 0:
            raise ValueError('Duplicate/invalid item ID')
        if item_db:
            if not value.startswith('{'):
                raise ValueError('Unexpected item table')
            value = value[1:]
        name, rest = lua_string(value)
        if not name.strip() or (item_db and not rest.startswith(',')) or (not item_db and rest):
            raise ValueError('Unexpected item name format')
        result[ident] = name
    if not result:
        raise ValueError('No item names parsed')
    return result


def norm_name(s):
    return ''.join(c for c in str(s).casefold() if c.isalnum())


def site_quests(page):
    matches = list(MARKER.finditer(page))
    if len(matches) != 1:
        raise ValueError('Expected exactly one quest-data block')
    quests = json.loads(matches[0][2])['quests']
    if not isinstance(quests, dict) or not quests:
        raise ValueError('Missing site quests')
    return quests


def build(site, source, names, pt):
    output, stats = {}, Counter()
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
        pairs = set()
        def add(item, relation):
            if type(item) is not int or item <= 0:
                raise ValueError(f'Invalid {relation} item for quest {qid}: {item!r}')
            pairs.add((item, relation))
        for row in src.get('objectives', {}).get('items', []):
            if not isinstance(row, list) or not row:
                raise ValueError(f'Invalid objective row in quest {qid}')
            add(row[0], 'objective')
        for item in src.get('startedBy', {}).get('items', []):
            add(item, 'start')
        for item in src.get('requiredSourceItems', []):
            add(item, 'required')
        for field in ('items', 'choice'):
            for row in src.get('rewards', {}).get(field, []):
                add(row['itemId'], 'reward')
        entries = []
        for ident, rel in sorted(pairs):
            if ident not in names:
                stats['missingItemName'] += 1
                continue
            entries.append({'id': ident, 'name': names[ident], 'namePtBR': pt.get(ident), 'relation': rel})
            stats[rel] += 1
            stats['ptRows'] += bool(pt.get(ident))
        if entries:
            output[qid] = entries
    stats['questsWithItems'] = len(output)
    stats['siteQuests'] = len(site)
    return dict(sorted(output.items(), key=lambda x: int(x[0]))), dict(stats)


def serialize(data):
    return json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e')


def inject(page, data):
    matches = list(ITEM_MARKER.finditer(page))
    if len(matches) > 1:
        raise ValueError('Multiple item-data blocks')
    payload = serialize(data)
    if matches:
        m = matches[0]
        return page[:m.start(2)] + payload + page[m.end(2):]
    matches = list(MARKER.finditer(page))
    if len(matches) != 1:
        raise ValueError('Expected exactly one quest-data block to insert after')
    pos = matches[0].end()
    return page[:pos] + '\n<script id="item-data" type="application/json">' + payload + '</script>' + page[pos:]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, default=ROOT/'quest-finder.html')
    p.add_argument('--output', type=Path, help='Optional HTML destination; never overwrites input')
    p.add_argument('--dataset', type=Path, default=ROOT/'tools/item-data.json')
    p.add_argument('--quest-commit', help='Override the community objective source revision')
    p.add_argument('--item-commit', help='Override the QuestieDB localization source revision')
    args = p.parse_args()
    page = args.input.read_text(encoding='utf-8')
    marker = MARKER.search(page)
    if not marker:
        raise ValueError('Missing quest-data block')
    source_meta = json.loads(marker.group(2))
    args.quest_commit = args.quest_commit or source_meta.get('objectiveSource', {}).get('commit') or QUEST_COMMIT
    args.item_commit = args.item_commit or source_meta.get('ptBRSource', {}).get('commit') or ITEM_COMMIT
    for sha in (args.quest_commit,args.item_commit):
        if not re.fullmatch('[0-9a-f]{40}', sha):
            raise ValueError('Expected 40-character lowercase commit SHA')
    if args.output and args.output.resolve() == args.input.resolve():
        raise ValueError('Output must differ from input')
    if args.dataset.resolve() == args.input.resolve() or args.output and args.dataset.resolve() == args.output.resolve():
        raise ValueError('Input, output and dataset paths must differ')
    raw = {'quests': download(QUEST_URL.format(args.quest_commit))}
    raw.update({k: download(ITEM_BASE.format(args.item_commit) + v) for k,v in PATHS.items()})
    source = json.loads(raw['quests'])
    names = parse_names(raw['items'].decode('utf-8'), True)
    pt = parse_names(raw['pt'].decode('utf-8'))
    # Traces may contain random-enchantment suffixes; use base names when present.
    for ident, name in parse_names(raw['trace'].decode('utf-8')).items():
        pt.setdefault(ident, name)
    site = site_quests(page)
    data, stats = build(site, source, names, pt)
    previous = ITEM_MARKER.search(page)
    if previous:
        old = json.loads(previous.group(2))
        if old and len(data) < len(old) * 0.9:
            raise ValueError(f'Refusing to publish: item coverage fell from {len(old)} to {len(data)} quests')
    if len(site) >= 1000 and (stats.get('matchedQuest', 0) < len(site)*0.8 or len(names) < 10000 or len(data) < 1000):
        raise ValueError('Refusing unexpectedly low coverage')
    rendered = inject(page, data) if args.output else None
    args.dataset.write_text(serialize(data)+'\n', encoding='utf-8', newline='\n')
    if args.output:
        args.output.write_text(rendered, encoding='utf-8', newline='\n')
    print(json.dumps({'questCommit':args.quest_commit, 'itemCommit':args.item_commit, 'sha256':{k:hashlib.sha256(v).hexdigest() for k,v in raw.items()}, 'stats':stats}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'Item update failed: {e}', file=sys.stderr)
        sys.exit(1)
