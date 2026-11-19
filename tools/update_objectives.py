#!/usr/bin/env python3
"""Refresh the offline objective texts in quest-finder.html from forever-quests.

SPDX-License-Identifier: GPL-3.0-only
"""
import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / 'quest-finder.html'
REPO = 'tyler3497/forever-quests'
API = f'https://api.github.com/repos/{REPO}/commits/main'
RAW = f'https://raw.githubusercontent.com/{REPO}/{{}}/data/quests.json'
MARKER = re.compile(r'(<script id="quest-data" type="application/json">)(.*?)(</script>)', re.S)
HEADERS = {'User-Agent': 'WoW-Forever-Quest-Finder/1.0', 'Accept': 'application/vnd.github+json'}


def get_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=45) as response:
        return json.load(response)


def norm_name(value):
    return ''.join(c for c in str(value).casefold() if c.isalnum())


def normalize(text):
    # WoW client substitution tokens have no player context on a static site.
    text = re.sub(r'\$[gG]\s*([^:;]+):([^;]+);', lambda m: m[1].strip() + '/' + m[2].strip(), text)
    text = re.sub(r'\$[nN]', 'adventurer', text)
    text = re.sub(r'\$[bB]', ' ', text)
    return ' '.join(text.split())


def refresh(page, source, commit):
    match = MARKER.search(page)
    if not match or len(MARKER.findall(page)) != 1:
        raise ValueError('Expected exactly one embedded quest-data script')
    data = json.loads(match.group(2))
    quests = data.get('quests')
    if not isinstance(quests, dict) or len(quests) < 1000:
        raise ValueError('Site quest data is missing or unexpectedly small')
    if not isinstance(source, dict) or len(source) < 1000:
        raise ValueError('Upstream quest data is missing or unexpectedly small')
    covered = 0
    mismatches = []
    for quest_id, quest in quests.items():
        previous = quest.pop('objectiveSteps', None)
        record = source.get(quest_id)
        if not isinstance(record, dict):
            continue
        source_name = record.get('name', '')
        if not source_name or norm_name(quest.get('name', '')) != norm_name(source_name):
            if record.get('objectivesText'):
                mismatches.append((quest_id, quest.get('name', ''), source_name))
            continue
        entries = record.get('objectivesText')
        if not isinstance(entries, list):
            continue
        lines = [normalize(s) for s in entries if isinstance(s, str) and normalize(s)]
        if lines:
            quest['objectiveSteps'] = lines
            covered += 1
    if covered < 1000:
        raise ValueError(f'Refusing to publish: only {covered} quests have objective text')
    old_count = sum(bool(q.get('objectiveSteps')) for q in json.loads(match.group(2))['quests'].values())
    if old_count and covered < old_count * 0.9:
        raise ValueError(f'Refusing to publish: coverage fell from {old_count} to {covered}')
    data['objectiveSource'] = {'repository': f'https://github.com/{REPO}', 'commit': commit,
                               'license': 'GPL-3.0-only', 'covered': covered, 'total': len(quests)}
    # Escape <, > and & inside JSON so untrusted data cannot terminate the script.
    serialized = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e')
    new_page = page[:match.start(2)] + serialized + page[match.end(2):]
    return new_page, covered, len(quests), mismatches


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', help='Pin a specific 40-character upstream commit; default: current main')
    args = parser.parse_args()
    commit = args.commit or get_json(API)['sha']
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('Expected a full lowercase Git commit SHA')
    source = get_json(RAW.format(commit))
    page = HTML.read_text(encoding='utf-8')
    output, covered, total, mismatches = refresh(page, source, commit)
    if output != page:
        HTML.write_text(output, encoding='utf-8', newline='\n')
    print(f'Upstream commit: {commit}')
    print(f'Quest objectives: {covered}/{total}; unavailable: {total-covered}')
    print(f'Skipped name conflicts with objective text: {len(mismatches)}')
    for ident, site, upstream in mismatches:
        print(f'  #{ident}: site={site!r}; upstream={upstream!r}')
    print('Updated quest-finder.html' if output != page else 'Already up to date')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'Objective update failed; existing page not replaced: {exc}', file=sys.stderr)
        sys.exit(1)
