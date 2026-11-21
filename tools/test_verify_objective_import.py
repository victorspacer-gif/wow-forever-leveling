import unittest

from verify_objective_import import verify


class VerifyObjectiveImportTests(unittest.TestCase):
    page = ('<style>.steps{display:grid}</style>'
            '<script id="quest-data" type="application/json">'
            '{"quests":{"610":{"pre":[[603,"ALL",26,""]],"objectiveSteps":["old"],'
            '"foreverObjectiveSteps":["curated"],"start":"Southshore"}},'
            '"sources":{"26":["Guide","https://example.com"]},"objectiveSource":{"commit":"a"}}'
            '</script><script id="item-data" type="application/json">{"quests":{}}</script>')

    def test_accepts_refreshed_objectives_and_item_index(self):
        candidate = (self.page.replace('["old"]', '["new"]')
                     .replace('"commit":"a"', '"commit":"b"')
                     .replace('"quests":{}', '"quests":{"610":[]}'))
        self.assertEqual(verify(self.page, candidate), 1)

    def test_refuses_css_js_or_markup_changes(self):
        for candidate in (self.page.replace('grid', 'block'), self.page + '<script></script>'):
            with self.assertRaisesRegex(ValueError, 'outside the data blocks'):
                verify(self.page, candidate)

    def test_refuses_changed_edges_coordinates_and_curated_steps(self):
        for old, new, field in [('"ALL"', '"Reported"', 'pre'),
                                ('Southshore', 'Stormwind', 'start'),
                                ('["curated"]', '[]', 'foreverObjectiveSteps')]:
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, rf'quest #610: {field}'):
                verify(self.page, self.page.replace(old, new))

    def test_refuses_id_and_source_changes(self):
        with self.assertRaisesRegex(ValueError, 'quest IDs'):
            verify(self.page, self.page.replace('"610":', '"611":'))
        with self.assertRaisesRegex(ValueError, 'source links'):
            verify(self.page, self.page.replace('https://example.com', 'https://example.org'))

    def test_refuses_duplicate_data_blocks(self):
        with self.assertRaisesRegex(ValueError, 'Expected one quest-data block'):
            verify(self.page, self.page + self.page)


if __name__ == '__main__':
    unittest.main()
