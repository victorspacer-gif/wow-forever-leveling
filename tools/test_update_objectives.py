import json
import unittest
from update_objectives import refresh, normalize


def fixture():
    q = {str(i): {'name': f'Quest {i}'} for i in range(1100)}
    source = {str(i): {'name': f'Quest {i}', 'objectivesText': [f'Do task {i}.']} for i in range(1100)}
    return '<script id="quest-data" type="application/json">' + json.dumps({'quests': q}) + '</script>', source


class ObjectiveUpdates(unittest.TestCase):
    def test_all_quests_and_safe_embedded_json(self):
        page, source = fixture()
        source['2']['objectivesText'] = ['Collect <item> & go.', '', 'Turn in.']
        source['3']['name'] = 'Different quest'
        source['4']['objectivesText'] = []
        output, covered, total, conflicts = refresh(page, source, 'a' * 40)
        self.assertEqual((covered, total), (1098, 1100))
        self.assertEqual(conflicts[0][0], '3')
        self.assertNotIn('<item>', output)
        payload = json.loads(output.split('>', 1)[1].split('</script>', 1)[0])
        self.assertEqual(payload['quests']['2']['objectiveSteps'], ['Collect <item> & go.', 'Turn in.'])
        self.assertNotIn('objectiveSteps', payload['quests']['3'])
        self.assertNotIn('objectiveSteps', payload['quests']['4'])
        again, *_ = refresh(output, source, 'a' * 40)
        self.assertEqual(again, output)

    def test_sudden_coverage_loss_rejected(self):
        page, source = fixture()
        output, *_ = refresh(page, source, 'a' * 40)
        for i in range(200):
            source[str(i)]['objectivesText'] = []
        with self.assertRaises(ValueError):
            refresh(output, source, 'a' * 40)

    def test_client_tokens(self):
        self.assertEqual(normalize('Hello $N, $g brother:sister;!'), 'Hello adventurer, brother/sister!')


if __name__ == '__main__':
    unittest.main()
