#!/usr/bin/env python3
"""Import the four launch zones into the offline Quest Finder (GPL-3.0-only)."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re

from item_update import MARKER, download, lua_string, norm_name, parse_names, serialize
from update_objectives import normalize
from update_ptbr import parse_lookup

HERE = Path(__file__).resolve().parent
PIN = '9cf27d6491dd80f1998aa0a846dbea9a3c5daad9'
UPSTREAM = f'https://raw.githubusercontent.com/Questie/QuestieDB/{PIN}/'
ZONE_IDS = {'Riverglades': 16591, 'Mount Hyjal': 616, "Shen'dralas": 16651, 'Zephras Isle': 16593}
ZONE_SYMBOLS = {'RIVERGLADES': 'Riverglades', 'MOUNT_HYJAL': 'Mount Hyjal',
                'SHEN_DRALAS': "Shen'dralas", 'ZEPHRAS_ISLE': 'Zephras Isle',
                'WINTERSPRING': 'Winterspring', 'MOONGLADE': 'Moonglade'}
CLASSES = {1: 'Warrior', 2: 'Paladin', 4: 'Hunter', 8: 'Rogue', 16: 'Priest',
           64: 'Shaman', 128: 'Mage', 256: 'Warlock', 1024: 'Druid'}
SIDE = {1: 'Alliance', 2: 'Horde', 3: 'Both'}
EXCLUDED = {93173, 95331, 98426}  # explicitly marked unused or reuse placeholders
SITE_ALIASES = {93034: ('Valley of Bones (Gelkis)', 'Valley of Bones'),
                92850: ('The Missing Scholar 2', 'The Missing Scholar'),
                93735: ('The Broken Construct 1', 'The Broken Construct'),
                93737: ('The Broken Construct 2', 'The Broken Construct')}
ROW = re.compile(r'^        \[(\d+)\] = \{[^\n]*\n(.*?)^        \},', re.M | re.S)
FIELD = re.compile(r'^            \[\w+Keys\.(\w+)\] = (.*?),(?: --.*)?$', re.M)
FILES = {k: f'src/corrections/Forever/generated/foreverBase{k.title()}.lua'
         for k in ('quest', 'npc', 'object', 'item')}
FILES.update({'items': 'data/Forever/foreverItemDB.lua',
              'objects': 'data/Forever/foreverObjectDB.lua',
              'npcs': 'data/Forever/foreverNpcDB.lua',
              'ptQuest': 'l10n/Forever/lookupQuests/ptBR.lua',
              'ptQuestTrace': 'l10n/Forever/traces/lookupQuests/ptBR.lua',
              'ptItem': 'l10n/Forever/lookupItems/ptBR.lua',
              'ptItemTrace': 'l10n/Forever/traces/lookupItems/ptBR.lua'})


def literal(text):
    """Read a limited Lua literal without evaluating downloaded Lua code."""
    def read(rest):
        rest = rest.lstrip()
        if rest.startswith(('"', "'")):
            return lua_string(rest)
        if rest.startswith('{'):
            result, rest = [], rest[1:].lstrip()
            while not rest.startswith('}'):
                item, rest = read(rest)
                result.append(item)
                rest = rest.lstrip()
                if rest.startswith(','):
                    rest = rest[1:].lstrip()
                elif not rest.startswith('}'):
                    raise ValueError(f'Malformed array: {text}')
            return result, rest[1:]
        m = re.match(r'(?:nil|true|false|-?\d+(?:\.\d+)?)(?=$|[,}\s])', rest)
        if not m:
            raise ValueError(f'Unsupported Lua literal: {text}')
        raw = m[0]
        value = json.loads({'nil': 'null'}.get(raw, raw))
        return value, rest[m.end():]

    value, rest = read(text)
    if rest.strip():
        raise ValueError(f'Trailing data in Lua literal: {text}')
    return value


def fields(text):
    return {int(i): dict(FIELD.findall(body)) for i, body in ROW.findall(text)}


def field(record, k, default=None):
    return literal(record[k]) if k in record else default


def legacy_names(text):
    names = {}
    for m in re.finditer(r'^\[(\d+)\] = \{(["\'].*)$', text, re.M):
        name, _ = lua_string(m[2])
        if name:
            names[int(m[1])] = name
    return names


def slot(arr, ix):
    return (arr[ix] or []) if len(arr) > ix else []


def apply_curated_chain(data, chain):
    for ident, source in chain['sources'].items():
        if ident in data['sources'] and data['sources'][ident] != source:
            raise ValueError(f'Curated chain source ID collision: {ident}')
        data['sources'][ident] = source
    for ident, patch in chain['quests'].items():
        q = data['quests'].setdefault(ident, {})
        if q and q['name'] != patch['name']:
            raise ValueError(f'Curated chain quest name mismatch: {ident}')
        existing = q.get('pre', [])
        edges = {tuple(edge[:2]): edge for edge in existing}
        for edge in patch.get('pre', []):
            edges[tuple(edge[:2])] = edge
        q.update(patch)
        if edges:
            q['pre'] = list(edges.values())


def import_data(data, listings, atlas, curated, raw):
    quests = data['quests']
    stats = {}
    generated = {k: fields(raw[k]) for k in ('quest', 'npc', 'object', 'item')}
    names = {k: legacy_names(raw[k+'s']) for k in ('item', 'npc', 'object')}
    for k, index in names.items():
        index.update({i: literal(r['name']) for i, r in generated[k].items() if 'name' in r})
    ptq = parse_lookup(raw['ptQuest'])
    for i, row in parse_lookup(raw['ptQuestTrace']).items():
        old = ptq.get(i, [None, None]); ptq[i] = [row[0] or old[0], row[1] or old[1]]
    pti = parse_names(raw['ptItemTrace']) | parse_names(raw['ptItem'])
    seen = set()
    previous_import = {int(i) for i,v in quests.items() if v.get('zoneRecord')}
    added_ids = set()
    for z, code in ZONE_IDS.items():
        section = listings[z]
        counter = Counter(listed=len(section['rows']))
        for row in section['rows']:
            i, title = row['id'], row['name']
            if type(i) is not int or i in seen or i <= 0:
                raise ValueError(f'Duplicate or malformed quest ID {i!r}')
            seen.add(i)
            if row['category'] != code and not (z == 'Zephras Isle' and row['category'] < 0):
                raise ValueError(f'Unexpected zone category for {i}')
            if i in EXCLUDED:
                counter['excluded'] += 1
                continue
            ident = str(i)
            if ident not in quests or i in previous_import:
                added_ids.add(i)
                counter['added'] += 1
            q = quests.setdefault(ident, {'name': title, 'zone': z, 'hasNew': True,
                                          'zoneRecord': True, 'unknown': True})
            if norm_name(q['name']) != norm_name(title) and (q['name'], title) != SITE_ALIASES.get(i):
                raise ValueError(f'Existing quest #{i} conflicts with {title!r}')
            q.setdefault('zone', z)
            if row['level'] > 0:
                q.setdefault('level', row['level'])
            if row['reqlevel'] > 0:
                q.setdefault('min', row['reqlevel'])
            if row.get('side') in SIDE:
                q.setdefault('side', SIDE[row['side']])
            if row.get('reqclass') in CLASSES:
                q.setdefault('class', CLASSES[row['reqclass']])
            if z == 'Zephras Isle' and q.get('zoneRecord') and row.get('reqrace') in (4294967296, 8589934592):
                q.setdefault('races', ['Skyborne (Alliance)' if row['reqrace'] == 4294967296 else 'Skyborne (Horde)'])
            q['foreverZone'] = z
            q['foreverZoneSource'] = section['url']
            q['foreverRewards'] = {k: row[k] for k in ('xp', 'money') if k in row}
            record = generated['quest'].get(i, {})
            old_name = field(record, 'name')
            if old_name and norm_name(old_name) != norm_name(title):
                raise ValueError(f'QuestieDB name conflict #{i}: {old_name!r} vs {title!r}')
            a, c = atlas.get(ident, {}), curated['quests'].get(ident, {})
            texts = c.get('steps') or field(record, 'objectivesText', []) or a.get('text', [])
            if texts:
                q['foreverObjectiveSteps'] = [normalize(t) for t in texts if normalize(t)]
                q['foreverObjectiveSources'] = c.get('sources') or (
                    [['QuestieDB Forever', f'https://github.com/Questie/QuestieDB/blob/{PIN}/{FILES["quest"]}']]
                    if 'objectivesText' in record else [['WoW Forever Atlas', a['url']]])
            if ident in ptq and (old_name or a or c):
                pt_name, pt_steps = ptq[ident]
                if pt_name and pt_name.strip():
                    q['foreverNamePtBR'] = pt_name.strip()
                lines = c.get('stepsPtBR') or [normalize(t) for t in pt_steps or [] if normalize(t)]
                if lines:
                    q['foreverObjectiveStepsPtBR'] = lines
            if c.get('stepsPtBR'):
                q['foreverObjectiveStepsPtBR'] = c['stepsPtBR']

            npc_links, item_links = {}, set()
            for link, key, label in [('start', 'startedBy', 'Starts quest'), ('end', 'finishedBy', 'Turn-in')]:
                groups = field(record, key, [])
                contacts = {(k, j): names[k].get(j) for ix,k in enumerate(('npc','object','item'))
                            for j in slot(groups, ix)}
                if not contacts:
                    contacts = {(s['kind'][:-1], s['id']): s['name'] for s in a.get('contacts', []) if s['label'] == label}
                if link in c.get('contacts', {}):
                    contacts = {(v['kind'], v['id']): v['name'] for v in c['contacts'][link]}
                display = []
                for (k, j), nm in sorted(contacts.items()):
                    if k == 'npc':
                        npc_links.setdefault(link, []).append({'id': j, 'name': nm})
                    if k == 'item' and link == 'start':
                        item_links.add((j, 'start'))
                    entity = generated[k].get(j, {})
                    area = ZONE_SYMBOLS.get(entity.get('zoneID', '').removeprefix('zoneIDs.'))
                    # Only pin a singleton in the entity's explicitly identified zone.
                    spawn = re.search(rf'\[{ZONE_IDS[area]}\] = \{{\{{(\d+(?:\.\d+)?), (\d+(?:\.\d+)?)\}}\}}',
                                      entity.get('spawns', '')) if area in ZONE_IDS else None
                    name = nm or f'{k.upper()} #{j}'
                    display.append(name + (f' — {area}' if area else '') +
                                   (f' ({spawn[1]}, {spawn[2]})' if spawn else ''))
                if c.get(link):
                    q[link] = c[link]
                elif display:
                    q.setdefault(link, ' / '.join(display))
            if npc_links:
                q['foreverNpcs'] = npc_links
            for objective in slot(field(record, 'objectives', []), 2):
                item_links.add((objective[0], 'objective'))
            provided = field(record, 'sourceItemId')
            if provided:
                item_links.add((provided, 'provided'))
            for line in row.get('itemchoices', []) + row.get('itemrewards', []):
                item_links.add((line[0], 'reward'))
            item_links.update(tuple(v) for v in c.get('items', []))
            items = [{'id': j, 'relation': k, 'name': names['item'][j], 'namePtBR': pti.get(j)}
                     for j, k in sorted(item_links) if j in names['item']]
            if items:
                q['foreverItems'] = items
            if c.get('requirements'):
                dest = q.setdefault('pre', [])
                for edge in c['requirements']:
                    if not any(x[:2] == edge[:2] for x in dest):
                        dest.append(edge)
            if c.get('clearNote'):
                q.pop('note', None)
            counter['objectives'] += bool(q.get('foreverObjectiveSteps') or q.get('objectiveSteps') or q.get('manualObjectiveSteps'))
            counter['endpoints'] += bool(q.get('start') or q.get('end'))
            counter['itemLinks'] += len(items)
        stats[z] = dict(counter)
    data['sources'].update(curated['graphSources'])
    apply_curated_chain(data, json.loads((HERE/'forever-explorers-league.json').read_text(encoding='utf-8')))
    for ident, rec in quests.items():
        for source_id, _, evidence, _ in rec.get('pre', []):
            if str(source_id) not in quests or str(evidence) not in data['sources']:
                raise ValueError(f'Unresolved prerequisite/source for {ident}: {source_id}, {evidence}')
    data['foreverZoneSource'] = {'questieCommit': PIN, 'zones': stats}
    data['stats']['total'] = len(quests)
    data['stats']['linked'] = sum(not q.get('guide') for q in quests.values())
    data['stats']['edges'] = sum(len(q.get('pre', [])) for q in quests.values())
    return stats, added_ids


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, default=HERE.parent/'quest-finder.html')
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if args.input.resolve() == args.output.resolve():
        p.error('output must differ from input')
    page = args.input.read_text(encoding='utf-8')
    match = MARKER.search(page)
    data = json.loads(match[2])
    load = lambda name: json.loads((HERE/name).read_text(encoding='utf-8'))
    with ThreadPoolExecutor(max_workers=5) as pool:
        raw = dict(zip(FILES, pool.map(lambda k: download(UPSTREAM + FILES[k]).decode('utf-8'), FILES)))
    stats, added = import_data(data, load('forever-zone-listings.json'), load('forever-atlas-zone-details.json'),
                               load('forever-zone-curations.json'), raw)
    result = page[:match.start(2)] + serialize(data) + page[match.end(2):]
    args.output.write_text(result, encoding='utf-8', newline='\n')
    print(json.dumps({'newQuestIds': len(added), 'zones': stats}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
