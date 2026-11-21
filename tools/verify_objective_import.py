#!/usr/bin/env python3
"""Reject an objective refresh that edits anything outside its allowlist."""
import argparse
import json
from pathlib import Path

from item_update import ITEM_MARKER, MARKER


def split(page):
    data = []
    for marker in (MARKER, ITEM_MARKER):
        matches = list(marker.finditer(page))
        if len(matches) != 1:
            raise ValueError('Expected one quest-data block and one item-data block')
        match = matches[0]
        data.append(json.loads(match[2]))
        page = page[:match.start(2)] + page[match.end(2):]
    return page, *data


def verify(before, after):
    original_shell, original, _ = split(before)
    candidate_shell, candidate, _ = split(after)
    if original_shell != candidate_shell:
        raise ValueError('Import modified HTML, CSS or JavaScript outside the data blocks')
    editable = {'objectiveSteps', 'namePtBR', 'objectiveStepsPtBR'}
    original_quests, candidate_quests = original.pop('quests'), candidate.pop('quests')
    if original_quests.keys() != candidate_quests.keys():
        raise ValueError('Import added or removed quest IDs; use the zone/chain curation path')
    for quest_id, previous in original_quests.items():
        current = candidate_quests[quest_id]
        immutable_before = {k: v for k, v in previous.items() if k not in editable}
        immutable_after = {k: v for k, v in current.items() if k not in editable}
        if immutable_before != immutable_after:
            keys = sorted(k for k in immutable_before.keys() | immutable_after.keys()
                          if k not in immutable_before or k not in immutable_after or immutable_before[k] != immutable_after[k])
            raise ValueError(f'Import modified protected fields on quest #{quest_id}: {", ".join(keys)}')
    for key in ('objectiveSource', 'ptBRSource'):
        original.pop(key, None)
        candidate.pop(key, None)
    if original != candidate:
        raise ValueError('Import modified protected site metadata, routes or source links')
    return len(candidate_quests)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('baseline', type=Path)
    p.add_argument('candidate', type=Path)
    args = p.parse_args()
    try:
        count = verify(args.baseline.read_text(encoding='utf-8'), args.candidate.read_text(encoding='utf-8'))
    except (ValueError, OSError) as exc:
        p.exit(1, f'Refusing objective import: {exc}\n')
    print(f'Import preserves layout, quest graph, and curated fields across all {count} quest IDs.')


if __name__ == '__main__':
    main()
