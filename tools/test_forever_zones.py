import json
import re
import unittest

from import_forever_zones import EXCLUDED, HERE, ZONE_IDS, literal
from item_update import MARKER


class ForeverZoneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        html = (HERE.parent/'quest-finder.html').read_text(encoding='utf-8')
        cls.page = json.loads(MARKER.search(html)[2])
        cls.listings = json.loads((HERE/'forever-zone-listings.json').read_text(encoding='utf-8'))
        cls.npcs = json.loads(re.search(r'globalThis.NPC_QUEST_DATA = (.*);',
                                       (HERE.parent/'npc-quest-data.js').read_text(encoding='utf-8'))[1])['npcs']

    def test_safe_lua_literals(self):
        self.assertEqual(literal('{nil, {{7, "objective"}, {8}}}'), [None, [[7, 'objective'], [8]]])
        for text in ('{1 2}', 'os.execute("false")', '{false} + {true}'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                literal(text)

    def test_zone_snapshots_match_every_record(self):
        quests = self.page['quests']
        for zone in ZONE_IDS:
            with self.subTest(zone=zone):
                rows = self.listings[zone]['rows']
                expected = {str(row['id']) for row in rows if row['id'] not in EXCLUDED}
                actual = {i for i, q in quests.items() if q.get('foreverZone') == zone}
                stats = self.page['foreverZoneSource']['zones'][zone]
                self.assertEqual(expected, actual)
                self.assertEqual(len(expected), stats['listed'] - stats.get('excluded', 0))
                self.assertEqual(sum(bool(quests[i].get('foreverObjectiveSteps') or
                                          quests[i].get('objectiveSteps') or quests[i].get('manualObjectiveSteps'))
                                     for i in actual), stats['objectives'])
                self.assertEqual(sum(bool(quests[i].get('zoneRecord')) for i in actual), stats['added'])
                for i in actual:
                    q = quests[i]
                    self.assertEqual(q['foreverZoneSource'], self.listings[zone]['url'])
                    for phase, field in [('start', 'starts'), ('end', 'ends')]:
                        for rel in q.get('foreverNpcs', {}).get(phase, []):
                            self.assertIn(int(i), self.npcs[str(rel['id'])][field])
        self.assertTrue(set(map(str, EXCLUDED)).isdisjoint(quests))

    def test_lamora_key_is_not_the_turn_in(self):
        lamora = self.page['quests']['95124']
        roles = {item['id']: item['relation'] for item in lamora['foreverItems']}
        self.assertEqual(roles, {268520: 'required', 268506: 'objective'})
        self.assertEqual([e[:2] for e in lamora['pre']], [[95122, 'Suggested link']])
        self.assertEqual(lamora['start'], lamora['end'])
        self.assertEqual(lamora['foreverNpcs']['start'][0]['id'], 259961)

    def test_hyjal_graph_uses_confirmed_source(self):
        quests = self.page['quests']
        self.assertEqual({tuple(e[:3]) for e in quests['90647']['pre']},
                         {(92317, 'ALL', 30), (92335, 'ALL', 30), (92500, 'ALL', 30)})
        for q in quests.values():
            for earlier, _, source, _ in q.get('pre', []):
                self.assertIn(str(earlier), quests)
                self.assertIn(str(source), self.page['sources'])


if __name__ == '__main__':
    unittest.main()
