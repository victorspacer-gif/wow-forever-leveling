#!/usr/bin/env python3
"""Offline tests for item dataset construction and inline embedding."""
import json
import re
import unittest
from pathlib import Path
import item_update as m


class ItemTests(unittest.TestCase):
    def setUp(self):
        self.site = {'1': {'name': 'An Example'}, '2': {'name': 'Different'}}
        self.source = {'1': {'id':1, 'name':'An Example', 'startedBy':{'items':[10]},
                             'objectives':{'items':[[10], [11, 3]]}, 'requiredSourceItems':[12],
                             'sourceItemId':13, 'rewards':{'items':[{'itemId':10}], 'choice':[{'itemId':14}, {'itemId':14}]}},
                       '2': {'id':2, 'name':'Wrong', 'startedBy':{'items':[10]}}}
        self.names = {10:'Sword',11:'Eye',12:'Tool',13:'Provided',14:'Choice'}
        self.data, self.stats = m.build(self.site, self.source, self.names, {10:'Espada'})

    def test_relations_not_inferred_and_not_duplicated(self):
        got = {(x['id'],x['relation']) for x in self.data['1']}
        self.assertEqual(got, {(10,'start'), (10,'objective'), (10,'reward'), (11,'objective'), (12,'required'), (14,'reward')})
        self.assertNotIn('2', self.data)
        self.assertEqual(self.stats['questMismatch'], 1)
        self.assertEqual(len(self.data['1']), 6)
        self.assertTrue(any(x['namePtBR']=='Espada' for x in self.data['1']))
        self.assertTrue(any(x['namePtBR'] is None for x in self.data['1']))

    def test_unavailable_item_and_bad_id(self):
        result, stats = m.build(self.site, self.source, {}, {})
        self.assertEqual(result, {})
        self.assertEqual(stats['missingItemName'], 6)
        self.source['1']['requiredSourceItems'] = [False]
        with self.assertRaises(ValueError): m.build(self.site, self.source, self.names, {})

    def test_id_collision_guard(self):
        self.source['1']['id'] = 2
        self.assertNotIn('1', m.build(self.site, self.source, self.names, {})[0])

    def test_safe_inline_and_repeatability(self):
        page = '<script id="quest-data" type="application/json">{"quests":{}}</script>'
        data = {'1':[{'id':1,'name':'</script><img>&','namePtBR':None,'relation':'reward'}]}
        out = m.inject(page, data)
        self.assertEqual(out, m.inject(out, data))
        raw = m.ITEM_MARKER.search(out)[2]
        self.assertNotIn('</script', raw.lower())
        self.assertEqual(json.loads(raw), data)
        self.assertEqual(len(list(m.ITEM_MARKER.finditer(out))), 1)
        with self.assertRaises(ValueError): m.inject(out+out, data)

    def test_lua_no_execution(self):
        self.assertEqual(m.parse_names("[1] = {'Recruit\\'s Shirt',nil},", True), {1:"Recruit's Shirt"})
        self.assertEqual(m.parse_names('[1] = "Espada",'), {1:'Espada'})
        with self.assertRaises(ValueError): m.parse_names('[1] = os.execute("oops"),')
        with self.assertRaises(ValueError): m.parse_names('[1] = "abc",\n[1] = "x",')

    def test_generated_dataset_invariants(self):
        page = (m.ROOT/'quest-finder.html').read_text(encoding='utf-8')
        block = m.ITEM_MARKER.search(page)
        if not block: self.skipTest('Run item_update.py to embed the dataset')
        data = json.loads(block[2])
        site = m.site_quests(page)
        self.assertGreater(len(data), 1000)
        for qid, rows in data.items():
            self.assertIn(qid, site)
            self.assertEqual(len(rows),len({(r['id'],r['relation']) for r in rows}))
            for row in rows:
                self.assertEqual(set(row), {'id','name','namePtBR','relation'})
                self.assertIs(type(row['id']), int)
                self.assertGreater(row['id'], 0)
                self.assertTrue(row['name'])
                self.assertIn(row['relation'], {'start','required','reward','objective'})

if __name__ == '__main__': unittest.main()
