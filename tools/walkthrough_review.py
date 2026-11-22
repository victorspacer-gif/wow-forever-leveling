"""Make a review queue, never publish an unreviewed video or direction."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
VIDEO_ID = re.compile(r'[A-Za-z0-9_-]{11}\Z')
FOREVER = re.compile(r'\b(?:wow|world of warcraft|warcraft)\s*forever\b|\bforever\s*wow\b')
OTHER_EDITION = re.compile(r'\b(?:retail|turtle wow|season of discovery|season of mastery|sod|classic era)\b')
OBJECT_ACTION = re.compile(r'\b(?:interact|click|activate|extinguish|open|unlock|repair|loot|recover|gather|'
                           r'collect|pick up|fill|place|read|use|summon|combine|search for)\b', re.I)
LANDMARK = re.compile(r'\b(?:pylon|chest|crate|brazier|shrine|altar|tablet|cauldron|'
                      r'stone|book|scroll|key|ge(y|i)ser|vial|flower|door|orb|lever|pool|cave|tomb|'
                      r'pedestal|temple|cage|banner|fragment|skull|bridge|dais|ruins|'
                      r'cache|barrel|tent|satchel|basket|journal|backpack|well|fountain)\b', re.I)
NAMED_OBJECTIVE = re.compile(r"\b[A-Z][\w'’-]+(?:[ -]+[A-Z][\w'’-]+)+")


def objective_text(quest):
    return ' '.join(text for field in ('foreverObjectiveSteps', 'objectiveSteps', 'manualObjectiveSteps')
                    for text in quest.get(field, []))


def normalize(text):
    text = unicodedata.normalize('NFKD', text.casefold()).translate(str.maketrans('', '', "’‘'"))
    return ' '.join(''.join(c if c.isalnum() else ' ' for c in text
                            if not unicodedata.combining(c)).split())


def phrase(needle, haystack):
    return bool(needle and f' {needle} ' in f' {haystack} ')


def load_data(root=ROOT):
    html = (root / 'quest-finder.html').read_text(encoding='utf-8')
    def block(id):
        return json.loads(re.search(fr'<script id="{id}" type="application/json">(.*?)</script>', html, re.S)[1])
    raw = (root / 'quest-walkthrough-data.js').read_text(encoding='utf-8')
    curated = json.loads(re.fullmatch(r'//[^\n]*\nglobalThis\.QUEST_WALKTHROUGHS = (.*);\s*', raw, re.S)[1])
    items = block('item-data')
    return block('quest-data')['quests'], items.get('quests', items), curated


def check_guides(quests, guides):
    errors = []
    for id, guide in guides.items():
        if id not in quests or guide.get('name') != quests[id]['name']:
            errors.append(f'#{id}: no matching quest ID and name')
        steps = guide.get('steps', [])
        if not steps or any(not isinstance(p, list) or len(p) != 2 or not all(
            isinstance(s, str) and s.strip() for s in p) for p in steps):
            errors.append(f'#{id}: every direction must have English and PT-BR text')
        sources = guide.get('sources', [])
        if not sources or any(not isinstance(p, list) or len(p) != 2 or not p[0] or
                              urlsplit(p[1]).scheme != 'https' or not urlsplit(p[1]).hostname for p in sources):
            errors.append(f'#{id}: at least one named HTTPS source is required')
        for field, types in (('video', {'walkthrough', 'chapter'}), ('relatedVideo', {'gameplay'})):
            v = guide.get(field)
            if v is None:
                continue
            if (not VIDEO_ID.fullmatch(v.get('id', '')) or not all(v.get(k, '').strip()
                for k in ('title', 'creator', 'evidence')) or v.get('coverage') not in types):
                errors.append(f'#{id}: {field} must have an ID, title, creator, review evidence, and valid coverage type')
            if v.get('coverage') == 'chapter':
                if type(v.get('start')) is not int or v['start'] < 0:
                    errors.append(f'#{id}: chapter requires a verified nonnegative start timestamp')
            elif 'start' in v:
                errors.append(f'#{id}: only a chapter may have a start timestamp')
    if errors:
        raise ValueError('\n'.join(errors))


def signals(quest, item_rows):
    """Prioritize likely object objectives. Generic drops and unknowns stay in the queue."""
    text = objective_text(quest)
    found = []
    if any(quest.get(k, '').startswith('Object:') for k in ('start', 'end')):
        found.append('object-pickup-or-turn-in')
    if OBJECT_ACTION.search(text) and LANDMARK.search(text):
        found.append('action-and-landmark-in-objective')
    if any(row.get('relation') in {'objective', 'required', 'provided'} for row in item_rows):
        found.append('objective-item')
    if not text:
        found.append('no-objective-text')
    return found


def video_candidates(quests, catalog):
    """Rank exact-title candidates; for collisions require an exact quest page or unique objective/NPC evidence."""
    ids_by_name = defaultdict(set)
    anchors = {}
    for id, q in quests.items():
        for field in ('name', 'namePtBR', 'foreverNamePtBR'):
            if q.get(field):
                ids_by_name[normalize(q[field])].add(id)
        anchors[id] = {normalize(n['name']) for values in q.get('foreverNpcs', {}).values() for n in values
                       if n.get('name')} | {normalize(i['name']) for i in q.get('foreverItems', [])
                                             if i.get('relation') == 'objective' and i.get('name')} | {
                       normalize(a) for a in NAMED_OBJECTIVE.findall(objective_text(q))}
    candidates = defaultdict(dict)
    for row in catalog:
        video_id = row.get('id', '')
        title = normalize(row.get('title', ''))
        if not VIDEO_ID.fullmatch(video_id) or not title or OTHER_EDITION.search(title):
            continue
        page_id = str(row.get('wowheadQuestId', ''))
        context = normalize(row.get('description', '')) + ' ' + ' '.join(map(normalize, row.get('chapters', [])))
        if not FOREVER.search(title + ' ' + context) and page_id not in quests:
            continue
        tokens = title.split()
        names = {name for a in range(len(tokens)) for b in range(a+1, len(tokens)+1)
                 if (name := ' '.join(tokens[a:b])) in ids_by_name}
        # Prefer the specific name, not a nested short quest title; a mention in prose alone is not a candidate.
        specific = {n for n in names if not any(n != m and phrase(n, m) for m in names)}
        if page_id in quests:
            # ID-scoped listings may be a multi-quest video; review the actual segment before publication.
            found = {page_id: (3, 'exact Forever quest page')}
        elif len(specific) != 1:
            continue
        else:
            name = next(iter(specific))
            group = ids_by_name[name]
            if len(group) == 1:
                found = {next(iter(group)): (1, 'exact title and Forever edition')}
            else:
                hits = {id for id in group if any(phrase(a, context) for a in
                    anchors[id].difference(*(anchors[other] for other in group if other != id)))}
                if len(hits) != 1:
                    continue
                found = {next(iter(hits)): (2, 'exact title, Forever edition, unique objective or NPC')}
        for id, (rank, reason) in found.items():
            existing = candidates[id].get(video_id)
            if existing and existing['rank'] >= rank:
                continue
            candidates[id][video_id] = {'id': video_id, 'title': row['title'], 'creator': row.get('creator'),
                'url': f'https://www.youtube.com/watch?v={video_id}', 'reason': reason, 'rank': rank}
    return {id: sorted(rows.values(), key=lambda v: (-v['rank'], v['id'])) for id, rows in candidates.items()}


def make_queue(quests, items, guides, catalog=()):
    matches = video_candidates(quests, catalog)
    out = []
    for id, q in quests.items():
        guide, name = guides.get(id, {}), q['name']
        rows = signals(q, [*items.get(id, []), *q.get('foreverItems', [])])
        priority = (3 * ('object-pickup-or-turn-in' in rows) + 3 * ('action-and-landmark-in-objective' in rows)
                    + ('objective-item' in rows) + ('no-objective-text' in rows))
        out.append({'id': int(id), 'name': name, 'zone': q.get('foreverZone') or q.get('zone'),
                    'priority': priority, 'signals': rows, 'hasDirections': bool(guide), 'hasVideo': 'video' in guide,
                    'wowhead': f'https://www.wowhead.com/forever/quest={id}',
                    'youtubeQuery': f'"{name}" "WoW Forever" quest', 'videoCandidates': matches.get(id, [])})
    return sorted(out, key=lambda r: (r['hasDirections'], -r['priority'], r['id']))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--check', action='store_true', help='validate published directions; do not write a queue')
    p.add_argument('--output', type=Path, help='write JSON queue (includes every quest unless --quest is used)')
    p.add_argument('--quest', type=int, action='append', help='limit output to this ID; repeatable')
    p.add_argument('--videos', type=Path, help='optional JSON list of YouTube title/description/chapters metadata')
    args = p.parse_args()
    if not args.check and args.output is None:
        p.error('use --check or --output')
    quests, items, guides = load_data()
    check_guides(quests, guides)
    counts = Counter(g[k]['coverage'] for g in guides.values() for k in ('video', 'relatedVideo') if k in g)
    print(f'{len(quests)} quests; {len(guides)} reviewed directions; {sum(counts.values())} video links '
          f'({counts["walkthrough"]} walkthroughs, {counts["chapter"]} chapters, {counts["gameplay"]} related gameplay)')
    if args.output:
        rows = make_queue(quests, items, guides, json.loads(args.videos.read_text(encoding='utf-8')) if args.videos else ())
        if args.quest:
            missing = set(args.quest) - {r['id'] for r in rows}
            if missing:
                p.error(f'unknown quest IDs: {sorted(missing)}')
            rows = [r for r in rows if r['id'] in args.quest]
        args.output.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f'{len(rows)} review rows; {sum(bool(r["signals"]) for r in rows)} with triage signals; '
              f'{sum(len(r["videoCandidates"]) for r in rows)} candidate matches (not published)')


if __name__ == '__main__':
    main()
