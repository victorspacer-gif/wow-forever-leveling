import json
import unittest
from update_ptbr import parse_row, parse_lookup, update


class PortugueseImport(unittest.TestCase):
    def test_parse_lua_without_execution(self):
        self.assertEqual(parse_row('{"Nome", {"Fale com \\"Tia\\".", "Volte."}}'), ['Nome', ['Fale com "Tia".', 'Volte.']])
        self.assertEqual(parse_row('{"Nome", nil}'), ['Nome', None])
        with self.assertRaises(ValueError):
            parse_row('{"Nome", os.execute("x")}')

    def test_lookup_rejects_unexpected_and_duplicates(self):
        with self.assertRaises(ValueError):
            parse_lookup('[1] = {"x", nil},\n[1] = {"x", nil},')
        with self.assertRaises(ValueError):
            parse_lookup('[2] = not_a_table,')

    def test_coverage_mismatch_and_script_escape(self):
        quests = {str(i): {'name': f'Quest {i}'} for i in range(1100)}
        community = {str(i): {'name': f'Quest {i}'} for i in range(1100)}
        localized = {str(i): [f'Missão {i}', ['Faça algo.']] for i in range(1100)}
        community['2']['name'] = 'Different quest'
        localized['3'][1] = ['Feche </script> & prossiga.']
        page = '<script id="quest-data" type="application/json">' + json.dumps({'quests':quests}) + '</script>'
        output, names, objectives = update(page, localized, community, 'a' * 40)
        self.assertEqual((names, objectives), (1099,1099))
        payload = json.loads(output.split('>',1)[1].split('</script>',1)[0])
        self.assertNotIn('namePtBR',payload['quests']['2'])
        self.assertEqual(payload['quests']['3']['objectiveStepsPtBR'],['Feche </script> & prossiga.'])
        again, *_ = update(output, localized, community, 'a' * 40)
        self.assertEqual(output, again)


if __name__ == '__main__':
    unittest.main()
