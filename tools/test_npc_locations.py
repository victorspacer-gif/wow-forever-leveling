import json
from pathlib import Path
import unittest

from item_update import site_quests

ROOT = Path(__file__).resolve().parents[1]


class NpcLocationTests(unittest.TestCase):
    def test_curated_locations_are_published(self):
        quests = site_quests((ROOT / 'quest-finder.html').read_text(encoding='utf-8'))
        ledger = json.loads(Path(__file__).with_name('npc_location_fixes.json').read_text(encoding='utf-8'))
        locations = {q.get(field) for q in quests.values() for field in ('start', 'end')}
        for previous, row in ledger['corrections'].items():
            with self.subTest(npc=row['npcId']):
                self.assertNotIn(previous, locations)
                self.assertIn(row['location'], locations)
                self.assertIn(row['evidence'], {'observed', 'reference'})
                self.assertTrue(row['source'].startswith('https://'))
