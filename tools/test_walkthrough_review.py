from copy import deepcopy
import unittest

from walkthrough_review import check_guides, load_data, make_queue, signals, video_candidates


class WalkthroughTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.quests, cls.items, cls.guides = load_data()

    def test_every_record_has_one_review_row(self):
        check_guides(self.quests, self.guides)
        rows = make_queue(self.quests, self.items, self.guides)
        self.assertEqual(len(rows), len(self.quests))
        self.assertEqual({str(r['id']) for r in rows}, set(self.quests))
        by_id = {r['id']: r for r in rows}
        self.assertIn('action-and-landmark-in-objective', by_id[651]['signals'])
        self.assertIn('no-objective-text', signals({}, []))
        self.assertTrue(by_id[93404]['hasVideo'])
        self.assertFalse(by_id[93604]['hasVideo'])  # old dungeon video must not be served as current

    def test_disambiguates_actual_forever_video_candidates(self):
        # Public metadata from YouTube and the exact Wowhead quest's Videos tab.
        bue = {'id':'YljPMrVgQoc', 'title':'Rot and Regret, WoW Forever Quest'}
        power = {'id':'qU7okIFjgUE', 'title':'WOW Forever Powering the Pylons Quest Guide'}
        variant = {'id':'x3ZsKvYSNf0', 'title':"Welcome to Shen'dar Village WoW Forever Quest"}
        mention = {'id':'uU7c_mfMEpU', 'title':'Breaking the Keystone (Elite) - Group Quest Guide | WoW Forever',
                   'description':'Before this: Stones of Binding'}
        old = {'id':'InvalidEra1', 'title':'Stones of Binding - WoW Classic Era',
               'description':'WoW Forever tags should not override explicit edition'}
        ambiguous = video_candidates(self.quests, [variant])
        self.assertFalse({'92514','93461'} & ambiguous.keys())
        matched = video_candidates(self.quests, [bue, {**bue, 'wowheadQuestId':'93404'}, power,
            {**variant, 'description':'Speak with Rathiril Sunlance'}, mention, old])
        self.assertEqual([v['id'] for v in matched['93404']], ['YljPMrVgQoc'])
        self.assertEqual(matched['93404'][0]['reason'], 'exact Forever quest page')
        self.assertEqual(matched['96018'][0]['id'], power['id'])
        self.assertEqual(matched['93461'][0]['id'], variant['id'])
        self.assertNotIn('92514', matched)
        self.assertNotIn('651', matched)

    def test_refuses_stale_id_or_incomplete_video_review(self):
        bad = deepcopy(self.guides['93606'])
        bad['video'].pop('start')
        bad['name'] = 'Not this quest'
        with self.assertRaisesRegex(ValueError, 'chapter requires') as err:
            check_guides(self.quests, {'93606': bad})
        self.assertIn('no matching quest ID and name', str(err.exception))


if __name__ == '__main__':
    unittest.main()
