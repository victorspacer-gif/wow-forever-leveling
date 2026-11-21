#!/usr/bin/env python3
"""Embed QuestieDB's Brazilian Portuguese quest names and objectives.

SPDX-License-Identifier: GPL-3.0-only
"""
import json
import re
import sys
from update_objectives import HTML, MARKER, get_json, github_head, norm_name, normalize

REPO = 'Questie/QuestieDB'
RAW = f'https://raw.githubusercontent.com/{REPO}/{{}}/l10n/Forever/lookupQuests/ptBR.lua'
TRACE = f'https://raw.githubusercontent.com/{REPO}/{{}}/l10n/Forever/traces/lookupQuests/ptBR.lua'
COMMUNITY = 'https://raw.githubusercontent.com/tyler3497/forever-quests/{}/data/quests.json'


def parse_row(value):
    # QuestieDB stores each record as a one-line Lua table. Its values are
    # double-quoted JSON-compatible strings, nested tables and nil. Reject
    # unfamiliar syntax instead of evaluating downloaded code.
    out = []
    quoted = escaped = False
    i = 0
    while i < len(value):
        c = value[i]
        if quoted:
            out.append(c)
            if escaped:
                escaped = False
            elif c == '\\':
                escaped = True
            elif c == '"':
                quoted = False
        elif c == '"':
            quoted = True
            out.append(c)
        elif c == '{':
            out.append('[')
        elif c == '}':
            out.append(']')
        elif value.startswith('nil', i):
            out.append('null')
            i += 2
        elif c in ' ,\t':
            out.append(c)
        else:
            raise ValueError(f'Unexpected Lua table token {c!r}')
        i += 1
    if quoted:
        raise ValueError('Unterminated string')
    return json.loads(''.join(out))


def parse_lookup(text):
    result = {}
    for line in text.splitlines():
        m = re.fullmatch(r'\[(\d+)\] = (\{.*\}),', line)
        if not m:
            if re.match(r'^\[\d+\]', line):
                raise ValueError('Unexpected QuestieDB record format')
            continue
        key = m[1]
        if key in result:
            raise ValueError(f'Duplicate quest id {key}')
        row = parse_row(m[2])
        if not isinstance(row, list) or len(row) != 2 or not (row[0] is None or isinstance(row[0], str)) or not (row[1] is None or isinstance(row[1], list) and all(isinstance(x, str) for x in row[1])):
            raise ValueError(f'Unexpected QuestieDB record shape for {key}')
        result[key] = row
    if len(result) < 1000:
        raise ValueError('PT-BR lookup is missing or unexpectedly small')
    return result


def update(page, records, community, commit):
    match = MARKER.search(page)
    if not match or len(MARKER.findall(page)) != 1:
        raise ValueError('Expected one quest-data block')
    data = json.loads(match.group(2))
    quests = data['quests']
    if len(quests) < 1000 or len(community) < 1000:
        raise ValueError('Quest data unexpectedly small')
    old_names = sum(bool(q.get('namePtBR')) for q in quests.values())
    old_objectives = sum(bool(q.get('objectiveStepsPtBR')) for q in quests.values())
    names = objectives = 0
    for ident, q in quests.items():
        q.pop('namePtBR', None)
        q.pop('objectiveStepsPtBR', None)
        src = community.get(ident)
        pt = records.get(ident)
        if not isinstance(src, dict) or not pt or norm_name(src.get('name', '')) != norm_name(q.get('name', '')):
            continue
        if pt[0] and pt[0].strip():
            q['namePtBR'] = pt[0].strip()
            names += 1
        lines = [normalize(s) for s in (pt[1] or []) if normalize(s)]
        if lines:
            q['objectiveStepsPtBR'] = lines
            objectives += 1
    if names < 1000 or objectives < 1000 or names < old_names * .9 or objectives < old_objectives * .9:
        raise ValueError(f'Refusing suspicious coverage: {names} names, {objectives} objectives')
    data['ptBRSource'] = {'repository':f'https://github.com/{REPO}', 'commit':commit,
                          'license':'QuestieDB mixed/uncertain; see upstream LICENSE.md', 'names':names, 'objectives':objectives, 'total':len(quests)}
    serialized = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e')
    return page[:match.start(2)] + serialized + page[match.end(2):], names, objectives


def main():
    import urllib.request
    commit = github_head(REPO, 'master')
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('Invalid QuestieDB commit SHA')
    req = urllib.request.Request(RAW.format(commit), headers={'User-Agent': 'WoW-Forever-Quest-Finder/1.0'})
    with urllib.request.urlopen(req, timeout=45) as response:
        records = parse_lookup(response.read().decode('utf-8'))
    req = urllib.request.Request(TRACE.format(commit), headers={'User-Agent': 'WoW-Forever-Quest-Finder/1.0'})
    with urllib.request.urlopen(req, timeout=45) as response:
        traces = parse_lookup(response.read().decode('utf-8'))
    for ident, row in traces.items():
        base = records.get(ident, ['', None])
        records[ident] = [row[0] or base[0], row[1] if row[1] is not None else base[1]]
    page = HTML.read_text(encoding='utf-8')
    match = MARKER.search(page)
    if not match:
        raise ValueError('Missing quest data')
    metadata = json.loads(match.group(2)).get('objectiveSource', {})
    ref = metadata.get('commit', '')
    if not re.fullmatch(r'[0-9a-f]{40}', ref):
        raise ValueError('Missing community source revision; run update_objectives.py first')
    community = get_json(COMMUNITY.format(ref))
    updated, names, objectives = update(page, records, community, commit)
    if updated != page:
        HTML.write_text(updated, encoding='utf-8', newline='\n')
    print(f'QuestieDB revision: {commit}')
    print(f'Brazilian Portuguese: {names} quest titles, {objectives} quest objectives')
    print('Updated quest-finder.html' if updated != page else 'Already up to date')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'PT-BR update failed; page not replaced: {exc}', file=sys.stderr)
        sys.exit(1)
