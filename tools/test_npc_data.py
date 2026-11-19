import unittest
from build_npc_data import build, parse_names


class NpcDataTests(unittest.TestCase):
    def test_parse_names(self):
        self.assertEqual(parse_names("[3] = {'Bob',1},\n[4] = {nil,1},\n[5] = {'',1},"), {3: 'Bob'})
        self.assertEqual(parse_names('[3] = {"Roberto",nil},'), {3: 'Roberto'})

    def test_index_and_matching(self):
        site = {'1': {'name': 'A Quest'}, '2': {'name': 'Other'}, '3': {'name': 'Missing'}}
        source = {'1': {'id': 1, 'name': 'A Quest', 'startedBy': {'npcs': [8, 8, 9]}, 'finishedBy': {'npcs': [8]}}, '2': {'id': 2, 'name': 'Different', 'startedBy': {'npcs': [8]}}}
        entries, stats = build(site, source, {8: 'Bob'}, {8: 'Roberto'})
        self.assertEqual(entries['8'], {'id': 8, 'name': 'Bob', 'namePtBR': 'Roberto', 'starts': [1], 'ends': [1]})
        self.assertIsNone(entries['9']['name'])
        self.assertEqual(stats['questMismatch'], 1)
        self.assertEqual(stats['missingQuest'], 1)
        self.assertEqual(stats['startsLinks'], 2)

    def test_invalid_id(self):
        with self.assertRaises(ValueError):
            build({'1': {'name': 'A'}}, {'1': {'id': 1, 'name': 'A', 'startedBy': {'npcs': [True]}}}, {}, {})


if __name__ == '__main__':
    unittest.main()
